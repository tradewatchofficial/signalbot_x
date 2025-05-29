import os
import asyncio
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

import discord
from dotenv import load_dotenv
import feedparser
import requests
from googletrans import Translator

# ─── HTTP 서버 (Render 헬스체크용) ────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_webserver():
    port = int(os.environ.get("PORT", 5000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

threading.Thread(target=run_webserver, daemon=True).start()
# ──────────────────────────────────────────────────────────────────────────

# ─── 환경변수 로드 ─────────────────────────────────────────────────────────
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID    = int(os.getenv("DISCORD_CHANNEL_ID"))
RSS_URL       = "https://nitter.net/elonmusk/rss"  # 필요 시 다른 인스턴스로 교체
# ──────────────────────────────────────────────────────────────────────────

# ─── 디스코드 & 번역기 초기화 ──────────────────────────────────────────────
translator = Translator()
intents    = discord.Intents.default()
intents.message_content = True
bot        = discord.Client(intents=intents)
# ──────────────────────────────────────────────────────────────────────────

# 마지막으로 처리한 RSS 엔트리 ID
last_entry_id = None

async def check_elon_rss():
    global last_entry_id
    await bot.wait_until_ready()
    print("✅ on_ready fired → starting RSS loop", flush=True)
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"❌ Channel {CHANNEL_ID} not found!", flush=True)
        return

    while True:
        print(f"[DEBUG] Fetching RSS… last_entry_id={last_entry_id}", flush=True)
        try:
            resp = requests.get(
                RSS_URL,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            )
            feed = feedparser.parse(resp.content)
        except Exception as e:
            print("❌ RSS fetch error:", e, flush=True)
            await asyncio.sleep(60)
            continue

        entries = feed.entries
        print(f"[DEBUG] Retrieved {len(entries)} entries", flush=True)

        new_entries = []
        for e in entries:
            if last_entry_id is None or e.id != last_entry_id:
                new_entries.append(e)
            else:
                break
        print(f"[DEBUG] New entries to send: {len(new_entries)}", flush=True)

        for e in reversed(new_entries):
            published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
            text      = e.title
            ko        = translator.translate(text, dest="ko").text
            url       = e.link

            msg = (
                f"🚀 **Elon Musk** at {published.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
                f"원문 : \"{text}\"\n"
                f"번역 : \"{ko}\"\n"
                f"트윗링크 : \"{url}\""
            )
            await channel.send(msg)

        if entries:
            last_entry_id = entries[0].id

        await asyncio.sleep(60)

@bot.event
async def on_ready():
    print(f"🔄 bot_x.py starting up... Logged in as {bot.user}", flush=True)
    bot.loop.create_task(check_elon_rss())

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.strip() == "!ping":
        await message.channel.send("🏓 Pong!",)

bot.run(DISCORD_TOKEN)
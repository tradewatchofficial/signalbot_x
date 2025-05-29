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
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# ─── HTTP 서버 (헬스체크) ────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_webserver():
    HTTPServer(("0.0.0.0", int(os.getenv("PORT", 5000))), Handler).serve_forever()

threading.Thread(target=run_webserver, daemon=True).start()

# ─── 환경변수 & RSS 인스턴스 설정 ─────────────────────────────────────────
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID    = int(os.getenv("DISCORD_CHANNEL_ID"))

BASE_URLS = [
    "https://nitter.snopyta.org",
    "https://nitter.1d4.us",
    "https://nitter.it",
    "https://nitter.net"
]
USER      = "elonmusk"
RSS_PATH  = f"/{USER}/rss"
# ──────────────────────────────────────────────────────────────────────────

# ─── requests 세션 + 재시도 설정 ────────────────────────────────────────────
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})
retries = Retry(total=5, backoff_factor=1, status_forcelist=[502,503,504], allowed_methods=["GET"])
session.mount("https://", HTTPAdapter(max_retries=retries))
# ──────────────────────────────────────────────────────────────────────────

# ─── Discord & Translator ─────────────────────────────────────────────────
translator = Translator()
intents    = discord.Intents.default()
intents.message_content = True
bot        = discord.Client(intents=intents)
# ──────────────────────────────────────────────────────────────────────────

last_entry_id = None

async def check_elon_rss():
    global last_entry_id
    await bot.wait_until_ready()
    print("✅ on_ready fired → starting RSS loop", flush=True)

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"❌ Channel {CHANNEL_ID} not found!", flush=True)
        return

    while True:
        print(f"[DEBUG] Fetching RSS… last_entry_id={last_entry_id}", flush=True)
        feed = None
        for base in BASE_URLS:
            url = base + RSS_PATH
            try:
                r = session.get(url, timeout=10)
                if r.status_code == 200:
                    feed = feedparser.parse(r.content)
                    print(f"[DEBUG] Fetched from {base}", flush=True)
                    break
                else:
                    print(f"[WARN] {base} returned {r.status_code}", flush=True)
            except Exception as e:
                print(f"[WARN] {base} error:", e, flush=True)

        if feed is None:
            print("❌ RSS fetch failed on all instances", flush=True)
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
            pub = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
            text = e.title
            ko   = translator.translate(text, dest="ko").text
            link = e.link

            msg = (
                f"🚀 **Elon Musk** at {pub.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
                f"원문 : \"{text}\"\n"
                f"번역 : \"{ko}\"\n"
                f"트윗링크 : \"{link}\""
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
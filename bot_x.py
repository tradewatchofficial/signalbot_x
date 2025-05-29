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

# ─── HTTP 서버 (Render 포트 바인딩용) ────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_webserver():
    port = int(os.environ.get("PORT", 5000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

threading.Thread(target=run_webserver, daemon=True).start()
# ────────────────────────────────────────────────────────────────────────

# ─── 환경변수 로드 ────────────────────────────────────────────────────────
load_dotenv()
DISCORD_TOKEN      = os.getenv("DISCORD_TOKEN")
CHANNEL_ID         = int(os.getenv("DISCORD_CHANNEL_ID"))
RSS_URL            = "https://nitter.net/elonmusk/rss"  # 필요 시 다른 Nitter 인스턴스로 교체
# ────────────────────────────────────────────────────────────────────────

# ─── 디스코드 & 번역기 초기화 ──────────────────────────────────────────────
translator = Translator()
intents    = discord.Intents.default()
intents.message_content = True
bot        = discord.Client(intents=intents)
# ────────────────────────────────────────────────────────────────────────

# 마지막으로 처리한 RSS 엔트리 ID
last_entry_id = None

async def check_elon_rss():
    global last_entry_id
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    while True:
        # ─── 디버그: RSS fetch 시작 ─────────────────────────────
        print(f"[DEBUG] Fetching RSS… last_entry_id={last_entry_id}")
        # ────────────────────────────────────────────────────────

        try:
            resp = requests.get(
                RSS_URL,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10
            )
            feed = feedparser.parse(resp.content)
        except Exception as e:
            print("❌ RSS fetch error:", e)
            await asyncio.sleep(60)
            continue

        entries = feed.entries
        print(f"[DEBUG] Retrieved {len(entries)} entries")  # 디버그: 몇 개 가져왔는지

        # 새로운 글만 골라내기
        new_entries = []
        for e in entries:
            if last_entry_id is None or e.id != last_entry_id:
                new_entries.append(e)
            else:
                break

        # 오래된 순서대로 전송
        for e in reversed(new_entries):
            # published_parsed → datetime (UTC aware)
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

        # 최신 entry.id 업데이트
        if entries:
            last_entry_id = entries[0].id

        # 60초마다 체크 (필요시 조정)
        await asyncio.sleep(60)

@bot.event
async def on_ready():
    print(f"✅ 봇 로그인 완료: {bot.user}")
    bot.loop.create_task(check_elon_rss())

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.strip() == "!ping":
        await message.channel.send("🏓 Pong!")

bot.run(DISCORD_TOKEN)
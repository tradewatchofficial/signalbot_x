import os
import asyncio
import threading
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

import discord
import feedparser
from dotenv import load_dotenv
from googletrans import Translator

# ─── HTTP 서버 (Render Web Service 포트 바인딩용) ────────────────────────
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
# 일론 머스크 RSS URL (Nitter)
RSS_URL            = "https://nitter.net/elonmusk/rss"
# ────────────────────────────────────────────────────────────────────────

# ─── 클라이언트 초기화 ───────────────────────────────────────────────────
translator = Translator()
intents    = discord.Intents.default()
intents.message_content = True
bot        = discord.Client(intents=intents)
# ────────────────────────────────────────────────────────────────────────

# 마지막으로 전송한 RSS 엔트리 ID 저장
last_entry_id = None

async def check_elon_rss():
    global last_entry_id
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    while True:
        feed = feedparser.parse(RSS_URL)
        entries = feed.entries

        new_entries = []
        for e in entries:
            # 첫 실행 땐 last_entry_id=None → 가장 최신만 처리
            if last_entry_id is None or e.id != last_entry_id:
                new_entries.append(e)
            else:
                break

        # 새로운 순서대로(오래된 것부터)
        for e in reversed(new_entries):
            # RSS published 파싱 (string → datetime)
            published = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
            text      = e.title
            # 실제 번역
            ko        = translator.translate(text, dest="ko").text
            url       = e.link

            msg = (
                f"🚀 **Elon Musk** at {published.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
                f"원문 : \"{text}\"\n"
                f"번역 : \"{ko}\"\n"
                f"트윗링크 : \"{url}\""
            )
            await channel.send(msg)

        # 가장 최신 entry.id 로 업데이트
        if entries:
            last_entry_id = entries[0].id

        # 1분마다 체크 (원하시면 더 길게 늘리세요)
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
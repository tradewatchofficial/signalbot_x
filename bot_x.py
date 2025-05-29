import os, asyncio, threading, urllib.parse
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

import discord
from dotenv import load_dotenv
import tweepy
from googletrans import Translator

# HTTP 서버 (Render 포트 바인딩용)
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
def run_webserver():
    port = int(os.environ.get("PORT", 5000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
threading.Thread(target=run_webserver, daemon=True).start()

# 환경변수 로드
load_dotenv()
DISCORD_TOKEN        = os.getenv("DISCORD_TOKEN")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
CHANNEL_ID           = int(os.getenv("DISCORD_CHANNEL_ID"))

# 클라이언트 초기화
translator = Translator()
twitter    = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
# 루프 밖에서 한 번만 가져오기
ELON_ID     = twitter.get_user(username="elonmusk").data.id

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

last_tweet_id = None

async def check_elon_tweets():
    global last_tweet_id
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    while True:
        now = datetime.utcnow()
        tweets = twitter.get_users_tweets(
            ELON_ID,
            since_id=last_tweet_id,
            max_results=10,
            tweet_fields=["created_at","text"]
        )

        to_send = []
        if tweets.data:
            for t in tweets.data:
                # ─── 30분 이내로 필터링 ───────────────────────
                if t.created_at and t.created_at >= now - timedelta(minutes=30):
                    to_send.append(t)
                # ────────────────────────────────────────────────

        for t in reversed(to_send):
            text      = t.text
            ko        = translator.translate(text, dest="ko").text
            timestamp = t.created_at.strftime("%Y-%m-%d %H:%M")
            url       = f"https://x.com/elonmusk/status/{t.id}"

            msg = (
                f"🚀 **Elon Musk** at {timestamp} UTC\n\n"
                f"원문 : \"{text}\"\n"
                f"번역 : \"{ko}\"\n"
                f"트윗링크 : \"{url}\""
            )
            await channel.send(msg)

        if tweets.data:
            last_tweet_id = tweets.data[0].id

        # 1분마다 체크 → 30분 내 새 트윗만 가져오기
        await asyncio.sleep(60)

@bot.event
async def on_ready():
    print(f"✅ 봇 로그인 완료: {bot.user}")
    bot.loop.create_task(check_elon_tweets())

@bot.event
async def on_message(message):
    if message.author.bot: return
    if message.content.strip() == "!ping":
        await message.channel.send("🏓 Pong!")

bot.run(DISCORD_TOKEN)
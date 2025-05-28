import os
import asyncio
import threading
import urllib.parse
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler

import discord
from dotenv import load_dotenv
import tweepy
from googletrans import Translator

# ─── HTTP Server for Render Free Web Service ─────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_webserver():
    port = int(os.environ.get("PORT", 5000))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

# Start the HTTP server in a daemon thread
threading.Thread(target=run_webserver, daemon=True).start()
# ────────────────────────────────────────────────────────────────────────

# ─── Load environment variables ─────────────────────────────────────────
load_dotenv()
DISCORD_TOKEN       = os.getenv("DISCORD_TOKEN")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
CHANNEL_ID          = int(os.getenv("DISCORD_CHANNEL_ID"))
# ────────────────────────────────────────────────────────────────────────

# ─── Initialize Twitter client and Translator ──────────────────────────
twitter    = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
translator = Translator()
# ────────────────────────────────────────────────────────────────────────

# ─── Initialize Discord client ──────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
# ────────────────────────────────────────────────────────────────────────

last_tweet_id = None

async def check_elon_tweets():
    global last_tweet_id
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)

    while True:
        now = datetime.utcnow()
        # Fetch up to 10 latest tweets since last_tweet_id
        tweets = twitter.get_users_tweets(
            twitter.get_user(username="elonmusk").data.id,
            since_id=last_tweet_id,
            max_results=10,
            tweet_fields=["created_at", "text"]
        )

        to_send = []
        if tweets.data:
            for t in tweets.data:
                # Only include tweets from the last 5 minutes
                if t.created_at and t.created_at >= now - timedelta(minutes=5):
                    to_send.append(t)

        # Send messages in chronological order
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

        # Update last_tweet_id to avoid duplicates
        if tweets.data:
            last_tweet_id = tweets.data[0].id

        # Wait 60 seconds before checking again
        await asyncio.sleep(60)


@bot.event
async def on_ready():
    print(f"✅ 봇 로그인 완료: {bot.user}")
    bot.loop.create_task(check_elon_tweets())


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.strip() == "!ping":
        await message.channel.send("🏓 Pong!")


bot.run(DISCORD_TOKEN)
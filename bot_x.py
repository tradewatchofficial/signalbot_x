import os, asyncio, urllib.parse
import discord
from dotenv import load_dotenv
import tweepy

# 1) 환경변수 로드
load_dotenv()
DISCORD_TOKEN       = os.getenv("DISCORD_TOKEN")
TWITTER_BEARER      = os.getenv("TWITTER_BEARER_TOKEN")
CHANNEL_ID          = int(os.getenv("DISCORD_CHANNEL_ID"))

# 2) Twitter 클라이언트
twitter = tweepy.Client(bearer_token=TWITTER_BEARER)
elon = twitter.get_user(username="elonmusk").data
ELON_ID = elon.id

# 3) Discord 클라이언트
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

last_tweet_id = None

async def check_elon_tweets():
    global last_tweet_id
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    while True:
        tweets = twitter.get_users_tweets(
            ELON_ID,
            since_id=last_tweet_id,
            max_results=5,
            tweet_fields=["created_at","text"]
        )
        if tweets.data:
            for t in reversed(tweets.data):
                text = t.text
                q = urllib.parse.quote(text)
                links = {
                  "Google": f"https://translate.google.com/?sl=en&tl=ko&text={q}&op=translate",
                  "Papago": f"https://papago.naver.com/?sk=en&tk=ko&st={q}",
                  "DeepL": f"https://www.deepl.com/translator#en/ko/{q}"
                }
                msg = (
                    f"🚀 **Elon Musk** (@elonmusk) at {t.created_at:%Y-%m-%d %H:%M} UTC\n\n"
                    f"> {text}\n\n**번역링크**:\n"
                )
                for name, url in links.items():
                    msg += f"- [{name}]({url})\n"
                await channel.send(msg)
            last_tweet_id = tweets.data[0].id
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
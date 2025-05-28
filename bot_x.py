import os, asyncio, urllib.parse
import discord
from dotenv import load_dotenv
import tweepy

# 1) 환경변수 로드
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TWITTER_BEARER = os.getenv("TWITTER_BEARER_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))

# 2) 트위터 클라이언트 초기화
twitter = tweepy.Client(bearer_token=TWITTER_BEARER)
# 엘론 머스크 유저 아이디 조회 (한 번만 실행해도 OK)
elon = twitter.get_user(username="elonmusk").data
ELON_ID = elon.id

# 3) 디스코드 클라이언트 초기화
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

# 마지막으로 처리한 트윗 ID 저장
last_tweet_id = None

async def check_elon_tweets():
    global last_tweet_id
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID)
    while True:
        # since_id에 None 이면 최신 5개, 아니면 그 이후만
        tweets = twitter.get_users_tweets(ELON_ID,
                                         since_id=last_tweet_id,
                                         max_results=5,
                                         tweet_fields=["created_at","text"])
        if tweets.data:
            for t in reversed(tweets.data):
                text = t.text
                # 번역 링크 생성
                q = urllib.parse.quote(text)
                links = {
                    "Google Translate": f"https://translate.google.com/?sl=en&tl=ko&text={q}&op=translate",
                    "Papago":          f"https://papago.naver.com/?sk=en&tk=ko&st={q}",
                    "DeepL":           f"https://www.deepl.com/translator#en/ko/{q}"
                }
                # 메시지 포맷 조립
                msg = f"🚀 **Elon Musk** (@elonmusk) at {t.created_at:%Y-%m-%d %H:%M} UTC\n\n"
                msg += f"> {text}\n\n"
                msg += "**번역 링크**:\n"
                for name, url in links.items():
                    msg += f"- [{name}]({url})\n"
                await channel.send(msg)
            last_tweet_id = tweets.data[0].id
        await asyncio.sleep(60)  # 1분마다 체크

@bot.event
async def on_ready():
    print(f"✅ 봇 로그인 완료: {bot.user}")
    # 백그라운드 태스크 시작
    bot.loop.create_task(check_elon_tweets())

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.strip() == "!ping":
        await message.channel.send("🏓 Pong!")

bot.run(DISCORD_TOKEN)
import requests
import re
import os
import redis

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 获取 Redis URL
redis_url = os.getenv("UPSTASH_REDIS_URL")
if not redis_url:
    raise ValueError("Please set REDIS_URL environment variable in GitHub Secrets")
# 连接 Redis
r = redis.from_url(redis_url, decode_responses=True)


# 频道 ID / @名
CHANNEL_IDS = os.getenv("CHANNEL_IDS").split(",")

# 过期时间（秒）
TTL = 1 * 60 * 60  #test 先不设置过期时间

def build_live_url(cid: str) -> str:
    cid = cid.strip()
    if cid.startswith("@"):
        return f"https://www.youtube.com/{cid}/live"
    else:
        return f"https://www.youtube.com/channel/{cid}/live"

def send_telegram(msg: str):
    requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        params={"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    )

for cid in CHANNEL_IDS:
    live_page = build_live_url(cid)
    resp = requests.get(live_page, headers={"User-Agent": "Mozilla/5.0"})
    html = resp.text

    match = re.search(r"watch\?v=([a-zA-Z0-9_-]{11})", html)
    if match:
        video_id = match.group(1)
        live_url = f"https://www.youtube.com/watch?v={video_id}"

        key = f"live:{cid}"
        last_id = r.get(key)

        if not last_id or last_id.decode() != video_id:
            send_telegram(f"📺频道正在直播！\n{live_url}")
            r.setex(key, video_id)  # 设置过期时间

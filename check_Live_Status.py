import requests
import re
import os
import redis

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Redis
REDIS_URL = os.getenv("UPSTASH_REDIS_URL")
rdb = redis.Redis.from_url(REDIS_URL,ssl=True)

# 频道 ID / @名
channel_ids_str = os.getenv("CHANNEL_IDS")
if not channel_ids_str:
    raise ValueError("CHANNEL_IDS environment variable is not set")

CHANNEL_IDS = channel_ids_str.split(",")
print(CHANNEL_IDS)
# 过期时间（秒）
TTL = 0 * 60 * 60  #test 先不设置过期时间

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
        last_id = rdb.get(key)

        if not last_id or last_id.decode() != video_id:
            send_telegram(f"频道 {cid} 正在直播！\n{live_url}")
            rdb.setex(key, TTL, video_id)  # 设置过期时间

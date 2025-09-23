import requests
import re
import os
import redis
import json

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

def get_live_url(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}/live"
    # 不允许自动重定向
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=False)

    # 如果状态码是 302 重定向，Location 就是正在直播的 URL
    if resp.status_code in (301, 302):
        live_url = resp.headers.get("Location")
        if live_url:
            # 补全为完整 URL
            if live_url.startswith("/watch"):
                live_url = "https://www.youtube.com" + live_url
            return live_url
    return None

# 遍历频道列表
for cid in CHANNEL_IDS:
    live_url = get_live_url(cid)
    if live_url:
        print("频道正在直播，链接:", live_url)
        key = f"live:{cid}"
        last_id = r.get(key)
        if not last_id or last_id.decode() != live_url:
            send_telegram(f"📺频道正在直播！\n{live_url}")
            r.set(key, live_url)
    else:
        print(f"频道 {cid} 当前没有直播")
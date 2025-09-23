import requests
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

# Holodex API Key
HOLODEX_API_KEY = os.getenv("HOLODEX_API_KEY")
if not HOLODEX_API_KEY:
    raise ValueError("Please set HOLODEX_API_KEY environment variable")

# 频道
CHANNEL_IDS = os.getenv("CHANNEL_IDS").split(",")

# 过期时间（秒）
#TTL = 1 * 60 * 60  #test 先不设置过期时间

def send_telegram(msg: str):
    requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        params={"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    )

def get_live_url(channel_id):
    url = f"https://holodex.net/api/v2/live/{channel_id}"
    headers = {"X-APIKEY": HOLODEX_API_KEY}
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        # if resp.status_code == 200:
        #   print(f"[{channel_id}] Holodex API请求成功: {resp.status_code} {resp.text}")
        #   return None
        data = resp.json()
        if data and data[0]["status"] == "live":
            video_id = data[0]["id"]
            return f"https://www.youtube.com/watch?v={video_id}"
    except ValueError:
        print(f"[{channel_id}] 返回内容不是 JSON，可能是 HTML 或 API Key 错误")
    except Exception as e:
        print(f"[{channel_id}] 请求异常: {e}")
    return None

# 遍历频道列表
for cid in CHANNEL_IDS:
    cid = cid.strip()
    live_url = get_live_url(cid)
    if live_url:
        print(f"[{cid}] 正在直播: {live_url}")
        key = f"live:{cid}"
        last_id = r.get(key)
        if not last_id or last_id.decode() != live_url:
            send_telegram(f"📺频道正在直播！\n{live_url}")
            r.set(key, live_url)
    else:
        print(f"频道 {cid} 当前没有直播")

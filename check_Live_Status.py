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

def get_live_video_id(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}/live"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    html = resp.text

    # 提取 ytInitialData JSON
    match = re.search(r'var ytInitialData = ({.*?});</script>', html)
    if not match:
        return None

    data = json.loads(match.group(1))

    try:
        # 获取频道 tab 内容
        tabs = data['contents']['twoColumnBrowseResultsRenderer']['tabs']
        for tab in tabs:
            tab_content = tab.get('tabRenderer', {}).get('content', {})
            sections = tab_content.get('sectionListRenderer', {}).get('contents', [])
            for section in sections:
                items = section.get('itemSectionRenderer', {}).get('contents', [])
                for item in items:
                    video = item.get('videoRenderer')
                    if video:
                        # 判断是否正在直播
                        badges = video.get('badges', [])
                        for badge in badges:
                            style = badge.get('metadataBadgeRenderer', {}).get('style')
                            if style == 'BADGE_STYLE_TYPE_LIVE_NOW':
                                return video.get('videoId')
    except Exception:
        return None

    return None

# 遍历频道列表
for cid in CHANNEL_IDS:
    video_id = get_live_video_id(cid)
    if video_id:
        live_url = f"https://www.youtube.com/watch?v={video_id}"
        print("频道正在直播，链接:", live_url)

        key = f"live:{cid}"
        last_id = r.get(key)
        if not last_id or last_id.decode() != video_id:
            send_telegram(f"📺频道正在直播！\n{live_url}")
            r.set(key, live_url)  # 可加过期时间 ex=10800
    else:
        print(f"频道 {cid} 当前没有直播")
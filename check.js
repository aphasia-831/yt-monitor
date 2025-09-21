import { Redis } from "@upstash/redis";

const {
  YT_API_KEY,
  CHANNEL_IDS,
  TELEGRAM_BOT_TOKEN,
  TELEGRAM_CHAT_ID,
  UPSTASH_REDIS_URL,
  UPSTASH_REDIS_TOKEN,
  NOTIFY_TTL_HOURS = "4"
} = process.env;

if (!YT_API_KEY || !CHANNEL_IDS || !TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
  console.error("Missing required env vars. Please set YT_API_KEY, CHANNEL_IDS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (and UPSTASH_REDIS_* if using redis).");
  process.exit(1);
}

const redis = UPSTASH_REDIS_URL && UPSTASH_REDIS_TOKEN
  ? new Redis({ url: UPSTASH_REDIS_URL, token: UPSTASH_REDIS_TOKEN })
  : null;

const channels = CHANNEL_IDS.split(",").map(s => s.trim()).filter(Boolean);
const TTL_SECONDS = Math.max(1, parseInt(NOTIFY_TTL_HOURS, 10) || 24) * 3600;

async function fetchJson(url) {
  const r = await fetch(url);
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`HTTP ${r.status}: ${txt}`);
  }
  return r.json();
}

async function getLiveListForChannel(channelId) {
  const url = `https://www.googleapis.com/youtube/v3/search?part=snippet&channelId=${encodeURIComponent(channelId)}&eventType=live&type=video&key=${YT_API_KEY}&maxResults=5`;
  const data = await fetchJson(url);
  if (!data.items || data.items.length === 0) return [];
  return data.items.map(item => {
    const videoId = item.id?.videoId;
    const title = item.snippet?.title || "（无标题）";
    const channelTitle = item.snippet?.channelTitle || "";
    const thumb = item.snippet?.thumbnails?.high?.url || item.snippet?.thumbnails?.default?.url || null;
    return { videoId, title, channelTitle, thumb };
  }).filter(x => x.videoId);
}

async function sendTelegramMessage(text) {
  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: TELEGRAM_CHAT_ID,
      text,
      disable_web_page_preview: false
    })
  });
  const j = await resp.json();
  if (!j.ok) {
    console.error("Telegram send error:", j);
  }
  return j;
}

async function main() {
  console.log("Start check:", new Date().toISOString());
  for (const ch of channels) {
    try {
      const items = await getLiveListForChannel(ch);
      if (items.length === 0) {
        console.log(`channel ${ch} no live`);
        continue;
      }
      for (const it of items) {
        const key = `yt_monitor:video:${it.videoId}`;

        // 如果配置了 Upstash，先检查 Redis
        if (redis) {
          const exists = await redis.get(key);
          if (exists) {
            console.log(`skip ${it.videoId} (already notified)`);
            continue;
          }
        }

        // 发送 Telegram
        const link = `https://www.youtube.com/watch?v=${it.videoId}`;
        const text = `📺 频道开播啦！\n${it.title}\n频道：${it.channelTitle}\n${link}`;
        console.log("notify:", it.videoId, it.title);
        await sendTelegramMessage(text);

        // 写入 Redis（避免重复推送）
        if (redis) {
          await redis.set(key, "1", { ex: TTL_SECONDS });
        }
      }
    } catch (e) {
      console.error("error for channel", ch, e?.message ?? e);
    }
  }
  console.log("Finished check");
}

main().catch(e => {
  console.error("Fatal error:", e);
  process.exit(1);
});

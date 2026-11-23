// GET /api/data: everything the app shows, with signed media URLs.
import { rest, sign, send } from './_sb.js';
import BRAND from './_brand.js';

// The full episode is found by itself: the first long video on the show's YouTube channel published on or after the
// recording day. UULF<channel> is YouTube's long-videos-only uploads playlist (no Shorts); its RSS feed needs no key.
// No channel id in brand.json: skip this, and the owner pastes the link by hand.
const CHANNEL = String(BRAND.posting?.youtube_channel_id || '').trim().replace(/^UC/, '');
const FEED = CHANNEL && `https://www.youtube.com/feeds/videos.xml?playlist_id=UULF${CHANNEL}`;
const showDay = t => new Date(t).toLocaleDateString('en-CA', { timeZone: BRAND.posting?.timezone || 'UTC' });
async function autoLinks(episodes) {
  const need = episodes.filter(e => !e.full_url && e.recorded_on);
  if (!FEED || !need.length) return;
  let xml = '';
  try { xml = await (await fetch(FEED, { signal: AbortSignal.timeout(4000) })).text(); } catch { return; }
  const vids = [...xml.matchAll(/<entry>([\s\S]*?)<\/entry>/g)].map(([, e]) => ({
    id: e.match(/<yt:videoId>(.*?)</)?.[1], title: (e.match(/<title>(.*?)<\/title>/)?.[1] || '').replace(/&amp;/g, '&').replace(/&#39;/g, "'").replace(/&quot;/g, '"'),
    day: showDay(e.match(/<published>(.*?)</)?.[1]) })).filter(v => v.id).sort((a, b) => a.day.localeCompare(b.day));
  for (const e of need) {
    const v = vids.find(x => x.day >= e.recorded_on);
    if (!v) continue;
    Object.assign(e, { full_url: `https://www.youtube.com/watch?v=${v.id}`, full_url_auto: true, full_title: v.title });
    await rest(`shorts_episodes?id=eq.${encodeURIComponent(e.id)}`, { method: 'PATCH', body: { full_url: e.full_url, full_url_auto: true, full_title: v.title } }).catch(() => {});
  }
}

export default async function handler(req, res) {
  try {
    const [episodes, items, versions, feedback] = await Promise.all([
      rest('shorts_episodes?select=*&order=recorded_on.desc.nullslast,id.desc'),
      rest('shorts_items?select=*&order=episode_id.desc,num.asc'),
      rest('shorts_versions?select=*&order=short_id.asc,round.desc'),
      rest('shorts_feedback?select=*&order=created_at.desc&limit=2000')
    ]);
    await autoLinks(episodes);
    // 7 days: a tab left open overnight kept 12 h links and then could not play anything.
    const urls = await sign(versions.flatMap(v => [v.video_path, v.poster_path, ...Object.values(v.tracks || {}), ...Object.values(v.play || {})]), 7 * 86400);
    for (const v of versions) {
      v.video = urls[v.video_path] || null;
      v.poster = urls[v.poster_path] || null;
      v.track_urls = Object.fromEntries(Object.entries(v.tracks || {}).map(([k, p]) => [k, urls[p] || null]));
      v.play_urls = Object.fromEntries(Object.entries(v.play || {}).map(([k, p]) => [k, urls[p] || null]));   // video + mix in one file
    }
    send(res, 200, { episodes, items, versions, feedback, at: new Date().toISOString(), build: process.env.VERCEL_DEPLOYMENT_ID || null });
  } catch (e) {
    send(res, 500, { error: String(e.message || e) });
  }
}

// /api/stats: real numbers for every live Short. GET reads the cached snapshots; POST {op:'refresh'} reads each platform and stores a new snapshot.
// YouTube and TikTok: their public video pages (fresh). Instagram: the Apify reel scraper (about $0.002 a reel, at most every 6 h),
// else Buffer post metrics when Buffer has them. Nothing is ever made up:
// a number the platform does not give stays null, and the app shows "no data yet".
import { rest, send, readBody } from './_sb.js';
import BRAND from './_brand.js';

const PLATFORMS = ['youtube', 'tiktok', 'instagram'];
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36';
const MIN_GAP = 2 * 60 * 1000;   // two refreshes closer than this reuse the last snapshot
const num = s => s == null ? null : Number(String(s).replace(/[^\d]/g, '')) || 0;

async function page(url) {
  const r = await fetch(url, { headers: { 'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9', Cookie: 'CONSENT=YES+1; SOCS=CAI' }, signal: AbortSignal.timeout(15000) });
  if (!r.ok) throw new Error(`${r.status}`);
  return r.text();
}

async function youtube(url) {
  const id = (url.match(/(?:v=|shorts\/|youtu\.be\/)([\w-]{11})/) || [])[1];
  if (!id) throw new Error('no video id');
  const h = await page(`https://www.youtube.com/shorts/${id}`);
  const views = h.match(/"viewCount":"(\d+)"/)?.[1];
  if (views == null) throw new Error('no view count on the page');
  const likes = h.match(new RegExp(`"externalVideoId":"${id}","likeCount":"(\\d+)"`))?.[1];
  const comments = h.match(/"accessibilityText":"View ([\d,]+) comments?"/)?.[1];   // the page's own Short; prefetched ones are escaped (\x22)
  return { views: num(views), likes: num(likes), comments: num(comments), shares: null };
}

async function tiktok(url) {
  const h = await page(url);
  const raw = h.match(/<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([\s\S]*?)<\/script>/)?.[1];
  if (!raw) throw new Error('no data on the page');
  const it = JSON.parse(raw)?.__DEFAULT_SCOPE__?.['webapp.video-detail']?.itemInfo?.itemStruct;
  const s = it?.stats;
  if (!s || !url.includes(it.id)) throw new Error('no stats for this video');
  return { views: num(s.playCount), likes: num(s.diggCount), comments: num(s.commentCount), shares: num(s.shareCount) };
}

const BUFFER_READ = `query($id: PostId!) { post(input: { id: $id }) { metrics { type value } } }`;
async function buffer(id) {
  const r = await fetch('https://api.buffer.com', {
    method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${process.env.BUFFER_API_KEY}` },
    body: JSON.stringify({ query: BUFFER_READ, variables: { id } }), signal: AbortSignal.timeout(15000)
  });
  const j = await r.json();
  if (j.errors) throw new Error(j.errors[0]?.message || 'buffer error');
  const m = j.data?.post?.metrics;
  if (!m?.length) throw new Error('no data yet');
  const v = Object.fromEntries(m.map(x => [x.type, x.value]));
  return { views: v.views ?? v.plays ?? null, likes: v.reactions ?? v.likes ?? null, comments: v.comments ?? null, shares: v.shares ?? null };
}

async function read(p, post) {
  if (p === 'youtube' && post.url) return { ...(await youtube(post.url)), source: 'youtube page' };
  if (p === 'tiktok' && post.url) return { ...(await tiktok(post.url)), source: 'tiktok page' };
  if (post.buffer_id) return { ...(await buffer(post.buffer_id)), source: 'buffer' };
  throw new Error('no link yet');
}

// Instagram shows no numbers without a login, so a paid Apify run reads the public reels. It runs in the background:
// one call starts it, a later call (the app asks again after about a minute) collects it. Job state lives in shorts_kv.
const IG_EVERY = 6 * 3600e3;
const APIFY = 'https://api.apify.com/v2';
async function apify(path, body) {
  const r = await fetch(APIFY + path, { method: body ? 'POST' : 'GET', headers: { Authorization: `Bearer ${process.env.APIFY_TOKEN}`, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(20000) });
  const j = await r.json();
  if (!r.ok) throw new Error(`apify ${r.status} ${j.error?.message || ''}`.trim());
  return j.data ?? j;
}
const igCode = u => (u || '').match(/\/(?:reel|reels|p)\/([\w-]+)/)?.[1];
const IG_USER = String(BRAND.posting?.instagram_username || '').trim().replace(/^@/, '');
// Instagram numbers are optional. Without a token and a username the page still works and says so.
const igOff = () => !process.env.APIFY_TOKEN ? 'Instagram numbers need an APIFY_TOKEN. YouTube and TikTok do not.'
  : !IG_USER ? 'Instagram numbers need instagram_username in brand.json.' : null;

async function instagram(live, at) {
  if (igOff()) return { rows: [], state: { off: igOff() } };
  const want = live.filter(it => it.posted?.instagram?.state === 'posted' && igCode(it.posted.instagram.url));
  const [row] = await rest('shorts_kv?k=eq.ig_run&select=v');
  let j = row?.v || {};
  const rows = [], now = Date.now();
  if (j.run && !j.done) {
    const run = await apify(`/actor-runs/${j.run}`);
    if (run.status === 'SUCCEEDED') {
      const items = await apify(`/datasets/${run.defaultDatasetId}/items?clean=1`);
      const by = new Map(items.map(x => [x.shortCode, x]));
      for (const it of want) {
        const x = by.get(igCode(it.posted.instagram.url)); if (!x) continue;
        rows.push({ short_id: it.id, platform: 'instagram', at, views: x.videoPlayCount ?? x.videoViewCount ?? null, likes: x.likesCount ?? null, comments: x.commentsCount ?? null, shares: null, source: 'apify' });
      }
      j = { ...j, done: true, harvested_at: new Date(now).toISOString(), found: rows.length, cost_usd: run.usageTotalUsd ?? null };
    } else if (['FAILED', 'ABORTED', 'TIMED-OUT'].includes(run.status) || now - Date.parse(j.started_at) > 20 * 60000) {
      j = { ...j, done: true, error: run.status };
    }
  }
  if (want.length && (!j.run || j.done) && (!j.started_at || now - Date.parse(j.started_at) > IG_EVERY)) {
    // Newest reels first; a few spare for pinned or older reels. About $0.001 + $0.0023 a reel; the cap stops a runaway.
    const recent = want.filter(it => now - Date.parse(it.posted.instagram.at || 0) < 45 * 86400e3).length;
    const limit = Math.min(recent, 30) + 4;
    const run = await apify(`/acts/apify~instagram-reel-scraper/runs?maxTotalChargeUsd=${(0.006 + 0.003 * limit).toFixed(3)}`, { username: [IG_USER], resultsLimit: limit });
    j = { ...j, run: run.id, started_at: new Date(now).toISOString(), done: false, limit, error: null };
  }
  await rest('shorts_kv', { method: 'POST', body: { k: 'ig_run', v: j, updated_at: new Date().toISOString() }, prefer: 'resolution=merge-duplicates' });
  return { rows, state: { pending: !!(j.run && !j.done), harvested_at: j.harvested_at || null, error: j.error || null } };
}

async function snapshots() {
  const since = new Date(Date.now() - 60 * 86400e3).toISOString();
  return rest(`shorts_stats?at=gte.${since}&select=short_id,platform,at,views,likes,comments,shares,source&order=at.asc&limit=20000`);
}

async function refresh() {
  const live = await rest(`shorts_items?status=eq.posted&select=id,posted`);
  const at = new Date().toISOString();
  let ig = { rows: [], state: {} };
  try { ig = await instagram(live, at); } catch (e) { ig.state = { error: String(e.message || e).slice(0, 120) }; }
  if (ig.rows.length) await rest('shorts_stats', { method: 'POST', body: ig.rows });
  const [last] = await rest('shorts_stats?platform=neq.instagram&select=at&order=at.desc&limit=1');
  if (last && Date.now() - new Date(last.at) < MIN_GAP) return { skipped: true, misses: [], ig: ig.state };
  const jobs = live.flatMap(it => PLATFORMS.filter(p => p !== 'instagram' && it.posted?.[p]?.state === 'posted').map(p => ({ id: it.id, p, post: it.posted[p] })));
  const done = await Promise.all(jobs.map(j => read(j.p, j.post).then(s => ({ ok: true, row: { short_id: j.id, platform: j.p, at, ...s } }), e => ({ ok: false, miss: { short_id: j.id, platform: j.p, why: String(e.message || e).slice(0, 120) } }))));
  const rows = done.filter(d => d.ok).map(d => d.row);
  if (rows.length) await rest('shorts_stats', { method: 'POST', body: rows });
  return { skipped: false, misses: done.filter(d => !d.ok).map(d => d.miss), ig: ig.state };
}

export default async function handler(req, res) {
  try {
    let misses = [], ig = null;
    if (req.method === 'POST') {
      const b = await readBody(req);
      if (b.op !== 'refresh') return send(res, 400, { error: 'unknown op' });
      ({ misses, ig } = await refresh());
    } else if (req.method !== 'GET') return send(res, 405, { error: 'GET or POST' });
    if (!ig) { const [row] = await rest('shorts_kv?k=eq.ig_run&select=v'); const j = row?.v || {}; ig = { pending: !!(j.run && !j.done), harvested_at: j.harvested_at || null, error: j.error || null, off: igOff() }; }
    const rows = await snapshots();
    send(res, 200, { rows, updated_at: rows.length ? rows[rows.length - 1].at : null, misses, ig });
  } catch (e) {
    send(res, 500, { error: String(e.message || e) });
  }
}

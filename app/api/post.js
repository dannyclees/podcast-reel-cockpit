// POST /api/post: real posting through Buffer, to the channels set in the BUFFER_CHANNELS env var.
// Buffer holds each post until its slot, then publishes it. Nothing is sent unless POSTING_ENABLED=1.
//   op status   -> is posting on, which Buffer channels
//   op prepare  -> build the file that would be posted (video + chosen music mix). Sends nothing.
//   op schedule -> {id, platforms, due: {platform: {iso} | {day, min}}, copy, round?, now?}; now: true posts at once
//                  (a post already waiting in Buffer is deleted first, since Buffer has no "share now" for it)
//   op cancel   -> {id, platform}: delete the waiting Buffer post
//   op sync     -> ask Buffer about every waiting post: sent -> Posted + live link, error -> Failed + reason
import { spawn } from 'node:child_process';
import { writeFile, readFile, rm } from 'node:fs/promises';
import ffmpegPath from 'ffmpeg-static';
import { rest, sign, send, readBody, download, upload } from './_sb.js';
import BRAND from './_brand.js';

const CHANNELS = JSON.parse(process.env.BUFFER_CHANNELS || '{}');   // {youtube: {id, name}, instagram: {id, name}}
const ENABLED = process.env.POSTING_ENABLED === '1';
const NAMES = { youtube: 'YouTube', instagram: 'Instagram', tiktok: 'TikTok' };
const STATUS = { draft: 'Draft', approved: 'Approved', scheduled: 'Scheduled', posted: 'Posted' };
const enc = encodeURIComponent;
const TZ = BRAND.posting?.timezone || 'UTC';

async function buffer(query, variables) {
  const r = await fetch('https://api.buffer.com', {
    method: 'POST', headers: { Authorization: `Bearer ${process.env.BUFFER_API_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, variables })
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok || j.errors) throw new Error(`Buffer: ${j.errors?.[0]?.message || r.status}`);
  return j.data;
}
const CREATE = `mutation($i: CreatePostInput!) { createPost(input: $i) { __typename
  ... on PostActionSuccess { post { id status dueAt } } ... on InvalidInputError { message } ... on UnexpectedError { message }
  ... on LimitReachedError { message } ... on RestProxyError { message } } }`;
const DELETE = `mutation($i: DeletePostInput!) { deletePost(input: $i) { __typename } }`;
const READ = `query($id: PostId!) { post(input: { id: $id }) { status externalLink sentAt error { message } } }`;

// A wall-clock time in the show's time zone (day + minutes after 00:00, may run past midnight) as a UTC instant.
function wallToUtc(day, min) {
  const [y, m, d] = day.split('-').map(Number);
  const wall = Date.UTC(y, m - 1, d) + min * 60000;
  const off = t => {   // time zone offset in ms at instant t
    const p = Object.fromEntries(new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
      .formatToParts(new Date(t)).map(x => [x.type, x.value]));
    return Date.UTC(+p.year, p.month - 1, +p.day, +p.hour, +p.minute, +p.second) - t;
  };
  return new Date(wall - off(wall - off(wall)));
}

// Live links as people open them: plain "@" (never the fullwidth U+FF20) and the www. host for TikTok.
const cleanLink = u => String(u || '').replace(/\uFF20/g, '@').replace(/^https:\/\/tiktok\.com\//, 'https://www.tiktok.com/');
const statusFrom = (posted, prev) => {
  const s = Object.values(posted).map(p => p?.state);
  return s.includes('posted') ? 'posted' : s.includes('scheduled') ? 'scheduled' : prev === 'draft' ? 'draft' : 'approved';
};
const getItem = async id => { const [it] = await rest(`shorts_items?id=eq.${enc(id)}&select=*`); if (!it) throw new Error(`no short ${id}`); return it; };
const patch = async (id, body) => (await rest(`shorts_items?id=eq.${enc(id)}`, { method: 'PATCH', body: { ...body, updated_at: new Date().toISOString() }, prefer: 'return=representation' }))[0];
const log = async (it, body) => (await rest('shorts_feedback', { method: 'POST', prefer: 'return=representation',
  body: { episode_id: it.episode_id, short_id: it.id, kind: 'status', author: 'app', body, status_at: it.status, round_at: it.round, track_at: it.track } }))[0];

function ffmpeg(args) {
  return new Promise((ok, bad) => {
    const p = spawn(ffmpegPath, args); let err = '';
    p.stderr.on('data', d => { err += d; });
    p.on('close', c => c === 0 ? ok() : bad(new Error(`ffmpeg ${c}: ${err.slice(-300)}`)));
  });
}

// The file to post: the full-quality master with the chosen music (and SFX) mix as its sound.
async function prepare(it, round = it.round) {
  const [v] = await rest(`shorts_versions?short_id=eq.${enc(it.id)}&round=eq.${round}&select=*`);
  if (!v) throw new Error(`no version ${round}`);
  if (!v?.master_path) throw new Error('no full-quality file for this version yet (run publish.py --master-only)');
  const tracks = v.tracks || {};
  const sfx = it.sfx !== false && Object.keys(tracks).some(k => k.startsWith('sfx_'));
  const key = (sfx ? 'sfx_' : '') + (it.track || 'none');
  if (key === 'none') return { path: v.master_path, key };
  if (!tracks[key]) throw new Error(`no ${key} mix for this version`);
  const out = `${v.master_path.replace(/master\.mp4$/, '')}post-${key}.mp4`;
  const tmp = `/tmp/${Date.now()}-${Math.random().toString(36).slice(2)}`;
  try {
    await writeFile(`${tmp}-v.mp4`, await download(v.master_path));
    await writeFile(`${tmp}-a.m4a`, await download(tracks[key]));
    await ffmpeg(['-y', '-v', 'error', '-i', `${tmp}-v.mp4`, '-i', `${tmp}-a.m4a`, '-map', '0:v:0', '-map', '1:a:0', '-c', 'copy', '-shortest', '-movflags', '+faststart', `${tmp}-o.mp4`]);
    const bytes = await readFile(`${tmp}-o.mp4`);
    await upload(out, bytes, 'video/mp4');
    return { path: out, key, mb: +(bytes.length / 1e6).toFixed(1) };
  } finally {
    await Promise.all(['-v.mp4', '-a.m4a', '-o.mp4'].map(x => rm(tmp + x, { force: true })));
  }
}

// R123: a Short is booked once per platform. Two guards, both fail closed:
// 1. claim(): one atomic write marks the platforms "booking". A second request loses the write and is refused.
// 2. inBuffer(): before each create, ask Buffer itself. A post already there is adopted, never booked again.
const BOOKING_MS = 10 * 60000;   // longer than any function can run, so an older claim is a crash
const booking = s => s?.state === 'booking' && Date.now() - Date.parse(s.at) < BOOKING_MS;
const KEY = t => String(t || '').replace(/\s+/g, ' ').trim().toLowerCase().slice(0, 200);
const LIST = `query($i: PostsInput!, $after: String) { posts(input: $i, first: 100, after: $after) { edges { node { id status dueAt sentAt text externalLink channelId } } pageInfo { hasNextPage endCursor } } }`;
let ORG;
async function listPosts(channelIds) {
  ORG ||= (await buffer('{ account { organizations { id } } }')).account.organizations[0].id;
  const out = []; let after = null;
  do {   // every page: Buffer does not sort these newest first
    const r = (await buffer(LIST, { i: { organizationId: ORG, filter: { channelIds, status: ['scheduled', 'sending', 'sent'] } }, after })).posts;   // never add needs_approval: Buffer then returns nothing
    out.push(...r.edges.map(e => e.node));
    after = r.pageInfo.hasNextPage ? r.pageInfo.endCursor : null;
  } while (after);
  if (!out.length) throw new Error('Buffer shows no posts on this channel, so the double-post check cannot run. Post once by hand in Buffer, then try again.');   // fail closed: an empty answer may be a bad answer
  return out;
}
const inBuffer = async (p, text, skip) => (await listPosts([CHANNELS[p].id])).find(x => x.id !== skip && KEY(x.text) === KEY(text));

// R124: two Shorts never share a time. Each request writes the time it wants, then reads the others: whoever claimed second steps aside.
const CLASH_MS = (BRAND.posting?.clash_hours ?? 1) * 3600e3, GAP_MS = (BRAND.posting?.gap_hours ?? 4) * 3600e3;
async function freeTime(it, wanted) {
  const me = Object.values(it.posted).find(s => booking(s) && s.due);
  if (!me) return wanted;
  const held = [], ahead = [];
  for (const o of await rest(`shorts_items?select=id,posted&id=neq.${enc(it.id)}`)) {
    const slots = Object.values(o.posted || {});
    for (const s of slots) if (s?.state === 'scheduled' && s.due) held.push(+new Date(s.due));
    const q = slots.find(s => booking(s) && s.due);
    if (q && (q.at < me.at || (q.at === me.at && o.id < it.id))) ahead.push({ at: q.at, id: o.id, t: +new Date(q.due) });
  }
  const settle = t => { for (let hit; (hit = held.find(h => Math.abs(h - t) < CLASH_MS)) !== undefined;) t = hit + GAP_MS; held.push(t); return t; };
  ahead.sort((a, b) => a.at < b.at ? -1 : a.at > b.at ? 1 : a.id < b.id ? -1 : 1).forEach(q => settle(q.t));
  return settle(wanted);
}

async function claim(it, plats, now, wanted) {
  if (plats.some(p => booking(it.posted?.[p]))) throw Object.assign(new Error('already being booked: nothing sent twice'), { code: 409 });
  const posted = { ...(it.posted || {}) }, at = new Date().toISOString();
  for (const p of plats) {
    const cur = posted[p];
    if (cur?.state === 'posted' || (cur?.state === 'scheduled' && !now)) continue;
    posted[p] = { state: 'booking', at, ...(wanted ? { due: wanted.toISOString() } : {}), ...(cur?.state === 'scheduled' ? { replaces: cur.buffer_id } : {}) };
  }
  const [won] = await rest(`shorts_items?id=eq.${enc(it.id)}&updated_at=eq.${enc(it.updated_at)}`, { method: 'PATCH', body: { posted, updated_at: new Date().toISOString() }, prefer: 'return=representation' });
  if (!won) throw Object.assign(new Error('already being booked: nothing sent twice'), { code: 409 });
  return won;
}

async function schedule(b, out) {
  if (!ENABLED) throw Object.assign(new Error('Posting is off. To turn it on, set POSTING_ENABLED=1 in Vercel and deploy again.'), { code: 403 });
  let it = await getItem(b.id);
  if (it.status === 'draft') throw Object.assign(new Error('approve it first'), { code: 409 });
  if (it.hold && !b.force) throw Object.assign(new Error(it.hold), { code: 409 });
  const plats = (b.platforms || []).filter(p => CHANNELS[p]);
  if (!plats.length) throw Object.assign(new Error('no connected platform chosen'), { code: 400 });
  const before = it.posted;
  const when = p => b.now ? new Date() : b.due?.[p]?.iso ? new Date(b.due[p].iso) : wallToUtc(b.due?.[p]?.day, b.due?.[p]?.min);
  const first = when(plats[0]), wanted = !b.now && Number.isFinite(+first) ? first : null;
  it = await claim(it, plats, b.now, wanted);
  let file, url, shift = 0;
  const words = t => new Date(t).toLocaleString('en-GB', { timeZone: TZ, weekday: 'short', hour: '2-digit', minute: '2-digit' });
  try {
    if (wanted) shift = await freeTime(it, +wanted) - wanted;
    if (shift) {
      const moved = new Date(+wanted + shift).toISOString();
      it = await patch(it.id, { posted: Object.fromEntries(Object.entries(it.posted).map(([k, s]) => [k, booking(s) ? { ...s, due: moved } : s])) });
      out.feedback.push(await log(it, `${words(wanted)} was taken by another Short, so this one moved to ${words(moved)}`));
    }
    file = await prepare(it, Number.isInteger(b.round) ? b.round : it.round);
    url = (await sign([file.path], 60 * 60 * 24 * 14))[file.path];
  } catch (e) {   // nothing went to Buffer: give the claim back
    await patch(it.id, { posted: before });
    throw e;
  }
  for (const p of plats) {
    const cur = it.posted?.[p];
    if (cur?.state !== 'booking') continue;   // posted, or already waiting in Buffer
    const due = new Date(+when(p) + shift);
    const c = b.copy?.[p] || {};
    let state;
    try {
      if (cur.replaces) {   // "post now" over a waiting post: if the old one cannot be removed, do not add a second
        const r = (await buffer(DELETE, { i: { id: cur.replaces } })).deletePost;
        if (r?.__typename !== 'DeletePostSuccess') throw new Error(`could not remove the waiting post: ${r?.__typename || 'no answer'}`);
      }
      if (!b.now && !(due > Date.now() + 5 * 60000)) throw new Error('that time has passed: pick a later one');
      if (!c.text?.trim()) throw new Error('post copy is empty');
      const there = b.repost ? null : await inBuffer(p, c.text, cur.replaces);   // repost: true is only for a post the owner deleted on purpose
      if (there) {
        state = there.status === 'sent'
          ? { state: 'posted', at: there.sentAt, buffer_id: there.id, via: 'buffer', url: cleanLink(there.externalLink), audio: file.key, round: Number.isInteger(b.round) ? b.round : it.round }
          : { state: 'scheduled', at: new Date().toISOString(), due: there.dueAt, buffer_id: there.id, via: 'buffer', url: '', audio: file.key, round: Number.isInteger(b.round) ? b.round : it.round };
        const posted = { ...it.posted, [p]: state }, prev = it.status;
        it = await patch(it.id, { posted, status: statusFrom(posted, prev) });
        out.feedback.push(await log(it, `${NAMES[p]}: already in Buffer, not booked again`));
        continue;
      }
      const input = { channelId: CHANNELS[p].id, schedulingType: 'automatic', mode: b.now ? 'shareNow' : 'customScheduled', ...(b.now ? {} : { dueAt: due.toISOString() }), needsApproval: false,
        text: c.text.slice(0, p === 'youtube' ? 5000 : 2200), assets: [{ video: { url } }] };
      if (p === 'youtube') {
        if (!c.title?.trim()) throw new Error('YouTube title is empty');
        input.metadata = { youtube: { title: c.title.slice(0, 100), privacy: 'public', categoryId: String(BRAND.posting?.youtube_category_id || '22'), madeForKids: false, notifySubscribers: true, license: 'youtube', embeddable: true } };
      } else if (p === 'instagram') input.metadata = { instagram: { type: 'reel', shouldShareToFeed: true } };
      const r = (await buffer(CREATE, { i: input })).createPost;
      if (r.__typename !== 'PostActionSuccess') throw new Error(r.message || r.__typename);
      state = { state: 'scheduled', at: new Date().toISOString(), due: due.toISOString(), buffer_id: r.post.id, via: 'buffer', url: '', audio: file.key, round: Number.isInteger(b.round) ? b.round : it.round };
    } catch (e) {
      state = { state: 'failed', at: new Date().toISOString(), error: String(e.message || e).slice(0, 300) };
    }
    const posted = { ...(it.posted || {}), [p]: state };
    const prev = it.status;
    it = await patch(it.id, { posted, status: statusFrom(posted, prev) });
    out.feedback.push(await log(it, state.state === 'scheduled'
      ? `${NAMES[p]}: ${b.now ? 'sent to Buffer to post now' : 'scheduled in Buffer for ' + due.toLocaleString('en-GB', { timeZone: TZ, weekday: 'short', hour: '2-digit', minute: '2-digit' })}`
      : `${NAMES[p]}: not scheduled: ${state.error}`));
    if (it.status !== prev) out.feedback.push(await log(it, `${STATUS[prev]} → ${STATUS[it.status]}`));
  }
  out.items.push(it);
}

async function cancel(b, out) {
  let it = await getItem(b.id);
  const cur = it.posted?.[b.platform];
  if (!cur) return out.items.push(it);
  if (cur.state === 'posted') throw Object.assign(new Error('already posted: delete it on the platform itself'), { code: 409 });
  if (booking(cur)) throw Object.assign(new Error('it is being booked right now: try again in a minute'), { code: 409 });
  if (cur.buffer_id && cur.state === 'scheduled') {
    try {
      const r = (await buffer(DELETE, { i: { id: cur.buffer_id } })).deletePost;
      if (r?.__typename !== 'DeletePostSuccess') throw new Error(`Buffer: ${r?.__typename || 'no answer'}`);
    } catch (e) {   // already gone from Buffer is fine; anything still there is an error
      let still = true;
      try { still = !!(await buffer(READ, { id: cur.buffer_id })).post; } catch (e2) { if (/not found/i.test(e2.message)) still = false; }
      if (still) throw e;
    }
  }
  const posted = { ...it.posted }; delete posted[b.platform];
  const prev = it.status;
  it = await patch(it.id, { posted, status: statusFrom(posted, prev) });
  out.feedback.push(await log(it, `${NAMES[b.platform] || b.platform}: removed from Buffer`));
  if (it.status !== prev) out.feedback.push(await log(it, `${STATUS[prev]} → ${STATUS[it.status]}`));
  out.items.push(it);
}

async function sync(out) {
  const waiting = (await rest('shorts_items?select=*&status=eq.scheduled'))
    .concat(await rest('shorts_items?select=*&status=eq.posted'))
    .filter(it => Object.values(it.posted || {}).some(p => p?.buffer_id && p.state === 'scheduled'));
  for (let it of waiting) {
    const posted = { ...it.posted }; const notes = [];
    for (const [p, s] of Object.entries(posted)) {
      if (!s?.buffer_id || s.state !== 'scheduled') continue;
      let post;
      try { post = (await buffer(READ, { id: s.buffer_id })).post; } catch (e) { continue; }
      if (!post) { posted[p] = { ...s, state: 'failed', error: 'the post is gone from Buffer' }; notes.push(`${NAMES[p]}: gone from Buffer`); }
      else if (post.status === 'sent') { posted[p] = { ...s, state: 'posted', at: post.sentAt || new Date().toISOString(), url: cleanLink(post.externalLink) }; notes.push(`${NAMES[p]}: posted`); }
      else if (post.status === 'error') { posted[p] = { ...s, state: 'failed', error: post.error?.message || 'Buffer could not post it' }; notes.push(`${NAMES[p]}: failed: ${posted[p].error}`); }
    }
    if (!notes.length) continue;
    const prev = it.status;
    it = await patch(it.id, { posted, status: statusFrom(posted, prev) });
    for (const n of notes) out.feedback.push(await log(it, n));
    if (it.status !== prev) out.feedback.push(await log(it, `${STATUS[prev]} → ${STATUS[it.status]}`));
    out.items.push(it);
  }
}

// Read-only: the same text twice on one channel, and everything still waiting. app-sync/dupcheck.py runs this daily.
async function duplicates() {
  const names = Object.fromEntries(Object.entries(CHANNELS).map(([k, c]) => [c.id, k]));
  const posts = await listPosts(Object.keys(names)), seen = {};
  for (const x of posts) (seen[`${x.channelId} ${KEY(x.text)}`] ||= []).push(x);
  const view = x => ({ platform: names[x.channelId], id: x.id, status: x.status, due: x.dueAt, sent: x.sentAt, url: cleanLink(x.externalLink), text: String(x.text || '').slice(0, 60) });
  return { checked: posts.length, duplicates: Object.values(seen).filter(v => v.length > 1).map(v => v.map(view)), waiting: posts.filter(x => x.status !== 'sent').map(view) };
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return send(res, 405, { error: 'POST only' });
  const out = { items: [], feedback: [] };
  try {
    const b = await readBody(req);
    if (b.op === 'status') return send(res, 200, { enabled: ENABLED, channels: Object.fromEntries(Object.entries(CHANNELS).map(([k, c]) => [k, c.name])) });
    if (b.op === 'prepare') { const it = await getItem(b.id); const f = await prepare(it); return send(res, 200, { ...f, url: (await sign([f.path], 3600))[f.path] }); }
    if (b.op === 'schedule') await schedule(b, out);
    else if (b.op === 'cancel') await cancel(b, out);
    else if (b.op === 'sync') await sync(out);
    else if (b.op === 'duplicates') return send(res, 200, await duplicates());
    else return send(res, 400, { error: 'unknown op' });
    send(res, 200, out);
  } catch (e) {
    send(res, e.code || 500, { error: String(e.message || e), ...out });
  }
}

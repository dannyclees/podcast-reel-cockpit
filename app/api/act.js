// POST /api/act: one change from the app. Every change is logged in shorts_feedback, so the version timeline can replay it.
import { rest, send, readBody } from './_sb.js';

const PLATFORMS = ['youtube', 'tiktok', 'instagram'];
const NAMES = { youtube: 'YouTube', tiktok: 'TikTok', instagram: 'Instagram' };
const STATUS = { draft: 'Draft', approved: 'Approved', scheduled: 'Scheduled', posted: 'Posted' };
const enc = encodeURIComponent;

async function getItem(id) {
  const [it] = await rest(`shorts_items?id=eq.${enc(id)}&select=*`);
  if (!it) throw new Error(`no short ${id}`);
  return it;
}
const patchItem = async (id, patch) =>
  (await rest(`shorts_items?id=eq.${enc(id)}`, { method: 'PATCH', body: { ...patch, updated_at: new Date().toISOString() }, prefer: 'return=representation' }))[0];
const log = async (row) => (await rest('shorts_feedback', { method: 'POST', body: row, prefer: 'return=representation' }))[0];
const stamp = (it, kind, body, author = 'owner') =>
  ({ episode_id: it.episode_id, short_id: it.id, kind, author, body, status_at: it.status, round_at: it.round, track_at: it.track });

// The overall status follows the platforms: any Posted -> posted, else any Scheduled -> scheduled, else draft/approved.
function statusFrom(posted, prev) {
  const states = PLATFORMS.map(p => posted[p]?.state);
  if (states.includes('posted')) return 'posted';
  if (states.includes('scheduled')) return 'scheduled';
  return prev === 'draft' ? 'draft' : 'approved';
}

// Feedback on one Short and version: saved as a note with state 'open' until someone marks it 'done'.
const FB_COLS = 'id,short_id,episode_id,round_at,status_at,body,state,created_at,done_at,done_note';

export default async function handler(req, res) {
  if (req.method === 'GET') {   // GET /api/act?op=feedback[&state=open|done|all]
    const q = new URL(req.url, 'http://x').searchParams;
    if (q.get('op') !== 'feedback') return send(res, 400, { error: 'unknown op' });
    const st = q.get('state') || 'open';
    const rows = await rest(`shorts_feedback?select=${FB_COLS}&kind=eq.note&${st === 'all' ? 'state=not.is.null' : `state=eq.${st === 'done' ? 'done' : 'open'}`}&order=created_at.asc&limit=500`);
    return send(res, 200, { feedback: rows });
  }
  if (req.method !== 'POST') return send(res, 405, { error: 'GET or POST' });
  try {
    const b = await readBody(req);
    const out = { item: null, episode: null, feedback: [] };

    if (b.op === 'note') {
      const body = String(b.body || '').trim().slice(0, 5000);
      if (!body) return send(res, 400, { error: 'empty note' });
      if (b.short_id) {
        out.item = await getItem(b.short_id);
        out.feedback.push(await log(stamp(out.item, 'note', body)));
      } else {
        out.feedback.push(await log({ episode_id: b.episode_id, short_id: null, kind: 'note', author: 'owner', body }));
      }
    } else if (b.op === 'trace') {
      // One play attempt, step by step, from the browser. Sent here (not /api/log) because ad blockers drop "log" paths.
      const row = { trace_id: String(b.id || '').slice(0, 20), ua: String(b.ua || req.headers['user-agent'] || '').slice(0, 300), build: String(b.build || '').slice(0, 80),
        layout: String(b.layout || '').slice(0, 4), age_min: Number.isFinite(b.age_min) ? Math.round(b.age_min) : null, events: Array.isArray(b.events) ? b.events.slice(0, 80) : [] };
      console.error('trace', JSON.stringify(row).slice(0, 3000));
      await rest('shorts_trace', { method: 'POST', body: row });
      return send(res, 200, { ok: true });
    } else if (b.op === 'feedback') {
      const body = String(b.body || '').trim().slice(0, 5000);
      if (!body) return send(res, 400, { error: 'empty feedback' });
      const it = await getItem(b.short_id);
      out.item = it;
      out.feedback.push(await log({ ...stamp(it, 'note', body), round_at: Number.isInteger(b.round) ? b.round : it.round, state: 'open' }));
    } else if (b.op === 'feedback_done') {
      const [f] = await rest(`shorts_feedback?id=eq.${enc(b.id)}`, { method: 'PATCH', body: { state: b.open ? 'open' : 'done', done_at: b.open ? null : new Date().toISOString(), done_note: b.open ? null : String(b.note || '').slice(0, 2000) || null }, prefer: 'return=representation' });
      if (!f) return send(res, 404, { error: 'no such feedback' });
      out.feedback.push(f);
    } else if (b.op === 'approve') {
      const it = await getItem(b.id);
      if (it.status === 'scheduled' || it.status === 'posted') return send(res, 409, { error: 'already scheduled or posted' });
      const status = b.on ? 'approved' : 'draft';
      out.item = it.status === status ? it : await patchItem(it.id, { status });
      if (it.status !== status) out.feedback.push(await log(stamp(out.item, 'status', `${STATUS[it.status]} → ${STATUS[status]}`)));
    } else if (b.op === 'track') {
      const it = await getItem(b.id);
      out.item = await patchItem(it.id, { track: String(b.track || 'none') });
    } else if (b.op === 'sfx') {
      const it = await getItem(b.id);
      out.item = await patchItem(it.id, { sfx: !!b.on });
    } else if (b.op === 'platform') {
      if (!PLATFORMS.includes(b.platform)) return send(res, 400, { error: 'bad platform' });
      if (!['none', 'scheduled', 'posted'].includes(b.state)) return send(res, 400, { error: 'bad state' });
      const it = await getItem(b.id);
      if (it.posted?.[b.platform]?.buffer_id && it.posted[b.platform].state === 'scheduled') return send(res, 409, { error: 'it is waiting in Buffer: use Cancel' });
      const posted = { ...(it.posted || {}) };
      const was = posted[b.platform]?.state || 'none';
      if (b.state === 'none') delete posted[b.platform];
      else posted[b.platform] = { state: b.state, at: was === b.state ? posted[b.platform].at : new Date().toISOString(), url: String(b.url ?? posted[b.platform]?.url ?? '').trim() };
      const status = statusFrom(posted, it.status);
      out.item = await patchItem(it.id, { posted, status });
      const word = { none: 'Not yet', scheduled: 'Scheduled', posted: 'Posted' };
      if (was !== b.state) out.feedback.push(await log(stamp(out.item, 'status', `${NAMES[b.platform]}: ${word[was]} → ${word[b.state]}`)));
      if (status !== it.status) out.feedback.push(await log(stamp(out.item, 'status', `${STATUS[it.status]} → ${STATUS[status]}`)));
    } else if (b.op === 'link') {
      if (!PLATFORMS.includes(b.platform)) return send(res, 400, { error: 'bad platform' });
      const it = await getItem(b.id);
      if (!it.posted?.[b.platform]) return send(res, 409, { error: 'schedule or post it first' });
      out.item = await patchItem(it.id, { posted: { ...it.posted, [b.platform]: { ...it.posted[b.platform], url: String(b.url || '').trim() } } });
    } else if (b.op === 'episode_link') {
      const url = String(b.url || '').trim();
      if (url && !/^https?:\/\//.test(url)) return send(res, 400, { error: 'link must start with https://' });
      out.episode = (await rest(`shorts_episodes?id=eq.${enc(b.episode_id)}`, { method: 'PATCH', body: { full_url: url || null, full_url_auto: false, full_title: null }, prefer: 'return=representation' }))[0];
    } else if (b.op === 'plan') {
      // Plans the posting times only. Nothing posts from it.
      const p = b.plan;
      if (p !== null) {
        const min = v => Number.isInteger(v) && v >= -720 && v <= 2880;
        if (!p || !/^\d{4}-\d{2}-\d{2}$/.test(p.day) || !min(p.start) || ![12, 16, 20, 24].includes(p.window_h)) return send(res, 400, { error: 'bad plan' });
        const ov = p.overrides || {};
        if (typeof ov !== 'object' || Object.values(ov).some(o => typeof o !== 'object' || Object.entries(o).some(([k, v]) => !PLATFORMS.includes(k) || !min(v)))) return send(res, 400, { error: 'bad nudges' });
      }
      out.episode = (await rest(`shorts_episodes?id=eq.${enc(b.episode_id)}`, { method: 'PATCH', body: { plan: p }, prefer: 'return=representation' }))[0];
    } else {
      return send(res, 400, { error: 'unknown op' });
    }
    send(res, 200, out);
  } catch (e) {
    send(res, 500, { error: String(e.message || e) });
  }
}

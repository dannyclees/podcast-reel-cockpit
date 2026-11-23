// Shorts review app: one timeline of posts (To review, then Scheduled and Live at the bottom); the selected Short opens on the right.
// Routes: #/ (desk)  #/s/<episode>/<short> (desk with that Short open)
// Names, tags, wording and the time zone come from window.BRAND (public/brand.js, generated at setup). Keys are listed in BRAND-TOKENS.md.
const CFG = window.BRAND || {};
const SHOW = CFG.show?.name || 'Shorts';
const APP_TITLE = CFG.app?.title || `${SHOW} Shorts`;
const APPROVER = CFG.app?.approver || 'Owner';
document.title = APP_TITLE;
const trackName = i => { const m = (CFG.music || [])[i - 1]; return (typeof m === 'string' ? m : m?.name) || `Track ${i}`; };
const TRACKS = [['none', 'No music', 'Off'], ['t1', trackName(1), '1'], ['t2', trackName(2), '2'], ['t3', trackName(3), '3']];
const TRACK_NAME = Object.fromEntries(TRACKS.map(([k, n]) => [k, n]));
const PLATFORMS = [['youtube', 'YouTube'], ['tiktok', 'TikTok'], ['instagram', 'Instagram']];
const PNAME = Object.fromEntries(PLATFORMS);
const STATUS = { draft: 'Draft', approved: 'Approved', scheduled: 'Scheduled', posted: 'Posted' };
const ALWAYS_TAGS = CFG.posting?.always_tags || [];
const LINK_GAP = '[full episode link]';
const TARGET = CFG.shorts_per_episode || 5;
const TZ = CFG.posting?.timezone || 'UTC';
const BUFFERED = ['youtube', 'instagram', 'tiktok'];   // all three post through Buffer
const SPEEDS = [1, 2, 3, 4];
let SPEED = (() => { try { return +localStorage.getItem('shorts-speed') || 3; } catch { return 3; } })();
let POSTING = { enabled: false, channels: {} };

let LOADED = 0, BUILD = null, NEWBUILD = false;   // BUILD: the deploy this page runs; a newer one reloads the page when nothing plays
let D = null;          // { episodes, items, versions, feedback }
let SEL = null;        // id of the Short open in the panel
let P = null;          // the one live player: { id, round, v, key, video }
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// ---------- data ----------
const items = ep => D.items.filter(i => i.episode_id === ep).sort((a, b) => (a.num ?? 99) - (b.num ?? 99));
const item = id => D.items.find(i => i.id === id);
const episode = id => D.episodes.find(e => e.id === id);
const versions = id => D.versions.filter(v => v.short_id === id).sort((a, b) => b.round - a.round);
const version = (id, r) => versions(id).find(v => v.round === r) || versions(id)[0] || {};
const current = it => version(it.id, it.round);
const notesFor = id => D.feedback.filter(f => f.short_id === id);
const epNotes = ep => D.feedback.filter(f => f.episode_id === ep && !f.short_id);
const pstate = (it, k) => {   // none | booking | scheduled | posted | failed
  const p = it.posted?.[k];
  if (p?.state === 'booking' && Date.now() - Date.parse(p.at) > 600000) return 'failed';   // the server crashed mid booking
  return p?.state || (p ? 'posted' : 'none');
};
const locked = it => it.status === 'scheduled' || it.status === 'posted';
// Sound effects: a version may carry sfx_none / sfx_t1 / sfx_t2 / sfx_t3 mixes next to the plain ones.
const hasSfx = v => Object.keys(v.track_urls || v.tracks || {}).some(k => k.startsWith('sfx_'));
const audioKey = (track, sfx, v) => (sfx && hasSfx(v) ? 'sfx_' : '') + track;

async function load() {
  const r = await fetch('/api/data', { cache: 'no-store' });
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || r.status);
  if (BUILD && j.build && j.build !== BUILD) NEWBUILD = true; BUILD = BUILD || j.build;
  D = j; LOADED = Date.now();
  let st = $('#bstamp'); if (!st) { st = document.createElement('div'); st.id = 'bstamp'; document.body.appendChild(st); }
  st.textContent = `build ${String(BUILD || 'local').replace(/^dpl_/, '').slice(0, 7)} · loaded ${new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}`;
  POSTING = await fetch('/api/post', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{"op":"status"}' })
    .then(r => r.ok ? r.json() : POSTING).catch(() => POSTING);
}

// Real posting goes through /api/post (Buffer). Same merge as act(), with the error shown when it fails.
async function postOp(body, ok) {
  const r = await fetch('/api/post', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({ error: String(r.status) }));
  for (const it of j.items || []) D.items = D.items.map(i => i.id === it.id ? it : i);
  if (j.feedback?.length) D.feedback = [...j.feedback, ...D.feedback];
  (j.items || []).forEach(it => refresh(it.id));
  if (!r.ok) { toast(j.error || 'Not done', true); throw new Error(j.error); }
  if (ok) toast(ok);
  return j;
}
const waitingInBuffer = () => D.items.some(it => Object.values(it.posted || {}).some(p => p?.buffer_id && p.state === 'scheduled'));
async function syncBuffer() { if (D && waitingInBuffer()) await postOp({ op: 'sync' }).catch(() => {}); }
setInterval(syncBuffer, 5 * 60000);


async function act(body, ok = 'Saved') {
  try {
    const r = await fetch('/api/act', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || r.status);
    if (j.item) D.items = D.items.map(i => i.id === j.item.id ? j.item : i);
    if (j.episode) D.episodes = D.episodes.map(e => e.id === j.episode.id ? j.episode : e);
    if (j.feedback?.length) D.feedback = [...j.feedback, ...D.feedback.filter(f => !j.feedback.some(n => n.id === f.id))];
    toast(ok);
    return j;
  } catch (e) {
    toast('Not saved: ' + e.message, true);
    throw e;
  }
}

// ---------- format ----------
const todayKey = () => new Date().toLocaleDateString('en-CA', { timeZone: TZ });
const addDays = (key, n) => { const d = new Date(key + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
const fmtDay = d => new Date(d + 'T12:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'long', timeZone: 'UTC' });
const fmtShort = d => new Date(d + 'T12:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });
const fmtWeekday = d => new Date(d + 'T12:00:00Z').toLocaleDateString('en-GB', { weekday: 'long', timeZone: 'UTC' });
const fmtTime = t => new Date(t).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: TZ });
const LTZ = Intl.DateTimeFormat().resolvedOptions().timeZone;
const tzName = (() => { try { return new Intl.DateTimeFormat('en-GB', { timeZone: LTZ, timeZoneName: 'short' }).formatToParts(new Date()).find(x => x.type === 'timeZoneName')?.value || ''; } catch { return ''; } })();
const fmtLocal = t => new Date(t).toLocaleString('en-GB', { timeZone: LTZ, weekday: 'short', hour: '2-digit', minute: '2-digit' }).replace(',', '');
// A plan slot (show-time-zone day + minutes, as the server reads it) as a real instant.
function planAt(day, min) {
  const [y, m, d] = day.split('-').map(Number), wall = Date.UTC(y, m - 1, d) + min * 60000;
  const off = t => { const p = Object.fromEntries(new Intl.DateTimeFormat('en-GB', { timeZone: TZ, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).formatToParts(new Date(t)).map(x => [x.type, x.value]));
    return Date.UTC(+p.year, p.month - 1, +p.day, +p.hour, +p.minute) - t; };
  return new Date(wall - off(wall - off(wall))).toISOString();
}
const fromNow = t => { const m = Math.round((new Date(t) - Date.now()) / 60000); if (m < 1) return 'now'; if (m < 60) return `in ${m} min`; const h = Math.floor(m / 60); return `in ${h} h${m % 60 ? ` ${m % 60} min` : ''}`; };
const dayKey = t => new Date(t).toLocaleDateString('en-CA', { timeZone: TZ });
const fmtWhen = t => {
  const k = dayKey(t), today = todayKey();
  const lbl = k === today ? 'Today' : k === addDays(today, -1) ? 'Yesterday' : fmtShort(k);
  return `${lbl}, ${fmtTime(t)}`;
};
const secs = s => s ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}` : '';

let toastT;
function toast(msg, bad = false) {
  const t = $('#toast'); t.textContent = msg; t.className = 'on' + (bad ? ' bad' : '');
  clearTimeout(toastT); toastT = setTimeout(() => t.className = '', bad ? 4200 : 1600);
}

// ---------- marks ----------
let uid = 0;
function logo(k, on) {
  const d = LOGO_D[k];
  if (!on) return `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${d}" style="fill:var(--line-2)"/></svg>`;
  if (k === 'youtube') return `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="8" width="10" height="8" fill="#fff"/><path d="${d}" fill="#FF0033"/></svg>`;
  if (k === 'tiktok') return `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${d}" fill="#25F4EE" transform="translate(-.7 -.5)"/><path d="${d}" fill="#FE2C55" transform="translate(.7 .5)"/><path d="${d}" style="fill:var(--ink)"/></svg>`;
  const g = 'ig' + (++uid);
  return `<svg viewBox="0 0 24 24" aria-hidden="true"><defs><radialGradient id="${g}" cx="30%" cy="107%" r="150%"><stop offset="0" stop-color="#FDF497"/><stop offset=".05" stop-color="#FDF497"/><stop offset=".45" stop-color="#FD5949"/><stop offset=".6" stop-color="#D6249F"/><stop offset=".9" stop-color="#285AEB"/></radialGradient></defs><path d="${d}" fill="url(#${g})"/></svg>`;
}
const TICK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.2 4.2L19 7" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const CLOCK = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="2.6"/><path d="M12 7.5V12l3 2" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg>';
const PLAY = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l11-6.5z" fill="currentColor"/></svg>';
const PAUSE = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6.5" y="5" width="4" height="14" rx="1.2" fill="currentColor"/><rect x="13.5" y="5" width="4" height="14" rx="1.2" fill="currentColor"/></svg>';
const NOTE = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 18V6l10-2v12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="6.5" cy="18" r="2.5" fill="currentColor"/><circle cx="16.5" cy="16" r="2.5" fill="currentColor"/></svg>';

// The liquid switch, as plain HTML.
function liquid(on, disabled, label, small = false) {
  const f = 'lq' + (++uid);
  return `<span class="liquid${small ? ' sm' : ''}" ${disabled ? 'data-disabled' : ''}><input type="checkbox" role="switch" aria-label="${esc(label)}" ${on ? 'checked' : ''} ${disabled ? 'disabled' : ''}>
    <svg viewBox="0 0 52 32" aria-hidden="true"><defs><filter id="${f}" x="-30%" y="-50%" width="160%" height="200%"><feGaussianBlur in="SourceGraphic" stdDeviation="2" result="blur"/><feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 18 -7" result="goo"/><feComposite in="SourceGraphic" in2="goo" operator="atop"/></filter></defs>
    <g filter="url(#${f})"><circle class="k1" cx="16" cy="16" r="10"/><circle class="k2" cx="36" cy="16" r="10"/></g></svg></span>`;
}

// One status pill per Short. From Approved on, the three platforms live inside it.
function marks(it) {
  return PLATFORMS.map(([k, n]) => {
    const s = pstate(it, k);
    return `<span class="mk ${s}" title="${n}: ${s === 'none' ? 'not yet' : s}">${logo(k, s !== 'none')}${s === 'posted' ? `<i class="ok">${TICK}</i>` : s === 'scheduled' ? `<i class="sch">${CLOCK}</i>` : ''}</span>`;
  }).join('');
}
const statusPill = it => `<span class="pill ${it.status}">${STATUS[it.status]}</span>`;
// Grey = not yet, clock + time = scheduled, green tick = posted (links to the post), red ! = failed (hover for why).
function platMarks(it) {
  return PLATFORMS.map(([k, n]) => {
    const s = pstate(it, k), p = it.posted?.[k] || {};
    const txt = s === 'scheduled' ? (p.due ? fmtTime(p.due) : 'Set') : s === 'posted' ? 'Live' : s === 'failed' ? 'Failed' : '';
    const tip = s === 'failed' ? `${n}: ${p.error || 'failed'}` : s === 'posted' ? `${n}: posted${p.url ? ', open it' : ''}` : s === 'scheduled' ? `${n}: scheduled${p.due ? ' ' + fmtWhen(p.due) : ''}` : `${n}: not yet`;
    const badge = s === 'posted' ? `<i class="ok">${TICK}</i>` : s === 'scheduled' ? `<i class="sch">${CLOCK}</i>` : s === 'failed' ? '<i class="bad">!</i>' : '';
    const inner = `<span class="lg">${logo(k, s !== 'none')}${badge}</span>${txt ? `<em>${txt}</em>` : ''}`;
    return s === 'posted' && p.url ? `<a class="pmk ${s}" href="${esc(p.url)}" target="_blank" rel="noopener" title="${esc(tip)}">${inner}</a>` : `<span class="pmk ${s}" title="${esc(tip)}">${inner}</span>`;
  }).join('');
}

// ---------- post copy: one caption for every platform (YouTube also gets a title), ending with the full-episode link ----------
const CTA = CFG.posting?.cta_line || 'Watch the full episode:';
const needsLink = it => !episode(it.episode_id)?.full_url;
function postCopy(it) {
  const c = it.copy || {}, url = episode(it.episode_id)?.full_url || '';
  const tags = [...ALWAYS_TAGS, ...(c.hashtags || []).filter(t => !ALWAYS_TAGS.some(a => a.toLowerCase() === t.toLowerCase()))].join(' ');
  const base = String(c.caption || c.instagram_caption || c.tiktok_caption || c.youtube_description || '')
    .replace(/(^|\s)#\w+/g, '$1')
    .replace(/^.*(\{FULL_EPISODE_LINK\}|link in bio).*$/gim, '')   // the call to action below replaces these lines
    .replace(/[ \t]+$/gm, '').replace(/\n{3,}/g, '\n\n').trim();
  return { title: c.youtube_title || it.title || '', caption: base ? `${base}\n\n${url ? `${CTA} ${url}\n\n` : ''}${tags}` : '' };
}
const buildCopy = it => { const { title, caption } = postCopy(it); return { youtube: { title, text: caption }, instagram: { text: caption }, tiktok: { text: caption } }; };

// ---------- quick actions ----------
async function setApprove(id, on) {
  await act({ op: 'approve', id, on }, on ? 'Approved' : 'Back to draft').catch(() => {});
  refresh(id);
}
async function setPlatform(id, k, state) {
  const word = { none: 'Not yet', scheduled: 'Scheduled', posted: 'Posted' }[state];
  await act({ op: 'platform', id, platform: k, state }, `${PNAME[k]}: ${word}`).catch(() => {});
  refresh(id);
}
async function chooseTrack(id, k) {
  if (P && P.id === id) applyAudio();
  if (k !== item(id).track) {
    D.items = D.items.map(i => i.id === id ? { ...i, track: k } : i);   // instant, then saved
    if (P && P.id === id) applyAudio();
    await act({ op: 'track', id, track: k }, `Music: ${TRACK_NAME[k]}`).catch(() => {});
  }
  refresh(id);
}
async function chooseSfx(id, on) {
  if (BUFFERED.some(k => pstate(item(id), k) === 'scheduled')) toast('The booked post keeps its sound. Cancel and book again to change it.');
  D.items = D.items.map(i => i.id === id ? { ...i, sfx: on } : i);
  if (P && P.id === id) applyAudio();
  await act({ op: 'sfx', id, on }, on ? 'Sound effects on' : 'Sound effects off').catch(() => {});
  refresh(id);
}

function linkEditor(ep, onSaved) {
  const el = document.createElement('div');
  el.className = 'linkbox';
  el.innerHTML = `<input type="url" placeholder="https://youtube.com/watch?v=…" value="${esc(ep.full_url || '')}" aria-label="Full episode link"><button class="btn ink sm">Save</button>`;
  const inp = $('input', el), b = $('button', el);
  const save = async () => { b.disabled = true; try { await act({ op: 'episode_link', episode_id: ep.id, url: inp.value.trim() }, 'Episode link saved'); onSaved?.(); } catch {} b.disabled = false; };
  b.onclick = save; inp.onkeydown = e => { if (e.key === 'Enter') save(); };
  return el;
}

// ---------- inline player: one <video> whose file already holds the chosen mix, so sound and picture cannot drift ----------
// The video plus mix file is made by /api/play on first use and kept; a muted video beside a separate mix drifted up to 3 s at 3x.
function stopPlayer() {
  if (!P) return;
  const card = P.video.closest('.pframe');
  P.video.pause(); P.video.removeAttribute('src'); P.video.load(); P.video.remove(); P = null;   // stop its download too
  if (card) { card.classList.remove('playing', 'paused', 'loading'); $('.prog i', card).style.width = '0'; $('.playbtn', card).innerHTML = PLAY; $('.retry', card)?.remove(); }
}

// Which sound: the chosen bed, with or without sound effects. "No music" without SFX = the video's own sound.
function soundKey(it, v) { const k = audioKey(it.track || 'none', it.sfx !== false, v); return v.tracks?.[k] || v.track_urls?.[k] ? k : 'none'; }
const playUrl = (v, key) => key === 'none' ? v.video : v.play_urls?.[key] || null;
const PLAYQ = new Map();   // "id|round|key" -> promise of the url
function ensurePlay(id, round, key) {
  const v = version(id, round); if (playUrl(v, key)) return Promise.resolve(playUrl(v, key));
  const k = `${id}|${round}|${key}`;
  if (!PLAYQ.has(k)) PLAYQ.set(k, fetch('/api/play', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id, round, key }) })
    .then(r => r.json().then(j => { if (!r.ok) throw new Error(j.error || r.status); return j; }))
    .then(j => { const vv = version(id, round); vv.play_urls = { ...(vv.play_urls || {}), [key]: j.url }; return j.url; })
    .finally(() => PLAYQ.delete(k)));
  return PLAYQ.get(k);
}
// After load, make the current file for each Short one at a time (newest episode first), so a click plays at once.
async function prefetchPlays() {
  const order = D.items.slice().sort((a, b) => (episode(b.episode_id)?.recorded_on || '').localeCompare(episode(a.episode_id)?.recorded_on || ''));
  for (const it of order) { const v = current(it); await ensurePlay(it.id, v.round, soundKey(it, v)).catch(() => {}); }
}

// Hovering starts loading the file, so a click plays at once.
let WARM = null;
function warm(id, round) {
  const it = item(id), v = version(id, round ?? it.round), key = soundKey(it, v);
  if (P?.id === id || (WARM?.id === id && WARM.round === v.round && WARM.key === key)) return;
  const url = playUrl(v, key);
  if (!url) { ensurePlay(id, v.round, key).catch(() => {}); return; }
  if (WARM) { WARM.video.removeAttribute('src'); WARM.video.load(); }   // free the connection
  const video = document.createElement('video');
  video.playsInline = true; video.preload = 'auto'; video.src = url; video.poster = v.poster || '';
  WARM = { id, round: v.round, key, video };
}

// Play trace: every attempt, step by step, so the logs show exactly where it stops in a real browser.
const TR = { id: null, t0: 0, ev: [], timer: null };
const vstate = v => v ? { rs: v.readyState, ns: v.networkState, t: +v.currentTime.toFixed(2), paused: v.paused, muted: v.muted, err: v.error?.code || null } : null;
function traceStart(what, extra) { flushTrace(); TR.id = Math.random().toString(36).slice(2, 8); TR.t0 = performance.now(); TR.ev = []; trace(what, extra); }
function trace(ev, extra = {}) {
  if (!TR.id) { TR.id = Math.random().toString(36).slice(2, 8); TR.t0 = performance.now(); }
  TR.ev.push({ ev, ms: Math.round(performance.now() - TR.t0), ...extra });
  clearTimeout(TR.timer); TR.timer = setTimeout(flushTrace, TR.ev.length > 40 ? 0 : 2000);
}
function flushTrace() {
  clearTimeout(TR.timer); if (!TR.ev.length) return;
  const body = { op: 'trace', id: TR.id, build: BUILD, layout: LAYOUT, ua: navigator.userAgent, age_min: (Date.now() - LOADED) / 60000, events: TR.ev };
  TR.ev = [];
  fetch('/api/act', { method: 'POST', keepalive: true, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }).catch(() => {});
}
addEventListener('pagehide', flushTrace);
// Log the click itself (capture phase), before any handler can stop it.
document.addEventListener('click', e => {
  const el = e.target.closest('.pframe, .th, .retry');
  if (!el) return;
  traceStart('click', { on: `${e.target.tagName.toLowerCase()}.${String(e.target.className?.baseVal ?? e.target.className).split(' ')[0]}`, in: el.className.split(' ')[0], where: el.closest('#panel') ? 'panel' : el.closest('#modal') ? 'modal' : el.closest('.card') ? 'card' : el.closest('.tr') ? 'row' : '?', id: el.closest('[data-id]')?.dataset.id });
}, true);

function report(what, extra = {}) {
  trace('report:' + what, extra);
  const v = P?.video;
  const info = { what, ...extra, ua: navigator.userAgent.slice(0, 120), build: BUILD, age_min: Math.round((Date.now() - LOADED) / 60000),
    video: v ? { rs: v.readyState, ns: v.networkState, err: v.error?.code, msg: v.error?.message, muted: v.muted, src: (v.currentSrc || v.src || '').split('?')[0].slice(-60) } : null };
  fetch('/api/log', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(info) }).catch(() => {});
}
// A click while the first file still loads must not pause it (a second click at the 'Not playing' note
// used to pause the video, so nothing ever played).
function togglePlay(frame) { if (!P.played && frame.classList.contains('loading')) return; P.video.paused ? P.video.play().catch(() => {}) : P.video.pause(); }
function startPlayer(id, round, card = $(`.pframe[data-id="${CSS.escape(id)}"]`), healed = false) {
  const it = item(id);
  if (!card) return;
  stopPlayer();
  const v = version(id, round ?? it.round), key = soundKey(it, v);
  const w = WARM?.id === id && WARM.round === v.round && WARM.key === key ? WARM : null; WARM = null;
  const video = w?.video || document.createElement('video');
  video.playsInline = true; video.preload = 'auto'; video.muted = false; video.defaultPlaybackRate = video.playbackRate = SPEED;
  card.insertBefore(video, card.firstChild);
  const me = { id, round: v.round, v, key, video };
  P = me;
  trace('startPlayer', { id, round: v.round, key, healed, warm: !!w, ready: !!playUrl(v, key), link_age_min: Math.round((Date.now() - LOADED) / 60000), v0: vstate(video) });
  for (const ev of ['loadstart', 'loadedmetadata', 'canplay', 'playing', 'waiting', 'stalled', 'error', 'abort'])
    video.addEventListener(ev, () => { if (P === me) trace('v:' + ev, vstate(video)); });
  setTimeout(() => { if (P === me) trace('after 5s', vstate(video)); }, 5000);
  const bar = $('.prog i', card), btn = $('.playbtn', card);
  video.addEventListener('play', () => { card.classList.add('playing'); card.classList.remove('paused'); btn.innerHTML = PAUSE; });
  video.addEventListener('playing', () => { me.played = true; card.classList.remove('loading'); $('.retry', card)?.remove(); });
  video.addEventListener('pause', () => { card.classList.add('paused'); btn.innerHTML = PLAY; });
  video.addEventListener('ended', () => { card.classList.add('paused'); btn.innerHTML = PLAY; });
  video.addEventListener('timeupdate', () => { bar.style.width = (100 * video.currentTime / (video.duration || 1)) + '%'; });
  video.addEventListener('error', async () => {   // most often a link that has expired: get fresh links and try once more
    if (P !== me || me.swapping) return;
    report('video error', { healed });
    if (healed) { stopPlayer(); toast(`This video would not load (error ${video.error?.code || '?'}). Reload the page.`, true); return; }
    card.classList.add('loading'); await freshen(true);
    if (P === me && card.isConnected) startPlayer(id, round, card, true);
  });
  $('.prog', card).onclick = e => { e.stopPropagation(); const r = e.currentTarget.getBoundingClientRect(); video.currentTime = (e.clientX - r.left) / r.width * (video.duration || 0); };
  card.classList.add('playing', 'loading');
  // No 'playing' after 4 s: say so on the frame, with a retry.
  setTimeout(() => {
    if (P !== me || me.played) return;
    trace('retry shown', vstate(video));
    $('.retry', card)?.remove();
    const r = document.createElement('button'); r.className = 'retry'; r.textContent = 'Not playing. Tap to retry';
    r.onclick = async e => { e.stopPropagation(); r.remove(); await freshen(true); startPlayer(id, round, card, false); };
    card.appendChild(r);
  }, playUrl(v, key) ? 4000 : 12000);   // a mix still being made takes ~6 s: do not cry wolf at 4 s
  const go = () => video.play().then(() => trace('play() ok', vstate(video))).catch(e => {
    trace('play() rejected', { name: e.name, msg: String(e.message).slice(0, 160) });
    if (P !== me || e.name === 'AbortError') return;
    card.classList.add('paused'); card.classList.remove('loading');
    report('play() rejected', { name: e.name, message: String(e.message).slice(0, 200) });
    toast(e.name === 'NotAllowedError' ? 'Click play again to start with sound.' : `Could not start the video: ${e.name}. Click play again.`, e.name !== 'NotAllowedError');
  });
  const url = playUrl(v, key);
  if (url) { if (!w) { video.src = url; video.poster = v.poster || ''; } return go(); }   // start inside the click
  // First play of this mix: the file is being made (a few seconds), then it plays.
  ensurePlay(id, v.round, key).then(u => { if (P !== me) return; video.src = u; go(); })
    .catch(e => { if (P !== me) return; stopPlayer(); toast('Could not prepare this video: ' + e.message, true); });
}

function setSpeed(x) {
  SPEED = x; try { localStorage.setItem('shorts-speed', String(x)); } catch {}
  if (P) P.video.playbackRate = x;
  paintSpeed();
}
function paintSpeed() {
  $$('.spd').forEach(b => b.textContent = `Speed ${SPEED}×`);
}

// Music or SFX changed while playing: load the other file at the same time and keep going.
async function applyAudio() {
  if (!P) return;
  const me = P, it = item(me.id), key = soundKey(it, me.v);
  if (key === me.key) return;
  me.key = key;
  const card = me.video.closest('.pframe'); card?.classList.add('loading');
  let url; try { url = await ensurePlay(me.id, me.round, key); } catch (e) { card?.classList.remove('loading'); toast('Could not switch the sound: ' + e.message, true); return; }
  if (P !== me || me.key !== key) return;
  const t = me.video.currentTime, playing = !me.video.paused, v = me.video;
  me.swapping = true;
  v.src = url;
  v.addEventListener('loadedmetadata', () => {
    v.currentTime = t; v.playbackRate = SPEED; me.swapping = false; card?.classList.remove('loading');
    trace('sound swapped', { key, t: +t.toFixed(2) });
    if (playing) v.play().catch(() => {});
  }, { once: true });
}

function playToggle(id) {
  if (P && P.id === id) { P.video.paused ? P.video.play() : P.video.pause(); return; }
  openPanel(id); startPlayer(id, VSEL, $(`${usesPanel() ? '#panel' : '#modal'} .pframe`));
}

// ---------- notes ----------
function entryHTML(f) {
  const who = f.author === 'team' ? 'Team' : APPROVER;
  if (f.kind === 'status') return `<div class="entry status"><span>${esc(f.body)}</span><time>${fmtWhen(f.created_at)}</time></div>`;
  return `<div class="entry ${f.kind}"><div class="head"><b>${who}</b><time>${fmtWhen(f.created_at)}</time>${f.status_at ? `<span class="pill sm ${f.status_at}"><span class="lbl">${STATUS[f.status_at] || f.status_at}</span></span>` : ''}</div><div class="text">${esc(f.body)}</div></div>`;
}

function composer(placeholder, onSend) {
  const el = document.createElement('div');
  el.className = 'composer';
  el.innerHTML = `<textarea placeholder="${esc(placeholder)}" aria-label="${esc(placeholder)}" rows="3"></textarea><div class="row"><span></span><button class="btn ink sm" disabled>Send note</button></div>`;
  const ta = $('textarea', el), b = $('button', el);
  ta.addEventListener('input', () => b.disabled = !ta.value.trim());
  ta.addEventListener('keydown', e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && ta.value.trim()) b.click(); });
  b.onclick = async () => { b.disabled = true; try { await onSend(ta.value.trim()); ta.value = ''; } catch { b.disabled = false; } };
  return el;
}

// ---------- the page: one timeline of posts (Live, Up next, To review) and one calm panel ----------
let VSEL = null;       // the version shown in the panel (round)
let MENU = null;       // the open chooser (speed or music)

const stateOf = it => it.status === 'posted' && PLATFORMS.some(([k]) => pstate(it, k) === 'scheduled') ? 'scheduled' : it.status;
const nextDue = it => BUFFERED.map(k => it.posted?.[k]).filter(p => p?.state === 'scheduled' && p.due).map(p => p.due).sort()[0] || null;
const liveAt = it => Math.max(0, ...Object.values(it.posted || {}).filter(p => p?.state === 'posted').map(p => +new Date(p.at || 0)));
const verLabel = v => (v.round_label || '').split('·')[0].trim() || `V${v.round}`;
const vTab = v => { const m = verLabel(v).match(/\b([A-Z])$/); return `V${v.round}${m ? ' ' + m[1] : ''}`; };
const thumbOf = it => current(it).poster || '';

// "00:00 tonight", "12:00 tomorrow", "15:00 Sun" in the viewer's own time
function whenWords(iso) {
  const t = new Date(iso), k = d => d.toLocaleDateString('en-CA', { timeZone: LTZ });
  const today = k(new Date()), tom = k(new Date(Date.now() + 864e5)), day = k(t);
  const hh = t.toLocaleTimeString('en-GB', { timeZone: LTZ, hour: '2-digit', minute: '2-digit' });
  const h = +hh.slice(0, 2);
  const word = day === today ? (h >= 18 ? 'tonight' : 'today') : day === tom ? (h < 5 ? 'tonight' : 'tomorrow') : t.toLocaleDateString('en-GB', { timeZone: LTZ, weekday: 'short' });
  return { time: hh, word };
}
const dayWords = iso => new Date(iso).toLocaleDateString('en-GB', { timeZone: LTZ, weekday: 'long', day: 'numeric', month: 'short' });

// The next free slot: 4 h after the last booked post, never sooner than 20 minutes from now.
function nextSlot() {
  const booked = D.items.flatMap(it => BUFFERED.map(k => it.posted?.[k]).filter(p => p?.state === 'scheduled' && p.due).map(p => +new Date(p.due)));
  const soon = Date.now() + 20 * 60000;
  const t = Math.max(booked.length ? Math.max(...booked) + 4 * 3600e3 : soon, soon);
  return new Date(Math.ceil(t / 900000) * 900000).toISOString();
}

// ---------- actions: one per step ----------
// What is running for a Short right now. The row stays where it is and shows it, then moves when the work is done.
const BUSY = new Map();
const setBusy = (id, label) => { const was = BUSY.get(id); BUSY.set(id, { label, tab: was ? was.tab : tabOf(item(id)) }); paintBusy(id); };
function paintBusy(id) { paintTabs(); $$(`[data-id="${CSS.escape(id)}"]:not(.pframe)`).forEach(el => el.classList.toggle('busy', BUSY.has(id))); if (SEL === id) paintPanelState(); const c = $(`.card[data-id="${CSS.escape(id)}"]`); if (c) paintCardInfo(id); $$(`.tr[data-id="${CSS.escape(id)}"] .acts, .ag[data-id="${CSS.escape(id)}"] .acts`).forEach(x => { x.innerHTML = `${sfxBtn(item(id))}${stepMini(item(id), item(id).round)}`; wireSteps(x, id, item(id).round); wireSfx(x, id); }); }
// The row folds away when the Short has left this tab, and the tab it went to gives a small bump.
async function clearBusy(id) {
  const from = BUSY.get(id)?.tab; BUSY.delete(id);
  const to = tabOf(item(id));
  if (from && to !== from && TAB === from && !playingInFeed()) {
    const el = $(`#feed [data-id="${CSS.escape(id)}"]:not(.pframe)`);
    if (el) { el.classList.remove('busy'); el.classList.add('leaving'); await new Promise(r => setTimeout(r, 340)); }
    BUMP = to;
  }
  refresh(id);
}
async function approveAndSchedule(id, round, at = nextSlot()) {
  if (BUSY.has(id)) return;   // a second click while this Short is working does nothing
  setBusy(id, 'Approving');
  try {
    let it = item(id);
    if (it.status === 'draft') { try { await act({ op: 'approve', id, on: true }, 'Approved'); } catch { return; } it = item(id); }
    if (!POSTING.enabled) return;
    const platforms = BUFFERED.filter(k => ['none', 'failed'].includes(pstate(it, k)));
    setBusy(id, `Scheduling for ${whenWords(at).time} ${whenWords(at).word}`);
    const j = await postOp({ op: 'schedule', id, round, platforms, due: Object.fromEntries(platforms.map(k => [k, { iso: at }])), copy: buildCopy(it) }).catch(() => null);
    if (j) { const w = whenWords(j.items?.find(x => x.id === id)?.posted?.[platforms[0]]?.due || at); toast(`Scheduled for ${w.time} ${w.word}`); }   // the server moves it if another Short holds that time
  } finally { await clearBusy(id); }
}
async function postNow(id, round) {
  if (BUSY.has(id)) return;
  const it = item(id), platforms = BUFFERED.filter(k => pstate(it, k) !== 'posted');
  setBusy(id, 'Sending to Buffer');
  try { await postOp({ op: 'schedule', id, round, now: true, platforms, copy: buildCopy(it) }, 'Posting now').catch(() => {}); }
  finally { await clearBusy(id); }
}
async function cancelPosts(id) {
  setBusy(id, 'Cancelling');
  try { for (const k of BUFFERED) if (pstate(item(id), k) === 'scheduled' || pstate(item(id), k) === 'failed') await postOp({ op: 'cancel', id, platform: k }).catch(() => {}); toast('Cancelled'); }
  finally { await clearBusy(id); }
}
async function reschedule(id, round, at) {
  if (BUFFERED.some(k => pstate(item(id), k) === 'scheduled')) await cancelPosts(id);
  await approveAndSchedule(id, round, at);
}

function wireSteps(root, id, round) {
  $$('[data-do]', root).forEach(b => b.onclick = async e => {
    e.stopPropagation(); b.disabled = true;
    if (b.dataset.do === 'approve') await approveAndSchedule(id, round);
    else if (b.dataset.do === 'now') await postNow(id, round);
    else if (b.dataset.do === 'cancel') await cancelPosts(id);
  });
}
const platIcons = it => PLATFORMS.map(([k, n]) => {
  const s = pstate(it, k), u = it.posted?.[k]?.url;
  const inner = `${logo(k, s !== 'none')}${s === 'posted' ? `<i class="ok">${TICK}</i>` : s === 'failed' ? '<i class="bad">!</i>' : ''}`;
  return u && s === 'posted' ? `<a class="pi ${s}" href="${esc(u)}" target="_blank" rel="noopener" title="Open on ${n}">${inner}</a>` : `<span class="pi ${s}" title="${n}: ${s === 'none' ? 'not booked' : s === 'failed' ? esc(it.posted[k].error || 'failed') : s}">${inner}</span>`;
}).join('');

// ---------- layouts: A = rows + side panel (default), B = big 9:16 cards + centred view, C = cards + side panel ----------
// Switch in the bar under the masthead, or ?layout=a|b|c in the URL. The choice is remembered on this browser.
const LAYOUTS = [['a', 'Rows + panel'], ['b', 'Big cards'], ['c', 'Cards + panel']];
let LAYOUT = (() => {
  const ok = k => LAYOUTS.some(([x]) => x === k), q = new URLSearchParams(location.search).get('layout');
  if (ok(q)) { try { localStorage.setItem('shorts-layout', q); } catch {} return q; }
  try { const s = localStorage.getItem('shorts-layout'); if (ok(s)) return s; } catch {}
  return 'a';
})();
const usesPanel = () => LAYOUT !== 'b';
// One tab per stage, so a Short leaves Drafts when it is booked and leaves it when it has feedback.
const TABS = [['draft', 'Drafts'], ['next', 'Scheduled'], ['live', 'Live'], ['rev', 'Revisions']];
let TAB = (() => { try { const v = localStorage.getItem('posts-tab'); return TABS.some(([k]) => k === v) ? v : 'draft'; } catch { return 'draft'; } })();
let BUMP = null;
const tabOf = it => {
  if (BUSY.has(it.id)) return BUSY.get(it.id).tab;
  const k = kindOf(it);
  if (k === 'live') return 'live';
  if (k === 'next') return 'next';
  if (openNotes(it.id).length) return 'rev';
  return k === 'wait' ? 'next' : 'draft';
};
// Revisions holds every Short with an open note, also one that is booked or live (it shows there as well, with a warning).
const inTab = (it, t) => t === 'rev' ? openNotes(it.id).length > 0 : tabOf(it) === t;
const tabCount = t => D.items.filter(it => inTab(it, t)).length;
function paintTabs() {
  const box = $('#ptabs'); if (!box) return;
  const going = BUSY.size > 0;
  box.innerHTML = TABS.map(([k, n]) => `<button role="tab" aria-selected="${k === TAB}" data-t="${k}" class="t-${k}${BUMP === k ? ' bump' : ''}"><span>${n}</span><b>${tabCount(k)}</b>${k === 'next' && going ? '<i class="tspin" aria-hidden="true"></i>' : ''}</button>`).join('');
  BUMP = null;
  $$('button', box).forEach(b => b.onclick = () => { if (b.dataset.t === TAB) return; if (playingInFeed()) stopPlayer(); TAB = b.dataset.t; try { localStorage.setItem('posts-tab', TAB); } catch {} paintTimeline(); });
}
function setLayout(k) {
  LAYOUT = k; try { localStorage.setItem('shorts-layout', k); } catch {}
  const u = new URL(location.href); u.searchParams.set('layout', k); history.replaceState(null, '', u);
  stopPlayer(); desk($('#app'), SEL);
}
const CSEL = {};          // the version each card shows (round); default is the current one
const cardRound = it => CSEL[it.id] ?? it.round;
let DIRTY = false;        // a full repaint waits while a card plays inline
const playingInFeed = () => !!P?.video.closest('#feed');

function desk(app, openId) {
  app.innerHTML = `${mast('posts')}
    <div class="tbar"><div class="lsw" role="group" aria-label="Layout"><span>Layout</span>${LAYOUTS.map(([k, n]) => `<button data-l="${k}" class="${k === LAYOUT ? 'on' : ''}" title="${n}"><b>${k.toUpperCase()}</b><i>${n}</i></button>`).join('')}</div></div>
    ${usesPanel() ? `<div class="desk open lay-${LAYOUT}" id="desk"><div class="feedcol"><div class="ptabs" id="ptabs" role="tablist" aria-label="Stage"></div><div class="${LAYOUT === 'a' ? 'tl' : 'board'}" id="feed"></div></div><aside class="panel" id="panel" aria-label="Selected Short"></aside></div>`
      : `<div class="nxs" id="nxs"></div><div class="ptabs" id="ptabs" role="tablist" aria-label="Stage"></div><div class="board lay-b" id="feed"></div><div class="modal" id="modal" hidden></div>`}`;
  $$('.lsw button', app).forEach(b => b.onclick = () => b.dataset.l !== LAYOUT && setLayout(b.dataset.l));
  if (openId && item(openId)) TAB = tabOf(item(openId));
  paintTimeline(); paintNext();
  openPanel(openId && item(openId) ? openId : null, { force: true });
}

const kindOf = it => nextDue(it) ? 'next' : liveAt(it) ? 'live' : it.status === 'approved' ? 'wait' : it.status === 'draft' ? 'review' : 'live';
const epLabel = ep => `${fmtWeekday(ep?.recorded_on)} ${fmtDay(ep?.recorded_on)} episode`;

// Each episode is one calm container: a small header row, then its Shorts split by hairlines.
function epHead(e, n) {
  const ep = episode(e), d = ep?.recorded_on ? new Date(ep.recorded_on + 'T12:00:00Z') : null;
  return `<header class="eph"><span class="epd">${d ? d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' }) : ''}</span>
    <b>${esc(ep?.full_title || SHOW)}</b><span class="epn">${n}</span></header>`;
}

function paintTimeline() {
  const feed = $('#feed'); if (!feed) return;
  DIRTY = false;
  const rows = LAYOUT === 'a';
  const by = k => D.items.filter(it => kindOf(it) === k);
  const live = by('live').sort((a, b) => liveAt(b) - liveAt(a));
  const one = it => rows ? rowHTML(it, kindOf(it)) : cardHTML(it);
  const groups = (list, sort) => {   // newest episode first; Up next keeps time order inside each episode
    const eps = [...new Set(list.map(it => it.episode_id))].sort((a, b) => (episode(b)?.recorded_on || '').localeCompare(episode(a)?.recorded_on || ''));
    return eps.map(e => { const l = list.filter(it => it.episode_id === e); if (sort) l.sort(sort); return `<div class="epg">${epHead(e, l.length)}<div class="${rows ? 'rws' : 'cards'}">${l.map(one).join('')}</div></div>`; }).join('');
  };
  const dayOf = iso => new Date(iso).toLocaleDateString('en-CA', { timeZone: LTZ });
  const booked = D.items.filter(it => inTab(it, 'next') && nextDue(it)).sort((a, b) => nextDue(a).localeCompare(nextDue(b))), waiting = D.items.filter(it => inTab(it, 'next') && !nextDue(it));
  const agRow = it => { const due = nextDue(it), w = due ? whenWords(due) : null;
    const fails = PLATFORMS.some(([p]) => pstate(it, p) === 'failed'), notes = openNotes(it.id).length;
    return `<article class="ag${SEL === it.id ? ' sel' : ''}${BUSY.has(it.id) ? ' busy' : ''}" data-id="${esc(it.id)}"><div class="ag-t">${w ? `<b>${w.time}</b>` : '<b>-</b>'}</div>
      <img class="ag-th" src="${esc(thumbOf(it))}" alt="" loading="lazy"><div class="ag-x"><b>${esc(it.title)}</b><span class="pis">${w ? platIcons(it) : fails ? `<i class="dot bad"></i><em class="ag-bad">Failed. Open it to see why.</em>` : `<i class="dot acc"></i>${it.hold ? 'Waiting' : 'Approved, not booked'}`}${notes ? `<em class="ag-note">${notes} note${notes > 1 ? 's' : ''}</em>` : ''}</span></div>
      <div class="acts">${sfxBtn(it)}${stepMini(it, it.round)}</div></article>`; };
  const agDays = [...new Set(booked.map(it => dayOf(nextDue(it))))];
  const agenda = agDays.map(d => { const l = booked.filter(it => dayOf(nextDue(it)) === d), today = dayOf(new Date()), tom = dayOf(Date.now() + 864e5);
      return `<div class="agd"><h3>${d === today ? 'Today' : d === tom ? 'Tomorrow' : new Date(d + 'T12:00:00Z').toLocaleDateString('en-GB', { weekday: 'long', timeZone: 'UTC' })} <small>${new Date(d + 'T12:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' })}</small></h3>${l.map(agRow).join('')}</div>`; }).join('')
    + (waiting.length ? `<div class="agd"><h3>No time yet</h3>${waiting.map(agRow).join('')}</div>` : '');
  const lvTile = it => `<article class="lv${SEL === it.id ? ' sel' : ''}" data-id="${esc(it.id)}"><img src="${esc(thumbOf(it))}" alt="" loading="lazy">
      <div class="lv-x"><span class="lv-d"><i class="dot ok"></i>${new Date(liveAt(it)).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: LTZ })}</span><b>${esc(it.title)}</b><span class="pis">${platIcons(it)}</span></div></article>`;
  // Revisions: a queue, oldest first. Each Short shows the feedback it got. A note leaves with feedback.py --done, or Done in the panel.
  const rvRow = (it, i) => { const notes = openNotes(it.id).slice().reverse(), k = kindOf(it), due = nextDue(it), w = due && whenWords(due);
    return `<article class="rv${SEL === it.id ? ' sel' : ''}" data-id="${esc(it.id)}"><span class="rv-n">${i + 1}</span><img class="rv-th" src="${esc(thumbOf(it))}" alt="" loading="lazy">
      <div class="rv-x"><b>${esc(it.title)}</b>${notes.map(f => `<q>${esc(f.body)}</q>`).join('')}
        <span class="rv-m"><span class="rv-q"><i></i>In the queue</span><small>${esc(vTab(version(it.id, notes[0].round_at)))} · ${fmtWhen(notes[0].created_at)}</small>${k === 'next' ? `<em>Still booked: posts ${w.time} ${w.word}</em>` : k === 'live' ? '<em>Already live</em>' : ''}</span></div></article>`; };
  const list = D.items.filter(it => inTab(it, TAB));
  const oldest = it => openNotes(it.id).reduce((m, f) => f.created_at < m ? f.created_at : m, '9');
  const empty = t => `<p class="tempty">${t}</p>`;
  paintTabs();
  feed.innerHTML = TAB === 'draft' ? `<section class="tsec s-review">${list.length ? groups(list, (a, b) => (a.num ?? 99) - (b.num ?? 99)) : empty(tabCount('rev') ? `No drafts to review. ${tabCount('rev')} ${tabCount('rev') > 1 ? 'Shorts are' : 'Short is'} in Revisions.` : 'No drafts to review.')}</section>`
    : TAB === 'next' ? `<section class="tsec s-next s-agenda">${list.length ? `<div class="agenda">${agenda}</div>` : empty('Nothing scheduled.')}</section>`
    : TAB === 'live' ? `<section class="tsec s-live s-wall">${live.length ? `<div class="lvwall">${live.map(lvTile).join('')}</div>` : empty('Nothing live yet.')}</section>`
    : `<section class="tsec s-rev">${list.length ? `<div class="rvq">${list.slice().sort((a, b) => oldest(a).localeCompare(oldest(b))).map(rvRow).join('')}</div>` : empty('Nothing to re-edit. Feedback you save lands here.')}</section>`;
  $$('.ag, .lv, .rv', feed).forEach(el => { const id = el.dataset.id;
    el.onclick = e => { if (!e.target.closest('button, a')) openPanel(id); };
    el.onpointerenter = () => { freshen(); warm(id); };
    wireSteps(el, id, item(id).round); wireSfx(el, id); });
  if (rows) $$('.s-review .tr', feed).forEach(r => {
    const id = r.dataset.id;
    r.onclick = e => { if (!e.target.closest('button, a')) openPanel(id); };
    r.onpointerenter = () => { freshen(); warm(id); };
    $('.th', r).onclick = e => { e.stopPropagation(); openPanel(id); startPlayer(id, VSEL, $('#panel .pframe')); };
    wireSteps(r, id, item(id).round); wireSfx(r, id);
  });
  else $$('.s-review .card', feed).forEach(wireCard);
  paintSpeed();
}

// One tiny status: a dot and a word or a time. Live and booked also show the platform ticks.
function tinyStatus(it) {
  const k = kindOf(it), due = nextDue(it), w = due && whenWords(due);
  const fails = PLATFORMS.filter(([p]) => pstate(it, p) === 'failed');
  const word = fails.length ? `<i class="dot bad"></i><em class="bad" title="${esc(fails.map(([p, n]) => `${n}: ${it.posted[p].error}`).join(' · '))}">Failed</em>`
    : k === 'next' ? `<i class="dot blue"></i>${w.time} ${w.word}` : k === 'live' ? `<i class="dot ok"></i>Live` : k === 'wait' ? `<i class="dot acc"></i>${it.hold ? 'Waiting' : 'Approved'}` : D.feedback.some(f => f.short_id === it.id && f.kind === 'note' && f.state === 'done') ? `<i class="dot acc"></i>Re-edited` : `<i class="dot"></i>Draft`;
  return `<span class="ts">${word}</span>${k === 'live' || k === 'next' ? `<span class="pis">${platIcons(it)}</span>` : ''}`;
}

// One click: sound effects on or off. It plays the other mix at once and saves the choice; posting uses it.
function sfxBtn(it, round) {
  const v = version(it.id, round ?? it.round); if (!hasSfx(v)) return '';
  const on = it.sfx !== false;
  return `<button class="sfxb${on ? ' on' : ''}" data-sfx title="Sound effects ${on ? 'on: click to remove' : 'off: click to add'}" aria-pressed="${on}">SFX</button>`;
}
function wireSfx(root, id) {
  $$('[data-sfx]', root).forEach(b => b.onclick = e => { e.stopPropagation(); const it = item(id); chooseSfx(id, it.sfx === false); });
}

// The one step, as a small round button. The time it books shows on hover; the panel says it in words.
function stepMini(it, round) {
  if (BUSY.has(it.id)) return `<span class="busyb" title="${esc(BUSY.get(it.id).label)}" role="status" aria-label="${esc(BUSY.get(it.id).label)}"></span>`;
  const s = stateOf(it);
  if (s === 'draft' || (s === 'approved' && !it.hold && POSTING.enabled)) {
    const w = whenWords(nextSlot()), tip = POSTING.enabled ? `Approve and schedule for ${w.time} ${w.word}` : 'Approve';
    return `<button class="okb" data-do="approve" title="${tip}" aria-label="${tip}">${TICK}</button>`;
  }
  return '';
}

function rowHTML(it, kind) {
  return `<article class="tr k-${kind}${SEL === it.id ? ' sel' : ''}${BUSY.has(it.id) ? ' busy' : ''}" data-id="${esc(it.id)}">
    <button class="th" aria-label="Play ${esc(it.title)}"><img src="${esc(thumbOf(it))}" alt="" loading="lazy"><i>${PLAY}</i></button>
    <div class="tt"><b>${esc(it.title)}</b><div class="tsl">${tinyStatus(it)}</div></div>
    <div class="acts">${sfxBtn(it)}${stepMini(it, it.round)}</div>
  </article>`;
}

function cardHTML(it) {
  const v = version(it.id, cardRound(it));
  return `<article class="card k-${kindOf(it)}${SEL === it.id ? ' sel' : ''}${BUSY.has(it.id) ? ' busy' : ''}" data-id="${esc(it.id)}">
    <div class="pframe" data-id="${esc(it.id)}"><img class="poster" src="${esc(v.poster || '')}" alt="" loading="lazy"><button class="playbtn" aria-label="Play ${esc(it.title)}">${PLAY}</button>
      <button class="spd" aria-haspopup="menu"></button><div class="prog"><i></i></div></div>
    <div class="cinfo">${cinfoHTML(it)}</div>
  </article>`;
}

function cinfoHTML(it) {
  const r = cardRound(it), vs = versions(it.id).slice().sort((a, b) => a.round - b.round);
  return `<button class="ctitle" title="Open">${esc(it.title)}</button>
    ${vs.length > 1 ? `<div class="vchips">${vs.map(x => `<button data-r="${x.round}" class="${x.round === r ? 'on' : ''}" title="${esc(verLabel(x))}${x.change_note ? ' · ' + esc(x.change_note) : ''}">${vTab(x)}${x.round === it.round ? '<i></i>' : ''}</button>`).join('')}</div>` : ''}
    <div class="cfoot">${tinyStatus(it)}${sfxBtn(it, r)}${stepMini(it, r)}</div>`;
}

function wireCard(card) {
  const id = card.dataset.id, frame = $('.pframe', card);
  card.onpointerenter = () => { freshen(); warm(id, cardRound(item(id))); };
  frame.onclick = e => { if (e.target.closest('.spd, .prog')) return; P && P.video.parentElement === frame ? togglePlay(frame) : startPlayer(id, cardRound(item(id)), frame); };
  $('.spd', card).onclick = e => { e.stopPropagation(); openMenu(e.currentTarget, SPEEDS.map(x => [x, `${x}×`]), SPEED, setSpeed); };
  wireInfo(card);
}
function wireInfo(card) {
  const id = card.dataset.id;
  $('.ctitle', card).onclick = () => openPanel(id);
  $$('.vchips button', card).forEach(b => b.onclick = () => {
    if (P && P.video.closest('.card') === card) stopPlayer();
    CSEL[id] = +b.dataset.r; const v = version(id, CSEL[id]);
    $('.poster', card).src = v.poster || ''; paintCardInfo(id);
  });
  wireSteps(card, id, cardRound(item(id))); wireSfx(card, id);
}
function paintCardInfo(id) {
  const card = $(`.card[data-id="${CSS.escape(id)}"]`); if (!card) return;
  $('.cinfo', card).innerHTML = cinfoHTML(item(id)); wireInfo(card);
}

function refresh(id) {   // repaint what shows this Short without stopping a video that plays
  const card = $(`.card[data-id="${CSS.escape(id)}"]`);
  if (playingInFeed()) { paintCardInfo(id); DIRTY = true; }
  else if (card && card.classList.contains(`k-${kindOf(item(id))}`) && inTab(item(id), TAB)) { paintCardInfo(id); paintTabs(); }
  else paintTimeline();
  paintNext();
  if (SEL === id) { paintPanelState(); if (!document.activeElement?.matches('textarea, input')) { paintMore(); paintFeedback(); } }
}
function paintFeedLinks() { paintTimeline(); }

// ---------- one Short: in the side panel (A, C) or a large centred view (B) ----------
function openPanel(id, { scroll = false, force = false } = {}) {
  const changed = SEL !== id;
  if (changed && P) stopPlayer();
  SEL = id;
  if (changed && id) VSEL = cardRound(item(id));
  $$('.card, .tr, .ag, .lv, .rv').forEach(r => r.classList.toggle('sel', r.dataset.id === id));
  const want = id ? `#/s/${id}` : '#/';
  if ((location.hash || '#/') !== want) history.replaceState(null, '', want);
  if (usesPanel()) {
    document.body.classList.toggle('sheet-open', !!id);
    if (changed || force) paintPanel();
    if (scroll && id) $(`.tr[data-id="${CSS.escape(id)}"], .card[data-id="${CSS.escape(id)}"], .ag[data-id="${CSS.escape(id)}"], .lv[data-id="${CSS.escape(id)}"], .rv[data-id="${CSS.escape(id)}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (!id && DIRTY) paintTimeline();
    return;
  }
  document.body.classList.toggle('modal-open', !!id);
  const m = $('#modal'); if (!m) return;
  m.hidden = !id;
  if (!id) { m.innerHTML = ''; if (DIRTY) paintTimeline(); return; }
  if (changed || force) paintPanel();
}

// Video, version chips, one status line with one button, the Feedback box. The rest folds away under Details.
function paintPanel() {
  const side = usesPanel(), box = side ? $('#panel') : $('#modal'); if (!box) return;
  closeMenu();
  if (side) { box.classList.toggle('dash', !SEL); if (!SEL) return paintNextPanel(box); }
  if (!SEL) return;
  const it = item(SEL), id = SEL;
  const vs = versions(id).slice().sort((a, b) => a.round - b.round), v = version(id, VSEL);
  const frame = `<div class="pframe" data-id="${esc(id)}"><img class="poster" src="${esc(v.poster || '')}" alt=""><button class="playbtn" aria-label="Play">${PLAY}</button>
      <button class="spd" aria-haspopup="menu"></button><div class="prog"><i></i></div></div>`;
  const tabs = vs.length > 1 ? `<div class="vtabs" role="tablist">${vs.map(x => `<button role="tab" data-r="${x.round}" class="${x.round === v.round ? 'on' : ''}" title="${esc(verLabel(x))}${x.change_note ? ' · ' + esc(x.change_note) : ''}">${vTab(x)}${x.round === it.round ? '<i></i>' : ''}</button>`).join('')}</div>` : '';
  const rest = `${tabs}<div class="pst" id="p-state"></div><div class="fb" id="p-fb"></div><details class="pv-more"><summary>Details</summary><div id="p-more"></div></details>`;
  box.innerHTML = side
    ? `<div class="pin pv"><div class="grab" aria-hidden="true"></div>
        <header class="pv-top"><button class="back" aria-label="Back">←</button><b>${esc(it.title)}</b></header>${frame}${rest}</div>`
    : `<div class="mback"></div><div class="mdl" role="dialog" aria-modal="true" aria-label="${esc(it.title)}">
        <div class="mplay">${frame}</div>
        <div class="minfo"><header class="mtop"><b>${esc(it.title)}</b><button class="mclose" aria-label="Close">✕</button></header>${rest}</div></div>`;
  $$('.back, .mclose, .mback', box).forEach(b => b.onclick = () => openPanel(null));
  const fr = $('.pframe', box);
  fr.onclick = e => { if (e.target.closest('.spd, .prog')) return; P && P.video.parentElement === fr ? togglePlay(fr) : startPlayer(id, VSEL, fr); };
  $('.spd', box).onclick = e => { e.stopPropagation(); openMenu(e.currentTarget, SPEEDS.map(x => [x, `${x}×`]), SPEED, setSpeed); };
  $$('.vtabs button', box).forEach(b => b.onclick = () => {
    stopPlayer(); VSEL = CSEL[id] = +b.dataset.r; paintPanel();
    const c = $(`.card[data-id="${CSS.escape(id)}"]`); if (c) { $('.poster', c).src = version(id, VSEL).poster || ''; paintCardInfo(id); }
  });
  paintSpeed();
  paintPanelState();
  paintFeedback();
  paintMore();
  const k = soundKey(it, v), other = audioKey(it.track || 'none', it.sfx === false, v);   // this sound, and the one SFX switches to
  ensurePlay(id, v.round, k).then(() => v.tracks?.[other] || other === 'none' ? ensurePlay(id, v.round, v.tracks?.[other] ? other : 'none') : null).catch(() => {});
}

function paintPanelState() {
  const box = $('#p-state'); if (!box || !SEL) return;
  const it = item(SEL), s = stateOf(it), due = nextDue(it), w = due && whenWords(due), slot = whenWords(nextSlot());
  if (BUSY.has(SEL)) { box.innerHTML = `<div class="schd" role="status"><div class="schd-l"><i class="tspin"></i><b>${esc(BUSY.get(SEL).label)}</b><span class="schd-p">${BUFFERED.map(k => `<i>${logo(k, true)}</i>`).join('')}</span></div><div class="schd-b"><i></i></div></div>`; return; }
  const fails = PLATFORMS.filter(([k]) => pstate(it, k) === 'failed');
  const line = fails.length ? `<i class="dot bad"></i><span class="bad">${esc(fails.map(([k, n]) => `${n}: ${it.posted[k].error}`).join(' · '))}</span>`
    : s === 'draft' ? `<i class="dot"></i><span>Draft${VSEL !== it.round ? ` · approving books ${vTab(version(SEL, VSEL))}` : ''}</span>`
    : s === 'approved' ? `<i class="dot acc"></i><span>${it.hold ? esc(it.hold) : 'Approved, not booked'}</span>`
    : s === 'scheduled' ? `<i class="dot blue"></i><span>Posts <b>${w.time} ${w.word}</b></span>`
    : `<i class="dot ok"></i><span>Live</span>`;
  const btn = s === 'draft' ? `<button class="btn go" data-do="approve" title="Books ${slot.time} ${slot.word}">${POSTING.enabled ? `Approve · ${slot.time}` : 'Approve'}</button>`
    : s === 'approved' && !it.hold && POSTING.enabled ? `<button class="btn go" data-do="approve">Schedule · ${slot.time}</button>`
    : s === 'scheduled' ? `<button class="btn ghost sm" data-do="now">Post now</button><button class="btn ghost sm" data-do="cancel">Cancel</button>` : '';
  box.innerHTML = `<div class="pl">${line}</div>${s === 'draft' ? '' : `<span class="pis">${platIcons(it)}</span>`}<div class="pacts">${sfxBtn(it, VSEL)}${btn}</div>`;
  wireSteps(box, SEL, VSEL); wireSfx(box, SEL);
}

// Feedback: a small box. Each note is saved against this Short and the version on screen, as "open".
const openNotes = id => D.feedback.filter(f => f.short_id === id && f.kind === 'note' && f.state === 'open');
function paintFeedback() {
  const box = $('#p-fb'); if (!box || !SEL) return;
  const id = SEL, it = item(id), v = version(id, VSEL), open = openNotes(id), edits = versions(id).filter(x => x.change_note);
  box.innerHTML = `<div class="fbx"><textarea rows="2" placeholder="Feedback on ${esc(vTab(v))}" aria-label="Feedback"></textarea><button class="btn ink sm" disabled>Save</button></div>
    ${open.length ? `<ul class="fbl">${open.slice(0, 4).map(f => `<li><span>${esc(f.body)}</span><small>${vTab(version(id, f.round_at))} · ${fmtWhen(f.created_at)}<button class="fdn" data-f="${f.id}" title="This note is dealt with: take it out of Revisions">Done</button></small></li>`).join('')}</ul>` : ''}
    ${edits.length ? `<div class="edh">Edits</div><ul class="fbl edl">${edits.map(x => `<li><span>${esc(x.change_note)}</span><small>${vTab(x)} · ${fmtWhen(x.created_at)}</small></li>`).join('')}</ul>` : ''}`;
  const ta = $('textarea', box), b = $('button', box);
  ta.oninput = () => b.disabled = !ta.value.trim();
  ta.onkeydown = e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && ta.value.trim()) b.click(); };
  b.onclick = async () => { b.disabled = true; try { await act({ op: 'feedback', short_id: id, round: VSEL, body: ta.value.trim() }, 'Feedback saved. It is in Revisions.'); BUMP = 'rev'; paintFeedback(); paintQueue(); } catch { b.disabled = false; } };
  $$('.fdn', box).forEach(x => x.onclick = async () => { x.disabled = true; try { await act({ op: 'feedback_done', id: +x.dataset.f }, 'Note done'); paintFeedback(); paintMore(); paintQueue(); } catch { x.disabled = false; } });
}

const paintQueue = () => { playingInFeed() ? paintTabs() : paintTimeline(); };

// Details: the rest, short.
function paintMore() {
  const box = $('#p-more'); if (!box || !SEL) return;
  const it = item(SEL), id = SEL, v = version(id, VSEL), ep = episode(it.episode_id), { title, caption } = postCopy(it);
  const due = nextDue(it), local = iso => { const d = new Date(iso); return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16); };
  const done = D.feedback.filter(f => f.short_id === id && f.kind === 'note' && f.state === 'done').slice(0, 5);
  box.innerHTML = `
    <div class="mrow"><span>Version</span><em>${esc(verLabel(v))} · ${fmtWhen(v.created_at)}${v.change_note ? ` · ${esc(v.change_note)}` : ''}</em></div>
    <div class="mrow"><span>Sound</span><button class="chip" data-m="music">${TRACK_NAME[it.track || 'none']} ▾</button>${hasSfx(v) ? `<button class="chip ${it.sfx !== false ? 'on' : ''}" data-m="sfx">SFX ${it.sfx !== false ? 'on' : 'off'}</button>` : ''}</div>
    ${stateOf(it) !== 'posted' ? `<div class="mrow"><span>Time</span><input type="datetime-local" value="${local(due || nextSlot())}" step="900" aria-label="Post time"><button class="chip" data-m="time">${due ? 'Move' : 'Book'}</button></div>` : ''}
    <div class="mrow"><span>Episode</span>${ep?.full_url ? `<a href="${esc(ep.full_url)}" target="_blank" rel="noopener" title="${esc(ep.full_title || '')}">Full episode ↗</a>` : '<em>no link yet</em>'}<button class="chip" data-m="link">Edit</button></div>
    <div class="mlink" hidden></div>
    <div class="mrow"><span>Copy</span><button class="chip" data-c="t">Title</button><button class="chip" data-c="c">Caption</button></div>
    ${done.length ? `<div class="mrow col"><span>Done</span>${done.map(f => `<em class="fdone">${esc(f.body)}</em>`).join('')}</div>` : ''}`;
  $('[data-m="music"]', box).onclick = e => openMenu(e.currentTarget, TRACKS.map(([k, n]) => [k, n]), it.track || 'none', k => chooseTrack(id, k));
  const sfx = $('[data-m="sfx"]', box); if (sfx) sfx.onclick = () => chooseSfx(id, it.sfx === false);
  const tm = $('[data-m="time"]', box); if (tm) tm.onclick = async () => { const v2 = $('input[type=datetime-local]', box).value; if (!v2) return; tm.disabled = true; await reschedule(id, VSEL, new Date(v2).toISOString()); };
  $('[data-m="link"]', box).onclick = () => { const m = $('.mlink', box); m.hidden = !m.hidden; if (!m.hidden && !m.childElementCount) m.appendChild(linkEditor(ep, () => { paintTimeline(); paintMore(); })); };
  $$('[data-c]', box).forEach(b => b.onclick = () => navigator.clipboard.writeText(b.dataset.c === 't' ? title : caption).then(() => toast('Copied')));
}

// The next post: a slim strip above the board (B), or big in the side panel when no Short is open (A, C).
function paintNext() {
  if (usesPanel()) { if (!SEL) paintPanel(); return; }
  const box = $('#nxs'); if (!box) return;
  box.innerHTML = ''; return;   // Nothing booked at the top; Scheduled lives at the bottom of the page
  const next = D.items.filter(it => nextDue(it)).sort((a, b) => nextDue(a).localeCompare(nextDue(b)));
  const n = next[0];
  if (!n) { box.innerHTML = ''; return; }   // "Up next" already says nothing is booked
  const w = whenWords(nextDue(n));
  box.innerHTML = `<div class="nxs-in"><span class="nx-k">Next post</span>
    <b class="nxs-t">${w.time} <small>${w.word}</small></b><span class="nxs-c">${fromNow(nextDue(n))}</span>
    <button class="nxs-s" data-id="${esc(n.id)}"><img src="${esc(thumbOf(n))}" alt=""><span>${esc(n.title)}</span></button>
    ${next.length > 1 ? `<span class="nxs-then">Then ${next.slice(1, 3).map(it => { const x = whenWords(nextDue(it)); return `<button data-id="${esc(it.id)}"><b>${x.time}</b> ${x.word}</button>`; }).join(' · ')}</span>` : ''}</div>`;
  $$('[data-id]', box).forEach(b => b.onclick = () => openPanel(b.dataset.id));
}
function paintNextPanel(panel) {
  // No "Next post" at the top. The empty panel just says what it is for.
  panel.innerHTML = `<div class="pin nx"><div class="nx-empty"><b>Pick a Short</b><span>It plays here.</span></div></div>`; return;
  const next = D.items.filter(it => nextDue(it)).sort((a, b) => nextDue(a).localeCompare(nextDue(b)));
  const n = next[0];
  if (!n) { panel.innerHTML = `<div class="pin nx"><div class="nx-empty"><b>Nothing booked</b><span>Approve a Short and it books the next free slot.</span></div></div>`; return; }
  const due = nextDue(n), w = whenWords(due);
  panel.innerHTML = `<div class="pin nx">
    <span class="nx-k">Next post</span>
    <div class="nx-when"><b>${w.time}</b><span>${w.word}</span></div>
    <div class="nx-count">${fromNow(due)}</div>
    <button class="nx-card" data-id="${esc(n.id)}"><img src="${esc(thumbOf(n))}" alt=""><div><b>${esc(n.title)}</b><span class="pis">${platIcons(n)}</span></div></button>
    ${next.length > 1 ? `<div class="nx-then"><span>Then</span>${next.slice(1, 3).map(it => { const x = whenWords(nextDue(it)); return `<button data-id="${esc(it.id)}"><b>${x.time}</b> ${x.word} · ${esc(it.title)}</button>`; }).join('')}</div>` : ''}
  </div>`;
  $$('[data-id]', panel).forEach(b => b.onclick = () => openPanel(b.dataset.id, { scroll: true }));
}
setInterval(() => { if (!D || !$('#feed')) return; paintNext(); if (!playingInFeed()) paintTimeline(); }, 60000);

// Video and music links are signed for 12 h. A page left open longer had dead links, so play did nothing (error 4).
// Get fresh links after 6 h (when the tab comes back, on hover, every 10 min), and once more if a video still fails.
const STALE = 6 * 3600e3;
let FRESHING = null;
function freshen(force = false) {
  if (NEWBUILD && !P) { location.reload(); return Promise.resolve(); }
  if (!D || FRESHING || (!force && Date.now() - LOADED < STALE)) return FRESHING || Promise.resolve();
  FRESHING = load().then(() => { if (NEWBUILD && !P) return location.reload(); if (!$('#feed')) return; paintNext(); if (playingInFeed()) DIRTY = true; else paintTimeline(); }).catch(() => {}).finally(() => { FRESHING = null; });
  return FRESHING;
}
addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') freshen(); });
setInterval(() => freshen(true), 10 * 60000);   // also finds a new deploy within 10 min

// A small chooser that opens on click (speed, music): readable in every state.
function openMenu(anchor, options, current, onPick) {
  closeMenu();
  const m = document.createElement('div');
  m.className = 'menu'; m.setAttribute('role', 'menu');
  m.innerHTML = options.map(([k, n]) => `<button role="menuitemradio" aria-checked="${k === current}" data-k="${k}" class="${k === current ? 'on' : ''}">${n}${k === current ? ` ${TICK}` : ''}</button>`).join('');
  document.body.appendChild(m);
  const r = anchor.getBoundingClientRect();
  m.style.left = Math.min(innerWidth - m.offsetWidth - 8, Math.max(8, r.right - m.offsetWidth)) + 'px';
  m.style.top = (r.bottom + 6 + m.offsetHeight > innerHeight ? r.top - m.offsetHeight - 6 : r.bottom + 6) + scrollY + 'px';
  $$('button', m).forEach(b => b.onclick = e => { e.stopPropagation(); const k = b.dataset.k; closeMenu(); onPick(isNaN(+k) ? k : +k); });
  MENU = m;
  setTimeout(() => addEventListener('click', closeMenu, { once: true }), 0);
}
function closeMenu() { MENU?.remove(); MENU = null; }

// ---------- stats: real numbers per live Short, from /api/stats ----------
const mast = on => `<header class="masthead"><img src="/img/logo.png" alt="${esc(SHOW)}" onerror="this.remove()"><h1>${esc(APP_TITLE)}</h1>
  <nav class="mtabs" aria-label="Views"><a href="#/"${on === 'posts' ? ' aria-current="page"' : ''}>Posts</a><a href="#/stats"${on === 'stats' ? ' aria-current="page"' : ''}>Stats</a></nav></header>`;
let ST = null, ST_OPEN = null, ST_BUSY = false, ST_TICK = null;
const lsGet = (k, d, ok) => { try { const v = localStorage.getItem(k); return ok.includes(v) ? v : d; } catch { return d; } };
let ST_CHART = lsGet('stats-chart', 'day', ['day', 'month']), ST_RANK = lsGet('stats-rank', 'bento', ['bento', 'list']);
const METRICS = [['views', 'Views'], ['likes', 'Likes'], ['comments', 'Comments'], ['shares', 'Shares']];
const fmtN = n => n == null ? '-' : n >= 1e6 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + 'M' : n >= 1e4 ? (n / 1e3).toFixed(n >= 1e5 ? 0 : 1) + 'K' : n.toLocaleString('en-GB');
const agoWords = t => { const m = Math.round((Date.now() - new Date(t)) / 60000); return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : m < 1440 ? `${Math.round(m / 60)} h ago` : `${Math.round(m / 1440)} d ago`; };

// One series per Short and platform, then "the value at time T" = the last snapshot at or before T (0 before the first one).
function statsModel(rows) {
  const keyed = new Map();
  for (const r of rows) { const k = r.short_id + '|' + r.platform; (keyed.get(k) || keyed.set(k, []).get(k)).push(r); }
  const batches = [...new Set(rows.map(r => r.at))].sort();
  const at = (list, t, m) => { let v = null; for (const r of list) { if (r.at > t) break; if (r[m] != null) v = r[m]; } return v; };
  const sumAt = (keys, t, m) => { let s = null; for (const k of keys) { const v = at(keyed.get(k), t, m); if (v != null) s = (s || 0) + v; } return s; };
  const latest = (k, m) => { const l = keyed.get(k); if (!l) return null; for (let i = l.length - 1; i >= 0; i--) if (l[i][m] != null) return l[i][m]; return null; };
  return { keyed, batches, at, sumAt, latest };
}

async function loadStats(op) {
  const r = await fetch('/api/stats', op ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ op }) } : { cache: 'no-store' });
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || r.status);
  return j;
}

async function refreshStats(manual) {
  if (ST_BUSY) return; ST_BUSY = true; paintStatsHead();
  try { ST = await loadStats('refresh'); paintStats(); if (manual) toast('Numbers updated'); if (ST.ig?.pending) setTimeout(() => $('#st-body') && refreshStats(false), 75000); }
  catch (e) { toast('Could not update: ' + e.message, true); }
  ST_BUSY = false; paintStatsHead();
}

async function statsView(app) {
  app.innerHTML = `${mast('stats')}<section class="stv" id="stv"><div class="st-head" id="st-head"></div><div id="st-body"><div class="loading"><i></i><i></i><i></i></div></div></section>`;
  clearInterval(ST_TICK); ST_TICK = setInterval(() => $('#st-head') ? paintStatsHead() : clearInterval(ST_TICK), 30000);
  paintStatsHead();
  try { ST = await loadStats(); } catch (e) { $('#st-body').innerHTML = `<p class="tempty">Could not load the numbers: ${esc(e.message)}</p>`; return; }
  paintStats(true);
  if (!ST.updated_at || Date.now() - new Date(ST.updated_at) > 30 * 60000) refreshStats(false);
}

function paintStatsHead() {
  const h = $('#st-head'); if (!h) return;
  h.innerHTML = `<div><h2>Stats</h2><span>${ST_BUSY ? 'Reading YouTube, TikTok and Instagram…' : ST?.updated_at ? `Updated ${agoWords(ST.updated_at)} · ${fmtLocal(ST.updated_at)}` : 'No numbers yet'}</span></div>
    <button class="btn ghost sm" id="st-refresh" ${ST_BUSY ? 'disabled' : ''}>${ST_BUSY ? 'Updating…' : 'Update now'}</button>`;
  $('#st-refresh').onclick = () => refreshStats(true);
}

function spark(vals, w = 120, h = 32) {
  const v = vals.filter(x => x != null);
  if (v.length < 2) return `<svg class="spark none" viewBox="0 0 ${w} ${h}" aria-hidden="true"><line x1="0" y1="${h - 2}" x2="${w}" y2="${h - 2}"/></svg>`;
  const lo = Math.min(...v), hi = Math.max(...v), r = hi - lo || 1;
  const pts = v.map((x, i) => [i / (v.length - 1) * w, h - 3 - (x - lo) / r * (h - 6)]);
  const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true"><path class="a" d="${d} L${w} ${h} L0 ${h}Z"/><path class="l" d="${d}"/><circle cx="${pts.at(-1)[0]}" cy="${pts.at(-1)[1]}" r="2.6"/></svg>`;
}

function paintStats(first = false) {
  const body = $('#st-body'); if (!body || !ST) return;
  paintStatsHead();
  const M = statsModel(ST.rows);
  const live = D.items.filter(it => liveAt(it));
  const keysOf = it => PLATFORMS.map(([p]) => it.id + '|' + p).filter(k => M.keyed.has(k));
  const allKeys = [...M.keyed.keys()];
  if (!live.length) { body.innerHTML = `<p class="tempty">Nothing live yet. Numbers show here after the first post.${ST.ig?.off ? ' ' + esc(ST.ig.off) : ''}</p>`; return; }
  if (!allKeys.length) { body.innerHTML = `<p class="tempty">No numbers yet. Press Update now.${ST.ig?.off ? ' ' + esc(ST.ig.off) : ''}</p>`; return; }
  const now = M.batches.at(-1);
  // Change: against the last check at least 24 h ago, else against the first check (and say so).
  const dayAgo = new Date(Date.parse(now) - 86400e3).toISOString();
  const base = [...M.batches].reverse().find(b => b <= dayAgo) || (M.batches.length > 1 ? M.batches[0] : null);
  const baseWord = base && base <= dayAgo ? 'in 24 h' : base ? `since ${fmtLocal(base)}` : '';

  // Round 10: a calm bento. One big Views tile (band texture), three small tiles, one chart with a Day / Month switch,
  // a platform card, then the ranking as bento tiles (or the old list, one tap away).
  const kpi = ([m, name]) => {
    // Change counts only posts that were already tracked at the start, so a platform's first numbers are not "new views".
    const baseKeys = base ? allKeys.filter(k => M.at(M.keyed.get(k), base, m) != null) : [];
    const total = M.sumAt(allKeys, now, m), was = baseKeys.length ? M.sumAt(baseKeys, base, m) : null, nowB = baseKeys.length ? M.sumAt(baseKeys, now, m) : null;
    const delta = nowB != null && was != null ? nowB - was : null;
    const dp = delta != null ? `<em class="dp${delta > 0 ? ' up' : ''}">${delta > 0 ? '▲ ' : ''}+${fmtN(delta)} <small>${baseWord}</small></em>` : '';
    if (m === 'views') return `<article class="b-hero"><span class="k">Views</span><b class="n" data-to="${total ?? ''}">${total == null ? '-' : first ? '0' : fmtN(total)}</b>
      <div class="kf">${dp}</div>${spark(M.batches.map(b => M.sumAt(allKeys, b, m)), 260, 70)}</article>`;
    return `<article class="b-kpi"><span class="k">${name}</span><b class="n" data-to="${total ?? ''}">${total == null ? '-' : first ? '0' : fmtN(total)}</b>${dp}</article>`;
  };

  const platTotal = Math.max(1, ...PLATFORMS.map(([p]) => M.sumAt(allKeys.filter(k => k.endsWith('|' + p)), now, 'views') || 0));
  const plats = PLATFORMS.map(([p, n]) => {
    const keys = allKeys.filter(k => k.endsWith('|' + p)), v = M.sumAt(keys, now, 'views');
    const note = v == null ? (p === 'instagram' ? (ST.ig?.pending ? 'updating…' : ST.ig?.off ? 'not set up' : ST.ig?.error ? 'read failed' : 'no data yet') : 'no data yet') : '';
    return `<div class="b-pl${v == null ? ' nodata' : ''}" title="${n}${p === 'instagram' && ST.ig?.harvested_at ? ` · read ${agoWords(ST.ig.harvested_at)}` : ''}"><span class="pl">${logo(p, v != null)}</span>
      <div class="pt"><i style="--w:${(v || 0) / platTotal * 100}%"></i></div><b>${v == null ? note : fmtN(v)}</b></div>`;
  }).join('');

  // Views per day / month: each bar = views first seen in that day or month (we only know a view when a check sees it).
  const days = []; for (let i = 6; i >= 0; i--) days.push(addDays(dayKey(now), -i));
  const endOf = d => M.batches.filter(x => dayKey(x) <= d).at(-1) || null;
  const perDay = days.map((d, i) => { const e = endOf(d); if (!e || dayKey(M.batches[0]) > d) return null; const pe = endOf(days[i - 1] || addDays(d, -1)); return (M.sumAt(allKeys, e, 'views') || 0) - (pe ? M.sumAt(allKeys, pe, 'views') || 0 : 0); });
  const months = []; { const last = dayKey(now).slice(0, 7); let m = dayKey(M.batches[0]).slice(0, 7); while (m <= last && months.length < 12) { months.push(m); const [y, mo] = m.split('-').map(Number); m = mo === 12 ? `${y + 1}-01` : `${y}-${String(mo + 1).padStart(2, '0')}`; } }
  const endOfM = m => M.batches.filter(x => dayKey(x).slice(0, 7) <= m).at(-1) || null;
  const perMonth = months.map((m, i) => { const e = endOfM(m), pe = i ? endOfM(months[i - 1]) : null; return (M.sumAt(allKeys, e, 'views') || 0) - (pe ? M.sumAt(allKeys, pe, 'views') || 0 : 0); });
  const chartOf = (vals, labels, title) => { const peak = Math.max(1, ...vals.filter(x => x != null));
    return vals.map((v, i) => `<div class="bar${v == null ? ' empty' : ''}${i === vals.length - 1 ? ' today' : ''}" title="${title(i)}: ${v == null ? 'not tracked' : v.toLocaleString('en-GB') + ' views'}">
      <span class="bv">${v == null ? '' : fmtN(v)}</span><i style="--h:${v == null ? 4 : Math.max(4, v / peak * 100)}%"></i><span class="bd">${labels[i]}</span></div>`).join(''); };
  const dayBars = chartOf(perDay, days.map(d => new Date(d + 'T12:00:00Z').toLocaleDateString('en-GB', { weekday: 'short', timeZone: 'UTC' })), i => fmtShort(days[i]));
  const monBars = chartOf(perMonth, months.map(m => new Date(m + '-15T12:00:00Z').toLocaleDateString('en-GB', { month: 'short', timeZone: 'UTC' })), i => months[i]);

  const ranked = live.map(it => { const keys = keysOf(it); return { it, keys, views: M.sumAt(keys, now, 'views') }; }).sort((a, b) => (b.views ?? -1) - (a.views ?? -1));
  const top = Math.max(1, ...ranked.map(r => r.views || 0));
  const epDate = it => { const d = episode(it.episode_id)?.recorded_on; return d ? new Date(d + 'T12:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' }) : ''; };
  const perOf = it => PLATFORMS.map(([p, n]) => { const k = it.id + '|' + p, v = M.keyed.has(k) ? M.latest(k, 'views') : null; return `<span class="pv-n${v == null ? ' nodata' : ''}" title="${n}">${logo(p, v != null)}${v == null ? '–' : fmtN(v)}</span>`; }).join('');
  const splitOf = it => { const vals = PLATFORMS.map(([p]) => { const k = it.id + '|' + p; return M.keyed.has(k) ? M.latest(k, 'views') || 0 : 0; }), sum = vals.reduce((a, b) => a + b, 0) || 1;
    return `<div class="b-split">${PLATFORMS.map(([p, n], i) => vals[i] ? `<i class="seg-${p}" style="flex:${vals[i] / sum}" title="${n}: ${vals[i].toLocaleString('en-GB')}"></i>` : '').join('')}</div>`; };
  const detailOf = it => `<div class="lb-detail">${PLATFORMS.map(([p, n]) => {
      const k = it.id + '|' + p, has = M.keyed.has(k), u = it.posted?.[p]?.url;
      const cell = m => { const v = has ? M.latest(k, m) : null; return `<div><b>${v == null ? '-' : fmtN(v)}</b><span>${m}</span></div>`; };
      return `<div class="lbp${has ? '' : ' nodata'}"><div class="lbp-h"><span title="${n}" aria-label="${n}">${logo(p, has)}</span>${u ? `<a href="${esc(u)}" target="_blank" rel="noopener">Open ↗</a>` : ''}</div>
        ${has ? `<div class="lbp-m">${METRICS.map(([m]) => cell(m)).join('')}</div>` : `<p>no data yet</p>`}</div>`; }).join('')}</div>`;
  const vnum = r => `<b data-to="${r.views ?? ''}">${r.views == null ? '-' : first ? '0' : fmtN(r.views)}</b>`;

  const tiles = ranked.map((r, i) => {
    const { it } = r, open = ST_OPEN === it.id, size = i === 0 ? 'xl' : i < 3 ? 'md' : 'sm';
    return `<article class="bt ${size}${open ? ' open' : ''}" data-id="${esc(it.id)}">
      <div class="bt-in"><div class="bt-po"><img src="${esc(thumbOf(it))}" alt="" loading="lazy"><span class="bt-rk">${i + 1}</span></div>
        <div class="bt-tx"><span class="bt-ep">${epDate(it)}</span><h4>${esc(it.title)}</h4>
          <div class="bt-v">${vnum(r)}<span>views</span></div>${splitOf(it)}<div class="lb-per">${perOf(it)}</div></div></div>
      ${open ? detailOf(it) : ''}</article>`;
  }).join('');
  const rows = ranked.map((r, i) => {
    const { it } = r, open = ST_OPEN === it.id;
    return `<article class="lb${open ? ' open' : ''}${i === 0 && r.views ? ' first' : ''}" data-id="${esc(it.id)}">
      <div class="lb-row"><span class="rk">${i + 1}</span><img class="lb-th" src="${esc(thumbOf(it))}" alt="" loading="lazy">
        <div class="lb-main"><b><span class="lb-ep">${epDate(it)}</span>${esc(it.title)}</b>
          <div class="lb-bar">${PLATFORMS.map(([p, n]) => { const k = it.id + '|' + p, v = M.keyed.has(k) ? M.latest(k, 'views') || 0 : 0; return v ? `<i class="seg-${p}" style="--w:${v / top * 100}%" title="${n}: ${v.toLocaleString('en-GB')}"></i>` : ''; }).join('')}</div>
          <div class="lb-per">${perOf(it)}</div></div>
        <div class="lb-v">${vnum(r)}<span>views</span></div></div>
      ${open ? detailOf(it) : ''}</article>`;
  }).join('');

  const seg = (name, cur, opts) => `<div class="b-seg" data-seg="${name}">${opts.map(([k, l]) => `<button data-k="${k}"${k === cur ? ' aria-pressed="true"' : ''}>${l}</button>`).join('')}</div>`;
  body.innerHTML = `
    <div class="bento">${kpi(METRICS[0])}${METRICS.slice(1).map(kpi).join('')}</div>
    <div class="bento2">
      <section class="st-card b-chart"><h3>Views per ${ST_CHART === 'month' ? 'month' : 'day'} ${seg('chart', ST_CHART, [['day', 'Day'], ['month', 'Month']])}</h3>
        <div class="bars${ST_CHART === 'month' ? ' mon' : ''}">${ST_CHART === 'month' ? monBars : dayBars}</div>
        <p class="st-note">Tracking since ${fmtShort(dayKey(M.batches[0]))}. Watch time needs the channel owner's sign-in.</p></section>
      <section class="st-card"><h3>By platform</h3><div class="b-pls">${plats}</div></section>
    </div>
    <section class="st-card b-rank"><h3>Top Shorts <small>${live.length} live · tap one for detail</small> ${seg('rank', ST_RANK, [['bento', 'Bento'], ['list', 'List']])}</h3>
      ${ST_RANK === 'list' ? `<div class="lbs">${rows}</div>` : `<div class="btiles">${tiles}</div>`}</section>`;
  $$('.lb, .bt', body).forEach(el => el.onclick = e => { if (e.target.closest('a, .lb-detail')) return; ST_OPEN = ST_OPEN === el.dataset.id ? null : el.dataset.id; paintStats(); });
  $$('.b-seg button', body).forEach(b => b.onclick = () => {
    const s = b.parentElement.dataset.seg, k = b.dataset.k;
    if (s === 'chart') ST_CHART = k; else ST_RANK = k;
    try { localStorage.setItem('stats-' + s, k); } catch {}
    paintStats();
  });
  if (first) countUp(body);
}

function countUp(root) {
  const els = $$('[data-to]', root).filter(e => e.dataset.to !== '');
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { els.forEach(e => e.textContent = fmtN(+e.dataset.to)); return; }
  const t0 = performance.now(), dur = 900;
  const step = t => { const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3); els.forEach(el => el.textContent = fmtN(Math.round(+el.dataset.to * e))); if (k < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}

// ---------- router ----------
let painted = false;
async function route() {
  const app = $('#app');
  const path = (location.hash.slice(1) || '/').split('?')[0];
  try { if (!D) await load(); } catch (e) { app.innerHTML = `<div class="err"><h2>Could not load</h2><p>${esc(e.message)}</p></div>`; return; }
  if (path === '/stats') { stopPlayer(); SEL = null; document.body.classList.remove('modal-open', 'sheet-open'); statsView(app); window.scrollTo(0, 0); return; }
  const openId = path.startsWith('/s/') ? decodeURIComponent(path.slice(3)) : null;
  if (painted && $('#feed')) { if (openId !== SEL) openPanel(openId, { scroll: true }); return; }
  desk(app, openId);
  if (!painted) { syncBuffer(); setTimeout(prefetchPlays, 1500); }
  painted = true;
  if (!openId) window.scrollTo(0, 0);
}
addEventListener('hashchange', route);
addEventListener('keydown', e => { if (e.key === 'Escape' && SEL) { stopPlayer(); openPanel(null); } });
let dayNow = todayKey();   // a new day row appears on its own, even if the page stays open overnight
setInterval(() => { if (todayKey() !== dayNow) { dayNow = todayKey(); if (!P) desk($('#app'), SEL); } }, 60000);
route();

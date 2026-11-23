// The page with no brand built in: public/index.html + a sample brand.css + brand.js, under a light and a dark palette,
// with /api mocked. Run from app/: node tests/page_test.mjs
// Without a browser it checks the files only. For the full check, point it at your own Chrome and puppeteer-core:
//   CHROME_PATH=/path/to/chrome PUPPETEER_DIR=/folder/holding/node_modules SHOTS=/tmp/shots node tests/page_test.mjs
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import vm from 'node:vm';

const pub = new URL('../public/', import.meta.url);
let bad = 0; const ok = (n, c, info = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n, info); if (!c) bad++; };
const TYPES = { html: 'text/html', css: 'text/css', js: 'text/javascript', svg: 'image/svg+xml' };

const LIGHT = { bg: '#F2F2EE', bg_2: '#E8E8E2', surface: '#FFFFFF', line: '#E2E2DA', line_2: '#D2D2C8', ink: '#111111', ink_2: '#333333', mute: '#7D7D75', accent: '#3DDC97', accent_soft: '#DFF8EC', accent_ink: '#14613F', on_accent: '#0B0B0C' };
const DARK = { bg: '#131316', bg_2: '#1D1D22', surface: '#222228', line: '#303038', line_2: '#42424C', ink: '#F4F4F2', ink_2: '#CFCFCB', mute: '#94948E', accent: '#FFB454', accent_soft: '#3A2C18', accent_ink: '#FFD49A', on_accent: '#1A1208' };
const brandCss = p => `:root {
  --on-accent: ${p.on_accent}; --font-display: 'BrandDisplay'; --font-body: 'BrandBody'; --font-mono: 'BrandMono';
  ${Object.entries({ bg: p.bg, 'bg-2': p.bg_2, surface: p.surface, line: p.line, 'line-2': p.line_2, ink: p.ink, 'ink-2': p.ink_2, mute: p.mute, accent: p.accent, 'accent-soft': p.accent_soft, 'accent-ink': p.accent_ink }).map(([k, v]) => `--app-${k}: ${v};`).join(' ')}
}`;
const brandJs = `window.BRAND = ${JSON.stringify({
  show: { name: 'Test Show', short: 'Test', handle: 'testshow', site: 'https://example.com' },
  people: [{ id: 'a', name: 'Host One', tag: '#HostOne' }],
  posting: { platforms: ['youtube', 'instagram', 'tiktok'], timezone: 'UTC', gap_hours: 4, clash_hours: 1, always_tags: ['#HostOne'], cta_line: 'Watch the full episode:' },
  app: { title: 'Test Show Shorts System', approver: 'Host One' }, logo: { wordmark_text: 'TEST SHOW' }, music: [], shorts_per_episode: 5
})};`;

// ---------- files only ----------
const html = await readFile(new URL('index.html', pub), 'utf8');
ok('index.html loads brand.css before app.css', html.indexOf('/brand.css') > 0 && html.indexOf('/brand.css') < html.indexOf('/app.css'));
ok('index.html loads brand.js before app.js', html.indexOf('/brand.js') > 0 && html.indexOf('/brand.js') < html.indexOf('/app.js'));
ok('index.html has no web font link', !/fonts\.googleapis|fonts\.gstatic/.test(html));
for (const f of ['logos.js', 'app.js']) { let good = true; try { new vm.Script(await readFile(new URL(f, pub), 'utf8'), { filename: f }); } catch (e) { good = false; console.log(e.message); } ok(`${f} parses`, good); }
const css = await readFile(new URL('app.css', pub), 'utf8');
const root = css.slice(css.indexOf(':root'), css.indexOf('}', css.indexOf(':root')));
ok('app.css maps every app token', ['bg', 'bg-2', 'surface', 'line', 'line-2', 'ink', 'ink-2', 'mute', 'accent', 'accent-soft', 'accent-ink'].every(k => root.includes(`var(--app-${k})`)));

// ---------- mock server ----------
const H = 3600e3, T = Date.now(), iso = t => new Date(t).toISOString();
const item = (n, status, posted = {}, extra = {}) => ({ id: `ep-2/s${n}`, episode_id: 'ep-2', num: n, title: `Sample Short number ${n} with a real length title`, round: 2, round_label: 'v2', status, track: 't1', sfx: true, hold: null, posted, updated_at: iso(T), created_at: iso(T - 40 * H),
  copy: { caption: 'A sample caption for this Short.', hashtags: ['#Sample'], youtube_title: `Sample Short ${n}` }, ...extra });
const sched = { state: 'scheduled', at: iso(T), due: iso(T + 20 * H), buffer_id: 'b1', url: '' };
const live = k => ({ state: 'posted', at: iso(T - 30 * H), buffer_id: 'b2', url: `https://example.com/${k}` });
const ITEMS = [item(1, 'draft'), item(2, 'draft'), item(3, 'approved'), item(4, 'scheduled', { youtube: sched, tiktok: sched, instagram: sched }), item(5, 'posted', { youtube: live('y'), tiktok: live('t'), instagram: live('i') }), item(6, 'posted', { youtube: live('y2') })];
const VERS = ITEMS.flatMap(it => [2, 1].map(r => ({ id: `${it.id}-${r}`, short_id: it.id, round: r, round_label: `v${r}`, change_note: 'Tighter first line.', video_path: 'v.mp4', video: '/mock/none.mp4', poster: '/mock/poster.svg', poster_path: 'p.jpg', tracks: { none: 'a', t1: 'a', t2: 'a', t3: 'a', sfx_none: 'a', sfx_t1: 'a' }, track_urls: { none: '/mock/a.m4a', t1: '/mock/a.m4a', t2: '/mock/a.m4a', t3: '/mock/a.m4a', sfx_none: '/mock/a.m4a', sfx_t1: '/mock/a.m4a' }, play: {}, play_urls: {}, duration: 48, created_at: iso(T - 20 * H) })));
const FB = [{ id: 1, episode_id: 'ep-2', short_id: 'ep-2/s2', kind: 'note', author: 'owner', body: 'Trim the first second and change the title.', status_at: 'draft', round_at: 2, track_at: 't1', created_at: iso(T - 2 * H), state: 'open' },
  { id: 2, episode_id: 'ep-2', short_id: 'ep-2/s1', kind: 'change', author: 'team', body: 'Round 2 uploaded.', status_at: 'draft', round_at: 2, track_at: 't1', created_at: iso(T - 3 * H) },
  { id: 3, episode_id: 'ep-2', short_id: 'ep-2/s1', kind: 'status', author: 'app', body: 'Approved → Draft', status_at: 'draft', round_at: 2, track_at: 't1', created_at: iso(T - 4 * H) }];
const DATA = { episodes: [{ id: 'ep-2', title: 'Sample episode', recorded_on: new Date(T - 48 * H).toISOString().slice(0, 10), full_url: 'https://example.com/full', full_title: 'The sample full episode' }], items: ITEMS, versions: VERS, feedback: FB, at: iso(T), build: 'test' };
const ROWS = ['youtube', 'tiktok', 'instagram'].flatMap((p, i) => [50, 26, 2].map((h, j) => ({ short_id: 'ep-2/s5', platform: p, at: iso(T - h * H), views: (j + 1) * 1200 * (i + 1), likes: (j + 1) * 40, comments: 4 + j, shares: i, source: 'test' })));
const posterSvg = p => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 90 160"><defs><linearGradient id="g" x2="0" y2="1"><stop offset="0" stop-color="#556"/><stop offset="1" stop-color="#223"/></linearGradient></defs><rect width="90" height="160" fill="url(#g)"/></svg>`;
const bandSvg = p => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 220" preserveAspectRatio="none"><rect width="400" height="220" fill="${p.ink}"/><circle cx="330" cy="60" r="130" fill="${p.accent}" opacity=".7"/></svg>`;
const logoSvg = p => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 190 34"><text x="0" y="26" font-family="Arial Black,Arial" font-size="24" fill="${p.bg}">TEST SHOW</text></svg>`;

function serve(p, statsMode) {
  return createServer(async (req, res) => {
    const u = new URL(req.url, 'http://x'), path = u.pathname;
    const send = (type, body, code = 200) => { res.writeHead(code, { 'Content-Type': type, 'Cache-Control': 'no-store' }); res.end(body); };
    const json = o => send('application/json', JSON.stringify(o));
    if (path === '/brand.css') return send(TYPES.css, brandCss(p));
    if (path === '/brand.js') return send(TYPES.js, brandJs);
    if (path === '/img/logo.png') return send(TYPES.svg, logoSvg(p));
    if (path.startsWith('/img/')) return send(TYPES.svg, bandSvg(p));
    if (path === '/mock/poster.svg') return send(TYPES.svg, posterSvg(p));
    if (path === '/api/data') return json(DATA);
    if (path === '/api/post') return json({ enabled: false, channels: { youtube: 'y', instagram: 'i', tiktok: 't' }, items: [], feedback: [] });
    if (path === '/api/stats') return json(statsMode.rows ? { rows: ROWS, updated_at: iso(T - 2 * H), misses: [], ig: { off: null } } : { rows: [], updated_at: null, misses: [], ig: { off: 'Instagram numbers need an APIFY_TOKEN. YouTube and TikTok do not.' } });
    if (path.startsWith('/api/')) return json({ ok: true, feedback: [] });
    try { const f = path === '/' ? 'index.html' : path.slice(1); send(TYPES[f.split('.').pop()] || 'application/octet-stream', await readFile(new URL(f, pub))); }
    catch { send('text/plain', 'not found', 404); }
  });
}

// ---------- browser part ----------
const { CHROME_PATH, PUPPETEER_DIR, SHOTS } = process.env;
if (!CHROME_PATH || !PUPPETEER_DIR) {
  console.log('Browser part skipped: set CHROME_PATH and PUPPETEER_DIR to run it.');
} else {
  const puppeteer = createRequire(PUPPETEER_DIR + '/x.js')('puppeteer-core');
  const browser = await puppeteer.launch({ executablePath: CHROME_PATH, headless: true, args: ['--mute-audio', '--no-sandbox'] });
  if (SHOTS) await mkdir(SHOTS, { recursive: true });
  for (const [name, palette] of [['light', LIGHT], ['dark', DARK]]) {
    const mode = { rows: false };
    const srv = serve(palette, mode); await new Promise(r => srv.listen(0, r));
    const base = `http://127.0.0.1:${srv.address().port}/`;
    const page = await browser.newPage(); await page.setViewport({ width: 1440, height: 900 });
    const errors = [];
    page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text() + ' ' + (m.location()?.url || '')); });
    page.on('pageerror', e => errors.push('page: ' + e.message));
    page.on('response', r => { if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`); });
    const shot = async n => { if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}-${n}.png` }); };
    await page.goto(base, { waitUntil: 'networkidle2' });
    await page.waitForSelector('.masthead');
    ok(`${name}: title comes from brand.js`, (await page.title()) === 'Test Show Shorts System');
    ok(`${name}: masthead shows the brand title`, (await page.$eval('.masthead h1', e => e.textContent)) === 'Test Show Shorts System');
    ok(`${name}: favicon follows the accent`, decodeURIComponent(await page.$eval('#favicon', e => e.href)).includes(palette.accent));
    ok(`${name}: page background is the brand colour`, await page.evaluate(bg => { const a = document.createElement('i'); a.style.color = bg; document.body.append(a); const want = getComputedStyle(a).color; a.remove(); return getComputedStyle(document.body).backgroundColor === want; }, palette.bg));
    await shot('drafts');
    for (const t of ['next', 'live', 'rev', 'draft']) {
      await page.evaluate(k => document.querySelector(`.ptabs button[data-t="${k}"]`).click(), t);
      await new Promise(r => setTimeout(r, 150));
      ok(`${name}: tab ${t} opens`, await page.$eval('#feed', e => e.children.length > 0 || e.textContent.length > 0));
      if (t !== 'draft') await shot('tab-' + t);
    }
    await page.goto(base + '#/s/' + encodeURIComponent('ep-2/s1'), { waitUntil: 'networkidle2' });
    await new Promise(r => setTimeout(r, 300));
    ok(`${name}: Short opens with track switch`, !!(await page.$('#panel .pframe')));
    await shot('panel');
    for (const n of [2, 4, 5]) {
      await page.evaluate(id => { location.hash = '#/s/' + encodeURIComponent(id); }, 'ep-2/s' + n);
      await new Promise(r => setTimeout(r, 300));
      await shot('panel-s' + n);
    }
    for (const l of ['b', 'c']) {
      await page.evaluate(k => { localStorage.setItem('shorts-layout', k); localStorage.setItem('posts-tab', 'next'); }, l);
      await page.goto(base + `?l=${l}#/`, { waitUntil: 'networkidle2' });
      await new Promise(r => setTimeout(r, 300));
      await shot('layout-' + l);
    }
    await page.evaluate(() => { localStorage.setItem('shorts-layout', 'a'); localStorage.setItem('posts-tab', 'draft'); });
    await page.goto(base + '#/stats', { waitUntil: 'networkidle2' });
    await page.waitForSelector('#st-head');
    await new Promise(r => setTimeout(r, 300));
    ok(`${name}: stats with no numbers says so plainly`, /APIFY_TOKEN/.test(await page.$eval('#st-body', e => e.textContent)));
    await shot('stats-empty');
    mode.rows = true;
    await page.goto(base + '?x=1#/stats', { waitUntil: 'networkidle2' });
    await page.waitForSelector('.b-hero, .kpi.main', { timeout: 5000 }).catch(() => {});
    await new Promise(r => setTimeout(r, 1200));
    if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}-stats.png`, fullPage: true });
    ok(`${name}: no console errors`, !errors.length, errors.slice(0, 6).join(' | '));
    await page.close(); srv.close();
  }
  await browser.close();
}
console.log(bad ? `${bad} FAILED` : 'ALL PASS'); process.exit(bad ? 1 : 0);

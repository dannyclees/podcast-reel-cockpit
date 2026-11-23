// The no-brand, no-keys paths of the API. Run from app/: node tests/api_test.mjs
import './_stubs.mjs';
process.env.SUPABASE_URL = 'http://fake'; process.env.SUPABASE_SERVICE_KEY = 'k';
delete process.env.APIFY_TOKEN; delete process.env.POSTING_ENABLED; delete process.env.BUFFER_CHANNELS;
const J = o => new Response(JSON.stringify(o), { status: 200 });
const asked = [];
globalThis.fetch = async url => {
  url = String(url); asked.push(url);
  if (url.includes('/rest/v1/')) return J([]);
  if (url.includes('/storage/v1/')) return J([]);
  throw new Error('should not be called: ' + url);
};
const load = f => import(new URL(`../${f}`, import.meta.url).href).then(m => m.default);
const call = (h, req) => new Promise(ok => { const res = { setHeader() {}, end(s) { ok({ code: res.statusCode, body: JSON.parse(s) }); } }; h(req, res); });
let bad = 0; const ok = (n, c, info = '') => { console.log((c ? 'PASS ' : 'FAIL ') + n, info); if (!c) bad++; };

const stats = await load('api/stats.js');
let r = await call(stats, { method: 'GET' });
ok('stats, no Apify token: page data comes back empty', r.code === 200 && r.body.rows.length === 0);
ok('stats, no Apify token: says so in plain words', /APIFY_TOKEN/.test(r.body.ig.off || ''), r.body.ig.off);
r = await call(stats, { method: 'POST', body: { op: 'refresh' } });
ok('stats refresh, no Apify token: works', r.code === 200 && /APIFY_TOKEN/.test(r.body.ig.off || ''));
process.env.APIFY_TOKEN = 'x';
r = await call(stats, { method: 'GET' });
ok('stats, token but no username: says so', /instagram_username/.test(r.body.ig.off || ''), r.body.ig.off);
delete process.env.APIFY_TOKEN;

const post = await load('api/post.js');
r = await call(post, { method: 'POST', body: { op: 'status' } });
ok('posting is off by default', r.code === 200 && r.body.enabled === false);
r = await call(post, { method: 'POST', body: { op: 'schedule', id: 'e/x' } });
ok('schedule refused while off, plain message', r.code === 403 && /POSTING_ENABLED=1/.test(r.body.error), r.body.error);

asked.length = 0;
const data = await load('api/data.js');
globalThis.fetch = async url => { url = String(url); asked.push(url); return J(url.includes('shorts_episodes') ? [{ id: 'e', title: 'E', recorded_on: '2026-01-01', full_url: null }] : []); };
r = await call(data, { method: 'GET' });
ok('data, blank YouTube channel id: no feed lookup', r.code === 200 && !asked.some(u => u.includes('youtube.com')));

const mw = await load('middleware.js');
const gate = (auth) => mw(new Request('http://x/', { headers: auth ? { authorization: 'Basic ' + btoa(auth) } : {} }));
delete process.env.SITE_PASSWORD; delete process.env.SITE_USER;
ok('middleware, no password set: fails closed', gate().status === 503);
process.env.SITE_PASSWORD = 'pw';
ok('middleware, no login: asks with a neutral realm', gate().status === 401 && gate().headers.get('www-authenticate').includes('Shorts Review'));
ok('middleware, default user is owner', gate('owner:pw') === undefined && gate('other:pw').status === 401);
console.log(bad ? `${bad} FAILED` : 'ALL PASS'); process.exit(bad ? 1 : 0);

// Tiny Supabase client: PostgREST + Storage over fetch, service key, server side only.
import BRAND from './_brand.js';

const URL = process.env.SUPABASE_URL;
const KEY = process.env.SUPABASE_SERVICE_KEY;
export const BUCKET = BRAND.app?.bucket || 'shorts-media';

const H = (extra = {}) => ({ apikey: KEY, Authorization: `Bearer ${KEY}`, 'Content-Type': 'application/json', ...extra });

export async function rest(path, { method = 'GET', body, prefer } = {}) {
  const r = await fetch(`${URL}/rest/v1/${path}`, {
    method, headers: H(prefer ? { Prefer: prefer } : {}), body: body === undefined ? undefined : JSON.stringify(body)
  });
  const text = await r.text();
  if (!r.ok) throw new Error(`supabase ${method} ${path.split('?')[0]}: ${r.status} ${text.slice(0, 300)}`);
  return text ? JSON.parse(text) : null;
}

// Signed URLs for private media. Returns {path: url}.
export async function sign(paths, expiresIn = 60 * 60 * 12) {
  const out = {};
  const list = [...new Set(paths.filter(Boolean))];
  if (!list.length) return out;
  // Storage refuses more than 1000 paths in one request (past 1000 the whole app would go down).
  const batches = [];
  for (let i = 0; i < list.length; i += 1000) batches.push(list.slice(i, i + 1000));
  await Promise.all(batches.map(async paths => {
    const r = await fetch(`${URL}/storage/v1/object/sign/${BUCKET}`, {
      method: 'POST', headers: H(), body: JSON.stringify({ expiresIn, paths })
    });
    if (!r.ok) throw new Error(`sign: ${r.status} ${(await r.text()).slice(0, 200)}`);
    for (const s of await r.json()) if (s.signedURL) out[s.path] = `${URL}/storage/v1${s.signedURL}`;
  }));
  return out;
}

export function send(res, code, data) {
  res.statusCode = code;
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Cache-Control', 'no-store');
  res.end(JSON.stringify(data));
}

export async function readBody(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  let s = ''; for await (const c of req) s += c;
  return s ? JSON.parse(s) : {};
}

// Storage bytes in and out (used by the posting step).
export async function download(path) {
  const r = await fetch(`${URL}/storage/v1/object/${BUCKET}/${path}`, { headers: { apikey: KEY, Authorization: `Bearer ${KEY}` } });
  if (!r.ok) throw new Error(`download ${path}: ${r.status}`);
  return Buffer.from(await r.arrayBuffer());
}
export async function upload(path, bytes, type) {
  const r = await fetch(`${URL}/storage/v1/object/${BUCKET}/${path}`, {
    method: 'POST', body: bytes, headers: { apikey: KEY, Authorization: `Bearer ${KEY}`, 'Content-Type': type, 'x-upsert': 'true' }
  });
  if (!r.ok) throw new Error(`upload ${path}: ${r.status} ${(await r.text()).slice(0, 200)}`);
  return path;
}

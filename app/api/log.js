// POST /api/log: the app reports a playback failure here, so the real cause shows in the Vercel logs.
import { send, readBody } from './_sb.js';

export default async function handler(req, res) {
  if (req.method !== 'POST') return send(res, 405, { error: 'POST only' });
  try { const b = await readBody(req); console.error('client', JSON.stringify(b).slice(0, 1500)); } catch {}
  send(res, 200, { ok: true });
}

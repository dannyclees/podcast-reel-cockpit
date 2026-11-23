// Edge gate: one password. Protects every page AND the API.
export const config = { matcher: ['/((?!_vercel|favicon.ico).*)'] };

export default function middleware(request) {
  const USER = process.env.SITE_USER || 'owner';
  const PASS = process.env.SITE_PASSWORD;

  // Fails CLOSED: this app holds unposted Shorts and a service key.
  if (!PASS) return new Response('Not configured.', { status: 503, headers: { 'Cache-Control': 'no-store' } });

  const header = request.headers.get('authorization') || '';
  if (header.startsWith('Basic ')) {
    let decoded = '';
    try { decoded = atob(header.slice(6)); } catch { decoded = ''; }
    const i = decoded.indexOf(':');
    const user = i === -1 ? '' : decoded.slice(0, i);
    const pass = i === -1 ? '' : decoded.slice(i + 1);
    if (pass === PASS && (user === USER || user === '')) return;
  }

  return new Response('Authentication required.', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="Shorts Review", charset="UTF-8"',
      'Cache-Control': 'no-store'
    }
  });
}

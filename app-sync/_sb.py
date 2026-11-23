"""Shared Supabase access for app-sync. Keys live in the kit's .env (never printed). App URL and bucket come from brand.json."""
import json, sys, urllib.request, urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'pipeline'))
import brand  # noqa: E402

BUCKET = brand.BRAND['app']['bucket']
APP_URL = (brand.BRAND['app'].get('url') or '').rstrip('/')

E = brand.env()
URL, KEY = E.get('SUPABASE_URL'), E.get('SUPABASE_SERVICE_KEY')


def _req(method, url, data=None, headers=None):
    if not (URL and KEY):
        raise SystemExit('No SUPABASE_URL or SUPABASE_SERVICE_KEY in .env. Run /shorts-setup.')
    h = {'apikey': KEY, 'Authorization': f'Bearer {KEY}'}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            body = r.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f'Supabase {method} {url.split("?")[0]} failed: {e.code} {e.read()[:300]!r}')
    except urllib.error.URLError as e:
        raise SystemExit(f'Could not reach Supabase: {e.reason}. Check SUPABASE_URL in .env and your connection.')


def rest(path, method='GET', body=None, prefer=None):
    h = {'Content-Type': 'application/json'}
    if prefer:
        h['Prefer'] = prefer
    data = None if body is None else json.dumps(body).encode()
    return _req(method, f'{URL}/rest/v1/{path}', data, h)


def upload(local, path, ctype):
    data = Path(local).read_bytes()
    _req('POST', f'{URL}/storage/v1/object/{BUCKET}/{path}', data,
         {'Content-Type': ctype, 'x-upsert': 'true', 'cache-control': 'max-age=31536000'})
    return path

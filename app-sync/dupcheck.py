#!/usr/bin/env python3
"""Same post twice on one of your channels? Asks Buffer through the app. Exit 1 if it finds any. Sends nothing.

  python3 app-sync/dupcheck.py
"""
import base64, json, sys, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sb import E, APP_URL  # noqa: E402

# Buffer keeps its records for ever: list the ids of old doubles you have already dealt with here, so they stop showing as new.
KNOWN = set()
if not APP_URL:
    sys.exit('No app.url in brand.json yet.')
AUTH = 'Basic ' + base64.b64encode(f"{E.get('SITE_USER', '')}:{E.get('SITE_PASSWORD', '')}".encode()).decode()
req = urllib.request.Request(APP_URL + '/api/post', data=json.dumps({'op': 'duplicates'}).encode(),
                             headers={'Authorization': AUTH, 'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req, timeout=120) as r:
    d = json.load(r)
new = [g for g in d['duplicates'] if not KNOWN & {x['id'] for x in g}]
print(f"checked {d['checked']} posts, {len(d['waiting'])} waiting in Buffer, {len(new)} newly doubled, {len(d['duplicates']) - len(new)} old")
for w in d['waiting']:
    print(f"  waiting  {w['platform']:9} {w['due']}  {w['text']}")
for group in new:
    print(f"  DOUBLED  {group[0]['platform']}: {group[0]['text']}")
    for x in group:
        print(f"    {x['status']:9} {x['sent'] or x['due']}  {x['url']}")
sys.exit(1 if new else 0)

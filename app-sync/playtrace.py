#!/usr/bin/env python3
"""Play traces from the review app: each click on a video, step by step (click, startPlayer, video events, after 5 s).

  python3 app-sync/playtrace.py            # last 10 attempts, newest first
  python3 app-sync/playtrace.py -n 30
  python3 app-sync/playtrace.py --real     # skip headless test browsers
"""
import argparse, sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sb import rest  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('-n', type=int, default=10)
ap.add_argument('--real', action='store_true')
a = ap.parse_args()
rows = rest('shorts_trace?select=at,trace_id,ua,build,layout,age_min,events&order=at.asc&limit=2000')
runs = OrderedDict()
for r in rows:
    if a.real and 'Headless' in (r['ua'] or ''):
        continue
    runs.setdefault(r['trace_id'], []).append(r)
for tid, parts in list(runs.items())[-a.n:][::-1]:
    h = parts[0]
    browser = next((b for b in ('Brave', 'Edg/', 'Chrome/', 'Safari/', 'Firefox/') if b in (h['ua'] or '')), '?').strip('/')
    print(f"{h['at'][:19].replace('T', ' ')} UTC  {tid}  {browser}  layout {h['layout']}  build {(h['build'] or '')[:12]}  tab age {h['age_min']} min")
    for p in parts:
        for e in p['events']:
            extra = {k: v for k, v in e.items() if k not in ('ev', 'ms')}
            print(f"    {e['ms']:>6} ms  {e['ev']:<18} {extra if extra else ''}")
    print()

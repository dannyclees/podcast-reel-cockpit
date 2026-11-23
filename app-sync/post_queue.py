#!/usr/bin/env python3
"""Post queue for the review app: wait for each fixed version, then approve it and book it in Buffer
(the platforms in brand.json posting.platforms) for its slot. Runs until something happens, prints it, and exits, so the caller can report it.

  python3 app-sync/post_queue.py           # watch the queue in app-sync/post_queue.json
  python3 app-sync/post_queue.py --show    # print the queue and stop

Queue entry: {"id": "<episode>/<id>", "label": "v2", "due": "<UTC ISO>" | "asap", "state": "waiting|scheduled|posted|failed"}
Rules: only the round whose label starts with "label" is posted. If it is not in the app 30 min before its slot,
the slot moves 1 h later (and again, until it lands). Uses the live app API, so every step is logged in the app.
"""
import base64, datetime, json, re, sys, time, urllib.parse, urllib.request, urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sb import E, APP_URL, rest, brand  # noqa: E402

Q = Path(__file__).resolve().parent / 'post_queue.json'
AUTH = 'Basic ' + base64.b64encode(f"{E.get('SITE_USER', '')}:{E.get('SITE_PASSWORD', '')}".encode()).decode()
POSTING = brand.BRAND['posting']
ALWAYS = POSTING.get('always_tags', [])
CTA = POSTING.get('cta_line', '')
PLATS = tuple(POSTING.get('platforms', ()))
TZ = brand.timezone()
UTC = datetime.timezone.utc


def api(path, body=None):
    req = urllib.request.Request(APP_URL + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Authorization': AUTH, 'Content-Type': 'application/json'}, method='GET' if body is None else 'POST')
    try:
        with urllib.request.urlopen(req, timeout=290) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {'error': f'{e.code} {e.read()[:300].decode(errors="replace")}'}


def caption(it, ep):
    """Same as postCopy() in public/app.js: one caption for every platform, the full-episode line, then the tags."""
    c = it.get('copy') or {}
    base = c.get('caption') or c.get('instagram_caption') or c.get('tiktok_caption') or c.get('youtube_description') or ''
    base = re.sub(r'(^|\s)#\w+', r'\1', base)
    base = re.sub(r'^.*(\{FULL_EPISODE_LINK\}|link in bio).*$', '', base, flags=re.M | re.I)
    base = re.sub(r'[ \t]+$', '', base, flags=re.M)
    base = re.sub(r'\n{3,}', '\n\n', base).strip()
    tags = ALWAYS + [t for t in c.get('hashtags') or [] if t.lower() not in {a.lower() for a in ALWAYS}]
    url = ep.get('full_url') or ''
    text = f"{base}\n\n{f'{CTA} {url}' + chr(10) * 2 if url else ''}{' '.join(tags)}"
    return {p: ({'title': c.get('youtube_title') or it['title'], 'text': text} if p == 'youtube' else {'text': text}) for p in PLATS}


def clock(dt):
    """A UTC instant as the app's {day, min} on the show's clock (brand.json posting.timezone)."""
    t = dt.astimezone(TZ)
    return {'day': t.date().isoformat(), 'min': t.hour * 60 + t.minute}


def when(iso):
    return datetime.datetime.fromisoformat(iso).astimezone(TZ).strftime(f'%a %d %b %H:%M {TZ.key}')


def save(q):
    Q.write_text(json.dumps(q, indent=1))


def step(q):
    now = datetime.datetime.now(UTC)
    d = api('/api/data')
    if 'error' in d:
        return None
    items = {i['id']: i for i in d['items']}
    eps = {e['id']: e for e in d['episodes']}
    vers = {(v['short_id'], v['round']): v for v in d['versions']}
    if any(e['state'] == 'scheduled' for e in q):
        s = api('/api/post', {'op': 'sync'})
        for it in s.get('items', []):
            items[it['id']] = it
    for e in q:
        it = items.get(e['id'])
        if not it:
            continue
        if e['state'] == 'waiting':
            # The version to post is named exactly ("v2 A"); a bare "v2" also matches a lone "v11 ..." but never one of several.
            mine = [v for (sid, _), v in vers.items() if sid == it['id']]
            norm = lambda x: ' '.join((x or '').lower().split())
            if e.get('note'):   # e.g. a rule number: the newest round whose change note carries it
                hits = sorted([v for v in mine if e['note'].lower() in (v.get('change_note') or '').lower()], key=lambda v: v['round'])[-1:]
            elif e.get('pin_round'):
                hits = [v for v in mine if v['round'] == e['pin_round']]
            else:
                hits = [v for v in mine if norm(v['round_label']) == norm(e['label'])] or [v for v in mine if norm(v['round_label']).startswith(norm(e['label']) + ' ')]
            if len(hits) > 1 and not e.get('warned'):
                e['warned'] = 1; save(q)
                return f"UNCLEAR {e['id']}: several versions match \"{e['label']}\" ({', '.join(v['round_label'] for v in hits)}). Nothing booked; say which one."
            v = hits[0] if len(hits) == 1 else {}
            ready = bool(v.get('master_path'))
            due = now + datetime.timedelta(minutes=8) if e['due'] == 'asap' else datetime.datetime.fromisoformat(e['due'])
            if not ready:
                if e['due'] != 'asap' and now > due - datetime.timedelta(minutes=30):
                    e['due'] = (due + datetime.timedelta(hours=1)).isoformat()
                    e.setdefault('pushed', 0); e['pushed'] += 1
                    save(q)
                    return f"PUSHED {e['id']}: {e['label']} is not in the app yet (latest is {it.get('round_label')}). New slot {when(e['due'])}."
                continue
            due = max(due, now + datetime.timedelta(minutes=8))
            if it['status'] == 'draft':
                r = api('/api/act', {'op': 'approve', 'id': it['id'], 'on': True})
                if 'error' in r:
                    e['state'] = 'failed'; e['error'] = r['error']; save(q)
                    return f"FAILED {e['id']}: could not approve: {r['error']}"
                it = r['item']
            ep = eps[it['episode_id']]
            r = api('/api/post', {'op': 'schedule', 'id': it['id'], 'round': v['round'], 'force': True, 'platforms': list(PLATS),
                                  'due': {p: clock(due) for p in PLATS}, 'copy': caption(it, ep)})
            it = (r.get('items') or [it])[-1]
            states = {p: (it.get('posted') or {}).get(p, {}) for p in PLATS}
            bad = {p: s.get('error') for p, s in states.items() if s.get('state') != 'scheduled'}
            e['due'] = due.isoformat(); e['round'] = v['round']; e['round_label'] = v['round_label']; e['track'] = it.get('track'); e['sfx'] = it.get('sfx')
            if bad or 'error' in r:
                e['state'] = 'failed'; e['error'] = r.get('error') or bad; save(q)
                return f"FAILED {e['id']}: {e['error']}"
            e['state'] = 'scheduled'; save(q)
            if it.get('hold'):
                rest(f"shorts_items?id=eq.{urllib.parse.quote(it['id'], safe='')}", 'PATCH', {'hold': None})
            return (f"SCHEDULED {e['id']} {v['round_label']} (round {v['round']}, music {it.get('track') or 'none'}, "
                    f"SFX {'on' if it.get('sfx') is not False else 'off'}) in Buffer for {when(e['due'])} on {', '.join(PLATS)}.")
        if e['state'] == 'scheduled' and e.get('swap_until') and it['round'] > e.get('round', 0):
            # A newer round landed after booking. Before swap_until: rebook the same slot with it. After: keep the booked one.
            v = vers.get((it['id'], it['round'])) or {}
            if now < datetime.datetime.fromisoformat(e['swap_until']) and v.get('master_path'):
                for p in PLATS:
                    r = api('/api/post', {'op': 'cancel', 'id': it['id'], 'platform': p})
                    if 'error' in r:
                        e['state'] = 'failed'; e['error'] = f'swap: cancel {p}: {r["error"]}'; save(q)
                        return f"FAILED {e['id']}: {e['error']} (the old booking may still be in Buffer)"
                old = e['round']; e['state'] = 'waiting'; e['label'] = it.get('round_label') or e['label']; e.pop('swap_until')
                save(q)
                return f"SWAP {e['id']}: round {it['round']} ({it.get('round_label')}) landed; the round {old} posts are cancelled in Buffer and it books again for {when(e['due'])}."
            if now >= datetime.datetime.fromisoformat(e['swap_until']):
                e.pop('swap_until'); save(q)
                return f"KEPT {e['id']}: no newer round before the cut-off, so round {e['round']} stays booked for {when(e['due'])}."
        if e['state'] == 'scheduled':
            st = {p: (it.get('posted') or {}).get(p, {}) for p in PLATS}
            if any(s.get('state') == 'failed' for s in st.values()):
                e['state'] = 'failed'; e['error'] = {p: s.get('error') for p, s in st.items() if s.get('state') == 'failed'}; save(q)
                return f"FAILED {e['id']}: {e['error']}"
            if all(s.get('state') == 'posted' for s in st.values()):
                e['state'] = 'posted'; e['links'] = {p: s.get('url') for p, s in st.items()}; save(q)
                return f"POSTED {e['id']}: " + ' · '.join(f'{p} {u}' for p, u in e['links'].items())
    return None


def main():
    q = json.loads(Q.read_text())
    if '--show' in sys.argv:
        for e in q:
            print(e['id'], e['label'], e['state'], e['due'] if e['due'] == 'asap' else when(e['due']), e.get('error', ''), e.get('links', ''))
        return
    while any(e['state'] in ('waiting', 'scheduled') for e in q):
        msg = step(q)
        if msg:
            print(msg)
            return
        time.sleep(60)
    print('QUEUE DONE')


if __name__ == '__main__':
    main()

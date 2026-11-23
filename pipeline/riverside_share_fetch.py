#!/usr/bin/env python3
"""riverside_share_fetch.py <recording-id> [--out episodes/ep-MMDD/raw] [--dry] [--only <id>_raw.wav,...]: one Riverside recording -> raw/ with no browser.

Uses the studio share link, not the Business API (riverside_fetch.py needs a Business key).
.env holds RIVERSIDE_SHARE_KEY= (read it off a recording share link) and RIVERSIDE_STUDIO_SLUG= (the slug in your studio's URL).
The link carries the key as its share-token parameter. The value is never printed.
  POST /api/v4/studio/{slug}/takes/find                    {sessionIds:[id]} -> tracks, each with archiveId + file ids
  GET  /api/v4/recordingfile/{file}/download?t=TOKEN       302 to a signed media.riverside.com file (raw .wav / .mp4 / .mp3)
  GET  /recordings-service/recordings/alignedTrackDownloadUrl?archiveId=A&share-token=TOKEN
                                                           {url} = signed "Aligned video" (-CFR.mp4). The -CFR.mp4 file id
                                                           itself gives 403. url null -> POST generateAlignedTracks, poll getRecording.
Writes raw/<id>_raw.wav and raw/<id>.mp4 per person (ids from brand.json, matched on people[].riverside_track), raw/screen.mp4 (aligned video) and raw/recording.json.
Downloads resume (curl -C -) and files whose size already matches are skipped. Then run ingest.py and align_audio.py.
--dry resolves every URL and prints what it would do, writing nothing. --only fetches just the named files (no recording.json).
"""
import argparse, json, os, re, subprocess, sys, time, urllib.parse, urllib.request
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand

BASE = 'https://riverside.com'
ROOT = str(brand.ROOT)
UA = 'Mozilla/5.0'


def env():
    e = brand.env(); key, slug = e.get('RIVERSIDE_SHARE_KEY'), e.get('RIVERSIDE_STUDIO_SLUG')
    if not (key and slug): sys.exit('Need RIVERSIDE_SHARE_KEY and RIVERSIDE_STUDIO_SLUG in .env')
    return key, slug


TOKEN, SLUG = env()


def call(path, body=None, method=None):
    req = urllib.request.Request(BASE + path, method=method or ('POST' if body is not None else 'GET'),
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json', 'User-Agent': UA,
                                          'x-studio-share-token': TOKEN, 'x-studio-slug': SLUG})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f'{method or "GET"} {path.split("?")[0]} -> HTTP {e.code} (share token revoked or expired? make a new share link)')


def role(name):
    n = (name or '').lower()
    if 'screen' in n: return 'screen'
    for p in brand.PEOPLE:
        for key in (p.get('riverside_track'), p.get('name')):
            if key and key.lower() in n: return p['id']
    return None


def file_url(fid):
    """Signed URL behind a recording file id (follows the 302 without downloading)."""
    q = urllib.parse.quote(TOKEN)
    r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-A', UA, '-w', '%{http_code} %{redirect_url}',
                        f'{BASE}/api/v4/recordingfile/{fid}/download?t={q}'], capture_output=True, text=True).stdout.split(' ', 1)
    return r[1].strip() if r[0] == '302' else None


def aligned_url(archive, dry):
    q = urllib.parse.urlencode({'archiveId': archive, 'share-token': TOKEN})
    u = call(f'/recordings-service/recordings/alignedTrackDownloadUrl?{q}').get('url')
    if u or dry: return u
    print(f'  {archive}: aligned track not made yet, asking Riverside to make it')
    r = call(f'/recordings-service/recordings/generateAlignedTracks?{q}', body={})
    if r.get('success') is not True: sys.exit(f'generateAlignedTracks failed: {r}')
    for _ in range(360):                                   # up to 30 min, like the share page (5 s steps)
        time.sleep(5)
        st = (call(f'/recordings-service/recordings/getRecording?{q}').get('alignedTrack') or {}).get('status')
        if st != 'processing': break
    return call(f'/recordings-service/recordings/alignedTrackDownloadUrl?{q}').get('url')


def remote_size(url):
    h = subprocess.run(['curl', '-s', '-r', '0-0', '-D', '-', '-o', '/dev/null', url], capture_output=True, text=True).stdout
    m = re.search(r'content-range: bytes 0-0/(\d+)', h, re.I)
    return int(m.group(1)) if m else None


def probe(f):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], capture_output=True, text=True)
    return float(r.stdout or 0)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('recording'); ap.add_argument('--out'); ap.add_argument('--dry', action='store_true'); ap.add_argument('--only')
    a = ap.parse_args()
    takes = call(f'/api/v4/studio/{urllib.parse.quote(SLUG)}/takes/find', body={'sessionIds': [a.recording], 'limit': 1}).get('takes') or []
    if not takes: sys.exit(f'No recording {a.recording} in studio {SLUG}')
    t = takes[0]; doc = t.get('_doc', t)
    when = datetime.fromisoformat(doc['createdAt'].replace('Z', '+00:00')).astimezone()
    out = a.out or os.path.join(ROOT, 'episodes', f'ep-{when:%m%d}', 'raw')
    print(f'{doc.get("name")} | {when:%d %b %Y %H:%M} | {doc.get("calculatedDuration", 0) / 60:.1f} min -> {out}')

    jobs, tracks = [], []                                  # (dest name, url)
    recs = [r.get('_doc', r) for r in doc.get('recordings') or t.get('recordings') or []]   # takes[0].recordings are wrapped mongoose docs
    # a joke name in the studio matches no host: give it the one host role nobody else has
    people = {r.get('speakerName') for r in recs if r.get('kind') == 'participant'}
    known = {role(n) for n in people} - {None}
    unknown = [n for n in people if not role(n)]
    left = set(brand.IDS) - known
    guess = {unknown[0]: left.pop()} if len(unknown) == 1 and len(left) == 1 else {}
    for n, g in guess.items(): print(f'  speaker "{n}" -> {g} (only host left)')
    for r in recs:
        rl = role(r.get('speakerName')) or (guess.get(r.get('speakerName')) if r.get('kind') == 'participant' else None)
        if r.get('kind') not in ('participant', 'screenshare') or not rl: continue
        tracks.append({'role': rl, 'speaker': r.get('speakerName'), 'kind': r.get('kind'), 'archiveId': r.get('archiveId'),
                       'resolution': r.get('resolution'), 'duration': r.get('duration')})
        if rl != 'screen':
            wav = next((u for u in map(file_url, r.get('files') or []) if u and urllib.parse.urlparse(u).path.endswith('.wav')), None)
            jobs.append((f'{rl}_raw.wav', wav))
        jobs.append((f'{rl}.mp4', aligned_url(r['archiveId'], a.dry)))

    for name, url in jobs:
        dest = os.path.join(out, name); size = remote_size(url) if url else None
        have = os.path.getsize(dest) if os.path.exists(dest) else 0
        state = 'NO URL' if not url else 'complete, skip' if size and have == size else f'{have}/{size} bytes here' if have else 'to fetch'
        host = urllib.parse.urlparse(url).netloc if url else '-'
        print(f'  {name:14s} {(size or 0) / 1e6:7.1f} MB  {host:40s} {state}')
    if a.dry: return
    if a.only: jobs = [j for j in jobs if j[0] in a.only.split(',')]
    if any(u is None for _, u in jobs): sys.exit('Some files had no URL, stopping (see NO URL above).')

    os.makedirs(out, exist_ok=True)
    for name, url in jobs:
        dest = os.path.join(out, name); size = remote_size(url)
        if size and os.path.exists(dest) and os.path.getsize(dest) == size: continue
        if subprocess.run(['curl', '-sS', '-L', '--fail', '-C', '-', '-o', dest, url]).returncode != 0:
            sys.exit(f'{name}: download failed (rerun to resume)')
    if not a.only: json.dump({'recording_id': a.recording, 'title': doc.get('name'), 'date': when.isoformat(), 'studio': SLUG,
               'duration': doc.get('calculatedDuration'), 'tracks': tracks}, open(os.path.join(out, 'recording.json'), 'w'), indent=1)
    for name, _ in jobs:
        f = os.path.join(out, name); print(f'  {name:14s} {os.path.getsize(f) / 1e6:7.1f} MB  {probe(f):8.1f} s')


if __name__ == '__main__':
    main()

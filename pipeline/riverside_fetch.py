#!/usr/bin/env python3
"""riverside_fetch.py [--project NAME] [--recording ID] [--out episodes/]: newest Riverside recording -> episodes/<date>/raw/

Riverside Business API v3 (docs.riverside.fm). Key: RIVERSIDE_API_KEY in the kit's .env (never printed).
Keys are only issued to Business accounts, by the Riverside customer success manager.
  GET https://platform.riverside.com/api/v3/recordings            newest first, 20 a page, 1 request/s
  GET https://platform.riverside.com/api/v3/recordings/{id}       tracks[] -> files[] {type: raw_audio|raw_video|cloud_recording, download_url}
  GET {download_url}                                              301 to a signed file URL (curl -L)
Writes raw/<role>.mp4 (raw video), raw/<role>_raw.wav (raw audio), raw/screen.mp4, raw/all.mp4 (cloud mix, the sync reference)
and raw/recording.json. Roles come from the track / file names (people[].riverside_track in brand.json, screen). Then run ingest.py and align_audio.py.
Raw tracks start when each person's local recording started: align_audio.py lines them up on the cloud mix.
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand

API = 'https://platform.riverside.com/api/v3'


def key():
    k = brand.env().get('RIVERSIDE_API_KEY')
    if not k: sys.exit('No RIVERSIDE_API_KEY in .env (Business plan: ask your Riverside success manager for one).')
    return k


def get(url):
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {key()}'})
    with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)


def role(name):
    n = (name or '').lower()
    if 'screen' in n: return 'screen'
    for p in brand.PEOPLE:
        for key in (p.get('riverside_track'), p.get('name')):
            if key and key.lower() in n: return p['id']
    if 'all' in n: return 'all'
    return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--project'); ap.add_argument('--recording'); ap.add_argument('--out', default=str(brand.EPISODES))
    a = ap.parse_args()
    if a.recording: rec = get(f'{API}/recordings/{a.recording}')
    else:
        recs = get(f'{API}/recordings')['data']
        if a.project: recs = [r for r in recs if a.project.lower() in (r.get('project_name') or '').lower()]
        if not recs: sys.exit('No recordings found.')
        rec = get(f"{API}/recordings/{recs[0]['recording_id']}"); time.sleep(1)
    day = (rec.get('created_date') or '')[:10].replace('-', '') or time.strftime('%Y%m%d')
    R = os.path.join(a.out, f'ep-{day}', 'raw'); os.makedirs(R, exist_ok=True)
    json.dump(rec, open(os.path.join(R, 'recording.json'), 'w'), indent=1)
    want = {'raw_video': '{r}.mp4', 'raw_audio': '{r}_raw.wav', 'cloud_recording': '{r}.mp4'}
    for t in rec['tracks']:
        r = 'all' if t['type'] == 'all_participants' else 'screen' if t['type'] == 'screenshare' else role(t.get('track_name') or ' '.join(f['name'] for f in t['files']))
        if not r: print('skipped a track with no recognisable name:', [f['name'] for f in t['files']]); continue
        for f in t['files']:
            if f['type'] not in want or (r == 'all') != (f['type'] == 'cloud_recording'): continue
            dst = os.path.join(R, want[f['type']].format(r=r))
            if os.path.exists(dst) and os.path.getsize(dst) == f.get('size'): continue
            print(f"downloading {r} {f['type']} ({f.get('size', 0) / 1e6:.0f} MB) -> {dst}")
            subprocess.run(['curl', '-sSL', '--fail', '-H', f'Authorization: Bearer {key()}', '-o', dst, f['download_url']], check=True)
    print('done ->', R)


if __name__ == '__main__':
    main()

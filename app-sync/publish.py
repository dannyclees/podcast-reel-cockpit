#!/usr/bin/env python3
"""Publish finished Shorts into the approval app.

  python3 app-sync/publish.py <episode> <short-id> [<short-id> ...] [options]
  python3 app-sync/publish.py --board boards/<date>/shorts.json [--only <episode>/<id>,...] [options]

Per Short it uploads: a web copy of the final mp4 (H.264 720x1280, faststart, about 5 MB), the full-quality final
(master.mp4, under 48 MB, used for posting: the app joins it with the chosen music mix),
a poster frame, one music-bed mix per track in brand.json "music" (<id>_t1/_t2/_t3.m4a; 0 tracks is fine), optional SFX mixes (<id>_sfx.m4a,
<id>_t1_sfx.m4a ... for the app's SFX switch) and the post copy from research/descriptions/<episode>.json.
Publishing a Short again makes a new round: the old round stays in History, the status goes back to Draft
(unless it is already Posted), and --note is logged as "what we changed".

Options:
  --dir DIR        folder with <id>.mp4 + <id>_t1.m4a ... (default: newest episodes/<ep>/v*/ that has <id>.mp4)
  --title TEXT     title (one Short only; default: board title, else the spec opener title, else youtube_title)
  --label TEXT     round label shown in the app (default: the folder name, e.g. "v10")
  --note TEXT      what changed in this round and why (shown in History)
  --round N        force the round number (default: last round + 1, or 1)
  --episode-title  episode title (default: the people in brand.json)
  --dry            encode only, upload nothing
  --copy-only      refresh the post copy and hashtags only (no new version)
  --master-only    upload master.mp4 for the current version only (no new version)

Hashtags: the app always adds brand.json posting.always_tags; the 3-5 topic tags come from "hashtags" in
research/descriptions/<ep>.json, else app-sync/hashtags.json, else the copy's own tags.
Versions: each publish of a Short is the next version (V1, V2, ...). Older versions stay playable in the app.
"""
import argparse, datetime, html, json, re, subprocess, sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _sb import rest, upload, APP_URL, brand  # noqa: E402
from _sb import E as SB_ENV  # noqa: E402


def warm_play(full_id, rnd, keys):
    """Make the app's play files (video + each mix) now, so the first click plays at once.
    Made on first click it takes ~6 s: the app says "Not playing" at 4 s and the next click pauses it."""
    import base64, urllib.request
    if not APP_URL or not keys:
        return
    auth = base64.b64encode(f"{SB_ENV.get('SITE_USER', '')}:{SB_ENV.get('SITE_PASSWORD', '')}".encode()).decode()
    bad = []
    for k in keys:
        req = urllib.request.Request(f'{APP_URL}/api/play', json.dumps({'id': full_id, 'round': rnd, 'key': k}).encode(),
                                     {'Content-Type': 'application/json', 'Authorization': f'Basic {auth}'})
        try:
            urllib.request.urlopen(req, timeout=90).read()
        except Exception as e:  # the app still makes it on first click
            bad.append(f'{k} ({e})')
    print(f'  play files: {len(keys) - len(bad)} of {len(keys)} ready' + (f', failed {bad}' if bad else ''))

CACHE = ROOT / 'app-sync/cache'


def enc(s):
    return quote(s, safe='')


def ep_date(ep):
    m = re.match(r'ep-(\d{2})(\d{2})$', ep)
    if not m:
        return None
    return f'{datetime.date.today().year}-{m[1]}-{m[2]}'


def newest_dir(ep, sid):
    dirs = [d for d in (ROOT / 'episodes' / ep).glob('v*') if (d / f'{sid}.mp4').exists()]
    if not dirs:
        raise SystemExit(f'No episodes/{ep}/v*/{sid}.mp4 found. Pass --dir.')
    return max(dirs, key=lambda d: (d / f'{sid}.mp4').stat().st_mtime)


def spec_title(d, sid):
    f = d / f'{sid}.json'
    if not f.exists():
        return None
    t = (json.loads(f.read_text()).get('opener') or {}).get('title')
    if not t:
        return None
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    t = re.sub(r'\s+', ' ', t).strip()
    return None if t.isupper() else t   # an ALL-CAPS opener title loses the casing of names: use youtube_title instead


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)


def web_copy(src, dst):
    if dst.exists() and dst.stat().st_mtime > src.stat().st_mtime:
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    dur = probe(src) or 60
    kbps = max(450, min(1100, int(5 * 8 * 1024 / dur) - 96))   # aim for about 5 MB
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(src),
                    '-vf', 'scale=720:1280:flags=lanczos', '-c:v', 'libx264', '-preset', 'slow', '-profile:v', 'high',
                    '-pix_fmt', 'yuv420p', '-b:v', f'{kbps}k', '-maxrate', f'{int(kbps * 1.6)}k', '-bufsize', f'{kbps * 2}k',
                    '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', str(dst)], check=True)
    return dst


def master_copy(src, dst, cap_mb=48):
    """The full-quality final for posting: stream copy with faststart, re-encoded only if it is over cap_mb."""
    if dst.exists() and dst.stat().st_mtime > src.stat().st_mtime:
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.stat().st_size <= cap_mb * 1e6:
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(src), '-c', 'copy', '-movflags', '+faststart', str(dst)], check=True)
        return dst
    kbps = int(cap_mb * 0.95 * 8 * 1000 / (probe(src) or 60)) - 200
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(src), '-c:v', 'libx264', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                    '-b:v', f'{kbps}k', '-maxrate', f'{int(kbps * 1.3)}k', '-bufsize', f'{kbps * 2}k',
                    '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(dst)], check=True)
    return dst


def upload_master(ep, sid, video, rnd):
    """Upload master.mp4 for one version and record it."""
    m = master_copy(Path(video), CACHE / ep / f'{sid}-r{rnd}-master.mp4')
    path = upload(m, f'{ep}/{sid}/r{rnd}/master.mp4', 'video/mp4')
    rest(f'shorts_versions?short_id=eq.{enc(ep + "/" + sid)}&round=eq.{rnd}', 'PATCH', {'master_path': path})
    print(f'  {ep}/{sid} r{rnd}: master {m.stat().st_size / 1e6:.1f} MB')
    return path


def poster(src, dst):
    if dst.exists() and dst.stat().st_mtime > src.stat().st_mtime:
        return dst
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', '1.2', '-i', str(src), '-frames:v', '1',
                    '-vf', 'scale=540:960', '-q:v', '4', str(dst)], check=True)
    return dst


COPY_KEYS = ('youtube_title', 'caption', 'youtube_description', 'tiktok_caption', 'instagram_caption')   # 'caption' = the one shared caption (the app falls back to instagram_caption)
TRACK_KEYS = [t['key'] for t in brand.tracks()]   # 0 to 3
GENERIC = {'#podcast', '#' + re.sub(r'\W', '', brand.SHOW['name']).lower(), *(t.lower() for t in brand.BRAND['posting'].get('always_tags', []))}


def topic_tags(full_id, d):
    """3-5 topic hashtags. Order: "hashtags" in the description json, app-sync/hashtags.json, else the copy's own tags."""
    if d.get('hashtags'):
        return d['hashtags'][:5]
    hf = ROOT / 'app-sync/hashtags.json'
    table = json.loads(hf.read_text()) if hf.exists() else {}
    if full_id in table:
        return table[full_id][:5]
    seen = []
    for k in COPY_KEYS:
        for t in re.findall(r'#\w+', d.get(k, '')):
            if t.lower() not in GENERIC and t.lower() not in [x.lower() for x in seen]:
                seen.append(t)
    return seen[:5]


def desc_for(ep, key):
    f = ROOT / 'research/descriptions' / f'{ep}.json'
    if not f.exists():
        return {}
    d = json.loads(f.read_text()).get(key) or {}
    out = {k: d[k] for k in COPY_KEYS if d.get(k)}
    out['hashtags'] = topic_tags(f'{ep}/{key}', d)
    return out


def publish_one(ep, sid, d, title=None, label=None, note=None, rnd=None, num=None, ep_title=None, dry=False,
                video=None, tracks=None, copy=None):
    video = Path(video) if video else d / f'{sid}.mp4'
    ep_title = ep_title or ' + '.join(brand.first_names())
    tracks = tracks or {k: d / f'{sid}_{k}.m4a' for k in TRACK_KEYS}
    # Optional sound-effect mixes for the app's SFX switch: <id>_sfx.m4a (no music) and <id>_t1_sfx.m4a ...
    sfx = {'sfx_none': video.parent / f'{sid}_sfx.m4a', **{f'sfx_{k}': video.parent / f'{sid}_{k}_sfx.m4a' for k in TRACK_KEYS}}
    tracks = {**tracks, **sfx}
    tracks = {k: Path(p) for k, p in tracks.items() if p and Path(p).exists()}
    copy = copy if copy is not None else desc_for(ep, sid)
    title = title or spec_title(d, sid) or copy.get('youtube_title') or sid
    label = label or d.name
    full_id = f'{ep}/{sid}'

    existing = rest(f'shorts_items?id=eq.{enc(full_id)}&select=*') if not dry else None   # --dry touches no network, so it works before the app exists
    item = existing[0] if existing else None
    if item and item['status'] == 'scheduled' and not dry:   # the old round is still booked in Buffer and would post
        raise SystemExit(f'{full_id} is scheduled. Cancel it in the app first, then publish the new round.')
    if rnd is None:
        last = rest(f'shorts_versions?short_id=eq.{enc(full_id)}&select=round&order=round.desc&limit=1') if not dry else None
        rnd = (last[0]['round'] + 1) if last else 1
    if rnd > 1 and not (note or '').strip():   # R125: every re-edit shows what changed under the Short
        raise SystemExit(f'{full_id}: round {rnd} needs --note (what changed and why)')

    web = web_copy(video, CACHE / ep / f'{sid}-r{rnd}.mp4')
    post = poster(web, CACHE / ep / f'{sid}-r{rnd}.jpg')
    mb = web.stat().st_size / 1e6
    print(f'  {full_id} round {rnd} ({label}): web copy {mb:.1f} MB, {len(tracks)} tracks, title "{title}"')
    if dry:
        return

    rest('shorts_episodes', 'POST', {'id': ep, 'title': ep_title, 'recorded_on': ep_date(ep)},
         prefer='resolution=ignore-duplicates')
    base = f'{ep}/{sid}/r{rnd}'
    vpath = upload(web, f'{base}/video.mp4', 'video/mp4')
    ppath = upload(post, f'{base}/poster.jpg', 'image/jpeg')
    tpaths = {k: upload(p, f'{base}/{k}.m4a', 'audio/mp4') for k, p in tracks.items()}   # keys: t1..t3, sfx_none, sfx_t1..

    row = {'id': full_id, 'episode_id': ep, 'title': title, 'round': rnd, 'round_label': label, 'copy': copy,
           'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if num is not None:
        row['num'] = num
    if item:
        if item['status'] != 'posted':
            row['status'] = 'draft'
        rest(f'shorts_items?id=eq.{enc(full_id)}', 'PATCH', row)
    else:
        if num is None:
            n = rest(f'shorts_items?episode_id=eq.{ep}&select=id')
            row['num'] = len(n) + 1
        rest('shorts_items', 'POST', row)
    rest('shorts_versions', 'POST', {'short_id': full_id, 'round': rnd, 'round_label': label, 'change_note': note,
                                     'video_path': vpath, 'poster_path': ppath, 'tracks': tpaths,
                                     'duration': round(probe(web), 2)},
         prefer='resolution=merge-duplicates')
    upload_master(ep, sid, video, rnd)
    warm_play(full_id, rnd, list(tpaths))
    status = (item or {}).get('status', 'draft')
    if item and status != 'posted':
        status = 'draft'
    rest('shorts_feedback', 'POST', {'episode_id': ep, 'short_id': full_id, 'kind': 'change', 'author': 'team',
                                     'body': note or f'Round {rnd} uploaded ({label}).', 'status_at': status,
                                     'round_at': rnd, 'track_at': (item or {}).get('track', 'none')})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('episode', nargs='?')
    ap.add_argument('ids', nargs='*')
    ap.add_argument('--board')
    ap.add_argument('--only')
    ap.add_argument('--dir')
    ap.add_argument('--title')
    ap.add_argument('--label')
    ap.add_argument('--note')
    ap.add_argument('--round', type=int)
    ap.add_argument('--episode-title')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--copy-only', action='store_true', help='refresh post copy + hashtags only, no new version')
    ap.add_argument('--master-only', action='store_true', help='upload master.mp4 for the current version only')
    a = ap.parse_args()

    if a.master_only:   # back-fill: the current version's folder is episodes/<ep>/<round_label>/<id>.mp4
        q = f'shorts_items?select=id,round,round_label' + (f'&episode_id=eq.{a.episode}' if a.episode else '')
        for it in rest(q):
            ep, sid = it['id'].split('/')
            if a.ids and sid not in a.ids:
                continue
            src = ROOT / 'episodes' / ep / it['round_label'] / f'{sid}.mp4'
            if not src.exists():
                print(f'  {it["id"]}: no {src.relative_to(ROOT)}, skipped')
                continue
            upload_master(ep, sid, src, it['round'])
        return

    if a.board:
        bf = (ROOT / a.board) if not Path(a.board).is_absolute() else Path(a.board)
        board = json.loads(bf.read_text())
        only = set(a.only.split(',')) if a.only else None
        per_ep = {}
        for s in board['shorts']:
            if only and s['id'] not in only:
                continue
            ep, sid = s['id'].split('/')
            per_ep[ep] = per_ep.get(ep, 0) + 1
            rel = lambda p: (bf.parent / p).resolve() if p else None
            video = rel(s['video'])
            dkey = s.get('desc_key', sid)
            copy = {}
            if s.get('desc_file'):
                d = json.loads(rel(s['desc_file']).read_text()).get(dkey) or {}
                copy = {k: d[k] for k in COPY_KEYS if d.get(k)}
                copy['hashtags'] = topic_tags(s['id'], d)
            if a.copy_only:
                rest(f'shorts_items?id=eq.{enc(s["id"])}', 'PATCH', {'copy': copy})
                print(f'  {s["id"]}: copy updated, tags {" ".join(copy["hashtags"])}')
                continue
            publish_one(ep, sid, video.parent, title=s.get('title'), label=a.label or video.parent.name,
                        note=a.note or s.get('note'), rnd=a.round, num=per_ep[ep], ep_title=a.episode_title, dry=a.dry,
                        video=video, tracks={k: rel(s.get(k)) for k in TRACK_KEYS}, copy=copy)
    else:
        if not a.episode or not a.ids:
            ap.error('give <episode> <short-id> [...] or --board')
        if a.title and len(a.ids) > 1:
            ap.error('--title works with one Short at a time')
        for sid in a.ids:
            if a.copy_only:
                copy = desc_for(a.episode, sid)
                rest(f'shorts_items?id=eq.{enc(a.episode + "/" + sid)}', 'PATCH', {'copy': copy})
                print(f'  {a.episode}/{sid}: copy updated, tags {" ".join(copy.get("hashtags", []))}')
                continue
            d = Path(a.dir) if a.dir else newest_dir(a.episode, sid)
            if not d.is_absolute():
                d = ROOT / d
            # R120-R122: no Short reaches the app until the content gate passes (the override is "content_ok" in the spec, with a reason)
            if subprocess.run([sys.executable, str(ROOT / 'pipeline/contentcheck.py'), a.episode, sid, str(d / f'{sid}.json')]).returncode:
                raise SystemExit(f'{a.episode}/{sid}: content gate FAIL, not published')
            publish_one(a.episode, sid, d, title=a.title, label=a.label, note=a.note, rnd=a.round,
                        ep_title=a.episode_title, dry=a.dry)
    print(f'Done. Open {APP_URL or "your app"}')


if __name__ == '__main__':
    main()

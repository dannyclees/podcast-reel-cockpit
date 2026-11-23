#!/usr/bin/env python3
"""ingest.py: separate tracks per person (or one finished episode file) -> a clean work folder.

usage:
  python3 ingest.py <episode dir>                  # finds <id>.mp4 (+ <id>_raw.wav) and screen.mp4 in <episode dir>/raw/
  python3 ingest.py <episode dir> --composite FILE [--regions JSON]
      one finished recording of everyone in one picture and one sound. It runs as a solo show: every word goes to the first person
      in brand.json and the Short shows their region. Regions are % of the frame [l, t, r, b], e.g. '{"screen": [5, 8, 95, 92], "a": [72, 48, 97, 95]}'.
      Default: the whole frame is the first person. Turns between people need separate tracks.

Two ways to fill raw/, brand.json recording.source says which:
  "local"      you place the files yourself: raw/<id>.mp4 for each person (ids from brand.json), optional raw/<id>_raw.wav and raw/screen.mp4.
               With no separate wav, the sound comes from the mp4.
  "riverside"  riverside_share_fetch.py or riverside_fetch.py writes the same names. Files downloaded by hand are matched on people[].riverside_track.

Writes <episode dir>/work/:
  tracks.json          which file is which, durations, sizes, offsets
  tracks/<name>.mp4    1080p proxies, all starting at the same moment
  audio/<name>.wav     16 kHz mono per speaker (for whisper + who-is-talking)
  activity.json        who is talking, 20 times a second
  speakers.json        speaking windows per speaker (hysteresis, 0.6 s minimum hold)

Each person records on their own machine, so each mic is mostly that one person.
That gives us speaker labels for free: no diarization model.
"""
import argparse, glob, json, os, re, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from brand import BRAND, IDS, PEOPLE

SR = 16000
HOP = 0.05   # 20 Hz activity grid


def probe(f):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height,r_frame_rate',
                        '-of', 'json', f], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    v = next((s for s in j['streams'] if s['codec_type'] == 'video'), None)
    a = any(s['codec_type'] == 'audio' for s in j['streams'])
    return dict(dur=float(j['format']['duration']), w=v and v['width'], h=v and v['height'], audio=a)


def role_of(n):
    """A lower-case file name -> a person id, 'screen' or None. <id>.mp4 and <id>_raw.wav first; Riverside names files
    '<recording> - <participant> ...', matched on people[].riverside_track, then on the person's name."""
    stem = os.path.splitext(n)[0]
    for p in IDS:
        if stem in (p.lower(), p.lower() + '_raw'): return p
    if re.search(r'screen|share', n): return 'screen'
    for p in PEOPLE:
        for key in (p.get('riverside_track'), p.get('name')):
            if key and key.lower() in n: return p['id']
    return None


def guess(files):
    out = {}
    for f in files:
        n = os.path.basename(f).lower()
        role = role_of(n)
        if not role: continue
        # prefer video over audio-only for the same role; keep the wav as the audio source if present
        kind = 'audio' if n.endswith(('.wav', '.m4a', '.mp3', '.aac')) else 'video'
        out.setdefault(role, {})[kind] = f
    return out


def wav(src, dst, ss=0.0):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{ss:.3f}', '-i', src, '-vn', '-ac', '1', '-ar', str(SR), dst], check=True)


def proxy(src, dst, ss=0.0):
    if os.path.exists(dst): return
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{ss:.3f}', '-i', src, '-vf', "scale=-2:'min(1080,ih)',fps=30",
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', dst], check=True)


def envelope(path):
    x = np.fromfile(path, dtype=np.int16, offset=44).astype(np.float32) / 32768
    n = int(SR * HOP); k = len(x) // n
    rms = np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(1) + 1e-10)
    return 20 * np.log10(rms)


def activity(env, names):
    """Per speaker: dB above their own noise floor. Active = the speaker with the most headroom, if any is talking."""
    L = min(len(e) for e in env.values())
    rel = {}
    for n in names:
        e = env[n][:L]
        floor = np.percentile(e, 15)
        k = 7; e = np.convolve(e, np.ones(k) / k, mode='same')   # 0.35 s smoothing
        rel[n] = e - floor
    M = np.stack([rel[n] for n in names])
    talk = M > 14                     # 14 dB over the floor = speech (Riverside local mics are quiet between words)
    best = M.argmax(0)
    raw = np.where(talk.any(0), best, -1)
    # hysteresis: a new speaker must hold 0.6 s to take the floor; short gaps keep the current speaker
    hold = int(0.6 / HOP); cur = -1; out = np.full(L, -1)
    i = 0
    while i < L:
        c = raw[i]
        if c != cur and c != -1:
            j = i
            while j < L and raw[j] in (c, -1) and j - i < hold: j += 1
            if j - i >= hold or cur == -1: cur = c
        out[i] = cur
        i += 1
    return rel, talk, out


def windows(seq, names):
    w, s = [], 0
    for i in range(1, len(seq) + 1):
        if i == len(seq) or seq[i] != seq[s]:
            if seq[s] >= 0: w.append([round(s * HOP, 2), round(i * HOP, 2), names[seq[s]]])
            s = i
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('episode')
    ap.add_argument('--composite', help='a finished episode file instead of separate tracks')
    ap.add_argument('--regions', help='with --composite: JSON {"screen": [l, t, r, b], "<id>": [l, t, r, b]} in percent of the frame')
    a = ap.parse_args()
    E = os.path.abspath(a.episode); W = os.path.join(E, 'work')
    for d in ('tracks', 'audio'): os.makedirs(os.path.join(W, d), exist_ok=True)

    if a.composite:
        p = probe(a.composite)
        T = dict(mode='composite', source=os.path.abspath(a.composite), dur=p['dur'], size=[p['w'], p['h']],
                 # regions are % of the frame [l, t, r, b]; fill these in from a still. cut.py crops them into <id>.mp4 and screen.mp4
                 regions=json.loads(a.regions) if a.regions else {IDS[0]: [0.0, 0.0, 100.0, 100.0]}, speakers=[IDS[0]])
        # no proxy: a webcam bubble is small, so crops read the full-resolution source
        wav(a.composite, os.path.join(W, 'audio', f'{IDS[0]}.wav'))
    else:
        files = [f for f in glob.glob(os.path.join(E, 'raw', '**', '*'), recursive=True) if os.path.isfile(f)]
        R = guess(files)
        if not any(i in R for i in IDS):
            sys.exit(f'No files for {", ".join(IDS)} in raw/. Name them raw/<id>.mp4 (+ raw/<id>_raw.wav, raw/screen.mp4). Ids come from brand.json. '
                     'One file of everyone: use --composite FILE.')
        T = dict(mode=BRAND.get('recording', {}).get('source', 'local'), tracks={}, speakers=[r for r in IDS if r in R])
        for role, kinds in R.items():
            # the video's own sound first: it is on the video's clock. A raw wav starts when that person's own recording started
            # (seconds off), so align_audio.py lines it up after this and points the track at the result
            v = kinds.get('video'); au = v or kinds.get('audio')
            info = dict(video=v, audio=au)
            if v:
                info.update({k: x for k, x in probe(v).items() if k != 'audio'}); proxy(v, os.path.join(W, 'tracks', f'{role}.mp4'))
            if role != 'screen' and au: wav(au, os.path.join(W, 'audio', f'{role}.wav'))
            T['tracks'][role] = info
        T['dur'] = min(t['dur'] for t in T['tracks'].values() if t.get('dur'))
        durs = {k: round(v.get('dur', 0), 2) for k, v in T['tracks'].items()}
        if max(durs.values()) - min(durs.values()) > 2:
            print('WARN track lengths differ by more than 2 s:', durs, '(tracks should start together; check by eye)')

    env = {n: envelope(os.path.join(W, 'audio', f'{n}.wav')) for n in T['speakers']}
    rel, talk, seq = activity(env, T['speakers'])
    json.dump(dict(hop=HOP, speakers=T['speakers'], active=seq.tolist(),
                   rel_db={n: np.round(rel[n], 1).tolist() for n in T['speakers']}), open(os.path.join(W, 'activity.json'), 'w'))
    json.dump(windows(seq, T['speakers']), open(os.path.join(W, 'speakers.json'), 'w'), indent=0)
    json.dump(T, open(os.path.join(W, 'tracks.json'), 'w'), indent=1)
    share = {n: round(float((seq == i).mean()) * 100, 1) for i, n in enumerate(T['speakers'])}
    print(f"ingested {T['mode']}: {T['dur']:.0f} s, speakers {T['speakers']}, talk share % {share} -> {W}")


if __name__ == '__main__':
    main()

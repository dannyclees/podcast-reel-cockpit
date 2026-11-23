#!/usr/bin/env python3
"""lipsync.py <episode dir>: is each person's picture in time with their own voice? (rule R37)

Why: a recorder lines the voices up, not the webcams. One person's video can run 0.27 s (8 frames) behind their voice while another's is in sync.
How: for each speaker, take 4 windows of 60 s where they talk most, track the mouth with Apple Vision (face_track),
and slide the mouth-open curve against the voice loudness. The best lag per window; the lag of the best window (r >= 0.3; under
2 frames = 0) is written to work/tracks.json as tracks[role].video_offset. cut.py then cuts that person's
video from t + offset. Re-run cut.py after this.
"""
import json, os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand

FT = str(brand.FACE_TRACK)


def loud(wav, a, dur, fps):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(a), '-t', str(dur), '-i', wav, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(float); hop = int(16000 / fps); n = len(x) // hop
    return np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1)


def lag(video, wav, a, dur=30, fps=30):
    tmp = tempfile.mkdtemp(); v = os.path.join(tmp, 'v.mp4'); j = os.path.join(tmp, 'f.json')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(a), '-t', str(dur), '-i', video, '-an', '-vf', 'scale=640:-2', '-c:v', 'libx264', '-crf', '25', v], check=True)
    subprocess.run([FT, v, j, str(fps)], check=True, capture_output=True)
    m = np.array([f.get('mouth') or 0 for f in json.load(open(j))['frames']]); e = loud(wav, a, dur, fps)
    L = min(len(m), len(e)); m = m[:L] - m[:L].mean(); e = e[:L] - e[:L].mean()
    r, k = max((np.corrcoef(m[max(0, k):L + min(0, k)], e[max(0, -k):L - max(0, k)])[0, 1], k) for k in range(-20, 21))
    return k / fps, r


def main(E):
    W = os.path.join(E, 'work'); T = json.load(open(os.path.join(W, 'tracks.json')))
    if T.get('mode') == 'composite': print('composite: picture and sound are one file, nothing to check'); return
    words = json.load(open(os.path.join(W, 'words.json')))
    for role in T['speakers']:
        info = T['tracks'][role]
        talk = np.zeros(int(max(w['start'] for w in words) // 60) + 2)
        for w in words:
            if w['spk'] == role: talk[int(w['start'] // 60)] += 1
        wins = [int(i) * 60 for i in np.argsort(-talk)[:4] if (int(i) + 1) * 60 < T['dur']] or [0]   # a recording under a minute: the whole of it
        res = [lag(info['video'], info['audio'], a, dur=60) for a in wins]
        o, r = max(res, key=lambda x: x[1])   # trust the window where mouth and voice match best
        off = round(o, 3) if r >= 0.3 and abs(o) >= 0.05 else 0.0   # under 2 frames counts as in sync
        info['video_offset'] = off
        print(f"{role}: windows {wins} -> {[(round(o, 2), round(r, 2)) for o, r in res]} -> video_offset {off:+.3f} s")
    json.dump(T, open(os.path.join(W, 'tracks.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(os.path.abspath(sys.argv[1]))

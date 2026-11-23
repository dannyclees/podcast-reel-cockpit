#!/usr/bin/env python3
"""cut.py <episode dir> [--only c1,c2]: cut every clip in <episode>/clips.json out of every track, all in sync.

clips.json:
{"clips": [{"id": "c1", "title": "...", "ranges": [[first_word, last_word], ...], "drops": [[a, b], ...], ...}]}
  ranges = word numbers (#n in lines.txt) to keep, in play order (a later range may come first: that is a cold open).
  drops  = word numbers to remove inside the ranges (fillers, plugs, retakes).

Inside a range, pauses longer than --max-gap shrink to --keep-gap (tight pace, 4+ words a second).
Writes <episode>/clips/<id>/: segs.json (source times), words.json (new times, speaker on each word),
  <track>.mp4 per video track (composite: a full-resolution crop per region; separate tracks: the 1080p proxies), voice.wav (48 kHz, all mics summed).
"""
import argparse, json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))

def quiet_env(W, T):
    """10 ms loudness of all mics summed (16 kHz work wavs), used to snap cut points into silence."""
    import numpy as np
    xs = [np.fromfile(os.path.join(W, 'audio', f'{s}.wav'), dtype=np.int16, offset=44).astype(np.float32) for s in T['speakers']]
    L = min(len(x) for x in xs); x = sum(v[:L] for v in xs)
    n = 160; k = L // n
    return np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(1) + 1.0)


def snap(env, t, lo, hi):
    """Quietest 10 ms frame between lo and hi (seconds); t if the window is empty."""
    import numpy as np
    a, b = int(max(0, lo) * 100), int(hi * 100)
    if b <= a + 1: return t
    seg = np.convolve(env[a:b], np.ones(3) / 3, mode='same')
    return (a + int(seg.argmin())) / 100


def segments(words, ranges, drops, max_gap, keep_gap, env=None):
    drop = set()
    for a, b in drops: drop.update(range(a, b + 1))
    runs = []
    for a, b in ranges:
        idx = [i for i in range(a, b + 1) if i not in drop]
        run = []
        for i in idx:   # break the range wherever a dropped word or a long pause sits between kept words
            if run and ((i != run[-1] + 1 and any(j in drop for j in range(run[-1] + 1, i))) or
                        words[i]['start'] - words[run[-1]]['end'] > max_gap):
                runs.append(run); run = []
            run.append(i)
        if run: runs.append(run)
    # a piece shorter than 0.7 s would flash on screen as its own shot: keep the pause instead and join it to its neighbour
    merged = []
    for run in runs:
        if merged and merged[-1][-1] + 1 == run[0] and (
                words[run[-1]]['end'] - words[run[0]]['start'] < 0.7 or words[merged[-1][-1]]['end'] - words[merged[-1][0]]['start'] < 0.7):
            merged[-1] = merged[-1] + run
        else: merged.append(run)
    runs = merged
    S = []
    for run in runs:
        f, l = run[0], run[-1]
        prev_end = words[f - 1]['end'] if f > 0 else 0.0
        next_start = words[l + 1]['start'] if l + 1 < len(words) else words[l]['end'] + 1.0
        lo = max(prev_end + 0.02, words[f]['start'] - 0.25); hi = min(next_start - 0.02, words[l]['end'] + 0.25)
        if env is not None:
            s = snap(env, words[f]['start'] - 0.04, lo, words[f]['start'] + 0.03)
            e = snap(env, words[l]['end'] + 0.08, words[l]['end'] - 0.03, hi)
        else:
            s, e = max(lo, words[f]['start'] - 0.04), min(hi, words[l]['end'] + keep_gap)
        S.append([round(s, 3), round(max(e, s + 0.1), 3), run])
    t, out_words = 0.0, []
    for s, e, run in S:
        for i in run:
            w = words[i]
            out_words.append(dict(i=len(out_words), src=i, text=w['text'], spk=w['spk'],
                                  start=round(max(0, t + w['start'] - s), 3), end=round(t + min(w['end'], e) - s, 3)))
        t += e - s
    return [[s, e] for s, e, _ in S], out_words, round(t, 3)


def unsquash(words, short=0.05, run_min=4):
    """Whisper sometimes squashes a whole line into a fraction of a second (14 words in 0.7 s while the
    speech ran 5 s). Spread any run of 4+ near-zero-length words over the time from the word before to the word after,
    weighted by word length, so captions and pictures land on the real words."""
    i, n = 0, len(words)
    while i < n:
        j = i
        while j < n and words[j]['end'] - words[j]['start'] < short: j += 1
        if j - i >= run_min:
            a = words[i - 1]['end'] + 0.05 if i > 0 else words[i]['start']
            b = words[j]['start'] if j < n else words[j - 1]['end']
            wts = [max(2, len(w['text'].strip())) for w in words[i:j]]; tot = sum(wts); t = a
            for w, k in zip(words[i:j], wts):
                d = (b - a) * k / tot; w['start'] = round(t, 3); w['end'] = round(t + d * .9, 3); t += d
            print(f'  unsquashed words {i}-{j - 1} over {a:.2f}-{b:.2f} s')
        i = max(j, i + 1)
    return words


def drop_times(segs, words, cuts):
    """R2 stumbles the transcript cannot see (a repeated phrase, a filler "like"): remove source-time intervals [a, b]
    from the cut. Words whose middle falls in a removed interval go too; the rest are re-timed on the new clock."""
    if not cuts: return segs, words, round(sum(e - s for s, e in segs), 3)
    def to_src(t):
        acc = 0.0
        for s, e in segs:
            if t <= acc + (e - s) + 1e-6: return s + (t - acc)
            acc += e - s
        return segs[-1][1]
    new = []
    for s, e in segs:
        pieces = [[s, e]]
        for a, b in cuts:
            nxt = []
            for ps, pe in pieces:
                if b <= ps or a >= pe: nxt.append([ps, pe]); continue
                if a > ps: nxt.append([ps, a])
                if b < pe: nxt.append([b, pe])
            pieces = nxt
        new += [[round(ps, 3), round(pe, 3)] for ps, pe in pieces if pe - ps > 0.05]
    def to_clip(src):
        acc = 0.0
        for s, e in new:
            if s - 1e-6 <= src <= e + 1e-6: return acc + (src - s)
            acc += e - s
        return None
    out = []
    for w in words:
        a, b = to_src(w['start']), to_src(w['end']); mid = (a + b) / 2
        if any(x <= mid <= y for x, y in cuts): continue
        ca, cb = to_clip(a), to_clip(b)
        if ca is None: continue
        w = dict(w, i=len(out), start=round(ca, 3), end=round(cb if cb is not None else ca + 0.1, 3)); out.append(w)
    return new, out, round(sum(e - s for s, e in new), 3)


def ff_cut(src, segs, dst, video=True, audio=True, vf=None, ar=None):
    parts, n = [], len(segs)
    fc = []
    for k, (s, e) in enumerate(segs):
        if video: fc.append(f'[0:v]trim={s}:{e},setpts=PTS-STARTPTS[v{k}]')
        if audio: fc.append(f'[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={e - s - 0.012:.3f}:d=0.012[a{k}]')
    ins = ''.join((f'[v{k}]' if video else '') + (f'[a{k}]' if audio else '') for k in range(n))
    fc.append(f'{ins}concat=n={n}:v={int(video)}:a={int(audio)}' + ('[v]' if video else '') + ('[a]' if audio else ''))
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', src, '-filter_complex', ';'.join(fc)]
    if video: cmd += ['-map', '[v]', '-r', '30', '-c:v', 'libx264', '-preset', 'fast', '-crf', '15', '-pix_fmt', 'yuv420p', '-g', '15']
    if audio: cmd += ['-map', '[a]'] + (['-c:a', 'pcm_s16le', '-ar', str(ar or 48000)] if dst.endswith('.wav') else ['-c:a', 'aac', '-b:a', '256k'])
    if not video: cmd += ['-vn']
    subprocess.run(cmd + [dst], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('episode'); ap.add_argument('--only'); ap.add_argument('--max-gap', type=float, default=0.42)
    ap.add_argument('--keep-gap', type=float, default=0.14); ap.add_argument('--retranscribe', action='store_true')
    a = ap.parse_args()
    E = os.path.abspath(a.episode); W = os.path.join(E, 'work')
    T = json.load(open(os.path.join(W, 'tracks.json'))); words = json.load(open(os.path.join(W, 'words.json')))
    C = json.load(open(os.path.join(E, 'clips.json')))['clips']
    only = set(a.only.split(',')) if a.only else None
    ENV = quiet_env(W, T)
    for c in C:
        if only and c['id'] not in only: continue
        D = os.path.join(E, 'clips', c['id']); os.makedirs(D, exist_ok=True)
        segs, nw, dur = segments(words, c['ranges'], c.get('drops', []), c.get('max_gap', a.max_gap), a.keep_gap, ENV)
        if c.get('end_pad'): segs[-1][1] = round(segs[-1][1] + c['end_pad'], 3); dur = round(dur + c['end_pad'], 3)   # let the last line ring out
        segs, nw, dur = drop_times(segs, nw, c.get('drop_times', []))   # source seconds, e.g. a stumble inside a take
        json.dump(dict(id=c['id'], segs=segs, duration=dur), open(os.path.join(D, 'segs.json'), 'w'), indent=1)
        json.dump(nw, open(os.path.join(D, 'words.json'), 'w'))
        if T['mode'] == 'composite':
            ff_cut(T['source'], segs, os.path.join(D, 'composite.mp4'), audio=False)
            ff_cut(T['source'], segs, os.path.join(D, 'voice.wav'), video=False)
            sw, sh = T['size']
            for role, (l, t, r, b) in T['regions'].items():   # short.py reads <id>.mp4 and screen.mp4: one crop per region, in sync
                cw, ch = int(sw * (r - l) / 100) // 2 * 2, int(sh * (b - t) / 100) // 2 * 2
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(D, 'composite.mp4'), '-vf', f'crop={cw}:{ch}:{int(sw * l / 100)}:{int(sh * t / 100)}',
                                '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '15', '-pix_fmt', 'yuv420p', '-g', '15', os.path.join(D, f'{role}.mp4')], check=True)
        else:
            for role, info in T['tracks'].items():
                p = os.path.join(W, 'tracks', f'{role}.mp4')
                off = info.get('video_offset', 0.0)   # R37: this person's picture runs late by off seconds (lipsync.py)
                if os.path.exists(p): ff_cut(p, [[round(a + off, 3), round(b + off, 3)] for a, b in segs], os.path.join(D, f'{role}.mp4'), audio=False)
            mics = []
            for role in T['speakers']:
                src = T['tracks'][role]['audio']
                ff_cut(src, segs, os.path.join(D, f'mic_{role}.wav'), video=False); mics.append(os.path.join(D, f'mic_{role}.wav'))
            ins = sum((['-i', m] for m in mics), [])
            subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex',
                            f'amix=inputs={len(mics)}:normalize=0', '-ac', '1', '-ar', '48000', os.path.join(D, 'voice.wav')], check=True)
        if a.retranscribe and T['mode'] != 'composite': nw = retranscribe(D, T['speakers'], nw)
        nw = unsquash(nw)
        for fx in c.get('say', []):   # caption fixes: [first clip word, last clip word, 'what was really said']
            fa, fb, txt = fx; parts = txt.split(); n = fb - fa + 1
            for k in range(n): nw[fa + k]['text'] = ' '.join(parts[k * len(parts) // n:(k + 1) * len(parts) // n]) or ''
        json.dump(nw, open(os.path.join(D, 'words.json'), 'w'))
        ep_words = os.path.join(D, 'words.episode.json')   # a re-cut changes the words: retext must not map onto the old cut's list
        if os.path.exists(ep_words): os.remove(ep_words)
        print(f"{c['id']}: {dur:.1f} s, {len(segs)} segments, {len(nw)} words, {len(nw) / dur:.2f} words/s -> {D}")


def retranscribe(D, speakers, fallback):
    """Captions must be exact: whisper the clip's own mix again, then label each word by the louder mic."""
    import numpy as np, sys
    CAP = os.path.join(HERE, 'vendor', 'captions.py')
    out = os.path.join(D, 'whisper')
    if not os.path.exists(os.path.join(out, 'words_raw.json')):
        subprocess.run([sys.executable, CAP, os.path.join(D, 'voice.wav'), '--out', out, '--model', 'medium.en'], check=True,
                       stdout=subprocess.DEVNULL)
    ws = json.load(open(os.path.join(out, 'words_raw.json')))
    if not ws or any(w['end'] - w['start'] > 8 for w in ws): print('  clip re-transcribe broken, keeping episode words'); return fallback
    env = {}
    for s in speakers:
        tmp = os.path.join(D, f'_{s}16.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(D, f'mic_{s}.wav'), '-ac', '1', '-ar', '16000', tmp], check=True)
        x = np.fromfile(tmp, dtype=np.int16, offset=44).astype(np.float32) / 32768; os.remove(tmp)
        n = 800; k = len(x) // n
        e = 20 * np.log10(np.sqrt((x[:k * n].reshape(k, n) ** 2).mean(1) + 1e-10))
        env[s] = e - np.percentile(e, 15)
    words = []
    for w in ws:
        a, b = int(w['start'] / 0.05), max(int(w['start'] / 0.05) + 1, int(w['end'] / 0.05))
        spk = max(speakers, key=lambda s: float(np.mean(env[s][a:b])) if len(env[s][a:b]) else -99)
        words.append(dict(i=len(words), text=w['text'], start=w['start'], end=w['end'], spk=spk))
    json.dump(words, open(os.path.join(D, 'words.json'), 'w'))
    return words


if __name__ == '__main__':
    main()

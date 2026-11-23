#!/usr/bin/env python3
"""align_words.py --episode <ep dir> [ids] | <clip dir>: forced alignment of words.json to voice.wav (rule R20). Run with the aligner venv:
    bin/.venv-align/bin/python pipeline/align_words.py <clip dir>

Why: captions ran about half a second off the voice. Whisper word times drift -0.9 to +1.5 s,
and whisper's own DTW mode was no better on these mics. Forced alignment knows the words already and only asks
"where in the sound is each letter", so it lands on the word (wav2vec2 base 960h, torchaudio forced_align).
Word numbers ("i") never change, so clips.json visuals keep pointing at the same words.
--episode: re-times work/words.json around each clip BEFORE cut.py (the episode transcript drifts up to 2.5 s,
so cuts landed on the wrong words). <clip dir>: re-times the clip's words.json after cut.py.
"""
import json, os, re, shutil, subprocess, sys
import numpy as np
import torch, torchaudio

ONES = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
TENS = 'zero ten twenty thirty forty fifty sixty seventy eighty ninety'.split()


def num(n):
    if n < 20: return ONES[n]
    if n < 100: return TENS[n // 10] + ('' if n % 10 == 0 else ' ' + ONES[n % 10])
    if n < 1000: return ONES[n // 100] + ' hundred' + ('' if n % 100 == 0 else ' ' + num(n % 100))
    if n < 1_000_000: return num(n // 1000) + ' thousand' + ('' if n % 1000 == 0 else ' ' + num(n % 1000))
    return ' '.join(ONES[int(c)] for c in str(n))


def spoken(t):
    """'30s' -> 'THIRTIES', '40-year-old' -> 'FORTY YEAR OLD', '350' -> 'THREE HUNDRED FIFTY'."""
    t = t.lower().replace('-', ' ').replace('%', ' percent')
    t = re.sub(r'(\d+)s\b', lambda m: re.sub(r'y$', 'ies', num(int(m.group(1)))) if num(int(m.group(1))).endswith('y') else num(int(m.group(1))) + 's', t)
    t = re.sub(r'\d+', lambda m: num(int(m.group(0))), t)
    return re.sub(r"[^a-z' ]", '', t).upper().split()


_M = {}


def model():
    if not _M:
        B = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
        _M['b'] = B; _M['m'] = B.get_model().eval(); _M['idx'] = {c: k for k, c in enumerate(B.get_labels())}
    return _M['b'], _M['m'], _M['idx']


def load(paths, t0=0.0, dur=None):
    """mono float32 at the model rate; several paths are summed (one mic per speaker)."""
    B, _, _ = model()
    cut = (['-ss', f'{t0:.3f}'] + (['-t', f'{dur:.3f}'] if dur else []))
    ins = sum((cut + ['-i', p] for p in paths), [])
    mix = ['-filter_complex', f'amix=inputs={len(paths)}:normalize=0'] if len(paths) > 1 else []
    raw = subprocess.run(['ffmpeg', '-v', 'error', *ins, *mix, '-ac', '1', '-ar', str(B.sample_rate), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return torch.from_numpy(np.frombuffer(raw, np.float32).copy())[None]


def align(wav, order):
    """{word i: (start, end)} in seconds from the start of wav, for words in play order."""
    B, m, idx = model()
    with torch.inference_mode():
        em = []
        step = B.sample_rate * 30   # 30 s pieces keep memory low; frames are 20 ms
        for a in range(0, wav.shape[1], step):
            e, _ = m(wav[:, a:a + step]); em.append(e)
        em = torch.log_softmax(torch.cat(em, 1), -1)
    fr = wav.shape[1] / em.shape[1] / B.sample_rate   # seconds per frame
    toks, owner = [], []
    for w in order:
        for part in spoken(w['text']):
            if toks: toks.append(idx['|']); owner.append(None)
            for c in part:
                if c in idx: toks.append(idx[c]); owner.append(w['i'])
    al, _ = torchaudio.functional.forced_align(em, torch.tensor([toks], dtype=torch.int32), blank=0)
    al = al[0].tolist()
    first, last, k = {}, {}, 0
    for f, t in enumerate(al):   # walk frames; each new non-blank token run advances k
        if t == 0 or (f and al[f - 1] == t and k): continue
        while k < len(toks) and toks[k] != t: k += 1
        if k >= len(toks): break
        if owner[k] is not None: first.setdefault(owner[k], f); last[owner[k]] = f
        k += 1
    return {i: (first[i] * fr, max((last[i] + 1) * fr, first[i] * fr + 0.08)) for i in first}


def report(order, new):
    m = np.abs(np.array([new[w['i']][0] - w['start'] for w in order if w['i'] in new]))
    return f'whisper was off by median {np.median(m):.2f} s, {(m > 0.25).mean():.0%} more than 0.25 s, worst {m.max():.2f} s'


def episode(E, only, ctx=40, pad=6.0):
    """re-time the episode words around each clip (+-ctx words, +-pad s of sound), before cut.py runs."""
    W = os.path.join(E, 'work')
    if not os.path.exists(os.path.join(W, 'words.whisper.json')): shutil.copy(os.path.join(W, 'words.json'), os.path.join(W, 'words.whisper.json'))
    words = json.load(open(os.path.join(W, 'words.json'))); T = json.load(open(os.path.join(W, 'tracks.json')))
    mics = [T['source']] if T.get('mode') == 'composite' else [T['tracks'][s]['audio'] for s in T['speakers']]
    for c in json.load(open(os.path.join(E, 'clips.json')))['clips']:
        if only and c['id'] not in only: continue
        i0 = max(0, min(r[0] for r in c['ranges']) - ctx); i1 = min(len(words) - 1, max(r[1] for r in c['ranges']) + ctx)
        order = words[i0:i1 + 1]
        t0 = max(0.0, order[0]['start'] - pad); t1 = order[-1]['end'] + pad
        new = align(load(mics, t0, t1 - t0), order)
        print(f"{c['id']}: {report(order, {i: (a + t0, b + t0) for i, (a, b) in new.items()})}")
        core = range(i0 + ctx // 2, i1 - ctx // 2 + 1)   # words near the window edges are less sure: keep only the middle
        for w in order:
            if w['i'] in new and w['i'] in core: w['start'], w['end'] = round(new[w['i']][0] + t0, 3), round(new[w['i']][1] + t0, 3)
    json.dump(words, open(os.path.join(W, 'words.json'), 'w'))


def clip(D):
    """after cut.py: one more pass on the clip's own sound, as a check (should move almost nothing)."""
    order = sorted(json.load(open(os.path.join(D, 'words.json'))), key=lambda w: w['i'])
    new = align(load([os.path.join(D, 'voice.wav')]), order)
    print(f'{os.path.basename(D)}: {len(new)}/{len(order)} words aligned; {report(order, new)}')
    for w in order:
        if w['i'] in new: w['start'], w['end'] = round(new[w['i']][0], 3), round(new[w['i']][1], 3)
    # the aligner marks the first clear letter; a word after a pause starts at the first sound, up to 0.3 s earlier
    x = load([os.path.join(D, 'voice.wav')])[0].numpy(); n = len(x) // 160
    db = 20 * np.log10(np.sqrt((x[:n * 160].reshape(n, 160) ** 2).mean(1)) + 1e-6)
    v = db > np.percentile(db, 30) + 12
    snapped = 0
    for k, w in enumerate(order):
        c = int(w['start'] * 100); lo = max(10, c - 30, int(order[k - 1]['end'] * 100) + 1 if k else 10)
        for f in range(lo, c + 1):
            if v[f] and not v[f - 10:f].any() and v[f:f + 6].mean() > 0.6:
                w['start'] = round(f / 100, 3); snapped += 1; break
    print(f'  {snapped} words moved back onto the first sound after a pause')
    json.dump(order, open(os.path.join(D, 'words.json'), 'w'))


if __name__ == '__main__':
    if sys.argv[1] == '--episode': episode(os.path.abspath(sys.argv[2]), set(sys.argv[3].split(',')) if len(sys.argv) > 3 else None)
    else: clip(os.path.abspath(sys.argv[1]))

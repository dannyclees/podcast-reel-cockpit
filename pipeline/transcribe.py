#!/usr/bin/env python3
"""transcribe.py <episode dir> [--model small.en]: word-level transcript with a speaker on every word.

Separate tracks: whisper runs on each speaker's own mic, then the lists merge by time.
A word heard on the wrong mic (bleed) is dropped: at that moment its own mic must be the louder one.
Composite: one speaker, one pass.

Writes work/words.json  [{i, text, start, end, spk}]  and work/lines.txt (for reading and picking clips).
"""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
CAPTIONS = os.path.join(HERE, 'vendor', 'captions.py')


def gate(src, dst, rel, hop, thr=11.0, pad=0.4):
    """Silence a mic wherever its own speaker is not talking. Whisper invents looping lines on near-silent bleed."""
    import numpy as np
    x = np.fromfile(src, dtype=np.int16, offset=44).astype(np.float32)
    on = np.array(rel) > thr
    k = int(pad / hop)
    on = np.convolve(on.astype(float), np.ones(2 * k + 1), mode='same') > 0      # keep 0.4 s either side of speech
    n = int(16000 * hop); m = np.repeat(on, n)[:len(x)]
    m = np.concatenate([m, np.zeros(len(x) - len(m), bool)]) if len(m) < len(x) else m
    ramp = np.convolve(m.astype(np.float32), np.ones(160) / 160, mode='same')    # 10 ms fades, no clicks
    y = (x * ramp).astype(np.int16)
    import wave
    with wave.open(dst, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(y.tobytes())
    return float(m.mean())


def broken(ws):
    return [w for w in ws if w['end'] - w['start'] > 8 or set(w['text'].strip()) <= set('.')]


def loopiness(ws):
    """Share of words inside a 5-word phrase that repeats 3+ times (whisper's looping failure)."""
    t = [w['text'].strip().lower().strip('.,!?') for w in ws]
    from collections import Counter
    g = Counter(tuple(t[i:i + 5]) for i in range(len(t) - 4))
    hot = {k for k, v in g.items() if v >= 3}
    hit = set()
    for i in range(len(t) - 4):
        if tuple(t[i:i + 5]) in hot: hit.update(range(i, i + 5))
    return len(hit) / max(1, len(t))


def bad_score(ws, dur):
    return sum(w['end'] - w['start'] for w in broken(ws)) / dur + loopiness(ws)


def repair(ws, pw, po, dur, model, depth=0):
    """Retry a broken or looping piece with smaller models; if it still fails, split it in half (max twice)."""
    best = ws
    for fb in ('small.en', 'base.en'):
        if bad_score(best, dur) < 0.15: return best
        fo = os.path.join(po, fb); os.makedirs(fo, exist_ok=True)
        if not os.path.exists(os.path.join(fo, 'words_raw.json')):
            subprocess.run([sys.executable, CAPTIONS, pw, '--out', fo, '--model', fb], check=True, stdout=subprocess.DEVNULL)
        alt = json.load(open(os.path.join(fo, 'words_raw.json')))
        print(f'  {os.path.basename(po)}: bad {bad_score(best, dur):.2f} -> {fb} {bad_score(alt, dur):.2f}')
        if bad_score(alt, dur) < bad_score(best, dur): best = alt
    if bad_score(best, dur) < 0.15 or depth >= 2: return best
    half = dur / 2; out = []
    for j, (a, b) in enumerate([(0, half), (half, dur)]):
        sub = os.path.join(po, f'h{j}'); os.makedirs(sub, exist_ok=True); sw = os.path.join(sub, 'piece.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a:.3f}', '-to', f'{b:.3f}', '-i', pw, sw], check=True)
        if not os.path.exists(os.path.join(sub, 'words_raw.json')):
            subprocess.run([sys.executable, CAPTIONS, sw, '--out', sub, '--model', model], check=True, stdout=subprocess.DEVNULL)
        hw = repair(json.load(open(os.path.join(sub, 'words_raw.json'))), sw, sub, b - a, model, depth + 1)
        out += [dict(w, start=round(w['start'] + a, 3), end=round(w['end'] + a, 3)) for w in hw]
    print(f'  {os.path.basename(po)}: split in half, bad now {bad_score(out, dur):.2f}')
    return out if bad_score(out, dur) < bad_score(best, dur) else best


def run_whisper(wav, out, model, piece=300.0):
    """Whisper in ~5 min pieces cut at the quietest point near each boundary (long files make whisper.cpp degenerate)."""
    final = os.path.join(out, 'words_raw.json')
    if os.path.exists(final): return json.load(open(final))
    import numpy as np
    x = np.fromfile(wav, dtype=np.int16, offset=44).astype(np.float32); sr = 16000; dur = len(x) / sr
    cuts = [0.0]
    while dur - cuts[-1] > piece * 1.3:
        a, b = int((cuts[-1] + piece - 20) * sr), int((cuts[-1] + piece + 20) * sr)
        e = np.convolve(np.abs(x[a:b]), np.ones(sr // 10) / (sr // 10), mode='same')
        cuts.append(round((a + int(e.argmin())) / sr, 3))
    cuts.append(dur)
    words = []
    for k in range(len(cuts) - 1):
        po = os.path.join(out, f'p{k:02d}'); os.makedirs(po, exist_ok=True)
        pw = os.path.join(po, 'piece.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{cuts[k]:.3f}', '-to', f'{cuts[k + 1]:.3f}', '-i', wav, pw], check=True)
        if not os.path.exists(os.path.join(po, 'words_raw.json')):
            subprocess.run([sys.executable, CAPTIONS, pw, '--out', po, '--model', model], check=True, stdout=subprocess.DEVNULL)
        ws = json.load(open(os.path.join(po, 'words_raw.json')))
        ws = repair(ws, pw, po, cuts[k + 1] - cuts[k], model)
        bad = broken(ws)
        if bad: print(f'  WARN piece {k}: {len(bad)} broken words dropped')
        for w in ws:
            if w in bad: continue
            words.append(dict(text=w['text'], start=round(w['start'] + cuts[k], 3), end=round(w['end'] + cuts[k], 3)))
    for i, w in enumerate(words): w['i'] = i
    json.dump(words, open(final, 'w'))
    return words


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('episode'); ap.add_argument('--model', default='small.en')
    a = ap.parse_args()
    W = os.path.join(os.path.abspath(a.episode), 'work')
    T = json.load(open(os.path.join(W, 'tracks.json')))
    A = json.load(open(os.path.join(W, 'activity.json')))
    hop = A['hop']; rel = A['rel_db']
    words = []
    for spk in T['speakers']:
        src = os.path.join(W, 'audio', f'{spk}.wav')
        if len(T['speakers']) > 1:
            g = os.path.join(W, 'audio', f'{spk}_gated.wav')
            if not os.path.exists(g): print(f'{spk}: gated, speech kept on {gate(src, g, rel[spk], hop) * 100:.0f}% of the track')
            src = g
        ws = run_whisper(src, os.path.join(W, 'whisper', spk), a.model)
        for w in ws: words.append(dict(text=w['text'], start=w['start'], end=w['end'], spk=spk))
    if len(T['speakers']) > 1:
        keep = []
        for w in words:
            k0, k1 = int(w['start'] / hop), max(int(w['start'] / hop) + 1, int(w['end'] / hop))
            own = max(rel[w['spk']][k0:k1] or [0])
            other = max(max(rel[s][k0:k1] or [0]) for s in T['speakers'] if s != w['spk'])
            if own >= 10 and own >= other - 3: keep.append(w)    # own mic clearly active, not quieter than the other
        print(f'bleed filter: kept {len(keep)} of {len(words)} words')
        words = keep
    words.sort(key=lambda w: w['start'])
    for i, w in enumerate(words): w['i'] = i
    json.dump(words, open(os.path.join(W, 'words.json'), 'w'))
    # readable lines, a new line on every speaker change or sentence end
    out, line, st = [], [], None
    for w in words:
        if line and (w['spk'] != st['spk'] or (line[-1][-1:] in '.?!' and len(line) > 6) or len(line) > 40):
            out.append(f"{int(st['start']//60)}:{int(st['start']%60):02d} #{st['i']} {st['spk'].upper()}: {' '.join(line)}"); line = []
        if not line: st = w
        line.append(w['text'].strip())
    if line: out.append(f"{int(st['start']//60)}:{int(st['start']%60):02d} #{st['i']} {st['spk'].upper()}: {' '.join(line)}")
    open(os.path.join(W, 'lines.txt'), 'w').write('\n'.join(out))
    print(f'{len(words)} words, {len(out)} lines -> {W}/words.json, lines.txt')


if __name__ == '__main__':
    main()

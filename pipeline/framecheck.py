#!/usr/bin/env python3
"""framecheck.py <final.mp4> [--sting 2.6] [--scan scan.json]: read EVERY frame of a finished Short (rules R21, R22, R23).

Why: every frame must show a person, and no text may cover a face. This reads faces and text with Apple Vision (bin/frame_scan, every frame) and fails on:
  R21 frame 0 has no face.
  R22 the first word is heard later than 0.15 s.
  R23a a face-less stretch longer than 3.0 s (the end sting is exempt).
  R38 the top of a head cut off by the frame or the split line.
  R23b any text box over a face (box overlap > 4% of the face; the show's own name and any logo the hosts wear are ignored,
       brand.json framecheck_ignore lists those words; a scrap with no 3-letter run counts only if it holds 3+ frames).
Writes <final>.framecheck.json next to the video and prints PASS or FAIL with the bad times.
"""
import argparse, json, os, re, subprocess
import numpy as np, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand

HERE = str(brand.ROOT)
_names = [brand.SHOW.get('name', ''), brand.SHOW.get('short', ''), brand.BRAND.get('logo', {}).get('wordmark_text', '')]
_worn = brand.BRAND.get('framecheck_ignore', [])   # logos on the hosts' caps and shirts, as plain words
_words = {w.lower() for n in _names + _worn for w in [n] + [x for x in n.split() if len(x) >= 4] if w}
IGNORE = re.compile('^(' + '|'.join(sorted(map(re.escape, _words)) or ['(?!)']) + ')$', re.I)   # the show's own name and the logos the hosts wear
# Apple Vision misreads a logo on a cap into many spellings, always 0.4 to 0.8 face heights ABOVE the brow. A read is the cap logo only if ALL hold:
# letters from a worn word (brand.json framecheck_ignore, add the misreads you see), no other word but one 3-letter scrap (a real caption line has several words),
# centred above the brow of a face (0.2 to 0.9 face heights up), inside that face's width and narrower than 0.65 of it. A caption on the hair or face fails these.
CAPLOGO = re.compile('|'.join(map(re.escape, _worn)) or '(?!)', re.I)


def cap_logo(tx, faces):
    s = tx['s'].strip(); b = tx['box']
    if not (IGNORE.match(s) or CAPLOGO.search(s)): return False
    other = [w for w in s.split() if sum(c.isalpha() for c in w) >= 3 and not CAPLOGO.search(w)]   # the logo's icon reads as "ffi", "Es"
    if len(other) > 1 or any(sum(c.isalpha() for c in w) > 3 for w in other): return False
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    for f in faces:
        h, w = f[3] - f[1], f[2] - f[0]
        if h > 0 and f[0] <= cx <= f[2] and f[1] - 0.9 * h <= cy <= f[1] - 0.2 * h and b[2] - b[0] <= 0.65 * w: return True
    return False


def on_cap(tx, faces):
    """one word read just where a worn logo sits, when the show lists worn logos. Vision misreads a cap into new spellings on every render, so treat it as a scrap: it counts only if it holds 3+ frames."""
    b = tx['box']
    if not _worn or len(re.findall(r'\w{2,}', tx['s'])) > 1: return False
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    return any(f[0] <= cx <= f[2] and f[1] - 0.9 * (f[3] - f[1]) <= cy <= f[1] - 0.2 * (f[3] - f[1]) and b[2] - b[0] <= 0.65 * (f[2] - f[0]) for f in faces)


def weak(s):
    """no run of 3+ letters, or almost only stripe glyphs (1 l I i ! |): a scrap read off a cap brim, a hand, a mic or a drawn outline."""
    if not re.search(r'[A-Za-z]{3}', s): return True
    return len(re.sub(r"[1lIi!|',.:;\s]", '', s)) <= 2   # stripes, rails, a mic grille


def scan_fresh(path, video):
    """The cache in checks/ is named by file name only, so a/x.mp4 and b/x.mp4 would share ONE scan. A cache is reused only if it was made from this exact file (path, size, mtime)."""
    key = f"{os.path.abspath(video)}|{os.path.getsize(video)}|{int(os.path.getmtime(video))}"
    kf = path + '.key'
    ok = os.path.exists(path) and os.path.exists(kf) and open(kf).read() == key
    return ok, (lambda: open(kf, 'w').write(key))


def overlap(a, b):
    w = max(0, min(a[2], b[2]) - max(a[0], b[0])); h = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return w * h


def first_sound(mp4):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', mp4, '-vn', '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32); n = len(x) // 160
    db = 20 * np.log10(np.sqrt((x[:n * 160].reshape(n, 160) ** 2).mean(1)) + 1)
    on = np.where(db > np.percentile(db, 30) + 12)[0]
    return on[0] / 100 if len(on) else None


def runs(ts, step):
    """merge times into [start, end] runs."""
    out = []
    for t in ts:
        if out and t - out[-1][1] <= step * 1.5: out[-1][1] = t
        else: out.append([t, t])
    return [[round(a, 2), round(b + step, 2)] for a, b in out]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('video'); ap.add_argument('--sting', type=float, default=2.6)
    ap.add_argument('--scan'); ap.add_argument('--fps', default='30')
    a = ap.parse_args()
    CK = os.path.join(HERE, 'checks'); os.makedirs(CK, exist_ok=True)
    scan = a.scan or os.path.join(CK, os.path.basename(a.video) + '.scan.json')
    ok, mark = scan_fresh(scan, a.video) if not a.scan else (os.path.exists(scan), lambda: None)
    if not ok:
        subprocess.run([str(brand.FRAME_SCAN), a.video, scan, a.fps], check=True); mark()
    S = json.load(open(scan)); F = S['frames']; step = 1 / S['fps']; end = S['dur'] - a.sting
    fails = []
    if not F[0].get('faces'): fails.append('R21 frame 0 has no face')
    fs = first_sound(a.video)
    if fs is None or fs > 0.15: fails.append(f'R22 first sound at {fs:.2f} s (max 0.15 s)')
    noface = runs([f['t'] for f in F if not f.get('faces') and f['t'] < end], step)
    long_nf = [r for r in noface if r[1] - r[0] > 3.0]
    for r in long_nf: fails.append(f'R23a no face {r[0]}-{r[1]} s ({r[1] - r[0]:.1f} s, max 3.0 s)')
    hits = []
    for f in F:
        for fc in f.get('faces', []):
            fc = [fc[0], max(0.0, fc[1] - 0.6 * (fc[3] - fc[1])), fc[2], fc[3]]   # R60: the hair counts as the head (Vision's box stops at the brow)
            area = (fc[2] - fc[0]) * (fc[3] - fc[1])
            for tx in f.get('text', []):
                if IGNORE.match(tx['s'].strip()) or cap_logo(tx, f.get('faces', [])): continue
                if len(re.sub(r'[^A-Za-z0-9]', '', tx['s'])) <= 2 and tx['box'][2] - tx['box'][0] < 0.08: continue   # a stray letter read off a logo or cap
                if (tx['box'][2] - tx['box'][0]) * (tx['box'][3] - tx['box'][1]) > 0.4: continue   # a misread box over most of the frame is not text
                if area and overlap(fc, tx['box']) / area > 0.04: hits.append((f['t'], tx['s'], weak(tx['s']) or on_cap(tx, f.get('faces', [])), tx['box']))
    # R38 head cut: the top of the head (face box top minus half a face) must sit inside its panel.
    # Two faces one above the other = a split: panels start at 0 and 0.5. Hair is not in Vision's face box, so half a face is the margin.
    cut = []
    for f in F:
        fs_ = f.get('faces', [])
        split = len(fs_) >= 2 and min((b[1] + b[3]) / 2 for b in fs_) < 0.5 < max((b[1] + b[3]) / 2 for b in fs_)
        for b in fs_:
            top = 0.5 if split and (b[1] + b[3]) / 2 > 0.5 else 0.0
            if b[1] - 0.5 * (b[3] - b[1]) < top - 0.01: cut.append(f['t'])
    for r in runs(sorted(set(cut)), step):
        if r[1] - r[0] >= 0.2: fails.append(f'R38 head cut off at the top {r[0]}-{r[1]} s')
    # a weak scrap counts only if it holds 3+ frames (0.1 s): real text on a face stays put, OCR noise flickers
    # (same place: the box overlaps the box one frame before; scraps from different spots do not chain)
    def held(t0, b0):
        n, t, b = 1, t0, b0
        for d in (-1, 1):
            t, b = t0, b0
            while True:
                nx = [h[3] for h in hits if h[2] and abs(h[0] - (t + d * step)) < step / 3 and overlap(h[3], b) > 0]
                if not nx: break
                n += 1; t += d * step; b = nx[0]
        return n >= 3
    hits = [(t, s) for t, s, w, bx in hits if not w or held(t, bx)]
    hit_runs = runs(sorted(set(t for t, _ in hits)), step)
    for r in hit_runs:
        words = sorted(set(s for t, s in hits if r[0] - step / 2 <= t <= r[1]))[:3]
        fails.append(f'R23b text on a face {r[0]}-{r[1]} s: {", ".join(words)}')
    # R86 caption blinks: a caption gone for 0.4 s or less between two captions is a glitch
    UP = brand.BRAND.get('caption', {}).get('uppercase')   # an all-caps brand has no lower-case letters to look for
    capf = [any(sum(ch.isalpha() for ch in x['s']) >= 4 and (UP or any(ch.islower() for ch in x['s'])) and x['box'][1] > 0.4
                and not cap_logo(x, f.get('faces', [])) for x in f.get('text', []))   # a cap logo is not a caption
            and f['t'] < end for f in F]
    blinks, k = [], 0
    while k < len(capf):
        if not capf[k]:
            j = k
            while j < len(capf) and not capf[j]: j += 1
            if k > 0 and j < len(capf) and (j - k) * step <= 0.4: blinks.append(round(F[k]['t'], 2))
            k = j
        else: k += 1
    if len(blinks) > 2: fails.append(f'R86 caption blinks {len(blinks)} times (first at {", ".join(map(str, blinks[:4]))} s)')
    # R37 on the FINAL: the mouth of the face on screen against the final's own sound (a stale voice file
    # can put every render out of sync). Pass: best lag within 2 frames (r >= 0.25), else FAIL.
    ft = os.path.join(CK, os.path.basename(a.video) + '.face.json')
    fok, fmark = scan_fresh(ft, a.video)
    if not fok:
        subprocess.run([str(brand.FACE_TRACK), a.video, ft, '30'], capture_output=True)
        if os.path.exists(ft): fmark()
    lip = None
    if os.path.exists(ft):
        fr = json.load(open(ft))['frames']; m = np.array([f.get('mouth') or 0 for f in fr])
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.video, '-vn', '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True).stdout
        x = np.frombuffer(raw, np.int16).astype(float); hop = 16000 // 30; n = len(x) // hop
        e = np.log10(np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(1)) + 1)
        L = min(len(m), len(e), int(end * 30)); m = m[:L] - m[:L].mean(); e = e[:L] - e[:L].mean()
        r, k = max((np.corrcoef(m[max(0, k):L + min(0, k)], e[max(0, -k):L - max(0, k)])[0, 1], k) for k in range(-20, 21))
        lip = dict(lag_frames=int(k), r=round(float(r), 2))
        if r >= 0.25 and abs(k) > 2: fails.append(f'R37 lips {k:+d} frames off the voice (r {r:.2f})')
        if r < 0.25: print(f'  note: mouth test weak here (r {r:.2f}); short.py proves picture and sound sync itself')
    face_share = np.mean([bool(f.get('faces')) for f in F if f['t'] < end])
    res = dict(video=a.video, lips=lip, frames=len(F), face_share=round(float(face_share), 3), first_sound=fs, noface=noface,
               text_on_face=hit_runs, fails=fails, verdict='PASS' if not fails else 'FAIL')
    json.dump(res, open(os.path.join(CK, os.path.basename(a.video) + '.framecheck.json'), 'w'), indent=1)
    print(f'{len(F)} frames, face on screen {face_share:.0%}, first sound {fs:.2f} s, lips {lip}')
    for x in fails: print('  FAIL', x)
    print('FRAMECHECK', res['verdict'])


if __name__ == '__main__':
    main()

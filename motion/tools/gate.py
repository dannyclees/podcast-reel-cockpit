#!/usr/bin/env python3
"""gate.py <mgs.mp4> [...]: the measured half of the motion gate, on a rendered run (1080 x 960).
The ground is one colour + a texture at 26 %, so anything far from the ground's brightness (more than 105 levels) or coloured (chroma > 45) is graphic.
  EMPTY   the graphic's bounding box covers under 12 % of the panel for more than 0.75 s (R78, J1 "nothing either side")
  LATE    the first 0.5 s has no graphic box of 12 % (R77: a run never opens on empty ground)
  (the last 0.95 s is the glide out of the split and is not judged)
  EDGE    graphic pixels in the outer 14 px band for more than 0.5 s (clipped or jammed against the edge: J10)
  SMALL   the graphic's bounding box spans under 55 % of the panel width for more than 1.5 s (J1 "big and visual")
Prints one line per test and GATE PASS / GATE FAIL. The eye half (the judge list in motion/STYLE.md, brand colours only) is done on the look.py sheet."""
import os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pipeline'))
import brand
G0 = brand.luminance(brand.C['ground']) * 255   # the ground's own brightness, dark or light
FPS = 6
def frames(v):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', v, '-vf', f'fps={FPS},scale=270:240', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 240, 270, 3).astype(int)
def runs(mask, need):
    out, n, start = [], 0, None
    for k, m in enumerate(list(mask) + [False]):
        if m: n += 1; start = k if start is None else start
        else:
            if n / FPS > need: out.append((start / FPS, (start + n) / FPS))
            n, start = 0, None
    return out
ok_all = True
for v in sys.argv[1:]:
    F = frames(v); luma = F.mean(3); chroma = F.max(3) - F.min(3)
    g = (np.abs(luma - G0) > 105) | (chroma > 45)
    gi = g[:, 8:-8, 8:-8]; cols = gi.any(1); rows = gi.any(2)
    span = lambda m: np.array([(np.ptp(np.where(c)[0]) + 1) / len(c) if c.sum() > 2 else 0 for c in m])
    width, height = span(cols), span(rows); box = width * height
    edge = np.concatenate([g[:, :4, :].reshape(len(g), -1), g[:, -4:, :].reshape(len(g), -1), g[:, :, :4].reshape(len(g), -1), g[:, :, -4:].reshape(len(g), -1)], 1).mean(1) > .02
    n = len(g) - int(.95 * FPS); box, width, edge = box[:n], width[:n], edge[:n]
    res = {'EMPTY': runs(box < .12, .75), 'LATE': [(0, .5)] if box[:3].max() < .12 else [], 'EDGE': runs(edge, .5), 'SMALL': runs(width < .55, 1.5)}
    bad = {k: x for k, x in res.items() if x}; ok_all &= not bad
    print(v.split('/')[-2] + '/' + v.split('/')[-1], 'PASS' if not bad else 'FAIL ' + '; '.join(f"{k} {', '.join(f'{a:.1f}-{b:.1f}s' for a, b in x[:4])}" for k, x in bad.items()))
print('GATE PASS' if ok_all else 'GATE FAIL')

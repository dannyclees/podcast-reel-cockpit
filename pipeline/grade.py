#!/usr/bin/env python3
"""grade.py: R95 colour for every speaker video: crisp, and the same from Short to Short.

Two layers, both plain ffmpeg filters:
  1. base fix, MEASURED per speaker from a still: white balance from the near-neutral pixels (low chroma, mid grey),
     exposure from the face box (skin mean luma to ~0.52), gentle contrast, light denoise + unsharp (720p webcams).
  2. optional creative LUT (brand.json grade.lut, a .cube file you own) blended in at grade.lut_strength (0..1).

  grade.py clip <clip dir>                               -> R95: grades each person's <id>.mp4 in place, keeps <id>_ungraded.mp4. Run after cut.py, and again after any re-cut.
  grade.py measure <still.png> [--box x0,y0,x1,y1]       -> prints the base filter for that camera
  grade.py still <in.png> <out.png> [--lut FILE] [--mix 0.6] [--base on|off] [--box ...]
  grade.py vf <still.png> [--lut FILE] [--mix 0.6]       -> prints the full -vf chain to grade that camera's video
"""
import argparse, os, shutil, subprocess, sys, tempfile
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand


def lut_path(lut): return str(brand.ROOT / lut)


def measure(still, box=None):
    a = np.asarray(Image.open(still).convert('RGB')).astype(float) / 255
    h, w, _ = a.shape
    mx, mn = a.max(2), a.min(2); chroma = mx - mn; luma = a @ [0.2126, 0.7152, 0.0722]
    neutral = (chroma < 0.08) & (luma > 0.2) & (luma < 0.85)
    if neutral.mean() > 0.01:
        m = a[neutral].mean(0); g = m.mean() / m
    else:
        g = np.ones(3)
    g = np.clip(g, 0.96, 1.04)   # never a big swing: the room lights are part of the look
    # exposure: the face box if given, else the centre third
    if box: x0, y0, x1, y1 = box
    else: x0, y0, x1, y1 = .33, .2, .67, .6
    face = a[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] * g
    fl = (face @ [0.2126, 0.7152, 0.0722]).mean()
    gamma = float(np.clip(np.log(0.52) / np.log(max(fl, 1e-3)), 0.85, 1.2))
    return dict(r=round(float(g[0]), 4), g=round(float(g[1]), 4), b=round(float(g[2]), 4), gamma=round(gamma, 3), face_luma=round(float(fl), 3))


def base_vf(m):
    return (f"hqdn3d=1.2:1.2:3:3,colorchannelmixer=rr={m['r']}:gg={m['g']}:bb={m['b']},"
            f"eq=gamma={1 / m['gamma']:.3f}:contrast=1.06:saturation=1.04,"
            f"curves=all='0/0.012 0.25/0.235 0.5/0.5 0.75/0.765 1/0.99',unsharp=5:5:0.55:5:5:0")


def full_vf(m, lut=None, mix=1.0, base=True):
    vf = base_vf(m) if base else 'null'
    if lut is None: return vf
    lp = lut_path(lut).replace("'", r"\'").replace(':', r'\:')
    if mix >= 0.999: return f"{vf},lut3d=file='{lp}'"
    return f"{vf},split[a][b];[b]lut3d=file='{lp}'[l];[a][l]blend=all_mode=normal:all_opacity={mix:.2f}"


def frames(f):
    return subprocess.run(['ffprobe', '-v', 'error', '-count_packets', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', f],
                          capture_output=True, text=True).stdout.strip()


def clip(D):
    """R95: grade each person's video in the clip. The frame count must not change, or the sync gate fails later."""
    g = brand.BRAND.get('grade') or {}; lut = g.get('lut'); mix = float(g.get('lut_strength', 0.6))
    for who in brand.IDS:
        cur = os.path.join(D, f'{who}.mp4'); raw = os.path.join(D, f'{who}_ungraded.mp4')
        if not os.path.exists(cur): continue
        src = raw if os.path.exists(raw) and os.path.getmtime(raw) >= os.path.getmtime(cur) - 1 else cur   # a new cut replaces the old original
        if src == cur: shutil.copy2(cur, raw); src = raw
        with tempfile.TemporaryDirectory() as tmp:
            still = os.path.join(tmp, 's.png'); out = os.path.join(tmp, 'o.mp4')
            dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{dur / 2:.2f}', '-i', src, '-frames:v', '1', still], check=True)
            vf = full_vf(measure(still), lut, mix)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-filter_complex', vf, '-an', '-r', '30', '-c:v', 'libx264', '-preset', 'fast', '-crf', '15',
                            '-pix_fmt', 'yuv420p', '-g', '15', out], check=True)
            a, b = frames(src), frames(out)
            if a != b: sys.exit(f'{who}: grade changed the frame count ({a} to {b}), kept the original')
            shutil.move(out, cur)
        print(f'{who}: graded ({a} frames{", LUT at " + str(mix) if lut else ""})')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('a'); ap.add_argument('b', nargs='?')
    ap.add_argument('--lut'); ap.add_argument('--mix', type=float, default=1.0); ap.add_argument('--base', default='on')
    ap.add_argument('--box')
    o = ap.parse_args(); box = [float(x) for x in o.box.split(',')] if o.box else None
    if o.cmd == 'clip': return clip(os.path.abspath(o.a))
    m = measure(o.a, box)
    if o.cmd == 'measure': print(m, '\n' + base_vf(m)); return
    vf = full_vf(m, o.lut, o.mix, o.base == 'on')
    if o.cmd == 'vf': print(vf); return
    if o.cmd == 'still':
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', o.a, '-filter_complex', vf, '-frames:v', '1', o.b], check=True)


if __name__ == '__main__':
    main()

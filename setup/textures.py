#!/usr/bin/env python3
"""textures.py: draws the show's texture pack from its brand colours. numpy + Pillow only.

Same show name + seed + colours = the same pixels, every time. A new seed = a new pack.
Styles: grain, halftone, ink, paper, mesh, grid, user_image. Every plate keeps its middle quiet so text reads,
works on a light or a dark ground, and is dithered so soft gradients never band.

Use from build_brand.py, or by hand:
  python3 setup/textures.py --style ink --ground 0E0E10 --accent 3DDC97 --out /some/folder
"""
import argparse
import colorsys
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

STYLES = ('grain', 'halftone', 'ink', 'paper', 'mesh', 'grid', 'user_image')

# Plate name -> (width, height, composition). Sizes are fixed by the pipeline and the kits.
PLATES = {
    'band': (1376, 768, 'band'),
    'tall_a': (768, 1376, 'tall_a'),
    'tall_b': (768, 1376, 'tall_b'),
    'card': (1584, 672, 'card'),
    'card_wide': (1584, 672, 'card_wide'),
    'g1': (576, 324, 'g1'),
    'g2': (576, 324, 'g2'),
    'g3': (576, 324, 'g3'),
    'g4': (576, 324, 'g4'),
    'g5': (576, 324, 'g5'),
    'ground': (1080, 960, 'ground'),
    'app_band': (1600, 893, 'band'),
}


# ---------- small maths ----------

def rng_for(*parts):
    h = hashlib.sha256('|'.join(str(p) for p in parts).encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], 'big'))


def rgb(hex_str):
    s = hex_str.strip().lstrip('#')
    return np.array([int(s[i:i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    if np.ndim(t) == 2:
        t = t[..., None]
    return a * (1 - t) + b * t


def luminance(c):
    c = np.asarray(c, dtype=np.float64)
    lin = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2])


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def spectral(h, w, beta, rng, ax=1.0, ay=1.0, f0=0.002):
    """Tile-free noise with a chosen softness, in 0..1. High beta = soft clouds, low beta = fine. ax/ay stretch it."""
    white = rng.standard_normal((h, w), dtype=np.float32)
    fy = np.fft.fftfreq(h)[:, None] * ay
    fx = np.fft.rfftfreq(w)[None, :] * ax
    amp = (fx * fx + fy * fy + f0 * f0) ** (-beta / 2)
    n = np.fft.irfft2(np.fft.rfft2(white) * amp, s=(h, w)).real
    n = (n - n.mean()) / (n.std() + 1e-9)
    return 1 / (1 + np.exp(-1.7 * n))


def blur(a, sigma):
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi * sigma) ** 2 * (fx * fx + fy * fy))
    return np.fft.irfft2(np.fft.rfft2(a) * g, s=(h, w)).real


def walk1d(n, rng, soft):
    """A smooth 1D wander, about 0..1."""
    w = np.convolve(rng.standard_normal(n + 2 * soft), np.hanning(2 * soft + 1), mode='same')[soft:soft + n]
    w = (w - w.mean()) / (w.std() + 1e-9)
    return 0.5 + 0.22 * w


def hue_shift(c, deg):
    h, l, s = colorsys.rgb_to_hls(*[float(v) for v in c])
    return np.array(colorsys.hls_to_rgb((h + deg / 360) % 1, l, s), dtype=np.float32)


def to_oklab(c):
    c = np.clip(c, 0, 1)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = lin[..., 0], lin[..., 1], lin[..., 2]
    l = np.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = np.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = np.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return np.stack([0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                     1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                     0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s], -1)


def from_oklab(c):
    L, a, b = c[..., 0], c[..., 1], c[..., 2]
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    lin = np.stack([4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
                    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
                    -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s], -1)
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)


# ---------- where the texture lives on each plate ----------

def edge_field(w, h, kind, rng):
    """Density 0..1: 1 where the texture is loud, 0 where text sits. Edges wander so it never reads as a clean vignette."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = x / (w - 1), y / (h - 1)
    ar = w / h
    wob = spectral(h, w, 2.1, rng) - 0.5
    wob2 = spectral(h, w, 1.6, rng) - 0.5
    su, sv = u + 0.11 * wob / max(ar, 1), v + 0.11 * wob2 * min(ar, 1)
    left, right = su, 1 - su
    top, bot = sv, 1 - sv

    def side(d, reach):
        return 1 - smooth(0.0, reach, d)

    def combine(*fields):
        out = np.zeros_like(u)
        for f in fields:
            out = 1 - (1 - out) * (1 - f)
        return out

    def quiet(rx, ry, soft=0.34):
        r = np.sqrt(((u - 0.5) / rx) ** 2 + ((v - 0.5) / ry) ** 2)
        return smooth(1 - soft, 1 + soft * 0.4, r)

    lean_a, lean_b = float(rng.uniform(0.75, 1.0)), float(rng.uniform(0.5, 0.85))
    if kind == 'band':
        d = combine(lean_a * side(left, 0.24), lean_b * side(right, 0.19)) * quiet(0.40, 0.72)
    elif kind == 'tall_a':
        d = combine(side(left, 0.30) * lean_a * (0.45 + 0.55 * v), side(right, 0.24) * lean_b, 0.7 * side(bot, 0.12)) * quiet(0.52, 0.36)
    elif kind == 'tall_b':
        d = combine(side(right, 0.34) * (1 - 0.55 * v), side(left, 0.26) * (0.2 + 0.8 * v), 0.65 * side(top, 0.11)) * quiet(0.50, 0.34)
    elif kind == 'card':
        d = combine(lean_a * side(left, 0.13), lean_b * side(right, 0.10), 0.40 * side(top, 0.13), 0.40 * side(bot, 0.13)) * quiet(0.50, 0.66, 0.24)
    elif kind == 'card_wide':
        d = combine(side(left, 0.20) * lean_a, 0.40 * side(right, 0.06), 0.30 * side(bot, 0.15)) * quiet(0.46, 0.62, 0.24)
    elif kind == 'g1':
        d = np.clip(1 - np.sqrt((su / 0.82) ** 2 + (bot / 0.95) ** 2), 0, 1) ** 0.7
    elif kind == 'g2':
        d = combine(side(left, 0.34), side(right, 0.34)) * (0.55 + 0.45 * smooth(0.2, 0.8, np.abs(u - 0.5) * 2))
    elif kind == 'g3':
        d = side(top, 0.72) ** 1.2
    elif kind == 'g4':
        band = np.abs((su - 0.5) * 0.8 + (sv - 0.5) * 1.0)
        d = 1 - smooth(0.02, 0.36, band)
    elif kind == 'g5':
        d = np.full_like(u, 0.30) * (0.5 + wob * 1.4 + 0.5) + 0.25 * side(np.minimum(left, right), 0.2)
    elif kind == 'ground':
        d = combine(lean_a * side(left, 0.26), lean_b * side(right, 0.22), 0.40 * side(bot, 0.28)) * quiet(0.46, 0.50)
    else:
        raise ValueError('unknown composition: ' + kind)
    return np.clip(d, 0, 1).astype(np.float32)


# ---------- the styles ----------
# Each one takes density D and returns an RGB float image over the ground.

def _inks(p):
    """The two strongest colours for this ground. A pale accent on a pale ground would vanish, so swap it out."""
    a, d = p['accent'], p['deep']
    if contrast(a, p['ground']) < 1.5:
        a, d = d, a
    if contrast(d, p['ground']) < 1.25:
        d = mix(a, p['ground'], 0.35)
    return a, d


def style_grain(D, p, rng):
    """Grainy gradient, like a riso print: colour built out of dots of noise."""
    h, w = D.shape
    a, d = _inks(p)
    cloud = spectral(h, w, 2.3, rng)
    tone = np.clip(D * (0.45 + 0.75 * cloud), 0, 0.86) ** 1.35
    n1, n2 = rng.random((h, w), dtype=np.float32), rng.random((h, w), dtype=np.float32)
    low = blur((n1 < tone).astype(np.float32), 0.55)
    high = blur((n2 < tone ** 2.0 * 0.8).astype(np.float32), 0.55)
    out = mix(np.broadcast_to(p['ground'], (h, w, 3)), d, np.clip(low * 0.92, 0, 1))
    out = mix(out, a, np.clip(high * 1.05, 0, 1))
    speck = rng.standard_normal((h, w), dtype=np.float32) * 0.010
    return out + speck[..., None]


def style_halftone(D, p, rng):
    """Print dots, two off-register screens. Dot size follows the density."""
    h, w = D.shape
    a, d = _inks(p)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    cloud = spectral(h, w, 2.4, rng)
    tone = np.clip(D * (0.42 + 0.46 * cloud), 0, 0.62)
    cell = float(rng.uniform(12.0, 19.0)) * (w * h / (1376 * 768)) ** 0.18
    base_angle = float(rng.choice([15, 22, 30, 45, 60]))
    out = np.broadcast_to(p['ground'], (h, w, 3)).copy()

    def screen(angle, scale, t, col, gain):
        th = np.deg2rad(angle)
        ca, sa = np.cos(th), np.sin(th)
        c = cell * scale
        fa = ((x * ca + y * sa) / c) % 1 - 0.5
        fb = ((-x * sa + y * ca) / c) % 1 - 0.5
        dist = np.sqrt(fa * fa + fb * fb) * c
        r = c * 0.74 * np.sqrt(np.clip(t, 0, 1))
        cov = np.clip(r + 0.5 - dist, 0, 1) * (r > 0.45)
        return mix(out, col, cov * gain)

    out = screen(base_angle + 34, 1.0, tone * 0.85, d, 0.95)
    out = screen(base_angle, 1.0, np.clip(tone - 0.08, 0, 1), a, 1.0)
    return out


def style_ink(D, p, rng):
    """Organic brushed strokes, built from layered noise. They run dry where the density falls away."""
    h, w = D.shape
    a, d = _inks(p)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    tilt = float(rng.uniform(-0.10, 0.10))
    xr = x + (y - h / 2) * tilt
    bristle = spectral(h, w, 0.9, rng, ax=1.0, ay=26.0, f0=0.004)
    fine = spectral(h, w, 0.55, rng, ax=1.0, ay=14.0, f0=0.01)
    bleed = spectral(h, w, 1.5, rng)
    layers = [np.zeros((h, w), np.float32), np.zeros((h, w), np.float32)]
    # strokes start where the density is, so they gather at the edges and leave the middle alone
    marg = D.mean(0) ** 2 + 1e-6
    n = max(8, int(w / 130))
    for k in range(n):
        wid = float(rng.uniform(0.022, 0.066)) * max(w, h * 0.7)
        centre = float(rng.choice(w, p=marg / marg.sum()))
        path = (walk1d(h, rng, max(60, h // 3)) - 0.5) * wid * 2.6 + centre
        thick = (0.60 + 0.8 * walk1d(h, rng, max(40, h // 5))) * wid
        dd = (xr - path[y.astype(int)]) / thick[y.astype(int)]
        v0, v1 = sorted(rng.uniform(-0.1, 1.1, 2))
        if v1 - v0 < 0.45:
            v0, v1 = max(-0.1, v0 - 0.3), min(1.1, v1 + 0.3)
        vv = y / h
        env = smooth(v0, v0 + 0.14, vv) * (1 - smooth(v1 - 0.18, v1, vv))
        prof = np.exp(-np.abs(dd) ** 3.2) * env
        shift = (path[y.astype(int)]).astype(int)
        br = bristle[y.astype(int), (x.astype(int) - shift) % w]
        fn = fine[y.astype(int), (x.astype(int) - shift) % w]
        th = 1.02 - 0.62 * D ** 0.85                     # dry where quiet, wet where loud
        body = prof * (0.30 + 0.55 * br + 0.35 * fn) + 0.10 * (bleed - 0.5)
        cov = smooth(th - 0.045, th + 0.045, body)
        layers[k % 2] = np.maximum(layers[k % 2], cov)
    deep_l = blur(layers[1], 0.6)
    acc_l = blur(layers[0], 0.5)
    out = mix(np.broadcast_to(p['ground'], (h, w, 3)), d, np.clip(deep_l, 0, 1))
    out = mix(out, a, np.clip(acc_l, 0, 1))
    wash = smooth(0.1, 0.9, D) * 0.07 * spectral(h, w, 2.2, rng)
    return mix(out, d, wash)


def style_paper(D, p, rng):
    """Paper collage: fibre in the stock, torn strips of colour at the edges."""
    h, w = D.shape
    a, d = _inks(p)
    dark = luminance(p['ground']) < 0.25
    mott = spectral(h, w, 2.2, rng) - 0.5
    base = p['ground'] + mott[..., None] * (0.030 if dark else 0.022)
    # fibres: short curved hairs in the stock
    S = 2
    fib_hi = Image.new('L', (w * S, h * S), 0)
    fib_lo = Image.new('L', (w * S, h * S), 0)
    dr_hi, dr_lo = ImageDraw.Draw(fib_hi), ImageDraw.Draw(fib_lo)
    n = int(w * h / 950)
    xs, ys = rng.random(n) * w * S, rng.random(n) * h * S
    th, ln, cv = rng.random(n) * np.pi * 2, rng.uniform(14, 70, n), rng.normal(0, 0.03, n)
    tone = rng.integers(70, 240, n)
    for i in range(n):
        pts, cx, cy, t = [], float(xs[i]), float(ys[i]), float(th[i])
        for _ in range(7):
            pts.append((cx, cy))
            cx += np.cos(t) * ln[i] / 6
            cy += np.sin(t) * ln[i] / 6
            t += cv[i] * 6
        (dr_hi if i % 3 else dr_lo).line(pts, fill=int(tone[i]), width=1)
    hi = np.asarray(fib_hi.resize((w, h), Image.LANCZOS), np.float32) / 255
    lo = np.asarray(fib_lo.resize((w, h), Image.LANCZOS), np.float32) / 255
    k = 0.10 if dark else 0.06
    out = base + (hi[..., None] * k * (0.5 + D[..., None])) * (1 if dark else -1) + (lo[..., None] * k * (1 if dark else 1) * 0.0)
    # torn strips
    rough = 0.55 * spectral(h, w, 1.9, rng) + 0.35 * spectral(h, w, 1.2, rng) + 0.10 * spectral(h, w, 0.5, rng)
    f = D + 0.30 * (rough - 0.5)
    t1, t2 = float(rng.uniform(0.40, 0.48)), float(rng.uniform(0.66, 0.74))
    m1, m2 = smooth(t1 - 0.004, t1 + 0.006, f), smooth(t2 - 0.004, t2 + 0.006, f)
    rim1 = smooth(t1 - 0.004, t1 + 0.004, f) * (1 - smooth(t1 + 0.012, t1 + 0.030, f))
    rim2 = smooth(t2 - 0.004, t2 + 0.004, f) * (1 - smooth(t2 + 0.012, t2 + 0.030, f))
    shadow_col = np.array([0, 0, 0], np.float32) if dark else mix(p['ground'], d, 0.5) * 0.72
    shadow1 = np.clip(np.roll(blur(m1, 5.0), 4, axis=0) - m1, 0, 1)
    out = mix(out, shadow_col, shadow1 * (0.55 if dark else 0.32))
    fibre_tint = 0.5 + hi * 0.8 - lo * 0.5
    strip = mix(d, a, smooth(0.25, 0.8, spectral(h, w, 2.4, rng)) * 0.35)
    out = mix(out, strip * (0.93 + 0.14 * fibre_tint[..., None]), m1)
    rim_col = mix(p['paper'], np.array([1, 1, 1], np.float32), 0.25)
    out = mix(out, rim_col, rim1 * (0.70 + 0.3 * hi))
    shadow2 = np.clip(np.roll(blur(m2, 4.0), 3, axis=0) - m2, 0, 1)
    out = mix(out, shadow_col, shadow2 * 0.4)
    out = mix(out, a * (0.94 + 0.12 * fibre_tint[..., None]), m2)
    out = mix(out, rim_col, rim2 * (0.65 + 0.3 * hi))
    return out


def style_mesh(D, p, rng):
    """Soft colour blobs melted into the ground, mixed in a perceptual colour space so they stay clean."""
    h, w = D.shape
    a, d = _inks(p)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = x / w, y / h
    du, dv = spectral(h, w, 2.6, rng) - 0.5, spectral(h, w, 2.6, rng) - 0.5
    uu, vv = u + 0.22 * du, v + 0.22 * dv
    ground_lab = to_oklab(p['ground'])
    field = np.broadcast_to(ground_lab, (h, w, 3)).copy()
    # a colourful ground pulls the extra blobs toward itself, so the mix stays in the family. A neutral ground lets the hue wander a little.
    tint = to_oklab(p['ground'])
    if float(np.hypot(tint[1], tint[2])) > 0.06:
        cols = [a, d, mix(a, p['ground'], 0.35), mix(d, p['ground'], 0.30), d, a]
    else:
        cols = [a, d, hue_shift(a, float(rng.uniform(14, 30))), hue_shift(a, -float(rng.uniform(14, 30))), d, a]
    # blobs sit where the density is highest
    flat = D.ravel() ** 2 + 1e-5
    picks = rng.choice(flat.size, len(cols), p=flat / flat.sum())
    ar = w / h
    for i, idx in enumerate(picks):
        cy, cx = np.unravel_index(int(idx), D.shape)
        cu, cv_ = cx / w, cy / h
        s = float(rng.uniform(0.12, 0.26))
        r2 = ((uu - cu) * max(ar, 1)) ** 2 + ((vv - cv_) * max(1 / ar, 1)) ** 2
        amt = np.exp(-r2 / (2 * s * s)) * float(rng.uniform(0.7, 1.0))
        field = field + (to_oklab(cols[i]) - field) * amt[..., None]
    gate = smooth(0.02, 0.62, D)
    out_lab = ground_lab + (field - ground_lab) * gate[..., None]
    return from_oklab(out_lab)


def style_grid(D, p, rng):
    """Fine ruled lines with filled cells that thicken toward the edges, like a technical drawing turning into data."""
    h, w = D.shape
    a, d = _inks(p)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    cell = float(rng.choice([20, 24, 28, 32]))
    major = int(rng.choice([4, 5]))
    ox, oy = float(rng.uniform(0, cell)), float(rng.uniform(0, cell))
    xc, yc = (x + ox) / cell, (y + oy) / cell
    dist = np.minimum(np.abs(xc - np.round(xc)), np.abs(yc - np.round(yc))) * cell
    line = np.clip(1.0 - dist, 0, 1) * 0.75
    xm, ym = (x + ox) / (cell * major), (y + oy) / (cell * major)
    dist_m = np.minimum(np.abs(xm - np.round(xm)), np.abs(ym - np.round(ym))) * cell * major
    line_m = np.clip(1.3 - dist_m, 0, 1)
    ink = p['on_ground']
    out = np.broadcast_to(p['ground'], (h, w, 3)).copy()
    # filled cells: chance rises with density, each cell one flat value
    ci, cj = np.floor(yc).astype(int), np.floor(xc).astype(int)
    gh, gw = int(ci.max() - ci.min() + 2), int(cj.max() - cj.min() + 2)
    rnd, pick = rng.random((gh, gw), dtype=np.float32), rng.random((gh, gw), dtype=np.float32)
    ci, cj = ci - ci.min(), cj - cj.min()
    cloud = spectral(h, w, 2.2, rng)
    tone = np.clip(D * (0.5 + 1.0 * cloud), 0, 1)
    # the density at each cell's own sample point, so a cell is either filled or not
    filled = (rnd[ci, cj] < tone ** 1.5 * 0.92).astype(np.float32)
    inset = np.clip(np.minimum(np.abs(xc - np.round(xc)), np.abs(yc - np.round(yc))) * cell - 1.0, 0, 1)
    mid = mix(d, a, (pick[ci, cj] > 0.55).astype(np.float32))
    out = mix(out, mid, filled * inset * 0.96)
    fade = smooth(0.0, 0.42, D)
    out = mix(out, ink, line * (0.05 + 0.20 * fade) * (1 - filled * 0.6))
    out = mix(out, ink, line_m * (0.05 + 0.38 * fade))
    # small ticks on the major crossings
    cross = np.clip(1.4 - np.abs(xm - np.round(xm)) * cell * major, 0, 1) * (np.abs(ym - np.round(ym)) * cell * major < 5) + \
        np.clip(1.4 - np.abs(ym - np.round(ym)) * cell * major, 0, 1) * (np.abs(xm - np.round(xm)) * cell * major < 5)
    out = mix(out, a, np.clip(cross, 0, 1) * smooth(0.04, 0.3, D))
    return out


def style_user_image(D, p, rng, image=None):
    """The owner's own image: cropped, graded to the brand colours, and quietened in the middle."""
    if image is None:
        raise SystemExit('Texture style is user_image but no image was given. Set texture.user_image in brand/brand.json.')
    h, w = D.shape
    src = Image.open(image).convert('RGB')
    # a different crop per plate, so the plates are not copies of each other
    fx, fy = float(rng.uniform(0.15, 0.85)), float(rng.uniform(0.15, 0.85))
    crop = ImageOps.fit(src, (w, h), Image.LANCZOS, centering=(fx, fy))
    im = np.asarray(crop, np.float32) / 255
    lum = np.clip(0.2126 * im[..., 0] + 0.7152 * im[..., 1] + 0.0722 * im[..., 2], 0, 1)
    lum = smooth(np.percentile(lum, 2), np.percentile(lum, 98) + 1e-3, lum)
    a, d = _inks(p)
    dark = luminance(p['ground']) < 0.25
    ramp_t = lum if dark else 1 - lum
    lo = np.broadcast_to(p['ground'], (h, w, 3))
    graded = mix(lo, d, smooth(0.05, 0.55, ramp_t))
    graded = mix(graded, a, smooth(0.45, 0.95, ramp_t))
    graded = mix(graded, im, 0.14)
    return mix(lo, graded, smooth(0.04, 0.55, D))


RENDER = {'grain': style_grain, 'halftone': style_halftone, 'ink': style_ink, 'paper': style_paper, 'mesh': style_mesh, 'grid': style_grid}


def render(style, w, h, comp, pal, show, seed, strength=0.5, user_image=None):
    """Returns an RGB uint8 array."""
    if style not in STYLES:
        raise SystemExit('Unknown texture style "%s". Pick one of: %s.' % (style, ', '.join(STYLES)))
    rng = rng_for(show, seed, style, comp, w, h)
    D = edge_field(w, h, comp, rng)
    D = np.clip(D * (0.55 + 0.9 * float(strength)), 0, 1)
    if style == 'user_image':
        out = style_user_image(D, pal, rng, user_image)
    else:
        out = RENDER[style](D, pal, rng)
    # triangular dither: one step of noise before rounding, so a soft gradient never shows bands
    tri = (rng.random((h, w, 3), dtype=np.float32) - rng.random((h, w, 3), dtype=np.float32)) / 255
    return (np.clip(out + tri, 0, 1) * 255 + 0.5).astype(np.uint8)


def render_grain(k, pal, show, seed, style):
    """A 540 x 540 RGBA film-grain plate that tiles. Always light specks: on a dark ground they lift through screen.
    On a light ground the kits use --grain-filter: invert(1) with multiply, which turns them into soft dark specks,
    so the tone here is set so the inverted colour lands near the show's text colour."""
    size = 540
    rng = rng_for(show, seed, style, 'grain', k)
    fine = {'paper': 1.0, 'grid': 0.45, 'halftone': 0.8, 'mesh': 0.5}.get(style, 0.6)
    n = rng.standard_normal((size, size), dtype=np.float32)
    n = blur(n, fine)
    n = (n - n.mean()) / (n.std() + 1e-9)
    alpha = np.clip(np.abs(n) ** 1.45 * 0.42, 0, 1) * (0.72 + 0.56 * spectral(size, size, 2.0, rng))
    dark = luminance(pal['ground']) < 0.25
    tone = np.array([1.0, 1.0, 1.0], np.float32) if dark else 1 - pal['on_ground'] * 0.6
    out = np.zeros((size, size, 4), np.float32)
    out[..., :3] = tone
    out[..., 3] = np.clip(alpha, 0, 1)
    return (out * 255 + 0.5).astype(np.uint8)


def palette(colors):
    keys = {'ground': 'ground', 'on_ground': 'on_ground', 'accent': 'accent', 'deep': 'accent_deep', 'paper': 'paper'}
    return {k: rgb(colors[v]) for k, v in keys.items()}


def build_pack(colors, show, seed, style, strength, user_image, outdir, app_ink=None, app_surface=None):
    """Writes every plate. outdir gets textures/... Returns the list of files written.
    The app shows band.jpg on its dark ink bands, so that one plate is drawn on app_ink, whatever the show's ground is."""
    outdir = Path(outdir)
    tex = outdir / 'textures'
    (tex / 'grain').mkdir(parents=True, exist_ok=True)
    pal = palette(colors)
    out = []
    for name, (w, h, comp) in PLATES.items():
        use = pal
        if name == 'app_band' and app_ink:
            use = dict(pal, ground=rgb(app_ink), on_ground=rgb(app_surface or '#FFFFFF'))
        arr = render(style, w, h, comp, use, show, seed, strength, user_image)
        im = Image.fromarray(arr)
        if name in ('ground', 'app_band') or name[0] == 'g':
            p = tex / (name + '.jpg')
            im.save(p, quality=92, subsampling=0)
        else:
            p = tex / (name + '.png')
            im.save(p, optimize=True)
        out.append(p)
    for k in range(4):
        p = tex / 'grain' / ('grain_%d.png' % k)
        Image.fromarray(render_grain(k, pal, show, seed, style)).save(p, optimize=True)
        out.append(p)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Draw a texture pack.')
    ap.add_argument('--style', default='grain', choices=STYLES)
    ap.add_argument('--ground', default='101012')
    ap.add_argument('--on-ground', default='FFFFFF')
    ap.add_argument('--accent', default='E8A33D')
    ap.add_argument('--deep', default='A5641B')
    ap.add_argument('--paper', default='F5F2EA')
    ap.add_argument('--show', default='Example Show')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--strength', type=float, default=0.5)
    ap.add_argument('--image', default=None)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    cols = {'ground': '#' + args.ground, 'on_ground': '#' + args.on_ground, 'accent': '#' + args.accent, 'accent_deep': '#' + args.deep, 'paper': '#' + args.paper}
    for f in build_pack(cols, args.show, args.seed, args.style, args.strength, args.image, args.out):
        print(f)

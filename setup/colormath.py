"""colormath.py: real colour maths for the brand build. Standard library only.

WCAG contrast, OKLCH lightness moves, and deriving a full set of tokens from a ground and an accent.
"""
import math
import re

HEX = re.compile(r'^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')
RGBA = re.compile(r'^rgba?\(\s*([\d.]+)\s*[, ]\s*([\d.]+)\s*[, ]\s*([\d.]+)\s*(?:[,/]\s*([\d.]+%?)\s*)?\)$', re.I)


def is_color(s):
    return isinstance(s, str) and bool(HEX.match(s.strip()) or RGBA.match(s.strip()))


def parse(s):
    """Any hex or rgba() string -> (r, g, b, a) with r g b in 0..255 and a in 0..1."""
    s = s.strip()
    m = HEX.match(s)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    m = RGBA.match(s)
    if m:
        a = m.group(4)
        a = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith('%') else float(a))
        return (float(m.group(1)), float(m.group(2)), float(m.group(3)), a)
    raise ValueError('not a colour: %r' % s)


def to_hex(c):
    return '#%02X%02X%02X' % tuple(int(round(max(0, min(255, v)))) for v in c[:3])


def to_rgba(c, a):
    txt = ('%.2f' % a).lstrip('0').rstrip('0').rstrip('.') or '0'
    return 'rgba(%d,%d,%d,%s)' % (round(c[0]), round(c[1]), round(c[2]), txt)


def over(fg, bg):
    """Composite a colour with alpha over an opaque one."""
    a = fg[3] if len(fg) > 3 else 1.0
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3)) + (1.0,)


def _lin(v):
    v /= 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _gam(v):
    v = max(0.0, min(1.0, v))
    return 255.0 * (12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055)


def luminance(c):
    return 0.2126 * _lin(c[0]) + 0.7152 * _lin(c[1]) + 0.0722 * _lin(c[2])


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def oklch(c):
    r, g, b = _lin(c[0]), _lin(c[1]), _lin(c[2])
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = [math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s)]
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    A = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    B = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return (L, math.hypot(A, B), math.degrees(math.atan2(B, A)) % 360)


def _from_oklab(L, A, B):
    l = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3
    m = (L - 0.1055613458 * A - 0.0638541728 * B) ** 3
    s = (L - 0.0894841775 * A - 1.2914855480 * B) ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def from_oklch(L, C, H):
    """OKLCH -> sRGB. Chroma is pulled in until the colour fits the screen, so the hue holds."""
    L = max(0.0, min(1.0, L))
    A, B = math.cos(math.radians(H)), math.sin(math.radians(H))
    lo, hi, c = 0.0, C, C
    for _ in range(18):
        lin = _from_oklab(L, A * c, B * c)
        if all(-0.0005 <= v <= 1.0005 for v in lin):
            lo = c
            c = (lo + hi) / 2 if hi > lo else c
            if abs(hi - lo) < 1e-3:
                break
        else:
            hi = c
            c = (lo + hi) / 2
    lin = _from_oklab(L, A * lo, B * lo)
    return tuple(_gam(v) for v in lin) + (1.0,)


def mix(a, b, t):
    """Perceptual mix in OKLab. t=0 gives a, t=1 gives b."""
    la, ca, ha = oklch(a)
    lb, cb, hb = oklch(b)
    A1, B1 = ca * math.cos(math.radians(ha)), ca * math.sin(math.radians(ha))
    A2, B2 = cb * math.cos(math.radians(hb)), cb * math.sin(math.radians(hb))
    L, A, B = la + (lb - la) * t, A1 + (A2 - A1) * t, B1 + (B2 - B1) * t
    return from_oklch(L, math.hypot(A, B), math.degrees(math.atan2(B, A)) % 360)


def fix_lightness(fg, bgs, want):
    """Move fg's lightness the shortest way until it reads at `want` against every background. Hue holds.
    Returns (colour, ok). bgs = a list of opaque colours."""
    def score(c):
        return min(contrast(c, b) for b in bgs)
    if score(fg) >= want:
        return fg, True
    L, C, H = oklch(fg)
    best = None
    for step in range(1, 201):
        d = step * 0.005
        for sign in (1, -1):
            cand = from_oklch(L + sign * d, C, H)
            if score(cand) >= want + 0.02:
                return tuple(int(round(v)) for v in cand[:3]) + (1.0,), True
            if best is None or score(cand) > score(best):
                best = cand
    return best, False


def better_on(bg, tint_h, tint_c=0.012):
    """The near-white or near-black that reads better on bg, with a whisper of the brand's hue."""
    light = from_oklch(0.985, tint_c * 0.6, tint_h)
    dark = from_oklch(0.17, tint_c * 1.4, tint_h)
    return light if contrast(light, bg) >= contrast(dark, bg) else dark


def hue_gap(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def derive(given, caption_box='auto'):
    """Fill every missing render token from what was given. given needs ground and accent.
    Returns {key: colour string} for the missing keys only."""
    g = parse(given['ground'])
    a = parse(given['accent'])
    gL, gC, gH = oklch(g)
    aL, aC, aH = oklch(a)
    dark = luminance(g) < 0.18
    out = {}
    have = dict(given)

    def get(k):
        return parse(have[k])

    def put(k, c):
        if k not in have:
            v = c if isinstance(c, str) else to_hex(c)
            out[k] = v
            have[k] = v

    put('on_ground', better_on(g, aH))
    if dark or gL < 0.86:      # a dark or a saturated ground gets a clean near-white card, never a muddy tint of itself
        put('paper', from_oklch(0.965, 0.012, aH))
    else:
        put('paper', from_oklch(min(0.995, gL + 0.05), max(0.002, gC * 0.35), gH))
    put('on_paper', better_on(get('paper'), aH, 0.016))
    panel_L = gL + 0.065 if dark else gL - 0.075
    put('panel', from_oklch(panel_L, max(gC, 0.006), gH))
    put('on_panel', better_on(get('panel'), aH))
    put('on_accent', better_on(a, aH, 0.02))
    deep_L = aL - 0.17 if aL > 0.38 else aL - 0.09
    # darkening a bright yellow straight down gives olive, so it leans toward orange as it falls
    deep_H = aH - 38 if aL > 0.80 and 80 < aH < 125 else aH
    put('accent_deep', from_oklch(max(0.16, deep_L), aC, deep_H))
    alarm_H = 25.0 if hue_gap(aH, 25.0) > 34 else 75.0
    alarm = from_oklch(0.66 if dark else 0.55, 0.20, alarm_H)
    put('alarm', alarm)
    mute = mix(get('on_paper'), get('paper'), 0.48)
    put('mute', mute)
    # caption box. Light box only when asked for, or on a light ground with no choice made.
    use_light = caption_box == 'light' or (caption_box == 'auto' and not dark)
    if use_light:
        box = get('paper')
        put('cap_box', to_rgba(box, 0.94))
    else:
        box = g if dark else from_oklch(0.17, 0.012, aH)
        put('cap_box', to_rgba(box, 0.86))
    box_over = over(parse(have['cap_box']), (128, 128, 128, 1.0))
    put('cap_text', better_on(box_over, aH))
    put('cap_spoken', a)
    return out


def derive_app(colors):
    """Tokens for the approval app: always a calm light surface, tinted toward the brand."""
    a = parse(colors['accent'])
    aL, aC, aH = oklch(a)
    n = 0.006
    surface = from_oklch(0.998, 0.001, aH)
    tokens = {
        'bg': to_hex(from_oklch(0.962, n, aH)), 'bg_2': to_hex(from_oklch(0.930, n * 1.2, aH)),
        'surface': to_hex(surface),
        'line': to_hex(from_oklch(0.905, n * 1.2, aH)), 'line_2': to_hex(from_oklch(0.855, n * 1.4, aH)),
        'ink': to_hex(from_oklch(0.20, 0.012, aH)), 'ink_2': to_hex(from_oklch(0.34, 0.012, aH)),
        'mute': to_hex(from_oklch(0.53, 0.012, aH)),
        'accent': colors['accent'],
    }
    soft = mix(a, surface, 0.80)
    tokens['accent_soft'] = to_hex(soft)
    ink, _ = fix_lightness(a, [soft, surface], 4.5)
    tokens['accent_ink'] = to_hex(ink)
    return tokens


def run_checks(colors, app):
    """Check every pair that carries text. Moves lightness of the foreground when it fails, and says so.
    Returns (colors, app, checks, changes). The caption box can sit over any picture, so it is tested over black and over white."""
    colors, app = dict(colors), dict(app)
    checks, changes = [], []

    def one(label, key, bgs, want, tok=colors, why=''):
        fg = parse(tok[key])
        before = min(contrast(fg, b) for b in bgs)
        fixed = False
        if before < want:
            new, ok = fix_lightness(fg, bgs, want)
            if ok:
                tok[key] = to_hex(new)
                changes.append('%s: moved %s from %s to %s (%.1f:1 was too low, needs %.1f:1).' % (label, key, to_hex(fg), tok[key], before, want))
                fixed = True
            else:
                changes.append('%s: could not reach %.1f:1 by moving %s. Pick a different background.' % (label, want, key))
        after = min(contrast(parse(tok[key]), b) for b in bgs)
        checks.append({'name': label, 'fg': to_hex(parse(tok[key])), 'bg': to_hex(bgs[0]), 'ratio': round(after, 2), 'min': want, 'ok': after >= want, 'fixed': fixed, 'why': why})

    def p(k):
        return parse(colors[k])

    # keep the caption box honest first: it must hold text over any picture, so a too-see-through box gets more solid
    box = p('cap_box')
    if box[3] < 0.72:
        changes.append('Caption box: raised its opacity from %.2f to 0.82 so it holds over any picture.' % box[3])
        colors['cap_box'] = to_rgba(box, 0.82)
        box = p('cap_box')
    over_b, over_w = over(box, (0, 0, 0, 1)), over(box, (255, 255, 255, 1))
    one('Caption text on caption box', 'cap_text', [over_b, over_w], 4.5, why='tested over a black and a white picture')
    one('Spoken word on caption box', 'cap_spoken', [over_b, over_w], 3.0, why='tested over a black and a white picture')
    one('Text on accent', 'on_accent', [p('accent')], 4.5)
    one('Text on ground', 'on_ground', [p('ground')], 4.5)
    one('Text on paper', 'on_paper', [p('paper')], 4.5)
    one('Text on panel', 'on_panel', [p('panel')], 4.5)
    one('Small text on paper', 'mute', [p('paper')], 3.0)
    one('Alarm on ground', 'alarm', [p('ground')], 3.0)
    one('App text on surface', 'ink', [parse(app['surface'])], 4.5, tok=app)
    one('App quiet text on surface', 'mute', [parse(app['surface'])], 3.0, tok=app)
    one('App accent text on soft accent', 'accent_ink', [parse(app['accent_soft']), parse(app['surface'])], 4.5, tok=app)
    return colors, app, checks, changes

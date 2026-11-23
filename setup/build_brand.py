#!/usr/bin/env python3
"""build_brand.py: reads brand/brand.json and generates every brand file the pipeline, the motion kits and the app load.

Safe to run again and again. It never writes keys anywhere. If brand.json has changed since it was approved, the
approval is cleared and the owner has to look at the preview again.

  python3 setup/build_brand.py            build everything
  python3 setup/build_brand.py --check    only validate brand.json and print the contrast checks
  python3 setup/build_brand.py --force    redraw textures and fetch fonts again even if nothing changed
"""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
BRAND_DIR = ROOT / 'brand'
BRAND_FILE = BRAND_DIR / 'brand.json'
REPORT = BRAND_DIR / 'build_report.json'
CACHE = BRAND_DIR / '.build_cache.json'
LOCK = BRAND_DIR / 'brand.lock'

import colormath as cm  # noqa: E402

COLOR_KEYS = ['ground', 'on_ground', 'paper', 'on_paper', 'panel', 'on_panel', 'accent', 'on_accent', 'accent_deep',
              'alarm', 'mute', 'cap_box', 'cap_text', 'cap_spoken']
APP_KEYS = ['bg', 'bg_2', 'surface', 'line', 'line_2', 'ink', 'ink_2', 'mute', 'accent', 'accent_soft', 'accent_ink']
FORMATS = {1: 'solo', 2: 'two-host', 3: 'three-host'}
SIGNATURES = ('stack', 'pop', 'slide')
ENERGY = ('low', 'medium', 'high')
HIGHLIGHT = ('block', 'colour', 'color', 'none')
SOURCES = ('riverside', 'local', 'combined')
TIMEOUT = 25


def say(msg):
    print(msg, flush=True)


def die(lines):
    if isinstance(lines, str):
        lines = [lines]
    print('\nThe brand did not build. Fix this and run it again:\n', file=sys.stderr)
    for ln in lines:
        print('  - ' + ln, file=sys.stderr)
    sys.exit(1)


def sha(path_or_bytes):
    data = path_or_bytes if isinstance(path_or_bytes, bytes) else Path(path_or_bytes).read_bytes()
    return hashlib.sha256(data).hexdigest()


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def resolve(p):
    """A path in brand.json is from the kit root, unless it is absolute or starts with ~."""
    q = Path(p).expanduser()
    return q if q.is_absolute() else ROOT / q


# ---------- load and validate ----------

def load():
    if not BRAND_FILE.exists():
        die('There is no brand/brand.json yet. Run /shorts-setup in Claude Code, or copy brand/brand.example.json to brand/brand.json.')
    try:
        return json.loads(BRAND_FILE.read_text())
    except json.JSONDecodeError as e:
        die('brand/brand.json is not valid JSON: line %d, column %d: %s.' % (e.lineno, e.colno, e.msg))


def validate(b):
    """Every error in one go, in plain words."""
    errs = []

    def need(cond, msg):
        if not cond:
            errs.append(msg)

    show = b.get('show') or {}
    need(str(show.get('name') or '').strip(), 'show.name is empty. Give the show a name.')
    need(str(show.get('short') or show.get('name') or '').strip(), 'show.short is empty. Give the show a short name.')
    people = b.get('people') or []
    need(1 <= len(people) <= 3, 'people must list 1, 2 or 3 people. It lists %d.' % len(people))
    ids = [p.get('id') for p in people]
    need(len(set(ids)) == len(ids) and all(ids), 'Each person needs a different id, like "a", "b", "c".')
    for p in people:
        need(str(p.get('name') or '').strip(), 'Person "%s" has no name.' % p.get('id'))
    cols = b.get('colors') or {}
    need(cols.get('ground'), 'colors.ground is missing. This is the main background colour.')
    need(cols.get('accent'), 'colors.accent is missing. This is the one colour the brand is known for.')
    for k, v in cols.items():
        need(cm.is_color(v), 'colors.%s is "%s", which is not a colour. Use a hex code like "#E8A33D".' % (k, v))
    for k, v in (b.get('app_colors') or {}).items():
        need(cm.is_color(v), 'app_colors.%s is "%s", which is not a colour.' % (k, v))
    f = b.get('fonts') or {}
    for role in ('display', 'body', 'mono'):
        spec = f.get(role) or {}
        need(spec.get('family') or spec.get('path'), 'fonts.%s needs a family name, or a file path with "source": "file".' % role)
        src = spec.get('source', 'google')
        need(src in ('google', 'file'), 'fonts.%s.source is "%s". Use "google" or "file".' % (role, src))
        if src == 'file':
            paths = [spec.get('path')] if spec.get('path') else list((spec.get('paths') or {}).values())
            need(paths, 'fonts.%s uses a file, so it needs "path".' % role)
            for fp in paths:
                if not resolve(fp).exists():
                    errs.append('fonts.%s points at %s, and that file is not there.' % (role, fp))
                elif Path(fp).suffix.lower() not in ('.ttf', '.otf'):
                    errs.append('fonts.%s is %s. Only ttf or otf work, because the pipeline measures text with the font file. Ask your designer for the ttf or otf.' % (role, Path(fp).suffix))
    tex = b.get('texture') or {}
    style = tex.get('style', 'grain')
    from_style = ('grain', 'halftone', 'ink', 'paper', 'mesh', 'grid', 'user_image')
    need(style in from_style, 'texture.style is "%s". Pick one of: %s.' % (style, ', '.join(from_style)))
    if style == 'user_image':
        ui = tex.get('user_image')
        need(ui and resolve(ui).exists(), 'texture.style is user_image, so texture.user_image must point at an image file.')
    sg = float(tex.get('strength', 0.5))
    need(0 <= sg <= 1, 'texture.strength must be between 0 and 1.')
    m = b.get('motion') or {}
    need(m.get('signature', 'stack') in SIGNATURES, 'motion.signature is "%s". Pick one of: %s.' % (m.get('signature'), ', '.join(SIGNATURES)))
    need(m.get('energy', 'medium') in ENERGY, 'motion.energy is "%s". Pick one of: %s.' % (m.get('energy'), ', '.join(ENERGY)))
    need((b.get('title') or {}).get('highlight', 'block') in HIGHLIGHT, 'title.highlight must be one of: %s.' % ', '.join(HIGHLIGHT))
    rad = (b.get('caption') or {}).get('radius', 28)
    need(isinstance(rad, (int, float)) and 0 <= rad <= 60, 'caption.radius must be a number from 0 to 60.')
    rec = b.get('recording') or {}
    need(rec.get('source', 'local') in SOURCES, 'recording.source is "%s". Use riverside, local or combined.' % rec.get('source'))
    post = b.get('posting') or {}
    tz = post.get('timezone', 'UTC')
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(tz)
    except Exception:
        errs.append('posting.timezone is "%s". Use a name like "Europe/London" or "America/New_York".' % tz)
    gap = post.get('gap_hours', 4)
    need(isinstance(gap, (int, float)) and gap > 0, 'posting.gap_hours must be more than 0.')
    n = b.get('shorts_per_episode', 5)
    need(isinstance(n, int) and 1 <= n <= 20, 'shorts_per_episode must be a whole number from 1 to 20.')
    music = b.get('music') or []
    need(len(music) <= 3, 'music can hold 0 to 3 tracks. It lists %d.' % len(music))
    for t in music:
        name = t.get('file') if isinstance(t, dict) else t
        if not name or not ((BRAND_DIR / 'music' / name).exists() or resolve(name).exists()):
            errs.append('music lists "%s", and that file is not in brand/music/. Put your licensed track there.' % name)
    lut = (b.get('grade') or {}).get('lut')
    if lut and not resolve(lut).exists():
        errs.append('grade.lut points at %s, and that file is not there.' % lut)
    logo = b.get('logo') or {}
    src_logo = logo.get('file')
    if src_logo and resolve(src_logo).resolve() != (BRAND_DIR / 'logo.png').resolve() and not resolve(src_logo).exists():
        errs.append('logo.file points at %s, and that file is not there.' % src_logo)
    if errs:
        die(errs)


def fill_defaults(b, notes):
    """Fill anything the wizard left out, so the pipeline never hits a missing key."""
    show = b.setdefault('show', {})
    show.setdefault('short', show.get('name', ''))
    for k, v in (('handle', ''), ('site', ''), ('tagline', ''), ('audience', ''), ('topics', []), ('saturated_topic', ''), ('voice', []), ('banned_words', [])):
        show.setdefault(k, v)
    show['handle'] = str(show['handle']).lstrip('@')
    people = b.get('people') or []
    want = FORMATS.get(len(people), 'two-host')
    if b.get('format') != want:
        if b.get('format'):
            notes.append('format was "%s" but %d people are listed, so format is now "%s".' % (b.get('format'), len(people), want))
        b['format'] = want
    for i, p in enumerate(people):
        p.setdefault('id', 'abc'[i])
        p.setdefault('role', 'host')
        tag = re.sub(r'[^A-Za-z0-9]', '', str(p.get('name', '')))
        p.setdefault('tag', '#' + tag if tag else '')
        p.setdefault('riverside_track', p.get('name', ''))
    rec = b.setdefault('recording', {'source': 'local', 'screen_share': False})
    if rec.get('source') == 'combined':     # one finished file of everyone: the pipeline treats it as local files with ingest --composite
        rec['source'], rec['combined'] = 'local', True
    b.setdefault('app_colors', {})
    f = b.setdefault('fonts', {})
    f.setdefault('app_body', (f.get('body') or {}).get('family', ''))
    for role, w in (('display', 400), ('mono', 400)):
        if role in f:
            f[role].setdefault('source', 'google')
            f[role].setdefault('weight', w)
    if 'body' in f:
        f['body'].setdefault('source', 'google')
        f['body'].setdefault('heavy', 800)
        f['body'].setdefault('bold', 700)
    logo = b.setdefault('logo', {})
    logo.setdefault('file', 'brand/logo.png')
    logo.setdefault('wordmark_text', show.get('name', ''))
    tex = b.setdefault('texture', {})
    tex.setdefault('style', 'grain')
    tex.setdefault('seed', 1)
    tex.setdefault('strength', 0.5)
    tex.setdefault('user_image', None)
    b.setdefault('influence', {'links': [], 'notes': ''})
    m = b.setdefault('motion', {})
    m.setdefault('signature', 'stack')
    m.setdefault('energy', 'medium')
    t = b.setdefault('title', {})
    t.setdefault('uppercase', True)
    t.setdefault('highlight', 'block')
    c = b.setdefault('caption', {})
    c.setdefault('radius', 28)
    c.setdefault('uppercase', False)
    e = b.setdefault('end_card', {})
    e.setdefault('cta', 'FULL EPISODE OUT NOW')
    e.setdefault('platforms', ['apple', 'spotify', 'youtube'])
    e.setdefault('click', 'brand/sfx/end_click.wav')
    b.setdefault('music', [])
    g = b.setdefault('grade', {})
    g.setdefault('lut', None)
    g.setdefault('lut_strength', 0.6)
    post = b.setdefault('posting', {})
    for k, v in (('platforms', ['youtube', 'instagram', 'tiktok']), ('timezone', 'UTC'), ('gap_hours', 4), ('clash_hours', 1),
                 ('always_tags', [p.get('tag') for p in people if p.get('tag')]), ('cta_line', 'Watch the full episode:'),
                 ('youtube_channel_id', ''), ('instagram_username', ''), ('tiktok_username', '')):
        post.setdefault(k, v)
    a = b.setdefault('app', {})
    a.setdefault('title', '%s Shorts System' % show.get('short', ''))
    a.setdefault('approver', people[0].get('name', '') if people else '')
    a.setdefault('bucket', 'shorts-media')
    a.setdefault('url', '')
    b.setdefault('versions_per_short', 1)
    b.setdefault('shorts_per_episode', 5)


# ---------- colour ----------

def build_colors(b):
    """Derive what is missing, check contrast, move lightness where it fails. Keys Claude derived stay in _derived and are
    worked out fresh each run, so changing the accent carries through."""
    derived = set(b.get('_derived') or [])
    given = {k: v for k, v in b['colors'].items() if k not in derived}
    given['ground'] = cm.to_hex(cm.parse(given['ground']))
    given['accent'] = cm.to_hex(cm.parse(given['accent']))
    new = cm.derive(given, (b.get('caption') or {}).get('box', 'auto'))
    colors = {k: (new.get(k) or given[k]) for k in COLOR_KEYS}
    derived_now = sorted(new)
    app_given = {k: v for k, v in (b.get('app_colors') or {}).items() if 'app.' + k not in derived}
    app_new = cm.derive_app(colors)
    app = {k: app_given.get(k, app_new[k]) for k in APP_KEYS}
    derived_now += ['app.' + k for k in APP_KEYS if k not in app_given]
    colors, app, checks, changes = cm.run_checks(colors, app)
    b['colors'] = colors
    b['app_colors'] = app
    b['_derived'] = sorted(set(derived_now))
    return checks, changes


# ---------- fonts ----------

def sfnt_info(path):
    """Read the font's table list by hand, with no libraries. Returns (magic, tables)."""
    data = Path(path).read_bytes()[:4096]
    magic = data[:4]
    if magic in (b'wOFF', b'wOF2'):
        return magic, set()
    if magic == b'ttcf':
        return magic, set()
    if len(data) < 12:
        return magic, set()
    n = struct.unpack('>H', data[4:6])[0]
    tables = set()
    for i in range(min(n, 200)):
        rec = data[12 + i * 16:12 + i * 16 + 4]
        tables.add(rec.decode('latin1'))
    return magic, tables


def css_format(path):
    return 'opentype' if Path(path).read_bytes()[:4] == b'OTTO' else 'truetype'


def fetch(url, ua=None):
    req = urllib.request.Request(url, headers={'User-Agent': ua or 'Python-urllib/3'})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read()


def google_ttf(family, weight):
    """The Google Fonts CSS API gives ttf links when it does not see a modern browser. Returns (bytes, weight used) or None."""
    fam = urllib.parse.quote_plus(family)
    order = sorted(range(100, 1000, 100), key=lambda w: (abs(w - weight), w))
    for w in order:
        url = 'https://fonts.googleapis.com/css2?family=%s:wght@%d' % (fam, w)
        try:
            css = fetch(url).decode('utf8')
        except urllib.error.HTTPError:
            continue
        except OSError as e:
            die('Could not reach Google Fonts (%s). Check the internet connection, or use "source": "file".' % e)
        m = re.search(r"url\((https://[^)]+\.(?:ttf|otf))\)", css)
        if not m:
            continue
        try:
            return fetch(m.group(1)), w
        except OSError as e:
            die('Could not download %s from Google Fonts (%s). Check the internet connection and try again.' % (family, e))
    return None


def instantiate(src, dst, weight, notes):
    """Turn a variable font into one static weight, because PIL always measures a variable font at its default weight."""
    try:
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
    except ImportError:
        Path(src).unlink()
        die('The font for %s is a variable font, and fontTools is needed to cut weight %d from it. Fix: python3 setup/doctor.py --python-deps' % (Path(dst).stem, weight))
    font = TTFont(src)
    axes = {a.axisTag: a for a in font['fvar'].axes}
    pins = {}
    for tag, a in axes.items():
        pins[tag] = max(a.minValue, min(a.maxValue, weight)) if tag == 'wght' else a.defaultValue
    if 'wght' in axes and pins['wght'] != weight:
        notes.append('The font for %s only goes to weight %d, so it uses that, not %d.' % (Path(dst).stem, pins['wght'], weight))
    instancer.instantiateVariableFont(font, pins, inplace=True)
    font.save(dst)


def place_font(src_bytes_or_path, dst, weight, notes):
    """Write a font to brand/fonts under its contract name. Refuses web-only formats. Static weights only."""
    dst = Path(dst)
    if isinstance(src_bytes_or_path, bytes):
        tmp = dst.with_suffix('.tmp')
        tmp.write_bytes(src_bytes_or_path)
    else:
        tmp = dst.with_suffix('.tmp')
        shutil.copy(src_bytes_or_path, tmp)
    magic, tables = sfnt_info(tmp)
    if magic in (b'wOFF', b'wOF2'):
        tmp.unlink()
        die('%s is a web font (woff). The pipeline measures text with the font file, so it needs ttf or otf. Ask your designer for the desktop font files.' % dst.name)
    if magic == b'ttcf':
        tmp.unlink()
        die('%s is a font collection (ttc). Export the single weight as ttf or otf.' % dst.name)
    if 'fvar' in tables:
        instantiate(tmp, dst, weight, notes)
        tmp.unlink()
    else:
        tmp.replace(dst)
    from PIL import ImageFont
    try:
        ImageFont.truetype(str(dst), 40).getbbox('Hamburgefonts 0123')
    except OSError as e:
        die('%s could not be read as a font (%s).' % (dst.name, e))


def build_fonts(b, cache, force, notes):
    fdir = BRAND_DIR / 'fonts'
    fdir.mkdir(parents=True, exist_ok=True)
    f = b['fonts']
    jobs = [('display', f['display'], f['display'].get('weight', 400)),
            ('body-heavy', f['body'], f['body'].get('heavy', 800)),
            ('body-bold', f['body'], f['body'].get('bold', 700)),
            ('mono', f['mono'], f['mono'].get('weight', 400))]
    app_family = f.get('app_body') or f['body'].get('family')
    app_spec = dict(f['body']) if app_family == f['body'].get('family') else {'family': app_family, 'source': 'google'}
    jobs.append(('app-body', app_spec, 400))
    licence = ['Fonts in this folder, and where they came from.',
               'A font must be licensed for video and for your use. Google Fonts are mostly open licence, but check each one.',
               'A font from a file is your responsibility: make sure your licence covers video and web.', '']
    fc = cache.setdefault('fonts', {})
    for name, spec, weight in jobs:
        dst = fdir / (name + '.ttf')
        src = spec.get('source', 'google')
        paths = spec.get('paths') or {}
        key = json.dumps([spec.get('family'), src, weight, spec.get('path'), paths.get(name)], sort_keys=True)
        if not force and dst.exists() and fc.get(name) == key:
            licence.append('%s: %s (%s), weight %s' % (dst.name, spec.get('family') or spec.get('path'), src, weight))
            continue
        if src == 'file':
            fp = paths.get(name) or spec.get('path')
            if not fp:
                die('fonts: no file given for %s.' % name)
            place_font(resolve(fp), dst, weight, notes)
            licence.append('%s: %s (your file), weight %s' % (dst.name, Path(fp).name, weight))
        else:
            got = google_ttf(spec['family'], weight)
            if not got and name == 'app-body':
                shutil.copy(fdir / 'body-bold.ttf', dst)
                notes.append('App body font "%s" is not on Google Fonts. The app uses the show body font.' % spec['family'])
                continue
            if not got:
                die('"%s" is not on Google Fonts. Check the spelling at fonts.google.com, or give the font file with "source": "file" and "path".' % spec['family'])
            data, used = got
            if used != weight:
                notes.append('%s has no weight %d, so %s uses weight %d, the nearest.' % (spec['family'], weight, dst.name, used))
            place_font(data, dst, used, notes)
            licence.append('%s: %s (Google Fonts), weight %s. https://fonts.google.com/specimen/%s' % (dst.name, spec['family'], used, urllib.parse.quote_plus(spec['family'])))
        fc[name] = key
    (fdir / 'LICENCES.txt').write_text('\n'.join(licence) + '\n')


# ---------- logo ----------

def draw_wordmark(text, font_path, color, out, uppercase):
    from PIL import Image, ImageDraw, ImageFont
    text = text.upper() if uppercase else text
    font = ImageFont.truetype(str(font_path), 360)
    l, t, r, btm = font.getbbox(text)
    w, h = r - l, btm - t
    pad = 12
    im = Image.new('RGBA', (w + pad * 2, h + pad * 2), tuple(int(round(v)) for v in color[:3]) + (0,))
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=font, fill=tuple(int(round(v)) for v in color[:3]) + (255,))
    if im.width > 1600:
        k = 1600 / im.width
        im = im.resize((1600, max(1, int(im.height * k))), Image.LANCZOS)
    im.save(out, optimize=True)


def svg_to_png(src, dst):
    """Rasterise an svg logo with whatever this Mac has. rsvg-convert keeps transparency. sips is the fallback."""
    if shutil.which('rsvg-convert'):
        subprocess.run(['rsvg-convert', '-w', '1600', '-o', str(dst), str(src)], check=True)
        return True
    r = subprocess.run(['sips', '-s', 'format', 'png', '-Z', '1600', str(src), '--out', str(dst)], capture_output=True)
    return r.returncode == 0 and Path(dst).exists()


def logo_stats(im):
    """Visible pixels only: average colour and how colourful it is."""
    import numpy as np
    a = np.asarray(im.convert('RGBA'), dtype=np.float32)
    vis = a[a[..., 3] > 128]
    if len(vis) == 0:
        return (128, 128, 128, 1.0), 0.0, False
    mean = vis[:, :3].mean(0)
    spread = (vis[:, :3].max(1) - vis[:, :3].min(1)).mean()
    transparent = (a[..., 3] < 8).mean() > 0.02
    return tuple(float(v) for v in mean) + (1.0,), float(spread), transparent


def recolor(im, color):
    from PIL import Image
    im = im.convert('RGBA')
    solid = Image.new('RGBA', im.size, tuple(int(round(v)) for v in color[:3]) + (255,))
    solid.putalpha(im.getchannel('A'))
    return solid


def build_logo(b, cache, notes):
    from PIL import Image
    target = BRAND_DIR / 'logo.png'
    logo = b['logo']
    src = logo.get('file')
    on_ground = cm.parse(b['colors']['on_ground'])
    ground = cm.parse(b['colors']['ground'])
    is_target = (not src) or resolve(src).resolve() == target.resolve()
    # a file at brand/logo.png that this build did not draw is the owner's own logo: keep it, and keep keeping it
    theirs = is_target and target.exists() and (cache.get('logo_theirs') or sha(target) != cache.get('logo_sha'))
    if theirs:
        im = Image.open(target).convert('RGBA')
        cache['logo_theirs'] = True
        notes.append('Kept the logo you put at brand/logo.png.')
    elif is_target:
        if not logo.get('wordmark_text'):
            die('There is no logo file and no logo.wordmark_text. Give one of them.')
        draw_wordmark(logo['wordmark_text'], BRAND_DIR / 'fonts' / 'display.ttf', on_ground, target, b['title'].get('uppercase', True))
        cache['logo_sha'] = sha(target)
        return
    else:
        p = resolve(src)
        if p.suffix.lower() == '.svg':
            tmp = BRAND_DIR / '.logo_svg.png'
            if not svg_to_png(p, tmp):
                die('Could not turn %s into a png on this Mac. Export the logo as a png with a transparent background.' % p.name)
            im = Image.open(tmp).convert('RGBA')
            tmp.unlink()
        else:
            im = Image.open(p).convert('RGBA')
        if im.getchannel('A').getbbox():
            im = im.crop(im.getchannel('A').getbbox())
    avg, spread, transparent = logo_stats(im)
    if transparent and cm.contrast(avg, ground) < 2.5:
        if spread < 28:
            im = recolor(im, on_ground)
            notes.append('Your logo was too close to the ground colour to read, and it is one colour, so it was recoloured to %s.' % b['colors']['on_ground'])
        else:
            notes.append('Warning: your logo is hard to read on the ground colour (%.1f:1). Give a version made for this ground.' % cm.contrast(avg, ground))
    elif not transparent:
        notes.append('Your logo has no transparent background, so it will show as a box. A transparent png looks better.')
    if max(im.size) > 1600:
        k = 1600 / max(im.size)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    im.save(target, optimize=True)
    cache['logo_sha'] = sha(target)


def app_logo(b, out):
    """The app shows the logo on its dark ink band, so a dark logo needs a light version there."""
    from PIL import Image
    im = Image.open(BRAND_DIR / 'logo.png').convert('RGBA')
    avg, spread, transparent = logo_stats(im)
    ink = cm.parse(b['app_colors']['ink'])
    if transparent and spread < 28 and cm.contrast(avg, ink) < 2.5:
        im = recolor(im, cm.parse(b['app_colors']['surface']))
    im.save(out, optimize=True)


# ---------- generated text files ----------

def css_tokens(b):
    c, a = b['colors'], b['app_colors']
    t = b['title']
    cap = b['caption']
    dark = (0.2126 * cm.parse(c['ground'])[0] + 0.7152 * cm.parse(c['ground'])[1] + 0.0722 * cm.parse(c['ground'])[2]) / 255 < 0.5
    render = [
        ('--ground', c['ground']), ('--on-ground', c['on_ground']), ('--paper', c['paper']), ('--on-paper', c['on_paper']),
        ('--panel', c['panel']), ('--on-panel', c['on_panel']), ('--accent', c['accent']), ('--on-accent', c['on_accent']),
        ('--accent-deep', c['accent_deep']), ('--alarm', c['alarm']), ('--mute', c['mute']),
        ('--cap-box', c['cap_box']), ('--cap-text', c['cap_text']), ('--cap-spoken', c['cap_spoken']),
        ('--font-display', "'BrandDisplay'"), ('--font-body', "'BrandBody'"), ('--font-mono', "'BrandMono'"),
        ('--cap-radius', '%spx' % cap.get('radius', 28)),
        ('--title-transform', 'uppercase' if t.get('uppercase') else 'none'),
        ('--title-highlight', t.get('highlight', 'block')),
        ('--cap-transform', 'uppercase' if cap.get('uppercase') else 'none'),
        ('--grain-blend', 'screen' if dark else 'multiply'),
        ('--grain-filter', 'none' if dark else 'invert(1)'),
    ]
    app = [('--app-' + k.replace('_', '-'), a[k]) for k in APP_KEYS]
    if a['accent'].upper() != c['accent'].upper():
        ac = cm.parse(a['accent'])
        app.append(('--app-on-accent', cm.to_hex(cm.better_on(ac, cm.oklch(ac)[2], 0.02))))
    return render, app


def font_faces():
    out = []
    fdir = BRAND_DIR / 'fonts'
    for fam, file, weight in (('BrandDisplay', 'display.ttf', 400), ('BrandBody', 'body-heavy.ttf', 800), ('BrandBody', 'body-bold.ttf', 700), ('BrandMono', 'mono.ttf', 400)):
        out.append("@font-face { font-family: '%s'; src: url('fonts/%s') format('%s'); font-weight: %d; font-display: swap; }" % (fam, file, css_format(fdir / file), weight))
    return out


def write_css(b):
    render, app = css_tokens(b)
    lines = ['/* Generated by setup/build_brand.py from brand/brand.json. Do not edit by hand: change brand.json and run the build again. */']
    lines += font_faces()
    lines.append(':root {')
    lines += ['  %s: %s;' % kv for kv in render]
    lines.append('  /* approval app */')
    lines += ['  %s: %s;' % kv for kv in app]
    lines.append('}')
    base = '\n'.join(lines) + '\n'
    (BRAND_DIR / 'brand.css').write_text(base)
    fmt = css_format(BRAND_DIR / 'fonts' / 'app-body.ttf')
    extra = ("/* Body text of the app: a regular weight, because BrandBody only holds the heavy weights. */\n"
             "@font-face { font-family: 'BrandAppBody'; src: url('fonts/app-body.ttf') format('%s'); font-weight: 400 600; font-display: swap; }\n"
             ":root { --app-font-body: 'BrandAppBody'; }\n" % fmt)
    return base, base + extra


def music_labels(b):
    out = []
    for m in b.get('music') or []:
        if isinstance(m, dict):
            out.append({'name': m.get('name') or Path(m.get('file', '')).stem})
        else:
            out.append({'name': Path(m).stem})
    return out


def safe_page(b):
    """What the browser may see. No keys ever live in brand.json, and this list is a second lock."""
    return {
        'show': {k: b['show'].get(k, '') for k in ('name', 'short', 'handle', 'site', 'tagline')},
        'people': [{k: p.get(k, '') for k in ('id', 'name', 'tag', 'role')} for p in b['people']],
        'format': b['format'],
        'app': {k: b['app'].get(k, '') for k in ('title', 'approver', 'bucket', 'url')},
        'posting': {k: b['posting'].get(k) for k in ('platforms', 'timezone', 'gap_hours', 'clash_hours', 'always_tags', 'cta_line', 'youtube_channel_id', 'instagram_username', 'tiktok_username', 'youtube_category_id') if k in b['posting']},
        'end_card': {k: b['end_card'].get(k) for k in ('cta', 'platforms')},
        'music': music_labels(b),
        'shorts_per_episode': b['shorts_per_episode'],
        'versions_per_short': b['versions_per_short'],
    }


def safe_server(b):
    return {
        'show': {k: b['show'].get(k, '') for k in ('name', 'short', 'handle', 'site')},
        'people': [{k: p.get(k, '') for k in ('id', 'name', 'tag')} for p in b['people']],
        'app': {k: b['app'].get(k, '') for k in ('title', 'approver', 'bucket', 'url')},
        'posting': {k: b['posting'].get(k) for k in ('platforms', 'timezone', 'gap_hours', 'clash_hours', 'always_tags', 'cta_line', 'youtube_channel_id', 'instagram_username', 'tiktok_username', 'youtube_category_id') if k in b['posting']},
        'shorts_per_episode': b['shorts_per_episode'],
    }


# ---------- copies into each kit ----------

def copy_into(src, dst):
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def distribute(b, css_base, css_app):
    tex = BRAND_DIR / 'textures'
    fonts = BRAND_DIR / 'fonts'
    core = ['display.ttf', 'body-heavy.ttf', 'body-bold.ttf', 'mono.ttf']

    kit = ROOT / 'motion' / 'kit'
    (kit).mkdir(parents=True, exist_ok=True)
    (kit / 'brand.css').write_text(css_base)
    for n in core:
        copy_into(fonts / n, kit / 'fonts' / n)
    copy_into(tex / 'ground.jpg', kit / 'img' / 'ground.jpg')
    for k in range(4):
        copy_into(tex / 'grain' / ('grain_%d.png' % k), kit / 'img' / ('grain_%d.png' % k))
    copy_into(BRAND_DIR / 'logo.png', kit / 'img' / 'logo.png')

    lib = ROOT / 'motion-library' / 'shared'
    lib.mkdir(parents=True, exist_ok=True)
    (lib / 'brand.css').write_text(css_base)
    for n in core:
        copy_into(fonts / n, lib / 'fonts' / n)
    copy_into(BRAND_DIR / 'logo.png', lib / 'logo.png')
    for k in range(4):
        copy_into(tex / 'grain' / ('grain_%d.png' % k), lib / ('grain_%d.png' % k))

    pub = ROOT / 'app' / 'public'
    pub.mkdir(parents=True, exist_ok=True)
    (pub / 'brand.css').write_text(css_app)
    (pub / 'brand.js').write_text('// Generated by setup/build_brand.py. Holds no keys.\nwindow.BRAND = %s;\n' % json.dumps(safe_page(b), indent=1, ensure_ascii=False))
    for n in core + ['app-body.ttf']:
        copy_into(fonts / n, pub / 'fonts' / n)
    copy_into(tex / 'app_band.jpg', pub / 'img' / 'band.jpg')
    copy_into(tex / 'g2.jpg', pub / 'img' / 'edge.jpg')
    (pub / 'img').mkdir(parents=True, exist_ok=True)
    app_logo(b, pub / 'img' / 'logo.png')

    api = ROOT / 'app' / 'api'
    api.mkdir(parents=True, exist_ok=True)
    (api / '_brand.js').write_text('// Generated by setup/build_brand.py. Holds no keys.\nexport default %s;\n' % json.dumps(safe_server(b), indent=1, ensure_ascii=False))


def plate_checks(b):
    """The middle of each plate must keep text readable. Worst one percent of pixels, not the average."""
    import numpy as np
    from PIL import Image
    on_g = cm.parse(b['colors']['on_ground'])
    out = []
    for name, (x0, x1, y0, y1) in (('band', (.30, .70, .30, .70)), ('tall_a', (.25, .75, .40, .60)), ('tall_b', (.25, .75, .40, .60)),
                                   ('card', (.22, .78, .30, .70)), ('card_wide', (.30, .70, .30, .70))):
        a = np.asarray(Image.open(BRAND_DIR / 'textures' / (name + '.png')).convert('RGB'), np.float32)
        h, w = a.shape[:2]
        mid = a[int(h * y0):int(h * y1), int(w * x0):int(w * x1)].reshape(-1, 3)
        lum = mid @ np.array([.2126, .7152, .0722], np.float32)
        worst = mid[np.argsort(lum)[int(len(lum) * .99)]]
        worst_other = mid[np.argsort(lum)[int(len(lum) * .01)]]
        r = min(cm.contrast(on_g, tuple(worst) + (1.0,)), cm.contrast(on_g, tuple(worst_other) + (1.0,)))
        out.append({'name': 'Text on the middle of %s' % name, 'fg': b['colors']['on_ground'], 'bg': cm.to_hex(tuple(mid.mean(0))), 'ratio': round(float(r), 2), 'min': 4.4, 'ok': bool(r >= 4.4), 'fixed': False, 'why': 'worst 1 percent of pixels, with room for the dither'})
    return out


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description='Build all brand files from brand/brand.json.')
    ap.add_argument('--check', action='store_true', help='validate and show the contrast checks only, write nothing')
    ap.add_argument('--force', action='store_true', help='redraw textures and fetch fonts even if nothing changed')
    args = ap.parse_args()

    b = load()
    notes = []
    validate(b)
    fill_defaults(b, notes)
    checks, changes = build_colors(b)
    if args.check:
        for c in checks:
            say('%s  %s  %.2f:1 (needs %.1f)' % ('PASS' if c['ok'] else 'FAIL', c['name'], c['ratio'], c['min']))
        for c in changes:
            say('Would change: ' + c)
        sys.exit(0 if all(c['ok'] for c in checks) else 1)

    try:
        import numpy  # noqa: F401
        import PIL  # noqa: F401
    except ImportError:
        die('numpy and Pillow are needed to draw the textures. Fix: python3 setup/doctor.py --python-deps')
    import sounds
    import textures

    BRAND_DIR.mkdir(exist_ok=True)
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    say('Fonts...')
    build_fonts(b, cache, args.force, notes)
    say('Logo...')
    build_logo(b, cache, notes)

    tx = b['texture']
    user_image = str(resolve(tx['user_image'])) if tx.get('user_image') else None
    tex_key = json.dumps([b['show']['name'], tx.get('style'), tx.get('seed'), tx.get('strength'), user_image and sha(user_image),
                          b['colors']['ground'], b['colors']['on_ground'], b['colors']['accent'], b['colors']['accent_deep'], b['colors']['paper'], b['app_colors']['ink'], b['app_colors']['surface']])
    tdir = BRAND_DIR / 'textures'
    want_files = [tdir / (n + ('.jpg' if n in ('ground', 'app_band') or n[0] == 'g' else '.png')) for n in textures.PLATES]
    if args.force or cache.get('textures') != tex_key or not all(p.exists() for p in want_files):
        say('Drawing textures (%s)...' % tx.get('style'))
        textures.build_pack(b['colors'], b['show']['name'], tx.get('seed', 1), tx.get('style', 'grain'), tx.get('strength', 0.5), user_image, BRAND_DIR,
                            app_ink=b['app_colors']['ink'], app_surface=b['app_colors']['surface'])
        cache['textures'] = tex_key
    else:
        say('Textures are up to date.')

    say('Sounds...')
    snd_key = json.dumps([b['show']['name'], tx.get('seed', 1)])
    if args.force or cache.get('sounds') != snd_key or not (BRAND_DIR / 'sfx' / 'end_click.wav').exists():
        sounds.build_kit(BRAND_DIR / 'sfx', b['show']['name'], tx.get('seed', 1))
        cache['sounds'] = snd_key

    say('Writing brand.css, brand.js and the copies into each kit...')
    # brand.json first, so the files below and the lock check all see the same version
    BRAND_FILE.write_text(json.dumps(b, indent=2, ensure_ascii=False) + '\n')
    css_base, css_app = write_css(b)
    distribute(b, css_base, css_app)

    rules = ROOT / 'rules' / 'MY-RULES.md'
    if not rules.exists():
        rules.parent.mkdir(parents=True, exist_ok=True)
        rules.write_text('# My rules\n\nRules from my own notes. They start at R200. Newest at the bottom.\n')

    pchecks = plate_checks(b)
    brand_sha = sha(BRAND_FILE)
    if LOCK.exists() and LOCK.read_text().strip().split()[0] != brand_sha:
        LOCK.unlink()
        notes.append('The brand changed, so the old approval was cleared. Look at the preview and approve it again.')
    REPORT.write_text(json.dumps({'brand_sha': brand_sha, 'checks': checks + pchecks, 'changes': changes, 'notes': notes}, indent=1) + '\n')
    CACHE.write_text(json.dumps(cache, indent=1) + '\n')

    fails = [c for c in checks + pchecks if not c['ok']]
    say('')
    say('Built the brand for %s.' % b['show']['name'])
    for c in changes:
        say('Changed: ' + c)
    for n in notes:
        say('Note: ' + n)
    say('Contrast: %d passed, %d failed.' % (len(checks + pchecks) - len(fails), len(fails)))
    for c in fails:
        say('FAIL: %s is %.2f:1 and needs %.1f:1.' % (c['name'], c['ratio'], c['min']))
    say('Next: python3 setup/preview.py')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()

"""brand.py: the one place the pipeline reads the show's brand, people and paths from. Everything comes from brand/brand.json."""
import json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_file = ROOT / 'brand' / 'brand.json'
if not _file.exists():
    raise SystemExit('No brand yet. Open this folder in Claude Code and type /shorts-setup.')
BRAND = json.loads(_file.read_text())
C = BRAND['colors']
SHOW = BRAND['show']
PEOPLE = BRAND['people']
IDS = [p['id'] for p in PEOPLE]
FONTS = ROOT / 'brand' / 'fonts'
FONT = {'display': FONTS / 'display.ttf', 'heavy': FONTS / 'body-heavy.ttf', 'bold': FONTS / 'body-bold.ttf', 'mono': FONTS / 'mono.ttf'}
TEX = ROOT / 'brand' / 'textures'
LOGO = ROOT / 'brand' / 'logo.png'
SFX = ROOT / 'brand' / 'sfx'
MUSIC = ROOT / 'brand' / 'music'
CSS = ROOT / 'brand' / 'brand.css'
FACE_TRACK = ROOT / 'bin' / 'face_track'
FRAME_SCAN = ROOT / 'bin' / 'frame_scan'
EPISODES = ROOT / 'episodes'
WHISPER = ROOT / 'bin' / 'models'
LOCK = ROOT / 'brand' / 'brand.lock'


def env():
    """Keys live in <kit>/.env. Never print them."""
    d = {}
    f = ROOT / '.env'
    if f.exists():
        for line in f.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1)
                d[k.strip()] = v.strip().strip('"')
    d.update({k: v for k, v in os.environ.items() if k in d})
    return d


def person(pid):
    return next(p for p in PEOPLE if p['id'] == pid)


def require_locked():
    """Nothing renders until the owner has seen the preview and approved the brand."""
    if not LOCK.exists():
        raise SystemExit('Brand not approved yet. Run /shorts-setup and approve the preview.')


# ---- small helpers the renderer shares ----
def luminance(col):
    """0..1 for a '#RRGGBB' colour. Used only to pick a blend that works on this ground."""
    c = col.lstrip('#')
    r, g, b = (int(c[k:k + 2], 16) / 255 for k in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


GROUND_DARK = luminance(C['ground']) < 0.5
# Film grain: light noise lifts a dark ground (screen). On a light ground screen does nothing, so the same plates are inverted and multiplied.
GRAIN_CSS = (':root { --grain-blend: screen; --grain-filter: none; }' if GROUND_DARK
             else ':root { --grain-blend: multiply; --grain-filter: invert(1); }')


def tracks():
    """The music beds, 0 to 3. brand.json "music" holds file names (in brand/music, or a path from the kit root) or
    {"file": ..., "bed": -21}. Returns [{'key': 't1', 'path': Path, 'bed': -21.0}, ...] for the files that exist."""
    out = []
    for m in BRAND.get('music') or []:
        m = m if isinstance(m, dict) else {'file': m}
        p = MUSIC / m['file'] if (MUSIC / m['file']).exists() else ROOT / m['file']
        if p.exists() and len(out) < 3:
            out.append({'key': f't{len(out) + 1}', 'path': p, 'bed': float(m.get('bed', -21))})
    return out


def first_names():
    return [p['name'].split()[0] for p in PEOPLE]


def timezone():
    """The show's clock for dates in messages and for the posting plan."""
    from zoneinfo import ZoneInfo
    return ZoneInfo(BRAND.get('posting', {}).get('timezone') or 'UTC')

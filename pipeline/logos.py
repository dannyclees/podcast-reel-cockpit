"""logos.py: a Short's logos live in its own clip folder. A mark that is not there yet is fetched once from simple-icons."""
import os, urllib.request

SOURCES = ('https://cdn.simpleicons.org/{}', 'https://cdn.jsdelivr.net/npm/simple-icons/icons/{}.svg')


def fetch(name, clip):
    """<clip>/logos/<name>.svg, fetched if missing. Returns the path, or None if no source has that mark (never fatal)."""
    dst = os.path.join(clip, 'logos', name + '.svg')
    if os.path.exists(dst): return dst
    for src in SOURCES:
        try:
            req = urllib.request.Request(src.format(name), headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as r: svg = r.read()
        except Exception: continue
        if b'<svg' in svg[:400]:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(svg)
            return dst
    print(f'WARNING no logo "{name}" on simple-icons: put your own at {dst}')
    return None

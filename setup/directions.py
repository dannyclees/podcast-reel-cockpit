#!/usr/bin/env python3
"""directions.py brand/directions.json: one page with 3 brand directions side by side, for an owner who has nothing yet.

Each direction uses the real texture code and real fonts, so what they pick is what they get. It writes
brand/directions/index.html and opens it. It changes nothing else.
"""
import argparse
import base64
import html
import io
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent

import build_brand as bb  # noqa: E402
import colormath as cm  # noqa: E402
import textures  # noqa: E402
from PIL import Image  # noqa: E402

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font: 400 16px/1.5 system-ui, -apple-system, sans-serif; background: #F4F4F1; color: #1A1A1A; }
main { max-width: 1240px; margin: 0 auto; padding: 44px 20px 70px; }
h1 { font-size: 30px; line-height: 1.1; } .sub { margin: 8px 0 30px; color: #555; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 20px; }
.d { background: #fff; border-radius: 20px; overflow: hidden; box-shadow: 0 1px 2px rgba(0,0,0,.06), 0 18px 34px -26px rgba(0,0,0,.4); }
.hero { aspect-ratio: 16 / 11; display: flex; align-items: center; justify-content: center; padding: 24px; background-size: cover; background-position: center; text-align: center; }
.t { font-size: 40px; line-height: 1.08; } .t mark { padding: 0 8px; border-radius: 5px; }
.cap { display: inline-block; margin-top: 14px; font-size: 18px; font-weight: 800; padding: 6px 14px; border-radius: 12px; }
.p { padding: 16px 18px 20px; } .p h2 { font-size: 19px; } .p .why { color: #555; font-size: 14.5px; margin: 4px 0 12px; }
.sw { display: flex; gap: 6px; margin-bottom: 12px; } .sw i { width: 34px; height: 34px; border-radius: 9px; display: block; box-shadow: inset 0 0 0 1px rgba(0,0,0,.08); }
.m { font-size: 13.5px; color: #333; }
"""


def uri(data, mime):
    return 'data:%s;base64,%s' % (mime, base64.b64encode(data).decode())


def font_face(family, name, weight, notes):
    got = bb.google_ttf(family, weight)
    if not got:
        notes.append('"%s" is not on Google Fonts.' % family)
        return ''
    return "@font-face { font-family: '%s'; src: url('%s'); font-weight: %d; }\n" % (name, uri(got[0], 'font/ttf'), weight)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--no-open', action='store_true')
    a = ap.parse_args()
    dirs = json.loads(Path(a.file).read_text())
    notes, faces, cards = [], [], []
    for i, d in enumerate(dirs):
        given = {'ground': cm.to_hex(cm.parse(d['colors']['ground'])), 'accent': cm.to_hex(cm.parse(d['colors']['accent']))}
        colors = dict(given, **cm.derive(given))
        colors, _, _, _ = cm.run_checks(colors, cm.derive_app(colors))
        tx = d.get('texture', {})
        pal = textures.palette(colors)
        arr = textures.render(tx.get('style', 'grain'), 1100, 756, 'band', pal, d.get('name', str(i)), tx.get('seed', 1), tx.get('strength', 0.5))
        buf = io.BytesIO()
        Image.fromarray(arr).save(buf, 'JPEG', quality=86, subsampling=0)
        plate = uri(buf.getvalue(), 'image/jpeg')
        disp, body = 'D%d' % i, 'B%d' % i
        faces.append(font_face(d['fonts']['display'], disp, 400, notes))
        faces.append(font_face(d['fonts']['body'], body, 800, notes))
        upper = 'uppercase' if d.get('title', {}).get('uppercase', True) else 'none'
        swatches = ''.join('<i style="background:%s"></i>' % colors[k] for k in ('ground', 'accent', 'accent_deep', 'paper', 'panel'))
        m = d.get('motion', {})
        cards.append(
            '<section class="d"><div class="hero" style="background-image:url(%s);color:%s"><div>'
            '<div class="t" style="font-family:%s;text-transform:%s">The part nobody <mark style="background:%s;color:%s">talks about</mark></div>'
            '<span class="cap" style="font-family:%s;background:%s;color:%s">and <b style="color:%s">nobody</b> tells you this</span>'
            '</div></div><div class="p"><h2>%s</h2><p class="why">%s</p><div class="sw">%s</div>'
            '<p class="m">%s + %s. Texture: %s. Motion: %s, %s energy.</p></div></section>' % (
                plate, colors['on_ground'], disp, upper, colors['accent'], colors['on_accent'],
                body, colors['cap_box'], colors['cap_text'], colors['cap_spoken'],
                html.escape(d.get('name', 'Direction %d' % (i + 1))), html.escape(d.get('why', '')), swatches,
                html.escape(d['fonts']['display']), html.escape(d['fonts']['body']), html.escape(tx.get('style', 'grain')),
                html.escape(m.get('signature', 'stack')), html.escape(m.get('energy', 'medium'))))
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Three directions</title><style>%s%s</style></head>'
            '<body><main><h1>Three directions for your show</h1><p class="sub">Pick one, or say which parts of which. The real preview comes next.</p><div class="grid">%s</div></main></body></html>'
            ) % (CSS, ''.join(faces), ''.join(cards))
    out = ROOT / 'brand' / 'directions' / 'index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    for n in notes:
        print('Note: ' + n)
    print('Directions: %s' % out)
    if not a.no_open:
        subprocess.run(['open', str(out)], check=False)


if __name__ == '__main__':
    main()

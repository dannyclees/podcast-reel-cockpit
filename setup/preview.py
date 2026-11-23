#!/usr/bin/env python3
"""preview.py: writes brand/preview/index.html, one page that shows the brand on real Short layouts.

It uses the real brand.css, the real plates and the real motion kit, all embedded, so the page opens from Finder with no
server and can be sent to a co-host. It has no sound of any kind. Nothing plays out loud.

  python3 setup/preview.py          write the page and open it
  python3 setup/preview.py --no-open
"""
import argparse
import base64
import html
import io
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parent
BRAND_DIR = ROOT / 'brand'

import colormath as cm  # noqa: E402

KIT = ROOT / 'motion' / 'kit'
SWATCHES = [('ground', 'Ground'), ('on_ground', 'Text on ground'), ('accent', 'Accent'), ('on_accent', 'Text on accent'), ('accent_deep', 'Deep accent'),
            ('paper', 'Paper'), ('on_paper', 'Text on paper'), ('panel', 'Panel'), ('on_panel', 'Text on panel'), ('alarm', 'Alarm'), ('mute', 'Quiet text'),
            ('cap_box', 'Caption box'), ('cap_text', 'Caption text'), ('cap_spoken', 'Spoken word')]


def b64(data, mime):
    return 'data:%s;base64,%s' % (mime, base64.b64encode(data).decode())


def plate(path, width=None, q=86):
    """A real plate as an embedded JPEG. Resized only to keep the page light."""
    from PIL import Image
    im = Image.open(path).convert('RGB')
    if width and im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=q, subsampling=0)
    return b64(buf.getvalue(), 'image/jpeg')


def png_file(path):
    return b64(Path(path).read_bytes(), 'image/png')


def embed_fonts(css):
    """Swap each font link for the font itself."""
    def sub(m):
        name = m.group(1)
        data = (BRAND_DIR / 'fonts' / name).read_bytes()
        return "url('%s')" % b64(data, 'font/otf' if data[:4] == b'OTTO' else 'font/ttf')
    return re.sub(r"url\('fonts/([^']+)'\)", sub, css)


def person_svg(kind):
    """A neutral stand-in for a video frame. It has no brand colour in it, so the brand is judged on its own."""
    back = {'a': ('#55504A', '#2E2B28', '#8C7F70'), 'b': ('#46505A', '#272C31', '#6F7F8C')}[kind]
    shirt = {'a': '#23262B', 'b': '#3A3430'}[kind]
    skin = {'a': '#B08A70', 'b': '#8F6C55'}[kind]
    hair = {'a': '#2A211C', 'b': '#17171A'}[kind]
    x = {'a': 520, 'b': 570}[kind]
    return ('<svg class="pic" viewBox="0 0 1080 960" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
            '<defs><linearGradient id="bk%(k)s" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="%(b0)s"/><stop offset="1" stop-color="%(b1)s"/></linearGradient>'
            '<radialGradient id="lt%(k)s" cx=".78" cy=".22" r=".5"><stop offset="0" stop-color="%(b2)s" stop-opacity=".7"/><stop offset="1" stop-color="%(b2)s" stop-opacity="0"/></radialGradient>'
            '<filter id="sf%(k)s"><feGaussianBlur stdDeviation="2"/></filter></defs>'
            '<rect width="1080" height="960" fill="url(#bk%(k)s)"/><rect width="1080" height="960" fill="url(#lt%(k)s)"/>'
            '<g filter="url(#sf%(k)s)"><path d="M%(l)d 960c10-190 110-290 %(w)d-290s%(w2)d 100 %(w3)d 290z" fill="%(sh)s"/>'
            '<rect x="%(nx)d" y="560" width="120" height="150" rx="50" fill="%(sk)s"/>'
            '<ellipse cx="%(x)d" cy="420" rx="168" ry="210" fill="%(sk)s"/>'
            '<path d="M%(hx)d 400c-10-170 90-240 190-240s200 70 180 240c-30-90-90-120-190-120s-150 40-180 120z" fill="%(hr)s"/></g></svg>'
            ) % dict(k=kind, b0=back[0], b1=back[1], b2=back[2], sh=shirt, sk=skin, hr=hair, x=x, l=x - 340, w=340, w2=340, w3=340, nx=x - 60, hx=x - 185)


def marks(platforms):
    out = []
    for name in platforms:
        p = BRAND_DIR / 'marks' / (name + '.svg')
        if p.exists():
            svg = re.sub(r'<title>.*?</title>', '', p.read_text(), flags=re.S).replace('<svg ', '<svg fill="currentColor" ', 1)
            out.append('<i class="ic">%s</i>' % svg)
    return ''.join(out)


def motion_doc(b, css_inline, ground_uri, grains):
    """The real motion kit, playing the show's signature move. Returns None if the kit is not there, and the page falls back to a small CSS sample."""
    js, kcss, gsap = KIT / 'kit.js', KIT / 'kit.css', KIT / 'gsap.min.js'
    if not (js.exists() and kcss.exists() and gsap.exists()):
        return None
    kit_js = js.read_text()
    if 'K.signature' not in kit_js:
        return None
    kit_css = kcss.read_text().replace("url('img/ground.jpg')", "url('%s')" % ground_uri)
    comp = """
window.BRAND_MOTION = %s;
""" % json.dumps({'signature': b['motion'].get('signature', 'stack'), 'energy': b['motion'].get('energy', 'medium')})
    run = """
K.init(4.8);
var s = K.scene(0, null);
var a = K.block(s, {x: 110, y: 90, w: 400, h: 400, r: 36, cls: 'paper', html: '<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px"><div class="num" style="font-size:190px;color:var(--on-paper)">1</div><div style="font:800 34px var(--font-body);color:var(--mute);letter-spacing:.08em">EPISODE</div></div>'});
var b = K.block(s, {x: 570, y: 90, w: 400, h: 400, r: 36, cls: 'dark', html: '<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px"><div class="num" style="font-size:190px;color:var(--on-panel)">5</div><div style="font:800 34px var(--font-body);color:var(--on-panel);letter-spacing:.08em;opacity:.7">SHORTS</div></div>'});
K.drop(a, .55, {side: -1}); K.drop(b, 1.1, {side: 1});
var w = K.words(s, {y: 590, size: 118, lines: [['EVERY', 'WEEK']]});
K.say(w.map.EVERY, 1.75); K.say(w.map.WEEK, 2.1); K.mark(w.map.WEEK, 2.35);
K.finish();
var still = false; try { still = /still/.test(parent.location.hash); } catch (e) {}
if (still) { K.tl.seek(3.6); } else { K.tl.repeat(-1).repeatDelay(.4).play(0); }
"""
    comp += 'window.GR = %s;\n' % json.dumps(grains)
    kit_js = kit_js.replace('url(img/grain_${k}.png)', 'url(${window.GR[k]})')
    def safe(t):
        return t.replace('</script', '<\\/script')
    return ('<!doctype html><html><head><meta charset="utf-8"><style>%s</style><style>%s</style><script>%s</script><script>%s</script></head>'
            '<body><div id="root"></div><script>%s</script><script>%s</script></body></html>'
            ) % (css_inline, kit_css, safe(gsap.read_text()), safe(comp), safe(kit_js), safe(run))


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__ brand preview</title>
<style>__CSS__</style>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--app-bg); color: var(--app-ink); font: 400 16px/1.5 'BrandAppBody', system-ui, sans-serif; -webkit-font-smoothing: antialiased; }
main { max-width: 1216px; margin: 0 auto; padding: 44px 20px 90px; }
header.top { display: flex; align-items: center; gap: 22px; flex-wrap: wrap; margin-bottom: 14px; }
.lockup { background: var(--ground); border-radius: 18px; padding: 16px 22px; display: flex; align-items: center; }
.lockup img { height: 44px; max-width: 320px; object-fit: contain; display: block; }
h1 { font: 400 40px/1.05 var(--font-display); letter-spacing: -.01em; text-transform: var(--title-transform); }
h2 { font: 400 24px/1.1 var(--font-display); letter-spacing: -.005em; margin: 56px 0 16px; text-transform: var(--title-transform); }
.sub { color: var(--app-ink-2); max-width: 720px; }
.facts { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
.facts span { font: 400 13px 'BrandMono', monospace; background: var(--app-surface); box-shadow: inset 0 0 0 1px var(--app-line); padding: 5px 12px; border-radius: 999px; }
.note { background: var(--app-accent-soft); color: var(--app-accent-ink); padding: 14px 18px; border-radius: 14px; margin-top: 22px; }

.frames { display: grid; grid-template-columns: repeat(auto-fill, 216px); gap: 24px; justify-content: space-between; margin-top: 34px; }
figure { width: 216px; }
figcaption { font-size: 13px; color: var(--app-mute); margin-top: 10px; }
.fr { width: 216px; height: 384px; border-radius: 22px; overflow: hidden; position: relative; background: var(--ground); box-shadow: 0 1px 2px rgba(0,0,0,.08), 0 22px 40px -28px rgba(0,0,0,.5); }
.st { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; transform: scale(.2); transform-origin: 0 0; overflow: hidden; background: var(--ground); }
.half { position: absolute; left: 0; width: 1080px; height: 960px; overflow: hidden; }
.half.t { top: 0; } .half.b { top: 960px; }
.pic { position: absolute; inset: 0; width: 100%; height: 100%; display: block; }
mark { background: var(--accent); color: var(--on-accent); padding: 0 14px; border-radius: 8px; }
.b-title mark { background: none; color: var(--accent); padding: 0; }

#q { position: absolute; left: 40px; top: 960px; transform: translateY(-50%); width: 1000px; background: url('__CARD__') center/cover; color: var(--on-ground); border-radius: 30px; padding: 44px 40px 48px; box-shadow: 0 30px 60px -20px rgba(0,0,0,.55); text-align: center; font: 400 70px/1.14 var(--font-display); text-transform: var(--title-transform); }
.cap { position: absolute; left: 0; right: 0; top: 960px; transform: translateY(-50%); text-align: center; }
.cap span { display: inline-block; background: var(--cap-box); color: var(--cap-text); font: 800 56px/1.18 var(--font-body); padding: 16px 34px; border-radius: var(--cap-radius); max-width: 960px; white-space: nowrap; text-transform: var(--cap-transform); }
.cap b { color: var(--cap-spoken); font-weight: 800; }
.news { position: absolute; left: 40px; top: 240px; width: 1000px; height: 424px; background: url('__CARDW__') center/cover; border-radius: 30px; padding: 40px 150px; color: var(--on-ground); display: flex; flex-direction: column; justify-content: center; gap: 26px; box-shadow: 0 30px 60px -20px rgba(0,0,0,.5); }
.news .src { font: 400 28px 'BrandMono', monospace; letter-spacing: .1em; text-transform: uppercase; opacity: .78; }
.news .t { font: 800 54px/1.14 var(--font-body); }
.gr-bg { position: absolute; inset: 0; background: url('__GROUND__') center/cover; opacity: .26; }
.mg { position: absolute; left: 0; top: 0; width: 1080px; height: 960px; border: 0; display: block; }
#end { position: absolute; inset: 0; background: var(--ground) url('__TALL__') center/cover; }
#end .lg { position: absolute; left: 190px; right: 190px; top: 560px; height: 300px; display: flex; align-items: center; justify-content: center; }
#end .lg img { max-width: 100%; max-height: 100%; object-fit: contain; display: block; }
#end .row { position: absolute; left: 0; right: 0; top: 960px; display: flex; justify-content: center; gap: 80px; color: var(--on-ground); }
#end .ic { width: 64px; height: 64px; display: block; } #end .ic svg { width: 100%; height: 100%; display: block; }
#end .pl { position: absolute; left: 0; right: 0; top: 1120px; display: flex; justify-content: center; }
#end .pi { position: relative; }
#end .pi i { position: absolute; inset: 0; border-radius: 26px; background: var(--accent); transform: translate(14px, 14px); }
#end .pi div { position: relative; background: var(--paper); color: var(--on-paper); border-radius: 26px; padding: 30px 54px; font: 800 46px/1 var(--font-body); letter-spacing: .08em; white-space: nowrap; }
.css-mg { position: absolute; left: 340px; top: 280px; width: 400px; height: 400px; }
.css-mg i, .css-mg b { position: absolute; inset: 0; border-radius: 36px; display: block; }
.css-mg i { background: var(--accent); animation: lay 3.4s infinite; } .css-mg b { background: var(--paper); color: var(--on-paper); display: flex; align-items: center; justify-content: center; font: 400 190px var(--font-display); animation: sig 3.4s infinite; }
@keyframes lay { 0%, 30% { transform: none; } 42%, 100% { transform: translate(16px, 16px); } }
@keyframes sig { 0% { transform: translateY(-900px); } 16% { transform: none; } 22% { transform: scale(1.03, .92); } 34%, 100% { transform: none; } }

.swatches { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 14px; }
.sw { border-radius: 16px; background: var(--app-surface); box-shadow: inset 0 0 0 1px var(--app-line); overflow: hidden; }
.sw .chip { height: 74px; box-shadow: inset 0 -1px 0 var(--app-line); } .sw .chk { background-image: conic-gradient(#999 25%, #eee 0 50%, #999 0 75%, #eee 0); background-size: 18px 18px; }
.sw .chip div { height: 100%; }
.sw p { padding: 10px 12px; font-size: 13px; line-height: 1.3; } .sw code { font: 400 12px 'BrandMono', monospace; color: var(--app-mute); display: block; margin-top: 2px; word-break: break-all; }

.type { display: grid; gap: 22px; background: var(--ground); color: var(--on-ground); border-radius: 22px; padding: 34px 34px 38px; }
.type small { display: block; font: 400 13px 'BrandMono', monospace; opacity: .66; margin-bottom: 6px; }
.t-d { font: 400 66px/1.04 var(--font-display); text-transform: var(--title-transform); overflow-wrap: anywhere; }
.t-h { font: 800 38px/1.2 var(--font-body); } .t-b { font: 700 28px/1.3 var(--font-body); } .t-m { font: 400 22px/1.3 var(--font-mono); }

.plates { display: grid; grid-template-columns: 1.15fr 1fr; gap: 14px; }
.plates .wide, .plates .talls { display: grid; gap: 14px; align-content: start; } .plates .talls { grid-template-columns: 1fr 1fr; }
.plates figure { width: auto; } .plates img { width: 100%; display: block; border-radius: 14px; }
.gs { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-top: 14px; } .gs img { width: 100%; display: block; border-radius: 10px; }
.grains { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 14px; }
.grains div { height: 110px; border-radius: 10px; background-color: var(--ground); position: relative; overflow: hidden; }
.grains div i { position: absolute; inset: 0; background-size: 270px 270px; mix-blend-mode: var(--grain-blend); filter: var(--grain-filter); }

.app { background: var(--app-bg); border-radius: 22px; box-shadow: inset 0 0 0 1px var(--app-line); padding: 18px; }
.masthead { position: relative; border-radius: 18px; overflow: hidden; background: var(--app-ink); display: flex; align-items: center; gap: 18px; padding: 22px 26px; }
.masthead::before { content: ''; position: absolute; inset: -20% -2% -20% auto; width: 55%; background: url('__APPBAND__') right center / cover no-repeat; opacity: .5; -webkit-mask-image: linear-gradient(90deg, transparent, #000 60%); mask-image: linear-gradient(90deg, transparent, #000 60%); }
.masthead img { position: relative; height: 34px; max-width: 220px; object-fit: contain; }
.masthead strong { position: relative; font: 400 26px/1 var(--font-display); color: var(--app-bg); padding-left: 18px; border-left: 1px solid color-mix(in srgb, var(--app-bg) 20%, transparent); }
.app .row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; background: var(--app-surface); border-radius: 14px; margin-top: 12px; padding: 14px 16px; box-shadow: inset 0 0 0 1px var(--app-line); }
.app .row p { flex: 1 1 220px; color: var(--app-ink-2); } .app .row small { color: var(--app-mute); display: block; }
.app .btn { background: var(--app-accent); color: var(--app-on-accent, var(--on-accent)); border-radius: 999px; padding: 8px 18px; font-weight: 600; font-size: 14px; }
.app .tag { background: var(--app-accent-soft); color: var(--app-accent-ink); border-radius: 999px; padding: 6px 12px; font-size: 13px; }

.checks { display: grid; gap: 6px; }
.ck { display: flex; align-items: center; gap: 12px; background: var(--app-surface); box-shadow: inset 0 0 0 1px var(--app-line); border-radius: 12px; padding: 9px 14px; flex-wrap: wrap; }
.ck .aa { width: 44px; height: 30px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 14px; box-shadow: inset 0 0 0 1px rgba(128,128,128,.25); flex: none; }
.ck .nm { flex: 1 1 200px; font-size: 14.5px; } .ck .nm small { color: var(--app-mute); display: block; font-size: 12.5px; }
.ck .rt { font: 400 13px 'BrandMono', monospace; color: var(--app-ink-2); }
.ck .res { font-weight: 600; font-size: 13px; min-width: 96px; text-align: right; }
.res.ok { color: var(--app-accent-ink); } .res.bad { color: #B3261E; }
ul.chg { margin-top: 14px; padding-left: 20px; color: var(--app-ink-2); font-size: 14.5px; } ul.chg li { margin: 4px 0; }
footer { margin-top: 54px; color: var(--app-mute); font-size: 14px; }
@media (max-width: 520px) { h1 { font-size: 30px; } .frames { justify-content: center; } .t-d { font-size: 44px; } }
</style></head><body><main>

<header class="top"><div class="lockup"><img src="__LOGO__" alt="__TITLE__"></div>
<div><h1>Your brand preview</h1></div></header>
<p class="sub">This is how your Shorts will look. Everything here comes from your brand file. The grey people stand in for your video. Nothing on this page makes a sound.</p>
<div class="facts">__FACTS__</div>
<div class="note">Happy with it? Tell Claude "approve". Want a change? Say what, in plain words: "warmer accent", "less texture", "a calmer title font".</div>

<section class="frames">
<figure><div class="fr"><div class="st"><div class="half t">__PA__</div><div class="half b">__PB__</div><div id="q" class="__TITLECLS__">The part nobody <mark>talks about</mark></div></div></div><figcaption>Title card on the seam</figcaption></figure>
<figure><div class="fr"><div class="st"><div class="half t">__PA__</div><div class="half b">__PB__</div><div class="cap"><span>and <b>nobody</b> tells you this</span></div></div></div><figcaption>Split with a caption, spoken word lit</figcaption></figure>
<figure><div class="fr"><div class="st"><div class="half t"><div class="gr-bg"></div><div class="news"><div class="src">Source name</div><div class="t">A real headline sits here on the card plate</div></div></div><div class="half b">__PB__</div></div></div><figcaption>News card</figcaption></figure>
<figure><div class="fr"><div class="st"><div class="half t">__MG__</div><div class="half b">__PA__</div></div></div><figcaption>Motion graphic: "__SIG__" move, __ENERGY__ energy</figcaption></figure>
<figure><div class="fr"><div class="st"><div id="end"><div class="lg"><img src="__LOGO__" alt=""></div><div class="row">__MARKS__</div><div class="pl"><div class="pi"><i></i><div>__CTA__</div></div></div></div></div></div><figcaption>End card</figcaption></figure>
</section>

<h2>Colour</h2><div class="swatches">__SWATCHES__</div>
<h2>Type</h2>
<div class="type">
<div><small>Display: __F_DISPLAY__</small><div class="t-d">__SHOWNAME__</div></div>
<div><small>Body heavy: __F_BODY__ __W_HEAVY__</small><div class="t-h">Captions and labels read like this at a glance</div></div>
<div><small>Body bold: __F_BODY__ __W_BOLD__</small><div class="t-b">Smaller labels sit a step down, 0123456789</div></div>
<div><small>Mono: __F_MONO__</small><div class="t-m">SOURCE, DATE, 12:34</div></div>
</div>
<h2>Texture plates</h2>
<div class="plates">
<div class="wide"><figure><img src="__BAND__" alt=""><figcaption>band</figcaption></figure>
<figure><img src="__CARD__" alt=""><figcaption>card</figcaption></figure>
<figure><img src="__CARDW__" alt=""><figcaption>card_wide</figcaption></figure></div>
<div class="talls"><figure><img src="__TALL__" alt=""><figcaption>tall_a</figcaption></figure>
<figure><img src="__TALLB__" alt=""><figcaption>tall_b</figcaption></figure></div>
</div>
<div class="gs">__GS__</div>
<div class="grains">__GRAINS__</div>

<h2>Your approval app</h2>
<div class="app"><div class="masthead"><img src="__APPLOGO__" alt=""><strong>__APPTITLE__</strong></div>
<div class="row"><p>Episode one, Short 3<small>Waiting for __APPROVER__</small></p><span class="tag">Draft</span><span class="btn">Approve</span></div></div>

<h2>Can people read it?</h2>
<div class="checks">__CHECKS__</div>
__CHANGES__
<footer>Made by setup/preview.py. To change anything, edit brand/brand.json and run python3 setup/build_brand.py, then this page again.</footer>
</main>__MGSCRIPT__
<script>
// A font can load for the pipeline and still be refused by a browser. Say so, instead of quietly showing a fallback.
document.fonts.ready.then(function () {
  var bad = []; document.fonts.forEach(function (f) { if (f.status === 'error') bad.push(f.family); });
  if (bad.length) { var d = document.createElement('div'); d.className = 'note'; d.textContent = 'Warning: a browser could not read this font: ' + bad.join(', ') + '. Your Shorts render in a browser, so pick another file.'; document.querySelector('.sub').after(d); }
});
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser(description='Write the brand preview page.')
    ap.add_argument('--no-open', action='store_true', help='write it, do not open it')
    args = ap.parse_args()
    bf = BRAND_DIR / 'brand.json'
    rep = BRAND_DIR / 'build_report.json'
    if not bf.exists() or not rep.exists():
        sys.exit('Build the brand first: python3 setup/build_brand.py')
    b = json.loads(bf.read_text())
    report = json.loads(rep.read_text())
    tex = BRAND_DIR / 'textures'
    app_css_path = ROOT / 'app' / 'public' / 'brand.css'
    css = embed_fonts(app_css_path.read_text())
    render_css = embed_fonts((BRAND_DIR / 'brand.css').read_text())
    uris = {'BAND': plate(tex / 'band.png', 1100), 'CARD': plate(tex / 'card.png', 1200), 'CARDW': plate(tex / 'card_wide.png', 1200),
            'TALL': plate(tex / 'tall_a.png', 640), 'TALLB': plate(tex / 'tall_b.png', 640), 'GROUND': plate(tex / 'ground.jpg', 1080), 'APPBAND': plate(tex / 'app_band.jpg', 900)}
    grains = [png_file(tex / 'grain' / ('grain_%d.png' % k)) for k in range(4)]
    logo, app_logo = png_file(BRAND_DIR / 'logo.png'), png_file(ROOT / 'app' / 'public' / 'img' / 'logo.png')

    swatch_html = []
    for key, label in SWATCHES:
        v = b['colors'][key]
        cls = ' chk' if cm.parse(v)[3] < 1 else ''
        swatch_html.append('<div class="sw"><div class="chip%s"><div style="background:%s"></div></div><p>%s<code>%s</code></p></div>' % (cls, v, html.escape(label), html.escape(v)))

    checks = []
    for c in report['checks']:
        res = ('<span class="res ok">%s</span>' % ('Pass, fixed' if c.get('fixed') else 'Pass')) if c['ok'] else '<span class="res bad">FAIL</span>'
        why = '<small>%s</small>' % html.escape(c['why']) if c.get('why') else ''
        checks.append('<div class="ck"><div class="aa" style="background:%s;color:%s">Aa</div><div class="nm">%s%s</div><div class="rt">%.1f:1, needs %.1f</div>%s</div>' % (c['bg'], c['fg'], html.escape(c['name']), why, c['ratio'], c['min'], res))
    lines = [html.escape(x) for x in report.get('changes', []) + report.get('notes', [])]
    changes = ('<ul class="chg">%s</ul>' % ''.join('<li>%s</li>' % x for x in lines)) if lines else ''

    f = b['fonts']
    tx = b['texture']
    facts = ['ground: ' + ('dark' if cm.luminance(cm.parse(b['colors']['on_ground'])) > .4 else 'light'), 'texture: %s' % tx.get('style'),
             'seed: %s' % tx.get('seed'), 'move: %s' % b['motion'].get('signature'), 'energy: %s' % b['motion'].get('energy'),
             'people: %d' % len(b['people'])]

    mg_doc = motion_doc(b, render_css, uris['GROUND'], grains)
    if mg_doc:
        mg = '<iframe class="mg" id="mg" title="Motion sample" scrolling="no"></iframe>'
        mg_script = '<script>document.getElementById("mg").srcdoc = %s;</script>' % json.dumps(mg_doc).replace('<', '\\u003c')
    else:
        mg = '<div class="gr-bg"></div><div class="css-mg"><i></i><b>5</b></div>'
        mg_script = ''

    gs = ''.join('<img src="%s" alt="">' % plate(tex / ('g%d.jpg' % k), 420) for k in range(1, 6))
    gr = ''.join('<div><i style="background-image:url(%s);opacity:.35"></i></div>' % u for u in grains)

    rep_map = {
        'TITLE': html.escape(b['show']['name']), 'SHOWNAME': html.escape(b['show']['name']), 'CSS': css,
        'LOGO': logo, 'APPLOGO': app_logo, 'APPTITLE': html.escape(b['app'].get('title', '')), 'APPROVER': html.escape(b['app'].get('approver', '')),
        'FACTS': ''.join('<span>%s</span>' % html.escape(x) for x in facts), 'PA': person_svg('a'), 'PB': person_svg('b'),
        'TITLECLS': 'b-title' if b['title'].get('highlight', 'block') != 'block' else '', 'MG': mg, 'MGSCRIPT': mg_script,
        'SIG': html.escape(b['motion'].get('signature', '')), 'ENERGY': html.escape(b['motion'].get('energy', '')),
        'MARKS': marks(b['end_card'].get('platforms', [])), 'CTA': html.escape(b['end_card'].get('cta', '')),
        'SWATCHES': ''.join(swatch_html), 'CHECKS': ''.join(checks), 'CHANGES': changes, 'GS': gs, 'GRAINS': gr,
        'F_DISPLAY': html.escape(f['display'].get('family', '')), 'F_BODY': html.escape(f['body'].get('family', '')), 'F_MONO': html.escape(f['mono'].get('family', '')),
        'W_HEAVY': str(f['body'].get('heavy', 800)), 'W_BOLD': str(f['body'].get('bold', 700)),
    }
    rep_map.update(uris)
    page = re.sub(r'__([A-Z_]+)__', lambda m: rep_map.get(m.group(1), m.group(0)), PAGE)
    out = BRAND_DIR / 'preview' / 'index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print('Preview: %s (%.1f MB)' % (out, out.stat().st_size / 1e6))
    if not args.no_open:
        subprocess.run(['open', str(out)], check=False)


if __name__ == '__main__':
    main()

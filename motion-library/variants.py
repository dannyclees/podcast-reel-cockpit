#!/usr/bin/env python3
"""variants.py <name ...>: render a treatment with a Short's own numbers and names (R74). Output renders/<name>/preview.mp4.
Each variant = a treatment + text replacements on its index.html. Add new ones to V."""
import os, shutil, subprocess, sys
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, '..', 'pipeline'))
import logos
# R77: graphics pop up at once, people have very short attention spans. The first bar moves on frame 0
FAST_SCALE = [("go({ v1: IN.a }, .3, .8, 'expo.out');", "go({ v1: IN.a }, 0, .6, 'expo.out');"),
              ("K.rise(document.getElementById('n1'), .45); K.rise(v1, .3, 20, .3);", "K.rise(document.getElementById('n1'), 0); K.rise(v1, 0, 20, .3);")]
# Copy one of these per Short, with its real numbers and names. Logos: src="logos/<name>.svg" is fetched from simple-icons into the render.
V = {
 # two prices side by side; the ratio sits off the bars so it never covers the picture
 'scale-example': ('scale-reveal', [("#x { left: 160px; top: 300px; font-size: 168px;", "#x { left: 64px; top: 36px; font-size: 118px;"),
                                    ("const IN = { a: 7000, b: 40000 };", "const IN = { a: 4000, b: 40000 };"), ("5.7&times;", "10&times;")] + FAST_SCALE),
 # a plain number change
 'age-example': ('age-shrink', [('const IN = { from: 30, to: 70, loss: .30 };', 'const IN = { from: 30, to: 70, loss: .25 };')]),
 # two years on a tape
 'year-example': ('year-tape', [("const IN = { from: 2026, mid: 2028, to: 2048 };", "const IN = { from: 2015, mid: 2020, to: 2026 };"), ('>Launch<', '>Still here<')]),
 # the inputs as they are
 'map-example': ('map-drop', []),
}
for name in sys.argv[1:] or V:
    src, reps = V[name]; d = os.path.join(H, 'renders', name)
    if os.path.exists(d): shutil.rmtree(d)
    shutil.copytree(os.path.join(H, 'treatments', src), d)
    for f in ('brand.css', 'gsap.min.js', 'hyperframes.json', 'kit.css', 'kit.js'): shutil.copy(os.path.join(H, 'shared', f), d)
    for sub in ('fonts', 'logos'):
        shutil.rmtree(os.path.join(d, sub), ignore_errors=True); shutil.copytree(os.path.join(H, 'shared', sub), os.path.join(d, sub))
    h = open(os.path.join(d, 'index.html')).read()
    for a, b in reps:
        assert a in h, (name, a); h = h.replace(a, b)
    # R78: in a Short a graphic holds its last state until the
    # next picture covers it; the library's 4.2 s fade-out left an empty top panel
    import re
    h = re.sub(r"K\.exit\([^;]*?\);", "", h)
    open(os.path.join(d, 'index.html'), 'w').write(h)
    for lg in re.findall(r'src="logos/([a-z0-9-]+)\.svg"', h):   # a real mark for this Short, fetched once
        got = logos.fetch(lg, d) if not os.path.exists(os.path.join(d, 'logos', lg + '.svg')) else None
    for f in ('preview.mp4', 'strip.jpg', 'poster.jpg'):
        if os.path.exists(os.path.join(d, f)): os.remove(os.path.join(d, f))
    env = dict(os.environ, HYPERFRAMES_NO_TELEMETRY='1', HYPERFRAMES_SKIP_SKILLS='1')
    r = subprocess.run(['npx', '--yes', 'hyperframes@0.8.181', 'render', '--quality', 'looks', '-w', '4', '--output', 'preview.mp4'], cwd=d, env=env,
                       stdin=subprocess.DEVNULL, capture_output=True, text=True)
    subprocess.run("ps -axo pid=,ppid=,command= | awk '$2==1 && /chrome-headless-shell/ {print $1}' | xargs kill 2>/dev/null", shell=True)
    print(name, 'ok' if os.path.exists(os.path.join(d, 'preview.mp4')) else 'FAILED: ' + (r.stdout + r.stderr)[-300:])

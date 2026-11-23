#!/usr/bin/env python3
"""build.py <short id> [--render] [--only r1,r2] [--spec]: the motion graphics for one Short.

A Short is cut into segments on words: "full" = the speaker full screen (opinions, R79), "split" + a run = a motion
graphic in the top half. One RUN = one HyperFrames comp = one mp4 (mgs_<run>.mp4 in the clip dir) that holds several
beats, so the graphics grow out of each other inside it (not cut, not cross-faded). Beats land on their words:
the run's JS gets c(src) = the local second the word with that source index starts, minus one frame (never late).

Input: motion/beats/<id>.json  {clip, out, name, opener, end, segments: [[src, "full"] | [src, "split", run]], runs: {run: {js, assets}}}
       motion/comps/<id>/<run>.js   the run's beats, written with motion/kit/kit.js (window.K)
Output: motion/comps/<id>/<run>/ (the comp), <clip>/mgs_<run>.mp4, and with --spec the short.py spec <out>/<name>.json
"""
import argparse, json, os, shutil, subprocess, sys
M = os.path.dirname(os.path.abspath(__file__))   # this motion/ folder
sys.path.insert(0, os.path.join(os.path.dirname(M), 'pipeline'))
import brand, logos
EP = str(brand.EPISODES)
HF = 'hyperframes@0.8.181'; FPS = 30


def load(id_):
    B = json.load(open(os.path.join(M, 'beats', id_ + '.json')))
    D = os.path.join(EP, B['clip']); words = json.load(open(os.path.join(D, 'words.json')))
    by_src = {}
    for w in words:
        if not w.get('added') and w.get('src') not in by_src: by_src[w['src']] = w   # same lookup as short.py T()
    dur = float(json.load(open(os.path.join(D, 'segs.json')))['duration'])
    T = lambda src, at='start', d=-0.08: round(max(0.0, by_src[src][at] + d), 3)   # short.py: segment time = word start - 0.08
    if B.get('end'): dur = min(dur, T(B['end'][0], 'end', B['end'][1]))
    return B, D, words, by_src, dur, T


def run_windows(B, T, dur):
    """each run: (t0, t1) on the Short's clock. t0 = its first segment time (0 for the opener's top), t1 = when it is covered."""
    segs = [[0.0 if s[0] == 'open' else T(s[0])] + s[1:] for s in B['segments']]
    if B['opener'].get('top'): segs.insert(0, [0.0, 'split', B['opener']['top']])
    segs.sort(key=lambda s: s[0]); win = {}
    for k, s in enumerate(segs):
        if s[1] == 'split' and len(s) > 2:
            nxt = next((x[0] for x in segs[k + 1:] if not (x[1] == 'split' and len(x) > 2 and x[2] == s[2])), dur)
            if s[2] not in win: win[s[2]] = [s[0], nxt]
            else: win[s[2]][1] = nxt
    return segs, win


def build_run(id_, run, B, D, words, by_src, t0, t1, render):
    R = B['runs'][run]; C = os.path.join(M, 'comps', id_, run); os.makedirs(os.path.join(C, 'a'), exist_ok=True)
    for f in ('brand.css', 'kit.css', 'kit.js', 'gsap.min.js', 'hyperframes.json'): shutil.copy(os.path.join(M, 'kit', f), C)
    for sub in ('fonts', 'img'):
        if os.path.exists(os.path.join(C, sub)): shutil.rmtree(os.path.join(C, sub))
        shutil.copytree(os.path.join(M, 'kit', sub), os.path.join(C, sub))
    for a in R.get('assets', []):   # "logo:name" (simple-icons, kept in the clip's logos/) | a file in the clip dir | {"clip": "screen.mp4", "from": src, "to": src, "crop": [x0,y0,x1,y1], "as": "x.mp4"}
        if isinstance(a, str) and a.startswith('logo:'):
            n = a[5:]; src = logos.fetch(n, D)
            if src: shutil.copy(src, os.path.join(C, 'a', n + '.svg'))
        elif isinstance(a, str):
            shutil.copy(os.path.join(D, a) if os.path.exists(os.path.join(D, a)) else os.path.join(M, 'assets', a), os.path.join(C, 'a', os.path.basename(a)))
        else:   # a piece of the screen share, cut on the Short's clock so it plays in time with what is said
            a0 = t0; dd = t1 - t0 + 1.2
            vf = f"crop={a['crop'][2]-a['crop'][0]}:{a['crop'][3]-a['crop'][1]}:{a['crop'][0]}:{a['crop'][1]}," if a.get('crop') else ''
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a0:.3f}', '-i', os.path.join(D, a['clip']), '-t', f'{dd:.3f}', '-an',
                            '-vf', vf + f"scale={a.get('w', 1280)}:-2,fps=30", '-c:v', 'libx264', '-crf', '16', '-g', '30', '-keyint_min', '30',
                            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', os.path.join(C, 'a', a['as'])], check=True)
    cues = {}
    for w in words:
        if w.get('added') or w['src'] in cues: continue
        cues[w['src']] = [round(w['start'] - t0 - 1 / FPS, 3), round(w['end'] - t0, 3)]
    cues_i = {w['i']: [round(w['start'] - t0 - 1 / FPS, 3), round(w['end'] - t0, 3)] for w in words}
    dur = round(t1 - t0 + 0.9, 2)   # + the glide out of the split
    js = open(os.path.join(M, 'comps', id_, R['js'])).read()
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="UTF-8"/><meta name="viewport" content="width=1080, height=960"/>
<title>{id_} {run}</title><script src="gsap.min.js"></script><link rel="stylesheet" href="brand.css"/><link rel="stylesheet" href="kit.css"/><style>{brand.GRAIN_CSS}</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-fps="{FPS}" data-width="1080" data-height="960"></div>
<script>window.BRAND_MOTION = {json.dumps(brand.BRAND.get('motion', {}))};</script>
<script src="kit.js"></script>
<script>
(function () {{
const CUES = {json.dumps(cues)}, CUESI = {json.dumps(cues_i)}, DUR = {dur};
const c = s => {{ if (!(s in CUES)) throw new Error('no word with src ' + s); return CUES[s][0]; }};   // the word starts (one frame early)
const ce = s => CUES[s][1];                                                                       // the word ends
const ci = i => CUESI[i][0];                                                                       // by clip word index
const tl = K.init(DUR); const A = 'a/';
{js}
K.finish();
}})();
</script></body></html>'''
    open(os.path.join(C, 'index.html'), 'w').write(html)
    json.dump(dict(name=f'mgs-{id_}-{run}', private=True, type='module'), open(os.path.join(C, 'package.json'), 'w'))
    json.dump(dict(id=run, name=run), open(os.path.join(C, 'meta.json'), 'w'))
    out = os.path.join(D, f'mgs_{run}.mp4')
    if render:
        env = dict(os.environ, HYPERFRAMES_NO_TELEMETRY='1', HYPERFRAMES_SKIP_SKILLS='1')
        for w in ('4', '2'):   # a render can time out when other renders share the machine: try again with fewer workers
            if os.path.exists(os.path.join(C, 'out.mp4')): os.remove(os.path.join(C, 'out.mp4'))
            r = subprocess.run(['npx', '--yes', HF, 'render', '--quality', 'standard', '-w', w, '--output', 'out.mp4'], cwd=C, env=env,
                               capture_output=True, text=True, stdin=subprocess.DEVNULL)
            subprocess.run("ps -axo pid=,ppid=,command= | awk '$2==1 && /chrome-headless-shell/ {print $1}' | xargs kill 2>/dev/null", shell=True)
            if r.returncode == 0 and os.path.exists(os.path.join(C, 'out.mp4')): break
        if r.returncode != 0 or not os.path.exists(os.path.join(C, 'out.mp4')):
            print(f'{id_} {run}: RENDER FAILED', (r.stdout + r.stderr)[-1500:]); return None
        shutil.copy(os.path.join(C, 'out.mp4'), out)
        print(f'{id_} {run}: rendered {dur:.2f} s -> {out}')
    return out


def write_spec(id_, B, segs, T):
    media = {run: dict(kind='video', file=f'mgs_{run}.mp4', fit='cover', bg='var(--ground)') for run in B['runs']}
    media.update(B.get('media', {}))
    spec = dict(opener=dict(B['opener']), segments=[], media=media, min_turn=1.2)
    if isinstance(spec['opener'].get('hold'), list): spec['opener']['hold'] = dict(w=B['opener']['hold'][0], at='end', d=B['opener']['hold'][1])
    for s in B['segments']:
        if s[0] == 'open': continue
        spec['segments'].append([dict(w=s[0])] + s[1:])
    if B.get('end'): spec['end'] = dict(w=B['end'][0], at='end', d=B['end'][1])
    for k in ('sources', 'sources_none', 'content_ok', 'sfx', 'safe_right', 'cap_split_y', 'cap_full_y', 'cap_pic_y', 'cap_glide_y'):   # a rebuild keeps what the spec says beyond the segments (R122)
        if k in B: spec[k] = B[k]
    out = os.path.join(EP, B['out']); os.makedirs(out, exist_ok=True)
    json.dump(spec, open(os.path.join(out, B['name'] + '.json'), 'w'), indent=1); print('wrote', os.path.join(out, B['name'] + '.json'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('id'); ap.add_argument('--render', action='store_true'); ap.add_argument('--only'); ap.add_argument('--spec', action='store_true')
    a = ap.parse_args()
    B, D, words, by_src, dur, T = load(a.id)
    segs, win = run_windows(B, T, dur)
    only = set(a.only.split(',')) if a.only else None
    for run, (t0, t1) in win.items():
        if run not in B['runs'] or (only and run not in only): continue   # a split can also show a plain media item from B['media'] (R118 SPLIT-IMG)
        print(f'{a.id} {run}: {t0:.2f} -> {t1:.2f} s')
        build_run(a.id, run, B, D, words, by_src, t0, t1, a.render)
    if a.spec: write_spec(a.id, B, segs, T)

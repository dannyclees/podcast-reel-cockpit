#!/usr/bin/env python3
"""short.py <clip dir> <edit6.json> <out.mp4> [--music track.mp3]: render a whole Short as ONE HyperFrames page.

Why: every rule lives in one renderer, so the opener styles only change the first seconds and everything else stays the same:
  R21 face first, R38 heads whole (speakers are 1.125:1 panels cut from the full source height; the page only crops sides),
  R37 lips in sync (cut.py video_offset), R7 only the speaker on screen, R45 glide into / out of a split (0.75 s),
  pictures always move, R47 captions word by word on the render clock (spoken word in the --cap-spoken colour), R48 title on the card plate,
  R26 "look at this" = the real screen crop, R46 end card intro, R17 two mixes (clean, and music + gentle sound effects).
Colours, fonts, plates, logo, sounds and people all come from brand/ (pipeline/brand.py). The page links brand.css.

edit6.json:
{"opener": {"style": "doac", "question": "WHY DOES A QUESTION<br>STOP THE SCROLL?", "hold": 3.4}
        or {"style": "texture", "title": "A SHORT TITLE LINE<br><mark>WITH ONE MARKED PART</mark>", "hold": 2.4, "top": "pic1"}
        or {"style": "headline", "media": "source1", "hold": 3.0},
 "segments": [[2.4, "split", "pic1"], [11.2, "split", "source1"], [13.6, "split", "map"], [17.5, "full"], ...],   # from time t
 "media": {"pic1": {"kind": "video", "file": "clip.mp4"},
           "map": {"kind": "video", "file": "map-drop.mp4", "fit": "contain", "bg": "var(--paper)"},
           "chart": {"kind": "screen", "crop": [1056, 40, 1900, 1000], "zoom": [[26.5, [1478, 540, 1900, 1000]]]},
           "img": {"kind": "image", "file": "x.jpg", "fit": "cover"},
           "source1": {"kind": "headline", "outlet": "NEWS OUTLET", "date": "1 JAN", "text": "The line as it was printed ..."}},
 "min_turn": 1.2}
"""
import argparse, json, os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand, cardbg, logos
from brand import BRAND, FONT, IDS

HF = 'hyperframes@0.8.181'
ML = str(brand.ROOT / 'motion-library' / 'shared')
VENDOR = str(brand.ROOT / 'pipeline' / 'vendor')
FT = str(brand.FACE_TRACK)
PANEL = {(1920, 1080): (1215, 1080), (1280, 720): (810, 720)}   # 1.125:1 at full source height
KIT = str(brand.SFX)
END = 2.6


def probe(f, what='format=duration'):
    return subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', what, '-of', 'csv=p=0', f], capture_output=True, text=True).stdout.strip()


def panel(src, dst, cx):
    w, h = map(int, probe(src, 'stream=width,height').split(','))
    pw, ph = PANEL.get((w, h), (min(w, round(h * 1.125)), h))
    x = int(max(0, min(w - pw, cx * w - pw / 2)))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', f'crop={pw}:{ph}:{x}:0,scale=1080:960,setsar=1', '-an', '-r', '30',
                    '-c:v', 'libx264', '-crf', '17', '-g', '15', '-pix_fmt', 'yuv420p', dst], check=True)


def turns(words, dur, min_turn, engaged=None):
    """who is on screen when: the speaker of the current words; a turn shorter than min_turn s is a reaction, not a cut.
    R73: a short turn (under 4 s) only cuts to that person if they look engaged (engaged(who, a, b) is True)."""
    runs = []
    for w in words:
        if runs and runs[-1][2] == w['spk']: runs[-1][1] = w['end']
        else: runs.append([w['start'], w['end'], w['spk']])
    keep = [r for r in runs if r[1] - r[0] >= min_turn] or runs
    if engaged: keep = [r for k, r in enumerate(keep) if k == 0 or r[1] - r[0] >= 4.0 or engaged(r[2], r[0], r[1])]
    out = []
    for r in keep:
        if out and out[-1][1] == r[2]: continue
        out.append([0.0 if not out else round(r[0] - 0.08, 3), r[2]])
    return out


def engagement(W, who_list):
    """face tracking of each speaker panel (Apple Vision): engaged = eyes open and not looking well down or away,
    judged against that person's own normal (their median pitch and gaze over the clip)."""
    import numpy as np
    data = {}
    for who in who_list:
        src = os.path.join(W, 'media', f'{who}.mp4'); out = os.path.join(W, f'face_{who}.json')
        if not os.path.exists(src): continue
        if not os.path.exists(out): subprocess.run([FT, src, out, '10'], capture_output=True)
        if os.path.exists(out): data[who] = [f for f in json.load(open(out))['frames'] if f.get('box')]
    base = {w: (float(np.median([f.get('pitch') or 0 for f in F] or [0])), float(np.median([f.get('gaze') or 0 for f in F] or [0]))) for w, F in data.items()}
    def engaged(who, a, b):
        F = [f for f in data.get(who, []) if a <= f['t'] <= b]
        if not F: return False
        p0, g0 = base[who]
        bad = [f for f in F if (f.get('eyes') or 1) < 0.12 or (f.get('pitch') or 0) > p0 + 6 or (f.get('gaze') or 0) > g0 + 0.25]
        return len(bad) / len(F) < 0.4
    return engaged


def listener_track(W, who, words, dur):
    """R79 + R73: the duo's top panel for `who` as a listener. Where they look down (eyes narrow or head tipped down,
    judged against their own best: 75th-pct eye opening, 25th-pct pitch), that stretch is filled with a moment from
    the same clip where they are looking up, listening and not talking (a cutaway). Writes media/oth_<who>.mp4."""
    import numpy as np
    src = os.path.join(W, 'media', f'{who}.mp4'); out = os.path.join(W, 'media', f'oth_{who}.mp4'); fj = os.path.join(W, f'face_{who}.json')
    if not os.path.exists(fj): subprocess.run([FT, src, fj, '10'], capture_output=True)
    F = {round(f['t'], 1): f for f in json.load(open(fj))['frames'] if f.get('box')} if os.path.exists(fj) else {}
    if not F: shutil.copy(src, out); return 0
    e_ref = float(np.percentile([f.get('eyes') or 0 for f in F.values()], 75)); p_ref = float(np.percentile([f.get('pitch') or 0 for f in F.values()], 25))
    talk = [(w['start'] - .3, w['end'] + .3) for w in words if w['spk'] == who]
    n = int(dur * 10)
    def ok(k):
        f = F.get(round(k / 10, 1))
        return bool(f) and (f.get('eyes') or 0) >= .75 * e_ref and (f.get('pitch') or 0) <= p_ref + 7
    good = [ok(k) for k in range(n)]
    quiet = [not any(a <= k / 10 <= b for a, b in talk) for k in range(n)]
    pool, k = [], 0   # cutaway sources: 1 s+ runs that are engaged and silent
    while k < n:
        if good[k] and quiet[k]:
            j = k
            while j < n and good[j] and quiet[j]: j += 1
            if j - k >= 10: pool.append((k / 10, j / 10))
            k = j
        else: k += 1
    # smooth: a bad stretch under 0.6 s stays as it is (a blink, a glance)
    bad, k = [], 0
    while k < n:
        if not good[k]:
            j = k
            while j < n and not good[j]: j += 1
            if j - k >= 6: bad.append((k / 10, j / 10))
            k = j
        else: k += 1
    if not bad or not pool: shutil.copy(src, out); return 0
    pieces, t, pi, off = [], 0.0, 0, 0.0
    for a, b in bad:
        if a > t: pieces.append((t, a))
        need = b - a
        while need > 0.05:   # fill from the pool in order, at most the rest of the current source run
            s0, s1 = pool[pi % len(pool)]; take = min(need, s1 - s0 - off)
            pieces.append((s0 + off, s0 + off + take)); need -= take; off += take
            if s0 + off >= s1 - .05: pi += 1; off = 0.0
        t = b
    if t < dur: pieces.append((t, dur))
    fc = ''.join(f'[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[p{i}];' for i, (a, b) in enumerate(pieces))
    fc += ''.join(f'[p{i}]' for i in range(len(pieces))) + f'concat=n={len(pieces)}:v=1:a=0[v]'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-filter_complex', fc, '-map', '[v]', '-r', '30', '-c:v', 'libx264', '-crf', '17',
                    '-g', '15', '-pix_fmt', 'yuv420p', out], check=True)
    print(f'listener {who}: {len(bad)} look-down stretch(es) replaced, {sum(b - a for a, b in bad):.1f} s')
    return len(bad)


_FONTS = {}
CAP_PX = 56   # caption size; main() lowers it only if one single word would not fit on the line


def _font(kind, size):
    """the brand's real font file, so every width below is measured, never guessed."""
    from PIL import ImageFont
    if (kind, size) not in _FONTS: _FONTS[(kind, size)] = ImageFont.truetype(str(FONT[kind]), size)
    return _FONTS[(kind, size)]


def cap_w(text):
    """Pixel width of a caption line at the #cap size and font, in the case it shows on screen."""
    return _font('heavy', CAP_PX).getlength(text.upper() if BRAND['caption'].get('uppercase') else text)


CAP_MAX_W = 860   # R76: #cap span is 960 px wide with 34 px padding each side, so a line wider than this would wrap


def chunks(ws, mx=7, maxw=None):
    """R68: two or three words at a time flicker, so a caption is a whole phrase, up to ~7 words,
    broken at a sentence end, a long pause or a speaker change (a comma only once the line has 4+ words).
    R76 one line of text maximum: a phrase also breaks before it would grow wider than one line."""
    out, cur = [], []
    for k, w in enumerate(ws):
        if cur:
            p = ws[k - 1]; gap = w[1] - p[2]
            wide = cap_w(' '.join(x[0] for x in cur + [w])) > (maxw or CAP_MAX_W)
            if wide or len(cur) >= mx or gap > 0.45 or p[0][-1:] in '.?!' or w[3] != p[3] or (p[0][-1:] == ',' and len(cur) >= 4):
                out.append(cur); cur = []
        cur.append(w)
    if cur: out.append(cur)
    # R86: a width or 7-word break could strand the sentence's last word alone for 0.1 s, a one-word flash. Pull the previous phrase's last word over when it is the same sentence, same speaker, and fits.
    for k in range(1, len(out)):
        p, c = out[k - 1], out[k]
        if len(c) == 1 and len(p) >= 3 and p[-1][0][-1:] not in '.?!' and p[-1][3] == c[0][3] and c[0][1] - p[-1][2] <= 0.45 \
                and c[0][2] - c[0][1] < 0.45 and cap_w(' '.join(x[0] for x in [p[-1]] + c)) <= (maxw or CAP_MAX_W):
            out[k] = [p.pop()] + c
    return out


def clean_voice(D):
    """R16 + R37: the Auphonic-clean voice of THIS cut. Rebuilt whenever voice.wav is newer (a stale voice_clean.wav
    from an older cut under a new picture puts every render out of sync). Then proven:
    same length and 0 ms lag against voice.wav, or the raw voice is used."""
    sys.path.insert(0, VENDOR)
    from _sync import load, env_db, lag_ms
    D = os.path.abspath(D); voice, clean = os.path.join(D, "voice.wav"), os.path.join(D, "voice_clean.wav")
    if not os.path.exists(clean) or os.path.getmtime(clean) < os.path.getmtime(voice):
        os.makedirs(os.path.join(D, 'work'), exist_ok=True)
        mov, outv = os.path.join(D, 'work', 'voice_for_auphonic.mov'), os.path.join(D, 'work', 'voice_auphonic.mp4')
        d = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', voice], capture_output=True, text=True).stdout)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=black:s=320x240:r=30:d={d:.3f}', '-i', voice, '-map', '0:v', '-map', '1:a',
                        '-c:v', 'libx264', '-c:a', 'pcm_s24le', '-shortest', mov], check=True)
        r = subprocess.run(['python3', os.path.join(VENDOR, 'auphonic.py'), mov, '--out', outv, '--title', os.path.basename(D)],
                           cwd=str(brand.ROOT), capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(outv):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', outv, '-vn', '-ac', '1', '-ar', '48000', '-c:a', 'pcm_s24le', clean], check=True)
        else:
            print('auphonic failed, using the raw voice:', (r.stdout + r.stderr).strip().splitlines()[-1:]); return voice
    lag, sc = lag_ms(env_db(load(voice)), env_db(load(clean)), 3000)
    dv = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', voice], capture_output=True, text=True).stdout)
    dc = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', clean], capture_output=True, text=True).stdout)
    if abs(lag) > 20 or abs(dv - dc) > 0.1:
        print(f'clean voice does not match this cut (lag {lag} ms, {dv:.2f} vs {dc:.2f} s): using the raw voice'); return voice
    print(f'clean voice matches this cut (lag {lag} ms)'); return clean


def verify_sync(out, W, D, turns_, segs_js, dur, voice):
    """R55 hard gate on the FINAL file: (a) its sound lines up with this cut's voice.wav (0 +-20 ms);
    (b) its picture shows the speaker panel frame for frame: on full-screen stretches, final frames are matched against
    the panel video (same crop) within +-10 frames; the best match must be 0 +-1 frame."""
    sys.path.insert(0, VENDOR)
    from _sync import load, env_db, lag_ms
    import numpy as np
    lag, sc = lag_ms(env_db(load(voice)), env_db(load(out)), 2000)
    res = {'audio_lag_ms': lag}
    def grey(f, a, n, vf):
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{a:.3f}', '-i', f, '-frames:v', str(n), '-vf', vf + ',scale=48:86,format=gray',
                              '-f', 'rawvideo', '-'], capture_output=True).stdout
        return np.frombuffer(raw, np.uint8).reshape(-1, 86, 48).astype(float)
    full = []   # full-screen windows: no split in force, one speaker for 3 s
    lay = [(t, l) for t, l, *r in segs_js]
    for k, (t, who) in enumerate(turns_):
        end = turns_[k + 1][0] if k + 1 < len(turns_) else dur
        for a in np.arange(t + 0.5, end - 3.0, 4.0):
            cur = [l for tt, l in lay if tt <= a + 0.8]
            nxt = [tt for tt, l in lay if a - 0.8 < tt < a + 3.8]
            if (not cur or cur[-1] == 'full') and not nxt: full.append((float(a), who))
    lags = []
    wins = [(a, who, 'full') for a, who in full[:4]]
    if len(wins) < 2:   # mostly split: check the speaker in the bottom half instead
        for k, (t, who) in enumerate(turns_):
            end = turns_[k + 1][0] if k + 1 < len(turns_) else dur
            for a in np.arange(t + 0.5, end - 3.0, 4.0):
                cur = [l for tt, l in lay if tt <= a - 0.8]
                nxt = [tt for tt, l in lay if a - 0.8 < tt < a + 3.8]
                if cur and cur[-1] == 'split' and not nxt: wins.append((float(a), who, 'split'))
        wins = wins[:4]
    for a, who, kind in wins:
        if kind == 'full':
            fin = grey(out, a, 60, 'null'); src = grey(os.path.join(W, 'media', f'{who}.mp4'), a - 10 / 30, 80, 'scale=2160:1920,crop=1080:1920')
        else:
            fin = grey(out, a, 60, 'crop=1080:960:0:960'); src = grey(os.path.join(W, 'media', f'{who}.mp4'), a - 10 / 30, 80, 'null')
        if len(fin) < 50 or len(src) < 75: continue
        err = [np.mean((fin[:50] - src[10 + k:60 + k]) ** 2) for k in range(-10, 11)]
        lags.append(int(np.argmin(err)) - 10)
    res['picture_lag_frames'] = lags
    ok = abs(lag) <= 20 and lags and all(abs(x) <= 1 for x in lags)
    print(f"sync check: sound {lag} ms, picture {lags} frames -> {'PASS' if ok else 'FAIL'}")
    return ok


def title_px(title, width, top=68, font='display'):
    """R88: measured with the real font, in the case it shows on screen, as big as fits up to top px. It always fits, in any
    font. A title that would fall under 60 px is hard to read: break the line or cut words (R121: 2 lines at most)."""
    import re as _re
    f = _font(font, 100)
    up = (lambda t: t.upper()) if BRAND['title'].get('uppercase') else (lambda t: t)
    w100 = max(f.getlength(up(_re.sub(r'<[^>]+>', '', x))) + (28 if '<mark>' in x else 0) * 100 / 64 for x in title.split('<br>'))
    px = int(min(top, width * 100 / w100))
    if px < 60: print(f'WARNING R88: title at {px}px, break the line or cut words: {title}')
    return px


def fit_px(text, width, top, font='heavy', track=0.0):
    """Biggest size up to top px at which one nowrap line fits width. track = letter-spacing in em."""
    w100 = _font(font, 100).getlength(text) + track * 100 * len(text)
    return int(min(top, width * 100 / w100))


def logo_box():
    """The logo keeps its own shape: fit it inside the old 600 x 259 box, standing on the same floor line."""
    from PIL import Image
    w, h = Image.open(brand.LOGO).size; sc = min(600 / w, 259 / h); lw, lh = round(w * sc), round(h * sc)
    return lw, lh, round((1080 - lw) / 2), 640 + 259 - lh


def onset(path):
    """Seconds of lead-in before the first sound in a file."""
    import numpy as np
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True, check=True).stdout
    x = np.abs(np.frombuffer(raw, np.int16).astype(float)) / 32768
    return float(np.argmax(x > 0.01)) / 16000 if (x > 0.01).any() else 0.0


def listeners(turns_, hosts):
    """R79: who the top panel shows while someone talks. With two people, the other one. With three, the last other person
    who spoke (the next id if nobody has yet). Alone: nobody."""
    out, last = [], None
    for t, who in turns_:
        others = [h for h in hosts if h != who]
        out.append([t, (last if last in others else others[0]) if others else None]); last = who
    return out


CSS = r'''
html, body { margin: 0; background: var(--ground); } * { box-sizing: border-box; }
#root { position: relative; width: 1080px; height: 1920px; overflow: hidden; background: var(--ground); }
.spk { position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; opacity: 0; }
#tp { position: absolute; left: 0; top: 0; width: 1080px; height: 960px; overflow: hidden; background: var(--ground); z-index: 3; }
.m { position: absolute; inset: 0; opacity: 0; overflow: hidden; }
.m > img, .m > video { position: absolute; left: 0; top: 0; width: 100%; height: 100%; }
.m.scr .z { width: auto; height: auto; max-width: none; transform-origin: 0 0; }
__CARDBG_CSS__
.hl .src { display: flex; justify-content: space-between; font: 800 30px var(--font-body); letter-spacing: .12em; color: var(--mute); margin-bottom: 22px; }
.hl .src b { color: var(--on-paper); }
.hl .t { font: 800 58px/1.12 var(--font-body); letter-spacing: -.01em; }
.hl .t img.il { height: 64px; width: 64px; vertical-align: -12px; margin: 0 6px; }
.m .oth { opacity: 0; object-fit: cover; }
.other { position: absolute; left: 0; top: 0; width: 1080px; height: 960px; object-fit: cover; z-index: 4; opacity: 0; }
#band { position: absolute; left: 0; top: 1450px; width: 1080px; height: 380px; z-index: 6; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 26px;
  background: radial-gradient(ellipse 60% 64% at 50% 50%, var(--ground) 62%, transparent 100%), url('band.png') center/cover; opacity: 0; }
#band .tx { font: 400 84px/1.1 var(--font-display); color: var(--on-ground); text-align: center; padding: 0 60px; white-space: nowrap; text-transform: var(--title-transform); }
#band mark { background: var(--accent); color: var(--on-accent); padding: 0 16px; border-radius: 8px; }
#qbox { position: absolute; left: 50%; top: 960px; transform: translate(-50%, -50%); background: var(--paper); color: var(--on-paper); font: 800 76px/1.06 var(--font-body); text-align: center; padding: 34px 54px 30px; white-space: nowrap; z-index: 7; opacity: 0; text-transform: var(--title-transform); }
#qbox.seam { width: 1000px; background: url('card.png') center/cover; color: var(--on-ground); border-radius: 30px;
  padding: 40px 40px 44px; white-space: normal; box-shadow: 0 30px 60px -20px rgba(0,0,0,.7); }
#qbox.seam .tx { font: 400 74px/1.12 var(--font-display); text-align: center; white-space: nowrap; }
#qbox.seam mark { background: var(--accent); color: var(--on-accent); padding: 0 14px; border-radius: 8px; }
#cap { position: absolute; left: 0; right: 0; text-align: center; visibility: hidden; z-index: 8; }
#cap span { display: inline-block; background: var(--cap-box); color: var(--cap-text); font: 800 __CAP_PX__px/1.18 var(--font-body); padding: 16px 34px; border-radius: var(--cap-radius); max-width: 960px; white-space: nowrap; text-transform: var(--cap-transform); }
#cap b { color: var(--cap-spoken); font-weight: 800; }
#end { position: absolute; inset: 0; background: var(--ground); z-index: 20; opacity: 0; }
#end .tex { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
#end #hLogo { position: absolute; border-radius: 18px; overflow: hidden; background: var(--ground); }
#end #hLogo img { position: absolute; left: 0; top: 0; width: 100%; height: 100%; object-fit: contain; }
#end #layer { position: absolute; border-radius: 18px; background: var(--accent); opacity: 0; }
#end .ic { position: absolute; top: 990px; width: 64px; height: 64px; display: block; opacity: 0; color: var(--on-ground); }
#end .ic svg { width: 100%; height: 100%; display: block; }
#end #ctaWrap { position: absolute; left: 0; right: 0; top: 1120px; display: flex; justify-content: center; }
#end #ctaInner { position: relative; opacity: 0; }
#end #ctaLayer { position: absolute; inset: 0; border-radius: 26px; background: var(--accent); }
#end #ctaBox { position: relative; background: var(--paper); color: var(--on-paper); border-radius: 26px; padding: 30px 54px; font: 800 48px/1 var(--font-body); letter-spacing: .08em; white-space: nowrap; }
'''

JS = r'''
const S = __SPEC__;
const tl = gsap.timeline({paused: true}); window.__timelines = window.__timelines || {}; window.__timelines['main'] = tl;
const $ = q => document.querySelector(q), E = 'power3.inOut', G = 0.75;
tl.set('#tp', {yPercent: S.lay0 === 'split' ? 0 : -101}, 0);   // one start position: a panel moved off and back on at 0 s left its videos black in HyperFrames
// who is on screen (R7)
S.turns.forEach(([t, who]) => { document.querySelectorAll('.spk').forEach(v => tl.set(v, {opacity: v.dataset.who === who ? 1 : 0}, t)); });
// R79 duo: the top panel shows the listener while another person talks
S.listeners.forEach(([t, who]) => { document.querySelectorAll('.oth').forEach(v => tl.set(v, {opacity: v.dataset.who === who ? 1 : 0}, t)); });
// layouts: full <-> split glide (R45); captions hide while a face moves (R23)
// R86: hiding the caption for 0.8 s at every layout change blanks it mid-phrase, 6-17 times a Short.
// The caption never hides for a glide: short.py parks it on the low line (cap_glide_y 1800, under every chin)
// for the glide and puts it on its new line when the glide lands (see capy). R23 still holds: no face moves under it.
let lay = S.lay0;
if (lay === 'split') tl.set('.spk', {top: 960, height: 960}, 0);
S.lays.forEach(([t, l]) => {
  if (l === lay) return;
  if (l === 'pic' || lay === 'pic') {   // R118 FULL-PIC: the top panel grows over the whole frame, the speakers wait under it
    if (l === 'pic' && lay === 'full') { tl.set('#tp', {height: 1920}, t); tl.fromTo('#tp', {yPercent: -101}, {yPercent: 0, duration: G, ease: E, immediateRender: false}, t); }
    else if (l === 'pic') tl.fromTo('#tp', {height: 960}, {height: 1920, duration: G, ease: E, immediateRender: false}, t);
    else if (l === 'split') { tl.set('.spk', {top: 960, height: 960}, t); tl.fromTo('#tp', {height: 1920, yPercent: 0}, {height: 960, duration: G, ease: E, immediateRender: false}, t); }
    else { tl.set('.spk', {top: 0, height: 1920}, t); tl.fromTo('#tp', {yPercent: 0}, {yPercent: -101, duration: G, ease: E, immediateRender: false}, t); tl.set('#tp', {height: 960}, t + G + .02); }
  } else if (l === 'split') { tl.to('.spk', {top: 960, height: 960, duration: G, ease: E}, t); tl.to('#tp', {yPercent: 0, duration: G, ease: E}, t); }
  else { tl.to('.spk', {top: 0, height: 1920, duration: G, ease: E}, t); tl.to('#tp', {yPercent: -101, duration: G, ease: E}, t); }
  lay = l;
});
// top-panel pictures: each new one fades in ON TOP of the last; the old one goes once it is covered (no fighting fades)
S.ivals.forEach(([id, a, b, pop], k) => {
  const m = document.getElementById('m_' + id);
  tl.set(m, {zIndex: 10 + k}, Math.max(0, a - .001));
  if (a < 0.05) tl.set(m, {opacity: 1, scale: 1}, 0);
  else tl.fromTo(m, {opacity: 0, scale: pop ? .82 : 1.06}, {opacity: 1, scale: 1, duration: pop ? .5 : .35, ease: pop ? 'back.out(1.7)' : 'power2.out', immediateRender: false}, a);
  tl.set(m, {opacity: 0}, b + .8);
});
// slow drift on still pictures; zoom steps on screen crops and saved stills (R26)
S.drift.forEach(([id, a, b]) => tl.fromTo('#m_' + id + ' .z', {scale: 1, xPercent: 0}, {scale: 1.06, xPercent: -1.2, duration: Math.max(.5, b - a), ease: 'none', transformOrigin: '50% 50%', immediateRender: false}, a));
S.cardbg.forEach(([id, a, b, st]) => CB[st](document.querySelector('#m_' + id + ' .hl'), tl, a, b));   // R58
S.crops.forEach(([id, t, sc, x, y]) => {
  const v = document.querySelector('#m_' + id + ' .z');
  if (t === null) tl.set(v, {scale: sc, x: x, y: y}, 0); else tl.to(v, {scale: sc, x: x, y: y, duration: .9, ease: 'power2.inOut'}, t);
});
// opener
const O = S.opener;
if (O.style === 'doac' || O.style === 'seam') {
  if ($('#qbox')) tl.set('#qbox', {opacity: 1}, 0);
  S.listeners.filter(([t]) => t < O.hold).forEach(([t, who]) => document.querySelectorAll('.other').forEach(v => tl.set(v, {opacity: v.dataset.who === who ? 1 : 0}, t)));
  if (document.querySelector('.other')) tl.set('.other', {opacity: 0}, O.hold);
  if ($('#qbox')) { tl.fromTo('#qbox', {scale: .9}, {scale: 1, duration: .35, ease: 'back.out(2)'}, .05);
    tl.to('#qbox', {opacity: 0, duration: .25}, O.hold - .1); }
}
if (O.style === 'texture') { tl.set('#band', {opacity: 1}, 0); tl.fromTo('#band .tx', {y: 24, opacity: 0}, {y: 0, opacity: 1, duration: .35, ease: 'power3.out'}, .05);
  tl.to('#band', {opacity: 0, y: 30, duration: .3, ease: 'power2.in'}, O.hold - .05); }
// captions: the whole phrase at once, the spoken word in its own colour (R47 + R68), one place on screen
const cap = $('#cap'), box = cap.querySelector('span');
S.chunks.forEach((c, ci) => {
  const nx = S.chunks[ci + 1];
  // R86: an end at (next start - 0.02) falls AFTER the next phrase's show (next start - 0.05), so every new phrase is
  // hidden again for its first word: 25-30 blinks per Short. A phrase stays up until the next one replaces it; it only hides across a real pause (> 0.8 s).
  const last = c[c.length - 1][2];
  const end = (nx && nx[0][1] - last < 1.3) ? null : last + 0.6;   // a hide must last 0.6 s+, or it reads as a blink
  c.forEach((w, k) => {
    const on = c.map((x, j) => j === k ? `<b>${x[0]}</b>` : x[0]).join(' ');
    tl.call(() => { box.innerHTML = on; cap.style.visibility = 'visible'; }, null, Math.max(0, (k === 0 ? w[1] - 0.05 : w[1] - 0.02)));
  });
  if (!nx || nx[0][1] - last > 0.15) tl.call(() => { box.innerHTML = c.map(x => x[0]).join(' '); }, null, last + 0.05);   // never after the next phrase shows
  if (end !== null) tl.call(() => { cap.style.visibility = 'hidden'; }, null, end);
});
S.capy.forEach(([t, y]) => tl.set(cap, {top: y + 'px', yPercent: -50}, t));
// title size is set by short.py from the text length (R48)
// end card (R46)
const T0 = S.dur;
tl.set('#end', {opacity: 1}, T0); tl.set(cap, {visibility: 'hidden'}, T0);
tl.fromTo('#end .tex', {opacity: 0}, {opacity: 1, duration: .35, ease: 'power1.out'}, T0);
// R69 + R83 + R96: logo lands at +0.12 s on the click, the marks follow, the pill lands at +0.80 s. The brand's signature only changes how they arrive.
const SIG = S.signature, EN = S.energy;   // motion.energy: how hard things land
const drop = (n, t, fall, from, h) => {
  if (SIG === 'pop') {
    tl.fromTo(n, {scale: .6, opacity: 0}, {scale: 1 + .05 * EN, opacity: 1, duration: fall, ease: 'power3.out'}, t);
    tl.to(n, {scale: 1, duration: .3, ease: 'back.out(3)'}, t + fall);
  } else if (SIG === 'slide') {
    tl.fromTo(n, {x: from}, {x: 0, duration: fall, ease: 'power3.out'}, t);
    tl.to(n, {x: -10 * EN, duration: .06, ease: 'power2.out'}, t + fall);
    tl.to(n, {x: 0, duration: .3, ease: 'back.out(3)'}, t + fall + .06);
  } else {
    tl.fromTo(n, {y: -from}, {y: 0, duration: fall, ease: 'power3.in'}, t);
    tl.to(n, {scaleY: 1 - .1 * EN, scaleX: 1 + .035 * EN, duration: .06, ease: 'power2.out', transformOrigin: `50% ${h}px`}, t + fall);
    tl.to(n, {scaleY: 1, scaleX: 1, duration: .38, ease: 'back.out(3)'}, t + fall + .06);
  }
};
drop('#hLogo', T0, .12, 900, S.logo_h);   // the whole logo lands on the click at +0.12 s
if (SIG === 'stack') tl.fromTo('#layer', {x: 0, y: 0, opacity: 0}, {x: 18, y: 18, opacity: 1, duration: .4, ease: 'power3.out'}, T0 + .28);
for (let k = 0; k < S.nmarks; k++) { tl.fromTo('#i' + k, {opacity: 0}, {opacity: 1, duration: .08}, T0 + .4 + k * .08); drop('#i' + k, T0 + .4 + k * .08, .13, 60, 64); }
const ctaFrom = SIG === 'pop' ? {opacity: 0, scale: .7} : SIG === 'slide' ? {opacity: 0, x: 120} : {opacity: 0, y: -60};
tl.fromTo('#ctaInner', ctaFrom, {opacity: 1, y: 0, x: 0, scale: 1, duration: .16, ease: SIG === 'stack' ? 'power3.in' : 'power3.out'}, T0 + .64);
if (SIG === 'stack') {
  tl.to('#ctaBox', {scaleY: 1 - .1 * EN, scaleX: 1 + .03 * EN, duration: .06, ease: 'power2.out', transformOrigin: '50% 100%'}, T0 + .8);
  tl.to('#ctaBox', {scaleY: 1, scaleX: 1, duration: .38, ease: 'back.out(3)'}, T0 + .86);
  tl.fromTo('#ctaLayer', {x: 0, y: 0}, {x: 12, y: 12, duration: .36, ease: 'power3.out'}, T0 + .86);
} else {
  tl.set('#ctaLayer', {x: 12, y: 12}, T0 + .64);   // the pill keeps its accent edge in every signature, as the preview shows (paper on a light ground would vanish)
  tl.to('#ctaBox', {scale: 1.04, duration: .06, ease: 'power2.out', yoyo: true, repeat: 1}, T0 + .8);
}
tl.set({}, {}, T0 + S.endlen);
'''


def marks():
    """R83: the platform marks under the logo, from brand/marks/<name>.svg, in the order end_card.platforms lists them. A missing one is skipped."""
    import re
    out = []
    for n in BRAND['end_card'].get('platforms', []):
        p = brand.ROOT / 'brand' / 'marks' / f'{n}.svg'
        if not p.exists(): print(f'no platform mark brand/marks/{n}.svg, skipped'); continue
        out.append(re.sub(r'<title>.*?</title>', '', p.read_text()).replace('<svg ', '<svg fill="currentColor" ', 1))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('clip'); ap.add_argument('spec'); ap.add_argument('out'); ap.add_argument('--music')
    ap.add_argument('--bed', type=float, default=-21); ap.add_argument('--workers', default='6')
    ap.add_argument('--sfx-only', action='store_true', help='only (re)write <out>_sfxstem.wav from the spec; no render (SFX for Shorts already rendered)')
    a = ap.parse_args()
    brand.require_locked()
    D = os.path.abspath(a.clip); S = json.load(open(a.spec)); out = os.path.abspath(a.out)
    W = os.path.splitext(out)[0] + '_hf'; os.makedirs(os.path.join(W, 'fonts'), exist_ok=True); os.makedirs(os.path.join(W, 'media'), exist_ok=True)
    words = json.load(open(os.path.join(D, 'words.json'))); dur = float(json.load(open(os.path.join(D, 'segs.json')))['duration'])
    # times may be given as an episode word ("w": source word number): the edit survives a re-cut of the clip
    by_src = {}
    for w in words:
        if not w.get('added') and w.get('src') not in by_src: by_src[w.get('src')] = w
    def T(x):
        if isinstance(x, (int, float)): return float(x)
        w = by_src[x['w']]; return round(max(0.0, (w['end'] if x.get('at') == 'end' else w['start']) + x.get('d', -0.08)), 3)
    S['segments'] = [[T(t)] + rest for t, *rest in S['segments']]
    for m in S['media'].values():
        if 'zoom' in m: m['zoom'] = [[T(t), b] for t, b in m['zoom']]
    if isinstance(S['opener'].get('hold'), dict): S['opener']['hold'] = T(S['opener']['hold'])
    if S.get('end'):   # R87: never cut someone off as they start a sentence: stop on a finished line
        dur = min(dur, T(S['end'])); words = [w for w in words if w['start'] < dur - 0.05]
    E = json.load(open(os.path.join(D, 'edit.json'))) if os.path.exists(os.path.join(D, 'edit.json')) else {}; faces = E.get('faces', {})
    for f in ('gsap.min.js', 'hyperframes.json'): shutil.copy(os.path.join(ML, f), W)
    shutil.copy(brand.CSS, W)   # brand.css loads fonts/ next to it
    for f in brand.FONTS.iterdir(): shutil.copy(f, os.path.join(W, 'fonts'))
    for f in ('band.png', 'tall_a.png', 'card.png'): shutil.copy(brand.TEX / f, W)   # card.png: R75 textured edge
    for k in range(4): shutil.copy(brand.TEX / 'grain' / f'grain_{k}.png', W)
    shutil.copy(brand.LOGO, os.path.join(W, 'logo.png'))
    json.dump(dict(name='short', private=True, type='module'), open(os.path.join(W, 'package.json'), 'w'))
    json.dump(dict(id='short', name='short'), open(os.path.join(W, 'meta.json'), 'w'))
    # speakers: panels from the clip tracks (already lip-synced by cut.py)
    body = ''
    hosts = [w for w in IDS if os.path.exists(os.path.join(D, f'{w}.mp4'))]   # 1, 2 or 3 people; a solo recording has one speaker
    for k, who in enumerate(hosts):
        dst = os.path.join(W, 'media', f'{who}.mp4')
        if not os.path.exists(dst): panel(os.path.join(D, f'{who}.mp4'), dst, (faces.get(who, [50])[0]) / 100)
        body += f'<video id="spk_{who}" class="spk" data-who="{who}" src="media/{who}.mp4" data-start="0" data-duration="{dur}" data-track-index="{k}" muted playsinline></video>\n'
    # timeline: events (t, layout, media) -> layout changes + picture intervals (overlapping fades fight each other, one card
    # covers another; so each new picture fades in ON TOP of the last, the old one is removed after)
    segs = S['segments']; op = S['opener']; hl_ids = []
    ev = [[t, l] + rest for t, l, *rest in segs]
    if op['style'] == 'texture' and op.get('top'): ev.append([op['hold'], 'split', op['top']])
    if op['style'] == 'headline': ev.append([0.0, 'split', op['media']])
    if op['style'] in ('doac', 'seam') and op.get('top'): ev.append([0.0, 'split', op['top']])
    ev.sort(key=lambda x: x[0])
    lay0 = 'split' if op['style'] in ('doac', 'seam', 'headline') else 'full'
    if op['style'] in ('doac', 'seam') and not any(abs(e[0] - op['hold']) < 0.05 for e in ev) and not op.get('top'):
        ev.append([op['hold'], 'full']); ev.sort(key=lambda x: x[0])
    lays, ivals, cur, lay = [], [], None, lay0
    for t, l, *r in ev:
        if l != lay: lays.append([t, l]); lay = l
        mid = r[0] if (l in ('split', 'pic') and r) else None   # R118 'pic' = FULL-PIC: the top panel covers the frame
        if mid != cur:
            if cur is not None: ivals[-1][2] = t
            if mid is not None: ivals.append([mid, t, dur, bool(S['media'][mid].get('pop'))])
            cur = mid
    starts = {}
    for mid, a_, b_, _ in ivals: starts.setdefault(mid, []).append(a_)
    tp = ''; crops = []; drift = []
    def fitbox(b, w=None, h=None):   # scale + offset so crop box b (source px) fits the 1080x960 panel, centred
        x0, y0, x1, y1 = b; sc = min(1080 / (x1 - x0), 960 / (y1 - y0))
        return [round(sc, 4), round(-x0 * sc + (1080 - (x1 - x0) * sc) / 2, 1), round(-y0 * sc + (960 - (y1 - y0) * sc) / 2, 1)]
    HAS_PIC = any(l == 'pic' for t, l, *r in ev)   # FULL-PIC media are 1080x1920 ("tall"); the others keep 960 while the panel grows
    for k, (mid, m) in enumerate(S['media'].items()):
        if mid not in starts: continue
        first = min(starts[mid]); bg = m.get('bg', 'var(--ground)')
        if HAS_PIC: bg += ';height:1920px;bottom:auto' if m.get('tall') else ';height:960px;bottom:auto'
        if m['kind'] == 'video':   # a keyframe every second, or HyperFrames seeks badly and freezes the clip
            # R78: the clip holds its last frame to the end of the Short (a graphic never leaves an empty panel)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(D, m['file']), '-an', '-vf', f'tpad=stop_mode=clone:stop_duration={dur:.2f}',
                            '-t', f'{dur - first + 0.5:.2f}', '-c:v', 'libx264', '-crf', '16', '-r', '30', '-g', '30',
                            '-keyint_min', '30', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', os.path.join(W, 'media', m['file'])], check=True)
            tp += (f'<div class="m" id="m_{mid}" style="background:{bg}"><video id="v_{mid}" class="z" src="media/{m["file"]}" style="object-fit:{m.get("fit", "cover")}" '
                   f'data-start="{first:.3f}" data-duration="{dur - first:.3f}" data-track-index="{10 + k}" muted playsinline></video></div>\n')
        elif m['kind'] == 'duo':   # R79: the listener's own panel (same lip-synced file as the speaker panels)
            for who in hosts: listener_track(W, who, words, dur)
            vids = ''.join(f'<video id="v_duo_{who}" class="oth" data-who="{who}" src="media/oth_{who}.mp4" data-start="0" data-duration="{dur}" '
                           f'data-track-index="{20 + j}" muted playsinline></video>' for j, who in enumerate(hosts))
            tp += f'<div class="m" id="m_{mid}" style="background:var(--ground)">{vids}</div>\n'
        elif m['kind'] == 'image':
            shutil.copy(os.path.join(D, m['file']), os.path.join(W, 'media', m['file']))
            tp += f'<div class="m" id="m_{mid}" style="background:{bg}"><img class="z" src="media/{m["file"]}" style="object-fit:{m.get("fit", "cover")}"></div>\n'
            for iv in ivals:
                if iv[0] == mid and not m.get('pop'): drift.append([mid, iv[1], iv[2]])
        elif m['kind'] in ('screen', 'still'):
            if m['kind'] == 'screen':
                src = os.path.join(W, 'media', 'screen.mp4')
                if not os.path.exists(src): shutil.copy(os.path.join(D, 'screen.mp4'), src)
                el = f'<video id="v_{mid}" class="z" src="media/screen.mp4" data-start="0" data-duration="{dur}" data-track-index="{10 + k}" muted playsinline></video>'
            else:   # a clean saved image, zoomed like a screen crop
                shutil.copy(os.path.join(D, m['file']), os.path.join(W, 'media', m['file']))
                el = f'<img class="z" src="media/{m["file"]}">'
            tp += f'<div class="m scr" id="m_{mid}" style="background:{m.get("bg", "var(--paper)")}">{el}</div>\n'
            crops.append([mid, None] + fitbox(m['crop']))
            for t, bx in m.get('zoom', []): crops.append([mid, t] + fitbox(bx))
        elif m['kind'] == 'headline':
            import re as _re   # {logo:name} in a card puts the real mark inline: say the name, show the name
            def _lg(mo):
                got = logos.fetch(mo.group(1), D)
                if not got: return ''
                shutil.copy(got, os.path.join(W, 'media', 'lg_' + mo.group(1) + '.svg'))
                return f'<img class="il" src="media/lg_{mo.group(1)}.svg">'
            txt = _re.sub(r'\{logo:([a-z0-9-]+)\}', _lg, m['text'])
            tp += (f'<div class="m" id="m_{mid}"><div class="hl">{cardbg.layers("")}<div class="card"><div class="src"><b>{m["outlet"]}</b><span>{m["date"]}</span></div>'
                   f'<div class="t">{txt}</div></div></div></div>\n')
            hl_ids.append(mid)
    body += f'<div id="tp">{tp}</div>\n'
    if op['style'] in ('seam', 'doac') and not op.get('top'):
        for k, who in enumerate(hosts):   # the listener sits on top; it swaps if the speaker changes inside the opener
            body += f'<video id="other_{who}" class="other" data-who="{who}" src="media/{who}.mp4" data-start="0" data-duration="{op["hold"]}" data-track-index="{5 + k}" muted playsinline></video>\n'
    TITLE_W = 760 if S.get('safe_right') else 840   # R110 safe_right: the title stays left of x=940
    QSTY = ' style="width:840px"' if S.get('safe_right') else ''   # R113 safe_right: the title card fits x 120..960
    if op.get('title_y'):   # opt-in: a 3-line title card centred higher, so its last line stays off the head (R23b/R60)
        QSTY = f' style="{"width:840px;" if S.get("safe_right") else ""}top:{int(op["title_y"])}px"'
    if op['style'] == 'seam' and op.get('title'):
        body += f'<div id="qbox" class="seam"{QSTY}><div class="tx" style="font-size:{title_px(op["title"], TITLE_W)}px">{op["title"]}</div></div>\n'
    if op['style'] == 'doac':
        body += f'<div id="qbox" style="font-size:{title_px(op["question"], 950, 76, "heavy")}px">{op["question"]}</div>\n'
    if op['style'] == 'texture':
        body += f'<div id="band"><div class="tx" style="font-size:{title_px(op["title"], 960)}px">{op["title"]}</div></div>\n'
    mk = marks(); lw, lh, lx, ly = logo_box(); box = f'left:{lx}px;top:{ly}px;width:{lw}px;height:{lh}px'
    icons = ''.join(f'<i class="ic" id="i{k}" style="left:{540 - (len(mk) * 144 - 80) // 2 + k * 144}px">{m}</i>' for k, m in enumerate(mk))   # 64 px marks, 80 px apart, centred
    cta = BRAND['end_card']['cta']
    body += (f'<div id="end"><img class="tex" src="tall_a.png"><div id="layer" style="{box}"></div>'
             f'<div id="hLogo" style="{box}"><img src="logo.png"></div>'
             f'{icons}<div id="ctaWrap"><div id="ctaInner"><div id="ctaLayer"></div><div id="ctaBox" style="font-size:{fit_px(cta, 720, 48, track=.08)}px">{cta}</div></div></div></div>\n')
    body += '<div id="cap"><span></span></div>\n'
    # captions: in a split they sit just ABOVE the middle line, never on the head below it
    SPLIT_Y, FULL_Y, PIC_Y = S.get('cap_split_y', 960), S.get('cap_full_y', 1330), S.get('cap_pic_y', 1640)   # cap_split_y: lift the line off a tall head (R23b); cap_full_y (opt-in): drop the full-screen line below a low chin
    if len(hosts) == 1:
        FULL_Y = 1720   # R85: a solo face cam fills the frame in full layout; the caption goes under the chin, never on the mouth
    cap_y, l = [[0.0, SPLIT_Y if lay0 == 'split' else FULL_Y]], lay0
    for t, l2 in lays: cap_y.append([t, SPLIT_Y if l2 == 'split' else PIC_Y if l2 == 'pic' else FULL_Y])
    if op['style'] in ('doac', 'seam') and (op.get('title') or op.get('question')):   # opener: the title card owns the middle line; caption under the speaker's chin
        cap_y = [[0.0, 1800], [op['hold'], SPLIT_Y if (not lays or lays[0][0] > op['hold'] + 0.01 or lays[0][1] == 'split') else FULL_Y]] + [c for c in cap_y if c[0] > op['hold'] + 0.01]
    if op['style'] == 'texture': cap_y = [[0.0, 1385]] + [c for c in cap_y if c[0] >= op['hold']]
    # R86 + R23: during a layout glide (G = 0.75 s) the caption parks on the low line, under every chin in
    # split and full (measured: lowest chin 1713 px), then moves to its new line when the glide lands. Hiding it for the glide
    # would blank the caption mid-phrase at every layout change (6-17 blinks a Short).
    G, PARK = 0.75, S.get('cap_glide_y', 1800)
    glides = [t for t, _ in lays]
    for c in cap_y:
        for g in glides:
            if g - 0.05 <= c[0] < g + G: c[0] = round(g + G, 3)
    cap_y = sorted(cap_y + [[round(max(0.0, g - 0.04), 3), PARK] for g in glides], key=lambda c: c[0])
    W8 = [[w['text'], round(w['start'], 3), round(w['end'], 3), w['spk']] for w in words if w['text'].strip()]
    shows = []
    for mid, a_, b_, _ in ivals:
        if mid in hl_ids:
            style = S['media'][mid].get('bg') or cardbg.STYLES[len(shows) % len(cardbg.STYLES)]
            shows.append([mid, a_, b_, style])
    segs_js = ev
    ENG = engagement(W, IDS); TURNS = turns(words, dur, S.get('min_turn', 1.2), ENG)
    # R76 in any font: if one single word is wider than the line, the whole Short's caption size comes down until it fits
    global CAP_PX
    maxw = 720 if S.get('safe_right') else CAP_MAX_W   # R110 safe_right: a centred line ends left of x=940
    widest = max([cap_w(w[0]) for w in W8] or [0])
    if widest > maxw: CAP_PX = int(CAP_PX * maxw / widest); print(f'caption size {CAP_PX}px: the longest word is wider than one line at 56px')
    spec = dict(dur=dur, endlen=END, cardbg=shows, turns=TURNS, listeners=listeners(TURNS, hosts), lay0=lay0, lays=lays, ivals=ivals, crops=crops, drift=drift,
                opener=op, chunks=chunks(W8, maxw=maxw), capy=cap_y, signature=BRAND.get('motion', {}).get('signature', 'stack'), energy={'low': .6, 'high': 1.4}.get(BRAND.get('motion', {}).get('energy'), 1), logo_h=lh, nmarks=len(mk))
    page_css = brand.GRAIN_CSS + CSS.replace('__CARDBG_CSS__', cardbg.CSS).replace('__CAP_PX__', str(CAP_PX))
    if BRAND['title'].get('highlight', 'block') != 'block': page_css += '\nmark { background: none !important; color: var(--accent) !important; padding: 0 !important; }'
    html = (f'<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="brand.css"><script src="gsap.min.js"></script><style>{page_css}</style></head><body>'
            f'<div id="root" data-composition-id="main" data-start="0" data-duration="{dur + END}" data-fps="30" data-width="1080" data-height="1920">{body}</div>'
            f'<script>{cardbg.JS}{JS.replace("__SPEC__", json.dumps(spec))}</script></body></html>')
    open(os.path.join(W, 'index.html'), 'w').write(html)
    def write_stem():
        total = dur + END
        ev_sfx = [(t, 'whoosh_lo' if os.path.exists(os.path.join(KIT, 'whoosh_lo.wav')) else 'whoosh', -6) for t, l, *r in segs_js if t > 0.2]   # sound kit files are -20 LUFS events: -6 sits ~16 dB under the voice, heard but gentle
        for anc, name, g in S.get('sfx', []): ev_sfx.append((anc if isinstance(anc, (int, float)) else T(anc), name, g))
        ev_sfx = [(t, nm, g) for t, nm, g in ev_sfx if 0 <= t < total and os.path.exists(os.path.join(KIT, nm + '.wav'))]
        stem = out[:-4] + '_sfxstem.wav'
        if ev_sfx:
            sins, sfc = [], []
            for k, (t, nm, g) in enumerate(ev_sfx):
                sins += ['-i', os.path.join(KIT, nm + '.wav')]; sfc.append(f'[{k}:a]aformat=sample_rates=48000:channel_layouts=mono,volume={g}dB,adelay={int(t * 1000)}:all=1[e{k}]')
            sfc = ';'.join(sfc) + ';' + ''.join(f'[e{k}]' for k in range(len(ev_sfx))) + f'amix=inputs={len(ev_sfx)}:normalize=0,apad=whole_dur={total},atrim=0:{total}[s]'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', *sins, '-filter_complex', sfc, '-map', '[s]', '-ar', '48000', '-ac', '1', stem], check=True)
            print(f'sfx stem -> {stem} ({len(ev_sfx)} effects)')
    if a.sfx_only: write_stem(); return
    pic = os.path.join(W, 'picture.mp4')
    env = dict(os.environ, HYPERFRAMES_NO_TELEMETRY='1', HYPERFRAMES_SKIP_SKILLS='1')
    r = subprocess.run(['npx', '--yes', HF, 'render', '--quality', 'looks', '-w', a.workers, '--output', pic], cwd=W, env=env,
                       stdin=subprocess.DEVNULL, capture_output=True, text=True)
    open(os.path.join(W, 'render.log'), 'w').write(r.stdout + r.stderr)
    subprocess.run("ps -axo pid=,ppid=,command= | awk '$2==1 && /chrome-headless-shell/ {print $1}' | xargs kill 2>/dev/null", shell=True)
    if not os.path.exists(pic): sys.exit(f'render failed, see {W}/render.log')
    # sound: voice (cleaned) + optional music bed and gentle effects with a visible cause (R17)
    voice = clean_voice(D); total = dur + END
    ins = ['-i', pic, '-i', voice]; fc = f'[1:a]atrim=0:{dur:.3f},afade=t=out:st={max(0, dur - 0.12):.3f}:d=0.12,apad=whole_dur={total}[v]'; mix = '[v]'; n = 1
    if a.music:
        ins += ['-stream_loop', '-1', '-i', a.music]; n += 1
        fc += (f';[{n}:a]atrim=0:{total},volume={a.bed}dB,afade=t=in:d=0.6,afade=t=out:st={total - 1.2}:d=1.2[m0];'
               f'[v]asplit[v][vk];[m0][vk]sidechaincompress=threshold=0.08:ratio=2:attack=40:release=700:makeup=1[mb]')
        sfx = []
        for t, l, *r in segs_js:
            if t > 0.2: sfx.append((t, 'whoosh_lo' if os.path.exists(os.path.join(KIT, 'whoosh_lo.wav')) else 'whoosh', -22))
        if op['style'] == 'texture': sfx.append((0.05, 'pop', -24))
        labs = ['[v]', '[mb]']
        for k, (t, name, g) in enumerate(sfx):
            p = os.path.join(KIT, name + '.wav')
            if not os.path.exists(p): continue
            n += 1; ins += ['-i', p]; fc += f';[{n}:a]volume={g}dB,adelay={int(t * 1000)}:all=1[s{k}]'; labs.append(f'[s{k}]')
        fc += f';{"".join(labs)}amix=inputs={len(labs)}:normalize=0[mx]'; mix = '[mx]'
    click = str(brand.ROOT / BRAND['end_card'].get('click', 'brand/sfx/end_click.wav'))   # R96: one click on the logo at +0.12 s, a light key on the button at +0.80 s
    if os.path.exists(click):   # R69: the end-card logo lands with a click, in every version. Lined up by the file's own lead-in, so any click file lands on time
        n += 1; ins += ['-i', click]; fc += f';[{n}:a]adelay={int(max(0, dur + 0.12 - onset(click)) * 1000)}:all=1[clk];{mix}[clk]amix=inputs=2:normalize=0[mc]'; mix = '[mc]'
    fc += f';{mix}loudnorm=I=-14:TP=-1.5:LRA=11[a]'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-t', f'{total:.3f}',
                    '-c:v', 'libx264', '-crf', '19', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', out], check=True)
    # SFX stem (for the on/off switch in the review app): the final stays clean; every effect goes into
    # <out>_sfxstem.wav (same length) and music_mix.py --sfx lays it beside the voice. Events: a soft whoosh on each layout
    # change, plus the spec's own "sfx": [[anchor, name, gain_dB], ...] (anchor = seconds or a word anchor like segments use).
    write_stem()
    T = TURNS
    if not verify_sync(out, W, D, T, segs_js, dur, os.path.join(D, 'voice.wav')): print('SYNC FAIL: do not ship', out)
    print('short ->', out)


if __name__ == '__main__':
    main()

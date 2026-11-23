#!/usr/bin/env python3
"""beatsheet.py <id>: motion/beats/<id>.md from the beats json + the run scripts. Each beat = the comment above it in the
run JS (what is said -> what is shown), and every cue it uses: word, source index, time on the Short's clock."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from build import load, run_windows, M
id_ = sys.argv[1]
B, D, words, by_src, dur, T = load(id_)
segs, win = run_windows(B, T, dur)
by_i = {w['i']: w for w in words}
out = [f"# {id_}: beat sheet", "", f"Clip `{B['clip']}`, {dur:.2f} s. Spec `episodes/{B['out']}/{B['name']}.json`. "
       f"Opener: {B['opener'].get('title', '').replace('<br>', ' ').replace('<mark>', '').replace('</mark>', '') or '(no title card, the top graphic is the hook)'}.", "",
       "## Segments", "", "| from (s) | layout | graphic |", "|---|---|---|"]
for s in segs: out.append(f"| {s[0]:.2f} | {s[1]} | {s[2] if len(s) > 2 else 'speaker full screen (opinion)'} |")
for run, (t0, t1) in win.items():
    out += ["", f"## {run}: {t0:.2f} to {t1:.2f} s", "", "| beat (said -> shown) | lands on | word time (s) |", "|---|---|---|"]
    js = open(os.path.join(M, 'comps', id_, B['runs'][run]['js'])).read().split('\n')
    cur = None
    for ln in js:
        m = re.match(r'\s*//\s?(.*)', ln)
        if m:
            txt = m.group(1).strip()
            if cur is not None and cur.get('cues') == [] and not txt.startswith(id_): cur['txt'] += ' ' + txt; continue
            cur = dict(txt=txt, cues=[]); out_rows = cur; continue
        if cur is None: continue
        for kind, n in re.findall(r'\b(c|ci)\((\d+)\)', ln):
            w = by_src.get(int(n)) if kind == 'c' else by_i.get(int(n))
            if w and (w['text'], w['start']) not in [(a, b) for a, b, _ in cur['cues']]: cur['cues'].append((w['text'], w['start'], f"{kind}({n})"))
        if cur['cues'] and not cur.get('done'):
            pass
    # second pass: emit rows in order
    cur = None; rows = []
    for ln in js:
        m = re.match(r'\s*//\s?(.*)', ln)
        if m:
            if cur and cur['cues']: rows.append(cur)
            if cur and not cur['cues']: cur['txt'] += ' ' + m.group(1).strip(); continue
            cur = dict(txt=m.group(1).strip(), cues=[]); continue
        if cur is None: continue
        for kind, n in re.findall(r'\b(c|ci)\((\d+)\)', ln):
            w = by_src.get(int(n)) if kind == 'c' else by_i.get(int(n))
            if w and all(w['start'] != x[1] for x in cur['cues']): cur['cues'].append((w['text'], w['start'], f"{kind}({n})"))
    if cur and cur['cues']: rows.append(cur)
    for r in rows:
        cues = sorted(r['cues'], key=lambda x: x[1])
        out.append(f"| {r['txt'].replace('|', '/')} | {', '.join(f'\"{a}\" {k}' for a, _, k in cues)} | {', '.join(f'{b:.2f}' for _, b, _ in cues)} |")
open(os.path.join(M, 'beats', id_ + '.md'), 'w').write('\n'.join(out) + '\n'); print('wrote', id_)

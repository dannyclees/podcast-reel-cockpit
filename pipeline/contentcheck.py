#!/usr/bin/env python3
"""contentcheck.py <episode> <short id> <spec.json>: the content gate. Exit 1 on FAIL. publish.py runs it before it uploads.

R120 start and end: the Short starts and ends on a whole thought.
R121 title: 2 lines at most, on the seam card, never the low texture band.
R122 sources: at least 2 first-hand items on screen, or a written reason why none exist.
Code cannot judge sense by itself, so it also prints the opening and the ending: read them before publish.
Spec keys: "sources": [{"media": "<key in spec media>", "url": "https://...", "what": "..."}], "sources_none": "reason",
"content_ok": "reason" (a person read the FAILs and overrides them; the reason is printed on every run).
Use --all <episode> to check the start and end of every clip of an episode.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand

ROOT = str(brand.ROOT)
DANGLE = set('a an the and but or so because which who if than to of for with at in on by from as is are was were my our your their his her i we they he she'.split())
BAD_START = set('and but because which or so also then though although however'.split())
BACK_REF = set('it that this they them he she those these there yeah yes no right exactly well okay'.split())
PAUSE = 0.45   # s: a gap this long reads as a break even with no full stop


def clean(t): return re.sub(r"[^\w'-]", '', t).lower()
def stops(t): return bool(re.search(r'[.?!]["\')]*$', t.strip()))
def sentences(ws):
    out, cur = [], []
    for w in ws:
        cur.append(w['text'])
        if stops(w['text']): out.append(' '.join(cur)); cur = []
    if cur: out.append(' '.join(cur))
    return out


def clip_dir(ep, sid):
    base = os.path.join(ROOT, 'episodes', ep, 'clips')
    for c in sorted(os.listdir(base)):
        if sid in c.split('-'): return os.path.join(base, c)
    sys.exit(f'{ep}/{sid}: no clip folder')


def check(ep, sid, spec=None):
    D = clip_dir(ep, sid)
    W = [w for w in json.load(open(os.path.join(D, 'words.json'))) if w['text'].strip()]
    S = json.load(open(spec)) if spec else {}
    if isinstance(S.get('end'), dict):   # same anchor as short.py: word number + at + d
        e = S['end']; w = W[e['w']] if e['w'] < len(W) else W[-1]; end = w[e.get('at', 'end')] + e.get('d', 0)
        W = [w for w in W if w['start'] < end - 0.05]
    elif S.get('end'): W = [w for w in W if w['start'] < float(S['end']) - 0.05]
    p = os.path.join(ROOT, 'episodes', ep, 'work', 'words.json')
    EP = json.load(open(p)) if os.path.exists(p) else []
    bad = []
    first, last = W[0], W[-1]
    # END
    lw = clean(last['text'])
    if not stops(last['text']): bad.append(f'END no full stop on the last word: "{last["text"]}"')
    if lw in DANGLE: bad.append(f'END the last word leaves the line hanging: "{last["text"]}"')
    sn = sentences(W)
    if len(sn[-1].split()) < 4: bad.append(f'END the last line is a scrap: "{sn[-1]}"')
    after = ''
    if last.get('src') is not None and EP:
        nx = [w for w in EP if w['i'] > last['src'] and w['text'].strip()][:14]
        after = ' '.join(w['text'] for w in nx)
        ln = EP[last['src']] if last['src'] < len(EP) else None
        if nx and ln and nx[0]['spk'] == last['spk'] and nx[0]['start'] - ln['end'] < PAUSE and nx[0]['text'][:1].islower():
            bad.append(f'END the speaker goes straight on: "{last["text"]} | {after[:50]}"')
        if nx and ln and nx[0]['spk'] == last['spk'] and nx[0]['start'] - ln['end'] < 0.25 and nx[0]['text'][:1].isupper():
            bad.append(f'END the speaker starts the next line {nx[0]["start"] - ln["end"]:.2f} s later: "{last["text"]} | {after[:50]}"')
        sg = json.load(open(os.path.join(D, 'segs.json')))['segs']
        if nx and not S.get('end') and sg[-1][1] > nx[0]['start'] + 0.04:
            bad.append(f'END the audio runs {sg[-1][1] - nx[0]["start"]:.2f} s into the next word: "{nx[0]["text"]}"')
    # START
    fw = clean(first['text'])
    if fw in BAD_START: bad.append(f'START opens on a joining word: "{first["text"]}"')
    if not first['text'][:1].isupper() and not first['text'][:1].isdigit(): bad.append(f'START opens mid sentence: "{first["text"]}"')
    warn = [f'START opens on "{first["text"]}": does a stranger know what it means?'] if fw in BACK_REF else []
    if first.get('src') and EP:
        pv = [w for w in EP if w['i'] < first['src'] and w['text'].strip()][-1:]
        fe = EP[first['src']] if first['src'] < len(EP) else None
        if pv and fe and pv[0]['spk'] == first['spk'] and not stops(pv[0]['text']) and fe['start'] - pv[0]['end'] < PAUSE:
            warn.append(f'START follows on from "{pv[0]["text"]}": does it stand alone?')
    # R121 TITLE
    op = S.get('opener') or {}
    if op:
        t = op.get('title') or op.get('question') or ''
        if t.count('<br') > 1: bad.append(f'TITLE has {t.count("<br") + 1} lines, the limit is 2: "{re.sub("<[^>]+>", " ", t)}"')
        if op.get('style') == 'texture': bad.append('TITLE sits in the low texture band (y 1450): use the seam card')
        if op.get('title_y') and not 820 <= op['title_y'] <= 960: bad.append(f'TITLE y {op["title_y"]} is out of 820 to 960')
        if op.get('title') and op.get('style') == 'seam':   # R88: measured in the brand's real font
            import short
            if short.title_px(op['title'], 760 if S.get('safe_right') else 840) < 60: warn.append('TITLE under 60 px in this font: cut words (R88, R121)')
    # R122 SOURCES
    if spec:
        src = [x for x in S.get('sources', []) if x.get('url', '').startswith('http') and x.get('media') in S.get('media', {})]
        if len(src) < 2 and not S.get('sources_none'):
            bad.append(f'SOURCES {len(src)} first-hand items on screen, the minimum is 2 (or write sources_none)')
        if S.get('sources_none'): warn.append(f'SOURCES none: {S["sources_none"]}')
    if bad and S.get('content_ok'):
        warn += [f'OVERRIDDEN {b}' for b in bad] + [f'REASON {S["content_ok"]}']; bad = []
    print(f'{ep}/{sid}: {"FAIL" if bad else "PASS"}  {len(W)} words')
    for b in bad: print('   FAIL', b)
    for x in warn: print('   READ', x)
    print('   opens:', ' / '.join(sentences(W)[:2])[:170])
    print('   ends :', ' / '.join(sn[-2:])[-170:])
    if after: print('   next :', after[:110])
    return not bad


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == '--all':
        ep = a[1]; cs = json.load(open(os.path.join(ROOT, 'episodes', ep, 'clips.json')))
        ids = [re.split('-', c['id'])[1] if re.match(r'c\d-', c['id']) else c['id'].split('-')[0] for c in cs['clips']]
        sys.exit(0 if all([check(ep, i) for i in ids]) else 1)
    sys.exit(0 if check(a[0], a[1], a[2] if len(a) > 2 else None) else 1)

#!/usr/bin/env python3
"""sents.py <clip dir> [end_src]: the clip's words grouped into sentences: [src of first word] start-end speaker: text"""
import json, sys, re
w = json.load(open(sys.argv[1] + '/words.json')); end = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
cur = []
def flush():
    if cur: print(f"[{cur[0]['src']:5d}] {cur[0]['start']:6.2f}-{cur[-1]['end']:6.2f} {cur[0]['spk'][:4]}: " + ' '.join(f"{x['text']}" for x in cur))
for x in w:
    if x['src'] > end: break
    if cur and (x['spk'] != cur[-1]['spk'] or x['start'] - cur[-1]['end'] > 0.35 or len(cur) >= 14): flush(); cur = []
    cur.append(x)
    if re.search(r'[.?!]$', x['text']): flush(); cur = []
flush()

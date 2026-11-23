#!/usr/bin/env python3
"""show.py <words.json> <a> <b>: print words a to b with their numbers, speakers and times, to pick exact clip ranges."""
import json, sys

words, a, b = json.load(open(sys.argv[1])), int(sys.argv[2]), int(sys.argv[3])
spk = None
for w in words:
    if not a <= w['i'] <= b: continue
    if w.get('spk') != spk:
        spk = w.get('spk'); print(f"\n[{spk}]", end=' ')
    print(f"#{w['i']}@{w['start']:.2f} {w['text']}", end=' ')
print()

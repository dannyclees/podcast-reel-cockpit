#!/usr/bin/env python3
"""retext.py <clip dir>: every spoken word gets a caption (R20, R47). Run with the aligner venv:
    bin/.venv-align/bin/python pipeline/retext.py <clip dir>

Why: the episode transcript (whisper small, 5 min pieces) drops words, so captions skip words. This re-transcribes the clip's own sound with whisper large-v3-turbo, gives each word the
speaker whose mic is louder, carries the episode word number ("src") over from the old words where the text matches
(so edit specs keep pointing at the same words), then forced-aligns the result (align_words.clip).
Old words kept as words.episode.json.
"""
import difflib, json, os, re, shutil, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import align_words, brand

MODEL = str(brand.WHISPER / 'ggml-large-v3-turbo.bin')


def norm(t): return re.sub(r"[^a-z0-9']", '', t.lower())


def env(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32); n = len(x) // 800
    e = 20 * np.log10(np.sqrt((x[:n * 800].reshape(n, 800) ** 2).mean(1)) + 1e-6)
    return e - np.percentile(e, 15)


def main(D):
    old_p = os.path.join(D, 'words.episode.json')
    if not os.path.exists(old_p): shutil.copy(os.path.join(D, 'words.json'), old_p)
    old = json.load(open(old_p))
    tmp = tempfile.mkdtemp(); wav = os.path.join(tmp, 'a.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(D, 'voice.wav'), '-ac', '1', '-ar', '16000', wav], check=True)
    subprocess.run(['whisper-cli', '-m', MODEL, '-f', wav, '-ml', '1', '-sow', '-oj', '-of', os.path.join(tmp, 'o'), '-np'], check=True, capture_output=True)
    segs = json.load(open(os.path.join(tmp, 'o.json')))['transcription']
    new = []
    for s in segs:
        t = s['text'].strip()
        if not t or t.startswith('['): continue
        a, b = s['offsets']['from'] / 1000, s['offsets']['to'] / 1000
        if new and not s['text'].startswith(' ') and not re.match(r'^\w', t[:1] or ''): new[-1]['text'] += t; continue   # glued punctuation
        new.append(dict(text=t, start=a, end=max(b, a + 0.05)))
    spk = {p: env(os.path.join(D, f'mic_{p}.wav')) for p in brand.IDS if os.path.exists(os.path.join(D, f'mic_{p}.wav'))}
    solo = old[0]['spk'] if old else brand.IDS[0]
    for w in new:
        a, b = int(w['start'] / 0.05), max(int(w['start'] / 0.05) + 1, int(w['end'] / 0.05))
        w['spk'] = max(spk, key=lambda p: float(np.mean(spk[p][a:b])) if len(spk[p][a:b]) else -99) if spk else solo   # solo recording: one voice
    # carry src across: matched words take the old word's src; unmatched ones take the nearest earlier src
    sm = difflib.SequenceMatcher(None, [norm(w['text']) for w in old], [norm(w['text']) for w in new], autojunk=False)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size): new[blk.b + k]['src'] = old[blk.a + k].get('src')
    last = old[0].get('src') if old else None
    by_old = {w.get('src'): w for w in old}
    prev_spk = new[0]['spk'] if new else brand.IDS[0]
    for w in new:
        if w.get('src') is None: w['src'] = last; w['added'] = True
        else: last = w['src']
        # who said it comes from the per-mic episode transcript (the louder-mic guess on the clip mix can give one person's
        # words to another and cut mid-sentence); an added word keeps the previous word's speaker
        if not w.get('added') and w['src'] in by_old: w['spk'] = by_old[w['src']]['spk']
        elif old: w['spk'] = prev_spk
        prev_spk = w['spk']
    for k, w in enumerate(new): w['i'] = k
    json.dump(new, open(os.path.join(D, 'words.json'), 'w'))
    added = [w['text'] for w in new if w.get('added')]
    print(f'{os.path.basename(D)}: {len(old)} episode words -> {len(new)} heard words; {len(added)} added: {" ".join(added[:30])}')
    align_words.clip(D)


if __name__ == '__main__':
    main(os.path.abspath(sys.argv[1]))

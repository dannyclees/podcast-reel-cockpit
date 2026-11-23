"""Shorts candidate finder.
Reads an episode's work/words.json (list of {i, text, start, end, spk}) and proposes one-take passages that
could become Shorts. It does NOT pick the Shorts. It ranks passages by signal density so a human (or Claude)
can score the top ones with the matrix in SELECTION.md.

Usage:
  python3 candidates.py ../../episodes/<ep>/work/words.json               # top 12
  python3 candidates.py <words.json> --top 20 --min 20 --max 180 --json out.json

How it works (plain English):
  1. Cut the word list into sentences (end punctuation, a speaker change, or a pause over 0.9 s).
  2. Tag every sentence with signals: number, household name, named thing, viewer stakes, everyday object,
     disagreement, story turn, "look at this" visual, verdict line, question, reaction from the other host.
     Also red flags: back-reference (needs context), call to action, filler start, saturated-topic words (brand.json show.saturated_topic).
  3. Find topic breaks ("speaking of", "should we talk about", "let's talk about", "next").
  4. Try every passage that starts on a sentence and ends on a sentence, 20 to 180 s, inside one topic.
  5. Score it: a strong first line, a payoff signal in every 15 s chunk, a turn, two voices, a finished last line.
     Subtract red flags. Keep the best passages that do not overlap.
All weights are judgement calls set from research/selection/SELECTION.md. They rank; they do not decide.
"""
import json, re, sys, argparse, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pipeline'))
from brand import SHOW

# ---------- word lists (crude on purpose: they must be readable and editable) ----------
HOUSEHOLD = (r"elon|musk|trump|jensen|zuckerberg|altman|bezos|bill gates|buffett|obama|putin|steve jobs|mrbeast|rogan|"
             r"kanye|taylor swift|biden|oprah|stallone|schwarzenegger|lebron|ronaldo|messi|pentagon|nasa|fbi|cia|"
             r"google|apple|microsoft|amazon|meta|facebook|tesla|spacex|nvidia|netflix|openai|chatgpt|disney|mcdonald|"
             r"walmart|costco|uber|iphone|mac ?mini|macbook|youtube|tiktok|instagram|whoop|oracle|samsung|sony|"
             r"military|white house|congress|france|china|japan|russia|india|america")
STOP = set("the a an and or of in on for to with about at by from our your their my this that these those topic topics niche show is are it its at most one short shorts per episode".split())


def keywords(text):
    """the plain words of a brand.json line, as regex alternatives"""
    return sorted({w for w in re.findall(r"[a-z0-9][a-z0-9'+-]+", (text or '').lower()) if w not in STOP}, key=lambda w: -len(w))


def any_of(words):
    return r"\b(" + "|".join(map(re.escape, words)) + r")\b" if words else r"(?!)"   # (?!) never matches


TOPICS = SHOW.get('topics') or []
# named things in this show's world: whatever its topics name, plus show.named_things if you add that list
NAMED_THING = any_of(keywords(' '.join(TOPICS + (SHOW.get('named_things') or []))))
NUMBER_WORDS = (r"\b(one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|fifty|hundred|thousand|"
                r"million|billion|trillion|half|double|triple|percent|percentile)\b")
EVERYDAY = (r"\b(freezer|fridge|refrigerat\w*|grocer\w*|stores?|supermarket|steak|vegetables|cheese|oatmeal|peanut butter|"
            r"ice cream|milkshake|food|car|cars|house|home|kids?|wife|girlfriend|phone|alarm clock|wearable|"
            r"band|gym|muscle|legs|neck|hands|nose|ears|soap|bath|chest|shower|bed|tv|show|money|salary|job|"
            r"rent|bills?|bank|water|power|electricity|soap|dog|school)\b")
STAKES = (r"\b(you|your|you're|you've|yourself)\b.{0,40}\b(money|job|kids?|health|home|house|freezer|fridge|food|data|"
          r"life|body|muscle|legs|car|family|savings|bills?|buy|stock up|pay|spend|lose|afford|die|live)\b|"
          r"\bcoming to a\b|\bnear you\b|\bin your\b|\byour local\b|\bcan hack\b|\bhack my\b|\bwhat about your\b")
DISAGREE = (r"\b(i disagree|no no|that's not|that is not|i don't think|i hate to say|the problem is|the reality is|"
            r"controversial|unpopular|wrong|overrated|myth|bullshit|nonsense|driven up the wall|how dare|"
            r"i don't really care|not that crazy|sounds crazy|the issue is|actually,|but honestly)\b")
TURN = (r"\b(turns out|it turned out|all of a sudden|but then|and then|so they|instead|imagine|here's the thing|"
        r"what happened|the twist|guess what|believe it or not|it's not .{0,30} it's|the reason why|"
        r"we immediately|and they did|did you know|you'd think|but what about)\b")
LOOK = (r"\b(look at this|look at that|you can see|on screen|this chart|pull (this|it) up|check this out|right here|"
        r"this image|this one|scroll down|as you can see|here's the|this graph|this scan|we're seeing)\b")
VERDICT = (r"\b(the takeaway|the truth is|the point is|the lesson|the key is|you need|you've got to|you got to|"
           r"never too late|everything is|nothing is|always|never|that's why|that's the|this is literally|"
           r"just goes to show|the reality is|the problem is|that's what|we need|it's crazy)\b")
REACT = (r"^(jesus|no way|wow|duh|bonkers|that is bad|crazy|haha|ha|what|seriously|oh my|dude|god damn)\b|\[laughter\]")
# R3: the topic the niche is drowning in: at most one Short per episode. Words from show.saturated_topic, plus show.saturated_words if you add that list
SATURATED = any_of(keywords(' '.join([SHOW.get('saturated_topic') or ''] + (SHOW.get('saturated_words') or []))))
BACKREF = (r"\b(as i said|like i said|as we said|we talked about|we said this|i mentioned|earlier|yesterday's episode|"
           r"last episode|check out yesterday|going back to|like we said|the other day we)\b")
CTA = (r"\b(subscribe|comment down below|comments down below|drop a comment|giving away|giveaway|link below|"
       r"let us know|hit the|follow for|check out yesterday)\b")
FILLER_START = r"^(and|so|but|yeah|like|um|uh|okay|ok|right|well|i mean|you know|anyway|now)\b"
TOPIC_BREAK = (r"\b(speaking of|should we talk about|shall we (talk|start|answer)|let's talk about|moving on|"
               r"next (story|topic|up)|on to the next|let's start with|we've got a couple of other)\b")
QUESTION_START = r"^(why|how|what|who|which|can|could|would|should|is|are|do|does|did|have|has|will)\b"

def rx(p): return re.compile(p, re.I)
R = {k: rx(v) for k, v in dict(household=HOUSEHOLD, named=NAMED_THING, numword=NUMBER_WORDS, everyday=EVERYDAY,
                                 stakes=STAKES, disagree=DISAGREE, turn=TURN, look=LOOK, verdict=VERDICT,
                                 react=REACT, sat=SATURATED, backref=BACKREF, cta=CTA, filler=FILLER_START,
                                 topic=TOPIC_BREAK, qstart=QUESTION_START).items()}
DIGIT = re.compile(r"\d|\$|%")

def fmt(t): return f"{int(t // 60)}:{int(t % 60):02d}"

# ---------- 1. sentences ----------
def sentences(words, pause=0.9):
    out, cur = [], []
    for k, w in enumerate(words):
        if cur and (w['spk'] != cur[-1]['spk'] or w['start'] - cur[-1]['end'] > pause):
            out.append(cur); cur = []
        cur.append(w)
        if w['text'][-1:] in '.?!':
            out.append(cur); cur = []
    if cur: out.append(cur)
    S = []
    for ws in out:
        text = ' '.join(w['text'] for w in ws).strip()
        S.append(dict(i0=ws[0]['i'], i1=ws[-1]['i'], start=ws[0]['start'], end=ws[-1]['end'], spk=ws[0]['spk'],
                      text=text, n=len(ws), q=text.endswith('?'), closed=text[-1:] in '.?!'))
    return S

# ---------- 2. tags ----------
def tag(s, prev=None):
    t = s['text']; tl = t.lower()
    g = {}
    g['number'] = bool(DIGIT.search(t)) or bool(R['numword'].search(t))
    g['household'] = bool(R['household'].search(t))
    g['named'] = g['household'] or bool(R['named'].search(t))
    g['everyday'] = bool(R['everyday'].search(t))
    g['stakes'] = bool(R['stakes'].search(t))
    g['disagree'] = bool(R['disagree'].search(t))
    g['turn'] = bool(R['turn'].search(t))
    g['look'] = bool(R['look'].search(t))
    g['verdict'] = bool(R['verdict'].search(t))
    g['question'] = s['q'] and s['n'] >= 4
    g['react'] = bool(R['react'].search(tl)) and s['n'] <= 8
    g['sat'] = bool(R['sat'].search(t))
    g['backref'] = bool(R['backref'].search(t))
    g['cta'] = bool(R['cta'].search(t))
    g['filler_start'] = bool(R['filler'].search(tl))
    g['topic_break'] = bool(R['topic'].search(t))
    return g

HEALTH = rx(r"\b(muscle|testosterone|health|fitness|gym|workout|creatine|protein|age|aging|70s|sleep|diet|body|legs|cardio|longevity)\b")
MONEY = rx(r"\$|\b(dollars?|cost|costs|price|money|spend|buy|sell|revenue|million|billion|cheap|expensive|budget|roi|k\b)")
HACK = rx(r"\b(hack\w*|cyber\w*|attack\w*|security|vulnerab\w*|threat)\b")

TOPIC_RX = [(t, rx(any_of(keywords(t)))) for t in TOPICS]
SAT_NAME = (SHOW.get('saturated_topic') or 'saturated topic').split(';')[0][:24]

def topic_guess(P):
    txt = ' '.join(s['text'] for s in P)
    n = max(1, len(txt.split()))
    d = lambda r: len(r.findall(txt)) * 100 / n          # hits per 100 words
    sa, ev, he, mo, ha = d(R['sat']), d(R['everyday']), d(HEALTH), d(MONEY), d(HACK)
    if ha >= 0.8 and ev >= 1.0: return 'tech-meets-everyday'
    if he >= 1.5: return 'health/body'
    if mo >= 1.2 and sa < 3: return 'money'
    if sa >= 2.5 and mo >= 1.0: return SAT_NAME + ' + money'
    if sa >= 2.5: return SAT_NAME
    best = max(TOPIC_RX, key=lambda x: d(x[1]), default=None)
    if best and d(best[1]) >= 1.5: return best[0][:24]
    if ev >= 2.0: return 'everyday/personal'
    return 'other'

PAYOFF_KEYS = ('number', 'household', 'turn', 'verdict', 'look', 'disagree', 'stakes')

def opener_strength(s):
    """0-3: is this a line a stranger would stop for? (Article I hook test, done crudely)"""
    g = s['g']; sc = 0
    # a leading "So," / "And" is trimmed in the edit (R2), so judge the rest of the line, but a line
    # that is weak once trimmed stays weak ("And I said a lot of these things..." scores 0)
    if g['question']: sc += 2
    if g['household'] or g['number']: sc += 1
    if g['disagree'] or g['stakes'] or g['everyday']: sc += 1
    if g['backref'] or g['cta']: sc -= 2
    if s['n'] < 4: sc -= 1
    if s['text'][:1].islower(): sc -= 1          # starts mid-sentence (a fragment after an interjection)
    return max(0, min(3, sc))

def ending_strength(S, j):
    """0-3: does the passage stop on a finished line? Short closed sentence, a verdict, or a reaction/topic break next."""
    s = S[j]; g = s['g']; sc = 0
    if s['n'] < 4 or g['react']: return 0         # "Yeah." is not an ending
    if s['closed'] and not s['q']: sc += 1
    if g['verdict'] or g['disagree'] or (s['n'] <= 14 and s['closed']): sc += 1
    nxt = S[j + 1] if j + 1 < len(S) else None
    if nxt and (nxt['g']['react'] or nxt['g']['topic_break'] or nxt['spk'] != s['spk']): sc += 1
    if s['text'].lower().rstrip('.?! ').endswith((' and', ' but', ' so', ' like', ' the', ' a', ' to', ' of')): sc -= 2
    if g['cta']: sc -= 2
    return max(0, min(3, sc))

# ---------- 3-5. passages ----------
def score_passage(S, a, b):
    P = S[a:b + 1]
    dur = P[-1]['end'] - P[0]['start']
    G = lambda k: sum(1 for s in P if s['g'][k])
    # a payoff signal in every 15 s chunk (R32: long only if it keeps paying off)
    chunks = max(1, int(dur // 15) + (1 if dur % 15 > 5 else 0))
    hit = set()
    for s in P:
        if any(s['g'][k] for k in PAYOFF_KEYS):
            hit.add(min(chunks - 1, int((s['start'] - P[0]['start']) // 15)))
    coverage = len(hit) / chunks
    spk = {s['spk'] for s in P}
    words = {s['spk']: sum(x['n'] for x in P if x['spk'] == s['spk']) for s in P}
    second = sorted(words.values())[0] / max(1, sum(words.values())) if len(spk) > 1 else 0
    o = opener_strength(P[0])
    # a cold open: the best question / claim inside the first 40% (Article II lets us move it to 0.0 s)
    cold = max(P[:max(1, int(len(P) * 0.4))], key=opener_strength)
    e = ending_strength(S, b)
    sat_share = G('sat') / len(P)
    sig = {k: G(k) for k in ('number', 'household', 'named', 'everyday', 'stakes', 'disagree', 'turn', 'look',
                             'verdict', 'question', 'react', 'sat', 'backref', 'cta')}
    score = (2.0 * max(o, opener_strength(cold) - 1) + 1.5 * e + 4.0 * coverage
             + 1.0 * min(2, sig['turn']) + 1.0 * min(2, sig['household'] + sig['number'] // 2)
             + 1.0 * min(2, sig['stakes'] + sig['everyday'] // 2) + 0.7 * min(2, sig['disagree'])
             + 0.7 * min(1, sig['look']) + (1.0 if second >= 0.12 else 0) + 0.5 * min(2, sig['react'])
             - 2.0 * sig['backref'] - 3.0 * sig['cta'] - (2.0 if sat_share > 0.5 else 0))
    # length: winners sit at ~45-75 s; past 90 s it must keep paying off
    if dur < 25: score -= 1.5
    if dur > 90 and coverage < 0.8: score -= 2.0
    if dur > 120 and coverage < 0.9: score -= 1.5
    flags = []
    if sig['backref']: flags.append('NEEDS-CONTEXT?')
    if sig['cta']: flags.append('CTA-INSIDE')
    if sat_share > 0.5: flags.append('SATURATED-TOPIC (R3: max 1 Short on it per episode)')
    if P[0]['g']['filler_start']: flags.append('FILLER-START (trim, R2)')
    if P[0]['text'][:1].islower(): flags.append('STARTS MID-SENTENCE')
    if e == 0: flags.append('WEAK-END')
    if len(spk) == 1: flags.append('ONE-VOICE')
    if dur > 90 and coverage < 0.8: flags.append('SAGS (gap >15 s without a payoff)')
    return dict(a=a, b=b, start=P[0]['start'], end=P[-1]['end'], dur=dur, i0=P[0]['i0'], i1=P[-1]['i1'],
                score=round(score, 2), opener=o, ending=e, coverage=round(coverage, 2), two_voices=round(second, 2),
                signals=sig, flags=flags, first=P[0]['text'], last=P[-1]['text'],
                topic=topic_guess(P), cold_open=cold['text'] if cold is not P[0] and opener_strength(cold) > o else None,
                speakers=sorted(spk))

def find(words, top=12, mn=20, mx=180, overlap=0.3):
    S = sentences(words)
    for k, s in enumerate(S): s['g'] = tag(s, S[k - 1] if k else None)
    seg, cur = [], 0
    for s in S:
        if s['g']['topic_break']: cur += 1
        seg.append(cur)
    C = []
    for a in range(len(S)):
        if S[a]['n'] < 4 or S[a]['g']['cta']: continue
        for b in range(a, len(S)):
            dur = S[b]['end'] - S[a]['start']
            if dur > mx: break
            if seg[b] != seg[a] and not (S[b]['g']['topic_break'] and b == a): break   # R1: one take, one topic
            if dur < mn: continue
            C.append(score_passage(S, a, b))
    C.sort(key=lambda c: -c['score'])
    keep = []
    for c in C:
        ok = True
        for k in keep:
            inter = max(0, min(c['end'], k['end']) - max(c['start'], k['start']))
            if inter / min(c['dur'], k['dur']) > overlap: ok = False; break
        if ok: c['alts'] = []; keep.append(c)
        if len(keep) >= top: break
    # alternates: other cuts of the same moment (different start or end), best first
    for c in C:
        for k in keep:
            if c is k or len(k['alts']) >= 2: continue
            inter = max(0, min(c['end'], k['end']) - max(c['start'], k['start']))
            # prefer a different START (the setup question is usually where cuts go wrong)
            if inter / min(c['dur'], k['dur']) > 0.4 and abs(c['start'] - k['start']) > 8 \
               and all(abs(c['start'] - x['start']) > 8 for x in k['alts']):
                k['alts'].append(c); break
    return S, keep

def short(t, n=150): return t if len(t) <= n else t[:n - 3] + '...'

def report(S, keep, src):
    L = []
    L.append(f"Shorts candidates for {src}")
    L.append(f"{len(S)} sentences. Ranked by signal density. This is a shortlist for scoring, not a pick.")
    L.append("Score each with the SELECTION.md matrix (gate + 0-3 tests). Signals: num=number, fam=household name,")
    L.append("named=named thing, every=everyday object, stake=viewer stakes, dis=disagreement, turn=story turn,")
    L.append("look=look-at-this visual, verd=verdict line, q=question, react=other host reacts, sat=saturated-topic words.")
    L.append("cover = share of 15 s chunks with a payoff signal (R32 wants ~1.0 for anything over 90 s).")
    L.append('')
    L.append(f"{'#':>2} {'time':>11} {'secs':>4} {'words':>11} {'score':>5} {'open':>4} {'end':>3} {'cover':>5} {'2nd':>4} {'topic':<24} signals")
    for r, c in enumerate(keep, 1):
        s = c['signals']
        sig = (f"num{s['number']} fam{s['household']} named{s['named']} every{s['everyday']} stake{s['stakes']} "
               f"dis{s['disagree']} turn{s['turn']} look{s['look']} verd{s['verdict']} q{s['question']} "
               f"react{s['react']} sat{s['sat']}")
        L.append(f"{r:>2} {fmt(c['start']):>5}-{fmt(c['end']):<5} {c['dur']:4.0f} {c['i0']:>5}-{c['i1']:<5} {c['score']:5.1f} "
                 f"{c['opener']:>4} {c['ending']:>3} {c['coverage']:5.2f} {c['two_voices']:4.2f} {c['topic']:<24} {sig}")
    L.append('')
    for r, c in enumerate(keep, 1):
        L.append(f"--- #{r}  {fmt(c['start'])}-{fmt(c['end'])}  ({c['dur']:.0f} s, words {c['i0']}-{c['i1']}, {'+'.join(c['speakers'])})")
        L.append(f"    first: {short(c['first'])}")
        if c['cold_open']: L.append(f"    cold open?: {short(c['cold_open'])}")
        L.append(f"    last:  {short(c['last'])}")
        if c['flags']: L.append(f"    flags: {', '.join(c['flags'])}")
        for x in c.get('alts', []):
            L.append(f"    alt cut: {fmt(x['start'])}-{fmt(x['end'])} ({x['dur']:.0f} s, words {x['i0']}-{x['i1']}, score {x['score']}) first: {short(x['first'], 80)}")
    return '\n'.join(L)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('words'); ap.add_argument('--top', type=int, default=12)
    ap.add_argument('--min', type=float, default=20); ap.add_argument('--max', type=float, default=180)
    ap.add_argument('--json')
    a = ap.parse_args()
    W = json.load(open(a.words))
    S, keep = find(W, a.top, a.min, a.max)
    print(report(S, keep, a.words))
    if a.json: json.dump([{k: v for k, v in c.items() if k != 'alts'} | {'alts': [{k: v for k, v in x.items() if k != 'alts'} for x in c.get('alts', [])]} for c in keep], open(a.json, 'w'), indent=1)

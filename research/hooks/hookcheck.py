#!/usr/bin/env python3
"""hookcheck: score a spoken first line and a written on-screen title against the hook rules (HOOKS.md).

Usage:
  python3 hookcheck.py --spoken "Why does nobody read the label?" --title "Shoppers ignored [350 warning] labels"
  python3 hookcheck.py --spoken "..."            (spoken only)
  python3 hookcheck.py --title "..."             (title only)
  python3 hookcheck.py --json candidates.json    (list of {"spoken":..,"title":..}; prints a ranked table)

Only rules a script can check are scored. Truth, picture-match and "would a stranger care" stay manual (see HOOKS.md checklist).
Rule weights come from what separated winners from controls in data/ (see HOOKS.md). They are rules of thumb, not proof."""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F

HEDGE = re.compile(r"\b(probably|maybe|i think|i guess|kind of|kinda|sort of|i feel like|i don't know|perhaps|might be)\b", re.I)
VERBS = set('''is are was were be been am has have had do does did can could will would should must may might shall
make makes made pay pays paid run runs ran give gives gave build builds built turn turns turned sell sells sold buy buys
bought lose loses lost quit quits leave leaves left see sees saw tell tells told say says said find finds found break breaks
broke steal steals stole meet met send sends sent hack hacks hacked take takes took win wins won beat beats fire fires fired
hire hires hired raise raises raised spend spends spent get gets got go goes went try tries tried ask asks asked call calls
called catch caught kill kills killed save saves saved die dies died start starts started stop stops stopped heat heats heated
cook cooks cooked melt melts melted burn burns burned rot rots rotted spoil spoils spoiled shut shuts lift lifts lifted
train trains trained move moves moved sit sits sat walk walks walked fall falls fell slip slips slipped look looks looked
need needs needed want wants wanted keep keeps kept grow grows grew shrink shrinks shrank work works worked think thinks thought
know knows knew hit hits attack attacks attacked suspect suspects suspected investigate investigates investigated cut cuts
eat eats ate drink drinks drank sleep sleeps slept age ages aged beat fix fixes fixed own owns owned rule rules ruled
probe probes probed shrank shrink trains
'''.split())

TFILL = re.compile(r"\b(today|tonight|now|right now|this week|this year|finally|just dropped|breaking)\b", re.I)

def wrap(text, width=22):
    lines, cur = [], ''
    for w in text.split():
        if len(cur) + len(w) + (1 if cur else 0) > width and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + ' ' + w).strip()
    if cur: lines.append(cur)
    return lines

def spans(title):
    return re.findall(r"\[([^\[\]]+)\]", title)

def plain(title):
    return title.replace('[', '').replace(']', '')

def has_verb(t):
    ws = [F.clean(w) for w in F.words(t)]
    return (any(w in VERBS for w in ws) or any(w.endswith("n't") for w in ws) or '?' in t
            or any(len(w) > 4 and w.endswith('ed') and not w.endswith('eed') for w in ws))

# ---------------- spoken rules ----------------
def spoken_rules(line):
    s = F.first_sentence(line, 40)
    ws = F.words(s)
    wbc = F.words_before_concrete(s)
    first3 = ' '.join(F.clean(w) for w in ws[:3])
    return [
        ('S1', 3, 'No throat-clearing opener (so/and/but/well/look/listen/I think/you know/I\'m telling you/okay)', not F.throat_clear(s) and not re.match(r"^(and|so|but|okay|ok|alright|all right)\b", first3)),
        ('S2', 2, f'No co-host name ({"/".join(F.brand.first_names())}) or "guys" in the first 8 words', not any(F.clean(w) in F.COHOST | {'guys'} for w in ws[:8])),
        ('S3', 2, 'Opens on a question (or, checked by eye, a story already moving)', F.spoken_question(s)),
        ('S4', 1, f'Concrete thing (number, name, object) in the first 8 words [found at word {wbc}]', wbc <= 7),
        ('S5', 1, 'No hedge (probably, maybe, I think, kind of)', not HEDGE.search(s)),
        ('S6', 1, f'First sentence 4 to 18 words (about 1 to 4.5 s at 4 words/s) [{len(ws)} words]', 4 <= len(ws) <= 18),
        ('S7', 1, 'No co-host name or "guys" anywhere in the line', not any(F.clean(w) in F.COHOST | {'guys'} for w in ws)),
    ]

# ---------------- written rules ----------------
def title_rules(title):
    t = plain(title)
    n = F.word_count(t)
    sp = spans(title)
    lines = wrap(t)
    return [
        ('W1', 2, f'3 to 7 words [{n}]', 3 <= n <= 7),
        ('W2', 2, f'Fits 2 lines of 22 characters [{len(lines)} lines: {" / ".join(lines)}]', len(lines) <= 2),
        ('W3', 3, 'Has a number or a named person/brand/place', F.has_number(t) or F.has_entity(t)),
        ('W4', 2, 'Has a concrete, picturable noun (thing, name or number)', F.concrete(t)),
        ('W5', 3, 'Is a sentence or question, not a label (has a verb or a "?")', has_verb(t)),
        ('W6', 3, 'No "X vs Y" label and no "What X looks like"', not F.looks_like_label(t)),
        ('W7', 1, 'No vague abstract noun carrying the title (truth, secret, mindset, journey...)', not F.vague(t)),
        ('W8', 2, f'Exactly one [highlight] span, 1 to 4 words [{len(sp)} span(s)]', len(sp) == 1 and 1 <= F.word_count(sp[0]) <= 4),
        ('W9', 1, 'No time filler (today, now, right now, this week, finally) and no emoji', not TFILL.search(t) and not F.emoji(t)),
        ('W10', 1, 'Not all caps', not F.all_caps(t)),
    ]

def score(rules):
    got = sum(w for _, w, _, ok in rules if ok); mx = sum(w for _, w, _, _ in rules)
    return got, mx

def report(kind, text, rules):
    got, mx = score(rules)
    print(f'\n{kind}: "{text}"   score {got}/{mx}')
    for rid, w, desc, ok in rules:
        print(f'  {"PASS" if ok else "FAIL"}  {rid} (+{w})  {desc}')
    return got, mx

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--spoken'); ap.add_argument('--title'); ap.add_argument('--json')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    if a.json:
        items = json.load(open(a.json)); out = []
        for it in items:
            row = dict(it)
            if it.get('spoken'):
                g, m = score(spoken_rules(it['spoken'])); row['spoken_score'] = f'{g}/{m}'; row['_s'] = g / m
                row['spoken_fails'] = [r for r, _, _, ok in spoken_rules(it['spoken']) if not ok]
            if it.get('title'):
                g, m = score(title_rules(it['title'])); row['title_score'] = f'{g}/{m}'; row['_t'] = g / m
                row['title_fails'] = [r for r, _, _, ok in title_rules(it['title']) if not ok]
            out.append(row)
        print(json.dumps(out, indent=1, ensure_ascii=False)); return
    if not (a.spoken or a.title): ap.error('give --spoken and/or --title')
    if a.spoken: report('SPOKEN', a.spoken, spoken_rules(a.spoken))
    if a.title: report('TITLE', a.title, title_rules(a.title))

if __name__ == '__main__':
    main()

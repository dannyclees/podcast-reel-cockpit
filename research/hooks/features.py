"""Shared, code-checkable hook features. Used by hookcheck.py.
All features are crude word-list rules. They are measured by code, so they are repeatable, not perfect."""
import re, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'pipeline'))
import brand

_DICT = set()
for p in ('/usr/share/dict/words', '/usr/share/dict/web2'):
    if os.path.exists(p):
        _DICT |= {w.strip() for w in open(p, errors='ignore') if w.strip() and w.strip()[0].islower()}
_FIRST = set()
if os.path.exists('/usr/share/dict/propernames'):
    _FIRST = {w.strip().lower() for w in open('/usr/share/dict/propernames') if w.strip()}
_FIRST -= _DICT          # drop names that are also common words (Will, Win, The)

def _known(c):
    """True if c (lower case) is an ordinary dictionary word, allowing simple endings"""
    if c in _DICT: return True
    for suf, add in (('s', ''), ('es', ''), ('ing', ''), ('ing', 'e'), ('ed', ''), ('ed', 'e'), ('er', ''), ('ers', ''), ('ly', ''), ('ies', 'y'), ('ied', 'y')):
        if c.endswith(suf) and (c[:-len(suf)] + add) in _DICT: return True
    return False

# people, brands, places, orgs that show up in podcasts (seed list, lower case), plus the words of this show's topics in brand.json
ENTITIES = set('''
elon musk zuck zuckerberg jensen huang altman sam bezos gates buffett trump biden obama hillary clinton
putin xi nadella pichai sundar dario amodei karpathy hormozi rogan lex fridman mrbeast kanye taylor swift
jobs wozniak thiel andreessen palmer luckey tom lee saylor vitalik toto wolff peter beck galloway
openai anthropic claude chatgpt gpt gemini grok xai deepmind google apple microsoft amazon meta facebook
instagram tiktok youtube netflix nvidia tesla spacex starlink twitter linux github cursor
mercedes ferrari f1 rolex disney disneyland mcdonalds walmart costco starbucks uber airbnb
coinbase bitcoin ethereum crypto solana goldman jpmorgan blackrock harvard stanford mit yc
pentagon nasa cia fbi nsa seal seals sas army navy marine marines wnba nba nfl
america american usa uk britain british england london china chinese japan korea india indian
russia russian ukraine iran iraq israel france french paris germany europe european texas
california florida canada mexico africa australia taiwan silicon valley wall street
'''.split()) | {w for t in brand.SHOW.get('topics') or [] for w in re.findall(r"[a-z0-9]{3,}", t.lower())}

NEGATIVE = set('''
kill kills killing killed dead death die dies dying deadly scam scams fake fraud lie lies lying liar
worst bad worse wrong mistake mistakes fail fails failed failing failure broke broken bankrupt
destroy destroyed destroys destroying threat threats warning danger dangerous risk risky brutal
shocking scary creepy creepiest terrifying terrify nightmare disaster crash crashed collapse collapsing
exposed expose exposes hack hacked hacks hacker hackers attack attacked war fire fired fires burn
burning lose losing lost loss problem problems overrated stop quit trap toxic insane crazy evil
illegal banned ban steal stole stolen cheat cheating poison doomed end over weak sick broke panic
never nobody nothing cant can't won't wont doesn't don't isn't aren't
'''.split())

CONTRAST = {'but', 'not', 'instead', 'actually', 'really', 'yet', 'until', 'unless', "isn't", "aren't",
            "doesn't", "don't", "won't", "wasn't", 'never', 'vs', 'vs.', 'versus', 'without', 'despite',
            'except', 'only', 'wrong', 'myth', 'truth', 'secretly', 'nobody', 'no'}

TIME = re.compile(r"\b(\d+\s*(second|seconds|sec|minute|minutes|min|hour|hours|day|days|week|weeks|month|months|year|years|yr|yrs)|"
                  r"today|tonight|yesterday|tomorrow|overnight|this week|last week|next week|this year|last year|"
                  r"next year|now|right now|soon|forever|daily|weekly|annually|/yr|/month|/day|"
                  r"20[0-9]{2}|19[0-9]{2}|decade|century|age|aged|old|young|at \d+)\b", re.I)

NUMWORDS = set('one two three four five six seven eight nine ten eleven twelve fifteen twenty thirty forty fifty '
               'hundred thousand million billion trillion half double triple'.split())

# abstract nouns that make a title vague ("what X looks like", "X vs Y" labels read as generated)
VAGUE = set('''
thing things stuff something everything anything way ways truth reality future secret secrets power
mindset journey lesson lessons life success value impact potential mistake mistakes tips hacks
game changer gamechanger insight insights perspective approach strategy strategies concept idea ideas
situation importance difference role nature state world
'''.split())

# a small list of physical, picturable nouns common in this set (extends with the title's own entities and numbers)
CONCRETE = set('''
dog dogs cat steak sushi burger dinner restaurant restaurants rocket rockets engine printer car cars truck
plane jet boat house home office desk phone iphone laptop computer chip chips robot robots
fridge fridges supermarket supermarkets store stores shop shops money cash dollar dollars bill check
wife husband kid kids son daughter dad mom mother father baby employee employees boss ceo founder
doctor surgeon nurse lawyer soldier soldiers seal hacker hackers teacher student students electrician electricians
gun guns bomb bombs weapon weapons knife fire fires water food coffee beer wine pizza watch watches ring
book books camera screen brain body muscle muscles heart blood bone bones legs thigh scan mri pill pills
gym bike city cities school prison hospital base bases military commissary airport road bridge factory farm land triathlete triathletes soap wagyu
email emails message messages code app apps website server data contract deal salary paycheck
'''.split())

FILLER_OPEN = re.compile(r"^\s*(so|and|but|well|okay|ok|um|uh|yeah|yes|right|like|look|listen|honestly|basically|"
                         r"i mean|i think|i guess|i feel like|i'm telling you|i am telling you|i tell you|let me tell you|"
                         r"you know|the thing is|here's the thing|to be honest|by the way|anyway|actually|literally|"
                         r"oh|man|dude|bro|guys)\b[\s,.!]", re.I)
COHOST = {n.lower() for n in brand.first_names()}   # the people on this show (brand.json)
QWORDS = {'what', 'why', 'how', 'who', 'when', 'where', 'which', 'is', 'are', 'can', 'could', 'should', 'would',
          'do', 'does', 'did', 'will', 'have', 'has', 'was', 'were'}

def words(t):
    return re.findall(r"[A-Za-z0-9$₹€£%'’.\-]+", t.replace('’', "'"))

def clean(w):
    return w.lower().strip(".'\"-!?,:;")

def is_title_case_caps(t):
    ws = [w for w in words(t) if w[0].isalpha()]
    return bool(ws) and sum(w.isupper() and len(w) > 1 for w in ws) / len(ws) >= 0.5

def is_title_case(t):
    ws = [w for w in words(t) if w[0].isalpha()]
    return bool(ws) and sum(w[0].isupper() for w in ws) / len(ws) >= 0.6

def has_number(t):
    return bool(re.search(r"\d", t)) or any(clean(w) in NUMWORDS for w in words(t))

def entity_tokens(t):
    ws = words(t); tc = is_title_case(t); caps = t.upper() == t
    out = []
    for i, w in enumerate(ws):
        c = clean(w)
        if not c or "n't" in c or "n’t" in c: continue
        if c in ENTITIES:
            out.append(w); continue
        if caps: continue
        if re.fullmatch(r"[A-Z]{2,6}s?", w) and c not in {'ai', 'ceo', 'ok', 'tv', 'diy', 'vs', 'i'} and (tc is False or not _known(c)) and not is_title_case_caps(t):
            out.append(w); continue
        if w[0].isupper() and (i > 0 or tc):
            if c in _FIRST: out.append(w); continue
            if "'" in c: c = c.split("'")[0]
            if len(c) > 2 and not _known(c):
                out.append(w)
        elif w[0].isupper() and i == 0 and c in _FIRST:
            out.append(w)
    return out

def has_entity(t):
    return bool(entity_tokens(t))

def is_question(t):
    ws = words(t)
    return '?' in t or (bool(ws) and clean(ws[0]) in {'who', 'which', 'should', 'could', 'would', 'is', 'are', 'can', 'do', 'does', 'did'})

def second_person(t):
    return bool(re.search(r"\b(you|your|you're|youre|yours|yourself|you'll|you've)\b", t, re.I))

def negative(t):
    return any(clean(w) in NEGATIVE for w in words(t)) or bool(re.search(r"n't\b", t, re.I))

def contrast(t):
    return any(clean(w) in CONTRAST for w in words(t)) or bool(re.search(r"n't\b", t, re.I))

def time_frame(t):
    return bool(TIME.search(t))

def how_why_what(t):
    ws = words(t.strip('"“” '))
    return bool(ws) and clean(ws[0]) in {'how', 'why', 'what', "what's", 'whats', 'when', 'who', 'where', 'which'}

def all_caps(t):
    letters = [c for c in t if c.isalpha()]
    return len(letters) >= 4 and sum(c.isupper() for c in letters) / len(letters) >= 0.9

def caps_word(t):
    """one or more SHOUTED words (3+ letters) in a title that is not all caps"""
    if all_caps(t): return False
    return any(re.fullmatch(r"[A-Z]{3,}", w) and clean(w) not in ENTITIES for w in words(t))

def concrete(t):
    ws = [clean(w) for w in words(t)]
    return any(w in CONCRETE or w.rstrip('s') in CONCRETE for w in ws) or has_entity(t) or bool(re.search(r"[$₹€£]\d|\d", t))

def vague(t):
    ws = [clean(w) for w in words(t)]
    return any(w in VAGUE for w in ws) and not concrete(t)

def vs_label(t):
    return bool(re.search(r"\b(vs\.?|versus)\b", t, re.I))

def looks_like_label(t):
    """noun-phrase label with no verb, e.g. 'What 70-year-old muscle looks like' / 'Muscle at 70 vs muscle at 30'"""
    if vs_label(t): return True
    if re.match(r"^\s*what .* looks like\s*$", t, re.I): return True
    return False

def word_count(t):
    return len([w for w in words(t) if re.search(r"[A-Za-z0-9]", w)])

def quoted(t):
    return bool(re.search(r"^[\"“'‘]|[\"“”]", t.strip()))

def emoji(t):
    return bool(re.search(r"[\U0001F300-\U0001FAFF☀-➿]", t))

TITLE_FEATURES = {
    'number present': has_number,
    'named person/brand/place': has_entity,
    'question': is_question,
    'second person (you/your)': second_person,
    'negative/threat word': negative,
    'concrete noun (thing/name/number)': concrete,
    'vague abstract noun only': vague,
    'how/why/what opener': how_why_what,
    'all caps title': all_caps,
    'one SHOUTED word': caps_word,
    'contrast/twist word': contrast,
    'time frame': time_frame,
    'X vs Y label': vs_label,
    'quote marks (said line)': quoted,
    'emoji': emoji,
}

# ---------- spoken first sentence ----------
def first_sentence(text, max_words=25):
    text = re.sub(r"\s+", " ", text).strip()
    m = re.search(r"^(.+?[.?!])(\s|$)", text)
    s = m.group(1) if m else text
    ws = s.split()
    return ' '.join(ws[:max_words])

def throat_clear(s):
    s2 = s.strip().lower()
    if FILLER_OPEN.match(s2 + ' '): return True
    ws = [clean(w) for w in s2.split()[:3]]
    if ws and ws[0] in COHOST: return True     # opens by addressing the co-host
    if len(ws) > 1 and ws[1] in COHOST and ws[0] in {'hey', 'so', 'and', 'look', 'dude', 'man', 'yo'}: return True
    return False

def words_before_concrete(s):
    ws = words(s)
    for i, w in enumerate(ws):
        c = clean(w)
        if c in CONCRETE or c.rstrip('s') in CONCRETE or c in ENTITIES or re.search(r"\d", w) or c in NUMWORDS:
            return i
        if w[0].isupper() and i > 0 and (c in _FIRST or (len(c) > 2 and not _known(c.split("'")[0]))):
            return i
    return len(ws)

def spoken_question(s):
    ws = words(s)
    return '?' in s or (bool(ws) and clean(ws[0]) in QWORDS)

def first_person_story(s):
    ws = [clean(w) for w in words(s)[:6]]
    return any(w in {'i', "i'm", "i've", "i'd", 'me', 'my', 'we', "we're", 'our'} for w in ws) and not spoken_question(s)

def mid_action(s):
    """starts on the thing itself: a claim, number, name or question, with no throat-clearing in front"""
    return (not throat_clear(s)) and (spoken_question(s) or words_before_concrete(s) <= 3)

# ---------- phrasing patterns named after reading the top 60 winners (judged), then coded ----------
PAST = set('''made paid ran gave built turned sold bought lost quit left saw told said found broke stole met sent
hacked took won beat fired hired raised spent got went did tried asked called caught killed saved died started
'''.split())

def money(t):
    return bool(re.search(r"[$₹€£]\s?\d|\d+\s?(k|m|b|million|billion|trillion|crore|lakh)\b", t, re.I))

def name_colon_claim(t):
    """'Tom Lee: Ethereum Could Top $10,000' / 'Ex-Twitter CEO: The next web...' """
    m = re.match(r"^([^:|]{2,40}):\s+\S", t)
    return bool(m) and (has_entity(m.group(1)) or re.search(r"\b(ceo|founder|expert|investor|doctor|billionaire)\b", m.group(1), re.I) is not None)

def name_on(t):
    """'Sir Peter Beck on why Rocket Lab builds everything in-house' """
    m = re.match(r"^(.{2,40}?)\s+on\s+\S", t)
    return bool(m) and has_entity(m.group(1))

def past_action(t):
    ws = [clean(w) for w in words(t)]
    return any(w in PAST for w in ws) or any(re.fullmatch(r"[a-z]{3,}ed", w) and w not in {'need', 'speed', 'seed', 'red', 'bed', 'feed', 'based', 'tired', 'scared', 'shed'} for w in ws)

def denial(t):
    return bool(re.search(r"\b(not|isn't|aren't|wasn't|won't|doesn't|don't|didn't|never|no longer|stopped)\b", t.replace('’', "'"), re.I))

def first_person_q(t):
    return is_question(t) and bool(re.search(r"\b(i|i'm|my|am i|me)\b", t.replace('’', "'"), re.I))

PATTERN_FEATURES = {
    'P money amount ($, million)': money,
    'P "Name: claim"': name_colon_claim,
    'P "Name on [thing]"': name_on,
    'P past-tense action verb': past_action,
    'P denial (not/won\'t/doesn\'t)': denial,
    'P first-person viewer question': first_person_q,
    'P name + number': lambda t: has_entity(t) and has_number(t),
}
TITLE_FEATURES.update(PATTERN_FEATURES)

# ---------- spoken: question or story already moving (judged pattern, coded proxy) ----------
STORY_PAST = PAST | set('''approached invited reached announced dropped showed signed turned came went pulled took
walked rang defaced invested lived married asked told said saw heard got had did made lost won sent'''.split())

def story_moving(s):
    """first sentence carries a past-tense action in its first 12 words (someone did something)"""
    ws = [clean(w) for w in words(s)[:12]]
    return any(w in STORY_PAST for w in ws) or any(len(w) > 4 and w.endswith('ed') and w not in {'need', 'interested', 'based', 'tired', 'scared', 'excited', 'supposed', 'used'} for w in ws)

def question_or_story(s):
    return spoken_question(s) or story_moving(s)

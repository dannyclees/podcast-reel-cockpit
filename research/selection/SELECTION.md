# How to pick the best bits

**In one line:** a stranger must get it in 5 s, it must turn, it must end on a finished line, and it must carry a famous name, a number or your own stakes. Your saturated topic, told flat, is your weakest choice. Everything else is detail.

Most channels in this data cover tech and business, and the saturated topic there was AI. So "saturated topic" below means `show.saturated_topic` in `brand/brand.json`, and "topics" means `show.topics`. Topic results may not transfer to your niche. Re-test them (see `../README.md`).

Files here:

- `candidates.py`: `words.json` in, a ranked shortlist of one-take passages out. The study scripts and raw data are not included.
- Hook wording, spoken and written, is a separate study: `../hooks/`. This file decides which passage. Hooks decides how it opens.

---

## 1. The process, step by step

1. **Run the finder.** `python3 research/selection/candidates.py episodes/<ep>/work/words.json --top 12`. It reads the transcript, tags every sentence and prints 12 one-take passages with their signals and 2 alternate cuts each.
2. **Gate them.** Drop any candidate that fails one of the 4 gates (section 3). This kills most of the list.
3. **Score the rest** with the matrix (section 3). Write the score in clips.json.
4. **Pick** `shorts_per_episode` (from brand.json, usually 3 to 5) that pass the topic mix rules (section 4). Highest score first, mix second.
5. **Set the boundaries** (section 5): first word, last word, optional 2 to 3 s cold open.
6. **Cold-read test (R4).** A fresh reader gets the clip as text only, plus the first 5 s alone (R24). They say what it is about. If they cannot, drop it or move the start.
7. **Check the red flags** (section 6). Then hand over to the edit.

The finder ranks. It does not pick. A person or Claude reads every shortlisted passage before it is scored.

---

## 2. What to scan for in a transcript

These are the signals `candidates.py` tags. Each one is a reason to look closer, not a reason to ship.

| Signal | What it looks like | Why (evidence) |
|---|---|---|
| Household name | Elon, Trump, the Pentagon, Google | Titles with one: 11.5% reach 5x, against 7.9% (measured, n=191) |
| A number | "$7,000", "350 stores", "at 70" | Most consistent title signal: up in 29 channels, down in 9 (measured) |
| Your stakes | "your local store", "your job", "your legs" | Everyday or personal stakes in 21 of 38 winners, against 2 of 13 (judged) |
| Everyday object | a fridge, a steak, a car, soap | Same as above. Abstract clips lose ("PMs are bad" 4.3x) |
| A turn | "turns out", "but then", "it's not X, it's Y", a myth busted | A turn in 35 of 38 winners, against 1 of 13 (judged) |
| Disagreement | "the problem is", "I don't think", "overrated" | Contrarian lines open many winners. As a title topic alone it gives no lift (measured) |
| A look-at-this moment | "look at this", "you can see", "pull this up", a scan, a chart | Inserts fill 40% of winners, against 3% of the rest (deconstruct) |
| A verdict line | "the takeaway", "never too late", "everything is a threat" | Finished last line in 33 of 38 winners, against 6 of 13 (judged) |
| A real question | a host asks a full question | Spoken question opener in 15 of 38 winners, against 0 of 13 (judged) |
| A reaction | the other host laughs, "no way" | Listener shown in 12 of 15 winners, against 1 of 6 (deconstruct) |

Red-flag tags the finder also prints: back-reference ("as I said", "yesterday's episode"), call to action or giveaway inside, filler start, starts mid-sentence, heavy on the saturated topic, one voice only, sags (a 15 s stretch with no payoff signal).

---

## 3. The scoring matrix

### Gates: any "no" drops the clip

| Gate | Question | Pass example | Fail example |
|---|---|---|---|
| G1 Stands alone (R4) | Can a stranger say what it is about from the text alone? | "Why can a stranger open my garage door?" | "And I said a lot of these things are probably vulnerable." (which things?) |
| G2 One take (R1) | Is it one continuous passage? Trims at the start and a 2 to 3 s cold open are allowed. Joins in the middle are not. | One passage, start to finish | Seven ranges stitched together |
| G3 Clear by 5 s (R24) | Is the topic in the words and the picture by 5 s? | The first line names the thing, and the thing is on screen | "Was that something that we shared?" |
| G4 No promo inside | No giveaway, subscribe or "comment below" inside the passage? | | A giveaway in the middle of the story |

### Tests: add them up

| Test | Points | The question | 3 points looks like | Evidence |
|---|---|---|---|---|
| Hook | 0-3, x2 | Is the first line a real question, a famous name, a number, or your stakes? 1 point each kind, max 3. | "Can Google really see your ..." (question + household name + stakes) | Question openers 15/38 winners, against 0/13 (judged); median 29.9x (deconstruct) |
| Turn | 0-3 | Does something flip? 1 = a mild "actually". 2 = a clear reversal. 3 = it changes how you see a thing you own or know. | A cheap thing proves more complex than the expensive one | 35/38 against 1/13 (judged) |
| Payoff | 0-3 | Does it stop on a finished punchline, verdict or rule? Over 60 s: is there also a payoff every 15 to 20 s? | A last line you could repeat to a friend | Finished end 33/38 against 6/13 (judged); R32 |
| Stranger | 0-3 | Would someone outside your niche care? 1 = everyday object or money. 2 = your own stakes. 3 = a household name or company too. An unknown guest's name scores 0. | A government body + your fridge + your local store | Household names 11.5%, against unknown guests 6.0% (measured) |
| Number | 0-1 | Is there a concrete number a viewer can repeat? | "350 stores" | 10.0% against 7.4%, up in 29 of 44 channels (measured) |
| Picturable | 0-3 | Can you show 3+ real things (your screen, a logo, a photo, a scan)? | Real scans side by side | Inserts 40% against 3% (deconstruct) |
| Two voices | 0-2 | Does the other host ask, push back or react on camera? | "That is wild." | Listener shown 12/15 against 1/6 (deconstruct) |
| Fits | 0-1 | Does the length follow the story, with no padding? | 45 s, one story, done | Section 5 |
| Saturated-topic penalty | 0 or -2 | Is it only about your saturated topic (the latest release, a benchmark, a tool), with no person, money, body or everyday stakes? Then -2. | A flat product benchmark | Pure AI titles 3.4% against 8.8%; AI tool demos 1.7% (measured, AI was the saturated topic) |

**Max 22.** Ship at 17+. 14 to 16 only if you need the slot. Under 14: drop.

A solo show has no Two voices test. Its max is 20, so ship at 16+. That threshold is scaled, not tested.

---

## 4. Topic mix per episode

1. **At most one Short led by your saturated topic (R3).** It should carry cost, money, a famous company or your stakes, not a benchmark. In the study: pure AI news 3.4% reach 5x, tool demos 1.7%, everything else 8.8%.
2. **At least one with a household name or company in the first line.** This is the best single topic signal found.
3. **At least one "stranger" topic:** body or health, money, or your topic hitting an everyday object.
4. **Never two from the same topic stretch.** If two candidates share a segment, keep the higher score.
5. **At most one single-voice monologue** on a two-person show. Two voices are part of what makes it a podcast and not a lecture.
6. **Guests and names nobody knows do not count as famous.** Named-guest titles: 6.0%, below baseline.

---

## 5. Length and boundaries

**Start.**

- Start on the first line that states the topic with a hook. Trim "So", "And", "Yeah", "I mean" (R2).
- If the best line comes later in the same passage, use it as a 2 to 3 s cold open, then play the take.
- Never start mid-sentence or on a reply to something the viewer cannot see (0 of 38 winners open mid-thought).

**End.**

- End on the punchline, verdict or rule. Keep up to 1.5 s of the other host's laugh or reaction.
- Never end on a question, an "and", a new topic, or a call to action (weak or call-to-action endings: 4 of 38 winners against 7 of 13).

**Length.**

- Default 40 to 75 s. Winners in the moment study: median 59.5 s, median 4 beats, one beat every 17.5 s or so (judged).
- 90 to 180 s only when it pays off every 15 to 20 s (finder column `cover` near 1.0) and is one take (R32).
- 20 to 30 s is fine when the whole story fits ("Is Wagyu overrated? Yes." 57.5x in 20 s).

**Where the payoff sits** (judged, 38 winners):

- Story clips: the hook asks, the end answers (15 of 38).
- Long clips: a payoff every 15 to 20 s (19 of 38).
- Answer first, then prove it (6 of 38): "Is Wagyu overrated? Yes." It only works if more proof follows. One clip that gave the answer in line 1 and then nothing reached 3.5x.

---

## 6. Red flags (drop or fix)

1. Back-reference: "as I said", "check out yesterday's episode", "this one", "that thing".
2. Needs earlier context: 1 of 38 winners against 5 of 13 others.
3. Joins in the middle (R1).
4. Unknown guest as the hook. A name the viewer does not know is not a hook.
5. Abstract claim with nothing to show: "Most PMs are bad" (4.3x), "anti-public benchmarks" (1.0x).
6. Definition or launch explainer (1.4x in the study).
7. Sponsor or giveaway inside the passage (0.7x in the study).
8. Weak ending: "quite remarkable", "Yeah.", a trailing "So you got to understand that".
9. Inside jokes a stranger misses: running gags, in-group names, your subscriber count.
10. A claim about a real person you cannot source (R27): health, drugs, crime, private life. Trim it, or check it with the owner and a lawyer if it matters.
11. A transcript gap at the start of a reply (overlapping speech drops words). Listen before you trust the text.

---

## 7. Worked example (made up, to show the scoring)

A two-host business show. The saturated topic in `brand.json` is "crypto". The finder prints 12 passages.

**Pick: "Why your grocery bill fell". 19/22. Ship.** Hook 3x2 (question, a household retailer, your stakes). Turn 3 (the discount turns out to be paid by the supplier). Payoff 2 (a clear verdict in the last line). Stranger 3. Number 1 ("11 cents on the dollar"). Picturable 2. Two voices 2. Fits 0 (a tangent sags in the middle, so trim the end).

**Drop: "This week's token launch". 6/22.** Hook 1x2, Turn 1, Payoff 1, Stranger 0, Number 1, Picturable 2, Two voices 1, Fits 0, penalty -2. It is on the saturated topic with no stakes.

**Mix check:** at most one Short on crypto. One household name in a first line. One everyday topic. Two passages from the same stretch means keep only the higher score.

Note what a finder gets wrong. It ranks number-heavy stretches high, and the penalty in the matrix fixes that. It also misses a strong opener that sits at the end of a passage. That is a cold-open call for the person reading.

---

## 8. Evidence

### Topic study (measured, titles, correlation only)

Data: 5,180 YouTube Shorts from 54 podcast channels, 3 to 90 days old (the 5,236 in `../LENGTH.md` used a slightly different filter). Group B = 29 remote or two-host tech channels, n=2,306. Multiple = views / channel median. "Adj" = 5x+ hits in the bucket divided by the hits expected from the same channels' other Shorts (1.0 = no better). "In-ch" = channels where the bucket's median beats the rest, up/down. Buckets are keyword rules, and a title can sit in several.

| Bucket | n | 5x+ | 95% CI | Adj | In-ch | Group B n | Group B 5x+ | Group B adj |
|---|---|---|---|---|---|---|---|---|
| All Shorts (baseline) | 5,180 | 7.9% | | | | 2,306 | 5.5% | |
| Household name (pre-set list) | 191 | 11.5% | 7.7-16.8 | 1.59 | 13/3 | 97 | 9.3% | 1.86 |
| Household name (wider list) | 302 | 15.6% | 11.9-20.1 | 2.66 | 15/4 | 179 | 15.1% | 3.40 |
| Named guest, not famous | 500 | 6.0% | 4.2-8.4 | 0.63 | 9/16 | 284 | 3.2% | 0.34 |
| Personal story (I, my, story) | 350 | 11.4% | 8.5-15.2 | 1.51 | 10/10 | 129 | 3.1% | 0.53 |
| Number in title | 880 | 10.0% | 8.2-12.2 | 1.34 | 29/9 | 394 | 7.1% | 1.83 |
| Everyday object or stakes | 544 | 9.7% | 7.5-12.5 | 1.05 | 17/13 | 165 | 7.9% | 1.34 |
| Health / body | 136 | 8.8% | 5.1-14.8 | 1.13 | 9/6 | 62 | 4.8% | 0.79 |
| Contrarian claim | 669 | 8.7% | 6.8-11.0 | 1.04 | 15/18 | 285 | 6.0% | 1.05 |
| Money / business | 1,275 | 8.5% | 7.1-10.2 | 1.01 | 16/15 | 524 | 6.3% | 1.68 |
| Future / fear | 470 | 7.7% | 5.6-10.4 | 1.04 | 18/9 | 237 | 5.9% | 1.16 |
| How-to / advice | 307 | 6.5% | 4.3-9.8 | 0.76 | 6/11 | 80 | 2.5% | 0.53 |
| Question mark title | 490 | 6.3% | 4.5-8.8 | 0.86 | 12/12 | 154 | 4.5% | 0.91 |
| Tech meets everyday life | 89 | 5.6% | 2.4-12.5 | 0.89 | 5/4 | 63 | 6.3% | 1.07 |
| Any AI word | 1,372 | 4.4% | 3.4-5.6 | 0.57 | 16/13 | 1,128 | 4.2% | 0.51 |
| AI news / model release | 320 | 3.4% | 1.9-6.0 | 0.63 | 11/10 | 283 | 3.2% | 0.60 |
| Pure AI (no person, money, body, everyday) | 889 | 3.4% | 2.4-4.8 | 0.41 | 14/16 | 775 | 3.6% | 0.42 |
| AI tool demo | 174 | 1.7% | 0.6-4.9 | 0.35 | 11/6 | 133 | 1.5% | 0.34 |

What to trust:

- **Strong:** household names up, unknown guests down, numbers up, the saturated topic down, tool demos down. Each holds in all Shorts and in Group B, and after the channel adjustment.
- **The wider name list is inflated.** Part of it was built after seeing winners, so it is partly circular. The pre-set list (Elon, Trump, Zuckerberg, Obama and similar) is the honest number: 11.5%.
- **Mixed:** money (Group B adj 1.68 but down in 11 of 22 channels), personal story (up overall, down in Group B).
- **Not proven:** tech meets everyday life. n=89, and the interval runs 2.4% to 12.5%.
- **Medians are flat** (0.9x to 1.35x for every bucket). Topic moves the chance of a breakout, not the typical Short.
- **Rules are crude.** On 80 random titles, a person agreed with the code's main bucket on 53 (66%). Treat this as a strong lead, not proof.
- Earlier work on 6,300 Shorts from 75 channels found the same order: famous person top (16.2%), AI and tech bottom (3.9%).
- A separate long-form study found news at 6% breakouts and cost, free, local and limits angles at 26%. That is long form, so it supports this but does not prove it for Shorts. Raw data not included.

### Moment study (judged, transcripts, correlation only)

Data: 51 podcast Shorts with transcripts. 38 at 10x+ the channel median, 13 below. One coder (Claude), not blind to the multiples, so expect some bias toward the winners. Raw codes not included.

| Trait | 10x+ (n=38) | Under 10x (n=13) |
|---|---|---|
| Topic clear by 5 s | 38 | 7 |
| Has a turn | 35 | 1 |
| Needs earlier context | 1 | 5 |
| Ends on a finished line | 33 | 6 |
| Ends on a joke exactly | 11 | 3 |
| Ends weak, mid-thought or on a call to action | 4 | 7 |
| Payoff at the end (a reveal) | 15 | 1 |
| Payoffs spread through | 19 | 7 |
| Answer first, then proof | 6 | 3 |
| Opens on a real question | 15 | 0 |
| Opens on a famous-name story | 6 | 0 |
| Opens on news | 3 | 4 |
| Everyday object or own stakes | 21 | 2 |
| Household name in it | 18 | 3 |
| Pure AI tool or AI news | 5 | 4 |

- Beats: median 4 in winners, 3 in the rest. Length: 59.5 s against 67 s. About one beat every 17.5 s.
- "Finished" matters more than "funny": only 11 of 38 winners end on a joke, but 33 end on a finished line.
- Context: 37 of 38 winners need nothing from earlier in the episode. This is the cheapest test you have.

### Limits

- Titles are not clips. A title is written after the clip is cut, so a good title can follow a good clip, not cause it.
- Channel style, guest fame and timing all sit behind these numbers. Nothing here is proven cause.
- Small judged sample (51), one coder, not blind.
- The finder's weights are judgement, set from the tables above. Re-tune them after 3 to 4 episodes of your own results: log each Short's score and its 7-day multiple, then check which tests predicted it.

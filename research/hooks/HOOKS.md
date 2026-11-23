# The hook system

Each Short has two hooks. The **spoken hook** is the first sentence said. The **written hook** is the title on screen and in the feed.

**Measured** = counted by code. **Judged** = read by Claude. Every number has its n. All of it is correlation, not proof. Most channels in the data cover tech and business, so re-test in another niche (see `../README.md`).

## The honest headline

- The hook is a floor, not a lift. A clean hook stops a loss. It does not make a winner on its own.
- Proof: real titles were scored with `hookcheck.py`. Full-marks titles hit 5x+ at 8.8% (n=499). The rest hit 7.8% (n=4,681). Spoken scores: winners 8.20/11, controls 7.98/11 (n=64 each).
- So the topic and the story carry most of the weight. The rules below remove known-bad choices and stack small edges.

## Where the data came from

| set | what | n |
|---|---|---|
| Titles | YouTube Shorts 3-90 days old, 54 podcast channels with 8+ Shorts. Multiple = views / that channel's median. | 5,180 (408 winners at 5x+, 2,737 controls at 1x or less) |
| Titles, Group B | remote or two-host tech shows | 2,306 (127 winners, 1,231 controls) |
| Spoken | first 8 s of audio, local whisper small.en. 64 winners + 64 controls from the same 30 channels (44 + 44 Group B). | 128 |
| Spoken check set | 31 deconstructed top Shorts + 25 caption transcripts (mostly winners) | 51 |

A slightly different filter gives 5,236 Shorts (used in `../LENGTH.md`). The study scripts and raw data are not included.

## What wins: written hook (measured)

1. **A number in the title.** Winners 25.5% against controls 18.3%. 5x+ rate 10.0% with a number (n=1,040) against 7.3% without (n=4,140). Higher in 22 of 31 channels, lower in 9.
2. **A named person, brand or place.** All: 52.5% against 48.1%. Group B: 69.3% against 58.1%, higher in 11 of 13 channels. Group B 5x+ rate 6.3% with a name against 4.3% without.
3. **Name and number stack.** 5x+ rate by how many of the two a title has: 0 = 6.9%, 1 = 8.2%, 2 = 10.1%. Group B: 4.0%, 5.9%, 7.5%. This is the cleanest title signal found.
4. **A concrete, picturable noun.** 70.1% against 62.9%. Higher in 25 of 31 channels.
5. **Short.** 5-7 words has the best 5x+ rate (8.9%, n=2,185). 11-14 words is worst (5.3%, n=715). Group B is flat (5.0 to 5.7%).
6. **No edge, or a small loss:** "you/your" (15.2% against 18.1%, 5x+ rate 7.1% against 8.0%), time words like "today" or "now" (4.7% against 5.9%; Group B 3.1% against 6.7%), questions (16.9% against 14.8%), threat words (22.8% against 23.0%), one SHOUTED word (14.0% against 14.4%), emoji (Group B 13.4% against 14.8%).
7. **"X vs Y" is not a loser in the data.** 5x+ rate 20% (n=60, 12 winners). But the winners put a price or a famous name on both sides ("$465 Fake Watch vs $205,000 Rolex", 6.9x). The losers use abstract sides ("Gross Profit VS Net Profit", 0.4x; "Speed vs. Intelligence", 0.8x). The bare label stays banned. That is taste (judged), not the data.

## What wins: spoken hook

Measured by code on the 128 first sentences, judged blind (set hidden) for type:

| first sentence type (judged) | winners (n=64) | controls (n=64) |
|---|---|---|
| story already moving ("one of the board members approached me...") | 25% | 12% |
| question | 20% | 16% |
| flat claim or news fact | 27% | 39% |
| throat-clearing or warm-up | 17% | 25% |
| fragment cut mid-thought | 11% | 8% |

- **Two-host studio shows (Group A, n=20 + 20):** winners throat-clear 5% against 25%. Story or question 75% against 35%.
- **Remote tech shows (Group B, n=44 + 44): no difference.** Throat-clear 23% against 25%. Start on the thing 64% against 64%. For shows like these, a clean first line is the norm, not the edge.
- **Shorter first sentence.** Median 13 words against 15. Group B 12.5 against 17. (measured)
- **Questions win in the check set.** 32% of 10x+ Shorts open on a question, against 8% under 10x (n=38 and 13). The earlier deconstruct found 7/15 against 0/6 (judged).
- **Speak from frame 0.** Speech starts at 0.06 s and says 11 words in 0 to 3 s (deconstruct, n=30). Reels: 10 words in 0 to 3 s (n=55).
- Opening by naming the co-host was too rare to measure (1 in 128). It is banned anyway, because a stranger does not know who that is.

## Spoken-hook rules

1. Start on the thing. A question, a story already moving, or the hard fact. Not the run-up to it.
2. Cut every throat-clear word: "So", "And", "Okay", "Look", "I think", "I'm telling you right now". If the story starts after "So", cut the "So". The 756x Short ("So one of the board members approached me...") would read better without it.
3. Prefer a question or a story in motion over a flat claim. Flat claims were more common in controls (39% against 27%).
4. Put a concrete thing (number, name, object) in the first 8 words.
5. Keep the first sentence to 4-18 words, about 1 to 4.5 s.
6. No hedges in the first sentence ("probably", "maybe", "kind of").
7. Never open on the co-host's name or "guys".
8. A cold open from later in the clip is fine. Use the best line, then roll from the start.

## Written-hook rules

1. 3-7 words. Two lines of about 22 characters at most.
2. Put in a number, a name, or both. Both is best.
3. Make it a sentence or a question. It needs a verb. A noun label is not a hook.
4. Name the thing on screen. A picturable noun, not an idea.
5. One highlight span, 1-4 words, one continuous run.
6. Say something the spoken line does not. Do not repeat it word for word.
7. Every word must be true and checkable. "Suspected" stays "suspected".
8. No "you/your" as the hook, no time filler, no emoji.

## Written-hook templates (real winners from the data)

These are public titles from the study. Use the shape, not the words.

1. **[Name] [did a surprising thing]**
   - "Toto Wolff turned down his job at Mercedes F1" (Cheeky Pint, 756.4x)
   - "Air Force Just Schooled a Navy SEAL 😂" (Shawn Ryan Show, 25.6x)
   - "Sam Altman Gave Up. His AI Agent Didn't" (Every, 10.9x)
2. **[Name]: [their claim, in their words]**
   - "Rocket Lab CEO Peter Beck: aliens might not be bodies, they're signals" (Sourcery, 154.9x)
   - "Tom Lee: Ethereum Could "Easily" Top $10,000" (Bankless, 41.4x)
   - "Jay Leno: "The Middle Class Is Dead"" (TBPN, 13.2x)
3. **[Thing] is not [what you expect]**
   - "Mercedes F1 doesn't have superstars" (Cheeky Pint, 155.8x)
   - "“Kanye West Was NOT A Billionaire!”" (The Iced Coffee Hour, 14.1x)
   - ""Watches Are NOT Investments!"" (Iced Coffee Hour Clips, 11.4x)
4. **Why / How [a specific thing] [does something odd]**
   - "How Much AI Does Google Use to Write Its Code?" (Big Technology, 33.6x)
   - "Why Sushi Restaurants Are So Profitable" (Iced Coffee Hour Clips, 29.6x)
   - "Why Google Paid $10 Million for Spirit Airlines Employees' Emails and Slack Messages" (Hard Fork, 11.2x)
5. **[Money or number] + [an odd object]**
   - "Sir Peter Beck on the $10M printer that builds a full rocket engine in one piece" (Sourcery, 223.2x)
   - "He made $1.8 million by selling a trash franchise" (My First Million, 17.3x)
   - "David Dobrik Pays $15k/Month for an EMPTY Shop" (Iced Coffee Hour Clips, 13.3x)
6. **Scale clash: a small number against a big one**
   - "SPOT A PSYCHOPATH IN FIVE SECONDS" (Diary of a CEO, 22.3x)
   - "16 SEALs Were Sent Into a City of 80,000 in Iraq 😳" (Shawn Ryan Show, 19.6x)
   - "10 Years Of Therapy In One Minute" (Modern Wisdom, 18.6x)
7. **The scam, exposed**
   - "The SpaceX Investment SCAM" (Iced Coffee Hour Clips, 25.5x)
   - "The High-Speed Rail Scam Just Got EXPOSED" (Valuetainment, 20.5x)
   - "Watch Expert EXPOSES Rick Ross's Fake Watch" (Iced Coffee Hour Clips, 16.3x)
8. **The unfinished line**
   - "Jensen's Master Plan Is Finally Here..." (This Week in Startups, 35.3x)
   - "Pound for pounds - the most dangerous animal is..." (Flagrant, 31.6x)
   - "You Need To Get More Violent...." (Alex Hormozi, 18.1x)
9. **The viewer's own question, in quotes** (one channel only: Alex Hormozi. Use for advice clips, not news.)
   - "“Why Do My Employees Leave?”" (109.2x)
   - "“Am I In The Wrong Business?”" (33.3x)
   - "“Should I Fire Them?”" (20.8x)

Patterns are judged from the top 60 winners. 13 of those 60 are Alex Hormozi, so channel style is mixed in. The coded versions of patterns 1 to 3 showed little lift on their own ("Name: claim" 4.2% against 3.9%). The number and the name do the work.

## Banned list

**Spoken openers**

- "So", "And", "But", "Okay", "Alright", "Well", "Look", "Listen", "Honestly", "Basically", "Like"
- "I think", "I mean", "I guess", "I feel like", "You know", "Here's the thing", "Let me tell you", "I'm telling you (right now)"
- The co-host's name or "Guys" in the first 8 words
- Hype with no thing in it: "This is the craziest thing I've seen", "I have a couple of things we need to talk about"
- Greetings: "Hello, welcome back"

**Written titles**

- Bare "X vs Y" labels with abstract sides ("Speed vs. Intelligence")
- "What X looks like"
- A bare noun label with no verb
- Vague nouns as the subject: truth, secret, mindset, journey, game changer, the future of X
- Time filler: today, now, this week, finally
- Emoji, all caps titles, and "you/your" as the hook
- Any word the source does not support

Add your own to `show.banned_words` in `brand/brand.json`.

## Scoring checklist

Run the script part:

```bash
python3 research/hooks/hookcheck.py --spoken "Can a toaster spy on you?" --title "Regulators probe [50,000 smart toasters]"
```

That example is made up. It only shows the format.

**Spoken (script, max 11):** S1 no throat-clear (3). S2 no co-host name or "guys" in the first 8 words (2). S3 opens on a question (2). S4 concrete thing in the first 8 words (1). S5 no hedge (1). S6 4-18 words (1). S7 no co-host name anywhere (1).

**Written (script, max 20):** W1 3-7 words (2). W2 fits 2 lines of 22 characters (2). W3 number or name (3). W4 concrete noun (2). W5 has a verb or "?" (3). W6 no "vs" label or "what X looks like" (3). W7 no vague noun (1). W8 one highlight span of 1-4 words (2). W9 no time filler or emoji (1). W10 not all caps (1).

**By eye (max 5, one point each):**

- M1 Is every word true, with a named source?
- M2 Does the title name what is on screen in the first 2 s?
- M3 Would a stranger who has never heard of your show care?
- M4 Does the title add something the spoken line does not?
- M5 Is the first line a question or a story already moving?

**Max 36. Ship gate:** spoken 9+, title 18+, and M1 = yes. M1 = no is a hard fail at any score.

## Keep it useful over time

1. For every new Short, score both hooks before render. Save the line, title and score next to the clip.
2. Once you have 30+ of your own Shorts with multiples, check if high scores beat low scores on your channel. If they do not, drop the rule that fails.
3. Change a rule only when new data moves it in 2 of 3 views: all channels, your closest group of shows, and the count inside channels.

## Limits

- Titles stand in for the written hook. Only 9 of 21 deconstructed two-person Shorts used a separate title card (`../deconstruct/FINDINGS.md`).
- `hookcheck.py` S3 rewards any question, even a warm-up like "How about this one?". Check it by eye.
- Feature detection is word lists. Name detection was about 85% right on a 40-title spot check. Add names from your niche to `features.py`.
- The spoken sample is small (64 + 64). Whisper drops some "um"s, so throat-clearing is under-counted in both sets.
- Big channels dominate the winners (Alex Hormozi has 13 of the top 60). The within-channel counts guard against this, but only partly.
- YouTube views roughly doubled from late August 2026. 1,377 of 5,180 Shorts (and 120 of 408 winners) are older than that, so some old Shorts look bigger or smaller than they are. Titles are compared on the same mix in both groups, so the bias is small, but it is there. One separate check found the change hit long form only, so the effect on Shorts may be smaller. Not settled.

## Files

- `features.py`: word lists and feature rules. `hookcheck.py`: the scorer.

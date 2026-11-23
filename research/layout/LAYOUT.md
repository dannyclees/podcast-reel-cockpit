# The layout mix

Question: is one frame for the whole Short (a person at the bottom, graphics on top) best practice? No.

## What top podcast Shorts do

Source: the frame-by-frame study of 31 top podcast Shorts in `../deconstruct` (14 public channels, including My First Million, All-In, Diary of a CEO, TBPN, Hard Fork, Dwarkesh), measured again for layout. Winners = 10x or more their channel's median Short (n=22). Others = under 10x (n=9). Script and raw data are not included.

| what | winners | others |
|---|---|---|
| layouts used per Short (5% of time or more) | 3 | 2 |
| layout changes per 10 s | 1.38 (one every 7 s or so) | 0.75 (one every 13 s or so) |
| median time in one layout before it changes | 4.3 s | 8.3 s |
| Shorts with real images or footage | 14 of 22 | 4 of 9 |
| Shorts with real images and motion graphics | 12 of 22 | not counted |
| time with no face (full-screen picture) | 13% | 6% |
| picture-top, face-bottom split as main layout | 3 of 22 (TWiST, Hard Fork, TBPN) | not counted |

In plain words:

1. Winners change the frame often and use about 3 different frames.
2. Most winners mix real pictures and motion graphics. Real pictures means the real person, product, place, or footage of the event.
3. The picture-top split is real (TWiST 36.9x, Hard Fork 17.4x, TBPN 14.2x), but it is one layout in the mix, not the whole Short.
4. The biggest winners (My First Million 79x, All-In 34x) put the picture full screen for 30 to 40% of the Short, with the voice over it.

Web: no independent study of layout mix was found. Creator blogs say "change something every 3 to 5 s" (gofaceless.ai, socialync.io) and "picture every noun" (quso.ai, rizzle.com), but give no data.

Limits: top Shorts only, and channel style is mixed in. This shows what winners do, not proven cause.

## The mix (target for a Short of about 55 s)

| code | frame | when | share |
|---|---|---|---|
| SPLIT-MG | motion graphic top, speaker bottom | explaining a number, an idea, a process | ~25% |
| SPLIT-IMG | real image or footage top, speaker bottom | a named thing is said (product, person, place, headline event) | ~15% |
| FULL-FACE | speaker full screen | opinion, joke, punchline, strong emotion | ~30% |
| FULL-PIC | real image, footage or motion graphic full screen, voice over it | the big reveal, the "look at this" moment | ~15 to 20% |
| LISTENER | the other person top, speaker bottom | only a real reaction, question or push-back (R79) | 0 to 10% |

The shares are a target set from the data and from review, not a measured optimum. A solo show drops LISTENER and gives its share to FULL-PIC.

Rules for the mix (R118):

- At least 3 of the 5 frames in every Short. Change about every 4 to 7 s. No frame runs longer than about 8 s.
- Not the same frame with only a new picture swapped in for more than 2 swaps in a row.
- Real images: at least 2 per Short when the clip names a real thing. About 1 real image for every 1 to 2 motion graphics (R117).
- A real image needs a real thing (R107: no generic stock).

How to use real images well:

- Full bleed or a clean crop, moving (slow push or pan), never a still that sits there.
- No text on top. No labels, no paragraph cards, no credit lines on screen. Keep credits in your source log.
- Grade it to sit with your look. A soft vignette is fine. No borders, no pins.
- Good sources: official product shots and press pages, Wikimedia, news footage of the event, the episode's own screen share. You own the rights question for each one. Fair use is not assumed.

## Example: a 55 s Short

| time | frame | what is on screen |
|---|---|---|
| 0.0 to 3.4 | SPLIT (seam opener) | title on the seam, hero picture top |
| 3.4 to 8 | FULL-FACE | the hook line |
| 8 to 14 | SPLIT-MG | the number drawn as it is said |
| 14 to 18 | FULL-PIC | the real product, slow push |
| 18 to 24 | FULL-FACE | the opinion |
| 24 to 30 | SPLIT-IMG | the real person or place |
| 30 to 32 | LISTENER | the other host laughs or pushes back |
| 32 to 40 | FULL-PIC | full-screen motion graphic, the payoff |
| 40 to 47 | SPLIT-MG | the "so what" |
| 47 to 55 | FULL-FACE | the punchline, then the end card |

Renderer: `pipeline/short.py` layouts are `"full"` (face), `"split"` (picture top, speaker bottom, with a `duo` media for a listener) and `"pic"` (FULL-PIC: the top panel grows over the whole 1080x1920, and captions move down).

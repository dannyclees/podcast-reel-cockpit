# The motion style

This is the method behind every motion graphic in a Short. It has a beat sheet per sentence. Every graphic shows exactly what is being said and lands on its word. Graphics grow out of each other. Only real assets are used. The look comes from `brand/brand.json`, and the method stays the same for every show.

## The look comes from tokens

Never hard-code a colour or a font. `setup/build_brand.py` writes `motion/kit/brand.css`, and the kit reads it.

- **Ground:** `var(--ground)` with your texture on it (`kit/img/ground.jpg`), plus film grain flickering at 15 fps (`kit/img/grain_0..3.png`). The ground breathes: scale 1.06 to 1 over the run. The middle stays quiet so the graphic reads.
- **Ink:** `var(--on-ground)`. **Accent:** `var(--accent)` only, one highlight per frame (R111). **Alarm:** `var(--alarm)`, only for "wrong", "flawed" or "not true".
- **Type:** `var(--font-display)` for big words and numbers. `var(--font-body)` at 800 for labels. `var(--font-body)` at 700, letter-spaced, in the accent for a kicker.
- **Blocks:** paper tiles `var(--paper)` with `var(--on-paper)` text (cards, logos), or dark tiles `var(--panel)` with `var(--on-panel)` text (meters, data). Radius 24 to 40.
- **Light or dark:** your ground may be light. Shadows and glows must work on both. Check by eye.

## The signature move

`motion.signature` in brand.json names your signature move, and `motion.energy` sets how hard it lands. `K.drop` plays it. The default, `stack`: a block falls, squashes on landing, springs back, then an accent layer slides out from under it, 16 px down and right.

Keep the layered version for one hero moment and the end card. Do not put an accent layer on every card (R100, R111).

## The 5 frame types

1. **Highlight text:** 1 to 3 big words in display type. Each lands on its spoken word. The key word gets the accent marker.
2. **A-roll:** the speaker full screen. Use for opinions and reactions (R79). No graphic.
3. **B-roll:** a real photo, screenshot or clip inside a block (cover fit, slow push), or the real screen share cut in time. Also full screen, FULL-PIC, with no text on it (R117, R118). Mix and targets are in `research/layout/LAYOUT.md`.
4. **Logos:** the real mark on a paper tile, dropped on the name (R82). Versus, row, or tiers when the claim is about rank. You own the rights question.
5. **Explainer:** bars, meters, slots, counters, arrows, crosses. They draw the claim (R81), never just its nouns.

## Timing rules

- A run is one comp and one mp4, placed on the Short's clock from its first word. Inside, `c(src)` is the word's start minus one frame. A beat lands on its word, never late. Target: 0 to 2 frames early.
- The first thing in a run lands within 0.5 s of its cut (R77). A run never opens on an empty ground.
- One scene leaves in 0.16 s (lift + fade) as the next one lands. Nothing leaves the panel empty (R78).
- Labels: at most 3 words and 1 number on screen at once (the said words of a highlight frame count).
- Facts only (R80): no invented figures. Use a meter with no digits when the real number is not known. A guess is drawn as a question.

## Safe area

- In a run (1080 x 960, the top half of a split): keep to x 120 to 960 and y 250 down (R110, R113). The caption sits on the seam around y 960. During a title opener, keep the hero above y 780.
- On the full frame (1080 x 1920): the safe box is (120, 250) to (960, 1800). Also nothing in the right 140 px of the bottom half (R110).
- The ground fills every pixel, edge to edge (R97). Vary it through the Short (R112).

## The eye test

`motion/tools/gate.py` measures what code can measure. These questions cover meaning and taste. Look at frames from `motion/tools/look.py`. YES is good. A borderline scene is a NO. Answer as a viewer on a phone. If you have to explain why it works, it is a NO. J1 to J18 are referred to by code comments.

| # | Question |
|---|---|
| J1 | **One hero.** Is the screen one cohesive visual that fills its panel, not panels piled up or a small card floating in empty space? |
| J2 | **Real, not placeholder.** Are logos, UI and footage real, never grey bars, wireframes or a generic stand-in? |
| J3 | **Show, don't echo.** Does the graphic show the idea, instead of typing the word just said or adding a label chip? Big centred words of the speech are the one exception. |
| J4 | **No cliches.** Is it free of crossed-out icons, restart arrows used as a metaphor, sparkle stars and generic glowing orbs? |
| J5 | **Pointers point.** Does every arrow, cursor, line or ring touch the exact thing it is about? |
| J6 | **It does something.** Does the visual change, reveal or pay off during the speech, not just sit there? |
| J7 | **Calm proof.** Are numbers and credentials one clean visual, not chips, stamps, avatar rings or a busy count-up? |
| J8 | **Progress is a picture.** Is a sequence shown as something moving (a track filling, bars rising), not a text counter? |
| J9 | **Your colours.** Is the accent used as a real highlight, with real logo colours, never grey on grey? |
| J10 | **Room to breathe.** Is there clear space around every element, with nothing jammed against an edge and captions clear of graphics? |
| J11 | **Type.** At most 3 words per graphic, only your brand fonts, headlines centred? |
| J12 | **Calm camera.** Does the speaker's picture hold still, with no punch-ins or fast zooms, and every jump cut covered? |
| J13 | **The face.** Is the speaker's face visible and engaged whenever they are on screen, never covered? |
| J14 | **Means something, follows the voice.** Does the graphic match what is said at that moment and land on its word? |
| J15 | **Ship it.** Would a design studio ship this frame? Does it belong with the frames before and after? |
| J16 | **Continuity.** Does each graphic grow out of the one before, rather than a hard cut to something unrelated? |
| J17 | **One ground.** Is every graphic on your ground and your texture, never full-screen colour blocks? |
| J18 | **Concrete example.** Does the graphic show a real, specific example instead of an abstract label or a row of icon tiles? |

Score composition, motion, type, colour and idea from 1 to 10. Fix the worst 3. Repeat until every score is 9 or more.

## Files

- `kit/kit.css`, `kit/kit.js`: ground, blocks, drop, words and marker, news card, bars, meters, svg draw.
- `beats/<id>.md`: the beat sheet a person reads. `beats/<id>.json`: segments and runs for `build.py`.
- `comps/<id>/<run>.js`: the beats of one run. `build.py <id> --render --spec` renders `mgs_<run>.mp4` into the clip folder and writes the `short.py` spec.
- `../motion-library/`: finished treatments to reuse before you invent a new one (R103).

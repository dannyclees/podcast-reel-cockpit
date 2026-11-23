# The rules

These rules run the whole system. There are 125 of them, R1 to R125. Each one came from a real note on a real Short, or from the research. The numbers stay fixed, because code comments refer to them. They are grouped by subject, so they are not in number order. Search for "R77" to find one.

Your own rules start at R200 in `rules/MY-RULES.md`.

## The law: every note becomes a rule

A note from the owner is never a one-off fix. The same day, it becomes three things (R19, R84):

1. **A rule.** The next free number from R200, as a plain testable instruction, in `rules/MY-RULES.md`.
2. **A gate, where code can measure it.** If a machine can check it, a machine checks it from now on.
3. **A check for clashes.** If it clashes with an older rule, say so. Settle it with outlier data, not with taste.

Type `/shorts-rule` and give the note. Claude does all three and tells you what changed.

## Rights: read this once

You are responsible for the rights to every clip, photo, logo, font and piece of music you use. Fair use is not assumed anywhere in this system. Where a rule says "show the real thing", it means "show the real thing that you have the right to show". If you do not have the right, use a motion graphic. This is not legal advice. Ask a lawyer if you are unsure.

## The 20 that matter most

These are the mistakes that came back again and again.

1. **R1** One continuous passage. No joins.
2. **R120** A whole thought at both ends. Never start or stop mid-thought.
3. **R50** Pick clips with the scoring system, not by feel.
4. **R51** The first words are the strongest line in the clip.
5. **R71** A stranger gets the title in one glance.
6. **R21** Frame 0 is a human face. **R22** The first word is heard within 0.15 s.
7. **R9** Text never touches a face. **R60** Hair counts as head.
8. **R38** Never cut off a head. **R34** Never squash a face.
9. **R59** Sync is proven inside every render. A fail is never shown.
10. **R68** Calm captions: one phrase, one place. **R76** One line only.
11. **R20** Captions land on the word.
12. **R118** Change the frame every 4 to 7 s. At least 3 frame types.
13. **R104** A motion graphic for every section. **R77** It lands at once.
14. **R81** The graphic draws the claim, not only its nouns. **R25** It must add something.
15. **R117** Real images of the real thing. **R107** Never generic stock.
16. **R80** Facts only on screen. No guesses.
17. **R110, R113** Keep everything inside the safe box. Platform UI covers the rest.
18. **R111** The accent colour is one highlight per frame, not a fill.
19. **R102** Never show unchecked work.
20. **R123, R124, R125** One booking per platform. Each Short has its own time. Every re-edit has a note.

## How to read a rule

Each rule has the instruction, a short **Why**, and a **Check**. The Check says what enforces it:

- **framecheck**: `pipeline/framecheck.py`, reads every frame of the final file with Apple Vision.
- **contentcheck**: `pipeline/contentcheck.py`, reads the words and the spec. `publish.py` runs it first.
- **motion gate**: `motion/tools/gate.py`, on each rendered motion run.
- **short.py**: `pipeline/short.py`, checks done inside the render.
- **publish.py**: `app-sync/publish.py`, refuses before upload.
- **app server**: `app/api/post.js`, refuses or adjusts when booking.
- **dupcheck**: `app-sync/dupcheck.py`, asks Buffer for doubles.
- **by eye**: no code can judge this. A person or Claude reads or watches it.

Every look value comes from `brand/brand.json`. "The accent colour", "your logo" and "your texture plates" always mean the values and files that come from there.

---

## Picking the clip

- **R1 One take.** A Short is one continuous passage. Trims at the start and a 2 to 3 s cold open are fine. Joins in the middle are not. **Why:** A stitched clip loses the thread. The speaker says one sentence, and the rest of the thought is gone. **Check:** by eye, gate G2 in `research/selection/SELECTION.md`.
- **R2 Strong first line.** Cut all filler at the start. The first words are the shocking thing. **Why:** A run-up like "and I said a lot of these things" loses the viewer before the story starts. **Check:** `research/hooks/hookcheck.py`, contentcheck for joining words.
- **R3 Mix of topics.** At most one Short per episode on your saturated topic (`show.saturated_topic` in brand.json). **Why:** The topic your niche is drowning in has the lowest breakout rate. In the study the saturated topic was AI and tech: 3.9% against a 7.8% average, on 6,300 Shorts. It may differ in your niche, so re-test. **Check:** by eye, section 4 of SELECTION.md.
- **R4 Cold-read test.** A fresh reader must say what the clip is about from the text alone. **Why:** Clips that need earlier context fail with strangers: 1 of 38 winners needed it, against 5 of 13 others. **Check:** by eye, gate G1 in SELECTION.md.
- **R24 Story clear by 5 s.** The core issue is in the text and in the picture by 5 s. Do the cold-read test on the first 5 s alone. **Why:** A viewer who cannot tell what the story is does not stay to find out. **Check:** by eye, gate G3 in SELECTION.md.
- **R32 Length follows the story.** There is no 60 s cap. Go up to 3 minutes when the passage is one take with a payoff every 15 to 20 s. Never pad. **Why:** 90 to 180 s Shorts broke out 2 to 3 times more often in 5,236 Shorts, but long beat short in only 10 of 20 channels. Length does not cause a win. A story that keeps paying off does. Proof in `research/LENGTH.md`. **Check:** by eye.
- **R50 Pick clips with the selection system.** Use `research/selection/SELECTION.md` and `candidates.py`: gates, then a score out of 22, ship at 17+. At most 1 Short on the saturated topic, at least 1 famous name, at least 1 everyday or body topic. **Why:** Choosing by feel picks what the host enjoyed, not what a stranger stays for. **Check:** by eye. The finder ranks. It does not decide.
- **R87 End on a finished line.** Stop on a complete sentence or punchline. Cut before the next word starts. Never end on a hand-off to the other host or on the first words of a reply. **Why:** Viewers feel it when a speaker is cut off about to start a sentence. **Check:** contentcheck.
- **R91 Cameras on first.** A clip never starts before all cameras are on. **Why:** Remote recordings can stay black for their first seconds. **Check:** framecheck catches it through R21.
- **R120 Whole thought at both ends.** A Short must not open on a joining word or mid sentence. It must not end on a hanging word, on a scrap under 4 words, with no full stop, with the speaker carrying straight on, or with the next line starting under 0.25 s later. **Why:** A clip can pass every picture gate and still make no sense at the start or the end. Code cannot judge sense, so the check also prints the opening and the ending. Read them. **Check:** contentcheck, by eye.

## Hooks and titles

- **R27 Proven hooks only.** Hook text comes from a template in `research/hooks/HOOKS.md` or a pattern from top podcasts. It must be true, with a source. No bare "X vs Y" label. **Why:** Invented hooks read as machine-made. **Check:** `research/hooks/hookcheck.py`, by eye for truth.
- **R51 Spoken hook: start in the action.** The first words are the strongest line in the clip, word for word. Often this is a cold open: a question from the host, or a number line. Then roll the story. No throat-clearing. **Why:** Story openers beat flat claims 25% to 12%, and flat claims were more common in controls (39% against 27%). **Check:** hookcheck.
- **R52 Written hook: the real headline wording.** Build the title from how the news or the top posts phrase it. A name and a number together win (10.1% hit 5x, against 6.9% with neither). Use 5 to 7 words, at most 2 lines, one continuous accent span. Use honest verbs like "suspects" or "probes" when it is not proven. **Why:** Phrasing that already spreads is proven phrasing, and overclaiming is a false statement on screen. **Check:** hookcheck, by eye for truth.
- **R71 The glance test.** A title tells a stranger what the Short is about in one glance: who or what, and what happened. A list of names with no verb fails. A claim that fails logic also fails ("run your own computer for less than a car": you already can). **Why:** A title that says nothing does nothing. **Check:** by eye.
- **R44 Hold a title card long enough to read.** At least 2.4 s. Cut on the end of a sentence. **Why:** A card that leaves too fast is not read. **Check:** by eye, spec value `hold`.
- **R70 Never text twice.** If the title card is on the middle line, the top half shows a picture, never a text card. If the top picture already carries the headline, drop the title card. **Why:** Two blocks of text compete, and neither is read. **Check:** by eye.
- **R88 Big title card.** *Replaced by R121 on line count.* Measure the title with the real font and set it as big as fits inside 840 px, up to 68 px. **Why:** Bigger titles are more legible. The old advice to use 3 lines when text is small is gone: cut words instead (R121). **Check:** short.py measures the text.
- **R121 Title: 2 lines, in the middle.** The title is 2 lines at most, on the seam card at y 820 to 960. Never in a low band at y 1450. Too long for 2 lines at a good size means cut words, not add lines. **Why:** Titles too low are not read, and titles too high hit the platform UI. **Check:** contentcheck.

## The opening

- **R5 Open on the main image.** *Narrowed by R21 and R61.* The strongest picture of the story is on screen from the first frame, with the hook laid over it like a thumbnail. Never a plain text box. **Why:** A beige text box looks machine-made. **Check:** by eye.
- **R21 Face first.** Frame 0 shows a human face: the speaker. **Why:** Viewers stop for a face. The story picture can share the frame, but it never replaces the face at frame 0. **Check:** framecheck.
- **R22 No dead air at the start.** The first word is heard within 0.15 s of frame 0. **Why:** Half a second of silence is a reason to swipe. Top Shorts start speech at a median of 0.06 s. **Check:** framecheck (0.2 s).
- **R33 Copy the proven opener, do not invent one.** *The default is now R56 and R61.* Before designing an opener, study what top shows do. The top-and-bottom split used by top interview shows has a question on the middle line and cuts to the speaker at about 3.4 s. **Why:** A proven layout beats a clever new one. **Check:** by eye.
- **R41 Show the striking picture whole.** If the picture is the hook, show all of it, readable. No zoom that hides it. **Why:** A crop can remove the reason the picture matters. **Check:** by eye.
- **R56 Default opener = the seam card.** A title card with your texture sits on the middle line, with the speaker below. The title has no filler words ("this", "a", "the" only when needed). 1 or 2 words go on the accent, never a whole line. **Why:** It puts the title, the picture and the speaker in one frame. **Check:** by eye, contentcheck for position.
- **R61 Seam opener = picture on top.** The opener shows the story picture in the top half from frame 0: a graph, a scan, a headline, a moving clip. The title card sits on the middle line and the speaker below. No idle listener on top. **Why:** A listener doing something else on top looks bad, and the picture does more work. **Check:** by eye.

## Faces and layout

- **R7 Only the speaker.** Whoever talks is on screen, half screen with a picture above, or full screen. The listener appears only for a real reaction, 1 to 2 s. No idle two-face split. **Why:** A silent face is wasted space. **Check:** by eye (split share at most 10%).
- **R8 Frame the whole face.** Never crop the top of a head or show only chin and chest. Check every face shot against the face tracker. **Why:** A face that is half covered reads as a broken edit. **Check:** framecheck.
- **R34 Never squash a face.** Every crop keeps the source aspect ratio. A split half is cropped at 1.125:1, never scaled from 2:1. **Why:** A squashed face is the first thing a viewer notices. **Check:** short.py builds panels this way, by eye.
- **R38 Never cut a head.** Cut every panel from the full-height frame before it reaches the page or render. Never let CSS `object-fit` crop a face. **Why:** A head off the screen can never ship. **Check:** framecheck fails a head cut off by the frame or the split line for 0.2 s or more.
- **R45 No hard cut into a split.** The speaker glides into the bottom half while the picture slides in from the top, in 0.75 s with an ease. Pictures always move: real footage, an image-to-video clip, or a slow drift on a real image. Never use AI motion on a medical or factual image. **Why:** A harsh cut in the middle feels cheap. AI motion on a factual image changes the facts. **Check:** short.py builds it, by eye.
- **R73 Engaged faces only.** Cut to a person only if they are engaged: eyes open, looking at the camera or the screen, not down at something else. **Why:** A person looking at their phone tells the viewer to leave. **Check:** short.py tracks eyes, pitch and gaze against that person's own normal.
- **R79 Listener only when they react.** Between pictures, the speaker is full screen. Cut to the listener in the top half only for a real reaction, a question or a push-back. Never for nodding along. **Why:** Winners show the listener more often (12 of 15 against 1 of 6), but those shots are reactions. Keeping a listener on screen all the time was tried and rejected. **Check:** by eye.
- **R85 Solo full shots: caption under the chin.** A solo camera blown up to full screen puts the face where the caption sits. Solo clips put full-layout captions at y 1720. **Why:** The caption would land on the mouth. **Check:** framecheck.
- **R114 Mix up the frame.** *Made concrete by R118.* The layout changes every few seconds. Never one layout for a whole Short. **Why:** One frame for a whole Short is visually flat. **Check:** see R118.
- **R118 The layout mix.** Five frames: SPLIT-MG (motion graphic top, speaker bottom), SPLIT-IMG (real image top, speaker bottom), FULL-FACE (speaker full screen), FULL-PIC (picture or graphic full screen, voice over it), LISTENER (other host on top, only for a reaction). Use at least 3. Change about every 4 to 7 s. No frame runs longer than about 8 s. Never more than 2 picture swaps in a row inside one split. Target shares for about 55 s: SPLIT-MG 25%, SPLIT-IMG 15%, FULL-FACE 30%, FULL-PIC 15 to 20%, LISTENER 0 to 10%. **Why:** Top podcast Shorts use 3 layouts and change every 7 s or so (median run 4.3 s). Those below 10x use 2 and change every 13 s or so. Data in `research/layout/LAYOUT.md`. **Check:** by eye. Write the layout per beat in the beat sheet and check it before render.

## Captions

- **R9 Captions never on a face.** In a split, they go on the middle line. Full screen face: below the chin. Full screen picture: lower third. **Why:** Text on a face can never ship. **Check:** framecheck, per frame against the tracked face box.
- **R10 No weak labels.** A label appears only when it adds a fact the picture cannot show. Use 1 to 3 strong words, big. **Why:** A small generic label looks weak. **Check:** by eye.
- **R20 Captions on the word.** Re-time every word to the voice. 90% of words after a pause must start within 0.12 s of the voice. **Why:** Captions half a second off feel broken, even when nobody can say why. **Check:** `pipeline/retext.py` aligns each word to the voice. Check by eye on the frame sheet.
- **R23 Frame-by-frame check.** Read every frame. A person is on screen (a full-screen graphic may hold at most 3 s). No text box touches a tracked face. Text leaves before a face moves under it. **Why:** Spot checks miss the half second that ruins a Short. **Check:** framecheck.
- **R39 Captions from the first word.** Even under a title card. **Why:** Without them, the opening looks out of sync with the voice. **Check:** by eye.
- **R40 No name arrows or labels that add nothing.** **Why:** An arrow to a host adds no information. **Check:** by eye.
- **R43 Caption look is fixed.** A rounded box (`cap_box`, radius from `caption.radius`), text in `cap_text`, the spoken word in `cap_spoken`. Do not restyle it per option. **Why:** Captions are the most seen element, and they must stay the same. **Check:** by eye. The values come from brand.json.
- **R47 Spoken word only.** *The phrase behaviour is replaced by R68.* Only the word being said is highlighted. Do not fill the phrase with colour as it plays. **Why:** A fill is busy, and a single word shows where the voice is. **Check:** by eye.
- **R53 Every spoken word gets a caption.** `pipeline/retext.py` re-transcribes the clip with whisper large-v3-turbo and force-aligns it. Stumbles the transcript cannot see are cut with `drop_times` in clips.json (source seconds). **Why:** Episode transcripts drop words, so captions skip what was said. **Check:** by eye against the sound.
- **R60 The hair is part of the head.** In a split, the caption must not sit on the head below it. Lift it with the spec key `cap_split_y` when a head is tall. **Why:** Face boxes stop at the brow, and captions landed on hair. **Check:** framecheck counts 0.6 of a face height above the brow as head.
- **R68 Calm captions.** The whole phrase (up to about 7 words) shows at once, with the spoken word highlighted, in one place: on the middle line in a split. Not 2 or 3 words jumping around. **Why:** Jumping captions are hard to watch. **Check:** by eye.
- **R76 One caption line.** A caption is one line, never two. The phrase breaks before it grows wider than the box (`CAP_MAX_W` in short.py, 860 px at 56 px). **Why:** 18 of 30 top podcast Shorts are mostly one line, and 7 of the top 10. Two lines gave no lift. `research/captions/RESULT.md`. **Check:** short.py measures it, CSS `white-space: nowrap` backs it up.
- **R86 Captions never blink.** A phrase stays up until the next one replaces it. It hides only across a pause over 1.3 s. A layout glide never hides it either: it parks on a low line (y 1800) for the 0.75 s glide, then moves to its new line. **Why:** A timing bug hid each new phrase for its first word, 25 to 30 times per Short. **Check:** framecheck fails more than 2 caption gaps of 0.4 s or less.

## Pictures and B-roll

- **R11 Picture every noun, instantly.** *Narrowed by R25: only when the picture adds something.* When a thing is named, its picture is on screen on that word. Source order: your screen share, a freely licensed photo, a generated image, then a motion graphic. **Why:** Inserts fill 40% of winners and 3% of the rest. **Check:** by eye (inserts 30 to 80%).
- **R25 The graphic test.** Three questions for every graphic. 1. Is it clear? 2. Is it beautiful, to the standard of the motion library? 3. Does it add something the words do not say: scale, proof, consequence, contrast? **Why:** A picture that only repeats the word (they say cheese, cheese appears) adds nothing. **Check:** by eye. Answer in clips.json `visuals[].why`.
- **R26 Show what they point at.** "Look at this" means the real thing on their screen, zoomed to the part they talk about and cropped to fit 9:16. Never a stand-in photo. **Why:** A stand-in breaks the moment and the trust. **Check:** by eye.
- **R29 Real A-roll and B-roll.** When a product or company is named, use its official demo or promo footage if you have the right to. Log the source. You are responsible for the rights to any clip. Fair use is not assumed. **Why:** Real footage is more convincing than anything you can draw. **Check:** by eye, source log.
- **R57 The news card.** When a claim has a real source, show the real headline word for word, with outlet and date, on a paper-colour card over your texture in the top half. The speaker goes below and the caption on the middle line. **Why:** A real headline is proof, and it looks clean. **Check:** by eye. See `{"kind": "headline"}` in the short.py spec.
- **R58 The texture behind a card moves, quietly.** `pipeline/cardbg.py`: drift, dots, edge, grain, glow, rotating through the set. A spec can pin one with `"bg"`. Never louder than the card. **Why:** A slow background keeps a held card fresh. **Check:** by eye.
- **R62 Pictures never fight.** Each new top picture fades in on top of the last. The old one is removed after it is covered. A graphic's payoff lands on the word that says it. **Why:** A later card once hid a map before its point landed. **Check:** by eye.
- **R63 Save the image, then crop it clean.** Never show a raw screenshot with browser parts, cursors or other posts. Save the picture, crop to the content, paint out cursors and icons, upscale. You are responsible for the rights to any image. Fair use is not assumed. **Why:** Extra interface looks careless and hides the point. **Check:** by eye.
- **R64 One picture, not a camera flight.** Prefer one clean image that pops in over a graphic that pans left to right. **Why:** A long pan is slow and hard to read on a phone. **Check:** by eye.
- **R72 Named thing = real B-roll.** When someone names a product, show the real thing: official footage or photos, logos, the real site. A text card is not B-roll. You are responsible for the rights to any clip, photo or logo. Fair use is not assumed. **Why:** A text card is the lazy option when the thing itself exists. **Check:** by eye.
- **R80 Facts only on screen.** Cards state the verified fact with its source. Never print a guess or an estimate. If a host says a wrong number, the card shows the right one without comment. Use a meter with no digits when the real number is not known. **Why:** A false number on screen is your false number. **Check:** by eye.
- **R81 The graphic shows what is said.** A graphic must draw the speaker's claim, not only its nouns. "Two at the top, a gulf, then everyone else" needs two logos high, an empty gap, the rest low. A row of logos side by side says the opposite. **Why:** A graphic that contradicts the words makes no sense. **Check:** by eye.
- **R82 Say the name, show the mark.** Every named company or product gets its real logo or photo on screen while it is said. Cards take inline logos with `{logo:name}`. You are responsible for the rights to any logo. Using a logo can imply a link with that company, so fair use is not assumed. **Why:** Writing only the text is lazy when the viewer could see the mark. **Check:** by eye.
- **R90 Crop by cutting the file.** Crop a screenshot still into its own image file before it goes on screen. **Why:** A crop box drawn inside the panel also shows the cut-off text around it. **Check:** by eye.
- **R98 Real faces, never person icons.** A person on screen is a real photo of a real person, or the speaker's own face. Never a generic user icon. You need the right to use the photo. **Why:** Person icons look like template slides. **Check:** by eye.
- **R99 Every chart line has a label.** Each line, bar or area carries its own name on it. No unlabelled line. **Why:** A viewer cannot pause to find out what a line means. **Check:** by eye.
- **R101 Sources first.** Before designing any graphic, research the topic: primary sources (the original article, government statement, company advisory), real photos, real news footage, real faces, real logos. Design from what you found. You are responsible for the rights to anything you use. Fair use is not assumed. **Why:** A graphic that could be on any channel is a fail. **Check:** by eye. See R122.
- **R107 No generic B-roll.** Use a photo or clip only when it shows the real thing being talked about: the real product, headline, place, person, screen, or footage of the event. Otherwise use a motion graphic. Never stock as filler. **Why:** A random photo of someone shopping helps nobody. **Check:** by eye.
- **R108 Motion graphics only.** *Photo ban lifted by R117. The rest still holds.* Show the idea as a thing that moves, never as a sentence. At most 3 words and 1 number per frame. No source or credit lines on screen (they stay in your source log). No paragraph or headline cards with long text. One connected world per Short. **Gate question:** Could this frame work with the sound off and no words? If not, redraw it. **Why:** Stills with too much text looked machine-made. **Check:** by eye.
- **R117 Real images are back, in the mix.** R108 still decides how an image looks: no text on it, no credit lines, no stock. A real image of the real thing is allowed: product, person, place, footage of the event. Each is full bleed or a clean crop, always moving (slow push or pan), graded to your look, no border, no pin, no label. Use at least 2 per Short when the clip names a real thing, and about 1 real image for every 1 to 2 motion graphics. **Why:** 14 of 22 top podcast Shorts at 10x+ use real images, against 4 of 9 below. 12 of 22 use both images and motion graphics. **Check:** by eye, `research/layout/LAYOUT.md`.
- **R122 First-hand material.** Every Short shows at least 2 first-hand items: the real chart from the paper, the real product video, the real page or post. The spec lists them in `sources` with the media key and the URL. If none exist, `sources_none` says why. Generic stock still fails R107. Note the rights for each item. You are responsible for them. Fair use is not assumed. **Why:** First-hand material is what makes a Short worth trusting. **Check:** contentcheck.

## Motion graphics

- **R12 Never a blank panel.** A graphic panel shows content from its first frame. Cut to the graphic when it starts, not before. **Why:** Seconds of empty panel feel like a mistake. **Check:** motion gate (EMPTY, LATE).
- **R13 Real motion design.** Graphics come from a curated motion library (`motion-library/`) or the motion kit, not flat icons in boxes. **Why:** Icons in boxes look weak. **Check:** by eye.
- **R14 Logos move.** A brand gets a motion treatment, not a static tile. **Why:** Static tiles do not hold attention. **Check:** by eye.
- **R66 HyperFrames needs.** An id on every video, a keyframe every second in every clip, and one start position per moving panel at 0 s. **Why:** Any of these missing gives a frozen or black video. **Check:** by eye on the render, `motion/tools/look.py`.
- **R74 Motion design is core.** Every Short has at least 2 real motion graphics, fed with the clip's own numbers and names, landing on the words. **Why:** Without them, a Short looks like a plain clip. **Check:** by eye.
- **R77 Graphics land at once.** The first picture is on screen from frame 0, and every graphic shows its subject within 0.5 s of its cut. Drop-ins, staggers and labels finish inside the first second. **Why:** Attention is short, and slow build-ups lose it. **Check:** motion gate (LATE).
- **R78 No empty panel.** A graphic holds its last state until the next picture covers it. Library exits are stripped for Shorts (`motion-library/variants.py`), and every video is padded with its last frame (`tpad` in short.py). **Why:** A graphic that left early once left 5 s of nothing. **Check:** motion gate (EMPTY).
- **R97 The ground covers every pixel.** Your texture fills the whole panel, edge to edge. A grey or empty strip at any edge is a fail. Use a texture image bigger than the panel (cover, never contain). **Why:** A strip at the edge is the first sign of a broken render. **Check:** by eye. Look at the outer 12 px on every graphic frame.
- **R100 No borders, no outlines, no pins.** Cards and photos sit clean on the ground. No accent outline or offset layer on every card, no map pins, no small icon tiles as decoration. Crops never cut text. **Why:** Decoration on every card turns into noise. **Check:** by eye.
- **R103 The bar.** One connected world per run. A hero visual per sentence, big and readable. Real assets. Graphics grow out of each other. Every beat on its word. Reuse the liked pieces in `motion-library` before inventing new ones. **Why:** A clear bar stops the slow slide to "good enough". The full eye test is in `motion/STYLE.md`. **Check:** by eye.
- **R104 A motion graphic for every section.** Every split stretch of a Short is a motion run (`motion/`, skill `shorts-motion`): your ground, your accent, your display type. Each beat lands on its word, one frame early. The run grows out of itself. The speaker goes full screen only for opinions and reactions. **Why:** Motion in every section is what lifts a clip above a captioned webcam. **Check:** motion gate (EMPTY, LATE, EDGE, SMALL), eye test.
- **R105 Show failure, never cross it out.** "Flawed", "wrong", or "not true" is drawn as the thing breaking (`K.crack`), falling off (`K.fall`), or a picture that proves it. Never a red X, a strike-through, a stamp or a restart arrow. Label pills are out. Only the said words as a centred line. **Why:** Crossed-out icons are a cliche of machine-made motion, and they explain nothing. **Check:** by eye.
- **R111 The accent is a highlight, not a frame.** No accent borders, offset layers, panels or fills behind objects. The accent is for one highlight per frame: a word marker, a tick, a pulse. Objects sit straight on your texture with a soft shadow. **Why:** When the accent is everywhere, it highlights nothing. **Check:** by eye.
- **R112 Vary the texture.** Each Short uses at least 3 grounds from `brand/textures` (`tall_a`, `tall_b`, `g1` to `g5`, at different crops, angles and scales). The ground changes with each new section by a slow cross-fade or a pan, never a hard flash. Two Shorts in a row never open on the same crop. **Why:** The same ground on every page looks samey. **Check:** by eye.
- **R116 Graphics step up.** When a new gate lands, older renders are below the bar. Rebuild them in the current look before they go to review again. **Why:** Older renders may predate the sync gates, too. **Check:** by eye.

### Motion library notes

Verdicts from reviews of the treatments in `motion-library/`:

- Strongest: stack-drop (it has weight), logo-plug, scale-reveal, map-drop, age-shrink.
- Fine, but can improve: chain-flight, year-tape. In scale-reveal, keep the number label clear of the picture.
- Unsure: split-flap. Rejected: glitch-slam.

## The safe area

- **R110 Top dead zone.** Nothing that matters may sit in the top 250 px of the 1080x1920 frame, or in the right 140 px of the bottom half. Only texture and soft motion can live there. **Why:** Instagram and TikTok draw their own UI there. A logo placed in that zone cannot be seen. **Check:** by eye. Draw the safe box on a frame from every beat.
- **R113 Side safe margins.** Every word, number, logo, chip and hero object stays inside x = 120 to 960. Captions too. The full safe box is (120, 250) to (960, 1800). **Why:** Tall phones crop about 9% off each side, around 100 px. Words have lost their last letter this way on a live post. **Check:** by eye before every post.

## Sound and sync

- **R16 Voice.** Use the raw mic WAV, optionally cleaned by a voice service such as Auphonic. Never the compressed audio inside a video file. **Why:** Video-file audio is low bitrate and sounds dull. **Check:** `pipeline/align_audio.py`, R119.
- **R17 Music is a test.** Every Short ships clean, and with music and sound effects if you have licensed music. **Why:** Whether music helps depends on the show, and you only learn by comparing. Music beds appear in 8 of 15 winners and 0 of 6 others, but channel style is mixed in. **Check:** by eye. You bring and own the music.
- **R37 Lips in sync.** `pipeline/lipsync.py` measures each person's mouth against their own voice and writes `video_offset` to work/tracks.json. `cut.py` shifts that person's picture. **Why:** Remote tools line up the voices, not the webcams. One camera ran 8 frames late. **Check:** framecheck on the final, within 2 frames when the mouth signal is strong enough (r at least 0.25).
- **R55 The sound belongs to this cut.** Rebuild the clean voice whenever the cut changes, then prove it: same length, and 0 ms lag against voice.wav. **Why:** A stale voice file from an older cut was once muxed under every new picture. **Check:** short.py.
- **R59 Sync is proven inside every render.** short.py checks the final file: sound 0 +-20 ms against this cut's voice, picture frame-matched to the speaker panel (0 +-1 frame). "SYNC FAIL" means it is never shown. **Why:** Sync errors are the one thing a viewer cannot forgive. **Check:** short.py.
- **R65 Music is a steady bed.** About 21 dB under the voice with gentle ducking (2:1), never pumping in and out. **Why:** Music that fades in and out on each pause is distracting. Top Shorts sit about 16.6 dB under. Pick what sounds right, but keep it steady. **Check:** `pipeline/music_mix.py` defaults.
- **R89 Music: three tracks to pick from.** Every Short gets the no-music cut plus up to three beds from `brand/music` (`music` in brand.json), switchable in the app while the video plays. The chosen track is saved with the approval. **Why:** Picking is faster than re-rendering. **Check:** app. If you have no music, the no-music cut stands alone.
- **R92 The voice stays bright.** After cleaning, compare the voice's 2 to 5 kHz band with the raw mic on the same 30 s. A drop of more than about 1.5 dB means check by ear. **Why:** In one test a cleaning service dropped 3.9 dB at 2 to 5 kHz, and the voice measured dull. The host listened and still preferred the cleaned sound. The ear wins. The number is a warning, not a gate. **Check:** by ear.
- **R106 SFX live in a stem, and the app switches them.** The final mp4 stays clean (voice + end click). short.py writes `<out>_sfxstem.wav` (a gentle whoosh on each layout change + the spec's `"sfx"` list). `music_mix.py <final> <track|none> <out> --sfx <stem>` makes `<id>_sfx.m4a` and `<id>_t1..t3_sfx.m4a`. Sounds that are -20 LUFS events need a gain of about -6 dB to land about 16 dB under the voice. -22 dB was inaudible. **Why:** Keeping SFX separate lets you switch them without a re-render. **Check:** by ear. Measure again if you change the sounds.
- **R119 Mic files are aligned before anything else.** Run `pipeline/align_audio.py` before transcribe. Every speaker's audio in work/tracks.json must be in work/audio_hq/. **Why:** Raw mic WAVs can start about 5 s away from the video. Skipping this step put one episode's picture 5 s off the voice. A weak lipsync match on every window (r under 0.15) means stop and check alignment. It does not mean "in sync". **Check:** the `/shorts` skill stops here, and `lipsync.py` reports r.

## Recording and picture quality

- **R93 Source quality ceiling.** You cannot download better than what was recorded. For crisper pictures, record at 1080p or 4K and check your plan and camera settings before the episode. **Why:** A 720p webcam stays a 720p webcam, whatever you do later. **Check:** `ffprobe` on the raw files.
- **R94 Transitions: off by default.** Plain hard cuts. A transition goes at a section change only, never between two speakers. **Why:** Most of 30 top podcast Shorts use only hard cuts. About 1 in 4 use a flash or light leak, and only at a section change. No transition files are included: bring your own, with rights. **Check:** by eye (no shot under 0.9 s), by eye.
- **R95 Colour grade on every speaker video.** A base fix is measured per camera (`pipeline/grade.py`: white balance, exposure, gentle contrast, light denoise and unsharp for 720p webcams). You can add your own LUT with `grade.lut` at `grade.lut_strength` in brand.json. Apply it after cut.py, and keep the originals as `*_ungraded.mp4`. The frame count must not change. Re-run after any re-cut. **Why:** Webcams from two people never match. **Check:** frame count, by eye.

## Brand

Same structure and timing for every show. All values come from `brand/brand.json`.

- **R6 No show name as typed text.** Use your logo, or nothing. **Why:** The show name typed out looks like a placeholder. **Check:** by eye.
- **R15 End sting.** *Layout now fixed by R83, timing by R96.* A short logo animation with its own sound, 9:16, then the platform logos. **Why:** A consistent ending builds recognition. **Check:** by eye.
- **R28 Your own look only.** Never borrow colours or a look from another brand or another channel the host runs. Your look is `colors` in brand.json. **Why:** A show is its own brand. Mixed looks confuse it. **Check:** by eye. No values outside brand.json.
- **R30 End card logos read on a phone.** *Size replaced by R83.* Use the real platform marks from your `end_card.platforms`. **Why:** Tiny or fake icons look bad. **Check:** by eye.
- **R35 End card.** *Updated by R42, R67 and R83.* Texture plate, then the real platform logos in a clean tone, then a clear pill with your `end_card.cta`. No sweep. **Why:** A simple end card reads at a glance. **Check:** by eye.
- **R42 One look.** Every brand surface uses only your tokens and your texture plates: ground, ink, paper, accent. Keep the same outlined pills and the same logo treatment. No accent sweeps on brand cards. **Why:** One look repeated is what makes a brand. **Check:** by eye.
- **R46 End card intro.** *Timing tightened by R69 and R96.* Texture fades up, the logo lands, small centred platform logos fade in, then the pill. **Why:** The order leads the eye to the action. **Check:** by eye.
- **R48 Title on your texture.** Title words in `on_ground` on the texture, with no box and no grey panel. One or two key words use the highlight in `title.highlight`. The logo on the title is optional and off by default. **Why:** The end card already carries the brand. **Check:** by eye.
- **R67 End card uses the real logo.** Your `brand/logo.png`, kept small, not the name spelled out in type. **Why:** Type is not a logo. **Check:** by eye.
- **R69 End card is quick, with a click.** The logo lands in about 0.3 s with a click sound. Platform logos and the pill follow within a second. **Why:** A slow end card feels like dead time. **Check:** by eye.
- **R75 The title card shows the texture edge.** Your texture is visible at both edges of the card, with no hard strip. Use a texture made for the card's shape (`card.png`, `card_wide.png`). **Why:** A flat card looks pasted on. **Check:** by eye.
- **R83 End card: three things.** Logo, a small row of platform marks right under it (64 px), then the `end_card.cta` pill. No byline. It animates with your signature move (`motion.signature`). **Why:** One clear pattern: mark, small platform row, one call to action. **Check:** by eye.
- **R96 End card sound and drop.** The logo drops as one block, not two halves, and lands at +0.12 s on your click sound (`end_card.click`). The button lands at +0.80 s on a lighter click. **Why:** The sound and the landing need to be one event. **Check:** by eye and ear.

## Rendering

- **R54 One renderer.** `pipeline/short.py` draws the whole Short from a spec json anchored on episode word numbers: opener, glides, moving pictures, screen crops, word captions, end card. Captions never cross a moving face. **Why:** One renderer means a fix applies everywhere. **Check:** short.py.

## Review and approval

- **R18 Always a link.** Every update to the owner ends with a clickable link to the new file or page. **Why:** Nobody should have to search for what you made. **Check:** by eye.
- **R19 Codify.** Every note from the owner becomes a rule the same day. See "The law" at the top. **Why:** Notes that stay in a chat get made twice. **Check:** `/shorts-rule`.
- **R31 Options before cuts.** When the owner is unhappy with a look, make an option board first (real examples from top shows, then mock-ups), then cut only what they pick. **Why:** A board costs minutes. A render round costs hours. **Check:** by eye.
- **R36 Pick one.** Show options, but always say which one you would ship. **Why:** Options without a pick push the work back on the owner. **Check:** by eye.
- **R49 Review pages are players.** Every preview: tap for sound from the top, tap again to pause or play, and a restart button. **Why:** A review tool that cannot pause slows the review. **Check:** app.
- **R84 Conflicts go to the owner.** If a new note clashes with an older rule, say so. Settle it by the outlier data, not by taste. **Why:** Rules that quietly contradict each other break the system. **Check:** `/shorts-rule`.
- **R102 Never show unchecked work.** Every Short is gated (framecheck, sync, R97 to R100, and a look at 1 frame per second) before it goes in the app. No "work in progress, not checked". **Why:** Unchecked work wastes the owner's attention, and it teaches them to distrust the app. **Check:** the `/shorts` skill.
- **R109 Two versions of every Short.** *Replaced by R115.* **Why:** Two versions were meant to reduce rebuild requests, but reviewing them was too much work. **Check:** none.
- **R115 Two versions max, one is fine.** A Short shows at most 2 versions in the app. A rebuild replaces the old version. It does not add V3 or V4. Set `versions_per_short` in brand.json. **Why:** Three versions are too many to look over. **Check:** by eye.
- **R123 One booking per platform, ever.** The server claims the platforms in one atomic write, asks Buffer before every create, and books nothing if either check fails. **Why:** Two requests once both passed, and the same Short posted twice on three platforms. **Gate question:** Does Buffer hold this text on this channel already? **Check:** app server, dupcheck.
- **R124 Every Short gets its own time.** The server decides. If a Short is under `clash_hours` (default 1 h) from another, it moves to `gap_hours` (default 4 h) after that Short and logs the move. **Why:** Two Shorts approved seconds apart both read the same next slot. **Gate question:** Does dupcheck show two different texts at one time? Move one, and check again just before any move by hand. **Check:** app server, dupcheck.
- **R125 Every re-edit leaves a note under the Short.** The note says what changed and why, in plain words. The app shows all of them under Edits, below the feedback box. **Why:** Without notes, nobody can track what changed between versions. **Gate question:** Can the owner read under the Short what changed in each version? **Check:** publish.py refuses round 2+ without `--note`.

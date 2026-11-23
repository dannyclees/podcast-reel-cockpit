# The /shorts-setup questions

The skill at `.claude/skills/shorts-setup/SKILL.md` runs these. Max 4 at a time. Skip what you know. Every question has a default, so "you choose" always works.

Save after each answer to `brand/answers.json`:

```json
{"round": 2, "done": [1], "answers": {"show_name": "...", "people": [{"name": "...", "tag": "..."}]}, "grabbed": {"url": "...", "confirmed": false}, "notes": "anything else they said"}
```

Tell them what they get for each answer only when it is not obvious. Do not lecture.

---

## Round 1: the show

Plain chat first, as one message. It is faster for them:

> Tell me about the show, however you like:
> 1. Its name, and a short name if it has one
> 2. Your handle and your website, if you have them
> 3. What it's about, and who watches
> 4. Who is on mic: names and how you tag them

Then AskUserQuestion for what is still open:

| Question | Options | Default | Goes to |
|---|---|---|---|
| How many people are on mic? | 1, 2, 3 | 2 | `people`, `format` |
| What topic is your niche drowning in? | free text, or "no idea" | blank | `show.saturated_topic` |

Say why you ask about the drowning topic: "We make at most one Short per episode on it, so you stand out." Rule R3.

From this: `show.name`, `show.short` (default: the name), `show.handle`, `show.site`, `show.topics`, `show.audience`, `people[]` with `id` a, b, c in order, `name`, `tag` (default `#` + name with no spaces), `role` "host". Also write `show.voice` in 3 to 5 plain words from how they talk to you.

---

## Round 2: recording

AskUserQuestion:

| Question | Options | Default | Goes to |
|---|---|---|---|
| How do you record? | Riverside, separate video files for each person, one combined file | separate files | `recording.source` |
| Do you share your screen on the show? | Yes, No | No | `recording.screen_share` |

- Riverside: ask how each person's track is named in Riverside. Default: their name. Goes to `people[].riverside_track`. Say a share link or an API key comes later, in `.env`.
- One combined file: set `"recording": {"source": "local", "combined": true}`. Say plainly: "This works, but the system can't cut between people, because it can't tell who is who. It treats the show as one speaker. Separate tracks give much better Shorts." Every word goes to the first person listed. The `/shorts` run uses `pipeline/ingest.py <episode> --composite <file>`.

---

## Round 3: where the look comes from

This is the key round. Ask in plain chat:

> Do you have brand guidelines? Give me anything you have, in any mix:
> a website, a guidelines PDF, a Figma link, a folder of images, a logo file, hex colours, font names.
> Nothing yet is fine too. I'll offer you three directions.
>
> And name 1 to 3 creators, shows or videos whose look you love, with links if you can.

Then go and read it all (Step 2 of the skill) and come back with what you found.

If they have nothing, make 3 directions. `brand/directions.json`:

```json
[
  {"name": "Short name for the direction",
   "why": "One line on why it fits this show",
   "colors": {"ground": "#101820", "accent": "#F2AA4C"},
   "fonts": {"display": "A Google Fonts family", "body": "A Google Fonts family"},
   "texture": {"style": "halftone", "seed": 1, "strength": 0.5},
   "motion": {"signature": "stack", "energy": "high"},
   "title": {"uppercase": true}}
]
```

Type pairs that work well, all on Google Fonts. Use them as a start, not a limit:

- Loud and condensed: Anton + Manrope. Bebas Neue + Work Sans. Oswald + Inter.
- Warm and editorial: Fraunces + DM Sans. Playfair Display + Source Sans 3. Newsreader + Instrument Sans.
- Modern and friendly: Bricolage Grotesque + Figtree. Sora + Plus Jakarta Sans. Outfit + Nunito Sans.
- Heavy and playful: Bowlby One + Outfit. Dela Gothic One + Lexend. Rubik + Karla.
- Technical: Space Grotesk + IBM Plex Sans. Syne + Space Mono.

Mono default: IBM Plex Mono, DM Mono or Space Mono. Pick the one that sits best with the body font.

---

## Round 4: look choices

Skip anything the guidelines or the influences already settled. Say what you settled and why. AskUserQuestion, up to 4 at a time:

| Question | Options | Default | Goes to |
|---|---|---|---|
| Is the ground dark or light? | Dark, Light, You choose | what the brand suggests | `colors.ground` |
| Which texture sits on the edges? | Grain, Halftone dots, Ink strokes, Torn paper | what fits the brand | `texture.style` |
| More textures? (only if they want others) | Soft colour mesh, Fine grid, My own image | | `texture.style`, `texture.user_image` |
| How do graphics arrive? | Stack: a block drops, squashes and a colour layer slides out. Pop: it scales in with a small bounce. Slide: it slides in from the side. | stack | `motion.signature` |
| How much energy? | Low, Medium, High | medium | `motion.energy` |
| Title style? | Uppercase with a colour block on the key word, Uppercase with coloured key word, Normal case with coloured key word | first | `title.uppercase`, `title.highlight` ("block" or "colour") |
| Caption style? | Rounded box, Square box, Pill | rounded | `caption.radius`: rounded 28, square 8, pill 60 |
| Captions in capitals? | No, Yes | No | `caption.uppercase` |

Caption box: dark box on a dark ground, light box on a light ground. To override, set `caption.box` to "dark" or "light".

Own image: must be theirs to use. The build crops it, grades it to the brand colours, and keeps the middle quiet.

---

## Round 5: distribution

Ask in two groups. First, plain chat:

> Where does the full episode live? (Apple Podcasts, Spotify, YouTube)
> What should the end card say? Default: FULL EPISODE OUT NOW
> What line goes in the post, before the link? Default: Watch the full episode:
> What's your time zone?
> Any hashtags on every post? Any words you never want to say?
> Who approves the Shorts?

Then AskUserQuestion:

| Question | Options | Default | Goes to |
|---|---|---|---|
| Where do you post? | YouTube Shorts, Instagram Reels, TikTok (multi-select) | all three | `posting.platforms` |
| How many hours between posts? | 2, 4, 6, 8 | 4 | `posting.gap_hours` |
| How many Shorts per episode? | 3, 5, 7 | 5 | `shorts_per_episode` |
| Music? | I have my own tracks, None for now | none | `music` |

Say this about music plainly:

> This kit ships with no music and no LUT. They're licensed, and that licence can't be passed on to you. Bring up to 3 tracks you have the rights to, and put them in `brand/music/`. A LUT (a colour look for your video) is optional: a .cube file you own. With none, the video gets a clean neutral grade.

Goes to: `end_card.platforms` (apple, spotify, youtube; marks are in `brand/marks/`), `end_card.cta`, `posting.cta_line`, `posting.timezone` (a real name like "Europe/London"), `posting.always_tags`, `show.banned_words`, `app.approver`, `app.title` (default: short name + " Shorts System"), `music` (file names in `brand/music/`), `grade.lut` (path).

Channel ids and usernames (`posting.youtube_channel_id`, `posting.instagram_username`, `posting.tiktok_username`): ask if they know them. Blank is fine, stats just stay off until they are filled in.

## Extra question, round 1
Do the people on mic wear a logo on camera (a cap, a shirt)? If yes, write the logo's words in brand.json `framecheck_ignore`. The frame check then knows that text is not a caption on a face. Add any misread spelling you see in a framecheck failure.

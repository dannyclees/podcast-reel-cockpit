# Shorts system

One episode in, finished Shorts in a review app out. New here? Read `START-HERE.md`. For the whole picture, open `docs/overview.html`.

macOS only. Face tracking and frame reading use Apple Vision.

## The idea

Three things make this work:

1. **A pipeline.** Recording, transcript, pick, hook, cut, motion, render, gates, review, approve, schedule, posted, stats.
2. **Rules.** `RULES.md` holds 125 rules, each from a real mistake. Code checks the ones it can measure. Your notes become new rules from R200 in `rules/MY-RULES.md`.
3. **A brand file.** `brand/brand.json` holds every colour, font, name and URL. Change it, and the whole system changes.

## Commands in Claude Code

- `/shorts-setup`: first run. Writes your brand, sets up tools and the app.
- `/shorts`: one episode. See `.claude/skills/shorts/SKILL.md` for each step.
- `/shorts-motion`: the motion graphics for one Short.
- `/shorts-rule`: give a note, get a rule and a gate.

## The folders

- `brand/`: `brand.json` (yours, made by setup), plus the generated CSS, fonts, logo, textures and sounds.
- `pipeline/`: ingest, transcribe, cut, render (`short.py`), gates (`framecheck.py`, `contentcheck.py`).
- `motion/`: the motion kit, the beats and comps for each Short, its gate (`tools/gate.py`), and `STYLE.md`.
- `motion-library/`: finished motion treatments to reuse.
- `app/`: the review app, deployed to your own Vercel. `app/POSTING.md` covers platform API details.
- `app-sync/`: publishes to the app and reads notes back.
- `research/`: the studies behind the rules. Start at `research/README.md`.
- `rules/`: your own rules.
- `episodes/<ep>/`: each episode: `raw/`, `work/`, `clips/`, `vN/`.
- `docs/`: `overview.html` and `approval.md`.
- `bin/`: built tools and models, made by setup. Not shared.

## Key files per episode

- `episodes/<ep>/raw/`: `<person id>.mp4`, `<person id>_raw.wav`, `screen.mp4`. Person ids come from `people` in brand.json. A show can have 1, 2 or 3 people.
- `episodes/<ep>/work/words.json` and `work/lines.txt`: the transcript with word numbers.
- `episodes/<ep>/clips.json`: which words make each clip (`ranges`, `drops`, `drop_times`).
- `episodes/<ep>/clips/<clip>/`: the cut tracks, `words.json`, `voice.wav`, motion runs.
- `episodes/<ep>/vN/<id>.json`: the render spec. `<id>.mp4`: the final. `<id>_t1.m4a`: a music mix.
- `research/descriptions/<ep>.json`: post copy per platform.

## The gates

No Short reaches the app until it passes. The table of what each one fails on is in `docs/overview.html`.

## What a re-edit looks like

Read notes, fix, render again, run the gates, then publish with `--note` (R125). If the note is general, run `/shorts-rule` first so it never comes back.


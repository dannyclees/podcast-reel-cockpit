# Shorts system

This folder turns a podcast episode into finished Shorts. It picks clips, cuts them, adds captions and motion graphics, gates them, and sends them to a review app. The owner approves there, and posting goes through Buffer. It runs on a Mac only, because face tracking uses Apple Vision.

If `brand/brand.json` does not exist, tell the owner to type `/shorts-setup`. Nothing else works without it.

## The skills

- `/shorts-setup`: first-time setup: brand, keys, app, tools. Writes `brand/brand.json`.
- `/shorts`: one episode in, Shorts in the review app out.
- `/shorts-motion`: the motion graphics for one Short. `/shorts` uses it.
- `/shorts-rule`: turns a note into a permanent rule.

## Order of reading

1. `START-HERE.md`: for a new owner.
2. `README.md`: the flow and the folders.
3. `RULES.md`, then `rules/MY-RULES.md`. The owner's rules start at R200.
4. Before picking: `research/selection/SELECTION.md`, `research/hooks/HOOKS.md`.
5. Before motion: `motion/STYLE.md`, `research/layout/LAYOUT.md`.
6. Approval and posting: `docs/approval.md`.

## Non-negotiables

- **Never post without approval.** Nothing goes to Buffer or any platform until the owner has approved it in the review app, or says so in chat for that exact Short. Never turn on `POSTING_ENABLED` without asking.
- **Never play audio aloud** while the owner may be recording, unless asked. Test muted. Check sound by numbers and files, not by speakers.
- **Keys only in `.env`.** For the app, keys go in Vercel env vars. Never print, copy or commit a key. Never put one in a URL, a doc or a chat.
- **No brand values outside `brand/brand.json`.** No hard-coded colour, font, name, handle or URL anywhere else. To change the look, edit brand.json and run `python3 setup/build_brand.py`.
- **Say what failed, plainly.** Never shrink a FAIL. Never call something done if a gate failed or was skipped. If unsure, say "not sure" and what would settle it.
- **Never show unchecked work (R102).** Every Short passes its gates before it reaches the app.
- **A note becomes a rule (R19, R84).** Use `/shorts-rule`. Never treat a note as a one-off without asking.
- **Every re-edit has a note (R125).** Pass `--note` to `publish.py`.
- **Rights belong to the owner.** Flag anything unclear about a clip, photo, logo or track. Fair use is not assumed. Never add licensed files on the owner's behalf.
- **Facts only on screen (R80).** Check every claim against a source. A claim you cannot check does not go on screen.
- **Do not delete recordings.** Raw files in `episodes/<ep>/raw/` are the owner's source.

## How to talk to the owner

The owner may not be technical. Use short plain sentences. Say what you did, whether it worked, and what they do next. If they must choose, give 2 options, what each costs, and which one you would pick (R36). End every update with a link to what you made (R18).

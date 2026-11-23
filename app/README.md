# Shorts review app

The page where you watch each Short, leave notes, approve it and book it. No build step.

## What it does

- Four tabs: Drafts, Scheduled, Live, Revisions.
- A player with a music track switch and a sound effects switch.
- Feedback notes per version, and an Edits list under each Short.
- Approve and schedule in one click. Posts go out through Buffer.
- One booking per platform (R123). A Short can never be booked twice, even with two clicks at once.
- No two Shorts at the same time (R124). If a time is taken, the Short moves on by `posting.gap_hours`.
- A stats page with real numbers per live Short. Instagram numbers are optional.

## Where things are

- `public/`: the page. Routes: `#/` posts, `#/s/<episode>/<short>` one Short, `#/stats` numbers.
- `api/data.js`: everything the page shows, with signed media links.
- `api/act.js`: notes, approvals, track and link changes. Every change is logged.
- `api/post.js`: booking, cancelling and syncing with Buffer.
- `api/play.js`: makes the one file the player plays (video plus the chosen mix).
- `api/stats.js`: reads the numbers.
- `middleware.js`: the password gate on every path, API included. With no password set, it refuses everything.
- `schema.sql`: the full database setup.

## Generated files

Setup writes these from `brand/brand.json`. Do not edit them by hand. `BRAND-TOKENS.md` lists the exact names the app reads.

- `public/brand.css`, `public/brand.js`, `public/fonts/`, `public/img/`
- `api/_brand.js`

## Set it up

Follow `SETUP.md`. Posting stays off until you set `POSTING_ENABLED=1`. See `POSTING.md` for platform facts.

## Tests

No keys and no install needed. Run from this folder.

```bash
node tests/post_test.mjs
node tests/api_test.mjs
node tests/page_test.mjs
```

`page_test.mjs` checks the files. To also check the page in a real browser, with a light and a dark palette, set `CHROME_PATH` and `PUPPETEER_DIR`. The top of the file shows how.

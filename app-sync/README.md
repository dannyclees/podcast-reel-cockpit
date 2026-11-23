# app-sync

Bridge between this pipeline and your approval app (`app/`, its URL is `app.url` in brand/brand.json). Keys are read from `.env` in the kit root.

- `publish.py <episode> <id> [...]` : upload finished Shorts (web copy + poster + one mix per music track + post copy). Again = new round.
  Add `--note "what changed and why"` on every new round (R125: it refuses a re-edit without one). It runs the content gate first.
  `--board boards/<date>/shorts.json` publishes a board file. No music tracks is fine: the Short ships with its own sound only.
- `pull.py` : write `state.json` (status, chosen track, posted links, every note) for the next render.
- `feedback.py` : list and close the notes left in the app.
- `post_queue.py`, `dupcheck.py`, `playtrace.py` : scheduling queue, duplicate-post check, video-play traces.
- `hashtags.json` : optional topic tags per Short, `{"<episode>/<id>": ["#tag", ...]}`.
- `cache/` : the web copies and posters (safe to delete).

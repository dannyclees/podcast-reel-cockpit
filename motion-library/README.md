# Motion library

Ready-made graphic treatments in your brand's tokens. `catalog.json` lists what each one is for.

- `treatments/<id>/index.html`: working HyperFrames page, 1080x960 top panel. `full.html` = 1080x1920 version (map-drop, split-flap, glitch-slam).
  Inputs sit in the `IN` object at the top of each script, filled with neutral samples. Timeline: `window.__timelines['main']`, paused, deterministic.
- `shared/`: `kit.css` (ground, cards), `kit.js` (count, pulse, packet, draw, every), gsap, sample logos. `setup/build_brand.py` adds `brand.css` and `fonts/`.
- `./build.sh [id ...]`: copies `shared/` into each treatment, renders `preview.mp4`, `strip.jpg` (6 frames), `poster.jpg`, kills orphan headless Chrome.
- `variants.py <name ...>`: a treatment with one Short's own numbers and names (R74). Real logos are fetched from simple-icons per Short.

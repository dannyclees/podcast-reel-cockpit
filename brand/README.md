# Your brand

`brand.json` is the one place your look lives: colours, fonts, names, handles, wording. `/shorts-setup` writes it. To change it later, edit it or ask Claude, then run:

```bash
python3 setup/build_brand.py
python3 setup/preview.py
```

The build makes everything else from it, so never edit these by hand:

- `brand.css`: colours and fonts
- `fonts/`: your 4 fonts, saved under fixed names, with `LICENCES.txt`
- `logo.png`: your logo, or a wordmark drawn from your display font
- `textures/`: the plates, drawn from your colours
- `sfx/`: a small sound kit, synthesised for your show
- `preview/index.html`: your preview. It opens from Finder and has no sound.
- `build_report.json`: every readability check, and anything the build changed

Your own files:

- `music/`: 0 to 3 tracks you have the rights to. The kit ships with none.
- `marks/`: platform marks for the end card.

`brand.example.json` shows the full shape. `brand.lock` means you approved the preview. Rendering refuses to run without it. If `brand.json` changes, the build clears it and you approve again.

A font must be licensed for video. Check yours.

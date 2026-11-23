#!/usr/bin/env python3
"""look.py <video> <out.jpg> t1 t2 ... [--w 270]: frames at those seconds, tiled 4 across with the time printed under each."""
import subprocess, sys, io
from PIL import Image, ImageDraw
args = [a for a in sys.argv[1:]]; W = 270
if '--w' in args: k = args.index('--w'); W = int(args[k + 1]); del args[k:k + 2]
v, out, ts = args[0], args[1], [float(x) for x in args[2:]]
ims = []
for t in ts:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', v, '-frames:v', '1', '-vf', f'scale={W}:-1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
    ims.append(Image.open(io.BytesIO(raw)).convert('RGB') if raw else Image.new('RGB', (W, W), 'red'))
cols = min(4, len(ims)); rows = (len(ims) + cols - 1) // cols; h = ims[0].height + 18
sheet = Image.new('RGB', (cols * W, rows * h), '#333'); d = ImageDraw.Draw(sheet)
for k, (t, im) in enumerate(zip(ts, ims)):
    x, y = (k % cols) * W, (k // cols) * h; sheet.paste(im, (x, y)); d.text((x + 4, y + im.height + 3), f'{t:.2f}s', fill='white')
sheet.save(out, quality=72)

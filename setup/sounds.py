#!/usr/bin/env python3
"""sounds.py: synthesises the show's small sound kit with numpy. 48 kHz mono wav. Nothing licensed, nothing sampled.

Each show gets slightly different sounds, from its name and seed. This file never plays anything.
Names match what the pipeline asks for: whoosh, whoosh_lo, pop, plus end_click, click, tick, impact, soft_impact, riser.
Levels sit near -20 dB RMS while the sound is active, so the gains in the render specs keep working.
"""
import hashlib
import wave
from pathlib import Path

import numpy as np

SR = 48000
NAMES = ('whoosh', 'whoosh_lo', 'pop', 'click', 'tick', 'impact', 'soft_impact', 'riser', 'end_click')


def _rng(*parts):
    h = hashlib.sha256('|'.join(str(p) for p in parts).encode()).digest()
    return np.random.default_rng(int.from_bytes(h[:8], 'big'))


def _t(sec):
    return np.arange(int(SR * sec)) / SR


def _env(t, attack, decay):
    return np.minimum(t / max(attack, 1e-5), 1.0) * np.exp(-np.maximum(t - attack, 0) / decay)


def _sweep_noise(n, f0, f1, q, rng):
    """White noise through a band-pass filter whose centre moves from f0 to f1. Done in overlapping FFT frames, so it stays smooth."""
    noise = rng.standard_normal(n)
    size, hop = 2048, 512
    win = np.hanning(size)
    out = np.zeros(n + size)
    freqs = np.fft.rfftfreq(size, 1 / SR)
    for i, start in enumerate(range(0, n, hop)):
        chunk = noise[start:start + size]
        if len(chunk) < size:
            chunk = np.pad(chunk, (0, size - len(chunk)))
        f = f0 * (f1 / f0) ** min(1.0, start / max(n - 1, 1))
        bw = f / q
        gain = np.exp(-((freqs - f) / bw) ** 2)
        out[start:start + size] += np.fft.irfft(np.fft.rfft(chunk * win) * gain, size) * win
    return out[:n]


def _lowpass(x, fc):
    spectrum = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(spectrum * (1 / np.sqrt(1 + (freqs / fc) ** 4)), len(x))


def _fit(x, level=-20.0, peak=-3.0):
    """Set the level while the sound is active, cap the peak, and fade the very end so there is never a click."""
    x = np.asarray(x, dtype=np.float64)
    active = np.abs(x) > 0.02 * (np.abs(x).max() + 1e-9)
    rms = np.sqrt((x[active] ** 2).mean()) if active.any() else 1.0
    x = x * (10 ** (level / 20)) / (rms + 1e-9)
    top = np.abs(x).max()
    limit = 10 ** (peak / 20)
    if top > limit:
        x = x * limit / top
    tail = min(len(x), int(0.004 * SR))
    if tail:
        x[-tail:] *= np.linspace(1, 0, tail)
    return x


def _clack(rng, pitch, sub=True):
    """A key landing: a sharp top, a woody body and, when asked, a low thump under it."""
    t = _t(0.28)
    top = _sweep_noise(len(t), 5200 * pitch, 3200 * pitch, 2.5, rng) * _env(t, 0.0006, 0.007)
    body = np.sin(2 * np.pi * 620 * pitch * t + 3 * np.exp(-t / 0.01)) * _env(t, 0.0008, 0.022) * 0.55
    out = top * 1.1 + body
    if sub:
        low = np.sin(2 * np.pi * (50 + 34 * np.exp(-t / 0.03)) * t) * _env(t, 0.002, 0.095) * 0.85
        out = out + low
    return out


def make(name, show, seed):
    rng = _rng(show, seed, name)
    pitch = float(rng.uniform(0.9, 1.12))
    if name == 'whoosh':
        t = _t(0.62)
        x = _sweep_noise(len(t), 700 * pitch, 3600 * pitch, 1.6, rng)
        x *= np.sin(np.pi * np.clip(t / t[-1], 0, 1)) ** 2.2
        return _fit(x)
    if name == 'whoosh_lo':
        t = _t(0.7)
        x = _sweep_noise(len(t), 220 * pitch, 1200 * pitch, 1.3, rng)
        x *= np.sin(np.pi * np.clip(t / t[-1], 0, 1)) ** 2.4
        return _fit(_lowpass(x, 2600))
    if name == 'pop':
        t = _t(0.16)
        ph = 2 * np.pi * np.cumsum(240 * pitch + 760 * pitch * np.exp(-t / 0.018)) / SR
        x = np.sin(ph) * _env(t, 0.0012, 0.034)
        x = x + _sweep_noise(len(t), 3800, 2400, 2.0, rng) * _env(t, 0.0005, 0.004) * 0.5
        return _fit(x)
    if name == 'click':
        t = _t(0.05)
        x = _sweep_noise(len(t), 4800 * pitch, 3000 * pitch, 2.2, rng) * _env(t, 0.0004, 0.004)
        x = x + np.sin(2 * np.pi * 1700 * pitch * t) * _env(t, 0.0005, 0.007) * 0.6
        return _fit(x)
    if name == 'tick':
        t = _t(0.035)
        x = np.sin(2 * np.pi * 2600 * pitch * t) * _env(t, 0.0003, 0.0055)
        return _fit(x, level=-22.0)
    if name in ('impact', 'soft_impact'):
        t = _t(0.72 if name == 'impact' else 0.5)
        hard = 1.0 if name == 'impact' else 0.45
        low = np.sin(2 * np.pi * np.cumsum(46 * pitch + 58 * np.exp(-t / 0.05)) / SR) * _env(t, 0.002, 0.2 if name == 'impact' else 0.12)
        hit = _lowpass(rng.standard_normal(len(t)), 900 if name == 'impact' else 500) * _env(t, 0.001, 0.028)
        return _fit(low + hit * 1.8 * hard)
    if name == 'riser':
        t = _t(1.6)
        k = t / t[-1]
        x = _sweep_noise(len(t), 260 * pitch, 5200 * pitch, 1.7, rng) * k ** 2.6
        tone = np.sin(2 * np.pi * np.cumsum(180 * pitch * 4 ** k) / SR) * k ** 3 * 0.25
        x = x + tone
        tail = int(0.02 * SR)
        x[-tail:] *= np.linspace(1, 0, tail)
        return _fit(x)
    if name == 'end_click':
        # The pipeline places this file 0.4 s before the end card starts. The logo lands at +0.12 s, the button at +0.80 s.
        total = int(SR * 1.75)
        x = np.zeros(total)
        first = _clack(rng, pitch, sub=True)
        second = _clack(rng, pitch * 1.18, sub=False) * 0.42
        a, b = int(SR * 0.52), int(SR * 1.20)
        x[a:a + len(first)] += first
        x[b:b + len(second)] += second
        return _fit(x, level=-16.0, peak=-2.0)
    raise ValueError(name)


def write_wav(path, x):
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def build_kit(outdir, show, seed):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out = []
    for name in NAMES:
        p = outdir / (name + '.wav')
        write_wav(p, make(name, show, seed))
        out.append(p)
    return out


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Synthesise the sound kit. It never plays anything.')
    ap.add_argument('--out', required=True)
    ap.add_argument('--show', default='Example Show')
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    for f in build_kit(a.out, a.show, a.seed):
        print(f)

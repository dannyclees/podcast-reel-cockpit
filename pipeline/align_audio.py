#!/usr/bin/env python3
"""align_audio.py <episode dir>: put each speaker's RAW mic WAV on the aligned-video timeline (lossless voice).

A recorder's aligned video often carries a low-bitrate AAC copy of the voice (68 kbps: dull and swirly).
The raw WAV is the real mic recording, but it starts when that person's local recording started.
This finds the offset by matching voice envelopes (vendor/_sync.py, to the millisecond), then writes
work/audio_hq/<role>.wav (48 kHz mono, same start and length as the video) and points tracks.json at it.
Needs raw/<role>_raw.wav next to raw/<role>.mp4. With no raw WAV the video's own sound stays, and that is fine.
"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'vendor'))
from _sync import load, env_db, lag_ms


def dur(f):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f],
                                capture_output=True, text=True).stdout)


def main(E):
    W = os.path.join(E, 'work'); T = json.load(open(os.path.join(W, 'tracks.json')))
    if T.get('mode') == 'composite': print('composite: one sound, nothing to line up'); return
    os.makedirs(os.path.join(W, 'audio_hq'), exist_ok=True)
    for role in T['speakers']:
        raw = os.path.join(E, 'raw', f'{role}_raw.wav'); vid = os.path.join(E, 'raw', f'{role}.mp4')
        if not os.path.exists(raw): print(f'{role}: no raw WAV, keeping the video audio'); continue
        lag, score = lag_ms(env_db(load(vid)), env_db(load(raw)), 20000)   # raw[t + lag] ~ video[t]
        off = lag / 1000.0
        out = os.path.join(W, 'audio_hq', f'{role}.wav'); D = dur(vid)
        # video time t plays raw time t + off: trim the start (off > 0) or pad it with silence (off < 0)
        af = f'atrim=start={off:.3f},asetpts=PTS-STARTPTS' if off >= 0 else f'adelay={int(-off * 1000)}:all=1'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-af', f'{af},apad', '-t', f'{D:.3f}', '-ar', '48000', '-ac', '1',
                        '-c:a', 'pcm_s24le', out], check=True)
        chk, _ = lag_ms(env_db(load(vid)), env_db(load(out)), 500)
        T['tracks'][role]['audio'] = out
        print(f'{role}: raw WAV offset {off:+.3f} s (match {score:.2f}), check lag {chk} ms '
              f"({'OK' if abs(chk) <= 20 else 'CHECK BY EAR'}) -> {out}")
    json.dump(T, open(os.path.join(W, 'tracks.json'), 'w'), indent=1)


if __name__ == '__main__':
    main(os.path.abspath(sys.argv[1]))

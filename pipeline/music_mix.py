#!/usr/bin/env python3
"""music_mix.py <final.mp4> <track.mp3|none> <out.m4a> [--bed -21] [--sfx stem.wav]: the finished Short's own sound with a music bed under it.

The approval app plays the video muted and keeps one audio file per track in step with it; a click swaps which one is heard.
So each track (0 to 3, from brand.json "music") is a full-length audio file of the SAME cut: the final's sound (voice, click, loudness already set) plus
the track as a steady bed (R65), ducked gently under the voice (same settings as short.py --music), then -14 LUFS.
"""
import argparse, json, subprocess


def dur(f):
    return float(json.loads(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', f],
                                           capture_output=True, text=True).stdout)['format']['duration'])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('final'); ap.add_argument('track'); ap.add_argument('out')
    ap.add_argument('--bed', type=float, default=-21); ap.add_argument('--start', type=float, default=0.0)
    ap.add_argument('--sfx', help='SFX stem from short.py (<final>_sfxstem.wav): mixed beside the voice, not into the duck key')
    a = ap.parse_args(); T = dur(a.final)
    ins = ['-i', a.final]; parts = ['[0:a]asplit[v][vk]']; mix = ['[v]']
    if a.track != 'none':   # "none" = no music (for the SFX-only mix)
        ins += ['-stream_loop', '-1', '-i', a.track]
        parts.append(f'[1:a]atrim=start={a.start}:duration={T},asetpts=PTS-STARTPTS,volume={a.bed}dB,afade=t=in:d=0.6,afade=t=out:st={T - 1.2:.2f}:d=1.2[m0]')
        parts.append('[m0][vk]sidechaincompress=threshold=0.08:ratio=2:attack=40:release=700:makeup=1[mb]'); mix.append('[mb]')
    else:
        parts.append('[vk]anullsink')
    if a.sfx:
        ins += ['-i', a.sfx]; parts.append(f'[{ins.count("-i") - 1}:a]aresample=48000[sx]'); mix.append('[sx]')
    parts.append(f'{"".join(mix)}amix=inputs={len(mix)}:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]' if len(mix) > 1 else '[v]loudnorm=I=-14:TP=-1.5:LRA=11[a]')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(parts),
                    '-map', '[a]', '-t', f'{T:.3f}', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', a.out], check=True)
    print('music mix ->', a.out, f'({T:.1f} s)')


if __name__ == '__main__':
    main()

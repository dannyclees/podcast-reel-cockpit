#!/bin/zsh
# render_finals.sh <ep> <dir> <names...>: the finished Shorts in episodes/<ep>/<dir>/: short.py (sync gate inside), framecheck, then the mixes.
#   <name>.json is the spec. The clip is found in episodes/<ep>/clips/ (a folder named <name>, or with <name> as one dash-separated part).
# Mixes: <name>.m4a (no music) and <name>_sfx.m4a, plus <name>_t1.m4a ... one per track in brand.json "music" (0 to 3), each with and without the SFX stem.
# With no tracks only the no-music cut ships. One render at a time.
H=${0:A:h}; ROOT=${H:h:h}; P=$ROOT/pipeline
ep=$1; dir=$2; shift 2
(( $# )) || { echo "usage: render_finals.sh <ep> <dir> <names...>"; exit 2; }
cd $ROOT/episodes/$ep/$dir || exit 1
TRACKS=$(python3 -c "
import sys; sys.path.insert(0, '$P')
import brand
for t in brand.tracks(): print(t['key'], t['bed'], t['path'], sep='\t')
")
for n in $@; do
  clip=$(python3 -c "
import os
print(next((os.path.join('../clips', c) for c in sorted(os.listdir('../clips')) if c == '$n' or '$n' in c.split('-')), ''))
")
  [[ -n $clip ]] || { echo "$n: no clip folder"; continue; }
  rm -f $n.mp4   # a failed render must never leave the old file to be checked
  python3 $P/short.py $clip $n.json $n.mp4 2>&1 | grep -E "WARNING|sync check|SYNC FAIL|Error|Traceback" | sed "s/^/$n: /"
  rm -rf ${n}_hf
  [[ -f $n.mp4 ]] || { echo "$n: RENDER FAILED"; continue; }
  python3 $P/framecheck.py $n.mp4 --sting 2.6 2>&1 | grep -E "FAIL|PASS" | sed "s/^/$n: /"
  S=${n}_sfxstem.wav
  python3 $P/music_mix.py $n.mp4 none $n.m4a >/dev/null
  [[ -f $S ]] && python3 $P/music_mix.py $n.mp4 none ${n}_sfx.m4a --sfx $S >/dev/null
  if [[ -n $TRACKS ]]; then
    while IFS=$'\t' read -r key bed track; do
      python3 $P/music_mix.py $n.mp4 "$track" ${n}_$key.m4a --bed $bed >/dev/null
      [[ -f $S ]] && python3 $P/music_mix.py $n.mp4 "$track" ${n}_${key}_sfx.m4a --bed $bed --sfx $S >/dev/null
    done <<< "$TRACKS"
  fi
  echo "$n done: $(ls $n*.m4a | wc -l | tr -d ' ') mixes"
done
echo FINALS_DONE

#!/bin/bash
# build.sh [id ...]: copy the shared kit next to each treatment and render preview.mp4 + strip.jpg + poster.jpg.
# Renders one at a time with 4 workers, then kills orphan headless Chrome.
cd "$(dirname "$0")"
IDS="$@"; [ -z "$IDS" ] && IDS=$(ls treatments)
for id in $IDS; do
  d=treatments/$id; [ -f $d/index.html ] || continue
  cp shared/brand.css shared/gsap.min.js shared/hyperframes.json shared/kit.css shared/kit.js $d/
  rm -rf $d/fonts $d/logos; cp -R shared/fonts $d/fonts; cp -R shared/logos $d/logos
  [ -f $d/package.json ] || echo "{\"name\":\"$id\",\"private\":true,\"type\":\"module\"}" > $d/package.json
  [ -f $d/meta.json ] || echo "{\"id\":\"$id\",\"name\":\"$id\"}" > $d/meta.json
  for page in index full; do
    [ -f $d/$page.html ] || continue
    out=preview.mp4; [ $page = full ] && out=preview-full.mp4
    ( cd $d && HYPERFRAMES_NO_TELEMETRY=1 HYPERFRAMES_SKIP_SKILLS=1 npx --yes hyperframes@0.8.181 render $( [ $page = full ] && echo "-c full.html" ) --quality looks -w 4 --output $out > render-$page.log 2>&1 < /dev/null )
    echo "$id/$page exit $?"
    ps -axo pid=,ppid=,command= | awk '$2==1 && /chrome-headless-shell/ {print $1}' | xargs kill 2>/dev/null
    if [ -f $d/$out ]; then
      dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $d/$out)
      tag=${out%.mp4}
      # 6-frame contact strip + poster
      ffmpeg -v error -y -i $d/$out -vf "fps=6/$dur,scale=360:-1,tile=6x1:padding=8:color=black" -frames:v 1 -q:v 4 $d/strip${tag#preview}.jpg
      ffmpeg -v error -y -ss $(python3 -c "print(round($dur*0.62,2))") -i $d/$out -frames:v 1 -vf scale=720:-1 -q:v 3 $d/poster${tag#preview}.jpg
    fi
  done
done

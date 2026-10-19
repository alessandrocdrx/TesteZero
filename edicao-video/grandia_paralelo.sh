#!/bin/bash
# Renders grandia.py (or SCRIPT=adeus for adeus.py) in N chunks side by side (every effect depends only on time, so the chunks are
# independent and join seamlessly), then joins them without re-encoding and adds the hymn once.
# Usage: CLIPES=dir FONTS=dir grandia_paralelo.sh CENAS_DIR HINO.mp3 OUT.mp4      (PARALELO=3 by default)
set -euo pipefail
cenas=$1 hino=$2 out=$3
dir=$(cd "$(dirname "$0")" && pwd); tmp=$(mktemp -d)
n=${PARALELO:-3}
script=${SCRIPT:-grandia}
dur=$(python3 -c "import sys; sys.path.insert(0, '$dir'); import $script; print($script.DUR)")
cuts=($(python3 -c "
fps, d, n = 30, $dur, $n
f = round(d * fps)
print(' '.join(f'{round(f * k / n) / fps:.4f}' for k in range(n + 1)))"))
pids=()
for ((k = 0; k < n; k++)); do
  CLIP="${cuts[k]},${cuts[k+1]}" python3 "$dir/$script.py" "$cenas" "$hino" "$tmp/p$k.mp4" > "$tmp/p$k.log" 2>&1 &
  pids+=($!)
done
for j in "${pids[@]}"; do wait "$j" || { echo "um pedaço falhou: veja $tmp/*.log" >&2; exit 1; }; done
for ((k = 0; k < n; k++)); do echo "file '$tmp/p$k.mp4'"; done > "$tmp/lista.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$tmp/lista.txt" -c copy "$tmp/video.mp4"
ffmpeg -loglevel error -y -i "$tmp/video.mp4" -i "$hino" -filter_complex \
  "[1:a]atrim=0:$dur,afade=t=out:st=$(python3 -c "print($dur - 1.2)"):d=1.2,loudnorm=I=-14:TP=-1.5:LRA=11[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 256k -ar 48000 -movflags +faststart -t "$dur" "$out"
rm -rf "$tmp"

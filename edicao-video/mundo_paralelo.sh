#!/usr/bin/env bash
# Renderiza mundo.py em 4 pedaços ao mesmo tempo e junta sem recodificar.
# Uso: mundo_paralelo.sh SRC ANALISE.npz CENARIOS MODELO OUT_SEM_AUDIO.mp4   (MATTE_CACHE e FONTS passam adiante)
set -euo pipefail
src=$1; npz=$2; bg=$3; model=$4; out=$5
dir=$(dirname "$0"); tmp=$(mktemp -d)
# limites em quadros exatos (30 fps): 0, 652, 1305, 1957, 2610
cuts=(0 21.734 43.501 65.234 87.0)
# no máximo 3 ao mesmo tempo: cada pedaço ocupa ~3 GB e 4 juntos estouram a memória de 15 GB
pids=()
for k in 0 1 2 3; do
  while [ "$(jobs -rp | wc -l)" -ge "${PARALELO:-3}" ]; do sleep 2; done
  CLIP="${cuts[k]},${cuts[k+1]}" python3 "$dir/mundo.py" "$src" "$npz" "$bg" "$model" "$tmp/p$k.mp4" > "$tmp/p$k.log" 2>&1 &
  pids+=($!)
done
for j in "${pids[@]}"; do wait "$j" || { echo "um pedaço falhou: veja $tmp/*.log" >&2; exit 1; }; done
for k in 0 1 2 3; do echo "file '$tmp/p$k.mp4'"; done > "$tmp/lista.txt"
ffmpeg -loglevel error -y -f concat -safe 0 -i "$tmp/lista.txt" -c copy "$out"
rm -rf "$tmp"

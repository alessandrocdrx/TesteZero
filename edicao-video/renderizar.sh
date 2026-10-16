#!/usr/bin/env bash
# Renderiza o reel (85 s) e o story (15 s). A voz original é copiada sem recodificar.
# Prévia rápida de quadros: PREVIEW="0.8,20,53" python3 mv.py entrada/v.mp4 previa
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p saida
python3 mv.py entrada/v.mp4 saida/sem_audio.mp4
ffmpeg -loglevel error -y -i saida/sem_audio.mp4 -i entrada/v.mp4 -map 0:v -map 1:a -c:v copy -c:a copy -movflags +faststart saida/reel.mp4
ffmpeg -loglevel error -y -ss 63.0 -t 15 -i saida/reel.mp4 -c:v libx264 -crf 18 -c:a copy -movflags +faststart saida/story.mp4
echo "Pronto: saida/reel.mp4 e saida/story.mp4"

# Corte viral TikTok (~40 s): trechos da voz original cortados nas respirações, sem alterar a voz
python3 viral.py entrada/v.mp4 saida/viral_sem_audio.mp4
f=""; i=0; parts=""
for seg in $(python3 viral.py - --segments); do
  a=${seg%:*}; b=${seg#*:}; d=$(python3 -c "print($b-$a-0.02)")
  f="$f[0:a]atrim=$a:$b,asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st=$d:d=0.02[a$i];"
  parts="$parts[a$i]"; i=$((i+1))
done
ffmpeg -loglevel error -y -i entrada/v.mp4 -filter_complex "${f}${parts}concat=n=$i:v=0:a=1[a]" -map "[a]" -c:a aac -b:a 192k saida/viral_audio.m4a
ffmpeg -loglevel error -y -i saida/viral_sem_audio.mp4 -i saida/viral_audio.m4a -map 0:v -map 1:a -c copy -movflags +faststart saida/tiktok_viral.mp4
echo "Pronto: saida/tiktok_viral.mp4"

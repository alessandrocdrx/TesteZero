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

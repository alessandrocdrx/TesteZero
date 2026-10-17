#!/usr/bin/env bash
# Instala dependências, baixa fontes e o vídeo, e transcreve o áudio.
# Uso: ./preparar.sh "https://www.tiktok.com/@perfil/video/ID"
set -euo pipefail
cd "$(dirname "$0")"
pip install -q "yt-dlp[curl-cffi]" faster-whisper "opencv-contrib-python-headless<5" mediapipe pillow numpy
# MediaPipe precisa de libEGL no Linux (apt-get install -y libegl1 libgles2)
mkdir -p modelos
[ -f modelos/selfie_multiclass.tflite ] || curl -sSfL -o modelos/selfie_multiclass.tflite https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite
mkdir -p fonts entrada
for f in anton/Anton-Regular.ttf archivoblack/ArchivoBlack-Regular.ttf "montserrat/Montserrat%5Bwght%5D.ttf" "cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf" "cormorantgaramond/CormorantGaramond-Italic%5Bwght%5D.ttf"; do
  n=$(basename "$f" | sed "s/%5Bwght%5D//"); [ -f "fonts/$n" ] || curl -sSfL -o "fonts/$n" "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/$f"
done
python3 -m yt_dlp --impersonate chrome -o "entrada/v.%(ext)s" "$1"
ffmpeg -loglevel error -y -i entrada/v.mp4 -ac 1 -ar 16000 entrada/a.wav
python3 transcrever.py entrada/a.wav > entrada/transcricao.txt
cat entrada/transcricao.txt

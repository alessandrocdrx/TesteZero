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

# Versão principal: o take inteiro, intacto, com tipografia de cinema (voz copiada sem recodificar)
python3 calmo.py entrada/v.mp4 saida/calmo_sem_audio.mp4
ffmpeg -loglevel error -y -i saida/calmo_sem_audio.mp4 -i entrada/v.mp4 -map 0:v -map 1:a -c copy -movflags +faststart saida/voa_nas_asas_do_vento.mp4
echo "Pronto: saida/voa_nas_asas_do_vento.mp4"

# Versão com efeitos ligados à letra, à voz e às expressões dela
python3 analisar.py entrada/v.mp4 entrada/a.wav entrada/analise.npz
python3 efeitos.py entrada/v.mp4 entrada/analise.npz saida/efeitos_sem_audio.mp4
ffmpeg -loglevel error -y -i saida/efeitos_sem_audio.mp4 -i entrada/v.mp4 -map 0:v -map 1:a -c copy -movflags +faststart saida/voa_nas_asas_efeitos.mp4
echo "Pronto: saida/voa_nas_asas_efeitos.mp4"

# Versão "mundo": o quarto dela vira pinturas russas do século XIX que seguem a letra
# o recorte dela é calculado uma vez e reaproveitado em toda renderização seguinte
[ -d entrada/recorte ] || python3 recorte.py entrada/v.mp4 modelos/selfie_multiclass.tflite entrada/recorte
# quarto vazio (placa limpa + cadeira) e testes automáticos antes de renderizar
[ -f entrada/quarto.npz ] || python3 quarto.py entrada/v.mp4 entrada/recorte entrada/quarto.npz
STEP=3 python3 qa_vazamento.py entrada/v.mp4 entrada/recorte entrada/quarto.npz saida/qc_vaz
STEP=3 python3 qa_ela.py entrada/v.mp4 entrada/recorte entrada/quarto.npz entrada/analise.npz
MATTE_CACHE=entrada/recorte python3 mundo.py entrada/v.mp4 entrada/analise.npz cenarios modelos/selfie_multiclass.tflite saida/mundo_sem_audio.mp4
ffmpeg -loglevel error -y -i saida/mundo_sem_audio.mp4 -i entrada/v.mp4 -map 0:v -map 1:a -c copy -movflags +faststart saida/voa_nas_asas_mundo.mp4
echo "Pronto: saida/voa_nas_asas_mundo.mp4"

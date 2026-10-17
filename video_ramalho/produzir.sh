#!/usr/bin/env bash
# Pipeline completo numa só cadeia: análise → render final → 8 testes.
# Cada etapa começa quando a anterior termina (sem laço de espera por nome de processo,
# que pode casar com o próprio comando e travar). Para no primeiro erro.
# Uso: ./produzir.sh [de] [ate]   (padrão 0 25)
set -euo pipefail
cd "$(dirname "$0")"
DE=${1:-0}; ATE=${2:-25}
mkdir -p _render
etapa() { echo "[$(date +%H:%M:%S)] $*" | tee -a _render/producao.log; }

etapa "análise (cenas já em cache são puladas)"
python3 analisar.py cena01 cena02 cena03 cena04 cena05 cena06 > _render/analise.log 2>&1
etapa "profundidade (cenas já em cache são puladas)"
python3 profundidade.py cena01 cena02 cena03 cena04 cena05 cena06 > _render/profund.log 2>&1
etapa "render final ${DE}–${ATE}s"
python3 render.py --final --de "$DE" --ate "$ATE" --saida Ramalho_Fogoes.mp4 > _render/final.log 2>&1
etapa "testes"
python3 testes.py Ramalho_Fogoes.mp4 --de "$DE" --ate "$ATE" --final > _render/testes.log 2>&1
etapa "pronto: todos os testes passaram"

#!/usr/bin/env bash
# Pipeline numa só cadeia, sem laço de espera por nome de processo (que pode casar com o próprio comando).
# Para no primeiro erro.
#
#   ./produzir.sh previa   análise → profundidade → prévia (_render/previa.jpg, ~1 min)
#   ./produzir.sh final    render completo → 8 testes   (só depois de conferir a prévia)
#
# O render final recusa rodar se render.py/efeitos3d.py/roteiro mudaram depois da última prévia:
# erro de composição tem que aparecer na prévia, não depois do render inteiro.
set -euo pipefail
cd "$(dirname "$0")"
MODO=${1:-previa}; DE=${2:-0}; ATE=${3:-25}
mkdir -p _render
etapa() { echo "[$(date +%H:%M:%S)] $*" | tee -a _render/producao.log; }

if [ "$MODO" = previa ]; then
  etapa "análise (cenas já em cache são puladas)"
  python3 analisar.py cena01 cena02 cena03 cena04 cena05 cena06 > _render/analise.log 2>&1
  etapa "profundidade (cenas já em cache são puladas)"
  python3 profundidade.py cena01 cena02 cena03 cena04 cena05 cena06 > _render/profund.log 2>&1
  etapa "prévia de quadros-chave"
  python3 previa.py > _render/previa.log 2>&1
  etapa "prévia pronta: conferir _render/previa.jpg antes de ./produzir.sh final"
elif [ "$MODO" = final ]; then
  for f in render.py efeitos3d.py roteiro.json; do
    if [ ! -f _render/previa.jpg ] || [ "$f" -nt _render/previa.jpg ]; then
      echo "ERRO: $f mudou depois da última prévia. Rode ./produzir.sh previa e confira antes." >&2; exit 2
    fi
  done
  etapa "render final ${DE}–${ATE}s"
  python3 render.py --final --de "$DE" --ate "$ATE" --saida Ramalho_Fogoes.mp4 > _render/final.log 2>&1
  etapa "testes"
  python3 testes.py Ramalho_Fogoes.mp4 --de "$DE" --ate "$ATE" --final > _render/testes.log 2>&1
  etapa "pronto: todos os testes passaram"
else
  echo "uso: ./produzir.sh previa | final [de] [ate]" >&2; exit 1
fi

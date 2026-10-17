"""Prévia ANTES do render completo: quadros-chave em resolução final, com legendas, numa folha de contato.

Renderiza só ~35 quadros (≈1 min): início, meio e fim de cada cena + o pico de cada efeito 3D
(palavra + 0,35 s) + a tela final. A folha é conferida a olho antes de gastar o render inteiro;
problemas de composição (camada duplicada, objeto feio, texto sobre texto) aparecem aqui.

Uso: python3 previa.py   →  _render/previa.jpg
"""
import os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import render as R

OUT = os.path.join(R.HERE, "_render")
FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 26)
W, H = R.tamanho(True)


def momentos():
    ts = []
    for nome, a, b, *_ in R.CENAS:
        ts += [(a + 0.15, f"{nome} início"), ((a + b) / 2, f"{nome} meio"), (b - 0.15, f"{nome} fim")]
    efeitos = [("amarela", "amarela"), ("falhando", "Falhando"), ("acender", "acender?"), ("conserto", "Concerto"),
               ("regulagem", "regulagem"), ("limpeza", "limpeza"), ("conversao", "conversão"), ("instalacao", "Instalação"),
               ("industrial", "industrial."), ("bem feito", "bem"), ("curitiba", "Curitiba"), ("whatsapp", "WhatsApp")]
    ts += [(R.palavra(p) + 0.35, f"efeito {n}") for n, p in efeitos]
    ts += [(R.palavra("Ramalho", 0) + 0.35, "efeito ramalho"), (R.T_AZUL + 0.35, "efeito chama azul")]
    return sorted(ts)


def main():
    os.makedirs(OUT, exist_ok=True)
    ass = os.path.join(OUT, "legendas.ass")
    R.gerar_ass(ass, W, H)
    tiles, cache_fr = [], {}
    for t, rot in momentos():
        fr = (np.clip(R.render_quadro(t, True, cache_fr), 0, 1) * 255).astype(np.uint8)
        png = os.path.join(OUT, "_previa_q.png")
        Image.fromarray(fr).save(png)
        # legendas no mesmo instante: o filtro ass usa o timestamp do quadro
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", png, "-vf", f"setpts=PTS+{t:.3f}/TB,ass={ass}",
                        "-frames:v", "1", png], check=True)
        im = Image.open(png).convert("RGB").resize((270, 480))
        tile = Image.new("RGB", (270, 512), (15, 15, 15)); tile.paste(im, (0, 32))
        ImageDraw.Draw(tile).text((4, 2), f"{t:.2f}s {rot}"[:22], font=FONT, fill=(255, 220, 60))
        tiles.append(tile)
    cols = 8
    folha = Image.new("RGB", (270 * cols, 512 * ((len(tiles) + cols - 1) // cols)))
    for j, tl in enumerate(tiles):
        folha.paste(tl, ((j % cols) * 270, (j // cols) * 512))
    folha.save(os.path.join(OUT, "previa.jpg"), quality=85)
    print("ok _render/previa.jpg", len(tiles), "quadros")


if __name__ == "__main__":
    main()

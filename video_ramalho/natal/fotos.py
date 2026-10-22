"""Fotos reais dos fogões (enviadas pelo cliente) em porta-retratos de Natal, para entrar no vídeo.

As fotos ficam em cache/fotos_natal/ (fora do git). Cada recorte evita marcas de fabricante
(ex.: "Consul" no painel, "STYLE" na frente do forno). Saída: cache/fotos_natal/q_NN.png (RGBA).

Uso: python3 natal/fotos.py
"""
import os
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(os.path.dirname(HERE), "cache", "fotos_natal")

# arquivo, recorte (x0, y0, x1, y1) em 4:5, sem marcas
FOTOS = [
    ("f871cb40-image.jpg", (60, 250, 1180, 1600)),   # cooktop preto, chama azul
    ("9fe13717-image.jpg", (0, 76, 963, 1280)),       # cooktop inox
    ("9a6fa56d-image.jpg", (0, 300, 900, 1425)),      # industrial com grelhas
    ("becda053-image.jpg", (0, 380, 880, 1480)),      # cooktop 5 bocas (sem o painel com a marca)
    ("0e119f0e-image.jpg", (100, 300, 1100, 1550)),   # industrial inox limpo
    ("db52567e-image.jpg", (80, 300, 1120, 1600)),    # industrial com chama regulada
    ("767dddb2-image.jpg", (100, 300, 900, 1300)),    # fogão inox (sem o painel com a marca)
]
FW, FH = 400, 500   # tamanho da foto dentro da moldura
BORDA, BASE = 22, 70  # moldura estilo polaroide (base mais larga)


def laco(d, cx, cy, s):
    """Laço vermelho de Natal centrado em (cx, cy)."""
    verm, esc = (205, 25, 35, 255), (140, 10, 20, 255)
    d.polygon([(cx, cy), (cx - 2.2 * s, cy - 1.1 * s), (cx - 2.0 * s, cy + 1.0 * s)], fill=verm, outline=esc)
    d.polygon([(cx, cy), (cx + 2.2 * s, cy - 1.1 * s), (cx + 2.0 * s, cy + 1.0 * s)], fill=verm, outline=esc)
    d.polygon([(cx - 0.3 * s, cy), (cx - 1.3 * s, cy + 2.4 * s), (cx - 0.5 * s, cy + 2.1 * s)], fill=esc)
    d.polygon([(cx + 0.3 * s, cy), (cx + 1.3 * s, cy + 2.4 * s), (cx + 0.5 * s, cy + 2.1 * s)], fill=esc)
    d.ellipse([cx - 0.55 * s, cy - 0.55 * s, cx + 0.55 * s, cy + 0.55 * s], fill=(235, 45, 50, 255), outline=esc)


def quadro(arq, caixa):
    foto = Image.open(os.path.join(PASTA, arq)).convert("RGB").crop(caixa).resize((FW, FH), Image.LANCZOS)
    w, h = FW + 2 * BORDA, FH + BORDA + BASE
    m = 40  # margem para sombra e laço
    out = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    sombra = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle([m + 8, m + 12, m + w + 8, m + h + 12], 10, fill=(0, 0, 0, 140))
    out.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle([m, m, m + w, m + h], 10, fill=(250, 246, 236, 255), outline=(212, 168, 60, 255), width=5)
    out.paste(foto, (m + BORDA, m + BORDA))
    d.rectangle([m + BORDA, m + BORDA, m + BORDA + FW, m + BORDA + FH], outline=(212, 168, 60, 255), width=2)
    # azevinho na base: duas folhas e frutinhas
    bx, by = m + w // 2, m + h - BASE // 2 + 4
    for sx in (-1, 1):
        d.ellipse([bx + sx * 8 - 22, by - 9, bx + sx * 8 + 22, by + 9] if sx > 0 else [bx - 30, by - 9, bx + 14, by + 9],
                  fill=(30, 120, 50, 255))
    for dx in (-7, 0, 7):
        d.ellipse([bx + dx - 6, by - 14, bx + dx + 6, by - 2], fill=(210, 20, 30, 255))
    laco(d, m + w // 2, m + 6, 22)
    return out


if __name__ == "__main__":
    for i, (arq, caixa) in enumerate(FOTOS, 1):
        quadro(arq, caixa).save(os.path.join(PASTA, f"q_{i:02d}.png"))
    print(len(FOTOS), "quadros em", PASTA)

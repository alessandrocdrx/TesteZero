"""Cartão final em tela cheia (1080×1920): logo, Técnico Marco, WhatsApp, Facebook, Curitiba e Região.

O logo (cache/fotos_natal/logo.png, autorizado) foi recortado do flyer do cliente; fica fora do git.
Saída: cache/fotos_natal/cartao_final.png

Uso: python3 natal/cartao.py
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(os.path.dirname(HERE), "cache", "fotos_natal")
W, H = 1080, 1920
NEGRITO = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
OURO, BRANCO, AMARELO, VERDE, AZUL = (226, 184, 72), (255, 255, 255), (255, 206, 40), (60, 214, 110), (120, 180, 255)


def fonte(px):
    return ImageFont.truetype(NEGRITO, px)


def texto(d, y, s, px, cor, contorno=6):
    f = fonte(px)
    w = d.textlength(s, font=f)
    d.text(((W - w) / 2, y), s, font=f, fill=cor, stroke_width=contorno, stroke_fill=(10, 14, 40))


def cartao():
    # fundo: azul-noite com brilho vermelho embaixo, flocos de neve
    yy = np.linspace(0, 1, H)[:, None]
    xx = np.linspace(-1, 1, W)[None, :]
    topo, baixo = np.array([10, 22, 62]), np.array([120, 14, 26])
    mist = np.clip(yy ** 1.6, 0, 1)[..., None]
    img = topo * (1 - mist) + baixo * mist
    img = img * (1 - 0.25 * xx ** 2)[..., None]
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
    neve = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dn = ImageDraw.Draw(neve)
    rng = np.random.default_rng(7)
    for _ in range(260):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1.5, 5)
        dn.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, int(rng.uniform(60, 180))))
    im.alpha_composite(neve.filter(ImageFilter.GaussianBlur(0.8)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([34, 34, W - 34, H - 34], 40, outline=OURO, width=6)
    d.rounded_rectangle([50, 50, W - 50, H - 50], 32, outline=(*OURO, 120), width=2)

    logo = Image.open(os.path.join(PASTA, "logo.png")).convert("RGBA")
    lw = 900
    logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    im.alpha_composite(logo, ((W - lw) // 2, 250))

    texto(d, 640, "Técnico Marco", 86, BRANCO)
    d.line([(240, 775), (W - 240, 775)], fill=OURO, width=3)
    texto(d, 820, "WhatsApp", 64, VERDE)
    texto(d, 912, "(41) 98485-1317", 100, AMARELO, 8)
    texto(d, 1100, "Facebook", 64, AZUL)
    texto(d, 1185, "/ramalhofogoes", 96, BRANCO)
    d.line([(240, 1330), (W - 240, 1330)], fill=OURO, width=3)
    texto(d, 1365, "Curitiba e Região", 62, BRANCO)
    texto(d, 1470, "Feliz Natal!", 92, (255, 90, 90), 7)
    return im.convert("RGB")


if __name__ == "__main__":
    cartao().save(os.path.join(PASTA, "cartao_final.png"))
    print("ok")

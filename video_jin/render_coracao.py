"""Renderiza o vídeo animado 'Pra você' na bandeira trans, sincronizado por timestamps de palavras."""
import json, math, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
BLUE, PINK, WHITE = (91, 206, 250), (245, 169, 184), (255, 255, 255)
INK = (58, 36, 92)
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SERIF_I = "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"

cards_path, audio, out = sys.argv[1], sys.argv[2], sys.argv[3]
cards = json.load(open(cards_path))  # [{"start":s,"end":e,"lines":[...],"big":bool}]
total = cards[-1]["end"] + 3.0

def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
def ease(t): t = max(0, min(1, t)); return t * t * (3 - 2 * t)

# bandeira ondulando (pré-calcula faixa por coluna em resolução reduzida)
SW, SH = W // 4, H // 4
def flag(t):
    im = Image.new("RGB", (SW, SH)); px = im.load()
    cols = [BLUE, PINK, WHITE, PINK, BLUE]
    for x in range(SW):
        off = 6 * math.sin(x / 28 + t * 1.6) + 3 * math.sin(x / 11 - t * 2.3)
        shade = 1 + 0.06 * math.sin(x / 28 + t * 1.6 + 1.2)
        for y in range(SH):
            yy = (y + off) / SH * 5
            i = max(0, min(4, int(yy)))
            c = cols[i]
            px[x, y] = tuple(min(255, int(v * shade)) for v in c)
    return im.resize((W, H), Image.BILINEAR)

def heart(d, cx, cy, s, fill):
    pts = []
    for k in range(60):
        a = k / 60 * 2 * math.pi
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((cx + x * s / 16, cy - y * s / 16))
    d.polygon(pts, fill=fill)

random.seed(7)
parts = [dict(x=random.uniform(0, W), y=random.uniform(0, H), s=random.uniform(10, 34),
              v=random.uniform(40, 110), ph=random.uniform(0, 6.28),
              c=random.choice([(255, 255, 255), (255, 214, 224), (210, 240, 255)]))
         for _ in range(38)]

fonts = {}
def font(path, size):
    k = (path, size)
    if k not in fonts: fonts[k] = ImageFont.truetype(path, size)
    return fonts[k]

def text_layer(card, t):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    big = card.get("big")
    f = font(SERIF_I if card.get("italic") else SERIF, 120 if big else 62)
    lines = card["lines"]
    lh = f.size * 1.4
    y0 = (H - lh * len(lines)) / 2
    fade_out = ease((card["end"] + 0.35 - t) / 0.35)
    # painel
    pa = ease((t - card["start"] + 0.15) / 0.4) * fade_out
    if pa > 0 and not card.get("nopanel"):
        d.rounded_rectangle([70, y0 - 70, W - 70, y0 + lh * len(lines) + 50], radius=48,
                            fill=(255, 255, 255, int(150 * pa)))
    n = len(lines)
    span = max(0.01, card["end"] - card["start"])
    for i, l in enumerate(lines):
        ls = card["start"] + span * i / n * 0.85
        a = ease((t - ls) / 0.6) * fade_out
        if a <= 0: continue
        bb = d.textbbox((0, 0), l, font=f)
        x = (W - (bb[2] - bb[0])) / 2
        y = y0 + i * lh + 30 * (1 - a)
        d.text((x, y), l, font=f, fill=INK + (int(255 * a),),
               stroke_width=3 if big else 0, stroke_fill=(255, 255, 255, int(255 * a)))
    return ov

p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio,
    "-filter_complex", f"[1:a]afade=t=out:st={total-1.5}:d=1.5[a]",
    "-map", "0:v", "-map", "[a]", "-t", f"{total:.2f}",
    "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], stdin=subprocess.PIPE)

flag_cache = {}
for fr in range(int(total * FPS)):
    t = fr / FPS
    key = round(t * 15)  # bandeira a 15fps de animação basta
    if key not in flag_cache:
        flag_cache.clear(); flag_cache[key] = flag(key / 15)
    base = flag_cache[key].convert("RGBA")
    pl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(pl)
    for q in parts:
        y = (q["y"] - q["v"] * t) % (H + 100) - 50
        x = q["x"] + 25 * math.sin(t * 0.8 + q["ph"])
        al = int(110 + 70 * math.sin(t * 2 + q["ph"]))
        heart(d, x, y, q["s"], q["c"] + (al,))
    base = Image.alpha_composite(base, pl.filter(ImageFilter.GaussianBlur(1.2)))
    ta = t - 1.2  # narração começa em 1.2s
    for c in cards:
        if c["start"] - 0.2 <= ta <= c["end"] + 0.4:
            base = Image.alpha_composite(base, text_layer(c, ta))
    g = ease(t / 1.0) * ease((total - t) / 1.5)
    img = base.convert("RGB")
    if g < 1: img = Image.blend(Image.new("RGB", (W, H)), img, g)
    p.stdin.write(img.tobytes())
p.stdin.close(); p.wait(); print("ok", p.returncode)

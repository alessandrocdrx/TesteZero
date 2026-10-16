"""Vídeo cinematográfico na bandeira trans (versão Nij, legendas sincronizadas pela voz).

Efeitos: bandeira em tecido ondulando com luz, zoom lento, raios de luz, bokeh,
brilhos cintilantes, corações subindo, explosões de luz, giro da bandeira
("de qualquer lado ela está certa"), pulsação de coração no clímax,
texto que surge do desfoque com brilho, vinheta e granulação de filme.

Uso: python3 render.py cartelas.json trilha.mp3 saida.mp4 [--preview SEG]
"""
import json, math, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
w, h = W // 2, H // 2  # camada de fundo em meia resolução
BLUE, PINK, WHITE = (91, 206, 250), (245, 169, 184), (255, 255, 255)
GOLD = (255, 214, 120)
FONT = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
FONT_I = "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"
FONT_SYM = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

cards = json.load(open(sys.argv[1]))
audio, out = sys.argv[2], sys.argv[3]
total = cards[-1]["end"] + 3.0
preview = None
if "--preview" in sys.argv:
    preview = float(sys.argv[sys.argv.index("--preview") + 1])


def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


# ---------- fundo (meia resolução, numpy) ----------
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
COLS = np.array([BLUE, PINK, WHITE, PINK, BLUE], np.float32) / 255
cx, cy = w / 2, h / 2
vign = 1 - 0.40 * (((xx - cx) / w) ** 2 + ((yy - cy) / h) ** 2) * 2.2
vign = np.clip(vign, 0.25, 1)[..., None]
text_shade = np.exp(-(((xx - cx) / (w * 0.55)) ** 2 + ((yy - cy) / (h * 0.28)) ** 2))[..., None]
ray_ang = np.arctan2(yy + 120, xx - w * 0.15)
ray_fall = np.exp(-np.hypot(xx - w * 0.15, yy + 120) / (h * 0.9))


def sprite_disk(r, soft):
    s = int(r * 2 + 4)
    g = np.mgrid[0:s, 0:s].astype(np.float32) - s / 2
    d = np.hypot(g[0], g[1])
    return np.clip((r - d) / soft, 0, 1) * (0.55 + 0.45 * np.clip(d / r, 0, 1))  # borda mais viva


def sprite_heart(sz):
    im = Image.new("L", (sz * 2, sz * 2), 0)
    d = ImageDraw.Draw(im)
    pts = []
    for k in range(80):
        a = k / 80 * 2 * math.pi
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((sz + x * sz / 18, sz - y * sz / 18))
    d.polygon(pts, fill=255)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255


def sprite_star(sz):
    g = np.mgrid[0:sz * 2, 0:sz * 2].astype(np.float32) - sz
    ax, ay = np.abs(g[1]), np.abs(g[0])
    s = np.exp(-ax / 1.6) * np.exp(-ay / sz * 3) + np.exp(-ay / 1.6) * np.exp(-ax / sz * 3)
    s += np.exp(-(ax ** 2 + ay ** 2) / (sz * 0.6) ** 2)
    return np.clip(s, 0, 1)


def add_sprite(img, spr, x, y, color, a):
    sh, sw = spr.shape
    x0, y0 = int(x - sw / 2), int(y - sh / 2)
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(w, x0 + sw), min(h, y0 + sh)
    if xa >= xb or ya >= yb:
        return
    s = spr[ya - y0:yb - y0, xa - x0:xb - x0, None] * a
    img[ya:yb, xa:xb] += s * np.array(color, np.float32)


random.seed(11)
bokeh = [dict(x=random.uniform(0, w), y=random.uniform(0, h), r=random.uniform(14, 38),
              v=random.uniform(4, 14), ph=random.uniform(0, 6.3),
              c=random.choice([(1, .9, .95), (.85, .95, 1), (1, 1, 1), (1, .92, .75)])) for _ in range(16)]
for b in bokeh:
    b["spr"] = sprite_disk(b["r"], 3.0)
hearts = [dict(x=random.uniform(0, w), y=random.uniform(0, h), s=random.choice([8, 11, 15]),
               v=random.uniform(18, 45), ph=random.uniform(0, 6.3),
               c=random.choice([(1, 1, 1), (1, .8, .87), (.8, .93, 1)])) for _ in range(26)]
heart_spr = {s: sprite_heart(s) for s in (8, 11, 15)}
stars = [dict(x=random.uniform(30, w - 30), y=random.uniform(h * .2, h * .8), s=random.choice([10, 14, 20]),
              f=random.uniform(.6, 1.6), ph=random.uniform(0, 6.3)) for _ in range(22)]
star_spr = {s: sprite_star(s) for s in (10, 14, 20)}

# eventos ao longo do tempo
bursts = [c["start"] for c in cards if c.get("fx") == "burst"] + [x for c in cards for x in c.get("burst_at", [])]
flips = [c["start"] for c in cards if c.get("fx") == "flip"]
hearts_fx = [(c["start"], c["end"]) for c in cards if c.get("fx") == "heart"]


def heartbeat(t):
    for a, b in hearts_fx:
        if a - 0.1 <= t <= b + 0.6:
            p = (t - a) % 0.95
            return math.exp(-p * 9) + 0.7 * math.exp(-max(0, p - 0.28) * 9) * (p > 0.28)
    return 0.0


def background(t, text_presence):
    zoom = 1.0 + 0.10 * (t / total) + 0.025 * heartbeat(t)
    X = (xx - cx) / zoom + cx
    Y = (yy - cy) / zoom + cy
    # giro da bandeira: compressão vertical cos() — simétrica, volta igual
    flipk = 1.0
    for f in flips:
        if f <= t <= f + 2.2:
            flipk = math.cos(math.pi * ease((t - f) / 2.2) * 2)  # dá uma volta inteira
    if flipk != 1.0:
        s = max(abs(flipk), 0.03)
        Y = (Y - cy) / s + cy
    ph = X / 70 + t * 1.3 + Y / 230
    ph2 = X / 33 - t * 2.0
    off = 10 * np.sin(ph) + 4 * np.sin(ph2)
    idx = np.clip(((Y + off) / h * 5).astype(np.int32), 0, 4)
    img = COLS[idx] * 1.04 * (1 + 0.11 * np.cos(ph) + 0.05 * np.cos(ph2))[..., None]
    if flipk != 1.0:
        img = img * ((Y >= 0) & (Y < h))[..., None] * (0.55 + 0.45 * abs(flipk))
    # raios de luz
    rays = (0.5 + 0.5 * np.sin(ray_ang * 22 + t * 0.25)) ** 8 * ray_fall
    img += rays[..., None] * np.array([1, .95, .9], np.float32) * (0.35 + 0.2 * math.sin(t * 0.4))
    # luz quente que passeia
    lx = w * (0.5 + 0.45 * math.sin(t * 0.13)); ly = h * (0.3 + 0.25 * math.sin(t * 0.09 + 1))
    leak = np.exp(-((xx - lx) ** 2 + (yy - ly) ** 2) / (2 * (w * 0.45) ** 2))
    img += leak[..., None] * np.array([.25, .12, .16], np.float32)
    # escurece o centro quando há texto (legibilidade, clima de cinema)
    img *= 1 - text_presence * (0.06 + 0.40 * text_shade)
    for b in bokeh:
        y = (b["y"] - b["v"] * t) % (h + 80) - 40
        x = b["x"] + 12 * math.sin(t * 0.3 + b["ph"])
        add_sprite(img, b["spr"], x, y, b["c"], 0.07 + 0.04 * math.sin(t + b["ph"]))
    for q in hearts:
        y = (q["y"] - q["v"] * t) % (h + 60) - 30
        x = q["x"] + 14 * math.sin(t * 0.9 + q["ph"])
        add_sprite(img, heart_spr[q["s"]], x, y, q["c"], 0.45 + 0.25 * math.sin(t * 2 + q["ph"]))
    for st in stars:
        tw = max(0.0, math.sin(t * st["f"] * 2 + st["ph"])) ** 6
        if tw > 0.02:
            add_sprite(img, star_spr[st["s"]], st["x"], st["y"], (1, .97, .9), tw * 0.9)
    # explosões de luz
    for bt in bursts:
        d = t - bt
        if -0.3 <= d <= 2.0:
            k = ease((d + 0.3) / 0.3) * math.exp(-max(0, d) * 2.2)
            r = w * (0.25 + 0.9 * max(0, d))
            glow = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * r * r))
            img += glow[..., None] * k * np.array([1, .93, .97], np.float32) * 0.65
    img += heartbeat(t) * 0.07
    img *= vign
    return img


# ---------- texto (resolução cheia) ----------
_fonts = {}


def font(path, size):
    if (path, size) not in _fonts:
        _fonts[(path, size)] = ImageFont.truetype(path, size)
    return _fonts[(path, size)]


def make_line(text, f, color, glow_color):
    bb = f.getbbox(text)
    pad = 50
    im = Image.new("RGBA", (bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), text, font=f, fill=color + (255,))
    a = np.asarray(im, np.float32)[..., 3] / 255
    sharp = a
    blur = np.asarray(im.getchannel("A").filter(ImageFilter.GaussianBlur(9)), np.float32) / 255
    glow = np.asarray(im.getchannel("A").filter(ImageFilter.GaussianBlur(20)), np.float32) / 255
    shadow = np.asarray(im.getchannel("A").filter(ImageFilter.GaussianBlur(7)), np.float32) / 255
    return dict(sharp=sharp, blur=blur, glow=glow, shadow=shadow,
                color=np.array(color, np.float32) / 255, glowc=np.array(glow_color, np.float32) / 255,
                w=im.width, h=im.height)


TINTS = {"gold": ((255, 205, 90), (255, 150, 40)), "blue": (BLUE, BLUE), "pink": (PINK, PINK), "white": (WHITE, (255, 240, 250))}


def build_card(c):
    kind = c.get("kind", "normal")
    lines = []
    if c.get("year"):
        lines.append((c["year"], font(FONT, 64), GOLD, (255, 170, 60)))
    bigs = c.get("line_big", [kind == "big"] * len(c["lines"]))
    for i, l in enumerate(c["lines"]):
        if bigs[i]:
            path = FONT_SYM if "♥" in l else FONT_I
            f = font(path, 150 if "♥" in l else 124)
        elif kind == "end":
            f = font(FONT_I if i == 0 else FONT, 58 if i == 0 else 66)
        else:
            f = font(FONT_I if c.get("italic") else FONT, 70)
        glowc = PINK if i % 2 == 0 else BLUE
        col = WHITE
        if c.get("tint"):
            tc, glowc = TINTS[c["tint"]]
            if bigs[i] or c["tint"] == "gold":
                col = tc if c["tint"] == "gold" else WHITE
        if "♥" in l:
            col, glowc = PINK, PINK
        lines.append((l, f, col, glowc))
    built = [make_line(*x) for x in lines]
    gap = -26
    total_h = sum(b["h"] for b in built) + gap * (len(built) - 1)
    y = (H - total_h) / 2
    n = len(built)
    span = c["end"] - c["start"]
    for i, b in enumerate(built):
        b["x"] = (W - b["w"]) // 2
        b["y"] = int(y)
        y += b["h"] + gap
        if c.get("line_starts"):
            b["t0"] = c["line_starts"][min(i, len(c["line_starts"]) - 1)]
        else:
            b["t0"] = c["start"] + (span * 0.75) * i / max(1, n)
    c["_built"] = built


for c in cards:
    build_card(c)


def draw_text(frame, t):
    for c in cards:
        if not (c["start"] - 0.3 <= t <= c["end"] + 0.8):
            continue
        out_k = ease((c["end"] + 0.6 - t) / 0.6)
        pulse = heartbeat(t) if c.get("fx") == "heart" else 0.0
        for b in c["_built"]:
            a = ease((t - b["t0"]) / 0.9) * out_k
            if a <= 0.001:
                continue
            m = ease((t - b["t0"]) / 0.7) * out_k  # desfocado -> nítido
            flare = math.exp(-max(0, t - b["t0"] - 0.2) * 2.5) * (t >= b["t0"])
            rise = int(28 * (1 - ease((t - b["t0"]) / 0.9)) - 22 * (1 - out_k))
            x0, y0 = b["x"], b["y"] + rise
            x1, y1 = x0 + b["w"], y0 + b["h"]
            if y0 < 0 or y1 > H:
                continue
            reg = frame[y0:y1, x0:x1]
            alpha = (b["sharp"] * m + b["blur"] * (1 - m)) * a
            reg *= (1 - 0.82 * b["glow"][..., None] * a) * (1 - 0.85 * b["shadow"][..., None] * a)
            reg += b["glow"][..., None] * b["glowc"] * a * (0.25 + 0.8 * flare + 0.7 * pulse)
            reg[:] = reg * (1 - alpha[..., None]) + b["color"] * alpha[..., None]


def text_presence(t):
    p = 0.0
    for c in cards:
        p = max(p, ease((t - c["start"] + 0.4) / 0.6) * ease((c["end"] + 0.8 - t) / 0.8))
    return p


# ---------- grão de filme ----------
rng = np.random.default_rng(3)
grains = [rng.normal(0, 0.010, (h, w, 1)).astype(np.float32) for _ in range(8)]

end_t = preview if preview else total
cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
       "-r", str(FPS), "-i", "-", "-i", audio,
       "-filter_complex", f"[1:a]apad,afade=t=out:st={total - 2.5}:d=2.5[a]",
       "-map", "0:v", "-map", "[a]", "-t", f"{end_t:.2f}",
       "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-tune", "film", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
nframes = int(end_t * FPS)
for fr in range(nframes):
    t = fr / FPS
    bg = background(t, text_presence(t))
    bg += grains[fr % 8]
    bg8 = (np.clip(bg, 0, 1) * 255).astype(np.uint8)
    frame = np.asarray(Image.fromarray(bg8).resize((W, H), Image.BILINEAR), np.float32) / 255
    draw_text(frame, t)
    g = ease(t / 1.2) * ease((total - t) / 2.5)
    frame = np.clip(frame * g, 0, 1)
    p.stdin.write((frame * 255).astype(np.uint8).tobytes())
    if fr % 300 == 0:
        print(f"{t:.0f}s / {end_t:.0f}s", flush=True)
p.stdin.close()
p.wait()
print("ok", p.returncode)

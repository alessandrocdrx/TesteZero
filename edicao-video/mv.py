"""Pop/K-pop MV style edit. Her image and voice stay untouched: only framing, cuts and overlays.
Usage: mv.py SRC OUT_SILENT_MP4"""
import math
import os
import random
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + "/"
ANTON = FD + "Anton-Regular.ttf"
ARCHIVO = FD + "ArchivoBlack-Regular.ttf"
DEJAVU_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

W, H, FPS, DUR = 1080, 1920, 30, 85.0
FACE = (540, 600)  # face centre in output coords

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PINK = (255, 64, 160)
YELLOW = (255, 222, 60)
CYAN = (70, 220, 255)
GOLD = (255, 196, 90)

# ---------- timeline ----------
LYRICS = [  # start, end, pt-br, original
    (2.4, 7.6, "Voa nas asas do vento", "Улетай на крыльях ветра"),
    (7.8, 15.0, "até a terra natal, nossa canção querida", "ты в край родной, родная песня наша"),
    (15.3, 23.8, "para onde te cantávamos livres", "туда, где мы тебя свободно пели"),
    (24.0, 31.4, "onde éramos tão felizes contigo", "где было так привольно нам с тобою"),
    (31.6, 39.5, "lá, o sol brilha tão forte", "там так ярко солнце светит"),
    (39.7, 46.7, "banhando de luz as montanhas de casa", "родные горы светом заливая"),
    (46.9, 55.4, "nos vales florescem as rosas", "в долинах пышно розы расцветают"),
    (55.6, 63.5, "e rouxinóis cantam nas matas verdes", "и соловьи поют в лесах зелёных"),
    (77.0, 82.4, "voa nas asas do vento…", "Улетай на крыльях ветра…"),
]
SECTION_HITS = [15.2, 46.8, 63.8, 77.0]

# camera "cuts": time -> (zoom, x offset, y offset) relative to face
SHOTS = [
    (0.0, 1.12, 0, 0), (2.4, 1.00, 0, 0), (7.8, 1.18, 0, 0), (11.4, 1.32, -20, 0),
    (15.2, 1.00, 0, 0), (19.6, 1.22, 30, 0), (24.0, 1.10, 0, 0), (28.0, 1.32, -30, 0),
    (31.6, 1.00, 0, 0), (35.8, 1.20, 0, 0), (39.7, 1.34, 20, 0), (43.4, 1.08, 0, 0),
    (46.8, 1.25, 0, 0), (55.6, 1.06, 0, 0), (59.6, 1.30, -20, 0),
    (63.8, 1.04, 0, 0), (77.0, 1.18, 0, 0), (80.0, 1.00, 0, 0),
]
SPLIT3 = (51.0, 55.4)
FRAME_IN_FRAME = (72.4, 76.0)
LETTERBOX = (63.8, 77.0)
CONTEXT = [
    (6.6, 10.6, "RÚSSIA · 1890", "Ópera “Príncipe Igor”, de Borodin"),
    (10.6, 15.0, "A HISTÓRIA", "Mulheres cativas, longe de casa, pedem ao vento que leve sua canção até a terra natal."),
]
STICKERS = [  # k-variety style captions: start, end, text, x, y, angle, fill
    (26.4, 29.4, "NO PONTO!", 700, 1000, -8, YELLOW),
    (48.0, 50.6, "UAU", 800, 1160, 8, CYAN),
    (59.8, 62.6, "QUE VOZ…", 330, 1010, -6, PINK),
    (69.0, 72.2, "ARREPIOU", 540, 1240, 4, YELLOW),
]
NAMETAG = (2.8, 6.6)
BAND_Y0 = 1080
BAND = (1 - 0.62 * np.clip(np.linspace(0, 1.6, H - 1080), 0, 1) ** 1.4)[:, None, None].astype(np.float32)
ENDCARD = 82.4


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ---------- sprites ----------
_fc = {}


def F(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size)
    return _fc[k]


def to_np(img):
    return np.array(img)


def text_sprite(text, path, size, fill, stroke=0, stroke_fill=BLACK, shadow=0, angle=0.0, tracking=0):
    f = F(path, size)
    d0 = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    x0, y0, x1, y1 = d0.textbbox((0, 0), text, font=f, stroke_width=stroke)
    pad = 20 + shadow
    img = Image.new("RGBA", (x1 - x0 + pad * 2, y1 - y0 + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if shadow:
        d.text((pad - x0 + shadow, pad - y0 + shadow), text, font=f, fill=(0, 0, 0, 150),
               stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
    d.text((pad - x0, pad - y0), text, font=f, fill=fill + (255,), stroke_width=stroke, stroke_fill=stroke_fill + (255,))
    if angle:
        img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    return to_np(img)


def wrap(text, f, maxw):
    d = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    lines, cur = [], []
    for w in text.split():
        if cur and d.textlength(" ".join(cur + [w]), font=f) > maxw:
            lines.append(cur)
            cur = [w]
        else:
            cur.append(w)
    lines.append(cur)
    return lines


def karaoke_sprites(text, size=78, maxw=900):
    """Returns (dim, bright, word_masks): word i becomes bright when revealed."""
    f = F(ANTON, size)
    lines = wrap(text.upper(), f, maxw)
    d0 = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    space = d0.textlength(" ", font=f)
    lh = int(size * 1.18)
    width = int(max(sum(d0.textlength(w, font=f) for w in ln) + space * (len(ln) - 1) for ln in lines)) + 60
    height = lh * len(lines) + 50
    dim = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    bright = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    dd, db = ImageDraw.Draw(dim), ImageDraw.Draw(bright)
    boxes = []
    for li, ln in enumerate(lines):
        lw = sum(d0.textlength(w, font=f) for w in ln) + space * (len(ln) - 1)
        x = (width - lw) / 2
        y = 20 + li * lh
        for w in ln:
            ww = d0.textlength(w, font=f)
            dd.text((x + 4, y + 5), w, font=f, fill=(0, 0, 0, 90))
            dd.text((x, y), w, font=f, fill=(255, 255, 255, 165), stroke_width=4, stroke_fill=(0, 0, 0, 140))
            db.text((x + 4, y + 5), w, font=f, fill=(0, 0, 0, 170))
            db.text((x, y), w, font=f, fill=WHITE + (255,), stroke_width=4, stroke_fill=(20, 0, 30, 255))
            boxes.append((int(x - 6), int(y - 6), int(x + ww + 10), int(y + lh)))
            x += ww + space
    return to_np(dim), to_np(bright), boxes


def card_sprite(title, body, width=860):
    ft, fb = F(ARCHIVO, 34), F(DEJAVU_B, 38)
    lines = [" ".join(l) for l in wrap(body, fb, width - 90)]
    h = 40 + 46 + 18 + len(lines) * 50 + 30
    img = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, width - 1, h - 1], 22, fill=(12, 8, 20, 185))
    d.rounded_rectangle([0, 0, 14, h - 1], 7, fill=PINK + (255,))
    d.text((44, 34), title, font=ft, fill=PINK + (255,))
    for i, l in enumerate(lines):
        d.text((44, 34 + 46 + 18 + i * 50), l, font=fb, fill=WHITE + (255,))
    return to_np(img)


def nametag_sprite():
    img = Image.new("RGBA", (720, 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 18, 189], fill=PINK + (255,))
    d.text((40, 0), "SASHA KVASHENAYA", font=F(ANTON, 76), fill=WHITE + (255,), stroke_width=3, stroke_fill=(0, 0, 0, 160))
    d.rectangle([40, 112, 40 + 480, 162], fill=WHITE + (255,))
    d.text((54, 116), "VOCAL · @KVASHENAYAKTO", font=F(ARCHIVO, 28), fill=BLACK + (255,))
    return to_np(img)


def paste(frame, spr, cx, cy, scale=1.0, alpha=1.0, anchor="c", reveal=1.0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    if scale != 1.0:
        spr = cv2.resize(spr, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    h, w = spr.shape[:2]
    if reveal < 1.0:  # left-to-right wipe
        spr = spr.copy()
        spr[:, int(w * reveal):, 3] = 0
    x = int(cx - w / 2) if anchor == "c" else int(cx)
    y = int(cy - h / 2)
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return
    s = spr[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    a = s[..., 3:4] / 255 * alpha
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (roi * (1 - a) + s[..., 2::-1] * a).astype(np.uint8)


def pop(t, a, b, ins=0.22, outs=0.15):
    """scale for pop-in with overshoot and quick shrink-out."""
    if t < a or t >= b:
        return 0.0
    k = (t - a) / ins
    s = 1.0 if k >= 1 else 0.4 + 0.6 * ease_out(k) + 0.18 * math.sin(k * math.pi)
    k2 = (b - t) / outs
    return s * (min(1.0, k2) if k2 < 1 else 1.0)


def fade(t, a, b, d=0.25):
    if t < a or t >= b:
        return 0.0
    return min(1.0, (t - a) / d, (b - t) / d)


# ---------- camera ----------
def shot_at(t):
    cur = SHOTS[0]
    for s in SHOTS:
        if t >= s[0]:
            cur = s
    return cur


def frame_zoom(src, z, ox=0, oy=0):
    cx, cy = FACE[0] + ox, FACE[1] + oy
    # keep the crop inside the source frame
    half_w, half_h = W / (2 * z), H / (2 * z)
    cx = min(max(cx, half_w), W - half_w)
    cy = min(max(cy, half_h), H - half_h)
    M = np.float32([[z, 0, W / 2 - z * cx], [0, z, H / 2 - z * cy]])
    return cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def camera(src, t):
    st, z, ox, oy = shot_at(t)
    z = z + 0.012 * (t - st)  # slow drift keeps every shot alive
    if LETTERBOX[0] <= t < LETTERBOX[1]:
        z = 1.04 + 0.26 * ease_in_out((t - LETTERBOX[0]) / (LETTERBOX[1] - LETTERBOX[0]))
    for hit in SECTION_HITS:  # punch-in on each new section
        if hit <= t < hit + 0.45:
            z += 0.18 * (1 - ease_out((t - hit) / 0.45))
    return frame_zoom(src, max(1.0, z), ox, oy)


# ---------- overlays (never on her face) ----------
def screen(img, light):
    a = img.astype(np.float32)
    return (255 - (255 - a) * (255 - light) / 255).astype(np.uint8)


def light_leak(t, strength, color, side):
    sw, sh = W // 6, H // 6
    yy, xx = np.mgrid[0:sh, 0:sw].astype(np.float32)
    px = (0.0 if side == "l" else 1.0) * sw + math.sin(t * 0.7) * sw * 0.15
    py = sh * (0.25 + 0.2 * math.sin(t * 0.45))
    d = np.sqrt((xx - px) ** 2 + ((yy - py) * 0.6) ** 2) / (sw * 0.75)
    g = np.clip(1 - d, 0, 1) ** 2 * strength
    g = cv2.resize(g, (W, H), interpolation=cv2.INTER_CUBIC) * EDGE_MASK
    return g[..., None] * np.array(color[::-1], np.float32)


_ex = np.abs(np.linspace(-1, 1, W))[None, :]
_ey = np.linspace(0, 1, H)[:, None]
_face = np.clip((_ex - 0.42) / 0.4, 0, 1) + np.clip((_ey - 0.62) / 0.3, 0, 1) * 0.5 + np.clip((0.12 - _ey) / 0.12, 0, 1)
EDGE_MASK = np.clip(_face, 0, 1).astype(np.float32)


class Sparkles:
    def __init__(self, n=70, seed=3):
        r = random.Random(seed)
        self.p = []
        for _ in range(n):
            side = r.choice(["l", "r", "b"])
            x = r.uniform(30, 260) if side == "l" else r.uniform(820, 1050) if side == "r" else r.uniform(60, 1020)
            y = r.uniform(200, 1700) if side != "b" else r.uniform(1450, 1850)
            self.p.append((x, y, r.uniform(-30, -90), r.uniform(0, 6.28), r.uniform(4, 11)))

    def draw(self, t, amount):
        layer = np.zeros((H, W, 3), np.float32)
        for x, y, vy, ph, s in self.p:
            yy = (y + vy * t) % H
            tw = (math.sin(t * 5 + ph) + 1) / 2 * amount
            if 250 < x < 830 and yy < 1250:
                continue
            if tw < 0.05:
                continue
            c = np.array([180, 230, 255], np.float32) * tw
            cx, cy = int(x), int(yy)
            L = int(s * 2.6)
            cv2.line(layer, (cx - L, cy), (cx + L, cy), c.tolist(), 2, cv2.LINE_AA)
            cv2.line(layer, (cx, cy - L), (cx, cy + L), c.tolist(), 2, cv2.LINE_AA)
            cv2.circle(layer, (cx, cy), int(s / 2.5), c.tolist(), -1, cv2.LINE_AA)
        return cv2.GaussianBlur(layer, (0, 0), 1.2)


def hit_fx(img, t):
    """flash + brief RGB split on section hits (transition only, ~4 frames)."""
    for hit in SECTION_HITS:
        d = t - hit
        if -0.03 <= d < 0.14:
            k = 1 - (d + 0.03) / 0.17
            s = int(18 * k)
            if s:
                b, g, r = cv2.split(img)
                img = cv2.merge([np.roll(b, -s, 1), g, np.roll(r, s, 1)])
            img = (img.astype(np.float32) * (1 - 0.7 * k) + 255 * 0.7 * k).astype(np.uint8)
    return img


def split3(src, t):
    out = np.full((H, W, 3), 255, np.uint8)
    gut = 10
    cw = (W - 2 * gut) // 3
    crops = [(1.9, -40), (1.45, 0), (1.9, 40)]
    for i, (z, ox) in enumerate(crops):
        appear = SPLIT3[0] + i * 0.12
        if t < appear:
            continue
        v = frame_zoom(src, z, ox, 0)
        strip = v[:, (W - cw) // 2:(W - cw) // 2 + cw]
        k = ease_out((t - appear) / 0.3)
        dy = int((1 - k) * (H if i % 2 == 0 else -H) * 0.4)
        x0 = i * (cw + gut)
        strip = np.roll(strip, dy, axis=0)
        out[:, x0:x0 + cw] = strip
    return out


def frame_in_frame(src, t):
    bg = cv2.GaussianBlur(frame_zoom(src, 1.5), (0, 0), 28)
    bg = (bg.astype(np.float32) * 0.55).astype(np.uint8)
    k = ease_out((t - FRAME_IN_FRAME[0]) / 0.4)
    s = 0.74 + 0.04 * k
    fg = cv2.resize(frame_zoom(src, 1.1), (int(W * s), int(H * s)))
    b = 12
    fg = cv2.copyMakeBorder(fg, b, b, b, b, cv2.BORDER_CONSTANT, value=WHITE)
    ang = -3 * k
    M = cv2.getRotationMatrix2D((fg.shape[1] / 2, fg.shape[0] / 2), ang, 1.0)
    rot = cv2.warpAffine(fg, M, (fg.shape[1], fg.shape[0]), borderValue=(0, 0, 0))
    mask = cv2.warpAffine(np.full(fg.shape[:2], 255, np.uint8), M, (fg.shape[1], fg.shape[0]))
    y0 = (H - fg.shape[0]) // 2 - 40
    x0 = (W - fg.shape[1]) // 2
    roi = bg[y0:y0 + fg.shape[0], x0:x0 + fg.shape[1]]
    m = (mask.astype(np.float32) / 255)[..., None]
    bg[y0:y0 + fg.shape[0], x0:x0 + fg.shape[1]] = (roi * (1 - m) + rot * m).astype(np.uint8)
    return bg


# ---------- main ----------
def main(src_path, out_path):
    cap = cv2.VideoCapture(src_path)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    n = len(frames)

    kara = [karaoke_sprites(pt) for _, _, pt, _ in LYRICS]
    ru = [text_sprite(r, DEJAVU_B, 34, (255, 225, 240), stroke=3, stroke_fill=(30, 0, 40)) for _, _, _, r in LYRICS]
    ctx = [card_sprite(a, b) for _, _, a, b in CONTEXT]
    tag = nametag_sprite()
    stick = [text_sprite(s[2], ARCHIVO, 96, s[6], stroke=12, stroke_fill=WHITE, shadow=10, angle=s[5]) for s in STICKERS]
    hook = [
        text_sprite("ELA CANTOU UMA", ANTON, 92, WHITE, stroke=5, shadow=8),
        text_sprite("ÓPERA RUSSA", ANTON, 150, YELLOW, stroke=7, shadow=10),
        text_sprite("DE 1890", ANTON, 150, YELLOW, stroke=7, shadow=10),
        text_sprite("SÓ COM A VOZ.", ANTON, 120, PINK, stroke=6, stroke_fill=WHITE, shadow=10),
    ]
    lb_text = text_sprite("SEM INSTRUMENTO  ·  SEM AUTOTUNE  ·  SÓ A VOZ", ARCHIVO, 30, WHITE)
    end = [
        text_sprite("VOA NAS ASAS", ANTON, 150, WHITE, stroke=6, shadow=10),
        text_sprite("DO VENTO", ANTON, 190, PINK, stroke=7, stroke_fill=WHITE, shadow=12),
        text_sprite("Borodin · Príncipe Igor (1890)", DEJAVU_B, 36, WHITE, stroke=2),
        text_sprite("VOZ: @KVASHENAYAKTO", ARCHIVO, 40, YELLOW, stroke=3),
        text_sprite("EDIÇÃO: @alessandrocdrx", ARCHIVO, 40, WHITE, stroke=3),
        text_sprite("QUAL PARTE TE ARREPIOU?", ANTON, 84, YELLOW, stroke=5, shadow=8),
    ]
    sparkles = Sparkles()

    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    want = {int(round(x * FPS)) for x in preview}
    enc = None if preview else subprocess.Popen([
        "ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        "-pix_fmt", "yuv420p", out_path], stdin=subprocess.PIPE)

    for i in range(int(DUR * FPS)):
        if preview and i not in want:
            continue
        t = i / FPS
        src = cv2.resize(frames[min(i, n - 1)], (W, H), interpolation=cv2.INTER_LANCZOS4)

        if SPLIT3[0] <= t < SPLIT3[1]:
            img = split3(src, t)
        elif FRAME_IN_FRAME[0] <= t < FRAME_IN_FRAME[1]:
            img = frame_in_frame(src, t)
        else:
            img = camera(src, t)

        # atmosphere at the frame edges
        light = np.zeros((H, W, 3), np.float32)
        if 15.2 <= t < 46.8:
            light += light_leak(t, 0.45, (255, 120, 200), "l")
        if 31.6 <= t < 46.8:
            light += light_leak(t + 2, 0.75 * ease_in_out((t - 31.6) / 4), GOLD, "r")
        if 46.8 <= t < 63.8:
            light += light_leak(t, 0.5, (255, 90, 170), "r") + light_leak(t + 4, 0.4, CYAN, "l")
        if t >= 63.8:
            light += sparkles.draw(t, min(1.0, (t - 63.8) / 1.5))
            light += light_leak(t, 0.5, GOLD, "l" if int(t) % 2 else "r")
        if light.any():
            img = screen(img, np.clip(light, 0, 255))

        # cinematic bars for the climax
        if LETTERBOX[0] <= t < LETTERBOX[1] + 0.4:
            k = ease_out((t - LETTERBOX[0]) / 0.6) if t < LETTERBOX[1] else 1 - ease_out((t - LETTERBOX[1]) / 0.4)
            bar = int(170 * k)
            img[:bar] = 0
            img[H - bar:] = 0
            if k > 0.95:
                paste(img, lb_text, W / 2, H - 85, alpha=fade(t, LETTERBOX[0] + 0.6, LETTERBOX[1]))
        img = hit_fx(img, t)
        if t < ENDCARD:  # dark band behind captions (below her face)
            img[BAND_Y0:] = (img[BAND_Y0:].astype(np.float32) * BAND).astype(np.uint8)

        # hook
        if t < 2.4:
            for j, (spr, a, y) in enumerate(zip(hook, [0.0, 0.2, 0.4, 0.85], [1130, 1265, 1420, 1580])):
                paste(img, spr, W / 2, y, pop(t, a, 2.4))

        # name tag
        if NAMETAG[0] <= t < NAMETAG[1]:
            r = ease_out((t - NAMETAG[0]) / 0.5)
            a = fade(t, NAMETAG[0], NAMETAG[1], 0.3)
            paste(img, tag, 60, 985, anchor="l", reveal=r, alpha=a)

        for (a, b, ttl, _), spr in zip(CONTEXT, ctx):
            if a <= t < b:
                k = ease_out((t - a) / 0.35)
                paste(img, spr, W / 2 - (1 - k) * 80, 300 + spr.shape[0] / 2, alpha=fade(t, a, b, 0.3))

        # lyrics: original on top, PT-BR karaoke below
        for (a, b, _, _), (dim, bright, boxes), r in zip(LYRICS, kara, ru):
            if not (a <= t < b):
                continue
            al = fade(t, a, b, 0.2)
            y = 1440
            if SPLIT3[0] <= t < SPLIT3[1] or FRAME_IN_FRAME[0] <= t < FRAME_IN_FRAME[1]:
                y = 1500
            paste(img, r, W / 2, y - bright.shape[0] / 2 - 26, alpha=al * 0.95)
            # words light up across the first 75% of the line
            k = (t - a) / ((b - a) * 0.75)
            nw = len(boxes)
            lit = min(nw, int(k * nw) + 1)
            spr = dim.copy()
            for wi in range(lit):
                x0, y0, x1, y1 = boxes[wi]
                spr[y0:y1, x0:x1] = bright[y0:y1, x0:x1]
            sc = 1.0 + 0.06 * (1 - ease_out((t - a) / 0.25))
            paste(img, spr, W / 2, y, scale=sc, alpha=al)

        for s, spr in zip(STICKERS, stick):
            if s[0] <= t < s[1]:
                wob = 1 + 0.03 * math.sin(t * 14)
                paste(img, spr, s[3], s[4], pop(t, s[0], s[1]) * wob)

        if t >= ENDCARD:
            k = ease_out((t - ENDCARD) / 0.6)
            blur = cv2.GaussianBlur(img, (0, 0), 1 + 18 * k)
            img = (blur.astype(np.float32) * (1 - 0.45 * k)).astype(np.uint8)
            img = screen(img, np.clip(sparkles.draw(t, 1.0), 0, 255))
            for spr, a, y in zip(end, [0.0, 0.2, 0.6, 0.8, 0.95, 1.3], [640, 820, 1000, 1100, 1170, 1380]):
                paste(img, spr, W / 2, y, pop(t, ENDCARD + a, 999))

        if preview:
            cv2.imwrite(f"{out_path}_{t:05.1f}.png", cv2.resize(img, (270, 480)))
            continue
        enc.stdin.write(img.tobytes())
        if i % 450 == 0:
            print(f"{t:5.1f}s", flush=True)
    if enc:
        enc.stdin.close()
        enc.wait()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

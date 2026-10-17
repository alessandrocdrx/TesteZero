"""'Voa nas asas do vento', with effects that follow the lyrics, her voice and her expressions.
Builds on calmo.py. Every effect lives around her: a mask that tracks her face keeps it untouched,
and the voice is copied bit for bit.
Usage: efeitos.py SRC ANALISE.npz OUT_SILENT_MP4      (PREVIEW="5.5,19,36,51,57,70" for review frames)"""
import math
import os
import random
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import calmo as C  # noqa: E402
from calmo import W, H, FPS, smooth, fade  # noqa: E402

# ---------- the song's images, timed to her voice (seconds in the original take) ----------
WIND = [(0.6, 15.4), (78.2, 85.6)]            # "voa nas asas do vento"
GUSTS = [5.5, 80.6]                           # "ветра" (vento) is sung here
BIRDS = (15.6, 31.8)                          # "para onde te cantávamos livres"
FLOCK_LIFT = 18.8                             # "свободно" (livres)
SUN = (31.4, 47.0)                            # "lá, o sol brilha... banhando de luz"
SUN_BLOOM = 35.8                              # "солнце" (sol)
ROSES = (46.8, 56.0)                          # "nos vales, as rosas se abrem"
ROSE_BURST = 50.7                             # "розы" (rosas)
NIGHTINGALES = (55.4, 63.8)                   # "rouxinóis cantam nas matas verdes"
EMBERS = (63.8, 78.2)                         # her voice alone

# word that turns gold when she sings its Russian twin: lyric index -> (word, time)
GOLD_WORDS = {0: ("vento", 5.5), 2: ("livres,", 18.8), 4: ("sol", 35.8), 5: ("luz", 44.8),
              6: ("rosas", 50.7), 7: ("rouxinóis", 56.3), 8: ("vento…", 80.6)}
GOLD = (255, 214, 150)

SW, SH = W // 2, H // 2  # light effects are drawn at half resolution, then softened


def env_at(a, b, t, fin=1.2, fout=1.2):
    return fade(t, a, b, fin, fout)


# ---------- face protection ----------
class Face:
    def __init__(self, npz):
        d = np.load(npz)
        b = d["boxes"] * 1.5  # 720 -> 1080
        self.cx = b[:, 0] + b[:, 2] / 2
        self.cy = b[:, 1] + b[:, 3] / 2
        self.r = float(np.median(b[:, 2])) * 0.78
        self.smile = d["smile"]
        self.energy = d["energy"]
        yy, xx = np.mgrid[0:SH, 0:SW].astype(np.float32)
        self.yy, self.xx = yy * 2, xx * 2

    def at(self, i):
        i = min(i, len(self.cx) - 1)
        return self.cx[i], self.cy[i]

    def mask(self, i, z=1.0):
        """1 where effects may appear, 0 on her face and hair (with a soft edge)."""
        cx, cy = self.at(i)
        cx = W / 2 + (cx - W / 2) * z
        cy = H * 0.33 + (cy - H * 0.33) * z
        r = self.r * z
        d = np.sqrt(((self.xx - cx) / (r * 0.95)) ** 2 + ((self.yy - cy - r * 0.15) / (r * 1.2)) ** 2)
        m = np.clip((d - 1.0) / 0.35, 0, 1)
        return cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)

    def e(self, t):
        return float(self.energy[min(int(t * FPS), len(self.energy) - 1)])

    def s(self, t):
        return float(self.smile[min(int(t * FPS), len(self.smile) - 1)])


# ---------- effect layers ----------
class Motes:
    """Wind: luminous dust carried left to right, speed and glow follow her voice."""

    def __init__(self, n=160, seed=1):
        r = random.Random(seed)
        self.p = [(r.uniform(0, SW), r.uniform(0, SH), r.uniform(0.4, 1.0), r.uniform(0, 6.28), r.uniform(0.8, 2.2))
                  for _ in range(n)]

    def draw(self, layer, t, amount, energy, gust):
        speed = 18 + 40 * energy + 160 * gust
        for x0, y0, depth, ph, size in self.p:
            x = (x0 + t * speed * depth) % (SW + 40) - 20
            y = y0 + math.sin(t * 0.9 * depth + ph) * 14 + math.sin(x * 0.01 + ph) * 8
            a = amount * (0.55 + 0.8 * energy) * depth * (0.6 + 0.4 * math.sin(t * 3 + ph))
            c = (230 * a, 245 * a, 255 * a)
            cv2.circle(layer, (int(x), int(y)), max(1, int(size * depth * 1.5)), c, -1, cv2.LINE_AA)
            if gust > 0.05:  # streaks only during the gust on "vento"
                L = int(30 * gust * depth)
                cv2.line(layer, (int(x) - L, int(y)), (int(x), int(y)), tuple(v * 0.5 for v in c), 1, cv2.LINE_AA)


class Birds:
    """'livres': a few birds cross the sky above her; the flock lifts when she sings 'свободно'."""

    def __init__(self, seed=4):
        r = random.Random(seed)
        self.b = []
        for k in range(7):
            side = k % 2
            self.b.append(dict(
                start=BIRDS[0] + r.uniform(0, 9), x0=-60 if side == 0 else W + 60, dir=1 if side == 0 else -1,
                y0=r.uniform(70, 230), speed=r.uniform(80, 130), size=r.uniform(24, 38), ph=r.uniform(0, 6.28)))

    def draw(self, img, t, amount, mask):
        for b in self.b:
            dt = t - b["start"]
            if dt < 0:
                continue
            x = b["x0"] + b["dir"] * b["speed"] * dt
            lift = 60 * smooth((t - FLOCK_LIFT) / 3.0)
            y = b["y0"] - lift - dt * 6 + math.sin(dt * 1.3 + b["ph"]) * 10
            if not (-80 < x < W + 80):
                continue
            s = b["size"]
            flap = math.sin(dt * 9 + b["ph"])
            wing = s * (0.35 + 0.45 * flap)
            pts = np.array([[x - s, y - wing], [x - s * 0.45, y - wing * 0.2], [x, y + s * 0.12],
                            [x + s * 0.45, y - wing * 0.2], [x + s, y - wing]], np.int32)
            xi, yi = int(np.clip(x, 0, W - 1)), int(np.clip(y, 0, H - 1))
            a = amount * float(mask[yi, xi]) * 0.85
            if a < 0.02:
                continue
            ov = img.copy()
            cv2.polylines(ov, [pts], False, (34, 28, 26), max(3, int(s / 6)), cv2.LINE_AA)
            cv2.addWeighted(ov, a, img, 1 - a, 0, img)


def sun_rays(layer, t, amount, energy):
    """'o sol brilha tão forte': warm rays from the upper right, blooming on 'солнце'."""
    bloom = math.exp(-((t - SUN_BLOOM) / 1.4) ** 2)
    k = amount * (0.45 + 0.35 * energy + 0.5 * bloom)
    ox, oy = SW * 1.05, -SH * 0.06
    for j in range(9):
        ang = math.radians(118 + j * 7.5 + math.sin(t * 0.25 + j) * 2.0)
        w = math.radians(2.2 + (j % 3))
        L = SH * 1.3
        pts = np.array([[ox, oy], [ox + L * math.cos(ang - w), oy + L * math.sin(ang - w)],
                        [ox + L * math.cos(ang + w), oy + L * math.sin(ang + w)]], np.int32)
        ray = np.zeros_like(layer)
        cv2.fillConvexPoly(ray, pts, (110 * k, 190 * k, 255 * k), cv2.LINE_AA)
        layer += ray * (0.5 + 0.5 * math.sin(t * 0.8 + j * 1.7)) ** 2
    cv2.circle(layer, (int(ox - 20), int(oy + 30)), int(160 + 60 * bloom), (90 * k, 170 * k, 255 * k), -1, cv2.LINE_AA)


class Petals:
    """'as rosas se abrem': rose petals drift down the sides; more fall while she smiles."""

    def __init__(self, n=46, seed=9):
        r = random.Random(seed)
        self.p = []
        for _ in range(n):
            side = r.random() < 0.5
            self.p.append(dict(
                x=r.uniform(20, 330) if side else r.uniform(750, 1060), t0=ROSES[0] + r.uniform(-1, 8.5),
                v=r.uniform(90, 150), sway=r.uniform(20, 55), ph=r.uniform(0, 6.28), rot=r.uniform(-2, 2),
                size=r.uniform(16, 28), col=r.choice([(92, 64, 214), (120, 96, 232), (70, 44, 190), (150, 130, 240)])))
        burst = random.Random(10)
        for _ in range(16):  # the burst on "розы"
            self.p.append(dict(
                x=burst.uniform(40, 1040), t0=ROSE_BURST + burst.uniform(-0.3, 0.6), v=burst.uniform(120, 190),
                sway=burst.uniform(30, 70), ph=burst.uniform(0, 6.28), rot=burst.uniform(-3, 3),
                size=burst.uniform(18, 30), col=burst.choice([(92, 64, 214), (120, 96, 232), (150, 130, 240)])))

    def draw(self, img, t, amount, mask, smile):
        for p in self.p:
            dt = t - p["t0"]
            if dt < 0:
                continue
            y = -40 + p["v"] * dt * (0.8 + 0.4 * smile)
            if y > H + 40:
                continue
            x = p["x"] + math.sin(dt * 1.4 + p["ph"]) * p["sway"]
            xi, yi = int(np.clip(x, 0, W - 1)), int(np.clip(y, 0, H - 1))
            a = amount * float(mask[yi, xi]) * 0.9
            if a < 0.02:
                continue
            s = p["size"]
            ang = math.degrees(p["rot"] * dt + p["ph"])
            squash = abs(math.sin(dt * 2.2 + p["ph"])) * 0.6 + 0.4  # petal turning in the air
            x0, y0 = max(int(x - s * 2), 0), max(int(y - s * 2), 0)
            x1, y1 = min(int(x + s * 2), W), min(int(y + s * 2), H)
            if x0 >= x1 or y0 >= y1:
                continue
            roi = img[y0:y1, x0:x1]
            ov = roi.copy()
            hh, ww = roi.shape[:2]
            gy, gx = np.mgrid[0:hh, 0:ww].astype(np.float32)
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            g = ((gx - (x - x0)) * ca + (gy - (y - y0)) * sa) / (2 * s) + 0.5  # light across the petal
            ov = np.clip(np.array(p["col"], np.float32) * (0.7 + 0.5 * np.clip(g, 0, 1))[..., None], 0, 255)
            m = np.zeros(roi.shape[:2], np.float32)
            cv2.ellipse(m, (int(x) - x0, int(y) - y0), (int(s), max(2, int(s * 0.62 * squash))), ang, 0, 360, 1.0, -1,
                        cv2.LINE_AA)
            m = cv2.GaussianBlur(m, (0, 0), 1.3)[..., None] * a
            roi[:] = (roi * (1 - m) + ov * m).astype(np.uint8)


class Glints:
    """'rouxinóis cantam': small green-gold glints twinkle at the edges, like song in a forest."""

    def __init__(self, n=55, seed=12):
        r = random.Random(seed)
        self.p = []
        for _ in range(n):
            side = r.random() < 0.5
            self.p.append((r.uniform(10, 150) if side else r.uniform(390, 530), r.uniform(60, SH - 60),
                           r.uniform(0, 6.28), r.uniform(2.5, 6.0), r.uniform(2.5, 4.5)))

    def draw(self, layer, t, amount, energy):
        for x, y, ph, f, s in self.p:
            tw = max(0.0, math.sin(t * f + ph)) ** 4 * amount * (0.9 + 0.9 * energy)
            if tw < 0.02:
                continue
            c = (150 * tw, 235 * tw, 210 * tw)
            cv2.circle(layer, (int(x), int(y)), int(s), c, -1, cv2.LINE_AA)
            L = int(s * 3.5)
            cv2.line(layer, (int(x) - L, int(y)), (int(x) + L, int(y)), tuple(v * 0.6 for v in c), 1, cv2.LINE_AA)
            cv2.line(layer, (int(x), int(y) - L), (int(x), int(y) + L), tuple(v * 0.6 for v in c), 1, cv2.LINE_AA)


class Embers:
    """Her voice alone: warm light particles rise; their speed and glow breathe with her voice."""

    def __init__(self, n=130, seed=21):
        r = random.Random(seed)
        self.p = [(r.uniform(0, SW), r.uniform(0, SH), r.uniform(0.4, 1.0), r.uniform(0, 6.28)) for _ in range(n)]
        self.rise = 0.0
        self.last = None

    def draw(self, layer, t, amount, energy):
        if self.last is not None:
            self.rise += (t - self.last) * (12 + 70 * energy)
        self.last = t
        for x0, y0, depth, ph in self.p:
            y = (y0 - self.rise * depth) % (SH + 20) - 10
            x = x0 + math.sin(t * 0.7 + ph) * 10 * depth
            a = amount * depth * (0.6 + 1.2 * energy) * (0.6 + 0.4 * math.sin(t * 4 + ph))
            cv2.circle(layer, (int(x), int(y)), max(2, int(3.4 * depth)), (120 * a, 200 * a, 255 * a), -1, cv2.LINE_AA)


def smile_warmth(layer, t, smile):
    """When she smiles, the corners take on a warm glow."""
    if smile < 0.05:
        return
    yy, xx = np.ogrid[0:SH, 0:SW]
    for cx, cy in [(0, SH * 0.15), (SW, SH * 0.2)]:
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (SW * 0.9)
        g = (np.clip(1 - d, 0, 1) ** 2 * smile * 0.55).astype(np.float32)
        layer += g[..., None] * np.array([80, 150, 255], np.float32)


# ---------- lyric sprites with a word that turns gold ----------
def line_sprites(pt, ru, word):
    lyr_f = C.font(C.ITALIC, 70, b"SemiBold Italic")
    ru_f = C.font(C.SERIF, 30, b"SemiBold")
    base = C.text_block([(ru.upper(), ru_f, (255, 255, 255, 175), 3, 22), (pt, lyr_f, (255, 255, 255, 255), 0, 0)])
    if not word:
        return base, None
    # same layout, but only the keyword, in gold, with a soft glow
    d0 = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    lines = [(ru.upper(), ru_f, 3, 22), (pt, lyr_f, 0, 0)]
    heights = [(f.getbbox("ÁÇgjУ")[3] + gap) for _, f, _, gap in lines]
    layer = Image.new("RGBA", (W, sum(heights) + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y = 30 + heights[0]
    tw = d0.textlength(pt, font=lyr_f)
    x = (W - tw) / 2 + d0.textlength(pt[:pt.index(word)], font=lyr_f)
    d.text((x, y), word, font=lyr_f, fill=GOLD + (255,))
    glow = layer.filter(ImageFilter.GaussianBlur(10))
    gold = Image.alpha_composite(glow, layer)
    return base, np.array(gold)


def main(src_path, npz, out_path):
    cap = cv2.VideoCapture(src_path)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    n = len(frames)
    face = Face(npz)
    motes, birds, petals, glints, embers = Motes(), Birds(), Petals(), Glints(), Embers()

    lyr = [line_sprites(pt, ru, GOLD_WORDS.get(i, (None,))[0]) for i, (_, _, pt, ru) in enumerate(C.LYRICS)]
    ctx = C.text_block([
        ("BORODIN  ·  PRÍNCIPE IGOR  ·  1890", C.font(C.SERIF, 28, b"SemiBold"), (255, 255, 255, 200), 5, 30),
        ("Mulheres presas longe de casa", C.font(C.ITALIC, 54, b"Medium Italic"), (255, 255, 255, 255), 0, 6),
        ("pedem ao vento que leve sua canção.", C.font(C.ITALIC, 54, b"Medium Italic"), (255, 255, 255, 255), 0, 0),
    ])
    card = C.text_block([
        ("Voa nas asas do vento", C.font(C.ITALIC, 92, b"Medium Italic"), (255, 255, 255, 255), 0, 18),
        ("УЛЕТАЙ НА КРЫЛЬЯХ ВЕТРА", C.font(C.SERIF, 30, b"Medium"), (255, 255, 255, 170), 5, 70),
        ("ALEXANDER BORODIN  ·  PRÍNCIPE IGOR, 1890", C.font(C.SERIF, 28, b"SemiBold"), (255, 255, 255, 200), 4, 26),
        ("voz  ·  @kvashenayakto", C.font(C.ITALIC, 44, b"Medium Italic"), (255, 255, 255, 255), 0, 10),
        ("edição  ·  @seu_perfil", C.font(C.ITALIC, 44, b"Medium Italic"), (255, 255, 255, 220), 0, 0),
    ], shadow=False)

    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    want = {int(round(x * FPS)) for x in preview}
    enc = None if preview else subprocess.Popen([
        "ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-tune", "film",
        "-pix_fmt", "yuv420p", out_path], stdin=subprocess.PIPE)

    for i in range(int(C.DUR * FPS)):
        t = i / FPS
        # embers integrate over time, so in preview they still need every frame of their span
        if preview and i not in want:
            if EMBERS[0] <= t < EMBERS[1]:
                embers.draw(np.zeros((SH, SW, 3), np.float32), t, 0, face.e(t))
            continue
        img = cv2.resize(frames[min(i, n - 1)], (W, H), interpolation=cv2.INTER_LANCZOS4)

        # the turn (from calmo): slow approach + edges into shadow
        k, z = 0.0, 1.0
        if C.TURN[0] <= t < C.TURN[1]:
            k = smooth((t - C.TURN[0]) / 2.0)
            z = 1.0 + 0.07 * smooth((t - C.TURN[0]) / (C.TURN[1] - C.TURN[0]))
            cx, cy = W / 2, H * 0.33
            M = np.float32([[z, 0, (1 - z) * cx], [0, z, (1 - z) * cy]])
            img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)

        cap_a = max((fade(t, a, b, fin=0.35, fout=0.4) for a, b, _, _ in C.LYRICS), default=0.0)
        shade = 0.55 * C.POOL * cap_a + 0.3 * C.BOTTOM + 0.35 * C.TOP * fade(t, C.CONTEXT[0] - 0.3, C.CONTEXT[1] + 0.3) \
            + 0.8 * C.VIGNETTE * k
        img = (img.astype(np.float32) * (1 - np.clip(shade, 0, 0.85))[..., None]).astype(np.uint8)

        # ---- lyric-driven light, kept off her face ----
        e, sm = face.e(t), face.s(t)
        mask = face.mask(i, z)
        light = np.zeros((SH, SW, 3), np.float32)
        wind = max(env_at(a, b, t) for a, b in WIND)
        if wind > 0:
            gust = max(math.exp(-((t - g) / 0.8) ** 2) for g in GUSTS)
            motes.draw(light, t, wind, e, gust)
        if (a := env_at(*SUN, t, 1.5, 2.0)) > 0:
            rays = np.zeros((SH, SW, 3), np.float32)
            sun_rays(rays, t, a * 0.75, e)
            light += cv2.GaussianBlur(rays, (0, 0), 14)
        if (a := env_at(*NIGHTINGALES, t)) > 0:
            glints.draw(light, t, a, e)
        if (a := env_at(*EMBERS, t, 1.5, 1.0)) > 0:
            embers.draw(light, t, a, e)
        smile_warmth(light, t, sm * (1.0 if t < C.FADE_OUT[0] else 0.0))
        if light.any():
            light = cv2.GaussianBlur(cv2.resize(light, (W, H), interpolation=cv2.INTER_LINEAR), (0, 0), 1.6)
            light *= mask[..., None]
            a = img.astype(np.float32)
            img = (255 - (255 - a) * (255 - np.clip(light, 0, 255)) / 255).astype(np.uint8)

        if (a := env_at(*BIRDS, t, 1.0, 1.5)) > 0:
            birds.draw(img, t, a, mask)
        if (a := env_at(*ROSES, t, 0.8, 1.6)) > 0:
            petals.draw(img, t, a, mask, sm)

        if t >= C.FADE_OUT[0]:
            img = (img.astype(np.float32) * (1 - smooth((t - C.FADE_OUT[0]) / (C.FADE_OUT[1] - C.FADE_OUT[0])))).astype(np.uint8)

        C.paste(img, ctx, 300, fade(t, *C.CONTEXT, fin=0.8, fout=0.7))
        for li, ((a, b, _, _), (base, gold)) in enumerate(zip(C.LYRICS, lyr)):
            al = fade(t, a, b, fin=0.35, fout=0.4)
            if al <= 0:
                continue
            C.paste(img, base, C.CAPTION_Y, al)
            if gold is not None:
                gt = GOLD_WORDS[li][1]
                C.paste(img, gold, C.CAPTION_Y, al * smooth((t - gt + 0.15) / 0.5))
        if t >= C.CARD:
            C.paste(img, card, 900, smooth((t - C.CARD) / 0.9))

        if preview:
            cv2.imwrite(f"{out_path}_{t:05.1f}.png", cv2.resize(img, (360, 640), interpolation=cv2.INTER_AREA))
            continue
        enc.stdin.write(img.tobytes())
        if i % 450 == 0:
            print(f"{t:5.1f}s", flush=True)
    if enc:
        enc.stdin.close()
        enc.wait()


if __name__ == "__main__":
    main(*sys.argv[1:4])

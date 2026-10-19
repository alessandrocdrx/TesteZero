"""'A Deus' to the user's own recording, cut at the silence after the first verse: 26 shots (the seven animated
clips of 'Glória' forward, backwards and mirrored, plus the angelic heroine and her dark counterpart as 3D
paintings). The story follows the hymn: dawn and miracle, a tear in the lake, freedom on her wings, the
cathedral's wind, then the fallen angel brings the storm and a battle of light against shadow (beams that clash,
shockwaves, 3D streaks, smoke closing in), until 'Luz do sol… graças a Deus' breaks it. Big lyrics with outline
and glow, the sung pronunciation above them, credits at the top, the editor's handle floating around the centre.
Builds on grandia.py. Usage: CLIPES=dir NOVAS=dir adeus.py _ AUDIO OUT.mp4     (PREVIEW="15.2,24.7" for frames)"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poder as P  # noqa: E402
import grandia as G  # noqa: E402
from poder import W, H, FPS, GOLD, CREAM, smooth, pulse, radial, rays  # noqa: E402

DUR = 89.0                      # the song falls silent at 88 s, after the first verse
EDITOR = "edição · @alessandrocdrx"
CREDITS = ("A DEUS", "Grandia II  ·  Noriyuki Iwadare  ·  voz Kaori Kawasumi")

# the lyrics (Fandom, Portuguese original), timed to the singing by whisper; short groups, read at a glance.
# Above each group, smaller: the words as she sings them, with the Japanese pronunciation
LYRICS = [
    [("Nascer", 9.5), ("do", 10.9), ("sol,", 11.3)],
    [("palavras,", 13.0)],
    [("milagre", 15.1)],
    [("Água", 20.4), ("pura,", 21.8)],
    [("uma", 23.6), ("lágrima", 24.0)],
    [("Paz,", 27.2), ("luz,", 28.3), ("amor", 29.1)],
    [("Fruto", 34.6), ("agreste,", 35.3)],
    [("respiração,", 36.6)],
    [("liberdade", 39.3)],
    [("Harmonia,", 45.4)],
    [("vento", 47.7), ("da", 48.4), ("bênção,", 48.9)],
    [("agradecimento", 51.7)],
    [("Tempestade,", 58.4)],
    [("inquietação,", 61.6)],
    [("escuridão", 64.3)],
    [("Luz", 71.4), ("do", 71.9), ("sol,", 72.2)],
    [("alegria,", 74.6)],
    [("graças", 77.8), ("a", 78.7), ("Deus", 79.2)],
]
SUNG = ["na-se-ru  do  so-ru", "pa-ra-vu-ra-su", "mi-ra-gu-ri", "a-gu-a  pu-ra", "u-ma  ra-gu-ri-ma",
        "pa-su  ru-su  a-mo-ru", "fu-ru-to  a-gu-re-su-to", "re-su-pi-ra-sa-un", "ri-be-ru-da-ji",
        "a-ru-mo-ni-a", "be-n-to  da  be-n-sa-un", "a-gu-ra-de-shi-me-n-to", "te-n-pe-su-ta-ji",
        "i-n-ki-e-ta-sa-un", "e-su-ku-ri-da-un", "ru-su  do  so-ru", "a-re-gu-ri-a", "gu-ra-sa-su  a  de-u-su"]
LINE_END = [12.6, 14.8, 19.0, 23.2, 26.8, 32.6, 36.3, 38.9, 44.0, 47.4, 51.3, 56.2, 61.3, 64.0, 69.6,
            74.3, 77.4, 82.0]
KEYS = {"sol,", "milagre", "lágrima", "luz,", "liberdade", "vento", "agradecimento", "Tempestade,",
        "escuridão", "Luz", "alegria,", "Deus"}

# the shots. Clips: off = seconds into the clip, m = mirrored, zoom = extra push. Paintings: a 3D camera
# (each value goes from the first to the second number), halo = where her halo is in the painting (0..1)
ANJO1 = dict(halo=(0.57, 0.115), col=GOLD)
ANJO2 = dict(halo=(0.58, 0.105), col=GOLD)
SOMBRA = dict(halo=(0.60, 0.094), col=np.array([90, 40, 230], np.float32))   # her cracked halo burns crimson
SHOTS = [
    ("v7", 0.0, 4.6, {}),
    ("anjo1", 4.6, 9.2, dict(ANJO1, z=(1.22, 1.04), dx=(0, 0), dy=(60, 0), yaw=(-3, 2), pitch=(4, 0))),
    ("v3", 9.2, 12.8, {}),
    ("anjo2", 12.8, 15.0, dict(ANJO2, z=(1.08, 1.2), dx=(-20, 20), dy=(80, 120), yaw=(3, -2), pitch=(0, 2))),
    ("v3", 15.0, 19.8, dict(m=1, off=3.5, zoom=0.08)),
    ("v5", 19.8, 23.4, {}),
    ("v5", 23.4, 26.6, dict(m=1, off=2.5, zoom=0.12)),
    ("v5r", 26.6, 29.8, {}),
    ("v6r", 29.8, 33.0, dict(off=3)),
    ("v1", 33.0, 36.4, {}),
    ("v1", 36.4, 38.9, dict(m=1, off=4, zoom=0.1)),
    ("v4", 38.9, 42.0, {}),
    ("anjo1", 42.0, 45.0, dict(ANJO1, z=(1.04, 1.22), dx=(0, 0), dy=(0, 90), yaw=(2, -3), pitch=(-3, 2))),
    ("v2", 45.0, 48.6, {}),
    ("v2", 48.6, 51.6, dict(m=1, off=4, zoom=0.1)),
    ("v2r", 51.6, 56.6, {}),
    ("sombra", 56.6, 59.6, dict(SOMBRA, z=(1.25, 1.05), dx=(0, 0), dy=(-60, 0), yaw=(-4, 3), pitch=(-5, 0))),
    ("v4r", 59.6, 61.6, dict(off=2)),
    ("sombra", 61.6, 63.6, dict(SOMBRA, m=1, z=(1.55, 1.7), dx=(-40, -60), dy=(820, 880), yaw=(3, -2), pitch=(2, 0))),
    ("v1r", 63.6, 66.4, {}),
    ("sombra", 66.4, 68.6, dict(SOMBRA, z=(1.1, 1.3), dx=(0, -40), dy=(200, 320), yaw=(-2, 4), pitch=(3, -2))),
    ("v4", 68.6, 70.8, dict(m=1, off=4, zoom=0.06)),
    ("v6", 70.8, 74.6, {}),
    ("anjo2", 74.6, 77.8, dict(ANJO2, z=(1.04, 1.24), dx=(0, 0), dy=(0, 110), yaw=(-3, 3), pitch=(2, -2))),
    ("v6", 77.8, 81.0, dict(m=1, off=5, zoom=0.06)),
    ("v7r", 81.0, DUR, {}),
]
XFADE = 0.5
BOLTS = [(58.4, 3), (59.9, 8), (61.6, 13), (65.6, 21), (68.2, 5)]
VIOLET = np.array([255, 70, 175], np.float32)          # BGR
GOLDB = np.array([150, 225, 255], np.float32)


# ---------- the lyrics ----------
def word_sprite(txt, ff, stroke):
    """fill and outline masks, a soft drop shadow and a glow (all float 0..1)"""
    pad = 50
    b = ff.getbbox(txt, stroke_width=stroke)
    size = (int(b[2] - b[0]) + 2 * pad, int(ff.size * 1.5) + 2 * pad)
    fill, full = Image.new("L", size, 0), Image.new("L", size, 0)
    ImageDraw.Draw(fill).text((pad - b[0], pad), txt, font=ff, fill=255)
    ImageDraw.Draw(full).text((pad - b[0], pad), txt, font=ff, fill=255, stroke_width=stroke, stroke_fill=255)
    a = np.array(fill).astype(np.float32) / 255
    s = np.clip(np.array(full).astype(np.float32) / 255 - a, 0, 1)
    sh = np.array(full.filter(ImageFilter.GaussianBlur(12))).astype(np.float32) / 255
    gl = np.array(full.filter(ImageFilter.GaussianBlur(22))).astype(np.float32) / 255
    return a, s, sh, gl


_GRAD = {}


def gradient(h, top, bottom):
    key = (h, tuple(top), tuple(bottom))
    g = _GRAD.get(key)
    if g is None:
        u = np.clip((np.arange(h, dtype=np.float32) / h - 0.3) / 0.45, 0, 1)[:, None, None]
        g = _GRAD[key] = (np.array(top, np.float32) * (1 - u) + np.array(bottom, np.float32) * u) / 255
    return g


WHITE_T, WHITE_B = (255, 255, 255), (215, 235, 250)
GOLD_T, GOLD_B = (200, 240, 255), (40, 160, 235)
INK = np.array([20, 18, 30], np.float32) / 255


def blit(img, spr, x, y, scale, alpha, gold, glow):
    """outlined, gradient-filled word; gold 0..1 turns the gradient from white to gold"""
    if alpha <= 0.003:
        return
    a, s, sh, gl = spr
    if abs(scale - 1) > 1e-3:
        a, s, sh, gl = (cv2.resize(m, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA if scale < 1
                                   else cv2.INTER_LINEAR) for m in (a, s, sh, gl))
    h, w = a.shape
    x0, y0 = int(x - w / 2), int(y - h / 2)
    X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
    if X1 <= X0 or Y1 <= Y0:
        return
    sl = (slice(Y0 - y0, Y1 - y0), slice(X0 - x0, X1 - x0))
    roi = img[Y0:Y1, X0:X1]
    roi *= 1 - sh[sl][..., None] * 0.75 * alpha
    if glow > 0:
        roi += gl[sl][..., None] * GOLD / 255 * 0.6 * glow * alpha
    st = s[sl][..., None] * alpha
    roi[:] = roi * (1 - st) + INK * st
    gw = gradient(h, WHITE_T, WHITE_B)[sl[0]]
    gg = gradient(h, GOLD_T, GOLD_B)[sl[0]]
    col = gw * (1 - gold) + gg * gold
    aa = a[sl][..., None] * alpha
    roi[:] = roi * (1 - aa) + col * aa


class Lyrics:
    """big centred words that fly in from depth on their own syllable, the sung word turns gold, key words stay
    gold and glow; the group leaves toward the camera. Above it, smaller, the pronunciation as she sings it"""
    CY = 1250

    def __init__(self):
        f = P.font(P.ITALIC, 150, b"SemiBold Italic")
        fk = P.font(P.ITALIC, 184, b"Bold Italic")
        fs = P.font(P.ITALIC, 54, b"Medium Italic")
        d0 = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
        maxw, space, lh = 960, 36, 176
        self.lines, self.sung = [], []
        for words, sung in zip(LYRICS, SUNG):
            rows, row, rw = [], [], 0
            for wtxt, at in words:
                ff = fk if wtxt in KEYS else f
                ww = d0.textlength(wtxt, font=ff) + (26 if wtxt in KEYS else 0)
                if row and rw + space + ww > maxw:
                    rows.append((row, rw))
                    row, rw = [], 0
                rw += (space if row else 0) + ww
                row.append((wtxt, at, ff, ww))
            rows.append((row, rw))
            fit = min(1.0, maxw / max(r[1] for r in rows))           # a long word shrinks to fit the width
            items, y0 = [], -(len(rows) - 1) * lh * fit / 2
            for ri, (row, rw) in enumerate(rows):
                x = -rw / 2
                for wtxt, at, ff, ww in row:
                    items.append((word_sprite(wtxt, ff, 6), (x + ww / 2) * fit, y0 + ri * lh * fit, at,
                                  wtxt in KEYS, fit))
                    x += ww + space
            self.lines.append(items)
            self.sung.append((word_sprite(sung, fs, 3), y0 - 125 * fit))

    def on(self, t):
        """1 while a group is on screen (for the dark band behind it)"""
        k = 0.0
        for items, end in zip(self.lines, LINE_END):
            k = max(k, smooth((t - items[0][3] + 0.4) / 0.4) * (1 - smooth((t - end - 0.2) / 0.5)))
        return k

    def draw(self, img, t, cx=W / 2):
        cy = self.CY
        for items, (sung, sy), end in zip(self.lines, self.sung, LINE_END):
            if not (items[0][3] - 0.3 <= t < end + 0.6):
                continue
            out = smooth((t - end) / 0.6)
            k0 = smooth((t - items[0][3] + 0.3) / 0.45)
            blit(img, sung, cx, cy + sy - 30 * out + 20 * (1 - k0), 1 + 0.3 * out, 0.92 * k0 * (1 - out), 0.25, 0)
            nxt = [it[3] for it in items[1:]] + [end]
            for (spr, x, y, at, key, fit), until in zip(items, nxt):
                a_in = smooth((t - at + 0.15) / 0.38)
                if a_in <= 0:
                    continue
                spread = 1 + 0.4 * out                              # the group passes the camera
                scale = fit * (0.55 + 0.45 * a_in) * spread * (1 + 0.09 * pulse(t, at, 0.1, 0.4) * (2 if key else 1))
                px = cx + x * spread
                py = cy + y * spread + 50 * (1 - a_in) - 70 * out
                speaking = 1.0 if at <= t < max(until, at + 0.3) else 0.0
                gold = max(speaking, 0.85 if key and t >= at else 0.0)
                blit(img, spr, px, py, scale, a_in * (1 - out), gold, 1.0 if key and t >= at else 0.35 * speaking)


_band = np.exp(-((np.arange(H, dtype=np.float32) - 1180) / 300) ** 2)
SCRIM = (0.5 * _band)[:, None, None]


# ---------- titles, credits, the editor's handle ----------
def title_sprite(txt, sub, size=190, tr=30):
    f = P.font(P.SERIF, size, b"SemiBold")
    fs = P.font(P.ITALIC, 52, b"Medium Italic")
    im = Image.new("L", (W, 440), 0)
    d = ImageDraw.Draw(im)
    tw = sum(d.textlength(c, font=f) + tr for c in txt) - tr
    x = (W - tw) / 2
    for c in txt:
        d.text((x, 20), c, font=f, fill=255)
        x += d.textlength(c, font=f) + tr
    d.text(((W - d.textlength(sub, font=fs)) / 2, 262), sub, font=fs, fill=230)
    a = np.array(im).astype(np.float32) / 255
    return a, cv2.GaussianBlur(a, (0, 0), 22)


def put_title(img, title, y0, k, scale):
    """the title in gold with a dark halo, scaled about its centre (it comes from depth)"""
    if k <= 0.003:
        return
    ta, tg = title
    if abs(scale - 1) > 1e-3:
        M = cv2.getRotationMatrix2D((W / 2, ta.shape[0] / 2), 0, scale)
        ta = cv2.warpAffine(ta, M, (W, ta.shape[0]))
        tg = cv2.warpAffine(tg, M, (W, ta.shape[0]))
    roi = img[y0:y0 + ta.shape[0]]
    roi *= 1 - np.clip(cv2.GaussianBlur(ta, (0, 0), 20) * 2.2, 0, 0.8)[..., None] * k
    roi += tg[..., None] * GOLD / 255 * 0.9 * k
    roi[:] = roi * (1 - ta[..., None] * k) + (GOLD + 40) / 255 * ta[..., None] * k


def credits_sprite():
    """the song's name and credits, small and still at the top (below the app's own bar)"""
    f = P.font(P.SERIF, 60, b"SemiBold")
    fs = P.font(P.ITALIC, 31, b"Medium Italic")
    im = Image.new("L", (W, 150), 0)
    d = ImageDraw.Draw(im)
    txt, tr = CREDITS[0], 16
    tw = sum(d.textlength(c, font=f) + tr for c in txt) - tr
    x = (W - tw) / 2
    for c in txt:
        d.text((x, 6), c, font=f, fill=255)
        x += d.textlength(c, font=f) + tr
    d.text(((W - d.textlength(CREDITS[1], font=fs)) / 2, 88), CREDITS[1], font=fs, fill=225)
    a = np.array(im).astype(np.float32) / 255
    return a, cv2.GaussianBlur(a, (0, 0), 8)


def editor_sprite():
    f = P.font(P.ITALIC, 48, b"SemiBold Italic")
    b = f.getbbox(EDITOR)
    im = Image.new("L", (int(b[2]) + 60, 110), 0)
    ImageDraw.Draw(im).text((30, 20), EDITOR, font=f, fill=255)
    a = np.array(im).astype(np.float32) / 255
    return a, cv2.GaussianBlur(a, (0, 0), 6), cv2.GaussianBlur(a, (0, 0), 14)


# the handle hops quickly between central spots (clear of the lyrics band and the credits), floating in each
SPOTS = [(540, 600), (330, 820), (750, 700), (540, 920), (340, 560), (760, 900), (540, 760), (720, 540)]
HOP, STAY = 0.45, 1.75


def editor_pos(t):
    n = int(t // (HOP + STAY))
    u = (t - n * (HOP + STAY)) / HOP
    a, b = SPOTS[n % len(SPOTS)], SPOTS[(n + 1) % len(SPOTS)]
    e = smooth(u - STAY / HOP) if u > STAY / HOP else 0.0
    x = a[0] + (b[0] - a[0]) * e + 14 * math.sin(t * 2.3)
    y = a[1] + (b[1] - a[1]) * e + 10 * math.sin(t * 1.9 + 1)
    return x, y


# ---------- 3D layers ----------
class Rain:
    """rain falling through depth, slanted by the wind: near drops long and soft, far ones short and sharp"""
    def __init__(self, n=1100, seed=5):
        r = np.random.default_rng(seed)
        self.x = r.uniform(-1.8, 1.8, n)
        self.y0 = r.uniform(0, 5, n)
        self.z = r.uniform(0.3, 3.6, n)
        self.sp = r.uniform(0.85, 1.2, n)

    def draw(self, t, amount, wind=0.3):
        if amount <= 0.01:
            return None
        sw, sh = W // 2, H // 2
        near = np.zeros((sh, sw), np.float32)
        far = np.zeros((sh, sw), np.float32)
        f = 0.9 * sw
        y = (self.y0 + 3.2 * self.sp * t) % 5.0 - 2.5
        px = sw / 2 + f * (self.x + wind * y * 0.3) / self.z
        py = sh / 2 + f * y / self.z
        ln = 46 / self.z
        for x0, y0, z, l in zip(px, py, self.z, ln):
            if not (-30 < x0 < sw + 30 and -30 < y0 < sh + 60):
                continue
            c = amount * min(1.0, 0.25 + 0.5 / z)
            cv2.line(near if z < 0.9 else far, (int(x0), int(y0)), (int(x0 - wind * l), int(y0 - l)), c,
                     2 if z < 0.9 else 1, cv2.LINE_AA)
        out = cv2.GaussianBlur(near, (0, 0), 2.2) + far
        return cv2.resize(out, (W, H))[..., None]


class Wind:
    """streaks of air sweeping across through depth (the 'vento da bênção')"""
    def __init__(self, n=160, seed=12):
        r = np.random.default_rng(seed)
        self.x0 = r.uniform(0, 5, n)
        self.y = r.uniform(-2.0, 2.0, n)
        self.z = r.uniform(0.4, 3.0, n)
        self.sp = r.uniform(0.8, 1.4, n)
        self.ph = r.uniform(0, 6.28, n)

    def draw(self, buf, t, amount):
        if amount <= 0.01:
            return
        sh, sw = buf.shape[:2]
        f = 0.9 * sw
        x = (self.x0 + 2.6 * self.sp * t) % 5.0 - 2.5
        for xx, yy, z, ph in zip(x, self.y, self.z, self.ph):
            px, py = sw / 2 + f * xx / z, sh / 2 + f * (yy + 0.08 * math.sin(xx * 2 + ph)) / z
            if not (-200 < px < sw + 200 and -20 < py < sh + 20):
                continue
            l = 120 / z
            c = (np.array([255, 240, 225], np.float32) / 255 * amount * min(1.0, 0.2 + 0.4 / z)).tolist()
            cv2.line(buf, (int(px - l), int(py + 6 * math.sin(ph))), (int(px), int(py)), c, 1, cv2.LINE_AA)


class Streaks:
    """light rushing past the camera from a vanishing point (the warp of a battle charge)"""
    def __init__(self, n=220, seed=17):
        r = np.random.default_rng(seed)
        a = r.uniform(0, 6.283, n)
        d = r.uniform(0.15, 1.6, n)
        self.x, self.y = np.cos(a) * d, np.sin(a) * d * 1.6
        self.z0 = r.uniform(0, 3, n)
        self.sp = r.uniform(0.8, 1.5, n)

    def draw(self, buf, t, amount, col, cx, cy):
        if amount <= 0.01:
            return
        sh, sw = buf.shape[:2]
        f = 0.5 * sw
        z = 3.2 - (self.z0 + 4.0 * self.sp * t) % 3.0
        z2 = z + 0.35
        c = col / 255 * amount
        for x, y, za, zb in zip(self.x, self.y, z, z2):
            p1 = (int(cx + f * x / za), int(cy + f * y / za))
            p2 = (int(cx + f * x / zb), int(cy + f * y / zb))
            if not (-50 < p1[0] < sw + 50 and -50 < p1[1] < sh + 50):
                continue
            cv2.line(buf, p1, p2, (c * min(1.0, 0.5 / za + 0.2)).tolist(), 2 if za < 0.8 else 1, cv2.LINE_AA)


def smoke_bank(sw, sh, seed=31):
    """a tileable field of dark smoke (several octaves of blurred noise), drawn once"""
    r = np.random.default_rng(seed)
    out = np.zeros((sh, sw), np.float32)
    for s, w in ((40, 0.5), (18, 0.3), (7, 0.2)):
        n = np.tile(r.normal(0, 1, (sh, sw)).astype(np.float32), (3, 3))      # blurred tiled: it wraps
        n = cv2.GaussianBlur(n, (0, 0), s)[sh:2 * sh, sw:2 * sw]
        out += w * n / (n.std() + 1e-6)
    return (out - out.min()) / (out.max() - out.min())


def ripples(t, at, cx, cy, size, sw, sh):
    """rings spreading on the water in perspective where the tear fell"""
    k = t - at
    if k < 0 or k > 4.0:
        return None
    buf = np.zeros((sh, sw), np.float32)
    for j in range(4):
        kk = k - j * 0.4
        if kk <= 0:
            continue
        r = size * (1 - math.exp(-kk / 1.3))
        cv2.ellipse(buf, (int(cx), int(cy)), (int(r), int(r * 0.24)), 0, 0, 360, math.exp(-kk / 1.5), 2, cv2.LINE_AA)
    return cv2.GaussianBlur(buf, (0, 0), 1.0) + cv2.GaussianBlur(buf, (0, 0), 7) * 1.5


def shockwave(t, at, cx, cy, sw, sh, flat=0.45, speed=520):
    """a ring of light thrown out by a clash, seen in perspective"""
    k = t - at
    if k < 0 or k > 1.4:
        return None
    buf = np.zeros((sh, sw), np.float32)
    r = speed * k
    cv2.ellipse(buf, (int(cx), int(cy)), (int(r), int(r * flat)), 0, 0, 360, 1.0, 3, cv2.LINE_AA)
    return (cv2.GaussianBlur(buf, (0, 0), 1.5) + cv2.GaussianBlur(buf, (0, 0), 10) * 2) * (1 - k / 1.4) ** 1.5


def beam(buf, p0, p1, col, k, t, width=10):
    """an energy beam with a white-hot core that flickers"""
    if k <= 0.01:
        return
    m = np.zeros(buf.shape[:2], np.float32)
    w = width * (0.8 + 0.3 * math.sin(t * 47) + 0.15 * math.sin(t * 89))
    cv2.line(m, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), 1.0, max(1, int(w)), cv2.LINE_AA)
    core = cv2.GaussianBlur(m, (0, 0), 1.2)
    halo = cv2.GaussianBlur(m, (0, 0), 9)
    buf += (core[..., None] * 1.2 + halo[..., None] * (col / 255) * 1.6) * k


_FLARE = {}


def flare(cx, cy, sw, sh):
    """an anamorphic lens flare: a long horizontal streak plus ghosts toward the centre"""
    key = (int(cx) // 4, int(cy) // 4)
    m = _FLARE.get(key)
    if m is None:
        gy, gx = np.mgrid[0:sh, 0:sw].astype(np.float32)
        m = np.exp(-((gx - cx) / (sw * 0.55)) ** 2 - ((gy - cy) / 3.5) ** 2) * 0.9
        for j, (k, r) in enumerate(((0.45, 16), (0.8, 9), (1.3, 26))):
            gxk, gyk = cx + (sw / 2 - cx) * k * 2, cy + (sh / 2 - cy) * k * 2
            m += np.exp(-((gx - gxk) ** 2 + (gy - gyk) ** 2) / (2 * r * r)) * 0.25
        m = m.astype(np.float32)
        if len(_FLARE) < 64:
            _FLARE[key] = m
    return m


# ---------- the shots ----------
def view_m(p, zoom, dx, dy, yaw, pitch):
    """the homography of P.Painting.view (the painting as a plane seen by a pinhole camera)"""
    f = 1.6 * W
    cx, cy = p.w / 2, p.h / 2
    ya, pa = math.radians(yaw), math.radians(pitch)
    Ry = np.array([[math.cos(ya), 0, math.sin(ya)], [0, 1, 0], [-math.sin(ya), 0, math.cos(ya)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(pa), -math.sin(pa)], [0, math.sin(pa), math.cos(pa)]])
    R = Rx @ Ry
    k = H / (p.h / 1.25) * zoom
    src, dst = [], []
    for x, y in ((0, 0), (p.w, 0), (p.w, p.h), (0, p.h)):
        q = R @ np.array([(x - cx) * k, (y - cy) * k, 0.0])
        z = f + q[2]
        dst.append((W / 2 + f * q[0] / z + dx, H / 2 + f * q[1] / z + dy))
        src.append((x, y))
    return cv2.getPerspectiveTransform(np.float32(src), np.float32(dst)), k


def shot(src, paint, name, o, lo, hi, t, shake, push):
    """a clip (its own camera already flies in 3D; a short one is slowed to fit) or a painting under the 3D
    camera. Returns the frame and, for the paintings, where the halo is on screen and how big"""
    u = (t - lo) / (hi - lo)
    halo = None
    if name in paint:
        p = paint[name]
        e = smooth(u) * 0.7 + u * 0.3
        lerp = lambda ab: ab[0] + (ab[1] - ab[0]) * e
        M, k = view_m(p, lerp(o["z"]) + 0.006 * math.sin(t * 1.3) + push, lerp(o["dx"]) + shake[0] + 6 * math.sin(t * 0.7),
                      lerp(o["dy"]) + shake[1] + 5 * math.sin(t * 0.9 + 1), lerp(o["yaw"]), lerp(o["pitch"]))
        f = cv2.warpPerspective(p.img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        hx, hy = o["halo"]
        q = cv2.perspectiveTransform(np.float32([[[hx * p.w, hy * p.h]]]), M)[0, 0]
        halo = (float(q[0]), float(q[1]), k * p.w * 0.095)
    else:
        c = src
        off = o.get("off", 0.0)
        f = c.at(off + (t - lo) * min(1.0, ((c.n - 1) / c.fps - off) / (hi - lo)))
        z = 1.0 + 0.04 * u + o.get("zoom", 0.0) + push
        M = cv2.getRotationMatrix2D((W / 2, H * 0.45), 0, z)
        M[:, 2] += shake
        f = cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    if o.get("m"):
        f = cv2.flip(f, 1)
        if halo:
            halo = (W - halo[0], halo[1], halo[2])
    return f, halo


def main(_cenas, audio, out):
    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    cdir, ndir = os.environ["CLIPES"], os.environ["NOVAS"]
    paint = {n: P.Painting(os.path.join(ndir, n + ".png")) for n in ("anjo1", "anjo2", "sombra")}
    clips = {}                                         # one decoder per shot, opened when the shot starts
    dust, feathers, rain, wind, streak = P.Dust(n=360, seed=9), G.Feathers(), Rain(), Wind(), Streaks()
    lyr = Lyrics()
    rise, sparks = P.Embers(260, 11), P.Embers(200, 23)
    title = title_sprite("A DEUS", "um hino ao Criador")
    cred = credits_sprite()
    ed = editor_sprite()
    sw, sh = W // 2, H // 2
    gy2, gx2 = np.mgrid[0:sh, 0:sw].astype(np.float32)
    gyf = (np.mgrid[0:H, 0:1][0].astype(np.float32) / H)[..., None]
    edge = np.clip((np.sqrt(((gx2 - sw / 2) / (sw * 0.62)) ** 2 + ((gy2 - sh * 0.45) / (sh * 0.6)) ** 2) - 0.45)
                   / 0.6, 0, 1).astype(np.float32)
    smoke = smoke_bank(sw // 2, sh // 2)
    edge_q = cv2.resize(edge, (sw // 2, sh // 2))
    edge = cv2.resize(edge, (W, H))[..., None]
    bolts = {a: P.lightning(seed, sw, sh) for a, seed in BOLTS}
    grain = P.grain_bank(sigma=0.014)
    tmp = out + ".video.mp4"
    enc = None if preview else subprocess.Popen([
        "ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
        tmp], stdin=subprocess.PIPE)
    clip = [float(x) for x in os.environ.get("CLIP", "").split(",") if x]      # a chunk: "start,end" seconds
    first, last = (round(clip[0] * FPS), round(clip[1] * FPS)) if clip else (0, int(DUR * FPS))
    frames = [int(round(p * FPS)) for p in preview] if preview else range(first, last)
    for i in frames:
        t = i / FPS
        p_mil = pulse(t, 15.1, 0.12, 0.9)
        p_lib = pulse(t, 39.3, 0.15, 1.3)
        p_luz = pulse(t, 71.4, 0.1, 1.6)
        p_ale = pulse(t, 74.6, 0.15, 1.2)
        p_deus = pulse(t, 79.2, 0.2, 1.8)
        p_bolt = max(pulse(t, a, 0.03, 0.3) for a, _ in BOLTS)
        p_inq = pulse(t, 61.6, 0.05, 0.9)
        p_hit = max(pulse(t, a, 0.05, 0.5) for a in (61.6, 62.6, 66.4, 68.6, 69.8))
        storm = smooth((t - 56.2) / 1.4) * (1 - smooth((t - 71.0) / 1.0))
        dark = smooth((t - 64.0) / 1.6) * (1 - smooth((t - 71.0) / 0.6))
        shake = (10 * p_inq * math.sin(t * 91) + 7 * p_bolt * math.sin(t * 67) + 9 * p_hit * math.sin(t * 101)
                 + 5 * p_deus * math.sin(t * 83),
                 10 * p_inq * math.cos(t * 77) + 7 * p_bolt * math.cos(t * 59) + 9 * p_hit * math.cos(t * 97)
                 + 5 * p_deus * math.cos(t * 71))
        u = (t - 36.6) / 2.4
        push = 0.035 * math.sin(math.pi * u) if 0 < u < 1 else 0.0          # 'respiração': the frame breathes
        img, halos = None, []
        for k, (name, a, b, o) in enumerate(SHOTS):
            lo, hi = a - (XFADE / 2 if k else 0), b + (XFADE / 2 if k < len(SHOTS) - 1 else 0)
            if not (lo <= t < hi):
                if k in clips and t >= hi:
                    clips.pop(k).cap.release()
                continue
            if name not in paint and k not in clips:
                clips[k] = G.Clip(os.path.join(cdir, name + ".mp4"))
            fr, halo = shot(clips.get(k), paint, name, o, lo, hi, t, shake, push)
            fr = fr.astype(np.float32) / 255
            w = min(smooth((t - lo) / XFADE) if k else 1.0,
                    1 - smooth((t - (hi - XFADE)) / XFADE) if k < len(SHOTS) - 1 else 1.0)
            img = fr * w if img is None else img + fr * w
            if halo:
                halos.append((halo, o["col"], w, name == "sombra"))
        punch = 0.05 * p_mil + 0.045 * p_lib + 0.04 * p_luz + 0.05 * p_deus + 0.03 * p_hit
        if punch > 0.002:
            M = cv2.getRotationMatrix2D((W / 2, H * 0.45), 0, 1 + punch)
            img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        # the storm: colour drains to a cold blue, the frame darkens, smoke of the fallen angel closes in
        if storm > 0.005:
            g = cv2.transform(img, np.full((1, 3), 1 / 3, np.float32))
            cold = cv2.merge([g * 1.12, g * 0.96, g * 0.82])
            img = img * (1 - 0.6 * storm) + cold * (0.6 * storm)
            img *= (1 - 0.25 * storm - 0.25 * dark) * (1 - edge * 0.7 * dark)
            ox, oy = int(t * 18) % smoke.shape[1], int(t * 31) % smoke.shape[0]
            s1 = np.roll(smoke, (oy, ox), (0, 1))
            s2 = np.roll(smoke[::-1], (-oy // 2, ox // 2 + 37), (0, 1))
            amt = 0.55 * storm + 0.45 * dark
            sm = np.clip((s1 * 0.6 + s2 * 0.4) * (0.45 + 1.2 * edge_q) - (1.05 - amt), 0, 1) * 2.2
            sm = cv2.resize(np.clip(sm, 0, 1) * amt, (W, H))[..., None]
            img = img * (1 - 0.85 * sm) + sm * VIOLET / 255 * 0.12
        L = np.zeros((sh, sw, 3), np.float32)

        def add(mask, col, k):
            if k > 0.004:
                L[:] += mask[..., None] * (np.array(col, np.float32) / 255) * k
        # her halo shines, pulsing, on every painting; the fallen angel's burns crimson
        for (hx, hy, hr), col, w, evil in halos:
            ring = np.zeros((sh, sw), np.float32)
            cv2.ellipse(ring, (int(hx / 2), int(hy / 2)), (max(2, int(hr / 2)), max(1, int(hr / 2 * 0.25))), 0, 0,
                        360, 1.0, 2, cv2.LINE_AA)
            glow = cv2.GaussianBlur(ring, (0, 0), 2) + cv2.GaussianBlur(ring, (0, 0), 9) * 2.5
            add(glow, col, (0.55 + 0.25 * math.sin(t * 3.1)) * w)
            add(radial(hx / 2, hy / 2, hr * 0.9, gx2, gy2), col, (0.25 if evil else 0.35) * w)
        # Nascer do sol: the sun swells and its rays turn; 'palavras' sparks; 'milagre' a magic circle
        sun = smooth((t - 9.0) / 2.5) * (1 - smooth((t - 19.4) / 0.8))
        if sun > 0.01:
            add(radial(sw * 0.47, sh * 0.37, 90 + 70 * smooth((t - 9.5) / 3), gx2, gy2), GOLD, 0.42 * sun)
            add(rays(sw * 0.47, sh * 0.37, t * 0.7, gx2, gy2, 14), [255, 225, 190], 0.22 * sun)
            add(flare(sw * 0.47, sh * 0.37, sw, sh), [255, 215, 170], 0.35 * sun)
        rise.draw(L, t, 13.0, sw * 0.5, sh * 0.42, 260, 1.0)
        mc = G.magic_circle(t, 15.1, sw * 0.5, sh * 0.82, sw * 0.44, sw, sh)
        if mc is not None:
            add(mc, [255, 220, 150], 0.9)
        add(radial(sw * 0.5, sh * 0.45, 200, gx2, gy2), GOLD, 0.28 * p_mil)
        streak.draw(L, t, 0.9 * p_mil, GOLDB, sw * 0.5, sh * 0.45)
        # lágrima: a tear of light falls into the lake, rings spread in perspective
        if 23.4 <= t < 24.6:
            yy = sh * (0.40 + 0.42 * smooth((t - 23.4) / 1.2) ** 1.6)
            add(radial(sw * 0.5, yy, 7, gx2, gy2), [255, 245, 235], 1.6)
            add(radial(sw * 0.5, yy, 22, gx2, gy2), [255, 230, 200], 0.5)
        rp = ripples(t, 24.6, sw * 0.5, sh * 0.84, sw * 0.5, sw, sh)
        if rp is not None:
            add(rp, [255, 240, 220], 0.8)
        add(radial(sw * 0.5, sh * 0.84, 60, gx2, gy2), [255, 240, 220], 0.9 * pulse(t, 24.6, 0.05, 0.5))
        # Paz, luz, amor: three lights bloom one after the other
        add(radial(sw * 0.28, sh * 0.42, 110, gx2, gy2), [255, 245, 235], 0.45 * pulse(t, 27.2, 0.2, 1.4))
        add(radial(sw * 0.5, sh * 0.47, 140, gx2, gy2), GOLD, 0.65 * pulse(t, 28.3, 0.2, 1.4))
        add(radial(sw * 0.72, sh * 0.42, 110, gx2, gy2), [205, 190, 255], 0.5 * pulse(t, 29.1, 0.2, 1.6))
        # liberdade: a gale of feathers, light opening behind her wings, a rush through the clouds
        if p_lib > 0.01:
            add(rays(sw * 0.5, sh * 0.3, t, gx2, gy2, 16), [255, 235, 215], 0.5 * p_lib)
            add(radial(sw * 0.5, sh * 0.32, 240, gx2, gy2), GOLD, 0.4 * p_lib)
            add(flare(sw * 0.5, sh * 0.3, sw, sh), [255, 225, 190], 0.5 * p_lib)
        streak.draw(L, t, 1.1 * p_lib, np.array([255, 245, 235], np.float32), sw * 0.5, sh * 0.32)
        # Harmonia: the cathedral's rays; vento da bênção: air sweeps through; agradecimento: light in her hands
        cat = smooth((t - 44.8) / 1.0) * (1 - smooth((t - 56.2) / 0.8))
        if cat > 0.01:
            add(rays(sw * 0.5, -sh * 0.1, t * 0.4, gx2, gy2, 9), [255, 235, 215], 0.35 * cat)
        wind.draw(L, t, 0.8 * smooth((t - 47.4) / 0.6) * (1 - smooth((t - 51.6) / 1.0)))
        add(radial(sw * 0.5, sh * 0.6, 120, gx2, gy2), GOLD, 0.9 * pulse(t, 51.7, 0.3, 1.8))
        rise.draw(L, t, 51.7, sw * 0.5, sh * 0.6, 300, 1.2)
        # the storm: lightning on the words
        for a, _ in BOLTS:
            pb = pulse(t, a, 0.03, 0.3)
            if pb > 0.01:
                add(bolts[a], [255, 235, 225], 1.0 * pb)
        # the battle: her light (from below left) against the shadow's beam (from above right); they clash,
        # throw shockwaves and sparks; in the darkness the shadow pushes, then her light drives it back
        c1 = smooth((t - 61.4) / 0.25) * (1 - smooth((t - 63.4) / 0.3))
        c2 = smooth((t - 66.3) / 0.3) * (1 - smooth((t - 68.5) / 0.3))
        c3 = smooth((t - 68.5) / 0.3) * (1 - smooth((t - 71.6) / 0.3))
        for ck, (px, py), gk, dk in ((c1, (0.5, 0.42), 1.0, 1.0), (c2, (0.36, 0.62 - 0.08 * smooth((t - 66.3) / 2)), 0.7, 1.3),
                                     (c3, (0.42 + 0.3 * smooth((t - 68.6) / 2.6), 0.55 - 0.32 * smooth((t - 68.6) / 2.6)), 1.4, 0.7)):
            if ck <= 0.01:
                continue
            P0 = (sw * px, sh * py)
            beam(L, (-20, sh * 1.02), P0, GOLD, ck * gk, t, 10 * gk)
            beam(L, (sw + 20, -20), P0, VIOLET, ck * dk, t + 3, 10 * dk)
            add(radial(P0[0], P0[1], 30 + 12 * math.sin(t * 40), gx2, gy2), [255, 250, 245], 1.4 * ck)
            add(radial(P0[0], P0[1], 110, gx2, gy2), [255, 200, 230], 0.5 * ck)
            add(flare(P0[0], P0[1], sw, sh), [255, 220, 235], 0.45 * ck)
            sparks.draw(L, t, math.floor(t * 3) / 3, P0[0], P0[1], 340, 0.7 * ck)
            streak.draw(L, t, 0.6 * ck, GOLDB, P0[0], P0[1])
        for a in (61.6, 62.6, 66.4, 68.6, 69.8):
            sx, sy = (0.5, 0.42) if a < 63 else ((0.36, 0.6) if a < 68 else (0.5, 0.48))
            swv = shockwave(t, a, sw * sx, sh * sy, sw, sh)
            if swv is not None:
                add(swv, [255, 220, 240], 0.8)
        # Luz do sol: the light breaks the storm from above; alegria: the dust bursts; Deus: the climax
        brk = smooth((t - 71.2) / 0.6) * (1 - smooth((t - 81.5) / 1.5))
        if brk > 0.01:
            add(rays(sw * 0.5, -sh * 0.06, t * 0.5, gx2, gy2, 18), [255, 235, 210], (0.12 + 0.3 * p_luz) * brk)
            add(radial(sw * 0.5, 0, 260, gx2, gy2), GOLD, (0.12 + 0.28 * p_luz) * brk)
            add(flare(sw * 0.5, sh * 0.06, sw, sh), [255, 225, 190], (0.15 + 0.4 * p_luz) * brk)
        sw_l = shockwave(t, 71.4, sw * 0.5, sh * 0.3, sw, sh, 0.5, 700)
        if sw_l is not None:
            add(sw_l, [255, 235, 210], 1.0)
        streak.draw(L, t, 1.2 * p_luz + 0.8 * p_deus, GOLDB, sw * 0.5, sh * 0.3)
        add(radial(sw * 0.5, sh * 0.35, 260, gx2, gy2), [255, 240, 225], 0.22 * p_ale)
        rise.draw(L, t, 74.6, sw * 0.5, sh * 0.5, 360, 1.2)
        mc = G.magic_circle(t, 79.2, sw * 0.5, sh * 0.86, sw * 0.46, sw, sh)
        if mc is not None:
            add(mc, [255, 220, 150], 1.0)
        add(radial(sw * 0.5, sh * 0.3, 320, gx2, gy2), GOLD, 0.3 * p_deus)
        sw_d = shockwave(t, 79.2, sw * 0.5, sh * 0.86, sw, sh, 0.3, 600)
        if sw_d is not None:
            add(sw_d, [255, 220, 150], 0.9)
        rise.draw(L, t, 79.2, sw * 0.5, sh * 0.6, 420, 1.3)
        L = cv2.GaussianBlur(L, (0, 0), 1.2)
        img = P.screen(img, cv2.resize(L, (W, H)))
        img += 0.1 * p_bolt + 0.12 * pulse(t, 71.4, 0.05, 0.4) + 0.1 * pulse(t, 79.2, 0.05, 0.5) + 0.06 * p_hit
        # depth layers: rain in the storm, gold dust, feathers in front of everything
        R = rain.draw(t, 0.55 * storm, 0.3 + 0.3 * p_inq)
        if R is not None:
            img = P.screen(img, R * np.array([0.95, 0.9, 0.85], np.float32))
        D = dust.draw(t, 0.18 + 0.4 * (p_mil + p_ale + p_deus), (0.42 + 0.15 * p_luz) * (1 - storm),
                      0.7 * max(p_ale, p_deus))
        if D is not None:
            img = P.screen(img, D)
        fa = (0.35 + 0.9 * smooth((t - 39.0) / 0.4) * (1 - smooth((t - 44.0) / 1.5))
              + 0.6 * smooth((t - 47.4) / 0.5) * (1 - smooth((t - 52.0) / 1.0))
              + 0.6 * smooth((t - 71.4) / 0.6)) * (1 - storm)
        Fr = feathers.draw(t, fa, 1.2 * p_lib + 0.9 * (smooth((t - 47.4) / 0.5) - smooth((t - 51.6) / 1.0)) + 0.5 * p_deus)
        if Fr is not None:
            fb, fal = Fr
            img = img * (1 - fal * 0.85) + fb * 0.95
        img = P.grade(img, gyf)
        img *= smooth(t / 1.0)
        for name, a, b, o in SHOTS[1:]:
            img += 0.1 * math.exp(-((t - a) / 0.1) ** 2)
        img *= 1 - SCRIM * lyr.on(t)
        lyr.draw(img, t)
        # the title comes out of depth in the intro and returns for the end card; the credits stay at the top
        ki = smooth((t - 1.6) / 1.2) * (1 - smooth((t - 8.2) / 0.8))
        put_title(img, title, 380, ki, 0.82 + 0.18 * smooth((t - 1.6) / 2.0) + 0.04 * smooth((t - 7.6) / 1.2))
        tt = t - 82.4
        if tt > 0:
            put_title(img, title, 380, smooth(tt / 1.0), 0.85 + 0.15 * smooth(tt / 1.6))
        ck = smooth((t - 8.6) / 0.8) * (1 - smooth((t - 81.8) / 0.6)) + smooth((t - 83.4) / 0.8)
        if ck > 0.003:
            ca, cg = cred
            y0 = 262
            if t >= 82:                                 # on the end card only the credits line, under the title
                ca, cg, y0 = ca[80:], cg[80:], 720
            roi = img[y0:y0 + ca.shape[0]]
            roi *= 1 - np.clip(cg * 2.0, 0, 0.75)[..., None] * min(ck, 1)
            roi[:] = roi * (1 - ca[..., None] * min(ck, 1)) + (GOLD + 30) / 255 * ca[..., None] * min(ck, 1)
        ea, es, eg = ed
        ek = smooth((t - 8.8) / 0.6)                    # after the intro title
        ex, ey = editor_pos(t)
        if tt > 1.4:                                    # on the end card it settles under the credits
            m = smooth((tt - 1.4) / 0.8)
            ex, ey = ex + (W / 2 - ex) * m, ey + (900 - ey) * m
        x0, y0 = int(ex - ea.shape[1] / 2), int(ey - ea.shape[0] / 2)
        roi = img[y0:y0 + ea.shape[0], x0:x0 + ea.shape[1]]
        roi *= 1 - es[..., None] * 0.75 * ek
        roi += eg[..., None] * GOLD / 255 * 0.4 * ek
        roi[:] = roi * (1 - ea[..., None] * ek) + CREAM / 255 * ea[..., None] * ek
        img *= 1 - smooth((t - (DUR - 1.4)) / 1.4)
        img += grain[i % len(grain)]
        frame = P.to_u8(img)
        if preview:
            cv2.imwrite(f"{out}_{t:05.1f}.png", frame)
            continue
        enc.stdin.write(frame.tobytes())
        if i % 150 == 0:
            print(f"{t:5.1f}s", flush=True)
    if preview:
        return
    enc.stdin.close()
    enc.wait()
    if clip:                                   # chunks are joined and get the sound in grandia_paralelo.sh
        os.replace(tmp, out)
        return
    subprocess.run([
        "ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-i", audio, "-filter_complex",
        f"[1:a]atrim=0:{DUR},afade=t=out:st={DUR - 1.2}:d=1.2,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-movflags", "+faststart", "-t", str(DUR), out], check=True)
    os.remove(tmp)


if __name__ == "__main__":
    main(*sys.argv[1:4])

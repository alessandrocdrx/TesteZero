"""'Eu nasci pra ser': a 100% AI Reel about power, magic, overcoming and pride.
Seven painted scenes (AI images), an original poem narrated by an AI voice, an AI score.
Everything moves in 3D: a virtual camera tilts and pushes into each painting, gold dust flies
through depth (size and blur follow 1/z), and each key word of the poem fires its own effect
on the exact syllable. Captions appear word by word inside the Reels/TikTok safe zone.
Usage: poder.py CENAS_DIR VOZ.mp3 TRILHA.mp3 OUT.mp4      (PREVIEW="3.2,23.7" for review frames)"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
FD = os.environ.get("FONTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"))
ITALIC = os.path.join(FD, "CormorantGaramond-Italic.ttf")
SERIF = os.path.join(FD, "CormorantGaramond.ttf")
BEBAS = os.path.join(FD, "BebasNeue-Regular.ttf")
GOLD = np.array([120, 200, 255], np.float32)          # BGR
CREAM = np.array([225, 240, 250], np.float32)
VOICE_AT = 1.0                                        # the voice starts after one second of score
DUR = 43.5
HANDLE = "@alessandrocdrx"

# the poem, word by word, with onsets measured on the narration (seconds in the voice file)
POEM = [
    [("Antes", 0.0), ("de", 0.4), ("ser", 0.5), ("fogo,", 0.7), ("eu", 1.8), ("fui", 2.0), ("faísca.", 2.2)],
    [("Me", 3.3), ("disseram:", 3.6), ("diminui.", 4.3), ("Eu", 5.4), ("cresci.", 5.6)],
    [("Carrego", 6.5), ("no", 6.9), ("peito", 7.1), ("um", 7.5), ("reino", 7.7), ("inteiro,", 8.0)],
    [("feito", 8.8), ("de", 9.0), ("quedas", 9.2), ("que", 9.7), ("viraram", 9.9), ("chão.", 10.3)],
    [("Cada", 11.0), ("cicatriz", 11.2), ("é", 11.8), ("um", 12.0), ("mapa:", 12.1)],
    [("mostra", 12.8), ("onde", 13.2), ("a", 13.4), ("dor", 13.5), ("tentou", 13.7), ("entrar…", 14.0)],
    [("e", 15.0), ("onde", 15.05), ("eu", 15.2), ("não", 15.3), ("deixei.", 15.6)],
    [("Não", 16.4), ("peço", 16.6), ("licença", 17.0), ("pra", 17.4), ("brilhar.", 17.6)],
    [("Minha", 18.3), ("magia", 18.5), ("não", 18.9), ("cabe", 19.0), ("na", 19.3), ("régua", 19.5),
     ("de", 19.8), ("ninguém.", 20.0)],
    [("Sou", 20.8), ("verso", 21.1), ("escrito", 21.3), ("à", 21.7), ("mão.", 22.0)],
    [("Sou", 22.6), ("trovão", 22.7), ("em", 23.3), ("silêncio.", 23.5)],
    [("Sou", 24.3), ("a", 24.4), ("raiz", 24.5), ("que", 24.9), ("rachou", 25.0), ("a", 25.5), ("pedra", 25.7)],
    [("pra", 26.1), ("ver", 26.5), ("o", 26.7), ("sol.", 26.8)],
    [("Tenho", 27.4), ("orgulho", 27.6), ("de", 28.1), ("cada", 28.3), ("pedaço", 28.6), ("meu,", 29.2)],
    [("inclusive", 29.5), ("dos", 30.0), ("que", 30.5), ("tentaram", 30.6), ("quebrar.", 31.0)],
    [("Eu", 31.8), ("não", 31.9), ("nasci", 32.1), ("pra", 32.5), ("caber.", 32.7)],
    [("Eu", 33.5), ("nasci", 33.6), ("pra", 34.0), ("ser.", 34.2)],
    [("E", 34.9), ("ser", 35.0), ("quem", 35.3), ("eu", 35.5), ("sou", 35.7), ("é", 36.0), ("o", 36.4),
     ("meu", 36.5), ("maior", 36.6), ("poder.", 37.1)],
]
LINE_END = [2.9, 6.2, 8.6, 10.7, 12.4, 14.4, 16.1, 18.0, 20.4, 22.3, 24.0, 25.95, 27.1, 29.45, 31.4,
            33.1, 34.6, 37.6]
KEYS = {"faísca.", "cresci.", "reino", "mapa:", "brilhar.", "magia", "trovão", "sol.", "orgulho",
        "quebrar.", "caber.", "ser.", "poder."}

# scenes: (image, start, end, camera) in video seconds; camera = zoom from/to, pan, yaw/pitch degrees
SCENES = [
    ("s1", 0.0, 7.25, dict(z=(1.18, 1.02), pan=(0, 40), yaw=(-3, 2), pitch=(4, 0))),
    ("s2", 7.25, 11.85, dict(z=(1.02, 1.14), pan=(-20, 10), yaw=(4, -2), pitch=(0, 2))),
    ("s3", 11.85, 17.25, dict(z=(1.10, 1.22), pan=(30, -30), yaw=(-4, 3), pitch=(2, -2))),
    ("s4", 17.25, 21.65, dict(z=(1.20, 1.04), pan=(0, -50), yaw=(2, -3), pitch=(-5, 1))),
    ("s5", 21.65, 28.25, dict(z=(1.04, 1.18), pan=(0, 60), yaw=(-3, 3), pitch=(-3, 3))),
    ("s6", 28.25, 32.65, dict(z=(1.16, 1.04), pan=(10, -20), yaw=(3, -3), pitch=(0, 0))),
    ("s7", 32.65, DUR, dict(z=(1.02, 1.20), pan=(0, 80), yaw=(-2, 2), pitch=(3, -2))),
]
XFADE = 0.7


def v(t_voice):
    return t_voice + VOICE_AT


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def pulse(t, at, pre=0.12, post=0.9):
    """0 → 1 exactly on the word, then decays"""
    if t < at - pre or t > at + post * 4:
        return 0.0
    if t < at:
        return smooth((t - at + pre) / pre)
    return math.exp(-(t - at) / post)


def font(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight:
        f.set_variation_by_name(weight)
    return f


# ---------- 3D camera on a painting ----------
class Painting:
    def __init__(self, path):
        img = cv2.imread(path, cv2.IMREAD_COLOR)
        s = max(W * 1.25 / img.shape[1], H * 1.25 / img.shape[0])
        self.img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        self.h, self.w = self.img.shape[:2]

    def view(self, zoom, dx, dy, yaw, pitch):
        """the painting as a plane in 3D, seen by a pinhole camera: rotating it gives real perspective"""
        f = 1.6 * W
        cx, cy = self.w / 2, self.h / 2
        ya, pa = math.radians(yaw), math.radians(pitch)
        Ry = np.array([[math.cos(ya), 0, math.sin(ya)], [0, 1, 0], [-math.sin(ya), 0, math.cos(ya)]])
        Rx = np.array([[1, 0, 0], [0, math.cos(pa), -math.sin(pa)], [0, math.sin(pa), math.cos(pa)]])
        R = Rx @ Ry
        k = H / (self.h / 1.25) * zoom      # the painting fills the frame with a 25% margin at zoom 1
        src, dst = [], []
        for x, y in ((0, 0), (self.w, 0), (self.w, self.h), (0, self.h)):
            p = R @ np.array([(x - cx) * k, (y - cy) * k, 0.0])
            z = f + p[2]
            dst.append((W / 2 + f * p[0] / z + dx, H / 2 + f * p[1] / z + dy))
            src.append((x, y))
        M = cv2.getPerspectiveTransform(np.float32(src), np.float32(dst))
        return cv2.warpPerspective(self.img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def scene_frame(p, cam, u, t, shake):
    e = smooth(u) * 0.7 + u * 0.3
    lerp = lambda ab: ab[0] + (ab[1] - ab[0]) * e
    breath = 0.006 * math.sin(t * 1.3)
    z = lerp(cam["z"]) + breath
    dx = cam["pan"][0] * (e - 0.5) + shake[0] + 6 * math.sin(t * 0.7)
    dy = cam["pan"][1] * (e - 0.5) + shake[1] + 5 * math.sin(t * 0.9 + 1)
    return p.view(z, dx, dy, lerp(cam["yaw"]), lerp(cam["pitch"]))


# ---------- gold dust flying through depth ----------
class Dust:
    def __init__(self, n=420, seed=7):
        r = np.random.default_rng(seed)
        self.x = r.uniform(-1.6, 1.6, n)
        self.y = r.uniform(-2.6, 2.6, n)
        self.z0 = r.uniform(0.25, 4.0, n)
        self.ph = r.uniform(0, 6.28, n)
        self.hue = r.uniform(0, 1, n)

    def draw(self, t, speed, amount, burst=0.0, origin=(0.0, 0.3)):
        """layers by depth: near motes are big and soft, far ones tiny and sharp (bokeh)"""
        if amount <= 0.01:
            return None
        sw, sh = W // 2, H // 2
        layers = [np.zeros((sh, sw, 3), np.float32) for _ in range(3)]
        travel = t * speed
        z = (self.z0 - travel) % 3.75 + 0.25
        x = self.x + 0.05 * np.sin(t * 0.8 + self.ph)
        y = self.y - 0.04 * t + 0.05 * np.cos(t * 0.6 + self.ph)
        if burst > 0:                                   # a word blows the dust outward from a point
            x = x + (x - origin[0]) * burst * 0.8
            y = y + (y - origin[1]) * burst * 0.8
        f = 0.9 * sw
        px = sw / 2 + f * x / z
        py = sh / 2 + f * y / z
        for i in np.argsort(-z):
            if not (-40 < px[i] < sw + 40 and -40 < py[i] < sh + 40):
                continue
            inv = 1 / z[i]
            rad = max(1.0, 2.2 * inv)
            tw = 0.6 + 0.4 * math.sin(t * 3 + self.ph[i])
            col = GOLD * (0.55 + 0.45 * self.hue[i]) + (1 - self.hue[i]) * np.array([60, 40, 0])
            col = col / 255 * tw * min(1.6, 0.35 + 0.9 * inv) * amount
            li = 0 if inv < 0.8 else (1 if inv < 1.6 else 2)
            cv2.circle(layers[li], (int(px[i]), int(py[i])), int(rad), col.tolist(), -1, cv2.LINE_AA)
        out = layers[0] + cv2.GaussianBlur(layers[1], (0, 0), 2.0) + cv2.GaussianBlur(layers[2], (0, 0), 6.0) * 1.6
        out += cv2.GaussianBlur(out, (0, 0), 8) * 0.8              # glow
        return cv2.resize(out, (W, H), interpolation=cv2.INTER_LINEAR)


class Embers:
    """sparks that rise from a point, used at 'faísca' and at 'ser'"""
    def __init__(self, n, seed):
        r = np.random.default_rng(seed)
        self.a = r.uniform(0, 6.28, n)
        self.sp = r.uniform(0.3, 1.0, n)
        self.life = r.uniform(1.0, 2.6, n)
        self.wob = r.uniform(0, 6.28, n)

    def draw(self, buf, t, at, cx, cy, spread, power):
        dt = t - at
        if dt < 0 or power <= 0:
            return
        for a, sp, life, wob in zip(self.a, self.sp, self.life, self.wob):
            if dt > life:
                continue
            k = dt / life
            r = spread * sp * (1 - math.exp(-dt * 2.2))
            x = cx + math.cos(a) * r + 14 * math.sin(wob + dt * 4)
            y = cy + math.sin(a) * r * 0.6 - 260 * sp * dt
            c = (GOLD + np.array([0, 20, 40])) / 255 * (1 - k) ** 1.5 * power
            cv2.circle(buf, (int(x), int(y)), max(1, int(4 * (1 - k) + 1)), c.tolist(), -1, cv2.LINE_AA)


# ---------- light: blooms, rays, lightning ----------
def radial(cx, cy, r, gx, gy):
    return np.exp(-((gx - cx) ** 2 + (gy - cy) ** 2) / (2 * r * r)).astype(np.float32)


def rays(cx, cy, t, gx, gy, n=14):
    a = np.arctan2(gy - cy, gx - cx)
    d = np.sqrt((gx - cx) ** 2 + (gy - cy) ** 2)
    s = 0.6 * (0.5 + 0.5 * np.cos(a * n + t * 0.6)) ** 3 + 0.4 * (0.5 + 0.5 * np.cos(a * (n - 5) - t * 0.4)) ** 4
    return cv2.GaussianBlur((s * np.exp(-d / 420)).astype(np.float32), (0, 0), 3)


def lightning(seed, sw, sh):
    r = np.random.default_rng(seed)
    buf = np.zeros((sh, sw), np.float32)

    def bolt(x, y, ang, length, width, depth):
        while length > 0 and 0 <= y < sh:
            step = r.uniform(12, 26)
            ang = 0.6 * ang + r.normal(0, 0.45)
            nx, ny = x + math.sin(ang) * step, y + math.cos(ang) * step
            cv2.line(buf, (int(x), int(y)), (int(nx), int(ny)), 1.0, max(1, int(width)), cv2.LINE_AA)
            if depth < 2 and r.random() < 0.07:
                bolt(nx, ny, ang + r.choice([-0.8, 0.8]), length * 0.4, width * 0.6, depth + 1)
            x, y, length = nx, ny, length - step
    bolt(sw * 0.62, 0, 0.1, sh * 0.55, 3, 0)
    return cv2.GaussianBlur(buf, (0, 0), 1.2) + cv2.GaussianBlur(buf, (0, 0), 12) * 2.5


# ---------- captions ----------
class Captions:
    """each line is laid out once; words fade and rise in on their own syllable, the spoken word turns gold"""
    def __init__(self):
        self.f = font(ITALIC, 84, b"SemiBold Italic")
        self.fk = font(ITALIC, 104, b"Bold Italic")
        self.lines = []
        d0 = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
        maxw, space = 860, 22
        for words in POEM:
            items, rows, row, rw = [], [], [], 0
            for wtxt, at in words:
                ff = self.fk if wtxt in KEYS else self.f
                ww = d0.textlength(wtxt, font=ff)
                if row and rw + space + ww > maxw:
                    rows.append((row, rw))
                    row, rw = [], 0
                rw += (space if row else 0) + ww
                row.append((wtxt, at, ff, ww))
            rows.append((row, rw))
            lh = 112
            y0 = -(len(rows) - 1) * lh / 2
            for ri, (row, rw) in enumerate(rows):
                x = -rw / 2
                for wtxt, at, ff, ww in row:
                    items.append((self.sprite(wtxt, ff), x + ww / 2, y0 + ri * lh, v(at), wtxt in KEYS))
                    x += ww + space
            self.lines.append(items)

    @staticmethod
    def sprite(txt, ff):
        pad = 40
        b = ff.getbbox(txt)
        im = Image.new("L", (int(b[2] - b[0]) + 2 * pad, int(ff.size * 1.45) + 2 * pad), 0)
        ImageDraw.Draw(im).text((pad - b[0], pad), txt, font=ff, fill=255)
        a = np.array(im).astype(np.float32) / 255
        sh = np.array(im.filter(ImageFilter.GaussianBlur(10))).astype(np.float32) / 255
        glow = np.array(im.filter(ImageFilter.GaussianBlur(18))).astype(np.float32) / 255
        return a, sh, glow

    def draw(self, img, t, cx=W / 2 - 40, cy=1330):
        for li, items in enumerate(self.lines):
            start, end = v(POEM[li][0][1]) - 0.15, v(LINE_END[li]) + 0.35
            if not (start <= t < end + 0.3):
                continue
            out = 1 - smooth((t - end) / 0.3)
            nxt = [it[3] for it in items[1:]] + [v(LINE_END[li])]
            for (spr, x, y, at, key), until in zip(items, nxt):
                a_in = smooth((t - at + 0.12) / 0.28)
                if a_in <= 0:
                    continue
                speaking = 1.0 if at <= t < max(until, at + 0.25) else 0.0
                lift = (1 - a_in) * 26
                scale = 1.0 + 0.10 * pulse(t, at, 0.1, 0.35) * (2.2 if key else 1)
                col = CREAM + (GOLD - CREAM) * max(speaking, 0.65 if key and t >= at else 0)
                self.blit(img, spr, cx + x, cy + y + lift, scale, a_in * out, col, key and t >= at)

    @staticmethod
    def blit(img, spr, x, y, scale, alpha, col, glow):
        a, sh, gl = spr
        if scale != 1.0:
            a = cv2.resize(a, None, fx=scale, fy=scale)
            sh = cv2.resize(sh, a.shape[::-1])
            gl = cv2.resize(gl, a.shape[::-1])
        h, w = a.shape
        x0, y0 = int(x - w / 2), int(y - h / 2)
        X0, Y0, X1, Y1 = max(x0, 0), max(y0, 0), min(x0 + w, W), min(y0 + h, H)
        if X1 <= X0 or Y1 <= Y0:
            return
        sl = (slice(Y0 - y0, Y1 - y0), slice(X0 - x0, X1 - x0))
        roi = img[Y0:Y1, X0:X1]
        s = sh[sl][..., None] * 0.85 * alpha
        roi *= 1 - s
        if glow:
            roi += gl[sl][..., None] * GOLD / 255 * 0.55 * alpha
        aa = a[sl][..., None] * alpha
        roi[:] = roi * (1 - aa) + col / 255 * aa


def big_title(lines):
    """end card: 'EU NASCI / PRA SER.' in tall capitals, gold, with its own glow"""
    f = font(BEBAS, 230)
    im = Image.new("L", (W, 560), 0)
    d = ImageDraw.Draw(im)
    for k, txt in enumerate(lines):
        tw = d.textlength(txt, font=f)
        d.text(((W - tw) / 2, 20 + k * 250), txt, font=f, fill=255)
    a = np.array(im).astype(np.float32) / 255
    return a, cv2.GaussianBlur(a, (0, 0), 24)


def handle_sprite():
    f = font(ITALIC, 46, b"SemiBold Italic")
    b = f.getbbox(HANDLE)
    im = Image.new("L", (int(b[2]) + 60, 110), 0)
    ImageDraw.Draw(im).text((30, 20), HANDLE, font=f, fill=255)
    a = np.array(im).astype(np.float32) / 255
    return a, cv2.GaussianBlur(a, (0, 0), 6), cv2.GaussianBlur(a, (0, 0), 14)


# ---------- grade: one palette for seven paintings ----------
def grade(img, gy):
    lum = img.mean(2, keepdims=True)
    shadows = np.clip(1 - lum * 2.2, 0, 1)
    highs = np.clip(lum * 1.8 - 0.8, 0, 1)
    img = img + shadows * np.array([0.05, 0.015, -0.01]) + highs * np.array([-0.03, 0.01, 0.04])
    vig = 1 - 0.38 * np.clip(((gy - 0.47) * 1.3) ** 2 + 0.0, 0, 1)
    return img * vig


def main(cenas, voz, trilha, out):
    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    paint = {s[0]: Painting(os.path.join(cenas, s[0] + ".png")) for s in SCENES}
    dust, caps = Dust(), Captions()
    spark, rise = Embers(160, 3), Embers(260, 11)
    title = big_title(["EU NASCI", "PRA SER."])
    hand = handle_sprite()
    sw, sh = W // 2, H // 2
    gy2, gx2 = np.mgrid[0:sh, 0:sw].astype(np.float32)
    gyf = (np.mgrid[0:H, 0:1][0].astype(np.float32) / H)[..., None]
    bolt = lightning(5, sw, sh)
    grain_r = np.random.default_rng(1)
    T = {w: v(at) for line in POEM for w, at in line}          # last onset of each word
    ON = lambda w: T[w]
    tmp = out + ".video.mp4"
    enc = None if preview else subprocess.Popen([
        "ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
        tmp], stdin=subprocess.PIPE)
    frames = [int(round(p * FPS)) for p in preview] if preview else range(int(DUR * FPS))
    for i in frames:
        t = i / FPS
        # word-driven energies
        p_cresci = pulse(t, ON("cresci."), 0.1, 0.5)
        p_trov = pulse(t, ON("trovão"), 0.03, 0.18)
        p_quebrar = pulse(t, ON("quebrar."), 0.05, 0.35)
        p_poder = pulse(t, ON("poder."), 0.1, 1.4)
        shake = (0.0, 0.0)
        for p, amp in ((p_trov, 22), (p_quebrar, 18), (p_cresci, 8), (p_poder, 10)):
            shake = (shake[0] + amp * p * math.sin(t * 91), shake[1] + amp * p * math.cos(t * 77))
        # base: the current painting, with a dolly-through crossfade into the next one
        img = None
        for k, (name, a, b, cam) in enumerate(SCENES):
            lo, hi = a - (XFADE / 2 if k else 0), b + (XFADE / 2 if k < len(SCENES) - 1 else 0)
            if not (lo <= t < hi):
                continue
            u = (t - lo) / (hi - lo)
            fr = scene_frame(paint[name], cam, u, t, shake).astype(np.float32) / 255
            w_in = smooth((t - lo) / XFADE) if k else 1.0
            w_out = 1 - smooth((t - (hi - XFADE)) / XFADE) if k < len(SCENES) - 1 else 1.0
            wgt = min(w_in, w_out)
            img = fr * wgt if img is None else img + fr * wgt
        img = np.clip(img, 0, 1.5)
        # punch zoom on 'cresci' and 'poder'
        punch = 0.06 * p_cresci + 0.05 * p_poder
        if punch > 0.002:
            M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1 + punch)
            img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        # light layer at half resolution
        L = np.zeros((sh, sw, 3), np.float32)
        def add(mask, col, k):
            L[:] += mask[..., None] * (np.array(col, np.float32) / 255) * k
        add(radial(sw * 0.5, sh * 0.66, 70 + 160 * pulse(t, ON("faísca."), 0.1, 0.8), gx2, gy2),
            GOLD, 1.3 * pulse(t, ON("faísca."), 0.1, 0.8) + 0.25 * (t < v(3.0)))
        add(radial(sw * 0.5, sh * 0.62, 150, gx2, gy2), GOLD, 1.1 * pulse(t, ON("reino"), 0.15, 0.9))
        sweep = pulse(t, ON("mapa:"), 0.2, 1.0) + pulse(t, ON("deixei."), 0.15, 0.8)
        if sweep > 0.01:                                       # a diagonal sheen across the gold scars
            s = (t - ON("mapa:")) * 260 - 200
            add(np.exp(-((gx2 + gy2 * 0.5 - s) / 40) ** 2).astype(np.float32), GOLD, 0.8 * sweep)
        p_br = pulse(t, ON("brilhar."), 0.15, 1.2)
        if p_br > 0.01:
            add(rays(sw * 0.5, sh * 0.42, t, gx2, gy2), [255, 200, 220], 0.55 * p_br)
            ring = np.exp(-((np.sqrt((gx2 - sw / 2) ** 2 + (gy2 - sh * 0.42) ** 2) - (t - ON("brilhar.")) * 520) / 14) ** 2)
            add(ring.astype(np.float32), [255, 220, 200], 0.6 * p_br)
        if p_trov > 0.01:
            add(bolt, [255, 235, 225], 1.8 * p_trov)
            L += 0.55 * p_trov
        p_sol = pulse(t, ON("sol."), 0.3, 1.3)
        if p_sol > 0.01:
            add(radial(sw * 0.5, sh * 0.18, 210, gx2, gy2), GOLD, 0.8 * p_sol)
            add(rays(sw * 0.5, sh * 0.18, t, gx2, gy2, 18), GOLD, 0.5 * p_sol)
        p_org = pulse(t, ON("orgulho"), 0.2, 1.2)
        if p_org > 0.01:
            add(radial(sw * 0.5, sh * 0.2, 160, gx2, gy2), GOLD, 1.0 * p_org)
        p_ser = pulse(t, ON("ser."), 0.1, 1.2)
        if p_ser + p_poder > 0.01:
            add(radial(sw * 0.5, sh * 0.45, 260, gx2, gy2), GOLD, 0.7 * p_ser + 1.0 * p_poder)
            add(rays(sw * 0.5, sh * 0.45, t, gx2, gy2, 16), GOLD, 0.45 * p_ser + 0.7 * p_poder)
        if t > ON("poder.") - 0.1:                                  # the sunrise keeps burning under the title
            add(radial(sw * 0.5, sh * 0.5, 300, gx2, gy2), GOLD, 0.35 * smooth((t - ON("poder.")) / 1.5))
        spark.draw(L, t, ON("faísca."), sw * 0.5, sh * 0.66, 120, 1.4)
        rise.draw(L, t, ON("ser."), sw * 0.5, sh * 0.62, 260, 1.4)
        rise.draw(L, t, ON("poder."), sw * 0.5, sh * 0.55, 380, 1.6)
        L = cv2.GaussianBlur(L, (0, 0), 1.5)
        img = img + cv2.resize(L, (W, H)) * (1 - img * 0.5)            # screen-like add
        # gold dust through depth: the camera flies faster on strong words
        speed = 0.18 + 0.5 * (p_cresci + p_br + p_ser + p_poder)
        burst = max(pulse(t, ON("quebrar."), 0.05, 0.6), p_poder * 0.6)
        amount = 0.55 + 0.4 * smooth((t - v(16)) / 4) + 0.5 * p_poder
        D = dust.draw(t, speed, amount, burst)
        if D is not None:
            img = img + D * (1 - img * 0.4)
        # chromatic split on 'quebrar'
        if p_quebrar > 0.02:
            o = int(10 * p_quebrar)
            img[..., 2] = np.roll(img[..., 2], o, 1)
            img[..., 0] = np.roll(img[..., 0], -o, 1)
        img = grade(img, gyf)
        # fade in from black, a brief flash at each cut
        img *= smooth(t / 0.8)
        for name, a, b, cam in SCENES[1:]:
            img += 0.22 * math.exp(-((t - a) / 0.12) ** 2)
        # captions and credits
        caps.draw(img, t)
        tt = t - (ON("poder.") + 0.9)
        if tt > 0:
            ta, tg = title
            k = smooth(tt / 0.8)
            y0 = 560 - int(30 * (1 - k))
            roi = img[y0:y0 + ta.shape[0]]
            roi += tg[..., None] * GOLD / 255 * 0.9 * k
            roi[:] = roi * (1 - ta[..., None] * k) + (GOLD + 40) / 255 * ta[..., None] * k
        ha, hs, hg = hand
        hk = smooth((t - 0.6) / 0.8) * (0.82 + 0.18 * math.sin(t * 1.1))
        hx = 70 + int(10 * math.sin(t * 0.5))
        hy = 150 + int(8 * math.sin(t * 0.8))
        if tt > 0.5:                                                   # the handle moves under the title
            m = smooth((tt - 0.5) / 1.0)
            hx = int(hx + ((W - ha.shape[1]) / 2 - hx) * m)
            hy = int(hy + (1140 - hy) * m)
            hk = max(hk, m)
        roi = img[hy:hy + ha.shape[0], hx:hx + ha.shape[1]]
        roi *= 1 - hs[..., None] * 0.7 * hk
        roi += hg[..., None] * GOLD / 255 * 0.35 * hk
        roi[:] = roi * (1 - ha[..., None] * hk) + CREAM / 255 * ha[..., None] * hk
        img *= 1 - smooth((t - (DUR - 0.8)) / 0.8)
        # film grain
        img += grain_r.normal(0, 0.018, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1)
        frame = (np.clip(img, 0, 1) * 255).astype(np.uint8)
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
    # sound: the voice one second in; the score ducks under it, swells at the end; -14 LUFS for the apps
    d = int(VOICE_AT * 1000)
    subprocess.run([
        "ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-i", voz, "-i", trilha, "-filter_complex",
        f"[1:a]adelay={d}|{d},apad,atrim=0:{DUR},asplit=2[vo][sc];"
        f"[2:a]atrim=0:{DUR},afade=t=out:st={DUR - 2.5}:d=2.5,volume=0.55[mu];"
        "[mu][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=400[duck];"
        "[vo][duck]amix=inputs=2:normalize=0:weights=1 1,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-movflags", "+faststart", "-t", str(DUR), out], check=True)
    os.remove(tmp)


if __name__ == "__main__":
    main(*sys.argv[1:5])

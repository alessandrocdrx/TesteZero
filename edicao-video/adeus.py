"""'A Deus' to the user's own recording: the seven animated shots of 'Glória' doubled (four of them also play
backwards), cut at the silence after the first verse. Big lyrics that fly in from depth word by word, and
effects that follow the hymn: the sun rises on 'Nascer do sol', a tear falls into the lake on 'lágrima',
feathers burst on 'liberdade', wind sweeps through depth on 'vento', a storm with rain in 3D and lightning on
'Tempestade… escuridão', and the light breaks through on 'Luz do sol… graças a Deus'.
Builds on grandia.py. Usage: CLIPES=dir adeus.py _ AUDIO OUT.mp4     (PREVIEW="15.2,24.7" for frames)"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poder as P  # noqa: E402
import grandia as G  # noqa: E402
from poder import W, H, FPS, GOLD, CREAM, smooth, pulse, radial, rays  # noqa: E402

DUR = 89.0                      # the song falls silent at 88 s, after the first verse

# the lyrics (Fandom, Portuguese original), timed to the singing by whisper; short groups, read at a glance
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
LINE_END = [12.6, 14.8, 19.0, 23.2, 26.8, 32.6, 36.3, 38.9, 44.0, 47.4, 51.3, 56.2, 61.3, 64.0, 69.6,
            74.3, 77.4, 82.0]
KEYS = {"sol,", "milagre", "lágrima", "luz,", "liberdade", "vento", "agradecimento", "Tempestade,",
        "escuridão", "Luz", "alegria,", "Deus"}

# the shots: each clip once forward and, for four of them, once backwards (vNr), cut on the phrases
SHOTS = [
    ("v7", 0.0, 9.2),      # intro: the balcony over the valley, the title
    ("v3", 9.2, 19.8),     # Nascer do sol, palavras, milagre
    ("v5", 19.8, 26.6),    # Água pura, uma lágrima (the lake)
    ("v5r", 26.6, 33.0),   # Paz, luz, amor
    ("v1", 33.0, 38.9),    # Fruto agreste, respiração
    ("v4", 38.9, 45.0),    # liberdade (wings on the cliff)
    ("v2", 45.0, 56.6),    # Harmonia, vento da bênção, agradecimento (the cathedral)
    ("v4r", 56.6, 63.0),   # Tempestade, inquietação
    ("v1r", 63.0, 70.8),   # escuridão
    ("v6", 70.8, 81.0),    # Luz do sol, alegria, graças a Deus
    ("v7r", 81.0, DUR),    # end card
]
XFADE = 0.8
BOLTS = [(58.4, 3), (59.9, 8), (61.6, 13), (65.6, 21), (68.2, 5)]


class Lyrics:
    """big words that fly in from depth on their own syllable; the sung word turns gold, key words stay gold
    and glow; when the group ends it flies on toward the camera and fades"""
    def __init__(self):
        f = P.font(P.ITALIC, 128, b"SemiBold Italic")
        fk = P.font(P.ITALIC, 164, b"Bold Italic")
        d0 = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
        maxw, space, lh = 940, 34, 158
        self.lines = []
        for words in LYRICS:
            rows, row, rw = [], [], 0
            for wtxt, at in words:
                ff = fk if wtxt in KEYS else f
                ww = d0.textlength(wtxt, font=ff) + (24 if wtxt in KEYS else 0)
                if row and rw + space + ww > maxw:
                    rows.append((row, rw))
                    row, rw = [], 0
                rw += (space if row else 0) + ww
                row.append((wtxt, at, ff, ww))
            rows.append((row, rw))
            items, y0 = [], -(len(rows) - 1) * lh / 2
            for ri, (row, rw) in enumerate(rows):
                x = -rw / 2
                for wtxt, at, ff, ww in row:
                    items.append((P.Captions.sprite(wtxt, ff), x + ww / 2, y0 + ri * lh, at, wtxt in KEYS))
                    x += ww + space
            self.lines.append(items)

    def on(self, t):
        """1 while a group is on screen (for the dark band behind it)"""
        k = 0.0
        for items, end in zip(self.lines, LINE_END):
            k = max(k, smooth((t - items[0][3] + 0.4) / 0.4) * (1 - smooth((t - end - 0.2) / 0.5)))
        return k

    def draw(self, img, t, cx=W / 2 - 30, cy=1290):
        for items, end in zip(self.lines, LINE_END):
            if not (items[0][3] - 0.25 <= t < end + 0.6):
                continue
            out = smooth((t - end) / 0.6)
            nxt = [it[3] for it in items[1:]] + [end]
            for (spr, x, y, at, key), until in zip(items, nxt):
                a_in = smooth((t - at + 0.15) / 0.38)
                if a_in <= 0:
                    continue
                spread = 1 + 0.4 * out                              # the group passes the camera
                scale = (0.55 + 0.45 * a_in) * spread * (1 + 0.09 * pulse(t, at, 0.1, 0.4) * (2 if key else 1))
                px = cx + x * spread
                py = cy + y * spread + 50 * (1 - a_in) - 70 * out
                speaking = 1.0 if at <= t < max(until, at + 0.3) else 0.0
                col = CREAM + (GOLD - CREAM) * max(speaking, 0.7 if key and t >= at else 0)
                P.Captions.blit(img, spr, px, py, scale, a_in * (1 - out), col, key and t >= at)


_band = np.exp(-((np.arange(H, dtype=np.float32) - 1290) / 260) ** 2)
SCRIM = (0.55 * _band)[:, None, None]


def title_sprite(txt, sub, size=190, tr=30):
    f = P.font(P.SERIF, size, b"SemiBold")
    fs = P.font(P.ITALIC, 62, b"Medium Italic")
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
    """streaks of air sweeping across through depth (the 'vento da bênção'), with petals of light"""
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


def shot(clips, name, lo, hi, t, shake, push):
    """the animated clip (its own camera already flies in 3D), a short one slowed to fit; a small push in"""
    c = clips[name]
    f = c.at((t - lo) * min(1.0, (c.n - 1) / c.fps / (hi - lo)))
    z = 1.0 + 0.04 * (t - lo) / (hi - lo) + push
    M = cv2.getRotationMatrix2D((W / 2, H * 0.45), 0, z)
    M[:, 2] += shake
    return cv2.warpAffine(f, M, (W, H), borderMode=cv2.BORDER_REFLECT)


def main(_cenas, audio, out):
    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    cdir = os.environ["CLIPES"]
    clips = {s[0]: G.Clip(os.path.join(cdir, s[0] + ".mp4")) for s in SHOTS}
    dust, feathers, rain, wind = P.Dust(n=360, seed=9), G.Feathers(), Rain(), Wind()
    lyr = Lyrics()
    rise = P.Embers(260, 11)
    title = title_sprite("A DEUS", "um hino ao Criador")
    hand = P.handle_sprite()
    sw, sh = W // 2, H // 2
    gy2, gx2 = np.mgrid[0:sh, 0:sw].astype(np.float32)
    gyf = (np.mgrid[0:H, 0:1][0].astype(np.float32) / H)[..., None]
    edge = np.clip((np.sqrt(((gx2 - sw / 2) / (sw * 0.62)) ** 2 + ((gy2 - sh * 0.45) / (sh * 0.6)) ** 2) - 0.45)
                   / 0.6, 0, 1).astype(np.float32)
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
        storm = smooth((t - 56.2) / 1.4) * (1 - smooth((t - 71.0) / 1.0))
        dark = smooth((t - 64.0) / 1.6) * (1 - smooth((t - 71.0) / 0.6))
        shake = (10 * p_inq * math.sin(t * 91) + 7 * p_bolt * math.sin(t * 67) + 5 * p_deus * math.sin(t * 83),
                 10 * p_inq * math.cos(t * 77) + 7 * p_bolt * math.cos(t * 59) + 5 * p_deus * math.cos(t * 71))
        u = (t - 36.6) / 2.4
        push = 0.035 * math.sin(math.pi * u) if 0 < u < 1 else 0.0          # 'respiração': the frame breathes
        img = None
        for k, (name, a, b) in enumerate(SHOTS):
            lo, hi = a - (XFADE / 2 if k else 0), b + (XFADE / 2 if k < len(SHOTS) - 1 else 0)
            if not (lo <= t < hi):
                continue
            fr = shot(clips, name, lo, hi, t, shake, push).astype(np.float32) / 255
            w_in = smooth((t - lo) / XFADE) if k else 1.0
            w_out = 1 - smooth((t - (hi - XFADE)) / XFADE) if k < len(SHOTS) - 1 else 1.0
            img = fr * min(w_in, w_out) if img is None else img + fr * min(w_in, w_out)
        punch = 0.05 * p_mil + 0.045 * p_lib + 0.04 * p_luz + 0.05 * p_deus
        if punch > 0.002:
            M = cv2.getRotationMatrix2D((W / 2, H * 0.45), 0, 1 + punch)
            img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        # the storm: colour drains to a cold blue, the frame darkens, the edges close in on 'escuridão'
        if storm > 0.005:
            g = cv2.transform(img, np.full((1, 3), 1 / 3, np.float32))
            cold = cv2.merge([g * 1.12, g * 0.96, g * 0.82])
            img = img * (1 - 0.65 * storm) + cold * (0.65 * storm)
            img *= (1 - 0.3 * storm - 0.25 * dark) * (1 - edge * 0.75 * dark)
        L = np.zeros((sh, sw, 3), np.float32)

        def add(mask, col, k):
            if k > 0.004:
                L[:] += mask[..., None] * (np.array(col, np.float32) / 255) * k
        # Nascer do sol: the sun swells and its rays turn; 'palavras' sparks; 'milagre' a magic circle
        sun = smooth((t - 9.0) / 2.5) * (1 - smooth((t - 19.4) / 0.8))
        if sun > 0.01:
            add(radial(sw * 0.47, sh * 0.37, 90 + 70 * smooth((t - 9.5) / 3), gx2, gy2), GOLD, 0.42 * sun)
            add(rays(sw * 0.47, sh * 0.37, t * 0.7, gx2, gy2, 14), [255, 225, 190], 0.22 * sun)
        rise.draw(L, t, 13.0, sw * 0.47, sh * 0.42, 260, 1.0)
        mc = G.magic_circle(t, 15.1, sw * 0.5, sh * 0.82, sw * 0.44, sw, sh)
        if mc is not None:
            add(mc, [255, 220, 150], 0.9)
        add(radial(sw * 0.5, sh * 0.45, 200, gx2, gy2), GOLD, 0.28 * p_mil)
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
        # liberdade: a gale of feathers, light opening behind her wings
        if p_lib > 0.01:
            add(rays(sw * 0.5, sh * 0.3, t, gx2, gy2, 16), [255, 235, 215], 0.5 * p_lib)
            add(radial(sw * 0.5, sh * 0.32, 240, gx2, gy2), GOLD, 0.4 * p_lib)
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
        # Luz do sol: the light breaks the storm from above; alegria: the dust bursts; Deus: the climax
        brk = smooth((t - 71.2) / 0.6) * (1 - smooth((t - 81.5) / 1.5))
        if brk > 0.01:
            add(rays(sw * 0.5, -sh * 0.06, t * 0.5, gx2, gy2, 18), [255, 235, 210], (0.12 + 0.3 * p_luz) * brk)
            add(radial(sw * 0.5, 0, 260, gx2, gy2), GOLD, (0.12 + 0.28 * p_luz) * brk)
        add(radial(sw * 0.5, sh * 0.35, 260, gx2, gy2), [255, 240, 225], 0.22 * p_ale)
        rise.draw(L, t, 74.6, sw * 0.5, sh * 0.5, 360, 1.2)
        mc = G.magic_circle(t, 79.2, sw * 0.5, sh * 0.86, sw * 0.46, sw, sh)
        if mc is not None:
            add(mc, [255, 220, 150], 1.0)
        add(radial(sw * 0.5, sh * 0.3, 320, gx2, gy2), GOLD, 0.3 * p_deus)
        rise.draw(L, t, 79.2, sw * 0.5, sh * 0.6, 420, 1.3)
        L = cv2.GaussianBlur(L, (0, 0), 1.5)
        img = P.screen(img, cv2.resize(L, (W, H)))
        img += 0.1 * p_bolt + 0.12 * pulse(t, 71.4, 0.05, 0.4) + 0.1 * pulse(t, 79.2, 0.05, 0.5)
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
        for name, a, b in SHOTS[1:]:
            img += 0.14 * math.exp(-((t - a) / 0.12) ** 2)
        img *= 1 - SCRIM * lyr.on(t)
        lyr.draw(img, t)
        # the title comes out of depth in the intro and returns for the end card
        ki = smooth((t - 1.6) / 1.2) * (1 - smooth((t - 8.2) / 0.8))
        put_title(img, title, 380, ki, 0.82 + 0.18 * smooth((t - 1.6) / 2.0) + 0.04 * smooth((t - 7.6) / 1.2))
        tt = t - 82.4
        if tt > 0:
            put_title(img, title, 380, smooth(tt / 1.0), 0.85 + 0.15 * smooth(tt / 1.6))
        ha, hs, hg = hand
        hk = smooth((t - 0.6) / 0.8) * (0.82 + 0.18 * math.sin(t * 1.1))
        hx, hy = 70 + int(10 * math.sin(t * 0.5)), 150 + int(8 * math.sin(t * 0.8))
        if tt > 0.5:
            m = smooth((tt - 0.5) / 1.0)
            hx = int(hx + ((W - ha.shape[1]) / 2 - hx) * m)
            hy = int(hy + (760 - hy) * m)
            hk = max(hk, m)
        roi = img[hy:hy + ha.shape[0], hx:hx + ha.shape[1]]
        roi *= 1 - hs[..., None] * 0.7 * hk
        roi += hg[..., None] * GOLD / 255 * 0.35 * hk
        roi[:] = roi * (1 - ha[..., None] * hk) + CREAM / 255 * ha[..., None] * hk
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

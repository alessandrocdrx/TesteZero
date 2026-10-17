"""Foreground layer for mundo.py: things between the camera and her, one family per verse.
Near-lens objects are defocused (depth of field), so they read as in front of her, not pasted on.
Everything is drawn at half resolution into three buffers: light (screen blend), near and mid (covering)."""
import math
import random

import cv2
import numpy as np

import efeitos as E
from calmo import smooth

SW, SH = E.SW, E.SH
LEAF = [(40, 105, 170), (30, 80, 140), (60, 140, 200), (35, 120, 120)]   # BGR: gold, rust, straw, olive
PINK = [(92, 64, 214), (120, 96, 232), (150, 130, 240), (70, 44, 190)]


def env(a, b, t, fin=1.0, fout=1.0):
    return E.env_at(a, b, t, fin, fout)


class Buffers:
    def __init__(self):
        self.light = np.zeros((SH, SW, 3), np.float32)
        self.near = np.zeros((SH, SW, 4), np.float32)   # premultiplied BGR + alpha
        self.mid = np.zeros((SH, SW, 4), np.float32)

    def busy(self):
        return self.light.any() or self.near[..., 3].any() or self.mid[..., 3].any()


def blob(buf, x, y, ax, ay, ang, col, a):
    """a covering ellipse (leaf, petal, feather) into a premultiplied buffer"""
    if a < 0.01 or not (-ax * 2 < x < SW + ax * 2 and -ax * 2 < y < SH + ax * 2):
        return
    m = np.zeros(buf.shape[:2], np.uint8)
    x0, y0 = int(max(x - ax - 2, 0)), int(max(y - ax - 2, 0))
    x1, y1 = int(min(x + ax + 3, SW)), int(min(y + ax + 3, SH))
    if x0 >= x1 or y0 >= y1:
        return
    sub = m[y0:y1, x0:x1]
    cv2.ellipse(sub, (int(x) - x0, int(y) - y0), (max(1, int(ax)), max(1, int(ay))), ang, 0, 360, 255, -1, cv2.LINE_AA)
    k = sub.astype(np.float32)[..., None] / 255 * a
    roi = buf[y0:y1, x0:x1]
    roi[..., :3] = roi[..., :3] * (1 - k) + np.float32(col) * k
    roi[..., 3:] = roi[..., 3:] * (1 - k) + k


class Leaves:
    """'Voa nas asas do vento': leaves and seeds blown across the lens; big blurred ones on the gust."""

    def __init__(self, seed=3):
        r = random.Random(seed)
        self.mid = [dict(x=r.uniform(0, SW + 200), y=r.uniform(0, SH), d=r.uniform(0.5, 1.0), ph=r.uniform(0, 6.3),
                         s=r.uniform(8, 16), col=r.choice(LEAF)) for _ in range(70)]
        self.near = [dict(t0=g + r.uniform(-0.6, 0.6), y=r.uniform(SH * 0.1, SH * 0.95), s=r.uniform(26, 48),
                          v=r.uniform(380, 560), ph=r.uniform(0, 6.3), col=r.choice(LEAF))
                     for g in E.GUSTS for _ in range(5)]
        self.travel, self.last = 0.0, None

    def draw(self, B, t, amount, energy, gust):
        if self.last is not None:
            self.travel += (t - self.last) * (40 + 90 * energy + 420 * gust)
        self.last = t
        for p in self.mid:
            x = (p["x"] + self.travel * p["d"]) % (SW + 200) - 100
            y = p["y"] + math.sin(t * 1.3 + p["ph"]) * 30 + self.travel * 0.08 * p["d"] % SH
            y = y % SH
            ang = math.degrees(t * 4 * p["d"] + p["ph"])
            blob(B.mid, x, y, p["s"], p["s"] * (0.3 + 0.3 * abs(math.sin(t * 3 + p["ph"]))), ang, p["col"],
                 amount * 0.9)
        for p in self.near:
            dt = t - p["t0"]
            x = -80 + p["v"] * dt
            if dt < 0 or x > SW + 80:
                continue
            y = p["y"] - 60 * dt + math.sin(dt * 3 + p["ph"]) * 25
            blob(B.near, x, y, p["s"], p["s"] * 0.45, math.degrees(dt * 5 + p["ph"]), p["col"], amount)

    @staticmethod
    def ribbons(B, t, amount, energy, gust):
        """silk-like wind streaks low in the frame"""
        k = amount * (0.25 + 0.5 * energy + 0.8 * gust)
        xs = np.arange(0, SW + 1, 12, dtype=np.float32)
        for j in range(5):
            y0 = SH * (0.55 + 0.08 * j)
            ys = y0 + 30 * np.sin(xs * 0.008 + t * (1.2 + 0.2 * j) + j) + 14 * np.sin(xs * 0.021 - t * 2 + j * 2)
            pts = np.stack([xs, ys], 1).astype(np.int32)
            c = (200 * k, 225 * k, 255 * k)
            cv2.polylines(B.light, [pts], False, c, 2, cv2.LINE_AA)


class Flight:
    """'livres': two big birds sweep past the lens, a few feathers drift down in front of her."""

    def __init__(self, seed=7):
        r = random.Random(seed)
        self.birds = [dict(t0=E.FLOCK_LIFT - 0.6, y0=SH * 0.95, y1=SH * 0.05, dir=1, s=150),
                      dict(t0=26.0, y0=SH * 0.15, y1=-SH * 0.1, dir=-1, s=110),
                      dict(t0=29.6, y0=SH * 0.9, y1=SH * 0.55, dir=1, s=90)]
        self.feathers = [dict(t0=E.BIRDS[0] + 1 + r.uniform(0, 14), x=r.choice([r.uniform(20, 150), r.uniform(390, 520)]),
                              v=r.uniform(35, 60), s=r.uniform(9, 15), ph=r.uniform(0, 6.3)) for _ in range(16)]

    def draw(self, B, t, amount):
        for b in self.birds:
            dt = t - b["t0"]
            if not (0 <= dt <= 1.6):
                continue
            k = dt / 1.6
            x = (-0.3 + 1.6 * k) * SW if b["dir"] > 0 else (1.3 - 1.6 * k) * SW
            y = b["y0"] + (b["y1"] - b["y0"]) * k
            s = b["s"] * (0.8 + 0.5 * math.sin(math.pi * k))
            flap = math.sin(dt * 14)
            wing = s * (0.25 + 0.4 * flap)
            # filled silhouette: leading edge of both wings, then back along a thicker trailing edge
            pts = np.array([[x - s, y - wing], [x - s * 0.4, y - wing * 0.15], [x, y + s * 0.05],
                            [x + s * 0.4, y - wing * 0.15], [x + s, y - wing],
                            [x + s * 0.45, y + s * 0.12 - wing * 0.1], [x, y + s * 0.22],
                            [x - s * 0.45, y + s * 0.12 - wing * 0.1]], np.int32)
            m = np.zeros((SH, SW), np.uint8)
            cv2.fillPoly(m, [pts], 255, cv2.LINE_AA)
            cv2.ellipse(m, (int(x), int(y)), (int(s * 0.22), int(s * 0.1)), 0, 0, 360, 255, -1, cv2.LINE_AA)
            a = m.astype(np.float32)[..., None] / 255 * amount * 0.92
            B.near[..., :3] = B.near[..., :3] * (1 - a) + np.float32((26, 22, 20)) * a
            B.near[..., 3:] = B.near[..., 3:] * (1 - a) + a
        for f in self.feathers:
            dt = t - f["t0"]
            if dt < 0:
                continue
            y = -20 + f["v"] * dt
            if y > SH + 20:
                continue
            x = f["x"] + math.sin(dt * 1.6 + f["ph"]) * 28
            blob(B.mid, x, y, f["s"], f["s"] * 0.32, 70 + math.sin(dt * 1.6 + f["ph"]) * 35, (235, 240, 245),
                 amount * 0.85)


def flare(B, t, amount, energy):
    """'o sol brilha tão forte': an anamorphic lens flare from the painted sun, peaking on 'солнце' and 'светом'"""
    peak = max(math.exp(-((t - E.SUN_BLOOM) / 1.2) ** 2), math.exp(-((t - 44.8) / 1.2) ** 2))
    k = amount * (0.35 + 0.3 * energy + 0.9 * peak)
    sx, sy = SW * (0.9 - 0.05 * math.sin(t * 0.2)), SH * 0.07
    L = np.zeros_like(B.light)
    cv2.ellipse(L, (int(sx), int(sy)), (int(SW * (0.6 + 0.5 * peak)), 3), 0, 0, 360, (255 * k, 200 * k, 140 * k), -1,
                cv2.LINE_AA)
    cv2.circle(L, (int(sx), int(sy)), int(50 + 40 * peak), (140 * k, 210 * k, 255 * k), -1, cv2.LINE_AA)
    cx, cy = SW / 2, SH / 2
    for f, r_, col in [(0.55, 20, (120, 200, 255)), (1.25, 46, (255, 170, 120)), (1.6, 14, (170, 255, 200)),
                       (2.05, 34, (255, 160, 200))]:
        gx, gy = sx + (cx - sx) * f, sy + (cy - sy) * f
        cv2.circle(L, (int(gx), int(gy)), r_, tuple(c * k * 0.12 for c in col), -1, cv2.LINE_AA)
    B.light += cv2.GaussianBlur(L, (0, 0), 3)


class Bokeh:
    """'as rosas se abrem': big defocused petals fall right in front of the lens; a burst on 'розы'."""

    def __init__(self, seed=15):
        r = random.Random(seed)
        self.p = [dict(t0=E.ROSES[0] + r.uniform(0, 8), x=r.uniform(-20, SW + 20), v=r.uniform(130, 210),
                       s=r.uniform(30, 55), ph=r.uniform(0, 6.3), col=r.choice(PINK)) for _ in range(12)]
        self.p += [dict(t0=E.ROSE_BURST + r.uniform(-0.2, 0.5), x=r.uniform(-20, SW + 20), v=r.uniform(220, 320),
                        s=r.uniform(35, 65), ph=r.uniform(0, 6.3), col=r.choice(PINK)) for _ in range(10)]

    def draw(self, B, t, amount, smile):
        for p in self.p:
            dt = t - p["t0"]
            if dt < 0:
                continue
            y = -80 + p["v"] * dt * (0.85 + 0.3 * smile)
            if y > SH + 80:
                continue
            x = p["x"] + math.sin(dt * 1.1 + p["ph"]) * 45
            sq = 0.45 + 0.5 * abs(math.sin(dt * 1.8 + p["ph"]))
            blob(B.near, x, y, p["s"], p["s"] * 0.6 * sq, math.degrees(dt * 1.2 + p["ph"]), p["col"], amount * 0.95)


class Forest:
    """'rouxinóis cantam nas matas verdes': we look through branches; fireflies and two nightingales flit past."""

    def __init__(self, seed=19):
        r = random.Random(seed)
        self.branch = []
        for corner in (0, 1):
            spr = np.zeros((SH // 2, SW // 2, 4), np.float32)
            for _ in range(70):
                x = r.uniform(0, SW * 0.45) if corner == 0 else r.uniform(SW * 0.05, SW * 0.5)
                y = r.uniform(0, SH * 0.3) * (1 - abs((x / (SW * 0.5)) - (0 if corner == 0 else 1)) * 0.6)
                s = r.uniform(18, 40)
                g = r.uniform(0.6, 1.0)
                blob(spr, x, y, s, s * 0.45, r.uniform(0, 180), (30 * g, 70 * g, 40 * g), 1.0)
            self.branch.append(cv2.GaussianBlur(spr, (0, 0), 5))
        self.flies = [(r.uniform(0, SW), r.uniform(SH * 0.25, SH), r.uniform(0, 6.3), r.uniform(0.6, 1.3))
                      for _ in range(26)]
        self.birds = [dict(t0=57.2, y=SH * 0.2, dir=1), dict(t0=61.0, y=SH * 0.82, dir=-1)]

    def draw(self, B, t, amount, energy):
        sway = math.sin(t * 0.9) * 8
        slide = (1 - amount) * 160
        for corner, spr in enumerate(self.branch):
            h, w = spr.shape[:2]
            x0 = int(-slide + sway) if corner == 0 else int(SW - w + slide + sway)
            y0 = int(-slide * 0.6)
            xa, xb = max(x0, 0), min(x0 + w, SW)
            ya, yb = max(y0, 0), min(y0 + h, SH)
            if xa >= xb or ya >= yb:
                continue
            s = spr[ya - y0:yb - y0, xa - x0:xb - x0] * amount
            roi = B.near[ya:yb, xa:xb]
            roi[:] = roi * (1 - s[..., 3:]) + s
        for x0, y0, ph, d in self.flies:
            x = x0 + math.sin(t * 0.5 * d + ph) * 40
            y = y0 + math.cos(t * 0.4 * d + ph) * 30
            k = amount * max(0.0, math.sin(t * 2.2 * d + ph)) ** 3 * (0.7 + 0.8 * energy)
            cv2.circle(B.light, (int(x), int(y)), int(6 + 6 * d), (110 * k, 240 * k, 220 * k), -1, cv2.LINE_AA)
        for b in self.birds:
            dt = t - b["t0"]
            if not (0 <= dt <= 1.1):
                continue
            x = (-0.1 + 1.2 * dt / 1.1) * SW if b["dir"] > 0 else (1.1 - 1.2 * dt / 1.1) * SW
            y = b["y"] + math.sin(dt * 9) * 14 - 40 * dt
            s = 26
            wing = s * (0.2 + 0.5 * math.sin(dt * 22))
            pts = np.array([[x - s, y - wing], [x, y + 4], [x + s, y - wing]], np.int32)
            m = np.zeros((SH, SW), np.uint8)
            cv2.polylines(m, [pts], False, 255, 5, cv2.LINE_AA)
            a = m.astype(np.float32)[..., None] / 255 * amount
            B.mid[..., :3] = B.mid[..., :3] * (1 - a) + np.float32((30, 40, 45)) * a
            B.mid[..., 3:] = B.mid[..., 3:] * (1 - a) + a


class Mist:
    """Her voice alone, under the moon: river mist rolls in front of her, rising and glowing with her voice."""

    def __init__(self, seed=23):
        r = np.random.default_rng(seed)
        n = np.zeros((SH // 2, SW), np.float32)
        for oc, amp in [(6, 1.0), (12, 0.5), (24, 0.25)]:
            g = r.random((oc, oc * 2)).astype(np.float32)
            g = np.hstack([g, g[:, :1]])
            n += cv2.resize(g, (SW + SW // (oc * 2), SH // 2), interpolation=cv2.INTER_CUBIC)[:, :SW] * amp
        n = (n - n.min()) / (n.max() - n.min())
        self.tex = np.hstack([n, n[:, ::-1]])   # mirrored, so the scroll wraps without a seam
        self.grad = (np.clip((np.arange(SH // 2) / (SH // 2)), 0, 1) ** 1.5)[:, None]

    def draw(self, B, t, amount, energy):
        off = int(t * 22) % self.tex.shape[1]
        tex = np.roll(self.tex, -off, axis=1)[:, :SW]
        m = np.clip(tex * 1.4 - 0.35, 0, 1) * self.grad * amount * (0.8 + 0.6 * energy)
        B.light[SH // 2:] += m[..., None] * np.float32((150, 120, 95))


class Foreground:
    def __init__(self):
        self.leaves, self.flight, self.bokeh, self.forest, self.mist = Leaves(), Flight(), Bokeh(), Forest(), Mist()

    def render(self, t, e, sm):
        B = Buffers()
        wind = max(env(a, b, t) for a, b in E.WIND)
        if wind > 0:
            gust = max(math.exp(-((t - g) / 0.8) ** 2) for g in E.GUSTS)
            self.leaves.draw(B, t, wind, e, gust)
        if (a := env(*E.BIRDS, t)) > 0:
            self.flight.draw(B, t, a)
        if (a := env(*E.SUN, t, 1.5, 1.5)) > 0:
            flare(B, t, a, e)
        if (a := env(*E.ROSES, t, 0.8, 1.2)) > 0:
            self.bokeh.draw(B, t, a, sm)
        if (a := env(*E.NIGHTINGALES, t, 1.2, 1.0)) > 0:
            self.forest.draw(B, t, a, e)
        if (a := env(*E.EMBERS, t, 2.0, 1.2)) > 0:
            self.mist.draw(B, t, a, e)
        return B

    @staticmethod
    def composite(img, B, mask, W, H):
        """img float BGR full-res; mask 1 away from her face. Near objects are defocused, mid ones lightly."""
        m = mask[..., None]
        for buf, sigma in ((B.mid, 1.2), (B.near, 4.5)):
            if not buf[..., 3].any():
                continue
            b = cv2.resize(cv2.GaussianBlur(buf, (0, 0), sigma), (W, H), interpolation=cv2.INTER_LINEAR)
            a = b[..., 3:] * m
            img = img * (1 - a) + b[..., :3] * m
        if B.light.any():
            L = cv2.resize(cv2.GaussianBlur(B.light, (0, 0), 1.5), (W, H), interpolation=cv2.INTER_LINEAR) * m
            img = 255 - (255 - img) * (255 - np.clip(L, 0, 255)) / 255
        return img

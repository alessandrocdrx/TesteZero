"""'Glória': a hymn to God as a vertical Reel, drawn like a fantasy JRPG from the Dreamcast years.
Seven anime scenes (AI images, one heroine kept consistent by a reference), an AI-sung hymn in
Portuguese. The camera moves through each painting in 3D, white feathers and gold dust fly in depth,
a magic circle lights under her on every 'Glória', and the lyrics appear word by word on the beat.
Builds on poder.py. Usage: grandia.py CENAS_DIR HINO.mp3 OUT.mp4     (PREVIEW="18.6,40.3" for frames)"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poder as P  # noqa: E402
from poder import W, H, FPS, GOLD, CREAM, smooth, pulse, radial, rays  # noqa: E402

DUR = 58.0
HANDLE = "@alessandrocdrx"

# the hymn as sung (seconds in the song), lines kept short so each one reads at a glance
HYMN = [
    [("Senhor,", 0.4), ("antes", 1.7), ("de", 2.0), ("ser", 2.4), ("chama,", 2.7)],
    [("eu", 3.4), ("fui", 3.6), ("faísca", 3.9)],
    [("na", 4.9), ("Tua", 5.6), ("mão", 6.2), ("aprendi", 6.7), ("a", 7.6), ("acender.", 7.9)],
    [("Disseram:", 9.1), ("diminui", 10.0)],
    [("e", 11.55), ("eu", 11.7), ("cresci,", 11.9)],
    [("pois", 12.8), ("foi", 13.2), ("o", 13.6), ("Teu", 13.9), ("sopro", 14.1), ("que", 14.8), ("me", 15.3),
     ("fez", 15.6), ("viver.", 16.1)],
    [("Glória,", 18.5), ("glória,", 20.1)],
    [("luz", 20.9), ("que", 21.0), ("me", 21.3), ("levanta,", 21.6)],
    [("das", 22.8), ("minhas", 23.2), ("quedas", 23.6), ("fizeste", 24.1), ("chão.", 24.7)],
    [("Cada", 25.4), ("cicatriz", 26.0), ("é", 26.7), ("Tua", 27.1), ("canção,", 27.4)],
    [("eu", 28.2), ("sou", 28.9), ("quem", 29.1), ("sou", 29.3), ("na", 29.6), ("Tua", 29.9), ("mão.", 30.4)],
    [("Não", 31.1), ("peço", 31.6), ("licença", 31.9), ("pra", 32.5), ("brilhar,", 33.1)],
    [("Tua", 33.8), ("graça", 34.1), ("não", 34.8), ("cabe", 35.0), ("em", 35.4), ("régua", 35.8), ("alguma.", 36.3)],
    [("Glória,", 38.2), ("glória,", 40.2)],
    [("asas", 40.8), ("de", 41.5), ("alvorada!", 41.7)],
    [("Não", 42.7), ("nasci", 43.2), ("pra", 43.9), ("caber,", 44.2)],
    [("nasci", 45.5), ("pra", 46.2), ("ser!", 46.4)],
    [("Aleluia,", 46.9)],
    [("meu", 48.5), ("maior", 48.9), ("poder", 49.5)],
    [("é", 50.2), ("ser", 50.7), ("quem", 51.8), ("sou", 52.8), ("em", 53.2), ("Ti.", 53.6)],
    [("Amém.", 55.5)],
]
LINE_END = [3.3, 4.8, 8.9, 11.4, 12.7, 17.4, 20.8, 22.7, 25.3, 28.1, 31.0, 33.7, 37.6, 40.7, 42.6, 45.4,
            46.8, 48.4, 50.1, 55.0, 57.0]
KEYS = {"faísca", "cresci,", "sopro", "Glória,", "luz", "cicatriz", "brilhar,", "graça", "alvorada!",
        "caber,", "ser!", "Aleluia,", "poder", "Ti.", "Amém."}
GLORIA = [18.5, 20.1, 38.2, 40.2]

# scenes in song seconds; the camera moves in 3D through each painting
SCENES = [
    ("s1", 0.0, 8.6, dict(z=(1.20, 1.03), pan=(0, 60), yaw=(-3, 2), pitch=(5, 0))),
    ("s2", 8.6, 18.2, dict(z=(1.03, 1.16), pan=(-10, 20), yaw=(3, -2), pitch=(0, 2))),
    ("s3", 18.2, 25.2, dict(z=(1.16, 1.04), pan=(30, -40), yaw=(-4, 3), pitch=(2, -2))),
    ("s5", 25.2, 31.0, dict(z=(1.04, 1.15), pan=(0, 30), yaw=(2, -2), pitch=(-2, 2))),
    ("s4", 31.0, 38.0, dict(z=(1.22, 1.04), pan=(0, -60), yaw=(3, -3), pitch=(-5, 1))),
    ("s6", 38.0, 46.8, dict(z=(1.04, 1.20), pan=(0, 70), yaw=(-3, 3), pitch=(-3, 3))),
    ("s7", 46.8, DUR, dict(z=(1.03, 1.18), pan=(0, 90), yaw=(-2, 2), pitch=(3, -2))),
]
XFADE = 0.8


class Feathers:
    """white feathers drifting down through depth, turning as they fall (near ones big and soft)"""
    def __init__(self, n=70, seed=4):
        r = np.random.default_rng(seed)
        self.x = r.uniform(-1.5, 1.5, n)
        self.y0 = r.uniform(-2.5, 2.5, n)
        self.z = r.uniform(0.35, 3.2, n)
        self.ph = r.uniform(0, 6.28, n)
        self.sp = r.uniform(0.6, 1.2, n)

    def draw(self, t, amount, gust=0.0):
        if amount <= 0.01:
            return None
        sw, sh = W // 2, H // 2
        near = np.zeros((sh, sw, 3), np.float32)
        far = np.zeros((sh, sw, 3), np.float32)
        f = 0.9 * sw
        for x, y0, z, ph, sp in zip(self.x, self.y0, self.z, self.ph, self.sp):
            y = (y0 + 0.16 * sp * t + 2.5) % 5.0 - 2.5
            xx = x + 0.18 * math.sin(t * 0.9 * sp + ph) + gust * 1.2 * (1 / z)
            px, py = sw / 2 + f * xx / z, sh / 2 + f * y / z
            if not (-60 < px < sw + 60 and -60 < py < sh + 60):
                continue
            s = 26 / z
            ang = math.degrees(math.sin(t * 1.6 * sp + ph) * 0.9) + 30
            flat = 0.25 + 0.2 * abs(math.sin(t * 1.3 + ph))         # it turns: thin when seen edge-on
            buf = near if z < 0.9 else far
            c = (np.array([250, 248, 245]) / 255 * amount * min(1.0, 0.45 + 0.6 / z)).tolist()
            cv2.ellipse(buf, (int(px), int(py)), (int(s), max(1, int(s * flat))), ang, 0, 360, c, -1, cv2.LINE_AA)
            cv2.line(buf, (int(px - s * math.cos(math.radians(ang))), int(py - s * math.sin(math.radians(ang)))),
                     (int(px + s * 1.25 * math.cos(math.radians(ang))), int(py + s * 1.25 * math.sin(math.radians(ang)))),
                     [v * 0.8 for v in c], 1, cv2.LINE_AA)
        out = cv2.GaussianBlur(near, (0, 0), 3.5) + cv2.GaussianBlur(far, (0, 0), 0.8)
        a = np.clip(out.max(2, keepdims=True) * 1.2, 0, 1)
        return cv2.resize(out, (W, H)), cv2.resize(a, (W, H))[..., None]


def magic_circle(t, at, cx, cy, size, sw, sh):
    """a glowing rune circle on the ground under her, seen in perspective (a flattened ellipse that turns)"""
    k = t - at
    if k < -0.2 or k > 3.0:
        return None
    grow = smooth((k + 0.2) / 0.5)
    fade = 1 - smooth((k - 1.8) / 1.2)
    buf = np.zeros((sh, sw), np.float32)
    rx, ry = size * grow, size * grow * 0.32
    for rr, w in ((1.0, 2), (0.86, 1), (0.62, 2), (0.45, 1)):
        cv2.ellipse(buf, (int(cx), int(cy)), (int(rx * rr), int(ry * rr)), 0, 0, 360, 1.0, w, cv2.LINE_AA)
    for j in range(12):                                         # rune ticks between the rings, turning
        a = j / 12 * 6.283 + t * 0.8
        p1 = (cx + math.cos(a) * rx * 0.88, cy + math.sin(a) * ry * 0.88)
        p2 = (cx + math.cos(a) * rx * 0.98, cy + math.sin(a) * ry * 0.98)
        cv2.line(buf, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), 1.0, 2, cv2.LINE_AA)
    for j in range(6):                                          # a hexagram inside
        a1, a2 = j / 6 * 6.283 - t * 0.5, (j + 2) / 6 * 6.283 - t * 0.5
        cv2.line(buf, (int(cx + math.cos(a1) * rx * 0.62), int(cy + math.sin(a1) * ry * 0.62)),
                 (int(cx + math.cos(a2) * rx * 0.62), int(cy + math.sin(a2) * ry * 0.62)), 1.0, 1, cv2.LINE_AA)
    pillar = np.exp(-((np.arange(sw) - cx) / (rx * 0.45 + 1)) ** 2)[None, :] * \
        np.clip((cy - np.arange(sh)[:, None]) / (sh * 0.5), 0, 1) ** 0.6 * (np.arange(sh)[:, None] < cy)
    out = cv2.GaussianBlur(buf, (0, 0), 1.0) + cv2.GaussianBlur(buf, (0, 0), 8) * 2
    return (out + pillar.astype(np.float32) * 0.35 * math.exp(-max(k, 0) / 0.8)) * fade


def scrim_k(t):
    """1 while a lyric line is on screen, easing in and out"""
    k = 0.0
    for words, end in zip(HYMN, LINE_END):
        k = max(k, smooth((t - words[0][1] + 0.4) / 0.4) * (1 - smooth((t - end - 0.3) / 0.5)))
    return k


_band = np.exp(-((np.arange(H, dtype=np.float32) - 1330) / 230) ** 2)
SCRIM = (0.55 * _band)[:, None, None]


def title_sprite():
    f = P.font(P.SERIF, 168, b"SemiBold")
    fs = P.font(P.ITALIC, 58, b"Medium Italic")
    im = Image.new("L", (W, 420), 0)
    d = ImageDraw.Draw(im)
    txt, tr = "GLÓRIA", 26
    tw = sum(d.textlength(c, font=f) + tr for c in txt) - tr
    x = (W - tw) / 2
    for c in txt:
        d.text((x, 20), c, font=f, fill=255)
        x += d.textlength(c, font=f) + tr
    sub = "um hino a Deus"
    d.text(((W - d.textlength(sub, font=fs)) / 2, 230), sub, font=fs, fill=230)
    a = np.array(im).astype(np.float32) / 255
    return a, cv2.GaussianBlur(a, (0, 0), 22)


def main(cenas, hino, out):
    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    paint = {s[0]: P.Painting(os.path.join(cenas, s[0] + ".png")) for s in SCENES}
    dust, feathers = P.Dust(n=360, seed=9), Feathers()
    caps = P.Captions(HYMN, LINE_END, KEYS, 0.0)
    rise = P.Embers(260, 11)
    title = title_sprite()
    hand = P.handle_sprite()
    sw, sh = W // 2, H // 2
    gy2, gx2 = np.mgrid[0:sh, 0:sw].astype(np.float32)
    gyf = (np.mgrid[0:H, 0:1][0].astype(np.float32) / H)[..., None]
    grain_r = np.random.default_rng(1)
    tmp = out + ".video.mp4"
    enc = None if preview else subprocess.Popen([
        "ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
        tmp], stdin=subprocess.PIPE)
    frames = [int(round(p * FPS)) for p in preview] if preview else range(int(DUR * FPS))
    for i in frames:
        t = i / FPS
        p_cresci = pulse(t, 11.9, 0.1, 0.5)
        p_glo = max(pulse(t, g, 0.1, 0.9) for g in GLORIA)
        p_br = pulse(t, 33.1, 0.15, 1.1)
        p_alv = pulse(t, 41.7, 0.2, 1.3)
        p_ser = pulse(t, 46.4, 0.1, 1.2)
        p_ale = pulse(t, 46.9, 0.2, 1.6)
        p_poder = pulse(t, 49.5, 0.1, 1.0)
        p_amen = pulse(t, 55.5, 0.3, 2.0)
        shake = (8 * p_cresci * math.sin(t * 91) + 6 * p_poder * math.sin(t * 83),
                 8 * p_cresci * math.cos(t * 77) + 6 * p_poder * math.cos(t * 71))
        img = None
        for k, (name, a, b, cam) in enumerate(SCENES):
            lo, hi = a - (XFADE / 2 if k else 0), b + (XFADE / 2 if k < len(SCENES) - 1 else 0)
            if not (lo <= t < hi):
                continue
            fr = P.scene_frame(paint[name], cam, (t - lo) / (hi - lo), t, shake).astype(np.float32) / 255
            w_in = smooth((t - lo) / XFADE) if k else 1.0
            w_out = 1 - smooth((t - (hi - XFADE)) / XFADE) if k < len(SCENES) - 1 else 1.0
            img = fr * min(w_in, w_out) if img is None else img + fr * min(w_in, w_out)
        punch = 0.05 * p_cresci + 0.035 * p_glo + 0.04 * p_poder
        if punch > 0.002:
            M = cv2.getRotationMatrix2D((W / 2, H * 0.45), 0, 1 + punch)
            img = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        L = np.zeros((sh, sw, 3), np.float32)

        def add(mask, col, k):
            L[:] += mask[..., None] * (np.array(col, np.float32) / 255) * k
        # the opening spark in her hand, the breath of 'sopro'
        add(radial(sw * 0.5, sh * 0.42, 60 + 120 * pulse(t, 3.9, 0.1, 0.8), gx2, gy2), GOLD, 0.9 * pulse(t, 3.9, 0.1, 0.8))
        add(radial(sw * 0.5, sh * 0.35, 200, gx2, gy2), [255, 240, 230], 0.5 * pulse(t, 14.1, 0.3, 1.2))
        # cathedral: god rays from the stained glass all through the prayer
        cat = smooth((t - 8.2) / 1.0) * (1 - smooth((t - 17.8) / 0.8))
        if cat > 0.01:
            add(rays(sw * 0.5, -sh * 0.1, t * 0.4, gx2, gy2, 9), [255, 235, 215], 0.35 * cat)
        # every 'Glória': a magic circle under her and a ring of light
        for g in GLORIA:
            mc = magic_circle(t, g, sw * 0.5, sh * 0.80, sw * 0.42, sw, sh)
            if mc is not None:
                add(mc, [255, 220, 150], 0.9)
        if p_glo > 0.01:
            add(radial(sw * 0.5, sh * 0.4, 180, gx2, gy2), GOLD, 0.4 * p_glo)
        add(radial(sw * 0.5, sh * 0.42, 140, gx2, gy2), GOLD, 0.6 * pulse(t, 26.0, 0.2, 1.0))   # cicatriz
        add(radial(sw * 0.5, sh * 0.6, 90, gx2, gy2), GOLD, 0.8 * pulse(t, 27.4, 0.2, 1.0))     # pendant glow
        if p_br > 0.01:
            add(rays(sw * 0.5, sh * 0.38, t, gx2, gy2), [255, 225, 220], 0.55 * p_br)
            ring = np.exp(-((np.sqrt((gx2 - sw / 2) ** 2 + (gy2 - sh * 0.38) ** 2) - (t - 33.1) * 520) / 14) ** 2)
            add(ring.astype(np.float32), [255, 225, 210], 0.6 * p_br)
        add(radial(sw * 0.5, sh * 0.4, 220, gx2, gy2), GOLD, 0.5 * pulse(t, 34.1, 0.2, 1.4))   # graça
        sun = p_alv + p_ser + p_poder + 0.4 * smooth((t - 38) / 2) * (1 - smooth((t - 46.4) / 1))
        if sun > 0.01:
            add(radial(sw * 0.62, sh * 0.15, 230, gx2, gy2), GOLD, 0.45 * sun)
            add(rays(sw * 0.62, sh * 0.15, t, gx2, gy2, 16), GOLD, 0.3 * sun)
        if p_ale > 0.01:
            add(radial(sw * 0.5, sh * 0.25, 300, gx2, gy2), [255, 245, 230], 0.45 * p_ale)
        if t > 54.0:
            add(radial(sw * 0.5, sh * 0.3, 320, gx2, gy2), GOLD, 0.25 * smooth((t - 54) / 2) + 0.5 * p_amen)
        rise.draw(L, t, 46.4, sw * 0.5, sh * 0.6, 280, 1.3)
        rise.draw(L, t, 55.5, sw * 0.5, sh * 0.55, 360, 1.2)
        L = cv2.GaussianBlur(L, (0, 0), 1.5)
        img = 1 - (1 - np.clip(img, 0, 1)) * (1 - np.clip(cv2.resize(L, (W, H)), 0, 1))   # screen
        # depth layers: gold dust, then feathers that pass in front of everything
        D = dust.draw(t, 0.16 + 0.5 * (p_glo + p_alv + p_ser), 0.45 + 0.35 * smooth((t - 18) / 3) + 0.4 * p_ale,
                      max(p_ser, p_poder) * 0.6)
        if D is not None:
            img = 1 - (1 - img) * (1 - np.clip(D, 0, 1))
        gust = p_alv * 0.8 + p_ser * 0.6 + p_glo * 0.3
        fa = 0.5 + 0.5 * smooth((t - 18) / 2) + 0.4 * (p_alv + p_ser)
        Fr = feathers.draw(t, fa, gust)
        if Fr is not None:
            fb, fal = Fr
            img = img * (1 - fal * 0.85) + fb * 0.95
        img = P.grade(img, gyf)
        img *= smooth(t / 0.8)
        for name, a, b, cam in SCENES[1:]:
            img += 0.18 * math.exp(-((t - a) / 0.12) ** 2)
        img *= 1 - SCRIM * scrim_k(t)                       # a soft dark band keeps the lyrics readable
        caps.draw(img, t)
        # end card: GLÓRIA rises out of the light on 'Amém', the handle settles under it
        tt = t - 55.6
        if tt > 0:
            ta, tg = title
            k = smooth(tt / 0.9)
            y0 = 360 - int(30 * (1 - k))
            roi = img[y0:y0 + ta.shape[0]]
            roi *= 1 - np.clip(cv2.GaussianBlur(ta, (0, 0), 20) * 2.2, 0, 0.8)[..., None] * k
            roi += tg[..., None] * GOLD / 255 * 0.9 * k
            roi[:] = roi * (1 - ta[..., None] * k) + (GOLD + 40) / 255 * ta[..., None] * k
        ha, hs, hg = hand
        hk = smooth((t - 0.6) / 0.8) * (0.82 + 0.18 * math.sin(t * 1.1))
        hx, hy = 70 + int(10 * math.sin(t * 0.5)), 150 + int(8 * math.sin(t * 0.8))
        if tt > 0.4:
            m = smooth((tt - 0.4) / 1.0)
            hx = int(hx + ((W - ha.shape[1]) / 2 - hx) * m)
            hy = int(hy + (720 - hy) * m)
            hk = max(hk, m)
        roi = img[hy:hy + ha.shape[0], hx:hx + ha.shape[1]]
        roi *= 1 - hs[..., None] * 0.7 * hk
        roi += hg[..., None] * GOLD / 255 * 0.35 * hk
        roi[:] = roi * (1 - ha[..., None] * hk) + CREAM / 255 * ha[..., None] * hk
        img *= 1 - smooth((t - (DUR - 0.6)) / 0.6)
        img += grain_r.normal(0, 0.014, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1)
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
    subprocess.run([
        "ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-i", hino, "-filter_complex",
        f"[1:a]atrim=0:{DUR},afade=t=out:st={DUR - 1.2}:d=1.2,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-movflags", "+faststart", "-t", str(DUR), out], check=True)
    os.remove(tmp)


if __name__ == "__main__":
    main(*sys.argv[1:4])

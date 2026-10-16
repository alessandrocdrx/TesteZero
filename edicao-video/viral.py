"""TikTok viral cut (~40 s). Picks segments of the original at her breaths; image and voice untouched.
Usage: viral.py SRC OUT_SILENT_MP4   (PREVIEW="1,14,23" for review frames)"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mv  # noqa: E402
from mv import W, H, FPS, WHITE, BLACK, PINK, YELLOW, GOLD, ease_out, ease_in_out, paste, pop, fade  # noqa: E402

MONT = mv.FD + "Montserrat.ttf"

# source segments cut at breaths (seconds in the original)
SEGMENTS = [(1.7, 15.2), (47.6, 55.5), (63.8, 81.9)]
JOINS, _acc = [], 0.0
for a, b in SEGMENTS:
    JOINS.append(_acc)
    _acc += b - a
DUR = _acc  # ~39.5 s


def src_time(t):
    for (a, b), j in zip(SEGMENTS, JOINS):
        if t < j + (b - a):
            return a + (t - j)
    return SEGMENTS[-1][1]


def out_time(s):
    for (a, b), j in zip(SEGMENTS, JOINS):
        if a <= s <= b:
            return j + (s - a)
    raise ValueError(s)


CLIMAX = out_time(65.0)          # where the big voice opens up
REPRISE = out_time(78.5)
CUTS = JOINS[1:]

# CapCut-style captions: (src start, src end, text)
CAPTIONS = [(2.0, 7.6, "Voa nas asas do vento"),
            (7.8, 15.0, "até a terra natal, nossa canção querida"),
            (48.2, 55.4, "nos vales florescem as rosas"),
            (78.5, 81.9, "voa nas asas do vento…")]

# TikTok "classic" text boxes: (out start, out end, lines, y)
BOXES = [(0.0, 3.6, ["ela pegou uma ópera russa de 1890…"], 300),
         (0.9, 3.6, ["…e cantou sem NENHUM instrumento"], 410),
         (3.6, CLIMAX - 0.6, [f"espera o 0:{int(CLIMAX):02d}"], 300),
         (JOINS[1] + 0.6, JOINS[1] + 4.6, ["ela SORRINDO enquanto canta isso"], 300),
         (CLIMAX + 6.0, CLIMAX + 10.0, ["sem autotune. sem playback."], 300),
         (REPRISE, DUR, ["salva pra ouvir de novo"], 300)]

POPS = [(CLIMAX - 0.2, CLIMAX + 1.6, "AQUI.", 160, YELLOW),
        (CLIMAX + 2.6, CLIMAX + 5.4, "ARREPIOU?", 120, PINK)]

SPLIT = (JOINS[1] + 5.0, JOINS[1] + 7.2)

# fast TikTok shot changes (out time, zoom, x offset); the first and last shot match for a clean loop
SHOTS = [(0.0, 1.12, 0), (2.1, 1.30, -20), (4.0, 1.00, 0), (6.1, 1.22, 25), (8.2, 1.36, 0), (10.2, 1.05, 0),
         (12.0, 1.28, -25), (JOINS[1], 1.20, 0), (JOINS[1] + 2.4, 1.00, 0), (JOINS[1] + 7.2, 1.32, 0),
         (JOINS[2], 1.00, 0), (REPRISE, 1.12, 0)]


def Fm(size, weight=b"Black"):
    f = ImageFont.truetype(MONT, size)
    f.set_variation_by_name(weight)
    return f


def tiktok_box(text, size=56):
    f = Fm(size, b"Bold")
    d0 = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    x0, y0, x1, y1 = d0.textbbox((0, 0), text, font=f)
    px, py = 26, 16
    img = Image.new("RGBA", (x1 - x0 + 2 * px, y1 - y0 + 2 * py), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, img.width - 1, img.height - 1], 18, fill=(255, 255, 255, 245))
    d.text((px - x0, py - y0), text, font=f, fill=(0, 0, 0, 255))
    return np.array(img)


def word_img(word, size, fill, stroke=9):
    f = Fm(size)
    d0 = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    x0, y0, x1, y1 = d0.textbbox((0, 0), word, font=f, stroke_width=stroke)
    img = Image.new("RGBA", (x1 - x0 + 24, y1 - y0 + 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((12 - x0 + 5, 12 - y0 + 7), word, font=f, fill=(0, 0, 0, 160), stroke_width=stroke, stroke_fill=(0, 0, 0, 160))
    d.text((12 - x0, 12 - y0), word, font=f, fill=fill + (255,), stroke_width=stroke, stroke_fill=BLACK + (255,))
    return np.array(img)


def build_caption_chunks():
    """Split each lyric into chunks of <=3 words, each word with its own time."""
    chunks = []
    for a, b, text in CAPTIONS:
        oa, ob = out_time(a), out_time(min(b, SEGMENTS[[i for i, s in enumerate(SEGMENTS) if s[0] <= a <= s[1]][0]][1]))
        words = text.upper().split()
        span = (ob - oa) * 0.82
        times = [oa + span * i / len(words) for i in range(len(words))]
        for c in range(0, len(words), 3):
            ws = words[c:c + 3]
            ts = times[c:c + 3]
            end = times[c + 3] if c + 3 < len(words) else ob
            chunks.append((ts, end, ws))
    return chunks


def draw_caption(img, t, chunks, cache, y=1300):
    for ts, end, ws in chunks:
        if not (ts[0] <= t < end):
            continue
        active = max(i for i, s in enumerate(ts) if s <= t)
        sprites = []
        for i, w in enumerate(ws):
            key = (w, i == active)
            if key not in cache:
                cache[key] = word_img(w, 92, YELLOW if i == active else WHITE)
            sprites.append(cache[key])
        gap = 18
        total = sum(s.shape[1] for s in sprites) + gap * (len(sprites) - 1)
        if total > W - 120:  # too wide: shrink the whole chunk
            k = (W - 120) / total
            sprites = [cv2.resize(s, None, fx=k, fy=k) for s in sprites]
            total = W - 120
        x = (W - total) / 2 - 30  # nudge left of TikTok's right rail
        for i, s in enumerate(sprites):
            sc = 1.0
            if i == active:
                sc = 1.12 - 0.12 * ease_out((t - ts[i]) / 0.15)
            paste(img, s, x + s.shape[1] / 2, y, scale=sc)
            x += s.shape[1] + gap


def shot_at(t):
    cur = SHOTS[0]
    for s in SHOTS:
        if t >= s[0]:
            cur = s
    return cur


def camera(src, t):
    st, z, ox = shot_at(t)
    z += 0.015 * (t - st)
    if JOINS[2] <= t < REPRISE:  # build-up: one long push-in through the climax
        z = 1.0 + 0.32 * ease_in_out((t - JOINS[2]) / (REPRISE - JOINS[2]))
        if t >= CLIMAX:  # subtle pulse on the open voice
            z += 0.01 * math.sin((t - CLIMAX) * 6)
    for c in CUTS + [CLIMAX]:
        if c <= t < c + 0.4:
            z += 0.2 * (1 - ease_out((t - c) / 0.4))
    return mv.frame_zoom(src, max(1.0, z), ox, 0)


def flash(img, t):
    for c in CUTS + [CLIMAX]:
        d = t - c
        if -0.02 <= d < 0.12:
            k = 1 - (d + 0.02) / 0.14
            s = int(16 * k)
            b, g, r = cv2.split(img)
            img = cv2.merge([np.roll(b, -s, 1), g, np.roll(r, s, 1)])
            img = (img.astype(np.float32) * (1 - 0.75 * k) + 255 * 0.75 * k).astype(np.uint8)
    return img


def main(src_path, out_path):
    cap = cv2.VideoCapture(src_path)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    n = len(frames)

    chunks = build_caption_chunks()
    cache = {}
    boxes = [[tiktok_box(l) for l in lines] for _, _, lines, _ in BOXES]
    pops = [mv.text_sprite(p[2], mv.ANTON, p[3], p[4], stroke=8, stroke_fill=WHITE, shadow=12) for p in POPS]
    credit = tiktok_box("voz: @kvashenayakto", 32)
    sparkles = mv.Sparkles(n=80, seed=11)
    mv.SPLIT3 = SPLIT

    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    want = {int(round(x * FPS)) for x in preview}
    enc = None if preview else subprocess.Popen([
        "ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", out_path], stdin=subprocess.PIPE)

    for i in range(int(round(DUR * FPS))):
        if preview and i not in want:
            continue
        t = i / FPS
        s = src_time(t)
        src = cv2.resize(frames[min(int(round(s * FPS)), n - 1)], (W, H), interpolation=cv2.INTER_LANCZOS4)

        img = mv.split3(src, t) if SPLIT[0] <= t < SPLIT[1] else camera(src, t)

        light = np.zeros((H, W, 3), np.float32)
        if JOINS[1] <= t < JOINS[2]:
            light += mv.light_leak(t, 0.5, (255, 90, 170), "r") + mv.light_leak(t + 4, 0.4, mv.CYAN, "l")
        if t >= JOINS[2]:
            amt = min(1.0, max(0.0, (t - CLIMAX + 0.5) / 1.0))
            light += sparkles.draw(t, amt) + mv.light_leak(t, 0.55 * amt, GOLD, "l" if int(t) % 2 else "r")
        if light.any():
            img = mv.screen(img, np.clip(light, 0, 255))
        img = flash(img, t)
        img[mv.BAND_Y0:] = (img[mv.BAND_Y0:].astype(np.float32) * mv.BAND).astype(np.uint8)

        for (a, b, _, y), sprs in zip(BOXES, boxes):
            if a <= t < b:
                for j, spr in enumerate(sprs):
                    paste(img, spr, W / 2 - 30, y + j * 125, scale=pop(t, a, b, ins=0.16, outs=0.1))

        for p, spr in zip(POPS, pops):
            if p[0] <= t < p[1]:
                paste(img, spr, W / 2 - 30, 1120, pop(t, p[0], p[1]) * (1 + 0.03 * math.sin(t * 16)))

        draw_caption(img, t, chunks, cache, y=1330 if not (SPLIT[0] <= t < SPLIT[1]) else 1380)
        if t >= REPRISE:
            paste(img, credit, 60, 1470, anchor="l", alpha=fade(t, REPRISE, DUR + 1))

        if preview:
            cv2.imwrite(f"{out_path}_{t:05.1f}.png", cv2.resize(img, (270, 480)))
            continue
        enc.stdin.write(img.tobytes())
    if enc:
        enc.stdin.close()
        enc.wait()


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "--segments":
        print(" ".join(f"{a}:{b}" for a, b in SEGMENTS))
    else:
        main(sys.argv[1], sys.argv[2])

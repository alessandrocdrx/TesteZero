"""'Voa nas asas do vento': the single take, intact. Cinematic typography, one turn at the climax.
Her image is never filtered; the voice is copied untouched. Usage: calmo.py SRC OUT_SILENT_MP4
PREVIEW="1,20,70" renders review frames instead of the video."""
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FD = os.environ.get("FONTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"))
SERIF = os.path.join(FD, "CormorantGaramond.ttf")
ITALIC = os.path.join(FD, "CormorantGaramond-Italic.ttf")

W, H, FPS = 1080, 1920, 30
AUDIO_END = 85.4
DUR = 87.0  # 1.6 s of silent black card after her last note

# poetic PT-BR translation, timed to her singing (onsets measured on the waveform)
LYRICS = [
    (1.1, 7.6, "Voa nas asas do vento", "Улетай на крыльях ветра"),
    (7.8, 15.0, "à terra natal, nossa canção querida,", "ты в край родной, родная песня наша,"),
    (15.9, 23.8, "para onde te cantávamos livres,", "туда, где мы тебя свободно пели,"),
    (24.0, 31.4, "onde éramos tão felizes contigo.", "где было так привольно нам с тобою."),
    (31.6, 39.5, "Lá, o sol brilha tão forte,", "Там так ярко солнце светит,"),
    (39.7, 46.7, "banhando de luz as nossas montanhas;", "родные горы светом заливая,"),
    (46.9, 55.4, "nos vales, as rosas se abrem,", "в долинах пышно розы расцветают,"),
    (55.6, 63.5, "e os rouxinóis cantam nas matas verdes.", "и соловьи поют в лесах зелёных."),
    (78.5, 82.1, "Voa nas asas do vento…", "Улетай на крыльях ветра…"),
    (82.4, 84.4, "à terra natal…", "ты в край родной…"),
]
CONTEXT = (0.3, 7.4)
TURN = (63.8, 78.0)   # her voice alone: no text, edges fall into shadow, slow approach
FADE_OUT = (84.2, 85.4)
CARD = 84.6


def font(path, size, weight):
    f = ImageFont.truetype(path, size)
    f.set_variation_by_name(weight)
    return f


def tracked(draw, xy, text, f, fill, tracking):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=f, fill=fill)
        x += draw.textlength(ch, font=f) + tracking


def tracked_width(draw, text, f, tracking):
    return sum(draw.textlength(ch, font=f) + tracking for ch in text) - tracking


def text_block(lines, width=W, shadow=True):
    """lines: list of (text, font, rgba, tracking, gap_after). Centered, soft shadow. Returns RGBA numpy."""
    d0 = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    heights = [(f.getbbox("ÁÇgjУ")[3] + gap) for _, f, _, _, gap in lines]
    h = sum(heights) + 60
    layer = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y = 30
    for (text, f, rgba, tr, _), lh in zip(lines, heights):
        tw = tracked_width(d0, text, f, tr) if tr else d0.textlength(text, font=f)
        x = (width - tw) / 2
        if tr:
            tracked(d, (x, y), text, f, rgba, tr)
        else:
            d.text((x, y), text, font=f, fill=rgba)
        y += lh
    if shadow:
        a = layer.split()[3]
        sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        sh.putalpha(a.point(lambda v: v * 0.75).filter(ImageFilter.GaussianBlur(9)))
        layer = Image.alpha_composite(sh, layer)
    return np.array(layer)


def paste(frame, spr, cy, alpha):
    if alpha <= 0.003:
        return
    h, w = spr.shape[:2]
    y = int(cy - h / 2)
    y0, y1 = max(y, 0), min(y + h, H)
    s = spr[y0 - y:y1 - y].astype(np.float32)
    a = s[..., 3:4] / 255 * alpha
    roi = frame[y0:y1, :w].astype(np.float32)
    frame[y0:y1, :w] = (roi * (1 - a) + s[..., 2::-1] * a).astype(np.uint8)


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def fade(t, a, b, fin=0.45, fout=0.45):
    if t < a or t >= b:
        return 0.0
    return smooth(min((t - a) / fin, (b - t) / fout, 1.0))


# masks that only touch the edges and the caption area, never her face
_x = np.linspace(-1, 1, W)[None, :]
_y = np.linspace(0, 1, H)[:, None]
_r = np.sqrt((_x * 0.95) ** 2 + ((_y - 0.33) * 1.25) ** 2)
VIGNETTE = np.clip((_r - 0.55) / 0.6, 0, 1) ** 1.6                     # 0 on the face, 1 at the corners
BOTTOM = np.clip((_y - 0.62) / 0.38, 0, 1) ** 1.3 * np.ones_like(_x)   # caption legibility
TOP = np.clip((0.2 - _y) / 0.2, 0, 1) ** 1.3 * np.ones_like(_x)
CAPTION_Y = 1390
# soft dark pool behind the captions (sweater/mic area, below her face)
POOL = np.exp(-((_x / 0.95) ** 2 + ((_y - CAPTION_Y / H) / 0.065) ** 2) * 1.6)


def main(src_path, out_path):
    cap = cv2.VideoCapture(src_path)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    n = len(frames)

    lyr_f = font(ITALIC, 70, b"SemiBold Italic")
    ru_f = font(SERIF, 30, b"SemiBold")
    lyr = [text_block([(ru.upper(), ru_f, (255, 255, 255, 175), 3, 22), (pt, lyr_f, (255, 255, 255, 255), 0, 0)])
           for _, _, pt, ru in LYRICS]
    ctx = text_block([
        ("BORODIN  ·  PRÍNCIPE IGOR  ·  1890", font(SERIF, 28, b"SemiBold"), (255, 255, 255, 200), 5, 30),
        ("Mulheres presas longe de casa", font(ITALIC, 54, b"Medium Italic"), (255, 255, 255, 255), 0, 6),
        ("pedem ao vento que leve sua canção.", font(ITALIC, 54, b"Medium Italic"), (255, 255, 255, 255), 0, 0),
    ])
    card = text_block([
        ("Voa nas asas do vento", font(ITALIC, 92, b"Medium Italic"), (255, 255, 255, 255), 0, 18),
        ("УЛЕТАЙ НА КРЫЛЬЯХ ВЕТРА", font(SERIF, 30, b"Medium"), (255, 255, 255, 170), 5, 70),
        ("ALEXANDER BORODIN  ·  PRÍNCIPE IGOR, 1890", font(SERIF, 28, b"SemiBold"), (255, 255, 255, 200), 4, 26),
        ("voz  ·  @kvashenayakto", font(ITALIC, 44, b"Medium Italic"), (255, 255, 255, 255), 0, 10),
        ("edição  ·  @alessandrocdrx", font(ITALIC, 44, b"Medium Italic"), (255, 255, 255, 220), 0, 0),
    ], shadow=False)

    preview = [float(x) for x in os.environ.get("PREVIEW", "").split(",") if x]
    want = {int(round(x * FPS)) for x in preview}
    enc = None if preview else subprocess.Popen([
        "ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-tune", "film",
        "-pix_fmt", "yuv420p", out_path], stdin=subprocess.PIPE)

    for i in range(int(DUR * FPS)):
        if preview and i not in want:
            continue
        t = i / FPS
        img = cv2.resize(frames[min(i, n - 1)], (W, H), interpolation=cv2.INTER_LANCZOS4)

        # the turn: a slow approach (max 7%) while the edges fall into shadow; released on her breath at 78.0
        k = 0.0
        if TURN[0] <= t < TURN[1]:
            k = smooth((t - TURN[0]) / 2.0)
            z = 1.0 + 0.07 * smooth((t - TURN[0]) / (TURN[1] - TURN[0]))
            cx, cy = W / 2, H * 0.33
            M = np.float32([[z, 0, (1 - z) * cx], [0, z, (1 - z) * cy]])
            img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)

        cap = max((fade(t, a, b, fin=0.35, fout=0.4) for a, b, _, _ in LYRICS), default=0.0)
        shade = 0.55 * POOL * cap + 0.3 * BOTTOM + 0.35 * TOP * fade(t, CONTEXT[0] - 0.3, CONTEXT[1] + 0.3) + 0.8 * VIGNETTE * k
        img = (img.astype(np.float32) * (1 - np.clip(shade, 0, 0.85))[..., None]).astype(np.uint8)

        if t >= FADE_OUT[0]:
            img = (img.astype(np.float32) * (1 - smooth((t - FADE_OUT[0]) / (FADE_OUT[1] - FADE_OUT[0])))).astype(np.uint8)

        paste(img, ctx, 300, fade(t, *CONTEXT, fin=0.8, fout=0.7))
        for (a, b, _, _), spr in zip(LYRICS, lyr):
            paste(img, spr, CAPTION_Y, fade(t, a, b, fin=0.35, fout=0.4))
        if t >= CARD:
            paste(img, card, 900, smooth((t - CARD) / 0.9))

        if preview:
            cv2.imwrite(f"{out_path}_{t:05.1f}.png", cv2.resize(img, (360, 640), interpolation=cv2.INTER_AREA))
            continue
        enc.stdin.write(img.tobytes())
    if enc:
        enc.stdin.close()
        enc.wait()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

"""Mistura de sprite RGBA (float 0..1) numa imagem RGB float, centralizada em (x, y)."""
import numpy as np


def blend(img, sp, x, y):
    H, W = img.shape[:2]
    h, w = sp.shape[:2]
    x0, y0 = int(round(x - w / 2)), int(round(y - h / 2))
    a0, b0 = max(0, -x0), max(0, -y0)
    a1, b1 = min(w, W - x0), min(h, H - y0)
    if a1 <= a0 or b1 <= b0:
        return
    reg = img[y0 + b0:y0 + b1, x0 + a0:x0 + a1]
    s = sp[b0:b1, a0:a1]
    al = s[..., 3:4]
    img[y0 + b0:y0 + b1, x0 + a0:x0 + a1] = reg * (1 - al) + s[..., :3] * al

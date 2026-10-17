"""Cut her out once, frame by frame, and keep it: mundo.py then reads the cut-out instead of recomputing it.
Usage: recorte.py SRC SEG_MODEL OUT_DIR"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mundo import Matte, FPS  # noqa: E402


def main(src, model, out):
    os.makedirs(out, exist_ok=True)
    matte = Matte(model)
    cap = cv2.VideoCapture(src)
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        a = matte(f, int(i * 1000 / FPS))
        cv2.imwrite(os.path.join(out, f"{i:05d}.png"), np.round(a * 255).astype(np.uint8))
        i += 1
    print("frames", i)


if __name__ == "__main__":
    main(*sys.argv[1:4])

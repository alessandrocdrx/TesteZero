"""Test 2a, her cut-out is never eaten: the chair cleanup removes nothing on her face, and almost nothing of her
solid body (well inside the segmenter's confident area). Thin strands over the chair may thin: that is the chair
seen through them being replaced. Usage: qa_ela.py SRC RECORTE QUARTO.npz ANALISE.npz"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mundo as M  # noqa: E402

LIMIT_FACE = 0.5   # pixel-equivalents removed on her face (none)
LIMIT_BODY = 150   # pixel-equivalents removed away from the chair / flowers / dream catcher


def main(src, rec, room_path, npz, step=3):
    room = M.load_room(room_path)
    boxes = np.load(npz)["boxes"]
    cap = cv2.VideoCapture(src)
    loss, i = [], 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i % step == 0:
            a = cv2.imread(os.path.join(rec, f"{i:05d}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
            guard = M.face_guard(boxes, i)
            removed = a - M.clean_alpha(f, a, room, guard)
            body = ~(room["never"] > 0.02)          # everywhere away from the room's objects: nothing may be removed
            loss.append((i / M.FPS, float((removed * (guard > 0.95)).sum()), float(removed[body].sum())))
        i += 1
    bad = [x for x in loss if x[1] > LIMIT_FACE or x[2] > LIMIT_BODY]
    wf = max(x[1] for x in loss)
    wb = sorted(loss, key=lambda x: -x[2])[:5]
    print(f"TESTE 2a recorte dela preservado: {'PASSOU' if not bad else 'FALHOU'}  (rosto: pior {wf:.1f} px, "
          f"limite {LIMIT_FACE}; fora dos objetos: pior {wb[0][2]:.0f} px, limite {LIMIT_BODY}; {len(bad)} quadros acima)")
    print("   piores fora dos objetos:", [(round(t, 1), round(v)) for t, _, v in wb])
    return not bad


if __name__ == "__main__":
    main(*sys.argv[1:5], step=int(os.environ.get("STEP", 3)))

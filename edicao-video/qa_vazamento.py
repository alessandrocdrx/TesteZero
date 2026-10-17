"""Test 1, room leak: how much of the chair / flowers / dream catcher can be seen, frame by frame.
Needs no render: the cut-out cache and the empty room are enough. Usage: qa_vazamento.py SRC RECORTE QUARTO.npz OUT"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mundo as M  # noqa: E402


LIMIT_PX = 150   # source pixels with a perceivable (>15%) room object; ~0.02% of the frame


def main(src, rec, room_path, out, step=1):
    room = M.load_room(room_path)
    boxes = np.load(os.path.join(os.path.dirname(os.path.abspath(room_path)), "analise.npz"))["boxes"]
    halo = cv2.resize(M.noise_field(99, scale=11), (720, 1280), interpolation=cv2.INTER_AREA)
    cap = cv2.VideoCapture(src)
    rows, heat, i = [], np.zeros((1280, 720), np.float32), 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        t = i / M.FPS
        intended = t < M.SCENES[1][1] + 1.0 or t >= M.SCENES[-1][1]   # the real room is meant to show here
        if i % step == 0 and not intended:
            a = cv2.imread(os.path.join(rec, f"{i:05d}.png"), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255
            a = M.clean_alpha(f, a, room, M.face_guard(boxes, i))
            keep = M.room_keep(a, halo, room)
            peak, px = M.room_leak(f, a, keep, room)
            vis = M.leak_map(f, a, keep, room)
            heat = np.maximum(heat, vis)
            rows.append(dict(frame=i, t=round(i / M.FPS, 2), peak=peak, px=px))
        i += 1
    json.dump(rows, open(out + ".json", "w"))
    worst = sorted(rows, key=lambda r: -r["px"])[:5]
    hv = cv2.applyColorMap((np.clip(heat, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
    cv2.imwrite(out + "_mapa.jpg", cv2.addWeighted(room["plate"].astype(np.uint8), 0.5, hv, 0.5, 0))
    bad = [r for r in rows if r["px"] > LIMIT_PX]
    print(f"TESTE 1 vazamento do quarto: {'PASSOU' if not bad else 'FALHOU'}  "
          f"(limite {LIMIT_PX} px perceptíveis por quadro; pior {max(r['px'] for r in rows):.0f} px, "
          f"média {np.mean([r['px'] for r in rows]):.0f}; {len(bad)} quadros acima)")
    print("   piores:", [(r["t"], round(r["px"])) for r in worst])
    return not bad


if __name__ == "__main__":
    main(*sys.argv[1:5], step=int(os.environ.get("STEP", 1)))

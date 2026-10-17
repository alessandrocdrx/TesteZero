"""The empty room: the camera never moves, so each wall pixel is the median of the frames where she is not
covering it. From that plate, the room's objects (chair, flowers, dark corners) are found by colour, without
ever touching her. Usage: quarto.py SRC RECORTE_DIR OUT.npz"""
import os
import sys

import cv2
import numpy as np


def main(src, rec, out, step=8):
    cap = cv2.VideoCapture(src)
    stack, masks, i = [], [], 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        if i % step == 0:
            a = cv2.imread(os.path.join(rec, f"{i:05d}.png"), cv2.IMREAD_GRAYSCALE)
            free = cv2.erode((a < 8).astype(np.uint8), np.ones((15, 15), np.uint8))  # clear of hair, too
            stack.append(f)
            masks.append(free.astype(bool))
        i += 1
    S, M = np.stack(stack), np.stack(masks)          # uint8 frames, kept small
    plate = np.zeros(S.shape[1:], np.float32)
    for y in range(0, S.shape[1], 64):                # median strip by strip, to stay in memory
        s_ = S[:, y:y + 64].astype(np.float32)
        s_[~M[:, y:y + 64]] = np.nan
        with np.errstate(all="ignore"):
            import warnings
            warnings.simplefilter("ignore")
            plate[y:y + 64] = np.nanmedian(s_, axis=0)
    seen = M.mean(0)
    known = ~np.isnan(plate[..., 0])
    plate = np.nan_to_num(plate).astype(np.uint8)
    hsv = cv2.cvtColor(plate, cv2.COLOR_BGR2HSV)
    v, sat = hsv[..., 2].astype(np.int32), hsv[..., 1].astype(np.int32)
    b_, r_ = plate[..., 0].astype(np.int32), plate[..., 2].astype(np.int32)
    wall_v = cv2.medianBlur(hsv[..., 2], 61).astype(np.int32)
    # the wall is a warm, pale grey; objects are the navy chair (blue over red), the black corner,
    # the saturated flowers and the bright dream catcher
    # only where the wall was seen in enough frames (near her head the median would mix in hair), and only by
    # colours her hair and skin never have: near-black with blue over red (chair: b-r ~ +4, wall ~ -15, hair ~ -50), neutral black, saturated orange flowers
    solid = seen > 0.25
    obj = known & solid & (((b_ - r_ > -3) & (v < 70)) | ((v < 45) & (np.abs(b_ - r_) < 8))
                           | ((sat > 140) & (v > 120)) | ((v - wall_v > 35) & (sat < 40)))
    obj = cv2.morphologyEx(obj.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    obj = cv2.morphologyEx(obj, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))
    # objects continue a little under where she always is
    obj = np.maximum(obj, cv2.dilate(obj, np.ones((41, 41), np.uint8)) * (~known))
    # the chair's whole shape, including the part always hidden behind her: convex hull of its navy pixels
    navy = (known & (seen > 0.02) & (b_ - r_ > -3) & (v < 70)).astype(np.uint8)
    navy = cv2.morphologyEx(navy, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(navy)
    hull = np.zeros_like(navy)
    if n > 1:
        big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        pts = np.column_stack(np.nonzero(lab == big)[::-1]).astype(np.int32)
        cv2.fillConvexPoly(hull, cv2.convexHull(pts), 1)
    never = np.maximum(obj, hull)
    np.savez_compressed(out, plate=plate, known=known, seen=seen, objects=obj, never=never, chair=hull)
    vis = plate.copy()
    vis[obj > 0] = (vis[obj > 0] * 0.4 + np.array([255, 0, 255]) * 0.6).astype(np.uint8)
    vis[~known] = (0, 255, 0)
    cnt, _ = cv2.findContours(hull, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(vis, cnt, -1, (0, 255, 255), 3)
    cv2.imwrite(os.path.splitext(out)[0] + ".jpg", np.hstack([plate, vis]))
    print("known", round(known.mean() * 100, 1), "% of the room; objects", round(obj.mean() * 100, 1), "%")


if __name__ == "__main__":
    main(*sys.argv[1:4])

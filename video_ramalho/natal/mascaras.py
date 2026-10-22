"""Recorte das duas personagens (Marcos + Papai Noel) em cada clipe 9:16, para dar profundidade aos objetos 3D.

Saída: cache/natal_v2/mascaras_cNN.npz  alpha uint8 (quadros, 960, 540), rembg isnet, só os blocos grandes.
Uso: python3 natal/mascaras.py
"""
import os, subprocess, sys, time
import numpy as np
import cv2

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(RAIZ, "cache", "natal_v2")
W, H = 540, 960


def frames(path):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{H}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)


def limpar(m):
    """Mantém os blocos grandes (as duas personagens) e descarta lixo (brilhos, enfeites soltos)."""
    bin_ = (m > 128).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(bin_, 8)
    if n <= 1:
        return np.zeros_like(m)
    areas = stats[1:, cv2.CC_STAT_AREA]
    ok = [i + 1 for i, a in enumerate(areas) if a >= 0.20 * areas.max()]
    out = np.isin(lab, ok).astype(np.uint8) * 255
    out = cv2.dilate(out, np.ones((3, 3), np.uint8))
    return cv2.GaussianBlur(out, (0, 0), 1.2)


def main():
    from rembg import new_session, remove
    sess = new_session("isnet-general-use")
    for i in range(1, 7):
        saida = os.path.join(PASTA, f"mascaras_c{i:02d}.npz")
        if os.path.exists(saida):
            print("cache", i); continue
        t0 = time.time(); ms = []
        for img in frames(os.path.join(PASTA, f"c{i:02d}.mp4")):
            a = np.asarray(remove(img, session=sess, only_mask=True))
            ms.append(limpar(a))
        np.savez_compressed(saida, a=np.array(ms, np.uint8))
        print(f"clipe {i}: {len(ms)} quadros em {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()

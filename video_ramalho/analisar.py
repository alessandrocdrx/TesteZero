"""Análise local de cada cena (feita uma vez, cacheada): recorte do personagem, rosto e placa do fundo.

Para cada cache/clipes/cenaNN.mp4, em 540x960 (os efeitos dependem só disto):
  cache/recorte/cenaNN/00000.png …  máscara do personagem (rembg isnet), borda suavizada
  cache/placa/cenaNN/00000.jpg …    fundo sem o personagem (inpaint), usado na paralaxe
  cache/analise_cenaNN.npz          caixa do rosto por quadro, centro e caixa do corpo
E da narração travada: cache/analise_voz.npz (energia RMS a cada 1/30 s).

Uso: python3 analisar.py cena05 [cena01 …]
"""
import os, subprocess, sys
import numpy as np
import cv2
from PIL import Image
from cache import Cache, sha256, DIR

W, H = 540, 960
c = Cache()
_sess = None


def frames(path):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={W}:{H}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)


def rosto(img, m):
    """Caixa da cabeça (x0,y0,x1,y1) pela máscara: do topo até o pescoço (linha mais estreita abaixo da cabeça)."""
    on = m > 128
    rows = np.nonzero(on.any(1))[0]
    if not len(rows):
        return np.array([0, 0, 0, 0], np.float32)
    y0, y1 = rows.min(), rows.max()
    span = y1 - y0
    wid = np.convolve(on[y0:y1 + 1].sum(1).astype(np.float32), np.ones(9) / 9, "same")
    a, b = int(0.12 * span), max(int(0.55 * span), int(0.12 * span) + 2)
    top = int(np.argmax(wid[:a + 1]))  # largura da cabeça
    neck = a + int(np.argmin(wid[a:b]))
    if wid[neck] > 0.92 * wid[:neck].max():  # sem pescoço visível (close): cabeça = 45% da altura
        neck = int(0.45 * span)
    cols = np.nonzero(on[y0:y0 + neck].any(0))[0]
    return np.array([cols.min(), y0, cols.max(), y0 + neck], np.float32)


def analisar(cena):
    global _sess
    clip = os.path.join(DIR, "clipes", cena + ".mp4")
    params = {"clip_sha256": sha256(clip), "w": W, "h": H, "seg": "isnet-general-use", "v": 2}
    if c.get("analise_" + cena, params):
        print("cache:", cena); return
    from rembg import new_session, remove
    _sess = _sess or new_session("isnet-general-use")
    dr, dp = os.path.join(DIR, "recorte", cena), os.path.join(DIR, "placa", cena)
    os.makedirs(dr, exist_ok=True); os.makedirs(dp, exist_ok=True)
    faces, corpos, prev = [], [], None
    for i, img in enumerate(frames(clip)):
        m = np.array(remove(Image.fromarray(img), session=_sess, only_mask=True), np.float32)
        if prev is not None:  # estabiliza a máscara no tempo (evita tremulação da borda)
            m = 0.65 * m + 0.35 * prev
        prev = m
        m8 = cv2.GaussianBlur(m, (0, 0), 1.2).clip(0, 255).astype(np.uint8)
        Image.fromarray(m8).save(os.path.join(dr, f"{i:05d}.png"))
        hole = cv2.dilate((m8 > 40).astype(np.uint8) * 255, np.ones((15, 15), np.uint8))
        placa = cv2.inpaint(img, hole, 7, cv2.INPAINT_TELEA)
        Image.fromarray(placa).save(os.path.join(dp, f"{i:05d}.jpg"), quality=90)
        faces.append(rosto(img, m8))
        ys, xs = np.nonzero(m8 > 128)
        corpos.append([xs.min(), ys.min(), xs.max(), ys.max()] if len(xs) else [0, 0, 0, 0])
    faces = np.array(faces)
    # suaviza a caixa do rosto (média móvel) e preenche quadros sem detecção
    k = np.ones(5) / 5
    faces = np.stack([np.convolve(np.pad(faces[:, j], 2, mode="edge"), k, "valid") for j in range(4)], 1)
    out = os.path.join(DIR, f"analise_{cena}.npz")
    np.savez(out, rosto=faces, corpo=np.array(corpos, np.float32), n=len(faces))
    c.put("analise_" + cena, params, os.path.relpath(out, DIR))
    print(cena, len(faces), "quadros")


def voz():
    audio = os.path.join(DIR, "narracao", "take1.mp3")
    params = {"audio_sha256": sha256(audio), "fps": 30}
    if c.get("analise_voz", params):
        return
    pcm = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", audio, "-f", "f32le", "-ac", "1", "-ar", "48000", "-"],
                                       capture_output=True, check=True).stdout, np.float32)
    hop = 1600
    rms = np.sqrt(np.array([np.mean(pcm[i:i + hop] ** 2) for i in range(0, len(pcm), hop)]) + 1e-9)
    rms = np.convolve(rms / rms.max(), np.ones(3) / 3, "same")
    out = os.path.join(DIR, "analise_voz.npz")
    np.savez(out, rms=rms.astype(np.float32), fps=30)
    c.put("analise_voz", params, os.path.relpath(out, DIR))


if __name__ == "__main__":
    voz()
    for cena in sys.argv[1:]:
        analisar(cena)

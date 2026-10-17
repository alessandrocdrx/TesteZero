"""Mapa de profundidade de cada cena (feito uma vez, cacheado) para a câmera 3D com paralaxe por pixel.

Depth Anything V2 small (ONNX, CPU) roda no quadro inteiro do clipe (no fundo já recortado o modelo
enxerga um "fantasma" onde estava o personagem). Depois a área do personagem é preenchida a partir do
fundo em volta, porque ele é desenhado como camada própria.

Saída: cache/profund_cenaNN.npz
  d     (K, 518, 294) uint8   disparidade do FUNDO, 0 = longe, 255 = perto (normalizada na cena toda)
  passo int                    um mapa a cada `passo` quadros (o render interpola)
  pers  (K,) float32           disparidade mediana do personagem (0..1), pivô da câmera

Uso: python3 profundidade.py cena01 [cena02 …]
"""
import os, subprocess, sys, urllib.request
import numpy as np
import cv2
from PIL import Image
from cache import Cache, sha256, DIR

MODELO = os.path.join(DIR, "modelos", "depth_anything_v2_small.onnx")
URL = "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx"
DW, DH, PASSO = 294, 518, 3  # múltiplos de 14 (entrada do modelo), 9:16
c = Cache()


def sessao():
    import onnxruntime as ort
    if not os.path.exists(MODELO):
        os.makedirs(os.path.dirname(MODELO), exist_ok=True)
        urllib.request.urlretrieve(URL, MODELO)
    return ort.InferenceSession(MODELO, providers=["CPUExecutionProvider"])


def quadros(path):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={DW}:{DH}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(DW * DH * 3)
        if len(b) < DW * DH * 3:
            break
        yield np.frombuffer(b, np.uint8).reshape(DH, DW, 3)


def analisar(cena, s):
    clip = os.path.join(DIR, "clipes", cena + ".mp4")
    params = {"clip_sha256": sha256(clip), "modelo": "depth-anything-v2-small", "w": DW, "h": DH, "passo": PASSO, "v": 1}
    if c.get("profund_" + cena, params):
        print("cache:", cena); return
    mean, std = np.float32([0.485, 0.456, 0.406]), np.float32([0.229, 0.224, 0.225])
    brutos, pers = [], []
    for i, img in enumerate(quadros(clip)):
        if i % PASSO:
            continue
        x = ((img.astype(np.float32) / 255 - mean) / std).transpose(2, 0, 1)[None]
        d = s.run(None, {"pixel_values": x})[0][0]
        m = np.asarray(Image.open(os.path.join(DIR, "recorte", cena, f"{i:05d}.png")), np.float32)
        m = cv2.resize(m, (DW, DH)) > 100
        brutos.append((d, m))
    tudo = np.concatenate([d.ravel() for d, _ in brutos])
    lo, hi = np.percentile(tudo, 1), np.percentile(tudo, 99.5)  # escala única na cena: sem tremulação
    out = []
    for d, m in brutos:
        n = np.clip((d - lo) / (hi - lo), 0, 1)
        pers.append(float(np.median(n[m])) if m.sum() > 200 else 0.5)
        n8 = (n * 255).astype(np.uint8)
        if m.any():  # fundo atrás do personagem: preenchido pelo entorno
            buraco = cv2.dilate(m.astype(np.uint8) * 255, np.ones((9, 9), np.uint8))
            n8 = cv2.inpaint(n8, buraco, 9, cv2.INPAINT_TELEA)
        out.append(cv2.GaussianBlur(n8, (0, 0), 1.5))
    path = os.path.join(DIR, f"profund_{cena}.npz")
    np.savez_compressed(path, d=np.array(out), passo=PASSO, pers=np.array(pers, np.float32))
    c.put("profund_" + cena, params, os.path.relpath(path, DIR))
    print(cena, len(out), "mapas")


if __name__ == "__main__":
    s = sessao()
    for cena in sys.argv[1:]:
        analisar(cena, s)

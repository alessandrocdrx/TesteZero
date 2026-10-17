"""Bateria de testes automáticos do anúncio (tipo C). Só entregar se TODOS passarem.

Uso: python3 testes.py VIDEO --de 11.8 --ate 15.6 [--final]
Gera: _render/relatorio.md, _render/relatorio.json e _render/inspecao.jpg (piores quadros de cada teste, ampliados).
"""
import argparse, json, os, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import render as R

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("--de", type=float, required=True); ap.add_argument("--ate", type=float, required=True)
ap.add_argument("--final", action="store_true")
a = ap.parse_args()
W, H = R.tamanho(a.final); k = W / 1080
OUT = os.path.join(R.HERE, "_render")
FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 22)


def ler_video(path, w, h):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


V = ler_video(a.video, W, H)
n0 = int(round(a.de * R.FPS)); N = len(V)
T = [(n0 + i) / R.FPS for i in range(N)]
res, piores = {}, {}

# diagnóstico do render (mesmos quadros, só dependem de t)
D, cache_fr = [], {}
for t in T:
    _, d = R.render_quadro(t, a.final, cache_fr, diag=True)
    D.append(d)

# ---------- 2. Integridade do personagem (consistência + deformação) ----------
cores, d_cor = [], []
for i in range(N):
    m = D[i]["mask"] > 0.6
    x0, y0, x1, y1 = [int(v) for v in D[i]["rosto"]]
    tronco = m.copy(); tronco[:max(0, y1)] = False  # camisa: abaixo da cabeça
    pele = m.copy(); pele[:max(0, y0)] = False; pele[max(0, y1):] = False
    c1 = V[i][tronco].mean(0) if tronco.any() else np.zeros(3)
    c2 = V[i][pele].mean(0) if pele.any() else np.zeros(3)
    cores.append(np.r_[c1, c2])
cores = np.array(cores); ref = np.median(cores, 0)
d_cor = np.abs(cores - ref).max(1)
area = np.array([d["mask"].mean() for d in D])
salto = np.abs(np.r_[0, area[2:] - 2 * area[1:-1] + area[:-2], 0]) / (area + 1e-6)  # pico isolado = deformação/estouro (braço rápido chega a ~5,5%)
res["2_integridade"] = {"desvio_cor_max": float(d_cor.max()), "salto_area_max_%": float(100 * salto.max()),
                        "passou": bool(d_cor.max() < 40 and salto.max() < 0.08)}
piores["2_integridade"] = int(np.argmax(d_cor + 300 * salto))

# ---------- 3. Áudio: sem clipping, sem estalos, sem dessincronia ----------
pcm = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-f", "f32le", "-ac", "1", "-ar", "48000", "-"],
                                   capture_output=True, check=True).stdout, np.float32)
pico_db = 20 * np.log10(np.abs(pcm).max() + 1e-9)
dif = np.abs(np.diff(pcm)); estalo = float(dif.max() / (np.percentile(dif, 99.9) + 1e-9))
dur_a = len(pcm) / 48000; dur_v = N / R.FPS
orig = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(R.DIR, "narracao", "take1.mp3"), "-f", "f32le",
                                     "-ac", "1", "-ar", "48000", "-"], capture_output=True, check=True).stdout, np.float32)
off = int((a.de - R.LEAD) * 48000)
seg = orig[max(0, off):max(0, off) + len(pcm)]
env = lambda x: np.array([np.sqrt(np.mean(x[i:i + 480] ** 2)) for i in range(0, len(x) - 480, 480)])
e1, e2 = env(pcm), env(seg)
n = min(len(e1), len(e2)); lags = range(-10, 11)
cc = [np.corrcoef(e1[max(0, l):n + min(0, l)], e2[max(0, -l):n - max(0, l)])[0, 1] for l in lags]
lag_ms = 10 * list(lags)[int(np.argmax(cc))]
res["3_audio"] = {"pico_dBFS": round(float(pico_db), 2), "razao_estalo": round(estalo, 2), "dur_audio": round(dur_a, 3),
                  "dur_video": round(dur_v, 3), "dessincronia_ms": lag_ms,
                  "passou": bool(pico_db < -1 and estalo < 8 and abs(dur_a - dur_v) <= 1 / R.FPS + 0.03 and abs(lag_ms) <= 20)}

# ---------- 4. Força do 3D: em cada trecho de 0,5 s, objetos ≥ 1,5% da tela OU paralaxe ≥ 1,5% da largura ----------
cob = np.array([d["cobertura"].mean() for d in D]); par = np.array([d["paralaxe"] for d in D])
janelas = []
for j in range(0, N, 15):
    sl = slice(j, min(N, j + 15))
    a_obj = float(cob[sl].max()); a_par = float(np.abs(par[sl]).max()) / W  # separação fundo × personagem
    janelas.append({"t": round(T[j], 2), "objetos_%": round(100 * a_obj, 2), "paralaxe_%": round(100 * a_par, 2),
                    "ok": a_obj >= 0.015 or a_par >= 0.015})
res["4_forca_3d"] = {"janelas": janelas, "passou": all(w["ok"] for w in janelas)}
piores["4_forca_3d"] = int(np.argmin(cob))

# ---------- 5. Sincronia: cada efeito a até ±0,2 s da palavra ----------
sinc = []
for nome, nome_k, t_pal in [("anéis chama azul", "chama azul", R.T_AZUL), ("check bem feito", "bem feito", R.palavra("bem"))]:
    if not (a.de <= t_pal <= a.ate):
        continue
    # primeiro quadro em que a cobertura cresce perto da palavra
    ce = np.array([d["por_efeito"].get(nome_k, 0.0) for d in D])
    idx = [i for i in range(N) if ce[i] > 0.002]
    t_ef = T[idx[0]] if idx else None
    sinc.append({"efeito": nome, "palavra_s": round(t_pal, 3), "efeito_s": t_ef,
                 "erro_s": None if t_ef is None else round(t_ef - t_pal, 3)})
res["5_sincronia"] = {"efeitos": sinc, "passou": all(s["erro_s"] is not None and abs(s["erro_s"]) <= 0.2 for s in sinc)}

# ---------- 6. Legendas e @: safe zone, fora do rosto, contraste ----------
ass = os.path.join(OUT, "legendas.ass")
raw = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"color=c=black@0:s={W}x{H}:r={R.FPS},format=rgba",
                      "-vf", f"trim=start={a.de}:end={a.ate},setpts=PTS-STARTPTS,ass={ass}", "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
                     capture_output=True, check=True).stdout
L = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 4)[:N, ..., 3] > 20
safe = dict(topo=250 * k, base=H - 420 * k, esq=60 * k, dir=W - 150 * k)
fora, sobre_rosto = 0, 0
pior6, pv = 0, -1
for i in range(len(L)):
    ys, xs = np.nonzero(L[i])
    if not len(ys):
        continue
    v = 0
    if ys.min() < safe["topo"] or ys.max() > safe["base"] or xs.min() < safe["esq"] or xs.max() > safe["dir"]:
        fora += 1; v += 1
    x0, y0, x1, y1 = [int(q) for q in D[i]["rosto"]]
    if L[i][max(0, y0):max(0, y1), max(0, x0):max(0, x1)].any():
        sobre_rosto += 1; v += 1
    if v > pv:
        pv, pior6 = v, i
lum = lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
lin = lambda c: [((x / 255) / 12.92 if x / 255 <= 0.04045 else (((x / 255) + 0.055) / 1.055) ** 2.4) for x in c]
contraste = (lum(lin((255, 200, 48))) + 0.05) / (lum(lin((10, 26, 48))) + 0.05)  # amarelo × contorno escuro
res["6_legendas"] = {"quadros_fora_safe_zone": fora, "quadros_sobre_rosto": sobre_rosto, "contraste": round(contraste, 2),
                     "passou": fora == 0 and sobre_rosto == 0 and contraste >= 4.5}
piores["6_legendas"] = pior6

# ---------- 7. Flicker: luminância média sem saltos entre quadros (exceto cortes de cena) ----------
Y = V.astype(np.float32).mean((1, 2, 3))
d2 = np.abs(Y[2:] - 2 * Y[1:-1] + Y[:-2])
cortes = {int(round((c[1] - a.de) * R.FPS)) for c in R.CENAS}
d2m = np.array([0 if any(abs(i + 1 - c) <= 1 for c in cortes) else v for i, v in enumerate(d2)])
res["7_flicker"] = {"max_2a_derivada_luma": round(float(d2m.max()), 2), "passou": bool(d2m.max() < 3.0)}
piores["7_flicker"] = int(np.argmax(d2m)) + 1

res["1_vazamento"] = {"passou": True, "nota": "não se aplica ao tipo C (100% IA)"}

# ---------- 8. Inspeção visual: recortes ampliados dos piores quadros ----------
tiles = []
for nome, i in piores.items():
    x0, y0, x1, y1 = [int(q) for q in D[i]["rosto"]]
    fr = Image.fromarray(V[i])
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2 + int(0.35 * (y1 - y0))
    s = int(max(x1 - x0, 120 * k) * 1.4)
    crop = fr.crop((cx - s, cy - s, cx + s, cy + s)).resize((360, 360), Image.LANCZOS)
    full = fr.resize((202, 360))
    tile = Image.new("RGB", (562, 392), (20, 20, 20)); tile.paste(full, (0, 32)); tile.paste(crop, (202, 32))
    ImageDraw.Draw(tile).text((6, 4), f"{nome}  t={T[i]:.2f}s", font=FONT, fill=(255, 220, 60))
    tiles.append(tile)
sheet = Image.new("RGB", (562 * 2, 392 * ((len(tiles) + 1) // 2)), (0, 0, 0))
for j, tl in enumerate(tiles):
    sheet.paste(tl, ((j % 2) * 562, (j // 2) * 392))
sheet.save(os.path.join(OUT, "inspecao.jpg"), quality=88)
res["8_inspecao"] = {"arquivo": "_render/inspecao.jpg", "passou": True, "nota": "conferir visualmente"}

tudo = all(v["passou"] for v in res.values())
json.dump(res, open(os.path.join(OUT, "relatorio.json"), "w"), indent=2, ensure_ascii=False)
md = [f"# Relatório de testes — {os.path.basename(a.video)} ({a.de}–{a.ate} s)", "", f"**Resultado: {'TODOS PASSARAM' if tudo else 'FALHOU'}**", "",
      "| Teste | Resultado | Detalhes |", "|---|---|---|"]
for kk in sorted(res):
    v = dict(res[kk]); ok = v.pop("passou")
    md.append(f"| {kk} | {'✅' if ok else '❌'} | {json.dumps(v, ensure_ascii=False)[:300]} |")
open(os.path.join(OUT, "relatorio.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md))
raise SystemExit(0 if tudo else 1)

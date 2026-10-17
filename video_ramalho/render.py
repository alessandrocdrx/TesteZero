"""Render do anúncio Ramalho Fogões (vertical 9:16) com câmera virtual, paralaxe, objetos 3D e legendas.

Tudo é função só do tempo t (sem estado entre quadros), então o trecho pedido é dividido em 4 pedaços
renderizados em paralelo e unidos com ffmpeg concat (sem recodificar). Uma única passada de encode.

Uso:
  python3 render.py --de 11.8 --ate 15.6 --saida teste.mp4            # rascunho 540x960
  python3 render.py --final --saida Ramalho_Fogoes.mp4                # 1080x1920, vídeo inteiro
"""
import argparse, json, math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
import cv2
from PIL import Image
import efeitos3d as e3
from cache import DIR

HERE = os.path.dirname(os.path.abspath(__file__))
FPS, LEAD, AW, AH = 30, 0.5, 540, 960  # AW/AH: resolução da análise (máscaras e placas)
ROSA_FUNDO = None

# ---------- narração e palavras (tempos do vídeo = narração + LEAD) ----------
PAL = json.load(open(os.path.join(DIR, "narracao", "take1.json")))
for w in PAL:
    w["s"] += LEAD; w["e"] += LEAD
# correções da transcrição para a legenda (o áudio está certo, o texto da transcrição não)
FIX = {"Concerto,": "Conserto,", "Chama": "Chama", "WhatsApp.": "WhatsApp:", "41": "(41)", "-9": "9", "-8485": "8485-", "-1317": "1317"}
for w in PAL:
    w["t"] = FIX.get(w["w"], w["w"])


def palavra(txt, n=0):
    hits = [w for w in PAL if w["w"].strip(".,?!:").lower() == txt.strip(".,?!:").lower()]
    return hits[n]["s"]


VOZ = np.load(os.path.join(DIR, "analise_voz.npz"))["rms"]


def energia(t):
    i = int((t - LEAD) * 30)
    return float(VOZ[i]) if 0 <= i < len(VOZ) else 0.0


# ---------- cenas: (clipe, início, fim no vídeo, tempo do clipe = a*t + b, plano, opções) ----------
T_AZUL = palavra("Chama", 2)  # "Chama azul" (0: chama amarela, 1: Chama Ramalho)
FIM = 25.0  # tela final até aqui
CORTES = [0.0, 4.1, 5.6, 9.25, 11.8, 15.15, 17.6, FIM]
A_FIM = (5.0 - 3.05) / (FIM - 17.6)
CENAS = [  # trechos do clipe escolhidos pela folha de contato
    ("cena01", 0.0, 4.1, (1.0, 0.6), 1.04, {"sem_rosto": True}),               # chama amarela falha e apaga
    ("cena02", 4.1, 5.6, (1.8, 2.2 - 1.8 * 4.1), 1.0, {}),                     # entra com a caixa e sorri
    ("cena03", 5.6, 9.25, (3.4 / 3.65, 1.6 - 3.4 / 3.65 * 5.6), 1.02, {}),   # encaixa a tampa e regula a chama, sorri
    ("cena04", 9.25, 11.8, (1.3, 1.6 - 1.3 * 9.25), 1.0, {}),                  # acende o industrial e mostra
    ("cena05", 11.8, 15.15, (0.672, 2.75 - 0.672 * 11.8), 1.06, {}),          # chama azul (só depois que a mão sai do fogo)
    ("cena06", 15.15, 17.6, (1.0, 0.6 - 15.15), 1.04, {}),                     # joinha
    # tela final: o fim do clipe 6 em câmera lenta, desfocado e escurecido, com o selo, o telefone e o número
    ("cena06", 17.6, FIM, (A_FIM, 3.05 - 17.6 * A_FIM), 1.04, {"fim": True}),
]


def cena_em(t):
    for c in CENAS:
        if c[1] <= t < c[2]:
            return c
    return CENAS[-1]


def dolly(t):
    """Dolly-zoom na troca de cena: o fundo encolhe e o personagem cresce ao mesmo tempo (0,4 s após o corte)."""
    for c in CORTES[1:-2]:
        u = t - c
        if 0 <= u < 0.4:
            e = (1 - u / 0.4) ** 2
            return 1 + 0.16 * e, 1 - 0.07 * e
    return 1.0, 1.0


# ---------- efeitos 3D: palavra → objeto (tabela do PLANO.md) ----------
def env(t, t0, dur, ent=0.25, sai=0.35):
    """Envelope de escala: pop de entrada (com overshoot) e saída suave."""
    if t < t0 or t > t0 + dur:
        return 0.0
    a = (t - t0) / ent
    up = 1.0 if a >= 1 else math.sin(a * math.pi / 2) * (1 + 0.25 * math.sin(a * math.pi))
    b = (t0 + dur - t) / sai
    return up * (1.0 if b >= 1 else max(b, 0))


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def efeitos(t, info):
    """Objetos ativos em t: (malha, rotação, centro_px(x,y) em AW×AH, z, tamanho_base_px, brilho, nome do efeito)."""
    out = []
    fx0, fy0, fx1, fy1 = info["rosto"]; bx0, by0, bx1, by1 = info["corpo"]
    cx = (fx0 + fx1) / 2 if fx1 > fx0 else AW / 2

    def add(malha, R, x, y, z, tam, glow, nome):
        if tam > 4:
            out.append((malha, R, (x, y), z, tam, glow, nome))

    # 1. "amarela": chama amarela entra pela esquerda, treme e falha
    t1 = palavra("amarela"); k = env(t, t1 - 0.05, CORTES[1] - t1 + 0.05)
    if k > 0:
        falha = 1.0 if math.sin(9.0 * t) > -0.55 else 0.45
        x = -60 + 250 * ease((t - t1) / 0.45)
        add(e3.juntar(e3.chama(t, (255, 190, 30), 1.0, seed=1)), e3.rot(0.1, 0.8 * t, 0.15 * math.sin(6 * t)),
            x, 0.40 * AH, 0.8, 250 * k * falha * (0.9 + 0.1 * math.sin(23 * t)), True, "amarela")
    # 2. "falhando": faíscas (tetraedros) estouram do queimador e caem, em várias profundidades
    t2 = palavra("Falhando")
    for rajada in (0.0, 0.45):
        for j in range(8):
            u = t - (t2 - 0.05 + rajada + 0.03 * j)
            if 0 <= u < 0.9:
                ang = -math.pi / 2 + (j - 3.5) * 0.32
                x = 0.55 * AW + 260 * math.cos(ang) * u
                y = 0.58 * AH + 330 * math.sin(ang) * u + 520 * u * u
                add(e3.faisca(), e3.rot(5 * u + j, 7 * u, j), x, y, 0.7 + 0.8 * j / 7, 70 * (1 - u / 0.9) + 10, True, "falhando")
    # 3. "acender?": interrogação gira e some no corte
    t3 = palavra("acender?"); k = env(t, t3 - 0.05, CORTES[1] - t3 + 0.05)
    if k > 0:
        add(e3.interrogacao(), e3.rot(0.15, 4.0 * (t - t3), 0), 0.74 * AW, 0.24 * AH, 0.9, 230 * k, False, "acender")
    # 4. "Ramalho Fogões": selo com a chama do logo, pop no centro-baixo e órbita curta
    t4 = palavra("Ramalho", 0); k = env(t, t4 - 0.05, CORTES[2] - t4 + 0.05)
    if k > 0:
        u = t - t4
        add(e3.selo(t), e3.rot(0.1, 0.5 * math.sin(2.2 * u), 0), AW / 2 + 70 * math.sin(1.8 * u), 0.52 * AH,
            0.9 + 0.08 * math.cos(1.8 * u), 230 * k, True, "ramalho")
    # 5. "Conserto": chave inglesa orbita o técnico (z 0,8 → 1,4)
    t5 = palavra("Concerto,"); k = env(t, t5 - 0.05, CORTES[3] - t5 + 0.05)
    if k > 0:
        a = 2.1 * (t - t5) - 0.6
        add(e3.chave_inglesa(), e3.rot(0.3, a + 1.2, 0.5), cx + 175 * math.cos(a), fy1 + 70 + 35 * math.sin(a),
            1.1 - 0.3 * math.sin(a), 210 * k, False, "conserto")
    # 6. "regulagem": botão de fogão gira 270°
    t6 = palavra("regulagem,"); k = env(t, t6 - 0.05, 2.1)
    if k > 0:
        add(e3.botao(), e3.rot(-0.9, 0, 1.5 * math.pi * ease((t - t6) / 1.2)), max(100, bx0 + 30), min(fy1 + 260, 0.7 * AH),
            0.85, 170 * k, False, "regulagem")
    # 7. "limpeza": bolhas sobem em várias profundidades (bokeh)
    t7 = palavra("limpeza"); k = env(t, t7 - 0.05, CORTES[3] - t7 + 0.05)
    if k > 0:
        for j in range(9):
            u = t - t7 - 0.11 * j
            if u > 0:
                z = 0.6 + 1.4 * ((j * 5) % 9) / 8
                add(e3.bolha(), e3.rot(0.2, u, 0), 60 + (j * 173) % 420 + 15 * math.sin(3 * u + j), 0.86 * AH - 300 * u,
                    z, 75 * k, False, "limpeza")
    # 8. "conversão de gás": botijão gira atrás do ombro
    t8 = palavra("conversão"); k = env(t, t8 - 0.05, CORTES[3] - t8 + 0.05)
    if k > 0:
        add(e3.botijao(), e3.rot(0.15, 1.6 * (t - t8), 0), min(fx1 + 95, AW - 90), fy1 + 30, 1.2, 250 * k, False, "conversao")
    # 9. "Instalação": registro com mangueira desliza para o lugar
    t9 = palavra("Instalação"); k = env(t, t9 - 0.05, CORTES[4] - t9 + 0.05)
    if k > 0:
        x = AW + 120 - (AW + 120 - min(cx + 150, AW - 110)) * ease((t - t9) / 0.5)
        add(e3.registro(), e3.rot(0.35, -0.5 + 0.25 * math.sin(2 * t), 0), x, min(fy1 + 210, 0.7 * AH), 0.9, 210 * k, False, "instalacao")
    # 10. "industrial": anel de 6 chamas azuis faz uma órbita completa ao redor do técnico
    t10 = palavra("industrial."); k = env(t, t10 - 0.05, T_AZUL - t10 + 0.1)  # passa o bastão aos anéis da "Chama azul"
    if k > 0:
        a = 2 * math.pi * (t - t10) / 1.2 - math.pi / 2
        add(e3.anel_de_chamas(t * 1.4, n=6, cor=(30, 110, 255)), e3.rot(0.4, 0.8 * t, 0), cx + 190 * math.cos(a),
            min(fy1 + 140, 0.62 * AH), 1.0 + 0.3 * math.sin(a), 220 * k, True, "industrial")
    # 11. "Chama azul": dois anéis de chama orbitando em sentidos opostos, abaixo do rosto
    t0 = T_AZUL - 0.05; k = env(t, t0, palavra("bem") - t0)  # saem quando entra o check (juntos viravam borrão)
    if k > 0:
        for sent, fase, dy in ((1, 0.0, 0.0), (-1, math.pi, 70.0)):
            a = sent * 2.2 * (t - t0) + fase
            z = 1.0 + 0.16 * math.sin(a)  # z<1 na frente, z>1 atrás (mais que isso vira borrão no peito)
            add(e3.anel_de_chamas(t * (1.3 + 0.2 * sent), cor=(30, 110, 255)), e3.rot(0.42, 0.9 * t * sent, 0.0),
                cx + 190 * math.cos(a), min(fy1 + 130, 0.6 * AH) + dy + 18 * math.sin(a + 0.6), z, 175 * k, True, "chama azul")
    # 12. "bem feito": check 3D com brilho, à direita do peito
    t12 = palavra("bem"); k = env(t, t12 - 0.05, CORTES[5] - t12 + 0.15)
    if k > 0:
        add(e3.check(), e3.rot(0.15, 0.6 * math.sin(2.5 * (t - t12)), -0.1), min(bx1 - 40, AW - 120), fy1 + 215, 0.85, 150 * k, True, "bem feito")
    # 13. "Curitiba e Região": pino de mapa cai e quica
    t13 = palavra("Curitiba"); k = env(t, t13 - 0.05, CORTES[6] - t13 + 0.05, ent=0.05)
    if k > 0:
        u = t - t13 + 0.05; yt = min(fy1 + 150, 0.62 * AH)
        y = -80 + (yt + 80) * (u / 0.35) ** 2 if u < 0.35 else yt - 45 * abs(math.sin(9 * (u - 0.35))) * math.exp(-4 * (u - 0.35))
        add(e3.pino(), e3.rot(0.1, 2.0 * u, 0), max(95, bx0 - 5), y, 0.9, 190 * k, False, "curitiba")
    # tela final: selo da Ramalho no alto
    k = env(t, CORTES[6], FIM - CORTES[6] + 1, ent=0.4)
    if k > 0:
        add(e3.selo(t), e3.rot(0.1, 0.45 * math.sin(1.3 * t), 0), AW / 2, 0.255 * AH, 0.95, 220 * k, True, "selo final")
    # 14. "WhatsApp": telefone genérico gira e fixa; o número fica até o fim
    t14 = palavra("WhatsApp."); k = env(t, t14 - 0.05, FIM - t14 + 1)
    if k > 0:
        ry = 4 * math.pi * (1 - math.exp(-2.5 * (t - t14))) + 0.25 * math.sin(1.5 * t)
        add(e3.telefone(), e3.rot(0.1, ry, 0.12), AW / 2, 0.49 * AH, 0.9, 190 * k, True, "whatsapp")
    return out


# ---------- composição ----------
def tamanho(final):
    return (1080, 1920) if final else (540, 960)


def carregar(cena, i, W, H):
    i = max(0, i)
    fr = os.path.join(DIR, "recorte", cena, f"{i:05d}.png")
    n = len(os.listdir(os.path.dirname(fr)))
    i = min(i, n - 1)
    m = np.asarray(Image.open(os.path.join(DIR, "recorte", cena, f"{i:05d}.png")), np.float32) / 255
    p = np.asarray(Image.open(os.path.join(DIR, "placa", cena, f"{i:05d}.jpg")).convert("RGB"), np.float32) / 255
    if (W, H) != (AW, AH):
        m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR); p = cv2.resize(p, (W, H), interpolation=cv2.INTER_CUBIC)
    return i, m, p


def quadro_clipe(cena, i, W, H, cache_fr):
    key = (cena, i)
    if key not in cache_fr:
        path = os.path.join(DIR, "clipes", cena + ".mp4")
        out = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"select=eq(n\\,{i}),scale={W}:{H}:flags=lanczos",
                              "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        if len(cache_fr) > 3:
            cache_fr.pop(next(iter(cache_fr)))
        cache_fr[key] = np.frombuffer(out, np.uint8).reshape(H, W, 3).astype(np.float32) / 255
    return cache_fr[key]


def warp(img, s, dx, dy, W, H, borda=cv2.BORDER_REFLECT):
    M = np.float32([[s, 0, (1 - s) * W / 2 + dx], [0, s, (1 - s) * H / 2 + dy]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=borda)


_PROF = {}


def profundidade(nome, pos, W, H):
    """Disparidade do fundo (0 longe … 1 perto) no quadro `pos` (24 fps, fracionário) e a do personagem (pivô)."""
    if nome not in _PROF:
        z = np.load(os.path.join(DIR, f"profund_{nome}.npz"))
        _PROF[nome] = (z["d"], int(z["passo"]), z["pers"])
    d, passo, pers = _PROF[nome]
    k = min(max(pos / passo, 0), len(d) - 1); k0 = int(k); k1 = min(k0 + 1, len(d) - 1); f = k - k0
    m = d[k0].astype(np.float32) * (1 - f) + d[k1].astype(np.float32) * f
    return cv2.resize(m / 255, (W, H), interpolation=cv2.INTER_LINEAR), float(pers[k0] * (1 - f) + pers[k1] * f)


def orbita(t):
    """Câmera 3D por cena: arco lateral (de um lado ao outro) + avanço. Em px de 1080 e fração de zoom."""
    nome, ta, tb, _, _, op = cena_em(t)
    u = ease(min(1.0, max(0.0, (t - ta) / (tb - ta))))
    lado = -1 if CENAS.index(cena_em(t)) % 2 else 1  # alterna o sentido a cada corte
    A = 60.0 if op.get("fim") else 120.0
    return lado * A * (2 * u - 1), 0.25 * A * math.sin(math.pi * u), 0.10 * u


def camera(t, plano):
    """Câmera virtual: plano da cena + zoom de respiração com a voz + leve câmera na mão + deslocamento p/ paralaxe."""
    zoom = plano * (1.0 + 0.025 * energia(t))
    sx = 3.0 * math.sin(1.7 * t) + 1.6 * math.sin(4.3 * t + 1)
    sy = 2.4 * math.sin(1.3 * t + 2) + 1.2 * math.sin(3.7 * t)
    dx = 22.0 * math.sin(0.55 * t + 1.2)  # movimento lateral lento (paralaxe visível no celular)
    return zoom, sx, sy, dx


def blend_sprite(out, sp, x, y, alpha_extra=None, screen=False):
    """Mistura um sprite RGBA (float) em out (float32) só na área do sprite."""
    H, W = out.shape[:2]; h, w = sp.shape[:2]
    x0, y0 = int(round(x - w / 2)), int(round(y - h / 2))
    a0, b0 = max(0, -x0), max(0, -y0); a1, b1 = min(w, W - x0), min(h, H - y0)
    if a1 <= a0 or b1 <= b0:
        return
    reg = out[y0 + b0:y0 + b1, x0 + a0:x0 + a1]
    s = sp[b0:b1, a0:a1]
    al = s[..., 3:4]
    if alpha_extra is not None:
        al = al * alpha_extra[y0 + b0:y0 + b1, x0 + a0:x0 + a1, None]
    if screen:
        reg[:] = 1 - (1 - reg) * (1 - s[..., :3] * al)
    else:
        reg[:] = reg * (1 - al) + s[..., :3] * al


def render_quadro(t, final, cache_fr, diag=False):
    W, H = tamanho(final); f = W / AW
    nome, ta, tb, (a, b), plano, op = cena_em(t)
    an = np.load(os.path.join(DIR, f"analise_{nome}.npz"))
    tc = a * t + b
    # clipes Kling a 24 fps → 30 fps: mistura os dois quadros vizinhos (sem trepidação nem tremulação de cadência)
    pos = max(0.0, tc * 24); i0 = int(pos); fr = pos - i0
    i, m, placa = carregar(nome, i0, W, H)
    img = quadro_clipe(nome, i, W, H, cache_fr)
    j, m1, placa1 = carregar(nome, i0 + 1, W, H)
    if j != i and fr > 0.01:
        img = img * (1 - fr) + quadro_clipe(nome, j, W, H, cache_fr) * fr
        m = m * (1 - fr) + m1 * fr; placa = placa * (1 - fr) + placa1 * fr
    info = {"rosto": an["rosto"][i], "corpo": an["corpo"][i]}
    if op.get("sem_rosto") or op.get("fim"):
        info["rosto"] = np.zeros(4, np.float32)
    zoom, sx, sy, dx = camera(t, plano)
    zf, zp = dolly(t)
    # paralaxe: fundo (placa) anda 1,8x mais que o personagem
    fundo = warp(placa, zoom * 1.015 * zf, (dx + sx) * f, sy * f, W, H)
    # câmera 3D: cada pixel do fundo anda conforme a profundidade, relativo ao personagem (pivô)
    dmap, dp = profundidade(nome, pos, W, H)
    dmap = warp(dmap, zoom * 1.015 * zf, (dx + sx) * f, sy * f, W, H)
    if op.get("sem_rosto"):
        dp = 0.5
    ox, oy, oz = orbita(t)
    rel = dmap - dp
    X, Y = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    esc = 1 + oz * rel * 2.2
    fundo = cv2.remap(fundo, (W / 2 + (X - W / 2) / esc - ox * f * rel).astype(np.float32),
                      (H * 0.55 + (Y - H * 0.55) / esc - oy * f * rel).astype(np.float32),
                      cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    paralaxe = abs(ox * f * (dp - float(np.percentile(dmap, 10)))) + abs(0.8 * dx * f)
    frente = warp(img, zoom * zp, (dx + sx) * f, sy * f, W, H)
    mask = warp(m, zoom * zp, (dx + sx) * f, sy * f, W, H, cv2.BORDER_CONSTANT)
    zoom_p = zoom * zp

    def proj(px, py):  # ponto da análise (AW×AH) → tela, com a mesma câmera do personagem
        return ((px - AW / 2) * zoom_p + AW / 2 + dx + sx) * f, ((py - AH / 2) * zoom_p + AH / 2 + sy) * f

    fx0, fy0 = proj(*info["rosto"][:2]); fx1, fy1 = proj(*info["rosto"][2:])
    zona_rosto = np.ones((H, W), np.float32)
    pad = 0.25 * (fx1 - fx0) / 2
    if info["rosto"].any():  # cenas sem rosto: caixa zerada viraria fatia negativa (tela quase toda)
        zona_rosto[max(0, int(fy0 - pad)):max(0, int(fy1 + pad)), max(0, int(fx0 - pad)):max(0, int(fx1 + pad))] = 0
    zona_rosto = cv2.GaussianBlur(zona_rosto, (0, 0), 6 * f)
    # névoa atrás do personagem (só no fundo), leve e azulada embaixo
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    nevoa = (0.10 * np.clip((yy - 0.45) / 0.55, 0, 1)) * np.array([0.75, 0.85, 1.0], np.float32)
    fundo = 1 - (1 - fundo) * (1 - nevoa)
    if op.get("fim"):  # tela final: a cena vira fundo desfocado e escurecido; os objetos ficam livres
        u = min(1.0, (t - ta) / 0.4)
        cena = frente * mask[..., None] + fundo * (1 - mask[..., None])
        fundo = cena * (1 - u) + cv2.GaussianBlur(cena, (0, 0), 1 + 6 * u * f) * u * (1 - 0.5 * u)  # ele continua reconhecível
        mask = mask * 0
    out = fundo.copy()
    objs = sorted(efeitos(t, info), key=lambda o: -o[3])  # de trás para frente
    brilho = np.zeros_like(out)
    sprites = []
    for malha, R, (px, py), z, base, glow, rot_ in objs:
        tam = int(base / z * f) // 2 * 2
        if tam < 8:
            continue
        sp = e3.sprite(malha, R, tam)
        sig = 5.0 * abs(1 / z - 1) * f  # bokeh ∝ |1/z − 1|
        if sig > 0.4:
            sp = cv2.GaussianBlur(sp, (0, 0), sig)
        x, y = proj(px, py)
        sprites.append((sp, x, y, z, glow, rot_))
    for sp, x, y, z, glow, _ in sprites:  # atrás do personagem: escondidos onde a máscara cobre
        if z > 1:
            blend_sprite(out, sp, x, y, 1 - mask)
    out = frente * mask[..., None] + out * (1 - mask[..., None])
    for sp, x, y, z, glow, _ in sprites:  # na frente: nunca sobre o rosto
        if z <= 1:
            blend_sprite(out, sp, x, y, zona_rosto)
    for sp, x, y, z, glow, _ in sprites:  # luz das chamas em screen blend
        if glow:
            g = cv2.GaussianBlur(sp, (0, 0), 14 * f) * 0.9
            blend_sprite(brilho, g, x, y, (1 - mask) if z > 1 else zona_rosto, screen=True)
    out = 1 - (1 - out) * (1 - brilho)
    out = np.clip(out, 0, 1)
    if not diag:
        return out
    cob, por = np.zeros((H, W, 3), np.float32), {}  # cobertura visível dos objetos 3D (para os testes)
    for sp, x, y, z, glow, nome_ef in sprites:
        branco = sp.copy(); branco[..., :3] = 1
        c1 = np.zeros((H, W, 3), np.float32)
        blend_sprite(c1, branco, x, y, (1 - mask) if z > 1 else zona_rosto)
        por[nome_ef] = por.get(nome_ef, 0.0) + float(c1[..., 0].mean())
        cob = np.maximum(cob, c1)
    return out, {"cobertura": cob[..., 0], "por_efeito": por, "rosto": (fx0, fy0, fx1, fy1), "mask": mask,
                 "paralaxe": paralaxe, "n_obj": len(sprites)}


# ---------- legendas e @ (ASS) ----------
def ts(t):
    t = max(0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def gerar_ass(path, W, H):
    k = W / 1080
    AMARELO, BRANCO, TINTA = "&H0030C8FF", "&H00FFFFFF", "&H00301A0A"
    L = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2", "",
         "[V4+ Styles]",
         "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
         "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
         # karaokê: Secondary = ainda não falada (branco), Primary = palavra atual/falada (amarelo-chama)
         f"Style: Leg,Liberation Sans,{int(76*k)},{AMARELO},{BRANCO},{TINTA},&H80000000,1,0,0,0,100,100,1,0,1,{6*k:.1f},{3*k:.1f},2,{int(160*k)},{int(160*k)},{int(540*k)},1",
         f"Style: Big,Liberation Sans,{int(150*k)},&H00FFB040,&H00FFB040,&H00401000,&H80000000,1,0,0,0,100,100,3,0,1,{9*k:.1f},{5*k:.1f},5,40,40,0,1",
         f"Style: At,Liberation Sans,{int(38*k)},&H20FFFFFF,&H20FFFFFF,&H60000000,&H00000000,1,0,0,0,100,100,1,0,1,{2.5*k:.1f},0,5,0,0,0,1",
         "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    # frases curtas: quebra em pontuação ou a cada 4 palavras
    frases, cur = [], []
    for j, w in enumerate(PAL):
        cur.append(w)
        if w["w"][-1] in ".,?!:" or len(cur) >= 4 or j == len(PAL) - 1:
            frases.append(cur); cur = []
    for j, p in enumerate(frases):
        st = p[0]["s"] - 0.06
        en = min(frases[j + 1][0]["s"] - 0.04 if j + 1 < len(frases) else p[-1]["e"] + 2.5, p[-1]["e"] + 1.0)
        parts, tt = [], st
        for w in p:
            pre = w["s"] - tt
            if pre > 0.01:
                parts.append(f"{{\\k{int(pre * 100)}}}")
            d = max(0.08, w["e"] - w["s"])
            parts.append(f"{{\\kf{int(d * 100)}}}{w['t']} "); tt = w["s"] + d
        txt = "".join(parts).strip()
        if p[0]["t"] == "(41)":  # o número já aparece grande na tela final; não repete na legenda
            continue
        L.append(f"Dialogue: 1,{ts(st)},{ts(en)},Leg,,0,0,0,,{{\\fad(80,120)\\fscx90\\fscy90\\t(0,140,\\fscx100\\fscy100)}}{txt}")
    pop = "{\\fad(120,300)\\fscx60\\fscy60\\t(0,200,\\fscx112\\fscy112)\\t(200,380,\\fscx100\\fscy100)}"
    L.append(f"Dialogue: 2,{ts(T_AZUL - 0.05)},{ts(T_AZUL + 1.6)},Big,,0,0,0,,{{\\pos({W//2},{int(H*0.585)})}}{pop}CHAMA AZUL")
    t4 = palavra("Ramalho", 0)
    L.append(f"Dialogue: 2,{ts(t4 - 0.05)},{ts(CORTES[2])},Big,,0,0,0,,{{\\pos({W//2},{int(H*0.585)})\\fs{int(84*k)}\\c&H0030C8FF&}}{pop}RAMALHO FOGÕES")
    # tela final: nome, número, região e Facebook, centralizados (o número entra quando é falado e fica até o fim)
    cx = W // 2
    L.append(f"Dialogue: 2,{ts(CORTES[6] + 0.1)},{ts(FIM)},Big,,0,0,0,,{{\\pos({cx},{int(H*0.385)})\\fs{int(84*k)}\\c&H0030C8FF&}}{pop}RAMALHO FOGÕES")
    L.append(f"Dialogue: 2,{ts(palavra('41'))},{ts(FIM)},Big,,0,0,0,,{{\\pos({cx},{int(H*0.605)})\\fs{int(84*k)}\\c&H00FFFFFF&}}{pop}(41) 98485-1317")
    L.append(f"Dialogue: 2,{ts(palavra('41') + 0.3)},{ts(FIM)},Big,,0,0,0,,{{\\pos({cx},{int(H*0.665)})\\fs{int(58*k)}\\c&H00FFB040&}}{pop}Curitiba e Região")
    L.append(f"Dialogue: 2,{ts(palavra('41') + 0.9)},{ts(FIM)},Big,,0,0,0,,{{\\pos({cx},{int(H*0.715)})\\fs{int(52*k)}\\c&H00FFFFFF&}}{pop}Facebook: /ramalhofogoes")
    # crédito do editor flutuando embaixo, centralizado, dentro da safe zone (base H-420)
    x0, y0 = W // 2, H - int(445 * k)
    t = 0.0
    while t < 60:
        a, b = (y0, y0 - int(8 * k)) if int(t / 2) % 2 == 0 else (y0 - int(8 * k), y0)
        L.append(f"Dialogue: 3,{ts(t)},{ts(t + 2)},At,,0,0,0,,{{\\move({x0},{a},{x0},{b})}}Edição: @alessandrocdrx")
        t += 2
    open(path, "w").write("\n".join(L) + "\n")


# ---------- pedaços paralelos ----------
def pedaco(args):
    k, ta, tb, final, ass, out = args
    W, H = tamanho(final)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-vf", f"setpts=PTS+{ta:.4f}/TB,ass={ass},setpts=PTS-STARTPTS,format=yuv420p",
           "-c:v", "libx264", "-preset", "medium" if final else "veryfast", "-crf", "18" if final else "23", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cache_fr = {}
    n0, n1 = int(round(ta * FPS)), int(round(tb * FPS))
    for n in range(n0, n1):
        fr = render_quadro(n / FPS, final, cache_fr)
        p.stdin.write((fr * 255 + 0.5).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--de", type=float, default=CENAS[0][1]); ap.add_argument("--ate", type=float, default=CENAS[-1][2])
    ap.add_argument("--final", action="store_true"); ap.add_argument("--saida", required=True)
    a = ap.parse_args()
    W, H = tamanho(a.final)
    tmp = os.path.join(HERE, "_render"); os.makedirs(tmp, exist_ok=True)
    ass = os.path.join(tmp, "legendas.ass"); gerar_ass(ass, W, H)
    n0, n1 = int(round(a.de * FPS)), int(round(a.ate * FPS))
    cortes = [n0 + (n1 - n0) * j // 4 for j in range(5)]
    jobs = [(j, cortes[j] / FPS, cortes[j + 1] / FPS, a.final, ass, os.path.join(tmp, f"p{j}.mp4")) for j in range(4)]
    with Pool(4) as pool:
        partes = pool.map(pedaco, jobs)
    lista = os.path.join(tmp, "lista.txt")
    open(lista, "w").write("".join(f"file '{p}'\n" for p in partes))
    audio = os.path.join(DIR, "narracao", "take1.mp3")
    dur = (n1 - n0) / FPS
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lista, "-i", audio,
                    "-filter_complex", f"[1:a]adelay={int(LEAD*1000)}|{int(LEAD*1000)},apad,atrim={a.de:.3f}:{a.de + dur:.3f},asetpts=PTS-STARTPTS,"
                    f"afade=t=in:d=0.05,afade=t=out:st={dur - 0.08:.3f}:d=0.08[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}",
                    "-movflags", "+faststart", a.saida], check=True)
    print("ok", a.saida)


if __name__ == "__main__":
    main()

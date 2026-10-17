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
    hits = [w for w in PAL if w["w"].strip(".,?!:").lower() == txt.lower()]
    return hits[n]["s"]


VOZ = np.load(os.path.join(DIR, "analise_voz.npz"))["rms"]


def energia(t):
    i = int((t - LEAD) * 30)
    return float(VOZ[i]) if 0 <= i < len(VOZ) else 0.0


# ---------- cenas: (nome do clipe, início, fim no vídeo, tempo do clipe = a*t + b, plano) ----------
T_AZUL = palavra("Chama", 2)  # "Chama azul" (0: chama amarela, 1: Chama Ramalho)
CENAS = [
    ("cena05", 11.8, 15.6, (1.0, 2.0 - T_AZUL), 1.06),
]


def cena_em(t):
    for c in CENAS:
        if c[1] <= t < c[2]:
            return c
    return CENAS[-1]


# ---------- efeitos 3D: palavra → objeto (tabela do PLANO.md) ----------
def env(t, t0, dur, ent=0.25, sai=0.35):
    """Envelope de escala: pop de entrada (com overshoot) e saída suave."""
    if t < t0 or t > t0 + dur:
        return 0.0
    a = (t - t0) / ent
    up = 1.0 if a >= 1 else math.sin(a * math.pi / 2) * (1 + 0.25 * math.sin(a * math.pi))
    b = (t0 + dur - t) / sai
    return up * (1.0 if b >= 1 else max(b, 0))


def efeitos(t, info):
    """Lista de objetos ativos em t: (malha, rotação, centro_px(x,y) em AW×AH, z, tamanho_base_px, brilho)."""
    out = []
    fx0, fy0, fx1, fy1 = info["rosto"]; bx0, by0, bx1, by1 = info["corpo"]
    cx = (fx0 + fx1) / 2
    # 11. "Chama azul": dois anéis de chama orbitando em sentidos opostos, abaixo do rosto
    t0 = T_AZUL - 0.05
    k = env(t, t0, CENAS[-1][2] - t0 + 0.1)  # fica até o corte (sai na transição)
    if k > 0:
        for sent, fase, dy in ((1, 0.0, 0.0), (-1, math.pi, 70.0)):
            a = sent * 2.2 * (t - t0) + fase
            z = 1.0 + 0.32 * math.sin(a)  # z<1 na frente, z>1 atrás
            x = cx + 190 * math.cos(a)
            y = min(fy1 + 130, 0.6 * AH) + dy + 18 * math.sin(a + 0.6)
            out.append((e3.anel_de_chamas(t * (1.3 + 0.2 * sent), cor=(30, 110, 255)), e3.rot(0.42, 0.9 * t * sent, 0.0),
                        (x, y), z, 215 * k, True, "chama azul"))
    # 12. "bem feito": check 3D com brilho, à direita do peito
    t1 = palavra("bem")
    k = env(t, t1 - 0.05, CENAS[-1][2] - t1 + 0.15)
    if k > 0:
        out.append((e3.check(), e3.rot(0.15, 0.6 * math.sin(2.5 * (t - t1)), -0.1), (min(bx1 - 40, AW - 120), fy1 + 215), 0.85, 150 * k, True, "bem feito"))
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
    nome, ta, tb, (a, b), plano = cena_em(t)
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
    zoom, sx, sy, dx = camera(t, plano)
    # paralaxe: fundo (placa) anda 1,8x mais que o personagem
    fundo = warp(placa, zoom * 1.015, (1.8 * dx + sx) * f, sy * f, W, H)
    frente = warp(img, zoom, (dx + sx) * f, sy * f, W, H)
    mask = warp(m, zoom, (dx + sx) * f, sy * f, W, H, cv2.BORDER_CONSTANT)

    def proj(px, py):  # ponto da análise (AW×AH) → tela, com a mesma câmera do personagem
        return ((px - AW / 2) * zoom + AW / 2 + dx + sx) * f, ((py - AH / 2) * zoom + AH / 2 + sy) * f

    fx0, fy0 = proj(*info["rosto"][:2]); fx1, fy1 = proj(*info["rosto"][2:])
    zona_rosto = np.ones((H, W), np.float32)
    pad = 0.25 * (fx1 - fx0) / 2
    zona_rosto[max(0, int(fy0 - pad)):int(fy1 + pad), max(0, int(fx0 - pad)):int(fx1 + pad)] = 0
    zona_rosto = cv2.GaussianBlur(zona_rosto, (0, 0), 6 * f)
    # névoa atrás do personagem (só no fundo), leve e azulada embaixo
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
    nevoa = (0.10 * np.clip((yy - 0.45) / 0.55, 0, 1)) * np.array([0.75, 0.85, 1.0], np.float32)
    fundo = 1 - (1 - fundo) * (1 - nevoa)
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
                 "paralaxe": 0.8 * dx * f, "n_obj": len(sprites)}


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
         f"Style: Leg,Liberation Sans,{int(78*k)},{AMARELO},{BRANCO},{TINTA},&H80000000,1,0,0,0,100,100,1,0,1,{6*k:.1f},{3*k:.1f},2,{int(70*k)},{int(170*k)},{int(470*k)},1",
         f"Style: Big,Liberation Sans,{int(150*k)},&H00FFB040,&H00FFB040,&H00401000,&H80000000,1,0,0,0,100,100,3,0,1,{9*k:.1f},{5*k:.1f},5,40,40,0,1",
         f"Style: At,Liberation Sans,{int(40*k)},&H40FFFFFF,&H40FFFFFF,&H60000000,&H00000000,1,0,0,0,100,100,1,0,1,{2.5*k:.1f},0,7,0,0,0,1",
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
        if p[0]["t"] == "(41)":  # número do WhatsApp sem espaços entre os blocos
            txt = txt.replace("(41) ", "(41) ").replace("8485- ", "8485-")
        L.append(f"Dialogue: 1,{ts(st)},{ts(en)},Leg,,0,0,0,,{{\\fad(80,120)\\fscx90\\fscy90\\t(0,140,\\fscx100\\fscy100)}}{txt}")
    pop = "{\\fad(120,300)\\fscx60\\fscy60\\t(0,200,\\fscx112\\fscy112)\\t(200,380,\\fscx100\\fscy100)}"
    L.append(f"Dialogue: 2,{ts(T_AZUL - 0.05)},{ts(T_AZUL + 1.6)},Big,,0,0,0,,{{\\pos({W//2},{int(H*0.665)})}}{pop}CHAMA AZUL")
    # @ flutuando: pequenos \move de ida e volta, dentro da safe zone (topo 250 px, esquerda 60 px)
    x0, y0 = int(70 * k), int(270 * k)
    t = 0.0
    while t < 60:
        a, b = (y0, y0 + int(10 * k)) if int(t / 2) % 2 == 0 else (y0 + int(10 * k), y0)
        L.append(f"Dialogue: 3,{ts(t)},{ts(t + 2)},At,,0,0,0,,{{\\move({x0},{a},{x0 + int(4*k)},{b})}}@alessandrocdrx")
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

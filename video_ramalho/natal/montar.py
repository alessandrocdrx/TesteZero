"""Vídeo de Natal da Ramalho Fogões: 1080×1920 (Reels), 30 s, 6 clipes Kling Omni + narração (Gabriel).

Etapas (uma só passada, sem versões extras):
  1. base.mp4: os 6 clipes (já 9:16) em sequência, 1080×1920, 30 fps, cortados em 30 s
  2. stage1.mp4: fotos reais dos fogões em porta-retratos 3D (natal/fotos.py) nas palavras-chave + cartão final em tela cheia (natal/cartao.py)
  3. legendas.ass: karaokê centralizado embaixo + faixa de contato fixa no alto
  4. Ramalho_Natal_Reels.mp4: legendas queimadas + narração (atraso de 0,5 s) + créditos

Uso: python3 natal/montar.py
"""
import json, os, subprocess
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(HERE)

W, H, FPS = 1080, 1920, 30  # Reels: 9:16
DUR = float(os.environ.get('NATAL_DUR', 30.0))  # NATAL_DUR=5 para um teste curto
LEAD = 0.5  # a narração entra meio segundo depois do início
PASTA = os.path.join(RAIZ, "cache", "natal_v2")
CLIPES = [os.path.join(PASTA, f"c{i:02d}.mp4") for i in range(1, 7)]
DUR_CLIPE = 5.041667
NARRACAO = os.path.join(RAIZ, "cache", "natal", "narracao_natal.mp3")
MUSICA = os.path.join(RAIZ, "cache", "natal", "musica_natal.mp3")
PALAVRAS = json.load(open(os.path.join(RAIZ, "cache", "natal", "narracao_natal.json"), encoding="utf-8"))
FIM_CARTAO = 24.4  # cartão final começa aqui (a narração termina em ~22,7 s)


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def base():
    """Concatena os 6 clipes 9:16 e corta em 30 s."""
    lista = os.path.join(HERE, "clipes.txt")
    with open(lista, "w") as f:
        for c in CLIPES:
            f.write(f"file '{c}'\n")
    out = os.path.join(HERE, "base.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lista,
         "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p",  # clipes já saem em 9:16
         "-t", str(DUR), "-an", "-c:v", "libx264", "-crf", "16", "-preset", "medium", out])
    return out


def palavra(txt, depois=0.0):
    """Tempo (já com o atraso da narração) da primeira ocorrência da palavra depois de `depois`."""
    alvo = txt.strip(".,?!:").lower()
    for p in PALAVRAS:
        if p["s"] > depois and p["w"].strip(".,?!:").lower() == alvo:
            return p["s"] + LEAD
    raise KeyError(txt)


FOTOS = os.path.join(RAIZ, "cache", "fotos_natal")  # fotos reais do cliente (fora do git)
# foto: palavra que a chama e lado onde aparece (alterna para duas poderem conviver)
# vazio: os fogões reais agora estão dentro das cenas 2 e 3 (Kling com as fotos como referência)
QUADROS = []  # ex.: [("fogão", "R"), ("revisão", "L"), ("conserto", "R"), ...]
XL, XR, YQ, ESC_Q = 0.27, 0.73, 0.215, 0.80  # posição e escala dos porta-retratos


def objetos():
    """Lista de (início, duração, sprite RGBA, lado, alvo x, alvo y) com o tempo da palavra."""
    from PIL import Image
    res = []
    for i, (chave, lado) in enumerate(QUADROS, 1):
        t0 = palavra(chave, depois=(palavra("Chama") - LEAD) if chave == "Azul" else 0.0)
        sp = np.asarray(Image.open(os.path.join(FOTOS, f"q_{i:02d}.png")).convert("RGBA"), np.float32) / 255.0
        sp[..., :3] *= sp[..., 3:4]  # pré-multiplica para a perspectiva não criar bordas escuras
        res.append([t0, 2.2, sp, lado, int((XL if lado == "L" else XR) * W), int(YQ * H)])
    for k, o in enumerate(res):  # sai antes da próxima do mesmo lado entrar
        prox = [p[0] for p in res[k + 1:] if p[3] == o[3]]
        if prox:
            o[1] = min(o[1], prox[0] - o[0])
    return res


def inclinar(sp, ang_y, ang_z, esc):
    """Gira o porta-retrato em 3D (eixo vertical = ang_y, plano = ang_z) com perspectiva; RGBA float."""
    import cv2
    h, w = sp.shape[:2]
    f = 1.6 * w  # distância focal: perspectiva suave
    cy, sy, cz, sz = np.cos(ang_y), np.sin(ang_y), np.cos(ang_z), np.sin(ang_z)
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = []
    for x, y in src:
        X, Y = (x - w / 2), (y - h / 2)
        X, Y = X * cz - Y * sz, X * sz + Y * cz
        Z = X * sy
        X = X * cy
        k = f / (f + Z)
        dst.append([X * k * esc, Y * k * esc])
    dst = np.float32(dst)
    lo = dst.min(0)
    dst -= lo
    tam = np.ceil(dst.max(0)).astype(int) + 1
    M = cv2.getPerspectiveTransform(src, dst)
    out = cv2.warpPerspective(sp, M, (int(tam[0]), int(tam[1])), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    a = np.clip(out[..., 3:4], 1e-6, 1)
    out[..., :3] = np.where(out[..., 3:4] > 1e-4, out[..., :3] / a, 0)
    return out


def pop(u):
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def cabeca(m, lado):
    """Topo da cabeça e x do centro da personagem da esquerda ou da direita (máscara 0..1, H×W)."""
    meio = m.shape[1] // 2
    reg = m[:, :meio] if lado == "L" else m[:, meio:]
    linhas = np.nonzero((reg > 0.5).any(1))[0]
    if not len(linhas):
        return None
    y0 = int(linhas.min())
    cols = np.nonzero((reg[y0:y0 + 60] > 0.5).any(0))[0]
    x = int(cols.mean()) + (0 if lado == "L" else meio)
    return x, y0


def compor():
    import cv2
    import render_util as ru
    objs = objetos()
    print("fotos:", [(round(o[0], 2), round(o[1], 2), o[3]) for o in objs])
    cartao = cv2.cvtColor(cv2.imread(os.path.join(FOTOS, "cartao_final.png")), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    fundo = base()
    mascaras = {}
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", fundo, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                            "-pix_fmt", "yuv420p", os.path.join(HERE, "stage1.mp4")], stdin=subprocess.PIPE)
    n = int(round(DUR * FPS))
    for i in range(n):
        raw = dec.stdout.read(W * H * 3)
        if len(raw) < W * H * 3:
            break
        t = i / FPS
        img = np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32) / 255.0
        c = min(5, int(t / DUR_CLIPE)); fq = int(round((t - c * DUR_CLIPE) * 24))  # clipes a 24 quadros/s
        if c not in mascaras:
            mascaras[c] = np.load(os.path.join(PASTA, f"mascaras_c{c + 1:02d}.npz"))["a"]
        am = mascaras[c]
        m = cv2.resize(am[min(fq, len(am) - 1)], (W, H), interpolation=cv2.INTER_LINEAR).astype(np.float32) / 255.0
        original = img.copy()
        for t0, dur, sp0, lado, xt, yt in objs:
            if not (t0 <= t < t0 + dur):
                continue
            u = t - t0
            k = pop(u / 0.45) * (1.0 if u < dur - 0.3 else max(0.0, (t0 + dur - t) / 0.3))
            if k <= 0.01:
                continue
            ini = cabeca(cv2.resize(am[min(fq, len(am) - 1)], (W // 4, H // 4)).astype(np.float32) / 255.0, lado)
            if ini:
                xi, yi = ini[0] * 4, ini[1] * 4 + 120
            else:
                xi, yi = xt, yt + 200
            e = pop(u / 0.7)  # sobe de trás da personagem até a posição final, crescendo
            x = xi + (xt - xi) * e
            y = yi + (yt - yi) * e
            sinal = 1 if lado == "L" else -1  # vira de frente para o centro
            ang_y = sinal * (0.9 * (1 - e) + 0.18 + 0.05 * np.sin(2.2 * u))
            ang_z = sinal * (-0.05 + 0.025 * np.sin(1.7 * u + 0.5))
            sp = inclinar(sp0, ang_y, ang_z, ESC_Q * (0.55 + 0.45 * e) * k)
            ru.blend(img, sp, x, y)
            if e < 0.999:  # ainda "atrás" da personagem: ela tapa a foto (profundidade real)
                img = img * (1 - m[..., None]) + original * m[..., None]
        if t >= FIM_CARTAO:  # cartão final em tela cheia (entra com zoom suave)
            a = pop((t - FIM_CARTAO) / 0.7)
            z = 1.06 - 0.06 * a
            cz = cv2.resize(cartao, None, fx=z, fy=z, interpolation=cv2.INTER_LINEAR)
            oy, ox = (cz.shape[0] - H) // 2, (cz.shape[1] - W) // 2
            img = img * (1 - a) + cz[oy:oy + H, ox:ox + W] * a
        enc.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
    enc.stdin.close(); enc.wait(); dec.wait()
    return os.path.join(HERE, "stage1.mp4")


def ass():
    """Legendas karaokê (frases curtas, centralizadas embaixo) + cartão final."""
    path = os.path.join(HERE, "legendas.ass")
    L = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2", "",
         "[V4+ Styles]",
         "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
         "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
         "Style: Leg,Liberation Sans,84,&H0030C8FF,&H00FFFFFF,&H00301A0A,&H80000000,1,0,0,0,100,100,0,0,1,6,2,2,110,110,430,1",
         "Style: Big,Liberation Sans,104,&H0030C8FF,&H0030C8FF,&H00401000,&H80000000,1,0,0,0,100,100,2,0,1,7,3,5,40,40,0,1",
         "Style: Num,Liberation Sans,70,&H00FFFFFF,&H00FFFFFF,&H00401000,&H80000000,1,0,0,0,100,100,2,0,1,6,3,5,40,40,0,1",
         "Style: Sub,Liberation Sans,58,&H00FFFFFF,&H00FFFFFF,&H00401000,&H80000000,1,0,0,0,100,100,1,0,1,4,2,5,40,40,0,1",
         "Style: Bar,DejaVu Sans,34,&H00FFFFFF,&H00FFFFFF,&H50301008,&HFF000000,1,0,0,0,100,100,0,0,3,12,0,8,0,0,0,1",
         "Style: At,Liberation Sans,26,&HA0FFFFFF,&HA0FFFFFF,&H90000000,&H00000000,0,0,0,0,100,100,1,0,1,1,0,5,0,0,0,1",
         "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]

    def ts(s):
        h, m = int(s // 3600), int(s % 3600 // 60)
        return f"{h}:{m:02d}:{s % 60:05.2f}"

    # frases: quebra em pontuação ou a cada 5 palavras
    palavras = list(PALAVRAS)
    iw = next(k for k, p in enumerate(palavras) if p["w"].strip(".,?!:").lower() == "whatsapp")
    fimnum = next(k for k in range(iw + 1, len(palavras)) if palavras[k]["w"].strip(".,?!:") == "1317")
    palavras[iw + 1:fimnum + 1] = [{"w": "(41) 98485-1317.", "s": palavras[iw + 1]["s"], "e": palavras[fimnum]["e"]}]
    grupos, atual = [], []
    for p in palavras:
        atual.append(p)
        if p["w"].rstrip().endswith((".", "!", "?", ",")) or len(atual) >= 5 or p["w"].strip(".,?!:").lower() == "whatsapp":
            grupos.append(atual); atual = []
    if atual:
        grupos.append(atual)
    for g in grupos:
        ini = g[0]["s"] + LEAD
        fim = g[-1]["e"] + LEAD + 0.15
        partes = []
        for j, p in enumerate(g):
            prox = g[j + 1]["s"] if j + 1 < len(g) else p["e"]
            dur = max(5, int(round((prox - p["s"]) * 100)))
            partes.append(f"{{\\k{dur}}}{p['w']} ")
        L.append(f"Dialogue: 0,{ts(ini)},{ts(fim)},Leg,,0,0,0,,{''.join(partes).rstrip()}")

    # contato fixo desde o início, discreto no alto (o cartão final em tela cheia assume no fim)
    L.append(f"Dialogue: 2,{ts(0)},{ts(FIM_CARTAO + 0.3)},Bar,,0,0,0,,{{\\pos({W//2},{int(H*0.045)})}}"
             "Técnico Marco · WhatsApp {\\c&H28CEFF&}(41) 98485-1317{\\c&HFFFFFF&}\\NFacebook: /ramalhofogoes")
    # crédito do editor: pequeno, semitransparente, flutuando embaixo (não fica em destaque nem é coberto)
    for k in range(int(DUR)):
        y = H - 110 - (18 if k % 2 else 0)
        L.append(f"Dialogue: 3,{ts(k)},{ts(k + 1)},At,,0,0,0,,{{\\pos({W//2},{y})}}Edição: @alessandrocdrx")
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")
    return path


def final(stage, legendas):
    out = os.environ.get("NATAL_SAIDA", os.path.join(RAIZ, "Ramalho_Natal_Reels.mp4"))
    run(["ffmpeg", "-y", "-v", "error", "-i", stage, "-i", NARRACAO, "-stream_loop", "-1", "-i", MUSICA,
         "-filter_complex",
         f"[0:v]ass={legendas}[v];"
         f"[1:a]adelay={int(LEAD*1000)}:all=1,apad,atrim=0:{DUR}[nar];"
         f"[2:a]atrim=0:{DUR},volume=0.22,afade=t=out:st={DUR - 3.5}:d=3.5[mus];"
         f"[nar][mus]amix=inputs=2:duration=first:weights=1 1:normalize=0[a]",
         "-map", "[v]", "-map", "[a]", "-t", str(DUR), "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    return out


if __name__ == "__main__":
    st = compor()
    lg = ass()
    print("pronto:", final(st, lg))

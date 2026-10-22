"""Vídeo de Natal da Ramalho Fogões: 1080×1920 (Reels), 30 s, 6 clipes Kling Omni + narração (Gabriel).

Etapas (uma só passada, sem versões extras):
  1. base.mp4: os 6 clipes (já 9:16) em sequência, 1080×1920, 30 fps, cortados em 30 s
  2. stage1.mp4: objetos 3D (efeitos3d) sincronizados às palavras-chave + escurecimento e cartão final
  3. legendas.ass: karaokê centralizado embaixo (palavra a palavra, pelo tempo da transcrição)
  4. Ramalho_Natal_1080p.mp4: legendas queimadas + narração (atraso de 0,5 s) + créditos

Uso: python3 natal/montar.py
"""
import json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(HERE)
sys.path.insert(0, RAIZ)
import efeitos3d as e3  # noqa: E402

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


# objeto 3D → (palavra-chave, malha(t), posição x, y relativos, tamanho em px)
def _malhas():
    return {
        "fogão": (lambda t: e3.juntar(*e3.chama_viva(t, (255, 190, 30), 1.0, seed=1)), 0.20, 0.34, 430),
        "conserto": (lambda t: e3.chave_inglesa(), 0.80, 0.34, 430),
        "regulagem": (lambda t: e3.registro(), 0.22, 0.30, 380),
        "Ramalho": (lambda t: e3.selo(t), 0.50, 0.24, 380),
        "Azul": (lambda t: e3.anel_de_chamas(t), 0.80, 0.30, 420),
        "Curitiba": (lambda t: e3.pino(), 0.20, 0.30, 380),
        "WhatsApp": (lambda t: e3.telefone(), 0.50, 0.28, 420),
        "Feliz": (lambda t: e3.faisca(), 0.50, 0.22, 300),
    }


def objetos():
    """Lista de (início, duração, malha(t), lado, alvo x, alvo y, tam) com o tempo da palavra."""
    cfg = {  # palavra: (malha, lado da personagem de onde nasce, alvo relativo, tamanho)
        "fogão": ("fogão", "L", (0.20, 0.20), 612),
        "conserto": ("conserto", "R", (0.80, 0.20), 612),
        "regulagem": ("regulagem", "L", (0.20, 0.22), 578),
        "Ramalho": ("Ramalho", "R", (0.50, 0.14), 544),
        "Azul": ("Azul", "R", (0.78, 0.20), 612),
        "Curitiba": ("Curitiba", "L", (0.20, 0.20), 578),
        "WhatsApp": ("WhatsApp", "R", (0.50, 0.16), 646),
        "Feliz": ("Feliz", "L", (0.30, 0.18), 510),
    }
    malhas = _malhas()
    res = []
    for chave, (_, lado, (x, y), tam) in cfg.items():
        t0 = palavra(chave, depois=(palavra("Chama") - LEAD) if chave == "Azul" else 0.0)
        res.append((t0, 1.8, malhas[chave][0], lado, int(x * W), int(y * H), tam))
    return sorted(res, key=lambda o: o[0])


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
    print("objetos:", [(round(o[0], 2), o[3]) for o in objs])
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
        for t0, dur, fn, lado, xt, yt, tam in objs:
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
            esc = (0.55 + 0.45 * e) * k
            sp = e3.sprite(fn(u), e3.rot(0.1, 2.0 * u, 0.0), max(8, int(tam * esc)))
            ru.blend(img, sp, x, y)
            if e < 0.999:  # ainda "atrás" da personagem: ela tapa o objeto (profundidade real)
                img = img * (1 - m[..., None]) + original * m[..., None]
        if t >= FIM_CARTAO:  # escurece o fundo no cartão final
            a = min(1.0, (t - FIM_CARTAO) / 0.8)
            img *= 1 - 0.65 * a
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
        if p["w"].rstrip().endswith((".", "!", "?", ",")) or len(atual) >= 5:
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

    # cartão final (começa depois da última fala): técnico, WhatsApp e Facebook juntos
    L.append(f"Dialogue: 2,{ts(FIM_CARTAO)},{ts(DUR)},Big,,0,0,0,,{{\\pos({W//2},{int(H*0.36)})}}RAMALHO FOGÕES")
    L.append(f"Dialogue: 2,{ts(FIM_CARTAO + 0.6)},{ts(DUR)},Sub,,0,0,0,,{{\\pos({W//2},{int(H*0.47)})}}Técnico Marcos")
    L.append(f"Dialogue: 2,{ts(FIM_CARTAO + 1.0)},{ts(DUR)},Num,,0,0,0,,{{\\pos({W//2},{int(H*0.56)})}}WhatsApp (41) 98485-1317")
    L.append(f"Dialogue: 2,{ts(FIM_CARTAO + 1.4)},{ts(DUR)},Sub,,0,0,0,,{{\\pos({W//2},{int(H*0.64)})}}Curitiba e Região")
    L.append(f"Dialogue: 2,{ts(FIM_CARTAO + 1.8)},{ts(DUR)},Sub,,0,0,0,,{{\\pos({W//2},{int(H*0.72)})}}Facebook: /ramalhofogoes")
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

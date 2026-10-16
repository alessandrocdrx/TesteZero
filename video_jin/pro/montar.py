"""Vídeo 'Nij' com edição limpa e legendas karaokê sincronizadas palavra por palavra.

Fundo: bandeira trans ondulando de leve + zoom lento + vinheta suave.
Legendas: frases curtas (até 2 linhas), cada palavra muda de cor no instante em
que é falada (tempos de palavras.json, transcrição da própria narração).
Destaques: JIN / NIJ / NINJA / MULHER entram grandes no centro, na hora da fala.
Som: só a narração.

Uso: python3 montar.py palavras.json narracao.mp3 saida.mp4
"""
import json, math, re, subprocess, sys
import numpy as np
from PIL import Image

words_path, audio, out = sys.argv[1:4]
W, H, FPS = 1080, 1920, 30
LEAD = 0.8  # respiro antes da voz
words = json.load(open(words_path))
for w in words:
    w["s"] += LEAD; w["e"] += LEAD
TOTAL = words[-1]["e"] + 2.5


def ts(t):
    t = max(0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


# ---------- frases: quebra em pontuação, no máximo 6 palavras ----------
phrases, cur = [], []
for i, w in enumerate(words):
    cur.append(w)
    end_punct = re.search(r"[.,:;!?…]$", w["w"])
    gap = i + 1 < len(words) and words[i + 1]["s"] - w["e"] > 0.45
    if end_punct and len(cur) >= 2 or len(cur) >= 6 or gap or i == len(words) - 1:
        phrases.append(cur); cur = []
# junta frase de 1 palavra com a seguinte quando colada (fica mais natural)
merged = []
for p in phrases:
    if merged and len(merged[-1]) == 1 and p[0]["s"] - merged[-1][-1]["e"] < 0.35 and len(p) < 5:
        merged[-1] = merged[-1] + p
    else:
        merged.append(p)
phrases = merged


def wrap(p):
    """Divide em 2 linhas equilibradas se passar de ~22 caracteres."""
    txt = " ".join(w["w"] for w in p)
    if len(txt) <= 22 or len(p) < 2:
        return [p]
    best, bi = 1e9, 1
    for k in range(1, len(p)):
        a = len(" ".join(w["w"] for w in p[:k])); b = len(" ".join(w["w"] for w in p[k:]))
        if abs(a - b) < best: best, bi = abs(a - b), k
    return [p[:bi], p[bi:]]


# ---------- ASS ----------
PINK = "&H00B8A9F5"; WHITE = "&H00FFFFFF"; INK = "&H005C2440"; BOX = "&H60301430"
ass = [
    "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2", "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
    "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    # karaokê: SecondaryColour = antes de falar (branco translúcido), PrimaryColour = já falada (branco forte)
    f"Style: Leg,Liberation Sans,86,{WHITE},&H90FFFFFF,{INK},&H90301430,1,0,0,0,100,100,1,0,1,7,4,2,60,60,200,1",
    f"Style: Big,Liberation Serif,190,{WHITE},{WHITE},{INK},&H80000000,1,1,0,0,100,100,4,0,1,9,6,5,40,40,0,1",
    "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
]
for i, p in enumerate(phrases):
    st = p[0]["s"] - 0.08
    nxt = phrases[i + 1][0]["s"] - 0.1 if i + 1 < len(phrases) else p[-1]["e"] + 1.5
    en = min(nxt, p[-1]["e"] + 1.2)
    lines = wrap(p)
    parts, t = [], st
    for li, line in enumerate(lines):
        for w in line:
            pre = max(0, w["s"] - t)  # pausa antes da palavra
            if pre > 0.01: parts.append(f"{{\\k{int(pre * 100)}}}")
            dur = max(0.08, w["e"] - w["s"])
            parts.append(f"{{\\kf{int(dur * 100)}}}{w['w']} ")
            t = w["s"] + dur
        if li < len(lines) - 1: parts.append("\\N")
    anim = "{\\fad(120,150)\\fscx92\\fscy92\\t(0,160,\\fscx100\\fscy100)}"
    ass.append(f"Dialogue: 1,{ts(st)},{ts(en)},Leg,,0,0,0,,{anim}{''.join(parts).strip()}")

# destaques no centro
def word_t(target, nth=0):
    hits = [w for w in words if re.sub(r"[^\wÀ-ú]", "", w["w"]).lower() == target]
    return hits[nth]["s"] if len(hits) > nth else None

big = []
for txt, key, nth, dur in [("Nij", "nij", 0, 1.1), ("JIN", "jin", 0, 2.6), ("NIJ", "nij", 1, 3.0),
                           ("Ninja", "ninja", 0, 2.4), ("Nij.", "nij", 2, 1.0), ("Mulher.", "mulher", 0, 2.2)]:
    t0 = word_t(key, nth)
    if t0 is not None:
        big.append((t0, dur, txt))
for t0, dur, txt in big:
    pop = "{\\fad(150,350)\\fscx70\\fscy70\\t(0,220,\\fscx108\\fscy108)\\t(220,420,\\fscx100\\fscy100)\\blur1}"
    ass.append(f"Dialogue: 2,{ts(t0 - 0.05)},{ts(t0 + dur)},Big,,0,0,0,,{pop}{txt}")
open("legendas.ass", "w").write("\n".join(ass) + "\n")
print(len(phrases), "frases,", len(big), "destaques")

# ---------- fundo: bandeira ondulando de leve ----------
w, h = W // 2, H // 2
yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
COLS = np.array([(91, 206, 250), (245, 169, 184), (255, 255, 255), (245, 169, 184), (91, 206, 250)], np.float32) / 255
vign = np.clip(1 - 0.35 * (((xx - w / 2) / w) ** 2 + ((yy - h / 2) / h) ** 2) * 2.2, 0.4, 1)[..., None]

cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
       "-i", audio, "-filter_complex",
       f"[0:v]scale={W}:{H}:flags=bicubic,ass=legendas.ass,fade=t=in:st=0:d=0.6,fade=t=out:st={TOTAL - 1.2:.2f}:d=1.2,format=yuv420p[v];"
       f"[1:a]adelay={int(LEAD * 1000)}|{int(LEAD * 1000)},apad,afade=t=out:st={TOTAL - 1.2:.2f}:d=1.2[a]",
       "-map", "[v]", "-map", "[a]", "-t", f"{TOTAL:.2f}", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for fr in range(int(TOTAL * FPS)):
    t = fr / FPS
    z = 1.0 + 0.06 * t / TOTAL
    X = (xx - w / 2) / z + w / 2; Y = (yy - h / 2) / z + h / 2
    ph = X / 80 + t * 0.9 + Y / 260
    off = 6 * np.sin(ph) + 2 * np.sin(X / 37 - t * 1.3)
    idx = np.clip(((Y + off) / h * 5).astype(np.int32), 0, 4)
    img = COLS[idx] * (1 + 0.06 * np.cos(ph))[..., None] * vign
    p.stdin.write((np.clip(img, 0, 1) * 255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait(); print("ok", p.returncode)

"""Monta o vídeo 'Nij' com as cenas geradas (16:9), a narração e as legendas karaokê.

Cada cena ocupa exatamente o trecho da narração que ela ilustra (tempos de palavras.json).
Cenas mais curtas que o trecho ficam em câmera lenta (até 0,6x) e, se ainda faltar, seguram o último quadro.
Legendas: o mesmo gerador de ../pro/montar.py, adaptado para 1920x1080.

Uso: python3 montar_cenas.py clipes/ ../pro/palavras.json ../pro/narracao_fabi.mp3 saida.mp4
(clipes/ contém cena01.mp4 … cena11.mp4)
"""
import json, os, subprocess, sys

clips_dir, words_path, audio, out = sys.argv[1:5]
W, H, FPS, LEAD, X = 1920, 1080, 30, 0.8, 0.35
here = os.path.dirname(os.path.abspath(__file__))

# ---------- legendas: reaproveita ../pro/montar.py em 16:9 ----------
src = open(os.path.join(here, "..", "pro", "montar.py")).read().split("# ---------- fundo")[0]
src = src.replace("W, H, FPS = 1080, 1920, 30", "W, H, FPS = 1920, 1080, 30")
src = src.replace("Liberation Sans,86,", "Liberation Sans,66,").replace(",1,7,4,2,60,60,200,1", ",1,5,3,2,120,120,70,1")
src = src.replace("Liberation Serif,190,", "Liberation Serif,130,").replace(",1,9,6,5,40,40,0,1", ",1,7,5,8,40,40,90,1")
src = src.replace('open("legendas.ass", "w")', 'open("legendas_169.ass", "w")')
src = src.replace("words_path, audio, out = sys.argv[1:4]", "")
g = {"words_path": words_path, "audio": audio, "out": out, "__name__": "legendas"}
exec(compile(src, "montar.py", "exec"), g)
TOTAL = g["TOTAL"]

# ---------- trechos de cada cena (início da fala da cena, em segundos da narração) ----------
starts = [0.0, 6.28, 10.82, 17.82, 25.6, 28.68, 32.34, 37.34, 42.1, 47.76, 57.2]
bounds = [0.0] + [s + LEAD for s in starts[1:]] + [TOTAL]
slots = [bounds[i + 1] - bounds[i] for i in range(len(starts))]

parts = []
for i, slot in enumerate(slots):
    clip = os.path.join(clips_dir, f"cena{i + 1:02d}.mp4")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", clip],
                               capture_output=True, text=True, check=True).stdout)
    need = slot + X
    speed = max(0.6, min(1.0, dur / need))  # só desacelera, no máximo até 0,6x
    hold = max(0.0, need - dur / speed)
    part = f"_parte{i + 1:02d}.mp4"
    vf = (f"setpts=PTS/{speed:.4f},fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"tpad=stop_mode=clone:stop_duration={hold + 0.1:.3f},trim=duration={need:.3f},setpts=PTS-STARTPTS,"
          f"eq=saturation=1.06:contrast=1.03,format=yuv420p")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", clip, "-an", "-vf", vf, "-c:v", "libx264", "-crf", "16",
                    "-preset", "fast", part], check=True)
    parts.append(part)
    print(f"cena {i + 1:2d}: trecho {slot:5.2f}s, clipe {dur:4.1f}s, velocidade {speed:.2f}x, congela {hold:.2f}s")

# ---------- junta com fusões curtas, legenda, voz ----------
args = ["ffmpeg", "-y", "-v", "error"]
for p in parts:
    args += ["-i", p]
args += ["-i", audio]
fc, prev, off = [], "[0:v]", 0.0
for i in range(1, len(parts)):
    off += slots[i - 1]
    fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={X}:offset={off - X / 2:.3f}[v{i}]")
    prev = f"[v{i}]"
n = len(parts)
fc.append(f"{prev}ass=legendas_169.ass,vignette=PI/5,fade=t=in:st=0:d=0.8,fade=t=out:st={TOTAL - 1.5:.2f}:d=1.5,format=yuv420p[v]")
fc.append(f"[{n}:a]adelay={int(LEAD * 1000)}|{int(LEAD * 1000)},apad,afade=t=out:st={TOTAL - 1.2:.2f}:d=1.2[a]")
args += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]", "-t", f"{TOTAL:.2f}",
         "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
subprocess.run(args, check=True)
for p in parts:
    os.remove(p)
print("ok", out)

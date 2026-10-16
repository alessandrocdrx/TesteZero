"""Trilha original: pad + cordas em Am-F-C-G, crescendo até o clímax, coração e sinos."""
import json, wave, subprocess
import numpy as np
cards = json.load(open("cartelas.json"))
sr = 44100; dur = cards[-1]["end"] + 3.0
t = np.arange(int(sr * dur)) / sr
out = np.zeros_like(t)
prog = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [130.81, 196.0, 261.63], [196.0, 246.94, 293.66]]
CL = 5.0
# intensidade: cresce até os cards "heart", cai no final
hs = [c["start"] for c in cards if c.get("fx") == "heart"]
climax = hs[0] if hs else dur * 0.7
I = np.clip(0.35 + 0.65 * (t / climax) ** 1.5, 0, 1)
I = np.where(t > hs[-1] + 4 if hs else t > dur, np.maximum(0.45, 1 - (t - hs[-1] - 4) / 12), I)
for k in range(int(dur / CL) + 1):
    s = k * CL; ch = prog[k % 4]
    i0 = int(s * sr); i1 = min(len(t), int((s + CL + 3) * sr))
    tt = t[i0:i1] - s
    env = np.minimum(1, tt / 2.0) * np.exp(-np.maximum(0, tt - CL) / 1.2)
    seg = np.zeros_like(tt)
    for j, f in enumerate(ch):
        for det in (-0.6, 0.0, 0.7):  # cordas: harmônicos com leve desafinação
            for hmn, amp in ((1, 1), (2, .45), (3, .25), (4, .12)):
                seg += amp * np.sin(2 * np.pi * (f + det) * hmn * tt) * (0.5 if j else 0.7)
    seg += 1.2 * np.sin(2 * np.pi * ch[0] / 2 * tt)
    vib = 1 + 0.05 * np.sin(2 * np.pi * 5 * tt)
    out[i0:i1] += seg * env * vib * 0.05 * I[i0:i1]
    # piano em arpejo
    notes = [ch[0] * 2, ch[1] * 2, ch[2] * 2, ch[1] * 4]
    for n in range(8):
        ns = n * CL / 8; m = tt >= ns; f = notes[n % 4]
        x = tt[m] - ns
        out[i0:i1][m] += 0.16 * (np.sin(2 * np.pi * f * x) + .3 * np.sin(4 * np.pi * f * x)) * np.exp(-x * 2.0)
def bell(at, f=1046.5, g=0.35):
    i0 = int(at * sr); x = t[i0:i0 + int(4 * sr)] - at
    out[i0:i0 + len(x)] += g * sum(a * np.sin(2 * np.pi * f * r * x) * np.exp(-x * d) for r, a, d in ((1, 1, 1.5), (2.76, .5, 2.5), (5.4, .25, 4)))
def thump(at, g=1.0):
    i0 = int(at * sr); x = t[i0:i0 + int(0.5 * sr)] - at
    out[i0:i0 + len(x)] += g * np.sin(2 * np.pi * (48 + 40 * np.exp(-x * 30)) * x) * np.exp(-x * 9)
for c in cards:
    fx = c.get("fx")
    if fx in ("burst", "flip"): bell(c["start"], 1046.5 if fx == "burst" else 1318.5)
    if c.get("year"): bell(c["start"], 1567.98, 0.2)
    if fx == "heart":
        b = c["start"]
        while b < c["end"] + 0.5: thump(b); thump(b + 0.28, 0.7); b += 0.95
out /= np.abs(out).max() * 1.15
out *= np.minimum(1, t / 2.5) * np.minimum(1, (dur - t) / 3.5)
st = np.stack([out, np.roll(out, int(0.015 * sr))], 1)
w = wave.open("_trilha_seca.wav", "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
w.writeframes((np.clip(st, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "_trilha_seca.wav", "-af",
  "aecho=0.8:0.75:90|210|370:0.35|0.25|0.15,lowpass=f=5000,loudnorm=I=-18", "-b:a", "192k", "trilha.mp3"], check=True)
import os; os.remove("_trilha_seca.wav")
print("ok", round(dur, 1))

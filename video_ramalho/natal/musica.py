"""Trilha de Natal sintetizada localmente (sem custo): melodia de "Jingle Bells" (domínio público),
sinos de trenó (ruído agudo curto) e baixo simples, 30 s, mono 44,1 kHz → cache/natal/musica_natal.mp3."""
import os, subprocess, wave
import numpy as np

SR, DUR, BPM = 44100, 30.0, 120
BEAT = 60.0 / BPM
# (nota MIDI, batidas) — "Jingle Bells", refrão em mi maior
MELODIA = [(76, 1), (76, 1), (76, 2), (76, 1), (76, 1), (76, 2), (76, 1), (79, 1), (72, 1), (74, 1), (76, 4),
           (77, 1), (77, 1), (77, 1), (77, 1), (77, 1), (76, 1), (76, 1), (76, 1), (76, 1), (74, 1), (74, 1), (76, 1), (74, 2), (79, 2)]


def freq(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def sintetizar():
    n = int(DUR * SR)
    out = np.zeros(n, np.float32)
    notas, t = [], 0.0
    while t < DUR:  # repete a melodia até cobrir os 30 s
        for m, b in MELODIA:
            notas.append((t, m, b * BEAT)); t += b * BEAT
            if t >= DUR:
                break
    rng = np.random.default_rng(7)
    for t0, m, d in notas:
        i0 = int(t0 * SR); k = int(d * SR)
        x = np.arange(min(k, n - i0)) / SR
        env = np.minimum(1, x / 0.01) * np.exp(-x * 2.5)
        tom = 0.6 * np.sin(2 * np.pi * freq(m) * x) + 0.2 * np.sin(2 * np.pi * 2 * freq(m) * x)
        out[i0:i0 + len(x)] += (0.22 * env * tom).astype(np.float32)
        # baixo: fundamental uma oitava abaixo, a cada batida
        for bt in np.arange(0, d, BEAT):
            j = int((t0 + bt) * SR); L = int(0.25 * SR)
            if j + L > n:
                break
            y = np.arange(L) / SR
            out[j:j + L] += (0.16 * np.exp(-y * 6) * np.sin(2 * np.pi * freq(m - 12) * y)).astype(np.float32)
    # sinos de trenó: ruído passa-alta curto a cada meia batida
    for t0 in np.arange(0, DUR, BEAT / 2):
        j = int(t0 * SR); L = int(0.05 * SR)
        if j + L > n:
            break
        ruido = rng.standard_normal(L).astype(np.float32)
        ruido = np.diff(ruido, prepend=0)  # passa-alta simples
        y = np.arange(L) / SR
        out[j:j + L] += 0.09 * ruido * np.exp(-y * 90)
    out = out / max(1e-6, np.abs(out).max()) * 0.7
    return out


def main():
    pcm = (sintetizar() * 32767).astype(np.int16)
    wav = os.path.join(os.path.dirname(os.path.abspath(__file__)), "musica_natal.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    mp3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache", "natal", "musica_natal.mp3")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-b:a", "192k", mp3], check=True)
    os.remove(wav)
    print("ok", os.path.normpath(mp3))


if __name__ == "__main__":
    main()

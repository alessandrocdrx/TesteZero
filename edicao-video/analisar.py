"""Per-frame analysis of the original: face box (smoothed), smile score, voice energy.
Usage: analisar.py VIDEO AUDIO_WAV OUT.npz"""
import sys
import wave

import cv2
import numpy as np

FPS = 30


def main(video, wav, out):
    face_cc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    smile_cc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_smile.xml")
    cap = cv2.VideoCapture(video)
    boxes, smiles = [], []
    last = None
    while True:
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.equalizeHist(cv2.cvtColor(cv2.resize(f, (360, 640)), cv2.COLOR_BGR2GRAY))
        faces = face_cc.detectMultiScale(g, 1.1, 5, minSize=(70, 70))
        if len(faces):
            x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
            last = (x * 2, y * 2, w * 2, h * 2)  # back to 720x1280
            roi = g[y + h // 2:y + h, x:x + w]
            s = smile_cc.detectMultiScale(roi, 1.7, 22, minSize=(w // 4, h // 8))
            smiles.append(1.0 if len(s) else 0.0)
        else:
            smiles.append(np.nan)
        boxes.append(last if last else (np.nan,) * 4)
    boxes = np.array(boxes, np.float32)
    # fill gaps, then smooth so the protective mask glides with her
    for c in range(4):
        col = boxes[:, c]
        idx = np.arange(len(col))
        ok = ~np.isnan(col)
        col[:] = np.interp(idx, idx[ok], col[ok])
        k = np.ones(9) / 9
        col[:] = np.convolve(np.pad(col, 4, mode="edge"), k, mode="valid")
    sm = np.array(smiles, np.float32)
    sm = np.nan_to_num(sm, nan=0.0)
    sm = np.convolve(np.pad(sm, 15, mode="edge"), np.ones(31) / 31, mode="valid")  # ~1 s window

    w = wave.open(wav)
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    sr = w.getframerate()
    hop = sr // FPS
    rms = np.array([np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2)) for i in range(len(a) // hop)])
    db = 20 * np.log10(rms + 1e-6)
    energy = np.clip((db + 45) / 30, 0, 1)  # -45 dB -> 0, -15 dB -> 1
    # attack fast, release slow: feels like breath
    env = np.zeros_like(energy)
    for i, e in enumerate(energy):
        prev = env[i - 1] if i else 0
        env[i] = prev + (e - prev) * (0.35 if e > prev else 0.06)
    np.savez(out, boxes=boxes, smile=sm, energy=env)
    print("frames", len(boxes), "face found in", int(np.mean(~np.isnan(np.array(smiles))) * 100), "%")
    print("smile>0.4 seconds:", [round(i / FPS, 1) for i in range(0, len(sm), 15) if sm[i] > 0.4])


if __name__ == "__main__":
    main(*sys.argv[1:4])

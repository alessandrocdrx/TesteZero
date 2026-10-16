"""Transcreve um .wav 16 kHz mono com tempos por palavra. Uso: transcrever.py AUDIO.wav [idioma]"""
import sys
import wave

import numpy as np
from faster_whisper import WhisperModel

w = wave.open(sys.argv[1])
audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
model = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = model.transcribe(audio, language=sys.argv[2] if len(sys.argv) > 2 else "ru", beam_size=5, word_timestamps=True)
for s in segs:
    print(f"[{s.start:5.1f}-{s.end:5.1f}] {s.text.strip()}")
    print("   " + " ".join(f"{x.word.strip()}@{x.start:.1f}" for x in s.words))

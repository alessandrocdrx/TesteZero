"""Transcreve a narração com tempos por palavra (faster-whisper local). Uso: transcrever.py audio.mp3 saida.json"""
import json, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
a = np.frombuffer(raw, np.float32)
m = WhisperModel("medium", device="cpu", compute_type="int8")
segs, _ = m.transcribe(a, language="pt", word_timestamps=True,
    initial_prompt="Monica Helms, Stonewall, Marsha P. Johnson, Sylvia Rivera, Pay It No Mind, Erika Hilton, Duda Salabert.")
words = [dict(w=w.word.strip(), s=round(w.start, 2), e=round(w.end, 2)) for s in segs for w in s.words]
json.dump(words, open(sys.argv[2], "w"), ensure_ascii=False)
print(" ".join(x["w"] for x in words))

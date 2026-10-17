"""Transcreve as takes da narração (faster-whisper local) e salva tempo por palavra.

Uso: python3 transcrever.py cache/narracao/take1.mp3 [...]
Saída: cache/narracao/takeN.json  [{w, s, e}]  (cacheado pelo sha256 do áudio)
"""
import json, os, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel
from cache import Cache, sha256

c = Cache()
model = None
for path in sys.argv[1:]:
    nome = "palavras_" + os.path.basename(path).rsplit(".", 1)[0]
    params = {"audio_sha256": sha256(path), "modelo": "whisper-medium", "lingua": "pt"}
    if c.get(nome, params):
        print("cache:", nome); continue
    model = model or WhisperModel("medium", device="cpu", compute_type="int8")
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = model.transcribe(np.frombuffer(pcm, np.float32), language="pt", word_timestamps=True)
    words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for s in segs for w in s.words]
    out = path.rsplit(".", 1)[0] + ".json"
    json.dump(words, open(out, "w"), ensure_ascii=False)
    c.put(nome, params, os.path.relpath(out, os.path.join(os.path.dirname(__file__), "cache")))
    print(os.path.basename(path), " ".join(w["w"] for w in words))

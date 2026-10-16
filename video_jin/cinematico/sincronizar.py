"""Sincroniza as cartelas (roteiro.py -> cartelas.json) com a narração, pelos tempos de cada palavra.

Para cada linha de cada cartela, acha na transcrição a primeira palavra da linha
(busca sequencial, tolerante a pontuação) e usa o instante em que ela é falada.
Uso: python3 sincronizar.py palavras.json ATRASO_VOZ
"""
import json, re, sys, unicodedata
words = json.load(open(sys.argv[1])); D = float(sys.argv[2])
cards = json.load(open("cartelas.json"))
def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(ch for ch in s if unicodedata.category(ch) != "Mn"))
wn = [norm(w["w"]) for w in words]
pos = 0
def find(line):
    global pos
    toks = [norm(t) for t in line.split() if norm(t)]
    if not toks: return None
    for k in range(pos, min(len(wn), pos + 40)):
        if wn[k] == toks[0] and (len(toks) < 2 or k + 1 >= len(wn) or wn[k + 1] == toks[1] or len(toks[0]) > 3):
            pos = k + 1; return words[k]["s"]
    return None
for c in cards:
    if c.get("kind") == "end": c["_ts"] = [None] * len(c["lines"]); continue
    ts = [find(c["year"])] if c.get("year") else []
    for l in c["lines"]: ts.append(find(l))
    c["_ts"] = ts
# preenche lacunas e monta tempos
last = 0.0
for i, c in enumerate(cards):
    ts = c.pop("_ts"); known = [t for t in ts if t is not None]
    if not known:  # cartela sem fala (ex.: lista final): entra logo após a anterior
        st = cards[i - 1]["end"] + 0.7 if i else D
        c["start"], c["end"] = st, st + (7.0 if c.get("kind") == "end" else 3.5); c.pop("line_starts", None); continue
    fill, prev = [], known[0]
    for t in ts: prev = t if t is not None else prev + 0.6; fill.append(prev)
    c["line_starts"] = [t + D - 0.15 for t in fill]
    c["start"] = c["line_starts"][0]
for i, c in enumerate(cards[:-1]):
    nxt = cards[i + 1]
    if "line_starts" in c: c["end"] = max(c["line_starts"][-1] + 1.2, nxt["start"] - 0.55)
    if c["end"] > nxt["start"] - 0.4: c["end"] = nxt["start"] - 0.4
# cartelas finais sem fala: encadeia depois da anterior
for i, c in enumerate(cards):
    if "line_starts" not in c and i:
        c["start"] = cards[i - 1]["end"] + 0.7
        c["end"] = c["start"] + (7.0 if c.get("kind") == "end" else 3.5)
    if i + 1 < len(cards) and "line_starts" not in cards[i + 1] and "line_starts" in c:
        c["end"] = c["line_starts"][-1] + 3.0
json.dump(cards, open("cartelas.json", "w"), ensure_ascii=False, indent=1)
for c in cards: print(f'{c["start"]:6.2f}-{c["end"]:6.2f} {c["lines"][0]}')

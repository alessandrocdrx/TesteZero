"""Cartelas do 'Nij' sincronizadas pelos tempos de cada palavra da narração (palavras.json)."""
import json
D = 2.0  # a voz entra 2s depois da abertura
B = [  # (linhas com início falado em s, extras)
 ([("Nij.", 0.0, "big")], dict(fx="burst")),
 ([("Leram teu nome", 1.24), ("da esquerda pra direita", 2.14), ("e acharam que sabiam", 3.92), ("quem você era.", 5.08)], {}),
 ([("Mas você sempre soube", 6.28), ("que a verdade se lê", 7.62), ("do jeito que o coração espera.", 8.64)], {}),
 ([("Jin, diziam.", 10.82, "big"), ("Ouro, metal,", 12.4), ("brilho guardado.", 13.82)], dict(tint="gold")),
 ([("Você virou o espelho,", 15.02), ("e o ouro respondeu:", 16.3)], dict(fx="flip")),
 ([("Nij.", 17.82, "big"), ("numa língua antiga", 18.52), ("quer dizer: nova.", 19.62)], dict(fx="burst")),
 ([("Nova não porque", 21.28), ("nasceu de novo,", 22.0), ("mas porque enfim nasceu", 23.12), ("o que era seu.", 24.14)], {}),
 ([("Tem o azul do céu", 25.6), ("de quem aprendeu", 26.74), ("a voar sozinha.", 27.6)], dict(tint="blue")),
 ([("O rosa da coragem", 28.68), ("que floresce", 30.14), ("sem pedir licença.", 30.92)], dict(tint="pink")),
 ([("E no meio, o branco:", 32.34), ("a página em branco", 33.98), ("onde você escreve", 35.0), ("a própria sentença.", 35.92)], dict(tint="white")),
 ([("E aí eu te leio:", 37.34), ("Ninja.", 38.76, "big")], dict(burst_at=[38.76])),
 ([("Porque ninguém viu o treino,", 39.46), ("só a chegada.", 40.96)], {}),
 ([("Cada passo no escuro", 42.1), ("foi um golpe certeiro", 43.3)], {}),
 ([("contra o medo,", 44.84), ("contra a dúvida,", 45.64), ("contra o nada.", 46.74)], dict(fx="heart")),
 ([("Você não se escondeu:", 47.76), ("se lapidou.", 49.16), ("Não fugiu.", 50.36), ("Atravessou.", 51.68)], {}),
 ([("E hoje, quando o mundo", 52.28), ("tenta te ler errado,", 53.48), ("você sorri,", 54.98), ("porque já sabe quem é.", 55.76)], {}),
 ([("Nij.", 57.2, "big"), ("Nova.", 58.36, "big"), ("Inteira.", 59.26, "big")], dict(burst_at=[57.2])),
 ([("Ouro de trás pra frente.", 59.94), ("Mulher.", 61.82, "big"), ("do jeito que sempre foi.", 62.42)], dict(fx="heart", burst_at=[61.82])),
 ([("♥", 65.0, "big")], dict(fx="burst", final=True)),
]
cards = []
for i, (ls, extra) in enumerate(B):
    start = ls[0][1] + D
    nxt = B[i + 1][0][0][1] + D if i + 1 < len(B) else start + 4.5
    c = dict(lines=[l[0] for l in ls], line_starts=[l[1] + D - 0.15 for l in ls],
             line_big=[len(l) > 2 for l in ls], start=start - 0.15, end=nxt - 0.55)
    c.update({k: v for k, v in extra.items() if k != "burst_at"})
    if "burst_at" in extra: c["burst_at"] = [x + D for x in extra["burst_at"]]
    cards.append(c)
json.dump(cards, open("cartelas.json", "w"), ensure_ascii=False, indent=1)
print("fim", cards[-1]["end"])

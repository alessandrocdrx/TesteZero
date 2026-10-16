"""Roteiro: cartelas com tempos (ritmo de leitura). Saída: cartelas.json"""
import json
B = [
 dict(lines=["Para você."], kind="big", italic=True, fx="burst"),
 dict(year="1999", lines=["Uma mulher chamada", "Monica Helms", "criou uma bandeira."]),
 dict(lines=["Azul claro.", "Rosa.", "E branco no meio."]),
 dict(lines=["E explicou:", "de qualquer lado", "que você a hasteie,", "ela estará sempre certa."], fx="flip"),
 dict(lines=["Assim como você."], kind="big", italic=True),
 dict(year="1969", lines=["Em Stonewall,", "Marsha P. Johnson", "e Sylvia Rivera", "estavam na linha de frente."]),
 dict(lines=["O “P” de Marsha", "queria dizer", "“Pay It No Mind”:", "não dê ouvidos."]),
 dict(year="2004", lines=["Mulheres trans e travestis", "levaram ao Congresso Nacional", "a campanha", "“Travesti e Respeito”."]),
 dict(lines=["Nasceu o 29 de janeiro:", "Dia Nacional da", "Visibilidade Trans."]),
 dict(year="2022", lines=["Erika Hilton e Duda Salabert", "foram eleitas as primeiras", "deputadas federais trans", "do Brasil."]),
 dict(lines=["Cada uma delas", "um dia foi uma menina", "que o mundo tentou", "ler errado."]),
 dict(lines=["E cada uma", "escreveu a própria história."]),
 dict(lines=["Agora é a sua vez."], kind="big", italic=True, fx="burst"),
 dict(lines=["O azul:", "o céu que é seu", "por direito."]),
 dict(lines=["O rosa:", "a coragem", "que floresce."]),
 dict(lines=["O branco:", "a página que só você", "pode escrever."]),
 dict(lines=["Você não é", "exceção."], kind="big"),
 dict(lines=["Você é", "continuação."], kind="big", fx="burst"),
 dict(lines=["Você é linda."], kind="big", fx="heart"),
 dict(lines=["Você é forte."], kind="big", fx="heart"),
 dict(lines=["Você é mulher."], kind="big", fx="heart"),
 dict(lines=["E de qualquer lado", "que o mundo olhe…"], fx="flip"),
 dict(lines=["você está certa."], kind="big", italic=True, fx="burst"),
 dict(lines=["Com amor. ♥"], kind="big", italic=True, fx="burst"),
 dict(lines=["Pesquise com carinho:", "Monica Helms", "Marsha P. Johnson", "Sylvia Rivera", "29 de janeiro", "Erika Hilton", "Duda Salabert"], kind="end"),
]
t = 1.5; out = []
for b in B:
    words = sum(len(l.split()) for l in b["lines"]) + (1 if b.get("year") else 0)
    d = {"big": 3.4, "end": 7.0}.get(b.get("kind"), 1.4 + words / 2.6)
    if b.get("fx") == "heart": d = 2.6
    out.append(dict(b, start=round(t, 2), end=round(t + d, 2))); t += d + 0.7
json.dump(out, open("cartelas.json", "w"), ensure_ascii=False, indent=1)
print("duração", round(t + 2.5, 1))

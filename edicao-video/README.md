# Edição "Voa nas asas do vento"

**Versão principal: `calmo.py`.** É o take dela inteiro, sem cortes na música, sem filtro e com a cor original.
- Tradução poética em PT-BR, com a letra em russo em cima, em serifa de cinema (Cormorant Garamond).
- Uma linha de contexto na abertura.
- Uma única virada no clímax: a legenda some, as bordas escurecem e a câmera se aproxima no máximo 7%.
- Créditos no final.

## Versão "mundo" (`mundo.py`): a mais ousada

O vídeo começa no quarto real dela. Na primeira palavra, o quarto se dissolve numa pintura, e a cada verso
ela canta dentro de um novo quadro russo do século XIX (gerados por IA no estilo de Kuindzhi, Levitan e
Shishkin, em `cenarios/`). No sorriso final, o sonho acaba e ela volta para o quarto.

| Verso | Cenário | Movimento e efeitos |
|---|---|---|
| "Voa nas asas do vento" | Estepe sob céu de vento | panorâmica da esquerda para a direita, poeira de luz |
| "onde te cantávamos livres" | Nascer do sol sobre o rio | pássaros voando **atrás** dela |
| "o sol brilha… banhando de luz" | Cáucaso dourado | raios de sol na pintura |
| "as rosas se abrem" | Vale de rosas | pétalas atrás e na frente dela |
| "rouxinóis cantam" | Floresta de Shishkin | brilhos entre as árvores |
| Só a voz (clímax) | Noite de luar no rio | a lua ao lado dela, partículas que respiram com a voz |
| Refrão final → sorriso | Estepe → quarto real | o sonho termina |

Técnica: ela é recortada quadro a quadro com o MediaPipe (segmentação multiclasse + máscara fixa do
microfone), a borda é refinada com filtro guiado, e os fios de cabelo são descontaminados. O fundo do
quarto visto através deles é estimado localmente e trocado pela pintura. Onde ela é sólida, o pixel
continua exatamente o original.

## Versão com efeitos ligados à letra (`efeitos.py`)

`analisar.py` lê o vídeo e o áudio e gera, quadro a quadro, três dados: onde está o rosto dela, quando ela
sorri e a energia da voz. `efeitos.py` usa isso para:

| Letra / momento | Efeito | Reage a |
|---|---|---|
| "Voa nas asas do vento" | Poeira luminosa levada pelo vento, com rajada em "ветра" | volume da voz |
| "onde te cantávamos livres" | Pássaros cruzam o céu acima dela e sobem em "свободно" | tempo da palavra |
| "o sol brilha… banhando de luz" | Raios de sol suaves do alto, que florescem em "солнце" | volume da voz |
| "as rosas se abrem" | Pétalas caem pelas laterais, com uma chuva em "розы" | sorriso dela |
| "rouxinóis cantam" | Brilhos verde-dourados piscam nas bordas | volume da voz |
| Só a voz (clímax) | Partículas de luz sobem e respiram com o canto | volume da voz |
| Quando ela sorri | Os cantos da tela esquentam | sorriso dela |
| Palavra-chave da legenda | Fica dourada quando ela canta a palavra em russo | tempo da palavra |

Uma máscara que acompanha o rosto dela quadro a quadro impede que qualquer efeito toque nele.

As versões `mv.py` (MV pop) e `viral.py` (corte TikTok) ficaram como experimentos anteriores.

## Experimentos anteriores: reel + story

Edição em estilo de MV pop/K-pop a partir do vídeo a cappella de @kvashenayakto.
**Regra do projeto:** a imagem e a voz dela não são alteradas. Nada de filtro no rosto,
e o áudio é copiado bit a bit. Toda a edição é enquadramento, cortes e camadas por cima.

## Como rodar

```bash
./preparar.sh "https://www.tiktok.com/@kvashenayakto/video/7562654671328890124"
./renderizar.sh          # gera saida/reel.mp4 (85 s), saida/story.mp4 (15 s) e saida/tiktok_viral.mp4 (~40 s)
PREVIEW="0.8,20,53" python3 mv.py entrada/v.mp4 previa   # confere quadros sem renderizar tudo
```

## Camadas da edição (tudo em `mv.py`)

| Camada | O que faz | Onde ajustar |
|---|---|---|
| Gancho (0–2,4 s) | "Ela cantou uma ópera russa de 1890, só com a voz." | `hook` |
| Câmera | Cortes de enquadramento (aberto, médio, close) em cada frase, com movimento lento | `SHOTS` |
| Entradas de seção | Zoom rápido + flash + separação de cor por 4 quadros | `SECTION_HITS` |
| Contexto | Cartões com a ópera de Borodin e a história da canção | `CONTEXT` |
| Selo do nome | Apresentação dela no estilo de grupo de K-pop | `nametag_sprite` |
| Legendas | Letra original em russo + PT-BR em karaokê palavra por palavra | `LYRICS` |
| Balões de reação | Estilo programa de variedades coreano ("NO PONTO!", "ARREPIOU") | `STICKERS` |
| Telas divididas | Três telas e quadro dentro de quadro | `SPLIT3`, `FRAME_IN_FRAME` |
| Clímax | Faixas de cinema + brilhos + luz dourada | `LETTERBOX`, `Sparkles` |
| Atmosfera | Luzes coloridas só nas bordas (máscara protege o rosto) | `EDGE_MASK` |
| Final | Título, créditos e chamada "Qual parte te arrepiou?" | `ENDCARD` |

Antes de postar, troque `@SEU_PERFIL` pelo seu @ e peça autorização à criadora original.

## Corte viral TikTok (`viral.py`, ~40 s)

- Trechos escolhidos nas respirações dela (`SEGMENTS`): abertura → sorriso → clímax → refrão.
- O vídeo termina na mesma frase em que começa ("voa nas asas do vento"), então o loop fica natural.
- Gancho em caixa de texto no estilo do TikTok + "espera o 0:22", que segura a atenção até o clímax.
- Legenda palavra por palavra no estilo CapCut (Montserrat Black, palavra ativa em amarelo).
- Cortes de câmera a cada ~2 s, zoom contínuo até o clímax, "AQUI." no ponto alto.
- Chamada final "salva pra ouvir de novo" (salvamentos pesam no algoritmo) + crédito da voz.

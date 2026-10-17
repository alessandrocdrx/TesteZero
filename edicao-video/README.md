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

**Câmera virtual (o que tira o vídeo do estático):**
- A cada meia frase, o enquadramento muda (aberto → médio → close), com "snap zoom" de 0,45 s e drift de câmera na mão (`SHOTS`).
- Parallax 2.5D: a pintura se move 1,8× mais que ela, então o fundo ganha profundidade.
- A troca de mundo é um "dolly zoom": o quadro antigo passa correndo pela câmera, com blur radial e flash quente, e o novo se assenta. Ela não muda de tamanho nessa hora.
- No clímax só de voz, um único push contínuo de 14 s, do plano aberto ao close.
- O quadro respira com a voz dela, e as legendas sobem para o lugar.

**Sem cara de chroma key:** não há recorte duro. Perto dela, o quarto real continua: o cabelo fica sempre sobre o
fundo verdadeiro, mas a parede pega a cor e a luz locais da pintura (razão das médias locais), e a pintura
assume o fundo a uma distância irregular, pictórica (`HALO`).

**Primeiro plano ligado à letra (`frente.py`):** os elementos perto da lente são desfocados (profundidade de campo).
| Verso | Na frente dela |
|---|---|
| "vento" | folhas e sementes sopradas pela lente, as maiores na rajada de "ветра" |
| "livres" | pássaros grandes passam rente à câmera em "свободно", penas caindo |
| "o sol brilha… de luz" | lens flare anamórfico saindo do sol pintado, pico em "солнце" e "светом" |
| "as rosas se abrem" | pétalas grandes desfocadas caem na frente da lente, chuva em "розы" |
| "rouxinóis… matas verdes" | olhamos por entre galhos; vaga-lumes e dois rouxinóis passam |
| só a voz, sob a lua | névoa do rio rola na frente dela e brilha com a voz |

**Objetos 3D (`Depth3D` em `frente.py`):** folhas, penas, pétalas e pontos de luz giram em 3D (rotação nos três
eixos, dobra central com sombreamento por normal, verso mais pálido). Cada um tem profundidade: os de z < 1
passam entre a lente e ela (maiores, mais rápidos, desfocados) e os de z > 1 ficam dentro da pintura, atrás
dela. Cada enxame reage à palavra da letra (rajada em "ветра", "свободно", "солнце", "розы").

**Para celular:** legenda grande (96 px) que quebra em duas linhas e fica longe dos botões do TikTok/Reels.
Os @ de @kvashenayakto e @alessandrocdrx flutuam devagar pelo quadro, sem passar pelo rosto, e trocam de faixa a
cada 12 s, para um repost não conseguir cortar ou cobrir o crédito.
Os objetos do quarto (cadeira, flores, apanhador de sonhos) nunca aparecem (`clutter`).

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

Ciclo rápido de revisão da versão "mundo": prancha de quadros, depois um trecho curto, e o vídeo inteiro só no fim.
```bash
python3 recorte.py entrada/v.mp4 modelos/selfie_multiclass.tflite entrada/recorte     # uma vez só
export MATTE_CACHE=entrada/recorte
PREVIEW="5.6,18.9,36,51,58,70" python3 mundo.py entrada/v.mp4 entrada/analise.npz cenarios modelos/selfie_multiclass.tflite previa
CLIP="48,58" python3 mundo.py entrada/v.mp4 entrada/analise.npz cenarios modelos/selfie_multiclass.tflite trecho.mp4
```

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

Antes de postar, peça autorização à criadora original.

## Corte viral TikTok (`viral.py`, ~40 s)

- Trechos escolhidos nas respirações dela (`SEGMENTS`): abertura → sorriso → clímax → refrão.
- O vídeo termina na mesma frase em que começa ("voa nas asas do vento"), então o loop fica natural.
- Gancho em caixa de texto no estilo do TikTok + "espera o 0:22", que segura a atenção até o clímax.
- Legenda palavra por palavra no estilo CapCut (Montserrat Black, palavra ativa em amarelo).
- Cortes de câmera a cada ~2 s, zoom contínuo até o clímax, "AQUI." no ponto alto.
- Chamada final "salva pra ouvir de novo" (salvamentos pesam no algoritmo) + crédito da voz.

# Edição "Voa nas asas do vento": reel + story

Edição em estilo de MV pop/K-pop a partir do vídeo a cappella de @kvashenayakto.
**Regra do projeto:** a imagem e a voz dela não são alteradas. Nada de filtro no rosto,
e o áudio é copiado bit a bit. Toda a edição é enquadramento, cortes e camadas por cima.

## Como rodar

```bash
./preparar.sh "https://www.tiktok.com/@kvashenayakto/video/7562654671328890124"
./renderizar.sh          # gera saida/reel.mp4 (85 s) e saida/story.mp4 (15 s)
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

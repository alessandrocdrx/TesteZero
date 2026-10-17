# Ramalho Fogões — anúncio vertical (Reels / TikTok / Shorts)

- **Formato:** 1080×1920, 30 fps, cerca de 30 s. O rascunho sai em 540×960.
- **Tipo:** C, 100% IA. Personagem e voz são criados do zero.
- **Créditos na tela:** @alessandrocdrx
- **Contato:** WhatsApp (41) 98485-1317 · Curitiba e Região

## Regras do tipo C neste projeto

- O técnico é um personagem inventado. Não é cópia de nenhuma pessoa real.
- O nome e o logo "Ramalho Fogões" aparecem com autorização do dono.
- Não aparece nenhuma marca de fogão (Consul, Fischer etc.) nem o logo do WhatsApp. No lugar do logo vai um ícone de telefone genérico.
- A voz masculina vem da biblioteca do ElevenLabs. Não imita a voz de ninguém.
- Ao postar, marque o vídeo como **conteúdo gerado por IA**. Reels, TikTok e Shorts pedem essa marcação.

## Pipeline com cache

Tudo o que custa dinheiro ou tempo é gerado uma vez só. O resultado fica em `cache/`, registrado em `cache/manifesto.json` com parâmetros, seed e sha256 (veja `cache.py`).

1. **Folha de referência:** o personagem em 4 vistas mais o cenário, com `gemini-3-pro-image`. A opção escolhida fica travada.
2. **Cenas:** feitas com `kling-omni-video` em 9:16 e 5 s cada. Todas usam a folha travada como `reference_images`, com a mesma descrição do personagem (`roteiro.json`).
3. **Narração:** gerada uma vez e travada. As palavras ganham tempo exato por transcrição local (faster-whisper), salvo em `cache/analise.npz`.
4. **Análise local de cada cena:** feita uma vez.
   - Máscara do personagem por quadro (rembg), salva em `cache/recorte/cenaNN/00000.png…`.
   - Caixa do rosto por quadro (OpenCV).
   - Placa do fundo sem o personagem (inpaint), usada para a paralaxe.
5. **Render:**
   - Os efeitos dependem só do tempo `t`.
   - O vídeo é renderizado em 4 pedaços paralelos, unidos com `ffmpeg concat`.
   - A composição é feita em float32, só na área que tem efeito.
   - Há um único encode no final.

## Câmera e profundidade

- **Planos:** cada frase tem o seu (aberto, médio ou fechado). A câmera tem um leve tremor de mão, e o zoom "respira" com a energia da voz.
- **Paralaxe:** a placa do fundo se move 1,8× mais que o personagem.
- **Transições:** dolly-zoom na troca de cena.
- **Camadas:**
  - z < 1 fica na frente do personagem; z > 1 fica atrás, desenhada só onde a máscara não cobre o personagem.
  - O tamanho é proporcional a 1/z, e o desfoque a |1/z − 1| (bokeh).
  - Há névoa atrás, e a luz das chamas entra em *screen blend*.
- **Objetos 3D:** malhas de verdade (toro, cilindro, cone, extrusões), com rotação e sombreado Lambert + especular.
  - As órbitas passam atrás e na frente do técnico.
  - Uma zona de exclusão é a caixa do rosto ampliada em 25%: nenhum objeto entra nela.

## Tabela palavra → efeito

Os tempos exatos saem da narração gerada, com tolerância de ±0,2 s.

| # | Palavra-chave | Efeito 3D | z | Comportamento |
|---|---|---|---|---|
| 1 | "amarela" | Chama 3D amarela tremulando (cone com ruído) | 0,8 | Entra pela esquerda, treme e falha |
| 2 | "falhando" | Faíscas 3D (pequenos tetraedros) | 0,7–1,5 | Explodem do queimador e caem |
| 3 | "acender?" | Ponto de interrogação extrudado | 0,9 | Gira e some |
| 4 | "Ramalho Fogões" | Selo 3D com a chama do logo + palavra GRANDE | 0,9 | Pop no centro-baixo e órbita curta |
| 5 | "Conserto" | Chave inglesa 3D | 0,8 → 1,4 | Orbita o técnico, passa atrás e na frente |
| 6 | "regulagem" | Botão de fogão 3D (cilindro com aleta) | 0,85 | Gira 270° |
| 7 | "limpeza" | Bolhas e brilhos (esferas com especular) | 0,6–2,0 | Sobem em várias profundidades (bokeh) |
| 8 | "conversão de gás" | Botijão 3D | 1,2 | Gira atrás do ombro |
| 9 | "Instalação" | Mangueira e registro 3D | 0,9 | Desliza para o lugar |
| 10 | "industrial" | Anel de 6 chamas azuis 3D | 1,0 | Órbita completa ao redor do técnico |
| 11 | "Chama azul" | Anéis de chama azul (toros) + palavra GRANDE | 0,7 / 1,3 | Dois anéis orbitam em sentidos opostos, com glow em screen |
| 12 | "bem feito" | Check ✔ 3D | 0,85 | Pop com brilho |
| 13 | "Curitiba e Região" | Pino de mapa 3D | 0,9 | Cai e quica |
| 14 | "WhatsApp" | Telefone 3D genérico + número GRANDE | 0,9 | Gira e fixa; o número fica até o fim |

## Legendas e @

- Legenda karaokê (gerador `video_jin/pro/montar.py`): a palavra atual fica destacada em amarelo-chama.
- **Safe zone 9:16:** topo 250 px, base 420 px, laterais 60 px, e a coluna direita (botões do app) fica livre.
- A legenda muda de posição por cena para nunca ficar sobre o rosto.
- O @alessandrocdrx flutua devagar no canto superior esquerdo, dentro da safe zone.

## Bateria de testes (`testes.py`)

1. ~~Vazamento~~: não se aplica ao tipo C.
2. **Integridade:**
   - Consistência do personagem entre cenas: histograma da camisa e cor da pele dentro da máscara.
   - Contact sheet ampliado de mãos e rosto para inspeção.
3. **Áudio:** sem clipping (pico < −1 dBFS), sem estalos (derivada anormal) e duração da trilha = vídeo ± 1 quadro.
4. **Força do 3D:** área ocupada pelos objetos e deslocamento de paralaxe ≥ 1,5% da largura em cada trecho.
5. **Sincronia:** início de cada efeito − tempo da palavra ≤ 0,2 s.
6. **Legendas e @:** caixas dentro da safe zone e sem interseção com a caixa do rosto. Contraste ≥ 4,5:1.
7. **Flicker:** variação de luminância média quadro a quadro abaixo do limite, exceto nos cortes.
8. **Inspeção visual:** recortes ampliados dos piores quadros de cada teste.

## Custo estimado (ElevenLabs)

| Item | Créditos | % do Creator (121 mil) |
|---|---|---|
| Folha de referência (4 opções) | ~4.900 | 4% |
| 6 cenas de 5 s com referência | ~20.400 | 17% |
| Narração | ~300 | 0,3% |
| **Total** | **~25.600** | **~21% (≈ R$ 25 do plano de R$ 120)** |

Cabe no Creator. No Starter não cabe: sobram cerca de 7 mil créditos.

## Fluxo de revisão

1. ✅ Este plano + tabela palavra → efeito. **A folha de referência só é gerada depois do seu ok.**
2. Relatório dos testes + contact sheet.
3. Clipe curto do trecho mais difícil: "Chama azul", com os anéis passando atrás e na frente do técnico.
4. Vídeo completo após aprovação.

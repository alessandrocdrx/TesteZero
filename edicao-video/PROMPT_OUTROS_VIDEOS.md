# Prompt reutilizável: edição com cache de recorte e 3D em profundidade

Copie o bloco abaixo para um novo pedido. Troque o que está entre `<…>`.

```text
Edite o vídeo <arquivo/link> de <@artista> para Reels/TikTok (1080×1920, 30 fps).
Créditos fixos e flutuando: <@artista> e @alessandrocdrx.

REGRAS INVIOLÁVEIS
- Rosto e corpo da pessoa sem filtro, sem retoque, sem deformar. Nada de efeito por cima do rosto.
- Áudio copiado sem recodificar (-c:a copy). Comprove com o MD5 do áudio do original e da saída.
- Nenhum objeto do cômodo original (cadeira, porta, móveis) pode aparecer atrás dela.

PIPELINE COM CACHE (calcular uma vez, reaproveitar sempre)
1. Decodificar o vídeo uma vez. Extrair letra com tempos por palavra, energia da voz e caixas do rosto para analise.npz.
2. Recorte (matte) de todos os quadros uma única vez, salvo em PNG numa pasta de cache (recorte/00000.png…).
   As renderizações seguintes leem o cache (MATTE_CACHE=pasta) e nunca rodam o segmentador de novo.
3. Modelo do cômodo vazio: mediana por pixel dos quadros em que ela não cobre o fundo.
   Gera a placa limpa, os mapas known/seen/reliable e a máscara dos objetos (por exemplo o casco da cadeira) num arquivo quarto.npz.
4. Limpar o recorte com chave de diferença contra a placa limpa, só na borda: o que for igual ao quarto vazio sai.
   Proteger uma elipse no rosto. Refinar a borda com guided filter. O light wrap fica restrito às bordas reais (Sobel no alpha).

3D E PROFUNDIDADE
- Câmera virtual: planos W/M/C sincronizados com as frases, snap ease, leve câmera na mão, zoom de respiração com a voz.
- Paralaxe: o fundo se move cerca de 1,8× mais que ela.
- Transições dolly-zoom entre cenários a cada mudança de verso.
- Camadas por profundidade z. Partículas com z<1 ficam na frente dela e z>1 atrás.
  Tamanho ∝ 1/z, desfoque ∝ |1/z − 1| (bokeh/DOF), luz em screen blend e névoa atrás.
- Objetos 3D de verdade: rotação 3D, sombreado nas duas faces, nervura, verso mais claro.
  Alguns objetos ORBITAM ao redor dela, passando atrás e depois na frente, e nunca cruzam o rosto.
- Cada palavra-chave da letra dispara o seu objeto no tempo exato da palavra (±0,2 s). Exemplos:
  vento → redemoinho de folhas, pássaros → bando vindo de trás até a câmera, sol → raios volumétricos com poeira,
  rosas → rosas desabrochando em 3D nos cantos + vórtice de pétalas, noite/lua → espiral de luar que cresce com a voz.

LEGENDAS
- Letra original + tradução PT-BR, grandes, palavra atual destacada, dentro da safe zone do TikTok/Reels.
  Nunca sobre o rosto e longe da UI lateral e inferior do app.

BATERIA DE TESTES AUTOMÁTICOS (só entregue se TODOS passarem; se algum falhar, corrija e rode de novo)
1. Vazamento do cômodo: ≤150 px perceptíveis por quadro em 100% dos quadros, com mapa de calor dos piores.
2. Integridade: alpha removido no rosto ≈ 0 e quase nada removido no corpo. Rosto da saída = rosto da fonte deformada.
3. Voz: MD5 do áudio idêntico.
4. Força do 3D: cobertura e contraste mínimos por verso (o efeito tem que ser visível no celular).
5. Sincronia: pico de cada efeito a até ±0,2 s da sua palavra.
6. Legendas e @: dentro da safe zone, legíveis, fora do rosto.
7. Flicker: variação quadro a quadro do alpha e do fundo abaixo do limite.
8. Inspeção visual: recortes ampliados dos piores quadros de cada teste.

VELOCIDADE
- Decodificação em streaming. Composição em float32, em meia resolução só na caixa onde há efeito.
- Efeitos sem estado (dependem só de t) para renderizar em 4 pedaços paralelos, unidos com ffmpeg concat.
- Uma única passada de encode. Rascunho em 540×960 para revisão.

FLUXO DE REVISÃO (não renderize o vídeo inteiro antes do meu ok)
1. Relatório dos testes + contact sheet de quadros-chave.
2. Clipe curto (CLIP="a,b") do trecho mais difícil.
3. Vídeo completo só depois da minha aprovação.

Faça commit e push dos scripts. Lembre-me de pedir permissão a <@artista> antes de postar.
```

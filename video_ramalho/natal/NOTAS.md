# Vídeo de Natal — Ramalho Fogões (notas para continuar)

## Pedido do cliente
- Vídeo vertical 9:16 (Reels), 30 s, 1080×1920.
- Personagem: Técnico Marcos (caricatura 3D, já autorizada) + Papai Noel.
- Cenário de Natal (árvore, sala decorada), **sem cenário parecido com a cozinha do vídeo anterior**.
- **Cenário parado** (câmera fixa), sem objetos andando sozinhos.
- Efeito 3D de profundidade (ainda não feito neste vídeo).
- Narração nova de Natal (voz Gabriel, ElevenLabs), trilha natalina.
- Legendas karaokê centralizadas, fora do rosto.
- Cartão final: RAMALHO FOGÕES, Técnico Marcos, WhatsApp (41) 98485-1317 e Facebook /ramalhofogoes juntos.
- Crédito "Edição: @alessandrocdrx" pequeno e flutuando embaixo, sem destaque.

## Regras
- Não publicar fotos do Marcos nem de familiares em repositório público.
- Sem logos de marcas de terceiros (Rinnai, Bosch, Brastemp etc.), sem logo de WhatsApp nem de Facebook.
- Marcar como conteúdo gerado por IA ao postar.
- Horários em Brasília (UTC−3).
- Não gerar versões extras: custa créditos.

## Estado atual
- Narração de Natal: `cache/natal/narracao_natal.mp3` (22,2 s), transcrição em `narracao_natal.json`.
- Trilha: `cache/natal/musica_natal.mp3`, sintetizada localmente (Jingle Bells, 30 s). Não é uma trilha profissional.
- Clipes Kling Omni (ElevenLabs), 16:9, 5 s cada: `cache/natal/c01.mp4` a `c06.mp4`. **Problemas:** rosto do Marcos duplicado em alguns, cenário pouco natalino quando cortado para 9:16.
- `montar.py`: monta o vídeo em 9:16, com objetos 3D, legendas, cartão e trilha. Último render enviado: versão 16:9 (`Ramalho_Natal_1080p.mp4`), que ficou ruim para o cliente.
- **Não aprovado.** Não postar nenhuma versão atual.

## O que falta
1. Clipes novos em 9:16, com cenário de Natal forte e um Marcos só em cena. Opção: gerar no Kling (conector do Kling, se disponível em uma sessão nova) ou o usuário gera e envia os .mp4.
2. Efeito 3D de profundidade no cenário (precisa de mapa de profundidade dos clipes novos, ver `profundidade.py`).
3. Render final e checagem visual antes de enviar.

## Prompts usados (cenário parado, 9:16, sem texto, sem logos)
Ver o histórico de gerações no canvas ElevenLabs, flow `xxyyW8QMbbygGFQZluUg`.

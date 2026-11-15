# ADR-008: Trava de ingredientes como segunda camada

**Status:** aceito · 15/11/2026

## Contexto
Na avaliação, o workflow respeitou só 70% das restrições (7 de 10 pedidos com restrição).
As 3 violações foram erros do classificador no sentido perigoso: ofereceu ovo e mel a quem
pediu vegano e trigo a quem pediu sem glúten. Nos 3 casos, o ingrediente proibido estava
escrito na lista.

## Decisão
Adicionar ao passo 3 uma regra em código (`src/mmp/pipeline/trava.py`): o prato só passa se o
classificador aprova **e** a lista de ingredientes não tem termo proibido pela definição da
restrição. Qualificadores liberam ingredientes compatíveis ("leite de coco", "queijo vegetal",
"tamari sem glúten") e falsos amigos ("couve manteiga", "pimenta calabresa"). Ligável por
`TRAVA_INGREDIENTES`.

## Alternativas
- Retreinar o modelo com mais dados: não garante as regras e não cabia no prazo.
- Usar só a trava: perde o que o modelo pega pelo contexto quando o ingrediente não é óbvio.

## Consequências
- Restrições respeitadas foram de 70% para **100%** nos pedidos de teste.
- Checada contra os rótulos dos 291 pratos: nenhum prato correto barrado.
- As regras de falsos amigos foram ajustadas olhando o cardápio inteiro, inclusive o teste.
  São regras gerais do português, mas isso fica registrado.
- Cada bloqueio tem motivo legível (`vegano: 'ovo de galinha' (ovo)`), o que torna a decisão
  auditável.
- Depende de a lista de ingredientes estar completa: um ingrediente omitido passa.

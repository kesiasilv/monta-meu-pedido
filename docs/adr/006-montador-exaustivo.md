# ADR-006: Montador por busca exaustiva, com margem de relevância

**Status:** aceito · 15/11/2026

## Contexto
O carrinho precisa respeitar o orçamento sempre, contando a taxa de entrega, e ter itens de um
único restaurante.

## Decisão
Agrupar os candidatos por restaurante e testar todas as combinações de 1 prato principal + 0 ou
1 bebida ou sobremesa. Descartar as que passam do orçamento ou do tempo e escolher a de maior
pontuação (relevância da busca + 0,10 por preferência atendida + 0,05 por incluir um extra).

Só entram pratos principais com relevância até 0,05 abaixo do mais relevante
(`MARGEM_RELEVANCIA`).

## Por que a margem
Em teste real, "poke até R$ 45" devolveu um sundae: nenhum poke cabia com a taxa, e o montador
pegava qualquer coisa que coubesse. Com a margem, se o prato pedido não cabe, o assistente
avisa e sugere aumentar o orçamento.

## Alternativas
Deixar o LLM escolher; algoritmo guloso; programação linear.

## Consequências
- Com no máximo 30 candidatos são menos de 1.000 combinações: instantâneo e sempre correto.
- O orçamento foi respeitado em 100% dos carrinhos da avaliação.
- Não serve para carrinhos grandes (fora do escopo).

# ADR-001: Workflow em vez de agente autônomo

**Status:** aceito · 15/11/2026

## Contexto
O assistente sempre segue a mesma sequência: entender o pedido, buscar pratos, filtrar
restrições, montar o carrinho e explicar. Orçamento e restrições alimentares são regras
críticas. Um agente autônomo decide os passos em tempo de execução e pode pular uma checagem,
repetir chamadas ou inventar um prato.

## Decisão
O código define a ordem dos 5 passos (`src/mmp/pipeline/workflow.py`). O LLM é chamado só para
interpretar o texto do cliente (passo 1) e escrever a explicação (passo 5). Todos os números da
resposta (preços, total, tempo) são gerados em código.

## Alternativas
- **Agente com tool calling:** flexível, mas imprevisível e mais caro.
- **Multiagente** (intérprete, montador, revisor): mais complexidade sem ganho para uma
  sequência fixa.

## Consequências
- Comportamento previsível e testável: cada passo é uma função com teste próprio.
- Duas chamadas de LLM por pedido; latência medida de ~3 s.
- Menos flexível para pedidos fora do padrão.
- Os passos 2 a 4 continuam utilizáveis como ferramentas, se uma versão com agente for comparada
  no futuro.

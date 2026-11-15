# ADR-004: Dados sintéticos com revisão por amostragem

**Status:** aceito · 15/11/2026

## Contexto
Não há dataset público de cardápios brasileiros com tags alimentares, e coletar dados de apps
de delivery fere os termos de uso.

## Decisão
Gerar cardápios com o LLM, validar cada item com Pydantic, aplicar regras de consistência
("vegano implica vegetariano e sem lactose") e revisar uma amostra de 50 pratos.

## Alternativas
- Rotular dados reais à mão: inviável em um dia.
- Coletar dados de apps: viola termos de uso.

## Consequências
- 291 pratos de 21 restaurantes (a cota do LLM interrompeu a geração em 21 de 30 categorias).
- A revisão foi feita por um segundo modelo (Claude), não por uma pessoa: 92% dos pratos sem
  nenhum erro, e os 4 erros foram conservadores.
- Os dados são mais limpos que cardápios reais e têm pistas explícitas nos nomes ("Vegano",
  "Fit"), o que favorece modelos simples.
- Os rótulos vêm do Gemini, o que favorece o Gemini zero-shot na comparação.
- Os tempos de entrega gerados ficaram todos entre 35 e 45 minutos.

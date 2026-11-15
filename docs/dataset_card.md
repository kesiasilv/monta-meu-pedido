---
language: pt
license: cc-by-4.0
task_categories: [text-classification]
tags: [food, multi-label-classification, synthetic, portuguese]
size_categories: [n<1K]
---

# Cardápios sintéticos de delivery com tags alimentares (pt-BR)

291 itens de cardápio (pratos, bebidas e sobremesas) de 21 restaurantes fictícios brasileiros,
cada um com nome, descrição, ingredientes, preço e 7 tags alimentares. Criado para o projeto
[Monta Meu Pedido](https://github.com/kesiasilv/monta-meu-pedido).

## Conteúdo

| Arquivo | O que tem |
|---|---|
| `pratos.json` | 291 itens com `id`, `restaurante_id`, `nome`, `descricao`, `ingredientes`, `preco`, `tipo`, `tags` |
| `restaurantes.json` | 21 restaurantes com `categoria`, `taxa_entrega` e `tempo_entrega_min` |
| `train.jsonl`, `val.jsonl`, `test.jsonl` | Divisão 203 / 44 / 44, estratificada pelas tags (seed 42) |
| `revisao_50.csv` | Amostra de 50 itens revisados |

## Tags

| Tag | Definição |
|---|---|
| `vegano` | Nenhum ingrediente de origem animal (carne, peixe, ovo, leite, mel) |
| `vegetariano` | Sem carne, peixe ou frutos do mar; pode ter ovo e laticínios |
| `sem_lactose` | Sem leite e derivados |
| `sem_gluten` | Sem trigo, cevada, centeio ou aveia comum |
| `fit` | Leve: grelhado, cozido ou cru, sem fritura, até ~600 kcal estimadas |
| `picante` | Pimenta ou molho apimentado como característica do prato |
| `doce` | Sabor predominante doce |

## Como foi criado

1. O `gemini-3.8-flash` gerou um restaurante por categoria (14 itens cada), com as definições
   das tags no prompt e temperatura 0,9.
2. Cada item foi validado com Pydantic; duplicados foram descartados; a regra "vegano implica
   vegetariano e sem lactose" foi aplicada.
3. 50 itens sorteados foram revisados por um segundo modelo (Claude) com as mesmas definições:
   92% sem nenhum erro; os 4 erros foram conservadores (restrição atendida marcada como não
   atendida).

## Limitações

- Sintético e de um único gerador: menos variado e mais limpo que cardápios reais, com pistas
  explícitas nos nomes ("Vegano", "Fit").
- 21 das 30 categorias planejadas (limite diário de cota); tempos de entrega entre 35 e 45 min.
- Rótulos gerados por LLM e revisados por amostragem, não por especialistas em nutrição.
- **Não use para decisões sobre alergias.**

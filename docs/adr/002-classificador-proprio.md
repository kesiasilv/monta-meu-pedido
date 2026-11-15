# ADR-002: Classificador próprio para as restrições

**Status:** aceito · 15/11/2026

## Contexto
Para filtrar pratos por restrição, é preciso saber as tags de cada prato. Chamar um LLM para
classificar cada prato a cada pedido adiciona custo por uso e latência.

## Decisão
Fine-tuning do `neuralmind/bert-base-portuguese-cased` (BERTimbau) para classificação
multi-label das 7 tags, publicado em
[KesiaSilva/bertimbau-tags-pratos](https://huggingface.co/KesiaSilva/bertimbau-tags-pratos).
Um baseline TF-IDF e um LLM zero-shot servem de comparação.

## Alternativas
- **LLM zero-shot:** mais preciso no teste (F1 macro ~0,94), mas ~1.000x mais lento que o
  baseline e com custo por uso.
- **Baseline TF-IDF:** F1 macro 0,898 no teste, praticamente empatado com o BERTimbau (0,884).
- **Regras por palavra-chave apenas:** viraram a trava do ADR-008, como segunda camada.

## Consequências
- A rodada 1 de treino (8 épocas, taxa 2e-5) ficou abaixo do baseline na validação. A rodada 2
  (até 20 épocas, taxa 5e-5) foi escolhida pela validação (F1 macro 0,952).
- No teste, o BERTimbau empatou com o baseline. Ele foi mantido no workflow porque a escolha
  segue a validação, e porque foi melhor nas duas restrições com mais ingredientes "escondidos"
  (sem lactose e sem glúten).
- Sozinho, o modelo deixou passar 3 violações em 10 pedidos com restrição, o que motivou o
  ADR-008.

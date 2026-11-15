# Um modelo pequeno substitui um LLM para filtrar restrições alimentares?

**Relatório técnico do projeto Monta Meu Pedido** · Késia Silva · novembro de 2026

## Resumo

Construí um assistente que monta pedidos de comida respeitando orçamento, restrições
alimentares e tempo de entrega. Para decidir se um prato atende a uma restrição, comparei três
classificadores multi-label em 7 tags: um baseline TF-IDF, um BERTimbau ajustado (fine-tuning)
e um LLM zero-shot (Gemini). Em 291 pratos sintéticos, o LLM foi o mais preciso (F1 macro 0,94),
mas ~1.000x mais lento que o baseline e com custo por uso. O BERTimbau (0,884) empatou com o
baseline (0,898). No workflow completo, o modelo sozinho respeitou as restrições em 70% dos
pedidos de teste; com uma trava de ingredientes escrita em código a partir das definições das
tags, chegou a 100%, sem barrar nenhum prato correto do cardápio.

## 1. Pergunta e contexto

Escolher comida exige cruzar orçamento, restrições, tempo e vontade. O ponto técnico central é
saber se um prato atende a uma restrição, o que exige entender a descrição e os ingredientes.
Um LLM faz isso bem, mas custa por chamada e é lento para rodar em muitos pratos.

**Pergunta A:** um classificador pequeno, treinado para a tarefa, substitui um LLM zero-shot?
**Pergunta B:** um workflow com LLM, busca semântica e esse classificador respeita as regras do
pedido?

## 2. Dados

| Item | Valor |
|---|---|
| Fonte | Sintética, gerada pelo `gemini-3.8-flash`, um restaurante por chamada |
| Tamanho | 21 restaurantes, 291 pratos (189 principais, 60 bebidas, 42 sobremesas) |
| Tags | `vegano`, `vegetariano`, `sem_lactose`, `sem_gluten`, `fit`, `picante`, `doce` |
| Validação | Pydantic em cada item; 0 inválidos, 3 duplicados descartados |
| Divisão | Estratificada multi-label: 203 treino / 44 validação / 44 teste, seed 42 |
| Revisão | 50 pratos conferidos por um segundo modelo (Claude): **92% sem erro** |

A geração parou em 21 de 30 categorias pelo limite diário do plano gratuito (20 requisições).
Os 4 erros encontrados na revisão foram conservadores: o Gemini disse que o prato não atendia a
uma restrição que os ingredientes atendiam. Detalhes em `data/processed/revisao_notas.md`.

## 3. Método

**Classificadores**
- **Baseline:** TF-IDF (1 e 2-gramas) + regressão logística, uma por tag.
- **BERTimbau:** fine-tuning de `neuralmind/bert-base-portuguese-cased`, perda BCEWithLogits,
  128 tokens, lote 16, weight decay 0,01, early stopping pelo F1 macro da validação.
- **LLM zero-shot:** `gemini-3.5-flash-lite` com as definições das tags no prompt, 10 pratos por
  chamada.

**Protocolo**
- Toda escolha (limiar por tag, épocas, taxa de aprendizado) foi feita na validação.
- O teste foi usado só na avaliação final.
- Os três modelos receberam exatamente os mesmos 44 pratos de teste.

**Duas rodadas do BERTimbau, decididas pela validação**

| Rodada | Épocas | Taxa | F1 macro validação | F1 macro teste |
|---|---|---|---|---|
| 1 | até 8 | 2e-5 | 0,853 | 0,795 |
| 2 | até 20 (parou na 11ª; melhor: 9ª) | 5e-5 | **0,952** | 0,884 |

A rodada 1 já ficava abaixo do baseline na validação (0,853 contra 0,890). Com 203 exemplos e
lote 16, ela fez só ~100 atualizações de pesos. A rodada 2 foi publicada.

## 4. Resultados: classificadores (pergunta A)

| Modelo | F1 micro | F1 macro | Acerto exato | Latência (ms/prato) | Custo por uso |
|---|---|---|---|---|---|
| Baseline TF-IDF | 0,907 | 0,898 | 0,568 | 0,1 | não (CPU) |
| BERTimbau | 0,909 | 0,884 | 0,545 | 34 (CPU) | não (CPU) |
| LLM zero-shot | 0,929 | **0,940** | 0,614 | 115 (em lotes) | sim |

| Tag | Baseline | BERTimbau | LLM zero-shot |
|---|---|---|---|
| vegano | 0,950 | 0,909 | 1,000 |
| vegetariano | 0,983 | 0,983 | 0,863 |
| sem_lactose | 0,873 | 0,915 | 0,963 |
| sem_gluten | 0,867 | **0,912** | 0,889 |
| fit | 0,815 | 0,769 | 0,867 |
| picante | 0,833 | 0,769 | 1,000 |
| doce | 0,963 | 0,929 | 1,000 |

Em duas execuções da avaliação, o F1 macro do LLM variou entre 0,938 e 0,940: o zero-shot não
é determinístico.

## 5. Análise

**O baseline é forte porque os dados facilitam.** O gerador escreve pistas explícitas nos nomes
("Feijoada Vegana", "Fit Burger"), e um modelo que conta palavras as encontra.

**O LLM está, em parte, concordando consigo mesmo.** Os rótulos de referência foram gerados pelo
Gemini, e o zero-shot também é um Gemini. Esse viés foi previsto antes do experimento e limita a
conclusão de que o LLM é "o mais preciso".

**A validação superestimou o BERTimbau** (0,952 contra 0,884 no teste). Os limiares por tag
foram escolhidos nos mesmos 44 pratos da validação e se ajustaram a eles. É o motivo de o teste
ficar guardado para o fim.

**Com 44 pratos de teste, diferenças de ~0,01 a 0,02 são ruído.** Em `picante` são 7 exemplos:
um erro muda o F1 em mais de 0,1.

**Resposta à pergunta A:** neste cenário, um modelo local (baseline ou BERTimbau) chega perto do
LLM sem custo por uso e com latência muito menor. A vantagem do BERTimbau sobre o baseline
aparece nas restrições com ingredientes menos óbvios (sem glúten: 0,912 contra 0,867; sem
lactose: 0,915 contra 0,873), mas não no F1 macro.

## 6. Resultados: workflow (pergunta B)

30 pedidos com regras conhecidas: 10 simples, 10 com restrições, 5 sem orçamento e 5
impossíveis. As restrições são conferidas contra os rótulos de referência, não contra o que o
classificador previu.

| Métrica | Rodada 1 (só o modelo) | Rodada 2 (modelo + trava) |
|---|---|---|
| Status correto | 100% | 97% |
| Orçamento e restrições entendidos pelo LLM | 100% | 100% |
| Orçamento respeitado | 100% | 100% |
| Tempo respeitado | 100% | 100% |
| **Restrições respeitadas** (10 pedidos com restrição) | **70%** | **100%** |
| Latência p50 / p95 | 3,1 s / 6,8 s | 3,0 s / 3,6 s |

**As 3 violações da rodada 1**

| Pedido | Item oferecido | Restrição violada | Ingrediente |
|---|---|---|---|
| vegano e sem glúten | Virado à Paulista Vegetariano | vegano | ovo de galinha |
| sem lactose e sem glúten | Tabule Fresco da Casa | sem glúten | trigo fino para kibe |
| picante e vegano | Suco de Laranja com Mel | vegano | mel |

Os 3 erros foram no sentido perigoso (oferecer o que não pode) e os 3 ingredientes estavam
escritos na lista. A **trava de ingredientes** (`src/mmp/pipeline/trava.py`) barra pratos com
termos proibidos pela definição de cada restrição, com exceções para qualificadores ("leite de
coco", "queijo vegetal") e falsos amigos ("couve manteiga", "pimenta calabresa"). Conferida
contra os 291 pratos, ela não barrou nenhum prato correto e pegou de 91% a 99% dos não
compatíveis.

A queda de status na rodada 2 veio de um pedido sem restrição em que a interpretação pelo LLM
falhou uma vez; repetido 3 vezes, deu certo nas 3.

## 7. Limitações

- Dados sintéticos, de um único gerador, com pistas explícitas nos nomes.
- 21 de 30 categorias; tempos de entrega concentrados entre 35 e 45 minutos.
- Conjuntos de validação e teste pequenos (44 pratos cada).
- Revisão dos rótulos feita por outro LLM, não por uma pessoa.
- As regras de falsos amigos da trava foram ajustadas olhando o cardápio inteiro.
- 30 pedidos de avaliação escritos por mim, não por usuários reais.
- O custo do LLM depende da tabela de preços vigente; o número exato não foi verificado.

## 8. Próximos passos

- Rotular à mão uma amostra de pratos reais, sem pistas nos nomes, e repetir a comparação.
- Comparar o workflow com um agente autônomo e uma versão multiagente no mesmo laboratório.
- Fine-tuning com LoRA de um LLM pequeno na mesma tarefa.
- Salvar o motivo de cada falha na avaliação.

## 9. Reprodutibilidade

```bash
make setup      # ambiente
make data       # gera, valida e divide (seed 42); precisa de GEMINI_API_KEY
make baseline   # treina o TF-IDF
# BERTimbau: notebooks/01_treino_bertimbau.ipynb no Colab (GPU T4)
make eval       # laboratório completo; resultados em evals/resultados/
```

Modelo: [KesiaSilva/bertimbau-tags-pratos](https://huggingface.co/KesiaSilva/bertimbau-tags-pratos).
Registro completo das decisões e problemas: `docs/diario-de-bordo.md` e `docs/adr/`.

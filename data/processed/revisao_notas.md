# Revisão dos rótulos (amostra de 50 pratos)

**Como foi feita:** os 50 pratos sorteados (seed 42) foram conferidos por um segundo modelo
(Claude), seguindo as definições das tags em `src/mmp/prompts.py`. O critério foi a **lista de
ingredientes** de cada prato, não o que o prato "costuma ter" na vida real.
Isto é uma revisão do tipo *LLM-as-judge*, não uma revisão humana.

**Resultado:** 46 de 50 pratos sem nenhum erro (92%). 4 correções, todas em restrições.

| Prato | Tag | Gemini | Revisão | Motivo |
|---|---|---|---|---|
| p217 Pad See Ew Vegetariano | `sem_lactose` | 0 | 1 | Nenhum laticínio nos ingredientes (ovo não é laticínio) |
| p016 Spicy Tuna Volcano | `sem_gluten` | 0 | 1 | Nenhum trigo, cevada ou shoyu listado |
| p215 Por Piah Tod | `sem_lactose` | 0 | 1 | Nenhum laticínio nos ingredientes |
| p113 Pizza Calabresa Artesanal | `sem_lactose` | 0 | 1 | Nenhum queijo listado (provável omissão do gerador) |

## O que os erros mostram

- **Todos os erros foram no mesmo sentido:** o Gemini disse que o prato **não** atende a restrição
  quando, pelos ingredientes, ele atende. É um erro conservador: na pior das hipóteses o
  assistente deixa de oferecer um prato que serviria, mas nunca oferece um que viola a restrição.
- O Gemini parece usar o "conhecimento de mundo" em vez da lista de ingredientes. Uma pizza
  calabresa real costuma ter queijo, mas a lista gerada não tem. Ou seja, parte do "erro" é uma
  **inconsistência entre ingredientes e rótulo** criada pelo próprio gerador.
- As tags de preferência (`fit`, `picante`, `doce`) e as de dieta (`vegano`, `vegetariano`)
  tiveram 100% de concordância nesta amostra.

## Limitações

- 50 pratos é uma amostra pequena: a taxa real de erro pode ser diferente.
- A revisão foi feita por outro LLM. O ideal é uma pessoa conferir pelo menos uma parte.
- Casos ambíguos de `fit` (ex.: moquecas e curries com leite de coco) foram mantidos como o
  Gemini rotulou.

# ADR-003: Gemini como LLM, atrás de uma interface

**Status:** aceito, revisado no mesmo dia · 15/11/2026

## Contexto
O projeto precisa custar zero e não pode depender de um provedor de LLM.

## Decisão
O código só conhece a interface `LLMClient` (`src/mmp/llm/base.py`). A classe base cuida de
pedir JSON, validar com Pydantic, pedir correção uma vez e repetir erros temporários. Cada
provedor implementa só a chamada (`gemini.py`, `claude.py`). O provedor e o modelo vêm do `.env`.

**Revisão durante a construção:**
- O plano previa `gemini-2.5-flash`, que não está disponível para contas novas (erro 404).
- A geração de dados usou `gemini-3.8-flash`, cujo plano gratuito permite 20 requisições por
  dia. A cota acabou com 21 de 30 restaurantes gerados.
- O workflow e a avaliação usam `gemini-3.5-flash-lite` (500 requisições por dia).

## Alternativas
- Chamar o SDK do Gemini direto no workflow.
- Modelo aberto local (Ollama) ou Gemma pela API, que não aceita system prompt nem modo JSON.

## Consequências
- Trocar de provedor ou de modelo é mudar uma linha do `.env`. Isso foi feito duas vezes durante
  a construção, sem mudar código.
- Erros que não adianta repetir (4xx exceto 429) param na hora; os temporários (429, 5xx, rede)
  são repetidos com espera crescente.
- Um modelo mais forte gerou os dados uma vez; um mais leve roda no dia a dia.

# Monta Meu Pedido

[![CI](https://github.com/kesiasilv/monta-meu-pedido/actions/workflows/ci.yml/badge.svg)](https://github.com/kesiasilv/monta-meu-pedido/actions/workflows/ci.yml)

Assistente de IA que monta pedidos de comida respeitando **orçamento, restrições alimentares e
tempo de entrega**, com um classificador alimentar próprio treinado e publicado no Hugging Face.

> **Cliente:** "Sou celíaca e intolerante a lactose, quero comida japonesa até 70 reais."
>
> **Assistente:** Montei no Haru Sushi & Cozinha Japonesa: Veggie Poke Bowl (R$ 46,00) + Chá
> Verde Sencha Gelado (R$ 11,00). Total R$ 64,90 (entrega R$ 7,90), chega em 40 min.
> Como não levam trigo nem laticínios, a refeição respeita suas restrições.

**Modelo:** [KesiaSilva/bertimbau-tags-pratos](https://huggingface.co/KesiaSilva/bertimbau-tags-pratos) ·
**Dataset:** [KesiaSilva/cardapios-delivery-ptbr](https://huggingface.co/datasets/KesiaSilva/cardapios-delivery-ptbr) ·
**Relatório técnico:** [RELATORIO.md](RELATORIO.md)

## Demonstração

![Demo: três pedidos com o carrinho e os bastidores de cada etapa](docs/demo.gif)

A demo mostra o pedido, a conversa com o assistente, o carrinho montado e os bastidores: o que
o LLM entendeu e quanto tempo levou cada etapa. Para rodar na sua máquina, veja
[Como rodar](#como-rodar) (precisa de uma chave gratuita do Google AI Studio).

O código da demo também está publicado no
[Hugging Face Spaces](https://huggingface.co/spaces/KesiaSilva/monta-meu-pedido), mas o Space
fica pausado: a conta gratuita não tem cota de CPU para mantê-lo rodando.

## Resultados

**Classificadores no conjunto de teste** (7 tags, 44 pratos)

| Modelo | F1 macro | Latência por prato | Custo por uso |
|---|---|---|---|
| Baseline TF-IDF | 0,898 | 0,1 ms | não |
| **BERTimbau ajustado (este projeto)** | 0,884 | 34 ms (CPU) | não |
| Gemini zero-shot | 0,940 | 115 ms | sim |

**Workflow em 30 pedidos de teste**

| | Só o modelo | Modelo + trava de ingredientes |
|---|---|---|
| Restrições respeitadas | 70% | **100%** |
| Orçamento e tempo respeitados | 100% | 100% |
| Latência p50 | 3,1 s | 3,0 s |

O classificador sozinho deixou passar ovo, mel e trigo em 3 pedidos com restrição. Uma trava em
código, derivada das definições das tags, zerou as violações sem barrar nenhum prato correto.
A análise completa, com limitações, está no [relatório](RELATORIO.md).

## Arquitetura

As peças se conectam numa só direção: a demo e a API chamam o workflow, e o workflow chama as
peças. Por isso dá para trocar a interface (por um app, por exemplo), o provedor de LLM ou o
classificador sem mexer no resto. Plano completo no [design doc](docs/design-doc.md).

```mermaid
flowchart LR
  U["Cliente"] --> D["Demo Gradio"]
  APP["App ou outro serviço"] --> API
  D --> API["API FastAPI<br/>POST /pedido"]
  API --> WF["Workflow<br/>orquestrado em código"]
  WF <--> LLM["Camada de LLM<br/>Gemini ou Claude"]
  WF --> S["Busca semântica<br/>embeddings + ChromaDB"]
  WF --> C["Classificador<br/>BERTimbau + trava"]
  WF --> CR["Montador de carrinho<br/>código puro"]
  S --> DB[("Cardápio")]
  C --> HUB[("Modelo no<br/>Hugging Face Hub")]
```

## Como funciona um pedido

O código decide a ordem dos passos; o LLM só entende o pedido e escreve a explicação
([por quê](docs/adr/001-workflow-em-vez-de-agente.md)).

```mermaid
flowchart TD
  IN["Mensagem do cliente"] --> P1["1. Interpretar<br/>LLM gera JSON validado"]
  P1 --> V{"Tem orçamento?"}
  V -- "não" --> Q["Pergunta ao cliente"]
  V -- "sim" --> P2["2. Buscar<br/>embeddings + filtros de preço e tempo"]
  P2 --> P3["3. Filtrar restrições<br/>BERTimbau + trava de ingredientes"]
  P3 --> P4["4. Montar carrinho<br/>código, dentro do orçamento"]
  P4 --> P5["5. Explicar<br/>LLM escreve o porquê"]
  P5 --> OUT["Carrinho + explicação"]
```

| Peça | Tecnologia | Código |
|---|---|---|
| Demo | Gradio no Hugging Face Spaces | `app.py` |
| API | FastAPI (`POST /pedido`, `GET /health`) | `src/mmp/api.py` |
| Workflow | Python, 5 passos testáveis | `src/mmp/pipeline/` |
| LLM | Gemini atrás da interface `LLMClient` (troca por `.env`) | `src/mmp/llm/` |
| Busca semântica | ChromaDB + `multilingual-e5-small` | `src/mmp/search.py` |
| Classificador | BERTimbau ajustado + baseline TF-IDF | `src/mmp/models/` |
| Avaliação | 3 classificadores + 30 pedidos com regras conhecidas | `evals/` |

## Como o LLM (Gemini) é usado

O LLM aparece em três papéis diferentes no projeto, e em nenhum deles decide preço, orçamento
ou restrição:

| Papel | Onde | Como |
|---|---|---|
| **Gerar os dados** | `src/mmp/data/generate.py` | Um restaurante por chamada, com as definições das tags no prompt e saída em JSON validada pelo Pydantic |
| **Entender e explicar o pedido** | passos 1 e 5 do workflow | Passo 1: texto → `PedidoInterpretado` (schema JSON, few-shot, instrução para ignorar comandos dentro da mensagem). Passo 5: explica um carrinho já fechado, e o código confere que ele só citou itens do carrinho |
| **Referência na avaliação** | `src/mmp/models/llm_zero_shot.py` | Classifica 10 pratos por chamada, para comparar precisão, custo e latência com o modelo próprio |

**Engenharia em volta do LLM** (`src/mmp/llm/`):
- **Interface única:** o resto do código só conhece `LLMClient`. Gemini e Claude implementam só
  a chamada; trocar é uma linha do `.env`.
- **Saída estruturada:** o schema do Pydantic vai no prompt, a resposta é validada e, se vier
  inválida, o LLM recebe o erro e tem uma chance de corrigir.
- **Erros temporários e definitivos:** limite de requisições (429), servidor ocupado (503) e rede
  são repetidos com espera crescente; chave ou modelo inválidos (4xx) param na hora.
- **Prompts versionados** num único arquivo: `src/mmp/prompts.py`.

**O que aconteceu na prática**, com detalhes no [diário de bordo](docs/diario-de-bordo.md):
o modelo planejado (`gemini-2.5-flash`) não estava disponível para contas novas; o
`gemini-3.8-flash` gerou os dados até esgotar a cota diária gratuita (20 requisições), em 21 de
30 restaurantes; o workflow e a avaliação passaram para o `gemini-3.5-flash-lite` (500 por dia).
Cada troca foi uma linha no `.env`, sem mudar código
([ADR-003](docs/adr/003-gemini-atras-de-interface.md)).

## Decisões de engenharia

- **Regras críticas em código:** orçamento, tempo e restrições nunca dependem do LLM. Todos os
  números da resposta são gerados pelo código.
- **Provedor de LLM trocável:** o modelo foi trocado duas vezes durante a construção mudando
  só o `.env` ([ADR-003](docs/adr/003-gemini-atras-de-interface.md)).
- **Erros temporários e definitivos:** limite de requisições e falhas de rede são repetidos com
  espera crescente; chave ou modelo inválidos param na hora.
- **Protocolo de avaliação:** escolhas feitas na validação, teste usado só no fim.
- **Testes sem rede:** 62 testes com dublês do LLM, da busca e do classificador; a CI roda lint,
  testes e o build da imagem Docker.

Todas as decisões, com alternativas e consequências: [docs/adr/](docs/adr/).
Tudo o que deu errado e como foi resolvido: [docs/diario-de-bordo.md](docs/diario-de-bordo.md).

## Como rodar

Requer Python 3.12 e [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/kesiasilv/monta-meu-pedido.git
cd monta-meu-pedido
cp .env.example .env    # preencha GEMINI_API_KEY
make setup
make test
make demo               # http://localhost:7860
```

| Comando | O que faz |
|---|---|
| `make data` | Gera, valida e divide os dados (já incluídos no repositório) |
| `make baseline` | Treina o baseline TF-IDF |
| `make index` | Cria o índice de busca semântica |
| `make api` | Sobe a API em `http://localhost:8000/docs` |
| `make eval` | Roda o laboratório de avaliação |
| `make space` | Monta a pasta para publicar a demo no Hugging Face Spaces |

O fine-tuning roda no Google Colab: [notebooks/01_treino_bertimbau.ipynb](notebooks/01_treino_bertimbau.ipynb).

## Estrutura

```
src/mmp/
├── config.py · schemas.py · prompts.py · cardapio.py
├── data/       geração, validação, divisão e revisão dos dados
├── llm/        interface LLMClient, Gemini, Claude e dublê para testes
├── models/     baseline, BERTimbau, LLM zero-shot e métricas
├── search.py   busca semântica
├── pipeline/   os 5 passos, o orquestrador e a trava de ingredientes
└── api.py      FastAPI
notebooks/      fine-tuning do BERTimbau no Google Colab
evals/          casos de teste e resultados
docs/           design doc, ADRs, diário de bordo e card do dataset
```

## Limitações

Cardápios sintéticos (21 restaurantes, 291 pratos) com pistas explícitas nos nomes; conjuntos de
validação e teste pequenos; rótulos gerados por LLM e revisados por amostragem. **Não use para
alergias graves.** Detalhes na seção 7 do [relatório](RELATORIO.md).

## Como usei IA para construir

O projeto foi construído em um dia com o Claude Code como par de programação. O planejamento
começou por um design doc com objetivos, não-objetivos e métricas de sucesso; cada decisão foi
discutida antes de virar código. Rodei os experimentos, conferi os resultados e decidi entre as
alternativas. Vários problemas só apareceram ao testar com dados e APIs reais (modelo
indisponível, cota diária, um carrinho com sundae no lugar de poke, um teste que dependia do
`.env`), e cada um está registrado no diário de bordo com causa e solução.

## Licença

MIT

# Diário de bordo

Registro cronológico do que aconteceu durante a construção: decisões, problemas, como foram
resolvidos e os números de cada experimento. O **design doc** (`docs/design-doc.md`) é o
plano; este diário é o que de fato aconteceu. O `RELATORIO.md` resume os dois no fim.

---

## 15/11/2026

### Planejamento
- **Escopo:** o plano inicial tinha automações (bot no Telegram via n8n) e um dashboard de
  insights. Ficaram para uma versão 2, e o projeto priorizou o modelo treinado, a avaliação
  comparativa e a qualidade de engenharia.
- **Workflow em vez de agente autônomo** (ADR-001). A sequência de passos é fixa e as regras
  são críticas, então o código decide a ordem e o LLM só interpreta e explica.

### Ambiente
- O Mac tinha Python 3.14. O projeto usa **Python 3.12 via `uv`**, porque bibliotecas de ML
  demoram a suportar a versão mais nova.

### Dados
| Problema | Causa | Solução |
|---|---|---|
| `404 NOT_FOUND` em todas as chamadas | `gemini-2.5-flash` não está disponível para contas novas | Troca para `gemini-3.8-flash` |
| A geração repetiu cada erro 404 três vezes (~15 min perdidos) | A política de nova tentativa tratava todo erro como temporário | Erros separados em **temporários** (rede, 429, 5xx: repete) e **definitivos** (4xx: para na hora). Teste novo cobre isso |
| `429 RESOURCE_EXHAUSTED` no meio da geração | Plano gratuito do `gemini-3.8-flash`: **20 requisições por dia** | Dados mantidos como estavam (ver abaixo) |

- **Resultado:** 21 de 30 categorias, **291 pratos** (189 principais, 60 bebidas, 42 sobremesas).
  0 inválidos, 3 duplicados descartados, 0 correções da regra "vegano implica sem lactose".
- **Categorias que ficaram de fora** pela cota: indiana, coreana, peruana, frutos do mar,
  padaria, pastelaria, creperia, doceria, lanchonete.
- **Divisão estratificada:** 203 treino / 44 validação / 44 teste (seed 42).
- **Limitação:** os tempos de entrega gerados ficaram todos entre 35 e 45 min.
- **Modelo usado no dia a dia:** `gemini-3.5-flash-lite` (500 requisições por dia no plano
  gratuito). Um modelo mais forte gerou os dados uma vez, e um mais leve roda no workflow.

### Revisão dos rótulos (amostra de 50)
- Feita por um segundo modelo (Claude, *LLM-as-judge*), não por uma pessoa. Detalhes em
  `data/processed/revisao_notas.md`.
- **46 de 50 pratos sem erro (92%).** 4 erros, todos conservadores: o Gemini disse que o prato
  não atendia a uma restrição que os ingredientes atendiam.

### Baseline (TF-IDF + regressão logística)
- Validação: F1 micro 0,898 · **F1 macro 0,890**
- Teste (rodado uma vez, em `make eval --sem-llm`): F1 micro 0,907 · **F1 macro 0,898**
- Interpretação: os dados sintéticos têm pistas explícitas no nome ("Vegano", "Fit"), o que
  favorece um modelo que conta palavras.

### Busca semântica
| Tentativa | "comida japonesa" trouxe | Decisão |
|---|---|---|
| `paraphrase-multilingual-MiniLM-L12-v2` | chili mexicano, esfiha | Fraco em português |
| + categoria do restaurante no texto indexado | um pouco melhor | Mantido |
| `intfloat/multilingual-e5-small` com prefixos `query:` / `passage:` | 3 sushis + bowl japonês | **Escolhido** |

### Workflow
- **Bug encontrado testando com o Gemini de verdade:** "poke até R$ 45" devolvia um sundae.
  Nenhum poke cabia com a taxa de entrega, e o montador pegava o que coubesse.
- **Correção:** o montador só considera pratos com relevância até 0,05 abaixo do mais relevante
  (`MARGEM_RELEVANCIA`). Se o prato pedido não cabe, ele avisa em vez de trocar por outro.
- Latência medida em 3 pedidos: ~2 s por pedido (quase tudo nas 2 chamadas ao LLM).

### Treino do BERTimbau (Colab, GPU T4)
- **Problema:** `No module named 'mmp'`. O Colab só enxerga pacotes instalados com
  `pip install -e` depois de reiniciar a sessão. **Solução:** adicionar `src` ao `sys.path`.
- O login no Hugging Face agora é por link + código (OAuth), não mais colando o token.

| Rodada | Épocas | Taxa de aprendizado | F1 macro validação | F1 macro teste |
|---|---|---|---|---|
| 1 | até 8 | 2e-5 | 0,853 | 0,795 |
| 2 | até 20 (parou na 11ª pelo early stopping; melhor época: 9) | 5e-5 | **0,952** | **0,884** |

Rodada 1, F1 no teste por tag: vegano 0,857 · vegetariano 0,931 · sem_lactose 0,900 ·
sem_gluten 0,839 · fit 0,710 · picante 0,462 (7 exemplos) · doce 0,867.

Rodada 2, F1 no teste por tag: vegano 0,909 · vegetariano 0,983 · sem_lactose 0,915 ·
sem_gluten 0,912 · fit 0,769 · picante 0,769 · doce 0,929.
Limiares escolhidos na validação: vegano 0,30 · vegetariano 0,65 · sem_lactose 0,30 ·
sem_gluten 0,40 · fit 0,55 · picante 0,50 · doce 0,70.

- **Decisão: fica a rodada 2** (validação 0,952 contra 0,853). É a versão publicada em
  `KesiaSilva/bertimbau-tags-pratos`.
- **Comparação honesta com o baseline no teste:** BERTimbau 0,884 contra baseline 0,898.
  Com 44 pratos de teste, essa diferença está dentro do ruído: na prática, empate.
- **A validação superestimou o BERTimbau** (0,952 na validação contra 0,884 no teste). Os
  limiares foram escolhidos nos mesmos 44 pratos da validação, então se ajustaram a eles.
  É um exemplo de por que o teste só pode ser usado no fim.
- **Por tag, nas restrições que filtram pratos:** o BERTimbau foi melhor em `sem_lactose`
  (0,915 contra 0,873) e `sem_gluten` (0,912 contra 0,867) e pior em `vegano` (0,909 contra
  0,950).
- **Classificador do workflow: BERTimbau.** Escolhido pela validação, que é o critério do
  protocolo, e não pelo teste.

### CI
- **Teste que passava no Mac e falhava no GitHub:** `test_pedido_longo_demais_e_recusado` não
  trocava o workflow real pelo falso. O FastAPI monta as dependências antes de validar o corpo
  da requisição, então o teste criava o workflow de verdade, que precisa da chave do Gemini.
  No Mac a chave existia (e o teste levava ~8 s carregando modelos); na CI não.
- **Correção:** uma fixture troca o workflow por um falso em todos os testes da API. Conferido
  rodando a suíte com o `.env` escondido, como na CI: 37 testes em ~1 s.
- **Lição:** teste que depende do ambiente de quem roda não é teste. A CI existe para pegar isso.

- **Por que a rodada 2:** a **validação** já mostrava o BERTimbau abaixo do baseline
  (0,853 contra 0,890). Com 203 exemplos e lote 16, a rodada 1 fez só ~100 atualizações de
  pesos. A decisão de ajustar foi tomada pela validação, não pelo teste.
- **Regra de decisão:** fica a rodada com maior F1 macro na **validação**.

### Avaliação completa (`make eval`, 15:45)
Resultados em `evals/resultados.md`. LLM `gemini-3.5-flash-lite`, workflow com o BERTimbau.

**A. Classificadores no teste (44 pratos)**

| Modelo | F1 macro | Latência (ms/prato) | Custo estimado (USD/1.000 pratos) |
|---|---|---|---|
| Baseline TF-IDF | 0,898 | 0,13 | ~0 (CPU) |
| BERTimbau | 0,884 | 32 (CPU do Mac) | ~0 (CPU) |
| LLM zero-shot | **0,938** | 130 (em lotes de 10) | 0,11 |

- O LLM zero-shot foi o mais preciso, mas **~1.000x mais lento que o baseline** e o único com
  custo por uso.
- **Viés conhecido a favor do LLM:** os rótulos de referência foram gerados pelo Gemini, e o
  zero-shot também é um Gemini. Ele está, em parte, concordando consigo mesmo. Esta limitação
  foi prevista no datasheet antes do experimento.
- O custo usa os preços configurados no `.env`, que eram os do `gemini-2.5-flash`. É preciso
  conferir o preço real do `gemini-3.5-flash-lite` antes de citar o número.

**B. Workflow em 30 pedidos**
- Status correto (ok / precisa_info / sem_opcao): **100%**. Orçamento e restrições entendidos
  pelo LLM: **100%**.
- Orçamento respeitado: **100%**. Tempo respeitado: **100%**. Latência p50 3,1 s · p95 6,8 s
  (meta RNF2: abaixo de 8 s).
- **Restrições respeitadas: 70%** (7 dos 10 carrinhos de pedidos com restrição).

**Correção de métrica:** a primeira versão do relatório dizia 85%, porque contava os 20
carrinhos, inclusive os 10 de pedidos sem restrição, que passam sempre. Corrigido para contar
só os pedidos com restrição; a tabela foi regerada a partir dos mesmos dados, sem rodar de novo.

**As 3 violações** (todas erros do BERTimbau, no sentido perigoso: ofereceu o que não podia):

| Caso | Prato | Restrição violada | Ingrediente que denuncia |
|---|---|---|---|
| r05 | Virado à Paulista Vegetariano | vegano | ovo de galinha |
| r06 | Tabule Fresco da Casa | sem_gluten | trigo fino para kibe |
| r09 | Suco de Laranja Integral com Mel (bebida extra) | vegano | mel puro de abelha |

- Os 3 ingredientes estão listados textualmente e aparecem nas **definições das tags** do
  design doc. O modelo errou onde uma regra simples por palavra acertaria.
- Contraste com a revisão dos rótulos: lá os erros do Gemini eram conservadores; aqui os erros
  do classificador são permissivos, o que é pior para um sistema de restrição alimentar.

### Trava de ingredientes (rodada 2 da avaliação)
- **O que é:** segunda camada no passo 3 (`src/mmp/pipeline/trava.py`). Um prato só passa se o
  classificador aprova **e** a lista de ingredientes não tem termo proibido pela definição da
  restrição. Ligável por `TRAVA_INGREDIENTES` no `.env`, para permitir a comparação.
- **Checagem contra os rótulos dos 291 pratos:** a primeira versão barrou indevidamente 12
  pratos veganos e 11 sem lactose por ambiguidades da língua ("couve manteiga", "pimenta
  calabresa", "chocolate sem leite", "ovo de galinha"). Depois de regras gerais para esses
  falsos amigos: **0 pratos barrados indevidamente** nas 4 restrições, e a trava pega 99%
  (vegano), 95% (vegetariano), 94% (sem lactose) e 91% (sem glúten) dos pratos não compatíveis.
- **Ressalva metodológica:** essas regras foram ajustadas olhando o cardápio inteiro, que
  inclui os pratos de teste. São regras gerais do português, não exceções por prato, mas o
  ajuste não foi feito só com dados de treino.

| | Rodada 1 (só o modelo) | Rodada 2 (modelo + trava) |
|---|---|---|
| Restrições respeitadas (10 carrinhos com restrição) | 70% | **100%** |
| Orçamento / tempo respeitados | 100% / 100% | 100% / 100% |
| Status correto | 100% | 97% |
| Latência p50 / p95 | 3,1 s / 6,8 s | 3,0 s / 3,6 s |

- **A queda de status (s03, "Me vê um hambúrguer até R$ 50") não tem relação com a trava:** o
  pedido não tem restrição. A interpretação pelo LLM falhou nessa chamada e o workflow pediu
  para reformular. Repetido 3 vezes depois, deu `ok` nas 3. Falha transitória do LLM.
- **Melhoria futura:** salvar o motivo de cada falha na avaliação, para distinguir erro do LLM
  de erro de regra sem precisar repetir o caso.
- **Conclusão:** o modelo sozinho aprovou 3 pratos que violavam restrições. A trava, uma regra
  de ~80 linhas escrita a partir das definições, eliminou as 3 violações sem barrar nenhum prato
  correto do cardápio. Mesma filosofia do orçamento: regra crítica fica em código.

### Publicação
- **Hugging Face Spaces:** o código da demo foi enviado (39 arquivos) e as chaves configuradas,
  mas o Space não inicia: *"You've reached your cpu-basic quota limit"*. A conta tem um único
  Space, então não há outro para pausar; a conta gratuita está sem cota de CPU.
- **Decisão:** a demo vai em vídeo no README, gravada rodando localmente. O Space fica publicado
  com o código, para rodar se a cota for liberada.
- **Alternativas avaliadas para uma demo pública gratuita:** Streamlit Community Cloud e Render
  têm de 512 MB a 1 GB de RAM no plano gratuito, pouco para PyTorch + BERTimbau +
  multilingual-e5 (~2 GB). Uma versão leve (baseline TF-IDF + trava, embeddings pela API do
  Gemini, sem PyTorch) caberia; fica como melhoria futura.
- **Interface da demo refeita:** pedido em cima, conversa embaixo, painel com o carrinho e com
  os bastidores (o que o LLM entendeu e o tempo de cada etapa).

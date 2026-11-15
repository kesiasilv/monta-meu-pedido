"""Fine-tuning e inferência do BERTimbau para classificação multi-label das 7 tags.

O treino roda no Google Colab (GPU T4) pelo notebook notebooks/01_treino_bertimbau.ipynb.
A inferência roda em CPU, baixando o modelo publicado no Hugging Face Hub.
"""

import json
import logging
from pathlib import Path

import numpy as np

from mmp.config import settings
from mmp.data.split import carregar_split
from mmp.models.metrics import ajustar_limiares, aplicar_limiares, calcular_metricas
from mmp.schemas import TAGS
from mmp.tags import binarizar, para_tags

log = logging.getLogger(__name__)

MODELO_BASE = "neuralmind/bert-base-portuguese-cased"
MAX_TOKENS = 128


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-x))


class BertimbauClassificador:
    nome = "bertimbau"

    def __init__(self, modelo_id: str, lote: int = 32) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(modelo_id)
        self.modelo = AutoModelForSequenceClassification.from_pretrained(modelo_id).eval()
        self.lote = lote
        limiares = getattr(self.modelo.config, "limiares", None) or {}
        self.limiares = np.array([limiares.get(t, 0.5) for t in TAGS])

    def prever_probs(self, textos: list[str]) -> np.ndarray:
        saidas = []
        with self._torch.no_grad():
            for i in range(0, len(textos), self.lote):
                entrada = self.tokenizer(
                    textos[i : i + self.lote],
                    truncation=True,
                    max_length=MAX_TOKENS,
                    padding=True,
                    return_tensors="pt",
                )
                saidas.append(self._torch.sigmoid(self.modelo(**entrada).logits).numpy())
        return np.vstack(saidas) if saidas else np.zeros((0, len(TAGS)))

    def prever(self, textos: list[str]) -> list[set[str]]:
        pred = aplicar_limiares(self.prever_probs(textos), self.limiares)
        return [para_tags(linha) for linha in pred]


def treinar(
    push_para: str | None = None,
    saida: Path | None = None,
    epocas: int = 20,
    taxa_aprendizado: float = 5e-5,
    lote: int = 16,
    seed: int = 42,
) -> dict:
    """Treina, ajusta limiares na validação, avalia uma vez no teste e publica no Hub.

    Os padrões são os da rodada 2, a publicada. A rodada 1 (8 épocas, taxa 2e-5) ficou abaixo do
    baseline na validação; as duas estão no RELATORIO.md.
    """
    import torch
    from datasets import Dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        EarlyStoppingCallback,
        Trainer,
        TrainingArguments,
        set_seed,
    )

    set_seed(seed)
    saida = saida or settings.artifacts_dir / "bertimbau"
    treino, val, teste = carregar_split("train"), carregar_split("val"), carregar_split("test")
    tokenizer = AutoTokenizer.from_pretrained(MODELO_BASE)

    def para_dataset(linhas: list[dict]) -> Dataset:
        cod = tokenizer(
            [r["texto"] for r in linhas], truncation=True, max_length=MAX_TOKENS,
            padding="max_length",
        )  # fmt: skip
        y = binarizar([r["tags"] for r in linhas]).astype(np.float32)
        return Dataset.from_dict({**cod, "labels": y.tolist()})

    ds_treino, ds_val, ds_teste = para_dataset(treino), para_dataset(val), para_dataset(teste)
    y_val = binarizar([r["tags"] for r in val])
    y_teste = binarizar([r["tags"] for r in teste])

    modelo = AutoModelForSequenceClassification.from_pretrained(
        MODELO_BASE,
        num_labels=len(TAGS),
        problem_type="multi_label_classification",
        id2label=dict(enumerate(TAGS)),
        label2id={t: i for i, t in enumerate(TAGS)},
    )

    def metricas_epoca(previsao) -> dict:
        pred = (_sigmoid(previsao.predictions) >= 0.5).astype(int)
        m = calcular_metricas(previsao.label_ids.astype(int), pred)
        return {"f1_macro": m["f1_macro"], "f1_micro": m["f1_micro"]}

    argumentos = TrainingArguments(
        output_dir=str(saida / "checkpoints"),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=taxa_aprendizado,
        per_device_train_batch_size=lote,
        per_device_eval_batch_size=32,
        num_train_epochs=epocas,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,
        save_total_limit=2,
        logging_steps=10,
        seed=seed,
        report_to="none",
        fp16=torch.cuda.is_available(),
    )
    trainer = Trainer(
        model=modelo,
        args=argumentos,
        train_dataset=ds_treino,
        eval_dataset=ds_val,
        compute_metrics=metricas_epoca,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )
    trainer.train()

    # Limiares escolhidos só na validação; o teste é usado uma única vez, no fim.
    probs_val = _sigmoid(trainer.predict(ds_val).predictions)
    limiares = ajustar_limiares(probs_val, y_val)
    probs_teste = _sigmoid(trainer.predict(ds_teste).predictions)

    resultado = {
        "modelo_base": MODELO_BASE,
        "hiperparametros": {
            "epocas_max": epocas,
            "taxa_aprendizado": taxa_aprendizado,
            "lote": lote,
            "max_tokens": MAX_TOKENS,
            "weight_decay": 0.01,
            "seed": seed,
        },  # fmt: skip
        "melhor_checkpoint": trainer.state.best_model_checkpoint,
        "limiares": dict(zip(TAGS, limiares.round(2).tolist(), strict=True)),
        "validacao": calcular_metricas(y_val, aplicar_limiares(probs_val, limiares)),
        "teste": calcular_metricas(y_teste, aplicar_limiares(probs_teste, limiares)),
        "tamanhos": {"treino": len(treino), "validacao": len(val), "teste": len(teste)},
    }

    modelo.config.update({"limiares": resultado["limiares"]})
    trainer.save_model(str(saida))
    tokenizer.save_pretrained(str(saida))
    (saida / "README.md").write_text(gerar_model_card(resultado, push_para), encoding="utf-8")
    (saida / "metricas.json").write_text(json.dumps(resultado, indent=2), encoding="utf-8")

    if push_para:
        from huggingface_hub import HfApi

        modelo.push_to_hub(push_para)
        tokenizer.push_to_hub(push_para)
        HfApi().upload_file(
            path_or_fileobj=str(saida / "README.md"), path_in_repo="README.md", repo_id=push_para
        )
        log.info("Publicado em https://huggingface.co/%s", push_para)
    return resultado


def gerar_model_card(r: dict, repo_id: str | None) -> str:
    repo_id = repo_id or "seu-usuario/bertimbau-tags-pratos"
    linhas_tag = "\n".join(
        f"| `{tag}` | {r['teste']['por_tag'][tag]['f1']:.3f} | "
        f"{r['teste']['por_tag'][tag]['suporte']} | {r['limiares'][tag]:.2f} |"
        for tag in TAGS
    )
    h = r["hiperparametros"]
    return f"""---
language: pt
license: mit
library_name: transformers
pipeline_tag: text-classification
base_model: {MODELO_BASE}
tags: [multi-label-classification, food, portuguese]
---

# BERTimbau: tags alimentares de pratos

Classificador multi-label que lê o nome, a descrição e os ingredientes de um prato e diz quais
destas 7 tags ele tem: `vegano`, `vegetariano`, `sem_lactose`, `sem_gluten`, `fit`, `picante`
e `doce`.

Faz parte do projeto **Monta Meu Pedido**, um assistente de IA que monta pedidos de comida.

## Uso pretendido

Filtrar pratos de cardápio por restrição alimentar e preferência, em português do Brasil.

**Fora do escopo:** decisões médicas ou alergias graves. O modelo erra, e foi treinado com dados
sintéticos.

## Como usar

```python
from transformers import pipeline
clf = pipeline("text-classification", model="{repo_id}", top_k=None, function_to_apply="sigmoid")
clf("Poke de tofu. Tofu grelhado com arroz e legumes. Ingredientes: tofu, arroz, pepino")
```

Os limiares por tag ficam em `config.limiares` (veja a tabela abaixo).

## Dados

~420 pratos de 30 restaurantes fictícios, gerados com um LLM e validados com regras de
consistência. 50 pratos foram revisados à mão para medir a qualidade dos rótulos.
Divisão estratificada: {r["tamanhos"]["treino"]} treino, {r["tamanhos"]["validacao"]} validação,
{r["tamanhos"]["teste"]} teste.

## Treino

Fine-tuning de `{MODELO_BASE}` com perda BCEWithLogits. Taxa de aprendizado {h["taxa_aprendizado"]},
lote {h["lote"]}, até {h["epocas_max"]} épocas com early stopping (paciência 2) pelo F1 macro da
validação, {h["max_tokens"]} tokens, weight decay {h["weight_decay"]}, seed {h["seed"]}.
O limiar de cada tag foi escolhido na validação.

## Resultados no teste

F1 micro **{r["teste"]["f1_micro"]:.3f}** · F1 macro **{r["teste"]["f1_macro"]:.3f}**

| Tag | F1 | Suporte | Limiar |
|---|---|---|---|
{linhas_tag}

A comparação com um baseline TF-IDF e com um LLM zero-shot está no relatório do projeto.

## Limitações

- Dados sintéticos: menos variados e mais limpos que cardápios reais.
- Os rótulos vieram de um LLM, então erros sistemáticos dele podem ter sido aprendidos.
- Cozinha brasileira de delivery; o desempenho em outros contextos não foi medido.
"""

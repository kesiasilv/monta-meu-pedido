"""Baseline: TF-IDF + regressão logística (uma por tag).

Existe para responder: quanto o transformer realmente acrescenta?

Uso: uv run python -m mmp.models.baseline
"""

import json
import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline

from mmp.config import settings
from mmp.data.split import carregar_split
from mmp.models.metrics import ajustar_limiares, aplicar_limiares, calcular_metricas
from mmp.tags import binarizar, para_tags

log = logging.getLogger(__name__)


def criar_pipeline(seed: int) -> Pipeline:
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)),
            (
                "clf",
                OneVsRestClassifier(
                    LogisticRegression(max_iter=2000, class_weight="balanced", random_state=seed)
                ),
            ),
        ]
    )


class BaselineClassificador:
    nome = "baseline_tfidf"

    def __init__(self, pipeline: Pipeline, limiares: np.ndarray) -> None:
        self.pipeline = pipeline
        self.limiares = limiares

    @classmethod
    def treinar(cls, textos: list[str], y: np.ndarray, seed: int) -> "BaselineClassificador":
        pipeline = criar_pipeline(seed)
        pipeline.fit(textos, y)
        return cls(pipeline, np.full(y.shape[1], 0.5))

    @classmethod
    def carregar(cls, caminho: Path) -> "BaselineClassificador":
        if not caminho.exists():
            raise FileNotFoundError(f"{caminho} não existe. Rode: make baseline")
        dados = joblib.load(caminho)
        return cls(dados["pipeline"], dados["limiares"])

    def salvar(self, caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"pipeline": self.pipeline, "limiares": self.limiares}, caminho)

    def prever_probs(self, textos: list[str]) -> np.ndarray:
        return self.pipeline.predict_proba(textos)

    def prever(self, textos: list[str]) -> list[set[str]]:
        pred = aplicar_limiares(self.prever_probs(textos), self.limiares)
        return [para_tags(linha) for linha in pred]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    treino, val = carregar_split("train"), carregar_split("val")
    y_treino = binarizar([r["tags"] for r in treino])
    y_val = binarizar([r["tags"] for r in val])

    modelo = BaselineClassificador.treinar([r["texto"] for r in treino], y_treino, settings.seed)
    probs_val = modelo.prever_probs([r["texto"] for r in val])
    modelo.limiares = ajustar_limiares(probs_val, y_val)
    modelo.salvar(settings.artifacts_dir / "baseline.joblib")

    metricas = calcular_metricas(y_val, aplicar_limiares(probs_val, modelo.limiares))
    destino = settings.artifacts_dir / "baseline_metricas_val.json"
    destino.write_text(json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Validação: F1 micro %.3f | F1 macro %.3f", metricas["f1_micro"], metricas["f1_macro"])
    for tag, m in metricas["por_tag"].items():
        log.info("  %-12s F1 %.3f (suporte %d)", tag, m["f1"], m["suporte"])
    log.info("O conjunto de teste só é usado em: make eval")


if __name__ == "__main__":
    main()

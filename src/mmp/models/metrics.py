"""Métricas multi-label e ajuste de limiar, compartilhados por todos os classificadores."""

import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score

from mmp.schemas import TAGS

GRADE_LIMIARES = np.round(np.arange(0.10, 0.91, 0.05), 2)


def ajustar_limiares(probs: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Escolhe, para cada tag, o limiar que maximiza o F1. Use só com dados de validação."""
    limiares = np.full(len(TAGS), 0.5)
    for j in range(len(TAGS)):
        melhores = [
            (f1_score(y[:, j], probs[:, j] >= limiar, zero_division=0), -abs(limiar - 0.5), limiar)
            for limiar in GRADE_LIMIARES
        ]
        limiares[j] = max(melhores)[2]
    return limiares


def aplicar_limiares(probs: np.ndarray, limiares: np.ndarray) -> np.ndarray:
    return (probs >= limiares).astype(int)


def calcular_metricas(y: np.ndarray, pred: np.ndarray) -> dict:
    por_tag = {
        tag: {
            "f1": round(float(f1_score(y[:, j], pred[:, j], zero_division=0)), 3),
            "precisao": round(float(precision_score(y[:, j], pred[:, j], zero_division=0)), 3),
            "recall": round(float(recall_score(y[:, j], pred[:, j], zero_division=0)), 3),
            "suporte": int(y[:, j].sum()),
        }
        for j, tag in enumerate(TAGS)
    }
    return {
        "f1_micro": round(float(f1_score(y, pred, average="micro", zero_division=0)), 3),
        "f1_macro": round(float(f1_score(y, pred, average="macro", zero_division=0)), 3),
        "acerto_exato": round(float((y == pred).all(axis=1).mean()), 3),
        "por_tag": por_tag,
    }

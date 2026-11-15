"""Classificadores de tags. Os módulos pesados (torch) só são importados quando usados."""

from mmp.config import Settings
from mmp.models.base import Classificador

__all__ = ["Classificador", "criar_classificador"]


def criar_classificador(settings: Settings) -> Classificador:
    match settings.classificador:
        case "baseline":
            from mmp.models.baseline import BaselineClassificador

            return BaselineClassificador.carregar(settings.artifacts_dir / "baseline.joblib")
        case "bertimbau":
            from mmp.models.bertimbau import BertimbauClassificador

            return BertimbauClassificador(settings.hf_model_id)

"""Divide os pratos em treino (70%), validação (15%) e teste (15%), estratificado pelas tags.

Os splits são gerados uma vez e nunca mais. Use --force só se os dados mudarem.

Uso: uv run python -m mmp.data.split [--force]
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np
from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit

from mmp.cardapio import Cardapio
from mmp.config import settings
from mmp.schemas import Prato
from mmp.tags import binarizar

log = logging.getLogger(__name__)


def dividir(pratos: list[Prato], seed: int) -> dict[str, list[Prato]]:
    y = binarizar([p.tags for p in pratos])
    indices = np.arange(len(pratos))

    primeiro = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=0.30, random_state=seed)
    treino_idx, resto_idx = next(primeiro.split(indices, y))

    segundo = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=0.50, random_state=seed)
    val_rel, teste_rel = next(segundo.split(resto_idx, y[resto_idx]))

    return {
        "train": [pratos[i] for i in treino_idx],
        "val": [pratos[i] for i in resto_idx[val_rel]],
        "test": [pratos[i] for i in resto_idx[teste_rel]],
    }


def salvar(splits: dict[str, list[Prato]], pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, pratos in splits.items():
        linhas = [
            json.dumps({"id": p.id, "texto": p.texto(), "tags": p.tags}, ensure_ascii=False)
            for p in pratos
        ]
        (pasta / f"{nome}.jsonl").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def carregar_split(nome: str, pasta: Path | None = None) -> list[dict]:
    pasta = pasta or settings.splits_dir
    texto = (pasta / f"{nome}.jsonl").read_text(encoding="utf-8")
    return [json.loads(linha) for linha in texto.splitlines() if linha.strip()]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if (settings.splits_dir / "test.jsonl").exists() and "--force" not in sys.argv:
        log.info("Splits já existem e não serão regerados. Use --force se os dados mudaram.")
        return
    cardapio = Cardapio.carregar(settings.processed_dir)
    splits = dividir(cardapio.pratos, settings.seed)
    salvar(splits, settings.splits_dir)
    for nome, pratos in splits.items():
        log.info("%s: %d pratos", nome, len(pratos))


if __name__ == "__main__":
    main()

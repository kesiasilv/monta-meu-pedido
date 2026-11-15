"""Conversão entre listas de tags e a matriz binária que os modelos usam."""

import numpy as np

from mmp.schemas import TAGS


def binarizar(listas_de_tags: list[list[str]] | list[set[str]]) -> np.ndarray:
    """[['vegano', 'fit'], []] -> matriz (n, 7) de 0 e 1 na ordem de TAGS."""
    y = np.zeros((len(listas_de_tags), len(TAGS)), dtype=int)
    for i, tags in enumerate(listas_de_tags):
        for t in tags:
            if t in TAGS:
                y[i, TAGS.index(t)] = 1
    return y


def para_tags(linha: np.ndarray) -> set[str]:
    return {TAGS[j] for j, v in enumerate(linha) if v}

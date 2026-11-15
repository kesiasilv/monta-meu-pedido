from typing import Protocol


class Classificador(Protocol):
    """Qualquer coisa que receba textos de pratos e devolva as tags de cada um."""

    nome: str

    def prever(self, textos: list[str]) -> list[set[str]]: ...

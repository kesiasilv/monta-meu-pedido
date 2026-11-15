"""Acesso ao cardápio (restaurantes e pratos) carregado dos arquivos processados."""

import json
from pathlib import Path

from mmp.schemas import Prato, Restaurante


class Cardapio:
    def __init__(self, restaurantes: list[Restaurante], pratos: list[Prato]) -> None:
        self.restaurantes = restaurantes
        self.pratos = pratos
        self._restaurantes = {r.id: r for r in restaurantes}
        self._pratos = {p.id: p for p in pratos}

    @classmethod
    def carregar(cls, pasta: Path) -> "Cardapio":
        restaurantes = json.loads((pasta / "restaurantes.json").read_text(encoding="utf-8"))
        pratos = json.loads((pasta / "pratos.json").read_text(encoding="utf-8"))
        return cls(
            [Restaurante.model_validate(r) for r in restaurantes],
            [Prato.model_validate(p) for p in pratos],
        )

    def prato(self, prato_id: str) -> Prato:
        return self._pratos[prato_id]

    def restaurante(self, restaurante_id: str) -> Restaurante:
        return self._restaurantes[restaurante_id]

    def extras_de(self, restaurante_id: str) -> list[Prato]:
        """Bebidas e sobremesas de um restaurante."""
        return [
            p for p in self.pratos if p.restaurante_id == restaurante_id and p.tipo != "principal"
        ]

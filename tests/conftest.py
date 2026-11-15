"""Cardápio pequeno e dublês (fakes) usados em todos os testes. Nenhum teste chama API real."""

import pytest

from mmp.cardapio import Cardapio
from mmp.schemas import Prato, Restaurante


def _prato(id_, rest, nome, preco, tipo, tags, ingredientes=None):
    return Prato(
        id=id_,
        restaurante_id=rest,
        nome=nome,
        descricao=f"{nome} delicioso",
        ingredientes=ingredientes or [nome.lower()],
        preco=preco,
        tipo=tipo,
        tags=tags,
    )


@pytest.fixture
def cardapio() -> Cardapio:
    restaurantes = [
        Restaurante(id="r01", nome="Poke Place", categoria="poke", taxa_entrega=0,
                    tempo_entrega_min=25),
        Restaurante(id="r02", nome="Cantina da Nona", categoria="italiana", taxa_entrega=8,
                    tempo_entrega_min=50),
    ]  # fmt: skip
    vegano = ["vegano", "vegetariano", "sem_lactose"]
    pratos = [
        _prato("p001", "r01", "Poke de salmão", 32.90, "principal", ["sem_lactose", "fit"]),
        _prato("p002", "r01", "Poke de tofu", 29.90, "principal", [*vegano, "fit"]),
        _prato("p003", "r01", "Água de coco", 6.00, "bebida", [*vegano, "sem_gluten"]),
        _prato("p004", "r01", "Mousse de chocolate", 12.00, "sobremesa", ["vegetariano", "doce"]),
        _prato("p005", "r02", "Lasanha bolonhesa", 45.00, "principal", []),
        _prato("p006", "r02", "Nhoque ao sugo", 38.00, "principal", ["vegetariano", "sem_lactose"]),
        _prato("p007", "r02", "Refrigerante", 7.00, "bebida", [*vegano, "sem_gluten", "doce"]),
    ]
    return Cardapio(restaurantes, pratos)


class FakeBuscador:
    """Relevância 0,9 se alguma palavra da consulta aparece no nome do prato, senão 0,5."""

    def __init__(self, cardapio: Cardapio) -> None:
        self.cardapio = cardapio

    def buscar(self, consulta, preco_max=None, tempo_max=None, k=30):
        palavras = consulta.lower().split()
        resultados = []
        for p in self.cardapio.pratos:
            restaurante = self.cardapio.restaurante(p.restaurante_id)
            if p.tipo != "principal":
                continue
            if preco_max is not None and p.preco > preco_max:
                continue
            if tempo_max is not None and restaurante.tempo_entrega_min > tempo_max:
                continue
            relevancia = 0.9 if any(w in p.nome.lower() for w in palavras) else 0.5
            resultados.append((p.id, relevancia))
        return sorted(resultados, key=lambda r: -r[1])[:k]


class FakeClassificador:
    """Classificador perfeito: devolve as tags de referência do prato."""

    nome = "fake"

    def __init__(self, cardapio: Cardapio) -> None:
        self._por_texto = {p.texto(): set(p.tags) for p in cardapio.pratos}

    def prever(self, textos):
        return [self._por_texto.get(t, set()) for t in textos]


@pytest.fixture
def buscador(cardapio) -> FakeBuscador:
    return FakeBuscador(cardapio)


@pytest.fixture
def classificador(cardapio) -> FakeClassificador:
    return FakeClassificador(cardapio)

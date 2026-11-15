"""Testes da API. O workflow real é sempre trocado por um falso: os testes não podem
depender do .env de quem roda (na CI ele nem existe)."""

import pytest
from fastapi.testclient import TestClient

from mmp.api import app, obter_workflow
from mmp.llm.fake import FakeLLMClient
from mmp.pipeline.workflow import Workflow
from mmp.schemas import PedidoInterpretado


@pytest.fixture
def cliente(cardapio, buscador, classificador):
    pedido = PedidoInterpretado(descricao_livre="poke", orcamento=40)
    llm = FakeLLMClient([pedido, "Ótima escolha."])
    app.dependency_overrides[obter_workflow] = lambda: Workflow(
        llm, buscador, classificador, cardapio
    )
    yield TestClient(app)
    app.dependency_overrides.clear()  # roda mesmo se o teste falhar


def test_health(cliente):
    assert cliente.get("/health").json()["status"] == "ok"


def test_pedido_devolve_carrinho(cliente):
    resposta = cliente.post("/pedido", json={"texto": "quero um poke até 40 reais"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert corpo["carrinho"]["total"] <= 40


def test_pedido_longo_demais_e_recusado(cliente):
    assert cliente.post("/pedido", json={"texto": "x" * 501}).status_code == 422

from fastapi.testclient import TestClient

from mmp.api import app, obter_workflow
from mmp.llm.fake import FakeLLMClient
from mmp.pipeline.workflow import Workflow
from mmp.schemas import PedidoInterpretado


def cliente_com(workflow: Workflow) -> TestClient:
    app.dependency_overrides[obter_workflow] = lambda: workflow
    return TestClient(app)


def test_health():
    assert TestClient(app).get("/health").json()["status"] == "ok"


def test_pedido_devolve_carrinho(cardapio, buscador, classificador):
    pedido = PedidoInterpretado(descricao_livre="poke", orcamento=40)
    llm = FakeLLMClient([pedido, "Ótima escolha."])
    cliente = cliente_com(Workflow(llm, buscador, classificador, cardapio))

    resposta = cliente.post("/pedido", json={"texto": "quero um poke até 40 reais"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["status"] == "ok"
    assert corpo["carrinho"]["total"] <= 40
    app.dependency_overrides.clear()


def test_pedido_longo_demais_e_recusado():
    resposta = TestClient(app).post("/pedido", json={"texto": "x" * 501})
    assert resposta.status_code == 422

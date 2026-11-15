import pytest

from mmp.llm.base import ErroDefinitivo, ErroLLM, extrair_json
from mmp.llm.fake import FakeLLMClient
from mmp.schemas import PedidoInterpretado


def test_extrair_json_remove_cercas_de_markdown():
    texto = 'Claro! ```json\n{"a": 1}\n``` pronto'
    assert extrair_json(texto) == '{"a": 1}'


def test_gerar_json_valida_contra_o_schema():
    llm = FakeLLMClient(['{"orcamento": 40, "descricao_livre": "poke"}'])
    pedido = llm.gerar_json("sys", "user", PedidoInterpretado)
    assert pedido.orcamento == 40
    assert llm.uso.chamadas == 1


def test_gerar_json_pede_correcao_uma_vez():
    llm = FakeLLMClient(["isso não é json", '{"descricao_livre": "pizza"}'])
    pedido = llm.gerar_json("sys", "user", PedidoInterpretado)
    assert pedido.descricao_livre == "pizza"
    assert "não seguiu o schema" in llm.chamadas[1]["user"]


def test_gerar_json_desiste_depois_da_correcao():
    llm = FakeLLMClient(["lixo", "lixo de novo"])
    with pytest.raises(ErroLLM):
        llm.gerar_json("sys", "user", PedidoInterpretado)


def test_erro_de_rede_tenta_de_novo():
    llm = FakeLLMClient([ConnectionError("caiu"), "tudo certo"])
    assert llm.gerar_texto("sys", "user") == "tudo certo"


def test_instrucao_json_vai_no_system_prompt():
    llm = FakeLLMClient(['{"descricao_livre": "x"}'])
    llm.gerar_json("Você extrai pedidos.", "user", PedidoInterpretado)
    assert "JSON Schema" in llm.chamadas[0]["system"]


def test_erro_definitivo_nao_e_repetido():
    class LLMComErroDefinitivo(FakeLLMClient):
        def _eh_definitivo(self, erro):
            return isinstance(erro, PermissionError)

    llm = LLMComErroDefinitivo([PermissionError("modelo não existe"), "não deveria chegar aqui"])
    with pytest.raises(ErroDefinitivo):
        llm.gerar_texto("sys", "user")
    assert llm.uso.chamadas == 1

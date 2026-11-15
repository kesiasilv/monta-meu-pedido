import pytest

from mmp.pipeline.trava import violacoes
from mmp.schemas import Prato


def prato(*ingredientes: str) -> Prato:
    return Prato(
        id="p1", restaurante_id="r1", nome="Teste", descricao="x",
        ingredientes=list(ingredientes), preco=10, tipo="principal",
    )  # fmt: skip


@pytest.mark.parametrize(
    ("ingrediente", "restricao"),
    [
        ("ovo de galinha", "vegano"),
        ("mel puro de abelha", "vegano"),
        ("trigo fino para kibe", "sem_gluten"),
        ("queijo Muçarela", "sem_lactose"),
        ("molho de soja escuro", "sem_gluten"),
        ("linguiça vegetal à base de glúten", "sem_gluten"),
        ("filé de robalo", "vegetariano"),
        ("maionese com sriracha", "vegano"),
    ],
)
def test_barra_ingrediente_proibido(ingrediente, restricao):
    assert violacoes(prato(ingrediente), {restricao})


@pytest.mark.parametrize(
    ("ingrediente", "restricao"),
    [
        ("leite de coco", "vegano"),
        ("leite de coco", "sem_lactose"),
        ("queijo vegetal de castanha de caju", "sem_lactose"),
        ("linguiça vegetal à base de glúten", "vegano"),
        ("talharim largo de arroz", "sem_gluten"),
        ("molho tamari cítrico sem glúten", "sem_gluten"),
        ("maionese vegana de alho negro", "vegano"),
        ("melado de cana", "vegano"),  # "mel" não pode casar com "melado"
        ("caramelo salgado", "vegano"),
        ("farinha de mandioca", "sem_gluten"),
        ("ovo caipira", "vegetariano"),  # ovo é permitido para vegetariano
        ("ovo de galinha", "vegetariano"),
        ("couve manteiga", "vegano"),  # é um tipo de couve
        ("pimenta calabresa em flocos", "vegetariano"),  # é um tempero
        ("chocolate amargo sem leite", "sem_lactose"),
    ],
)
def test_libera_ingrediente_compativel(ingrediente, restricao):
    assert violacoes(prato(ingrediente), {restricao}) == []


def test_mensagem_diz_o_ingrediente_e_o_termo():
    [motivo] = violacoes(prato("arroz", "ovo de galinha"), {"vegano"})
    assert "ovo de galinha" in motivo and "vegano" in motivo


def test_restricao_desconhecida_e_ignorada():
    assert violacoes(prato("carne"), {"fit"}) == []

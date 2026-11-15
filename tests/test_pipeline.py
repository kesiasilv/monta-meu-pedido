"""Testes dos 5 passos e do workflow, com o cardápio mini do conftest e dublês (sem API)."""

from mmp.llm.fake import FakeLLMClient
from mmp.pipeline import steps
from mmp.pipeline.workflow import Workflow
from mmp.schemas import PedidoInterpretado


def pedido(**campos) -> PedidoInterpretado:
    return PedidoInterpretado(**{"descricao_livre": "poke", "orcamento": 40, **campos})


def candidatos_filtrados(p, buscador, classificador, cardapio):
    return steps.filtrar_restricoes(steps.buscar(p, buscador, cardapio), p, classificador)


# ------------------------------------------------------------------ passos


def test_buscar_inclui_extras_do_mesmo_restaurante(cardapio, buscador):
    candidatos = steps.buscar(pedido(), buscador, cardapio)
    tipos = {c.prato.tipo for c in candidatos if c.prato.restaurante_id == "r01"}
    assert tipos == {"principal", "bebida", "sobremesa"}


def test_filtrar_mantem_so_quem_tem_todas_as_restricoes(cardapio, buscador, classificador):
    p = pedido(restricoes=["vegano"])
    nomes = {c.prato.nome for c in candidatos_filtrados(p, buscador, classificador, cardapio)}
    assert "Poke de tofu" in nomes
    assert "Poke de salmão" not in nomes
    assert "Mousse de chocolate" not in nomes


def test_carrinho_nunca_passa_do_orcamento(cardapio, buscador, classificador):
    for orcamento in (30, 36, 40, 50, 70):
        p = pedido(orcamento=orcamento)
        cands = candidatos_filtrados(p, buscador, classificador, cardapio)
        carrinho = steps.montar_carrinho(cands, p, cardapio)
        if carrinho:
            assert carrinho.total <= orcamento


def test_carrinho_e_de_um_restaurante_so_e_inclui_extra_quando_cabe(
    cardapio, buscador, classificador
):
    p = pedido(orcamento=40)
    carrinho = steps.montar_carrinho(
        candidatos_filtrados(p, buscador, classificador, cardapio), p, cardapio
    )
    restaurantes = {cardapio.prato(i.prato_id).restaurante_id for i in carrinho.itens}
    assert len(restaurantes) == 1
    assert len(carrinho.itens) == 2


def test_taxa_de_entrega_conta_no_orcamento(cardapio, buscador, classificador):
    # Nhoque custa 38 + 8 de taxa = 46: não cabe em 40.
    p = pedido(descricao_livre="nhoque", orcamento=40, restricoes=["vegetariano", "sem_lactose"])
    cands = [
        c for c in candidatos_filtrados(p, buscador, classificador, cardapio)
        if c.prato.restaurante_id == "r02"
    ]  # fmt: skip
    assert steps.montar_carrinho(cands, p, cardapio) is None


def test_tempo_maximo_exclui_restaurantes_demorados(cardapio, buscador, classificador):
    p = pedido(descricao_livre="lasanha", orcamento=100, tempo_max_min=30)
    carrinho = steps.montar_carrinho(
        candidatos_filtrados(p, buscador, classificador, cardapio), p, cardapio
    )
    assert carrinho.restaurante_id == "r01"


def test_preferencia_desempata(cardapio, buscador, classificador):
    p = pedido(orcamento=31, preferencias=["fit"])
    carrinho = steps.montar_carrinho(
        candidatos_filtrados(p, buscador, classificador, cardapio), p, cardapio
    )
    assert carrinho.itens[0].nome == "Poke de tofu"


def test_resumo_usa_numeros_do_codigo(cardapio, buscador, classificador):
    p = pedido(orcamento=40)
    carrinho = steps.montar_carrinho(
        candidatos_filtrados(p, buscador, classificador, cardapio), p, cardapio
    )
    resumo = steps.resumo_carrinho(carrinho)
    assert steps.reais(carrinho.total) in resumo
    assert "entrega grátis" in resumo


def test_explicacao_que_cita_prato_fora_do_carrinho_cai_no_plano_b(
    cardapio, buscador, classificador
):
    p = pedido(orcamento=40, restricoes=["vegano"])
    cands = candidatos_filtrados(p, buscador, classificador, cardapio)
    carrinho = steps.montar_carrinho(cands, p, cardapio)
    texto_ruim = "Você também pode pedir a Mousse de chocolate!"
    cands_todos = steps.buscar(p, buscador, cardapio)
    explicacao = steps.explicar(p, carrinho, cands_todos, cardapio, FakeLLMClient([texto_ruim]))
    assert explicacao == steps.explicacao_padrao(p)


# ------------------------------------------------------------------ workflow


def criar(cardapio, buscador, classificador, respostas):
    return Workflow(FakeLLMClient(respostas), buscador, classificador, cardapio)


def test_workflow_ok(cardapio, buscador, classificador):
    interpretado = pedido(orcamento=40, restricoes=["sem_lactose"], preferencias=["fit"])
    wf = criar(cardapio, buscador, classificador, [interpretado, "Leve e sem laticínios."])
    resposta = wf.processar("Tô com R$ 40, quero um poke leve sem lactose")
    assert resposta.status == "ok"
    assert resposta.carrinho.total <= 40
    assert "Leve e sem laticínios." in resposta.mensagem
    assert set(wf.tempos_ms) == {"1_interpretar", "2_buscar", "3_filtrar", "4_montar", "5_explicar"}


def test_workflow_pergunta_o_orcamento(cardapio, buscador, classificador):
    wf = criar(cardapio, buscador, classificador, [pedido(orcamento=None)])
    resposta = wf.processar("quero um poke")
    assert resposta.status == "precisa_info"
    assert "Quanto" in resposta.mensagem


def test_workflow_sem_opcao_quando_nada_cabe(cardapio, buscador, classificador):
    wf = criar(cardapio, buscador, classificador, [pedido(orcamento=5)])
    assert wf.processar("poke por 5 reais").status == "sem_opcao"


def test_workflow_sem_opcao_quando_restricao_elimina_tudo(cardapio, buscador, classificador):
    p = pedido(orcamento=100, restricoes=["vegano", "sem_gluten"])
    wf = criar(cardapio, buscador, classificador, [p])
    assert wf.processar("vegano e sem glúten").status == "sem_opcao"


def test_workflow_llm_falhando_pede_para_reformular(cardapio, buscador, classificador):
    wf = criar(cardapio, buscador, classificador, ["lixo", "lixo de novo"])
    assert wf.processar("asdfgh").status == "precisa_info"


def test_nao_troca_o_prato_pedido_por_outro_pouco_parecido(cardapio, buscador, classificador):
    # A busca acha os pokes (relevância 0,9) e um nhoque barato e pouco parecido (0,5).
    # Com R$ 20, nenhum poke cabe. O nhoque caberia, mas não é o que o cliente pediu.
    cands = candidatos_filtrados(pedido(orcamento=100), buscador, classificador, cardapio)
    for c in cands:
        if c.prato.id == "p006":
            c.prato = c.prato.model_copy(update={"preco": 5.0})
    assert steps.montar_carrinho(cands, pedido(orcamento=20), cardapio) is None

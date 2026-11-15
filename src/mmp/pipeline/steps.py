"""Os 5 passos do workflow. Cada um é uma função pura, testável sozinha.

1. interpretar          LLM     texto -> PedidoInterpretado
2. buscar               código  pedido -> candidatos (principais + extras dos mesmos restaurantes)
3. filtrar_restricoes   modelo  candidatos -> só os que respeitam as restrições
4. montar_carrinho      código  candidatos + orçamento -> Carrinho
5. explicar             LLM     carrinho -> texto (com checagem e plano B em código)
"""

import json
import logging
from collections import defaultdict

from mmp import prompts
from mmp.cardapio import Cardapio
from mmp.llm import ErroLLM, LLMClient
from mmp.models.base import Classificador
from mmp.schemas import Candidato, Carrinho, ItemCarrinho, PedidoInterpretado
from mmp.search import Buscador

log = logging.getLogger(__name__)

BONUS_POR_PREFERENCIA = 0.10  # cada preferência atendida (fit, picante, doce) soma isto
BONUS_POR_EXTRA = 0.05  # leve preferência por incluir bebida ou sobremesa quando cabe
# Só entram no carrinho principais com relevância até esta distância do mais relevante.
# Sem isso, se o poke não cabe no orçamento, o montador empurraria um sorvete qualquer.
MARGEM_RELEVANCIA = 0.05


# ------------------------------------------------------------------ 1. interpretar


def interpretar(texto: str, llm: LLMClient) -> PedidoInterpretado:
    """O LLM transforma linguagem natural em dados. O Pydantic valida o resultado."""
    return llm.gerar_json(prompts.SYSTEM_INTERPRETAR, texto, PedidoInterpretado)


# ------------------------------------------------------------------ 2. buscar


def buscar(
    pedido: PedidoInterpretado, buscador: Buscador, cardapio: Cardapio, k: int = 30
) -> list[Candidato]:
    """Pratos principais parecidos com o pedido + bebidas e sobremesas desses restaurantes."""
    encontrados = buscador.buscar(
        pedido.descricao_livre, preco_max=pedido.orcamento, tempo_max=pedido.tempo_max_min, k=k
    )
    candidatos = [
        Candidato(prato=cardapio.prato(prato_id), relevancia=relevancia)
        for prato_id, relevancia in encontrados
    ]
    restaurantes = {c.prato.restaurante_id for c in candidatos}
    for restaurante_id in sorted(restaurantes):
        candidatos += [Candidato(prato=p) for p in cardapio.extras_de(restaurante_id)]
    return candidatos


# ------------------------------------------------------------------ 3. filtrar restrições


def filtrar_restricoes(
    candidatos: list[Candidato], pedido: PedidoInterpretado, classificador: Classificador
) -> list[Candidato]:
    """Usa o classificador treinado para prever as tags e remove quem viola alguma restrição."""
    if not candidatos:
        return []
    previstas = classificador.prever([c.prato.texto() for c in candidatos])
    exigidas = {r.value for r in pedido.restricoes}
    filtrados = []
    for candidato, tags in zip(candidatos, previstas, strict=True):
        candidato.tags_previstas = tags
        if exigidas <= tags:  # o prato precisa ter TODAS as tags exigidas
            filtrados.append(candidato)
    return filtrados


# ------------------------------------------------------------------ 4. montar carrinho


def _pontuacao(candidato: Candidato, preferencias: set[str]) -> float:
    return candidato.relevancia + BONUS_POR_PREFERENCIA * len(
        preferencias & candidato.tags_previstas
    )


def montar_carrinho(
    candidatos: list[Candidato], pedido: PedidoInterpretado, cardapio: Cardapio
) -> Carrinho | None:
    """Testa todas as combinações de 1 principal + 0 ou 1 extra do mesmo restaurante.

    Descarta as que passam do orçamento (com a taxa) ou do tempo e fica com a de maior
    pontuação. Em caso de empate, a mais barata. Sem nenhuma combinação válida, devolve None.
    """
    preferencias = {p.value for p in pedido.preferencias}
    relevancias = [c.relevancia for c in candidatos if c.prato.tipo == "principal"]
    corte = max(relevancias, default=0.0) - MARGEM_RELEVANCIA
    por_restaurante: dict[str, list[Candidato]] = defaultdict(list)
    for c in candidatos:
        if c.prato.tipo == "principal" and c.relevancia < corte:
            continue  # pouco parecido com o que o cliente pediu
        por_restaurante[c.prato.restaurante_id].append(c)

    melhor: tuple[float, float, Carrinho] | None = None
    for restaurante_id, itens in por_restaurante.items():
        restaurante = cardapio.restaurante(restaurante_id)
        if pedido.tempo_max_min and restaurante.tempo_entrega_min > pedido.tempo_max_min:
            continue
        principais = [c for c in itens if c.prato.tipo == "principal"]
        extras = [c for c in itens if c.prato.tipo != "principal"]

        for principal in principais:
            for extra in [None, *extras]:
                escolhidos = [principal] if extra is None else [principal, extra]
                subtotal = round(sum(c.prato.preco for c in escolhidos), 2)
                total = round(subtotal + restaurante.taxa_entrega, 2)
                if pedido.orcamento is not None and total > pedido.orcamento:
                    continue
                pontos = _pontuacao(principal, preferencias)
                if extra is not None:
                    pontos += BONUS_POR_EXTRA + BONUS_POR_PREFERENCIA * len(
                        preferencias & extra.tags_previstas
                    )
                chave = (round(pontos, 6), -total)
                if melhor is None or chave > melhor[:2]:
                    carrinho = Carrinho(
                        restaurante_id=restaurante_id,
                        restaurante_nome=restaurante.nome,
                        itens=[
                            ItemCarrinho(
                                prato_id=c.prato.id,
                                nome=c.prato.nome,
                                preco=c.prato.preco,
                                tipo=c.prato.tipo,
                            )
                            for c in escolhidos
                        ],  # fmt: skip
                        subtotal=subtotal,
                        taxa_entrega=restaurante.taxa_entrega,
                        total=total,
                        tempo_entrega_min=restaurante.tempo_entrega_min,
                    )
                    melhor = (*chave, carrinho)
    return melhor[2] if melhor else None


# ------------------------------------------------------------------ 5. explicar


def reais(valor: float) -> str:
    return f"R$ {valor:.2f}".replace(".", ",")


def resumo_carrinho(carrinho: Carrinho) -> str:
    """Todos os números da resposta vêm daqui, do código. O LLM nunca escreve preço."""
    itens = " + ".join(f"{i.nome} ({reais(i.preco)})" for i in carrinho.itens)
    taxa = (
        "entrega grátis"
        if carrinho.taxa_entrega == 0
        else f"entrega {reais(carrinho.taxa_entrega)}"
    )
    return (
        f"Montei no {carrinho.restaurante_nome}: {itens}. Total {reais(carrinho.total)} "
        f"({taxa}), chega em {carrinho.tempo_entrega_min} min."
    )


def explicacao_padrao(pedido: PedidoInterpretado) -> str:
    """Plano B quando o LLM falha ou cita algo fora do carrinho."""
    criterios = [r.value.replace("_", " ") for r in pedido.restricoes]
    criterios += [p.value for p in pedido.preferencias]
    if not criterios:
        return "Escolhi a combinação mais parecida com o que você pediu dentro do orçamento."
    return f"Escolhi itens que atendem ao que você pediu: {', '.join(criterios)}."


def explicar(
    pedido: PedidoInterpretado,
    carrinho: Carrinho,
    candidatos: list[Candidato],
    cardapio: Cardapio,
    llm: LLMClient,
) -> str:
    """O LLM explica o porquê. O código confere que ele só citou itens do carrinho."""
    no_carrinho = {i.prato_id for i in carrinho.itens}
    entrada = json.dumps(
        {
            "pedido_do_cliente": pedido.model_dump(mode="json"),
            "carrinho": [
                {
                    "nome": cardapio.prato(i.prato_id).nome,
                    "ingredientes": cardapio.prato(i.prato_id).ingredientes,
                }
                for i in carrinho.itens
            ],  # fmt: skip
        },
        ensure_ascii=False,
    )
    try:
        texto = llm.gerar_texto(prompts.SYSTEM_EXPLICAR, entrada)
    except ErroLLM as erro:
        log.warning("Explicação caiu no plano B: %s", erro)
        return explicacao_padrao(pedido)

    fora_do_carrinho = [
        c.prato.nome
        for c in candidatos
        if c.prato.id not in no_carrinho and c.prato.nome.lower() in texto.lower()
    ]
    if fora_do_carrinho or not texto:
        log.warning("Explicação citou itens fora do carrinho (%s). Plano B.", fora_do_carrinho)
        return explicacao_padrao(pedido)
    return texto

"""O orquestrador: executa os 5 passos sempre na mesma ordem e trata os desvios.

A ordem é decidida aqui, em código, e não pelo LLM (ADR-001).
"""

import logging
import time
from dataclasses import dataclass, field

from mmp.cardapio import Cardapio
from mmp.config import Settings
from mmp.llm import ErroLLM, LLMClient
from mmp.models.base import Classificador
from mmp.pipeline import steps
from mmp.schemas import Resposta
from mmp.search import Buscador

log = logging.getLogger(__name__)


@dataclass
class Workflow:
    llm: LLMClient
    buscador: Buscador
    classificador: Classificador
    cardapio: Cardapio
    tempos_ms: dict[str, float] = field(default_factory=dict)

    def _cronometrar(self, nome: str, inicio: float) -> None:
        self.tempos_ms[nome] = round((time.perf_counter() - inicio) * 1000, 1)

    def processar(self, texto: str) -> Resposta:
        self.tempos_ms = {}

        # 1. Interpretar
        t = time.perf_counter()
        try:
            pedido = steps.interpretar(texto, self.llm)
        except ErroLLM:
            log.exception("Falha ao interpretar o pedido")
            return Resposta(
                status="precisa_info",
                mensagem="Não consegui entender o pedido. Pode dizer quanto quer gastar "
                "e o que está com vontade de comer?",
            )
        self._cronometrar("1_interpretar", t)

        if pedido.orcamento is None:
            return Resposta(
                status="precisa_info",
                mensagem="Quanto você quer gastar, no máximo, contando a entrega?",
                pedido=pedido,
            )

        # 2. Buscar
        t = time.perf_counter()
        candidatos = steps.buscar(pedido, self.buscador, self.cardapio)
        self._cronometrar("2_buscar", t)
        if not any(c.prato.tipo == "principal" for c in candidatos):
            prazo = f" que chegue em até {pedido.tempo_max_min} min" if pedido.tempo_max_min else ""
            return Resposta(
                status="sem_opcao",
                mensagem=f"Não encontrei pratos até {steps.reais(pedido.orcamento)}{prazo}. "
                "Quer aumentar o orçamento ou o tempo de espera?",
                pedido=pedido,
            )

        # 3. Filtrar restrições
        t = time.perf_counter()
        candidatos = steps.filtrar_restricoes(candidatos, pedido, self.classificador)
        self._cronometrar("3_filtrar", t)
        if not any(c.prato.tipo == "principal" for c in candidatos):
            restricoes = ", ".join(r.value.replace("_", " ") for r in pedido.restricoes)
            return Resposta(
                status="sem_opcao",
                mensagem=f"Não encontrei pratos {restricoes} com essa descrição dentro do "
                "orçamento. Quer tentar outro tipo de comida?",
                pedido=pedido,
            )

        # 4. Montar carrinho
        t = time.perf_counter()
        carrinho = steps.montar_carrinho(candidatos, pedido, self.cardapio)
        self._cronometrar("4_montar", t)
        if carrinho is None:
            return Resposta(
                status="sem_opcao",
                mensagem="Os pratos que servem passam do orçamento quando somo a taxa de "
                "entrega. Quer aumentar um pouco o valor?",
                pedido=pedido,
            )

        # 5. Explicar
        t = time.perf_counter()
        explicacao = steps.explicar(pedido, carrinho, candidatos, self.cardapio, self.llm)
        self._cronometrar("5_explicar", t)

        log.info("Pedido processado em %s ms", self.tempos_ms)
        return Resposta(
            status="ok",
            mensagem=f"{steps.resumo_carrinho(carrinho)}\n\n{explicacao}",
            carrinho=carrinho,
            pedido=pedido,
        )


def criar_workflow(config: Settings) -> Workflow:
    """Monta o workflow com as peças reais, escolhidas pelo .env."""
    from mmp.llm import criar_cliente
    from mmp.models import criar_classificador
    from mmp.search import criar_buscador

    cardapio = Cardapio.carregar(config.processed_dir)
    return Workflow(
        llm=criar_cliente(config),
        buscador=criar_buscador(config, cardapio),
        classificador=criar_classificador(config),
        cardapio=cardapio,
    )


def main() -> None:
    """Uso: uv run python -m mmp.pipeline.workflow "Tô com R$ 40, quero algo leve" """
    import sys

    from mmp.config import settings
    from mmp.logs import configurar_logs

    configurar_logs()
    texto = " ".join(sys.argv[1:]) or "Tô com R$ 40, quero algo leve, sem lactose, em 40 min"
    resposta = criar_workflow(settings).processar(texto)
    print(f"\nPedido: {texto}\nStatus: {resposta.status}\n\n{resposta.mensagem}")


if __name__ == "__main__":
    main()

"""API HTTP: a porta de entrada para programas (um app iOS, um bot, outro serviço).

Uso: make api   e abra http://localhost:8000/docs
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI

from mmp import __version__
from mmp.config import settings
from mmp.pipeline.workflow import Workflow, criar_workflow
from mmp.schemas import PedidoEntrada, Resposta

app = FastAPI(
    title="Monta Meu Pedido",
    version=__version__,
    description="Recebe um pedido em linguagem natural e devolve um carrinho que respeita "
    "orçamento, restrições alimentares e tempo de entrega.",
)


@lru_cache
def obter_workflow() -> Workflow:
    """Cria o workflow uma vez só (carregar modelos é lento) e reaproveita entre requisições."""
    return criar_workflow(settings)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "versao": __version__}


@app.post("/pedido", response_model=Resposta)
def fazer_pedido(
    entrada: PedidoEntrada, workflow: Annotated[Workflow, Depends(obter_workflow)]
) -> Resposta:
    return workflow.processar(entrada.texto)

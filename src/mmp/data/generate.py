"""Gera cardápios sintéticos com o LLM, um restaurante por chamada.

Cada restaurante gerado é salvo na hora em data/raw/, então se a geração cair no meio
(limite de requisições, internet), rodar de novo continua de onde parou.

Uso: uv run python -m mmp.data.generate
"""

import json
import logging
import time
from typing import Literal

from pydantic import BaseModel, Field

from mmp import prompts
from mmp.config import settings
from mmp.data.validate import processar
from mmp.llm import ErroLLM, criar_cliente

log = logging.getLogger(__name__)

CATEGORIAS = [
    "japonesa", "poke havaiano", "brasileira caseira", "marmita fit", "vegana",
    "vegetariana", "hamburgueria", "hamburgueria vegana", "pizzaria", "italiana",
    "mexicana", "árabe", "nordestina", "mineira", "chinesa",
    "tailandesa", "indiana", "coreana", "peruana", "frutos do mar",
    "churrascaria", "saladas e bowls", "açaí e sucos", "padaria e café", "pastelaria",
    "creperia", "doceria", "sorveteria", "lanchonete", "sem glúten",
]  # fmt: skip

PRINCIPAIS, BEBIDAS, SOBREMESAS = 9, 3, 2
PAUSA_ENTRE_CHAMADAS_S = 7  # o plano gratuito do Gemini limita requisições por minuto

Tag = Literal["vegano", "vegetariano", "sem_lactose", "sem_gluten", "fit", "picante", "doce"]


class ItemGerado(BaseModel):
    nome: str
    descricao: str = Field(description="Uma frase vendedora, como num cardápio")
    ingredientes: list[str]
    preco: float
    tipo: Literal["principal", "bebida", "sobremesa"]
    tags: list[Tag]


class RestauranteGerado(BaseModel):
    nome: str
    taxa_entrega: float
    tempo_entrega_min: int
    itens: list[ItemGerado]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    llm = criar_cliente(settings)
    raw_path = settings.data_dir / "raw" / "restaurantes_raw.jsonl"
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    feitas = set()
    if raw_path.exists():
        feitas = {json.loads(linha)["categoria"] for linha in raw_path.read_text().splitlines()}
        if feitas:
            log.info("Continuando: %d categorias já geradas.", len(feitas))

    for i, categoria in enumerate(CATEGORIAS, start=1):
        if categoria in feitas:
            continue
        log.info("[%d/%d] Gerando %s...", i, len(CATEGORIAS), categoria)
        user = prompts.USER_GERAR_CARDAPIO.format(
            categoria=categoria, principais=PRINCIPAIS, bebidas=BEBIDAS, sobremesas=SOBREMESAS
        )
        try:
            gerado = llm.gerar_json(
                prompts.SYSTEM_GERAR_CARDAPIO, user, RestauranteGerado, temperatura=0.9
            )
        except ErroLLM as erro:
            log.error("Pulando %s: %s", categoria, erro)
            continue
        with raw_path.open("a", encoding="utf-8") as arquivo:
            registro = {"categoria": categoria, **gerado.model_dump()}
            arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
        time.sleep(PAUSA_ENTRE_CHAMADAS_S)

    log.info("Tokens usados: %s", llm.uso)
    relatorio = processar(raw_path, settings.processed_dir)
    log.info("Dados prontos: %s", relatorio)


if __name__ == "__main__":
    main()

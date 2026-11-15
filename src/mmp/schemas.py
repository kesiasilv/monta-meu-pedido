"""Contratos de dados. Todo dado que passa entre módulos é um destes modelos."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

TAGS: list[str] = [
    "vegano",
    "vegetariano",
    "sem_lactose",
    "sem_gluten",
    "fit",
    "picante",
    "doce",
]


class Restricao(StrEnum):
    """Obrigatória: um prato sem a tag exigida sai do pedido."""

    VEGANO = "vegano"
    VEGETARIANO = "vegetariano"
    SEM_LACTOSE = "sem_lactose"
    SEM_GLUTEN = "sem_gluten"


class Preferencia(StrEnum):
    """Desejável: só aumenta a pontuação do prato."""

    FIT = "fit"
    PICANTE = "picante"
    DOCE = "doce"


TipoItem = Literal["principal", "bebida", "sobremesa"]


class Restaurante(BaseModel):
    id: str
    nome: str
    categoria: str
    taxa_entrega: float = Field(ge=0)
    tempo_entrega_min: int = Field(gt=0)


class Prato(BaseModel):
    id: str
    restaurante_id: str
    nome: str
    descricao: str
    ingredientes: list[str]
    preco: float = Field(gt=0)
    tipo: TipoItem
    # Rótulo de referência (gerado pelo LLM e revisado por amostragem).
    # O workflow nunca usa este campo: ele usa as tags previstas pelo classificador.
    tags: list[str] = []

    def texto(self) -> str:
        """Texto de entrada dos classificadores."""
        return f"{self.nome}. {self.descricao}. Ingredientes: {', '.join(self.ingredientes)}"


class PedidoInterpretado(BaseModel):
    """Saída do passo 1 (interpretar)."""

    orcamento: float | None = Field(None, gt=0, description="Valor máximo em reais")
    restricoes: list[Restricao] = []
    preferencias: list[Preferencia] = []
    descricao_livre: str = Field(description="O que o cliente quer comer, em poucas palavras")
    tempo_max_min: int | None = Field(None, gt=0, description="Tempo máximo de entrega")


class Candidato(BaseModel):
    """Prato encontrado na busca, com a relevância e as tags previstas pelo classificador."""

    prato: Prato
    relevancia: float = 0.0
    tags_previstas: set[str] = set()


class ItemCarrinho(BaseModel):
    prato_id: str
    nome: str
    preco: float
    tipo: TipoItem


class Carrinho(BaseModel):
    """Saída do passo 4 (montar carrinho)."""

    restaurante_id: str
    restaurante_nome: str
    itens: list[ItemCarrinho]
    subtotal: float
    taxa_entrega: float
    total: float
    tempo_entrega_min: int


class PedidoEntrada(BaseModel):
    """Corpo do POST /pedido."""

    texto: str = Field(min_length=3, max_length=500)


class Resposta(BaseModel):
    """Saída do workflow e da API."""

    status: Literal["ok", "precisa_info", "sem_opcao"]
    mensagem: str
    carrinho: Carrinho | None = None
    pedido: PedidoInterpretado | None = None

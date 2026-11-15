"""Interface única para qualquer provedor de LLM.

O resto do código só conhece `LLMClient`. Trocar de provedor é mudar o .env.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ErroLLM(Exception):
    """O LLM falhou ou devolveu algo que não segue o contrato, mesmo depois de tentar de novo."""


class ErroDefinitivo(ErroLLM):
    """Erro que não adianta repetir: chave inválida, modelo inexistente, pedido malformado."""


@dataclass
class Uso:
    """Tokens consumidos, para estimar custo na avaliação."""

    tokens_entrada: int = 0
    tokens_saida: int = 0
    chamadas: int = 0


class LLMClient(Protocol):
    uso: Uso

    def gerar_json(
        self, system: str, user: str, schema: type[T], temperatura: float = 0.0
    ) -> T: ...

    def gerar_texto(self, system: str, user: str, temperatura: float = 0.3) -> str: ...


def instrucao_json(schema: type[BaseModel]) -> str:
    esquema = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    return (
        "Responda APENAS com um objeto JSON válido, sem texto antes ou depois e sem markdown, "
        f"seguindo este JSON Schema:\n{esquema}"
    )


def extrair_json(texto: str) -> str:
    """Tira cercas de markdown e qualquer texto fora do objeto JSON."""
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim == -1:
        return texto.strip()
    return texto[inicio : fim + 1]


class ClienteBase(ABC):
    """Implementa validação, nova tentativa e backoff. Cada provedor só implementa `_completar`."""

    tentativas_rede = 3
    espera_inicial_s = 10.0

    def __init__(self) -> None:
        self.uso = Uso()

    @abstractmethod
    def _completar(self, system: str, user: str, json_mode: bool, temperatura: float) -> str:
        """Faz uma chamada ao provedor e devolve o texto da resposta."""

    def _eh_definitivo(self, erro: Exception) -> bool:
        """Cada provedor diz quais erros não adianta repetir. Por padrão, todos são repetidos."""
        return False

    def _chamar(self, system: str, user: str, json_mode: bool, temperatura: float) -> str:
        espera = self.espera_inicial_s
        for tentativa in range(1, self.tentativas_rede + 1):
            try:
                self.uso.chamadas += 1
                return self._completar(system, user, json_mode, temperatura)
            except Exception as erro:  # erros de rede e limite de requisições
                if self._eh_definitivo(erro):
                    raise ErroDefinitivo(f"Erro que não adianta repetir: {erro}") from erro
                if tentativa == self.tentativas_rede:
                    raise ErroLLM(f"Falha ao chamar o LLM: {erro}") from erro
                log.warning("LLM falhou (%s). Nova tentativa em %.0f s.", erro, espera)
                time.sleep(espera)
                espera *= 2
        raise AssertionError("inalcançável")

    def gerar_json(self, system: str, user: str, schema: type[T], temperatura: float = 0.0) -> T:
        system_completo = f"{system}\n\n{instrucao_json(schema)}"
        texto = self._chamar(system_completo, user, json_mode=True, temperatura=temperatura)
        try:
            return schema.model_validate_json(extrair_json(texto))
        except ValidationError as erro:
            log.warning("JSON inválido do LLM. Pedindo correção uma vez.")
            correcao = (
                f"{user}\n\nSua resposta anterior não seguiu o schema. Erros: {erro}. "
                "Responda de novo, corrigindo."
            )
            texto = self._chamar(system_completo, correcao, json_mode=True, temperatura=0.0)
            try:
                return schema.model_validate_json(extrair_json(texto))
            except ValidationError as erro2:
                raise ErroLLM(f"JSON inválido mesmo após correção: {erro2}") from erro2

    def gerar_texto(self, system: str, user: str, temperatura: float = 0.3) -> str:
        return self._chamar(system, user, json_mode=False, temperatura=temperatura).strip()

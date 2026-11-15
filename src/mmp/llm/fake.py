"""LLM falso para testes: devolve respostas fixas, na ordem, sem chamar API nenhuma."""

from pydantic import BaseModel

from mmp.llm.base import ClienteBase


class FakeLLMClient(ClienteBase):
    espera_inicial_s = 0.0

    def __init__(self, respostas: list[str | BaseModel | Exception]) -> None:
        super().__init__()
        self.respostas = list(respostas)
        self.chamadas: list[dict] = []

    def _completar(self, system: str, user: str, json_mode: bool, temperatura: float) -> str:
        self.chamadas.append({"system": system, "user": user, "json_mode": json_mode})
        if not self.respostas:
            raise AssertionError("FakeLLMClient chamado mais vezes do que o esperado")
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        if isinstance(resposta, BaseModel):
            return resposta.model_dump_json()
        return resposta

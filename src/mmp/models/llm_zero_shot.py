"""Referência: o LLM classificando sem treino nenhum, só com as definições das tags no prompt."""

import json
from typing import Literal

from pydantic import BaseModel

from mmp import prompts
from mmp.llm import ErroLLM, LLMClient

Tag = Literal["vegano", "vegetariano", "sem_lactose", "sem_gluten", "fit", "picante", "doce"]


class ClassificacaoPrato(BaseModel):
    indice: int
    tags: list[Tag]


class ClassificacaoLote(BaseModel):
    resultados: list[ClassificacaoPrato]


class LLMZeroShotClassificador:
    nome = "llm_zero_shot"

    def __init__(self, llm: LLMClient, lote: int = 10) -> None:
        self.llm = llm
        self.lote = lote

    def prever(self, textos: list[str]) -> list[set[str]]:
        saida: list[set[str]] = []
        for inicio in range(0, len(textos), self.lote):
            parte = textos[inicio : inicio + self.lote]
            entrada = json.dumps(
                [{"indice": i, "prato": t} for i, t in enumerate(parte)], ensure_ascii=False
            )
            try:
                resposta = self.llm.gerar_json(
                    prompts.SYSTEM_CLASSIFICAR, entrada, ClassificacaoLote
                )
                por_indice = {r.indice: set(r.tags) for r in resposta.resultados}
            except ErroLLM:
                por_indice = {}
            saida.extend(por_indice.get(i, set()) for i in range(len(parte)))
        return saida

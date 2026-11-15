"""Valida, limpa e numera os dados brutos gerados pelo LLM."""

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from mmp.schemas import TAGS, Prato, Restaurante

log = logging.getLogger(__name__)


def normalizar_tags(tags: list[str]) -> tuple[list[str], int]:
    """Aplica as regras de consistência e devolve (tags, número de correções).

    Todo prato vegano também é vegetariano e sem lactose, por definição.
    """
    conjunto = {t for t in tags if t in TAGS}
    correcoes = 0
    if "vegano" in conjunto:
        for implicada in ("vegetariano", "sem_lactose"):
            if implicada not in conjunto:
                conjunto.add(implicada)
                correcoes += 1
    return [t for t in TAGS if t in conjunto], correcoes


def processar(raw_path: Path, saida: Path) -> dict:
    restaurantes: list[Restaurante] = []
    pratos: list[Prato] = []
    nomes_vistos: set[str] = set()
    stats = {"itens_brutos": 0, "invalidos": 0, "duplicados": 0, "correcoes_de_tag": 0}

    linhas = raw_path.read_text(encoding="utf-8").splitlines()
    for r_idx, linha in enumerate(linhas, start=1):
        bruto = json.loads(linha)
        restaurante_id = f"r{r_idx:02d}"
        try:
            restaurante = Restaurante(
                id=restaurante_id,
                nome=bruto["nome"],
                categoria=bruto["categoria"],
                taxa_entrega=round(float(bruto["taxa_entrega"]), 2),
                tempo_entrega_min=int(bruto["tempo_entrega_min"]),
            )
        except (ValidationError, KeyError, ValueError) as erro:
            log.warning("Restaurante inválido descartado: %s", erro)
            continue
        restaurantes.append(restaurante)

        for item in bruto.get("itens", []):
            stats["itens_brutos"] += 1
            chave = item.get("nome", "").strip().lower()
            if chave in nomes_vistos:
                stats["duplicados"] += 1
                continue
            tags, correcoes = normalizar_tags(item.get("tags", []))
            try:
                prato = Prato(
                    id=f"p{len(pratos) + 1:03d}",
                    restaurante_id=restaurante_id,
                    nome=item["nome"].strip(),
                    descricao=item["descricao"].strip(),
                    ingredientes=[i.strip() for i in item["ingredientes"] if i.strip()],
                    preco=round(float(item["preco"]), 2),
                    tipo=item["tipo"],
                    tags=tags,
                )
            except (ValidationError, KeyError, ValueError, AttributeError):
                stats["invalidos"] += 1
                continue
            stats["correcoes_de_tag"] += correcoes
            nomes_vistos.add(chave)
            pratos.append(prato)

    stats["restaurantes"] = len(restaurantes)
    stats["pratos"] = len(pratos)
    stats["pratos_por_tag"] = {t: sum(t in p.tags for p in pratos) for t in TAGS}

    saida.mkdir(parents=True, exist_ok=True)
    salvar_json(saida / "restaurantes.json", [r.model_dump() for r in restaurantes])
    salvar_json(saida / "pratos.json", [p.model_dump() for p in pratos])
    salvar_json(saida / "relatorio_dados.json", stats)
    return stats


def salvar_json(caminho: Path, dados) -> None:
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

"""Revisão humana dos rótulos gerados pelo LLM.

1. `amostrar`: sorteia 50 pratos e cria data/processed/revisao_50.csv.
   As colunas de tag já vêm preenchidas com o rótulo do LLM (1 = tem, 0 = não tem).
2. Você abre o CSV e corrige só o que estiver errado, segundo as definições das tags.
3. `calcular`: mede a concordância entre o LLM e a sua revisão.

Uso: uv run python -m mmp.data.review amostrar | calcular
"""

import csv
import json
import random
import sys

from mmp.cardapio import Cardapio
from mmp.config import settings
from mmp.schemas import TAGS

TAMANHO_AMOSTRA = 50


def caminho_csv():
    return settings.processed_dir / "revisao_50.csv"


def amostrar() -> None:
    if caminho_csv().exists():
        print(f"{caminho_csv()} já existe. Apague o arquivo se quiser sortear de novo.")
        return
    cardapio = Cardapio.carregar(settings.processed_dir)
    amostra = random.Random(settings.seed).sample(cardapio.pratos, TAMANHO_AMOSTRA)
    with caminho_csv().open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["id", "nome", "ingredientes", "tags_llm", *TAGS])
        for p in amostra:
            escritor.writerow(
                [p.id, p.nome, "; ".join(p.ingredientes), " ".join(p.tags)]
                + [int(t in p.tags) for t in TAGS]
            )
    print(f"Revise {caminho_csv()} e depois rode: make concordancia")


def calcular() -> dict:
    with caminho_csv().open(encoding="utf-8") as arquivo:
        linhas = list(csv.DictReader(arquivo))

    def concorda(linha: dict, tag: str) -> bool:
        """O rótulo do LLM e a sua revisão dizem a mesma coisa para esta tag?"""
        return (tag in linha["tags_llm"].split()) == (linha[tag].strip() == "1")

    concordancia_por_tag = {
        tag: round(sum(concorda(linha, tag) for linha in linhas) / len(linhas), 3) for tag in TAGS
    }
    pratos_sem_erro = sum(all(concorda(linha, t) for t in TAGS) for linha in linhas)
    resultado = {
        "pratos_revisados": len(linhas),
        "pratos_sem_nenhum_erro": pratos_sem_erro,
        "taxa_pratos_corretos": round(pratos_sem_erro / len(linhas), 3),
        "concordancia_por_tag": concordancia_por_tag,
    }
    destino = settings.processed_dir / "revisao_resultado.json"
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return resultado


if __name__ == "__main__":
    comando = sys.argv[1] if len(sys.argv) > 1 else ""
    {"amostrar": amostrar, "calcular": calcular}.get(comando, lambda: print(__doc__))()

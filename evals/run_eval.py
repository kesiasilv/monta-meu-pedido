"""Laboratório de avaliação (seção 9 do design doc).

Pergunta A: o classificador próprio vale a pena contra um LLM?
  Baseline, BERTimbau e LLM zero-shot no conjunto de TESTE: F1, custo e latência.
Pergunta B: o workflow respeita as regras?
  30 pedidos com regras conhecidas, checados contra os rótulos de referência.

Uso:
  uv run python -m evals.run_eval              (tudo)
  uv run python -m evals.run_eval --sem-llm    (só baseline e BERTimbau, sem gastar cota)
"""

import argparse
import json
import logging
import statistics
import time
from datetime import datetime
from pathlib import Path

from mmp.cardapio import Cardapio
from mmp.config import settings
from mmp.data.split import carregar_split
from mmp.logs import configurar_logs
from mmp.models.metrics import calcular_metricas
from mmp.tags import binarizar

log = logging.getLogger(__name__)
PASTA = Path(__file__).parent
PAUSA_ENTRE_PEDIDOS_S = 8  # o plano gratuito limita 15 requisições por minuto


# ------------------------------------------------------------------ pergunta A


def avaliar_classificador(classificador, teste: list[dict], llm=None) -> dict:
    textos = [r["texto"] for r in teste]
    inicio = time.perf_counter()
    previstas = classificador.prever(textos)
    segundos = time.perf_counter() - inicio
    resultado = calcular_metricas(binarizar([r["tags"] for r in teste]), binarizar(previstas))
    resultado["latencia_ms_por_prato"] = round(segundos * 1000 / len(textos), 2)
    if llm is not None:
        custo = (
            llm.uso.tokens_entrada * settings.llm_preco_entrada_usd_por_milhao
            + llm.uso.tokens_saida * settings.llm_preco_saida_usd_por_milhao
        ) / 1_000_000
        resultado["custo_usd_por_1000_pratos"] = round(custo / len(textos) * 1000, 4)
        resultado["tokens"] = {"entrada": llm.uso.tokens_entrada, "saida": llm.uso.tokens_saida}
    else:
        resultado["custo_usd_por_1000_pratos"] = 0.0  # roda localmente, em CPU
    return resultado


def pergunta_a(usar_llm: bool) -> dict:
    teste = carregar_split("test")
    resultados = {}

    from mmp.models.baseline import BaselineClassificador

    resultados["baseline_tfidf"] = avaliar_classificador(
        BaselineClassificador.carregar(settings.artifacts_dir / "baseline.joblib"), teste
    )
    try:
        from mmp.models.bertimbau import BertimbauClassificador

        bert = BertimbauClassificador(settings.hf_model_id)
        resultados["bertimbau"] = avaliar_classificador(bert, teste)
    except Exception as erro:  # modelo ainda não publicado, sem internet etc.
        log.warning("BERTimbau não avaliado: %s", erro)

    if usar_llm:
        from mmp.llm import criar_cliente
        from mmp.models.llm_zero_shot import LLMZeroShotClassificador

        llm = criar_cliente(settings)
        resultados["llm_zero_shot"] = avaliar_classificador(
            LLMZeroShotClassificador(llm), teste, llm
        )
    return resultados


# ------------------------------------------------------------------ pergunta B


def checar_caso(caso: dict, resposta, cardapio: Cardapio) -> dict:
    checagem = {
        "id": caso["id"],
        "categoria": caso["categoria"],
        "status_esperado": caso["status"],
        "status_obtido": resposta.status,
        "status_correto": resposta.status == caso["status"],
    }
    if resposta.pedido is not None:
        checagem["orcamento_entendido"] = resposta.pedido.orcamento == caso["orcamento"]
        checagem["restricoes_entendidas"] = {r.value for r in resposta.pedido.restricoes} == set(
            caso["restricoes"]
        )
    if resposta.carrinho is not None:
        c = resposta.carrinho
        pratos = [cardapio.prato(i.prato_id) for i in c.itens]
        checagem["respeita_orcamento"] = caso["orcamento"] is None or c.total <= caso["orcamento"]
        checagem["respeita_tempo"] = (
            caso["tempo_max_min"] is None or c.tempo_entrega_min <= caso["tempo_max_min"]
        )
        # Checado contra os rótulos de REFERÊNCIA, não contra o que o classificador previu.
        violacoes = [
            f"{p.nome} sem {r}" for p in pratos for r in caso["restricoes"] if r not in p.tags
        ]
        checagem["respeita_restricoes"] = not violacoes
        checagem["violacoes"] = violacoes
        checagem["carrinho"] = [p.nome for p in pratos]
        checagem["total"] = c.total
    return checagem


def pergunta_b() -> dict:
    from mmp.pipeline.workflow import criar_workflow

    casos = json.loads((PASTA / "casos_workflow.json").read_text(encoding="utf-8"))
    workflow = criar_workflow(settings)
    checagens, latencias = [], []
    for i, caso in enumerate(casos, start=1):
        log.info("[%d/%d] %s", i, len(casos), caso["texto"])
        inicio = time.perf_counter()
        resposta = workflow.processar(caso["texto"])
        latencias.append((time.perf_counter() - inicio) * 1000)
        checagens.append(checar_caso(caso, resposta, workflow.cardapio))
        time.sleep(PAUSA_ENTRE_PEDIDOS_S)

    def taxa(chave: str) -> float | None:
        valores = [c[chave] for c in checagens if chave in c]
        return round(sum(valores) / len(valores), 3) if valores else None

    ordenadas = sorted(latencias)
    return {
        "casos": len(casos),
        "status_correto": taxa("status_correto"),
        "orcamento_entendido": taxa("orcamento_entendido"),
        "restricoes_entendidas": taxa("restricoes_entendidas"),
        "carrinhos_montados": sum("respeita_orcamento" in c for c in checagens),
        "respeita_orcamento": taxa("respeita_orcamento"),
        "respeita_tempo": taxa("respeita_tempo"),
        "respeita_restricoes": taxa("respeita_restricoes"),
        "latencia_ms_p50": round(statistics.median(latencias)),
        "latencia_ms_p95": round(ordenadas[int(0.95 * (len(ordenadas) - 1))]),
        "por_caso": checagens,
    }


# ------------------------------------------------------------------ relatório


def tabela_markdown(r: dict) -> str:
    linhas = [
        f"# Resultados da avaliação · {r['data']}",
        "",
        f"LLM: `{r['llm']}` · classificador do workflow: `{r['classificador_workflow']}`",
        "",
        "## A. Classificadores no conjunto de teste",
        "",
        "| Modelo | F1 micro | F1 macro | Acerto exato | Latência (ms/prato) | Custo (USD/1.000) |",
        "|---|---|---|---|---|---|",
    ]
    for nome, m in r.get("classificadores", {}).items():
        linhas.append(
            f"| {nome} | {m['f1_micro']:.3f} | {m['f1_macro']:.3f} | {m['acerto_exato']:.3f} | "
            f"{m['latencia_ms_por_prato']} | {m['custo_usd_por_1000_pratos']} |"
        )
    if "classificadores" in r:
        nomes = list(r["classificadores"])
        linhas += ["", "### F1 por tag", "", "| Tag | " + " | ".join(nomes) + " |"]
        linhas.append("|---" * (len(nomes) + 1) + "|")
        tags = next(iter(r["classificadores"].values()))["por_tag"]
        for tag in tags:
            valores = " | ".join(
                f"{r['classificadores'][n]['por_tag'][tag]['f1']:.3f}" for n in nomes
            )
            linhas.append(f"| {tag} | {valores} |")

    if "workflow" in r:
        w = r["workflow"]
        linhas += [
            "",
            "## B. Workflow em 30 pedidos",
            "",
            f"- Status correto: **{w['status_correto']:.0%}**",
            f"- Orçamento entendido: {w['orcamento_entendido']:.0%} · "
            f"Restrições entendidas: {w['restricoes_entendidas']:.0%}",
            f"- Carrinhos montados: {w['carrinhos_montados']}",
            f"- Respeita orçamento: **{w['respeita_orcamento']:.0%}** · "
            f"tempo: **{w['respeita_tempo']:.0%}** · "
            f"restrições: **{w['respeita_restricoes']:.0%}**",
            f"- Latência p50 {w['latencia_ms_p50']} ms · p95 {w['latencia_ms_p95']} ms",
            "",
            "| Caso | Categoria | Esperado | Obtido | Carrinho | Violações |",
            "|---|---|---|---|---|---|",
        ]
        for c in w["por_caso"]:
            carrinho = ", ".join(c.get("carrinho", [])) or "-"
            violacoes = ", ".join(c.get("violacoes", [])) or "-"
            linhas.append(
                f"| {c['id']} | {c['categoria']} | {c['status_esperado']} | "
                f"{c['status_obtido']} | {carrinho} | {violacoes} |"
            )
    return "\n".join(linhas) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sem-llm", action="store_true", help="não chama o LLM")
    parser.add_argument("--sem-workflow", action="store_true", help="pula a pergunta B")
    args = parser.parse_args()
    configurar_logs()

    modelo_llm = (
        settings.gemini_model if settings.llm_provider == "gemini" else settings.claude_model
    )
    resultado = {
        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "llm": f"{settings.llm_provider}/{modelo_llm}",
        "classificador_workflow": settings.classificador,
        "classificadores": pergunta_a(usar_llm=not args.sem_llm),
    }
    if not args.sem_llm and not args.sem_workflow:
        resultado["workflow"] = pergunta_b()

    pasta = PASTA / "resultados"
    pasta.mkdir(exist_ok=True)
    carimbo = datetime.now().strftime("%Y%m%d_%H%M")
    (pasta / f"{carimbo}.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    markdown = tabela_markdown(resultado)
    (pasta / f"{carimbo}.md").write_text(markdown, encoding="utf-8")
    (PASTA / "resultados.md").write_text(markdown, encoding="utf-8")
    print(markdown)


if __name__ == "__main__":
    main()

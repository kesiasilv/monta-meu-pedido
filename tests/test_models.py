import numpy as np

from mmp.llm.fake import FakeLLMClient
from mmp.models.baseline import BaselineClassificador
from mmp.models.llm_zero_shot import LLMZeroShotClassificador
from mmp.models.metrics import ajustar_limiares, calcular_metricas
from mmp.tags import binarizar


def test_binarizar_segue_a_ordem_das_tags():
    y = binarizar([["fit", "vegano"], []])
    assert y.tolist() == [[1, 0, 0, 0, 1, 0, 0], [0] * 7]


def test_ajustar_limiares_acha_o_corte_que_separa_as_classes():
    y = np.zeros((4, 7), dtype=int)
    y[:2, 0] = 1
    probs = np.full((4, 7), 0.05)
    probs[:, 0] = [0.35, 0.30, 0.20, 0.10]
    limiares = ajustar_limiares(probs, y)
    assert 0.20 < limiares[0] <= 0.30


def test_metricas_perfeitas():
    y = binarizar([["fit"], ["doce"], ["vegano", "vegetariano"]])
    m = calcular_metricas(y, y)
    assert m["f1_micro"] == 1.0 and m["acerto_exato"] == 1.0


def test_baseline_aprende_palavras_obvias():
    textos = ["brigadeiro doce de chocolate", "pudim doce de leite"] * 5 + [
        "frango grelhado com salada",
        "salmão grelhado com legumes",
    ] * 5
    tags = [["doce"]] * 10 + [["fit"]] * 10
    modelo = BaselineClassificador.treinar(textos, binarizar(tags), seed=42)
    assert "doce" in modelo.prever(["bolo doce"])[0]


def test_zero_shot_monta_lotes_e_tolera_falha():
    resposta = '{"resultados": [{"indice": 0, "tags": ["doce"]}, {"indice": 1, "tags": []}]}'
    llm = FakeLLMClient([resposta, "erro", "erro de novo"])
    clf = LLMZeroShotClassificador(llm, lote=2)
    assert clf.prever(["pudim", "arroz", "salada"]) == [{"doce"}, set(), set()]

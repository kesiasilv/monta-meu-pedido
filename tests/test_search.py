"""O ChromaDB e o modelo de embeddings não entram na CI. Aqui testamos a lógica pura: os filtros."""

from mmp.search import montar_filtro


def test_sem_preco_nem_tempo_filtra_so_pratos_principais():
    assert montar_filtro(None, None) == {"tipo": "principal"}


def test_preco_e_tempo_viram_condicoes_com_and():
    filtro = montar_filtro(40, 30)
    assert filtro == {
        "$and": [
            {"tipo": "principal"},
            {"preco": {"$lte": 40.0}},
            {"tempo_entrega_min": {"$lte": 30}},
        ]
    }


def test_so_preco():
    assert montar_filtro(25.5, None)["$and"][1] == {"preco": {"$lte": 25.5}}

import json

from mmp.data.split import dividir
from mmp.data.validate import normalizar_tags, processar
from mmp.schemas import Prato


def test_vegano_implica_vegetariano_e_sem_lactose():
    tags, correcoes = normalizar_tags(["vegano"])
    assert tags == ["vegano", "vegetariano", "sem_lactose"]
    assert correcoes == 2


def test_normalizar_descarta_tags_desconhecidas_e_ordena():
    tags, _ = normalizar_tags(["doce", "inventada", "fit"])
    assert tags == ["fit", "doce"]


def test_processar_descarta_invalidos_e_duplicados(tmp_path):
    item = {
        "nome": "Poke",
        "descricao": "bom",
        "ingredientes": ["arroz"],
        "preco": 30,
        "tipo": "principal",
        "tags": ["vegano"],
    }
    bruto = {
        "categoria": "poke",
        "nome": "Poke Place",
        "taxa_entrega": 5,
        "tempo_entrega_min": 25,
        "itens": [item, dict(item), {**item, "nome": "Caro", "preco": -1}],
    }
    raw = tmp_path / "raw.jsonl"
    raw.write_text(json.dumps(bruto) + "\n")

    stats = processar(raw, tmp_path / "out")

    assert stats["pratos"] == 1
    assert stats["duplicados"] == 1
    assert stats["invalidos"] == 1
    pratos = json.loads((tmp_path / "out" / "pratos.json").read_text())
    assert pratos[0]["id"] == "p001"
    assert pratos[0]["tags"] == ["vegano", "vegetariano", "sem_lactose"]


def test_dividir_e_reprodutivel_e_sem_sobreposicao():
    tags_possiveis = [["vegano", "vegetariano", "sem_lactose"], ["fit"], ["doce"], []]
    pratos = [
        Prato(
            id=f"p{i:03d}",
            restaurante_id="r01",
            nome=f"Prato {i}",
            descricao="x",
            ingredientes=["y"],
            preco=10,
            tipo="principal",
            tags=tags_possiveis[i % 4],
        )
        for i in range(100)
    ]
    a = dividir(pratos, seed=42)
    b = dividir(pratos, seed=42)

    ids = {nome: {p.id for p in lista} for nome, lista in a.items()}
    assert ids == {nome: {p.id for p in lista} for nome, lista in b.items()}
    assert len(ids["train"]) == 70
    assert not ids["train"] & ids["val"] and not ids["train"] & ids["test"]
    assert not ids["val"] & ids["test"]

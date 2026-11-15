"""Busca semântica: encontra os pratos principais mais parecidos com o que o cliente descreveu.

Cada prato vira um vetor (embedding) que representa o significado do texto. A frase do cliente
também vira um vetor, e a busca devolve os pratos mais próximos. Assim, "algo leve e refrescante"
encontra um poke mesmo sem nenhuma palavra em comum.

Preço e tempo de entrega são filtros exatos aplicados no banco, nunca pelo LLM.

Uso: uv run python -m mmp.search   (cria o índice e roda buscas de exemplo)
"""

import logging
from pathlib import Path
from typing import Protocol

from mmp.cardapio import Cardapio
from mmp.config import Settings, settings
from mmp.logs import configurar_logs

log = logging.getLogger(__name__)


class Buscador(Protocol):
    def buscar(
        self,
        consulta: str,
        preco_max: float | None = None,
        tempo_max: int | None = None,
        k: int = 30,
    ) -> list[tuple[str, float]]:
        """Devolve (id do prato, relevância de 0 a 1), da mais relevante para a menos."""
        ...


def montar_filtro(preco_max: float | None, tempo_max: int | None) -> dict | None:
    """Filtro no formato do ChromaDB. O ChromaDB exige $and quando há mais de uma condição."""
    condicoes = [{"tipo": "principal"}]
    if preco_max is not None:
        condicoes.append({"preco": {"$lte": float(preco_max)}})
    if tempo_max is not None:
        condicoes.append({"tempo_entrega_min": {"$lte": int(tempo_max)}})
    return condicoes[0] if len(condicoes) == 1 else {"$and": condicoes}


class ChromaBuscador:
    COLECAO = "pratos"

    def __init__(self, cardapio: Cardapio, pasta: Path, modelo_embeddings: str) -> None:
        import chromadb
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        self.cardapio = cardapio
        self._cliente = chromadb.PersistentClient(path=str(pasta))
        self._embeddings = SentenceTransformerEmbeddingFunction(model_name=modelo_embeddings)
        self._colecao = self._abrir_colecao()
        # Modelos da família E5 foram treinados com estes prefixos e pioram sem eles.
        e5 = "e5" in modelo_embeddings
        self._prefixo_consulta = "query: " if e5 else ""
        self._prefixo_documento = "passage: " if e5 else ""

    def _abrir_colecao(self):
        return self._cliente.get_or_create_collection(
            self.COLECAO,
            embedding_function=self._embeddings,
            metadata={"hnsw:space": "cosine"},
        )

    def documento(self, prato) -> str:
        """Texto indexado: inclui o tipo de cozinha, que o nome do prato nem sempre revela."""
        restaurante = self.cardapio.restaurante(prato.restaurante_id)
        return f"{self._prefixo_documento}Cozinha {restaurante.categoria}. {prato.texto()}"

    def tamanho(self) -> int:
        return self._colecao.count()

    def indexar(self) -> int:
        """Recria o índice do zero com todos os pratos principais do cardápio."""
        self._cliente.delete_collection(self.COLECAO)
        self._colecao = self._abrir_colecao()
        principais = [p for p in self.cardapio.pratos if p.tipo == "principal"]
        self._colecao.add(
            ids=[p.id for p in principais],
            documents=[self.documento(p) for p in principais],
            metadatas=[
                {
                    "tipo": p.tipo,
                    "restaurante_id": p.restaurante_id,
                    "preco": p.preco,
                    "tempo_entrega_min": self.cardapio.restaurante(
                        p.restaurante_id
                    ).tempo_entrega_min,
                }
                for p in principais
            ],
        )
        return len(principais)

    def buscar(
        self,
        consulta: str,
        preco_max: float | None = None,
        tempo_max: int | None = None,
        k: int = 30,
    ) -> list[tuple[str, float]]:
        resultado = self._colecao.query(
            query_texts=[self._prefixo_consulta + consulta],
            n_results=min(k, max(self.tamanho(), 1)),
            where=montar_filtro(preco_max, tempo_max),
        )
        ids, distancias = resultado["ids"][0], resultado["distances"][0]
        # Distância de cosseno vai de 0 (idêntico) a 2 (oposto). Relevância = 1 - distância.
        return [(i, round(1 - d, 4)) for i, d in zip(ids, distancias, strict=True)]


def criar_buscador(config: Settings, cardapio: Cardapio) -> ChromaBuscador:
    """Abre o índice salvo em artifacts/chroma, criando-o na primeira vez."""
    buscador = ChromaBuscador(cardapio, config.artifacts_dir / "chroma", config.embedding_model)
    if buscador.tamanho() == 0:
        log.info("Índice vazio. Indexando %d pratos...", len(cardapio.pratos))
        buscador.indexar()
    return buscador


def main() -> None:
    configurar_logs()
    cardapio = Cardapio.carregar(settings.processed_dir)
    buscador = ChromaBuscador(cardapio, settings.artifacts_dir / "chroma", settings.embedding_model)
    total = buscador.indexar()
    log.info("Índice criado com %d pratos principais.", total)

    exemplos = [
        ("algo leve e refrescante", 50.0, None),
        ("comida japonesa", 40.0, 40),
        ("hambúrguer", None, None),
        ("um prato quentinho e caseiro", 35.0, None),
    ]
    for consulta, preco, tempo in exemplos:
        print(f'\n"{consulta}" (até R$ {preco}, até {tempo} min)')
        for prato_id, relevancia in buscador.buscar(consulta, preco, tempo, k=5):
            p = cardapio.prato(prato_id)
            print(f"  {relevancia:.2f}  {p.nome}  (R$ {p.preco:.2f})")


if __name__ == "__main__":
    main()

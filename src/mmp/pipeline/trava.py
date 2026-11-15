"""Trava de ingredientes: segunda camada de segurança para as restrições alimentares.

O classificador pode errar. Esta trava lê a lista de ingredientes e barra o prato se encontrar
um termo proibido pela definição da restrição (as mesmas definições de `prompts.DEFINICOES_TAGS`).
É uma regra em código, como o orçamento: previsível, auditável e testada.

Um ingrediente com um qualificador de liberação ("leite de coco", "queijo vegetal",
"tamari sem glúten") não é barrado.
"""

import re
import unicodedata

from mmp.schemas import Prato

CARNES = [
    "carne", "frango", "galinha", "peru", "bovina", "bovino", "suina", "suino", "porco",
    "bacon", "presunto", "calabresa", "linguica", "costela", "picanha", "fraldinha", "patinho",
    "file mignon", "charque", "pernil", "lombo", "salame", "pepperoni", "almondega",
    "hamburguer de carne", "cordeiro", "sobrecoxa", "coxa", "peito de frango",
]  # fmt: skip
PEIXES_E_FRUTOS_DO_MAR = [
    "peixe", "salmao", "atum", "tilapia", "robalo", "bacalhau", "sardinha", "camarao", "lula",
    "polvo", "marisco", "mexilhao", "ostra", "caranguejo", "kani", "ovas", "tobiko",
    "frutos do mar", "anchova",
]  # fmt: skip
LATICINIOS = [
    "leite", "queijo", "mucarela", "mussarela", "parmesao", "gorgonzola", "provolone",
    "catupiry", "requeijao", "manteiga", "creme de leite", "nata", "chantilly", "iogurte",
    "coalhada", "cream cheese", "sour cream", "ricota", "cheddar", "coalho", "ghee", "whey",
    "doce de leite", "leite condensado", "burrata", "brie", "mascarpone",
]  # fmt: skip
OVOS = ["ovo", "ovos", "gema", "clara de ovo", "maionese"]
GLUTEN = [
    "gluten", "trigo", "cevada", "centeio", "malte", "aveia", "massa", "macarrao", "talharim",
    "espaguete", "lasanha", "nhoque", "pao", "brioche", "torrada", "croissant", "empanado",
    "empanada", "panko", "farinha de rosca", "kibe", "quibe", "cuscuz marroquino", "seitan",
    "shoyu", "molho de soja", "tortilha de trigo", "cerveja", "biscoito", "bolacha",
]  # fmt: skip

# Qualificadores que tornam o ingrediente compatível com a restrição.
# Inclui nomes que só parecem proibidos: "couve manteiga" é couve, "pimenta calabresa" é tempero.
FALSOS_AMIGOS = ["couve manteiga", "pimenta calabresa", "sem leite", "sem lactose"]
LIBERA_ORIGEM_ANIMAL = [
    "vegetal", "vegano", "vegana", "plant", "de soja", "de coco", "de castanha", "de caju",
    "de amendoa", "de amendoas", "de amendoim", "de cacau", "de grao-de-bico", "de ervilha",
    "de arroz", "de aveia", "de jaca", "de cogumelo", *FALSOS_AMIGOS,
]  # fmt: skip
LIBERA_GLUTEN = [
    "sem gluten", "de arroz", "de mandioca", "de milho", "de tapioca", "de grao-de-bico",
    "tamari", "100% milho", "pao de queijo",
]  # fmt: skip

REGRAS: dict[str, tuple[list[str], list[str]]] = {
    "vegano": (CARNES + PEIXES_E_FRUTOS_DO_MAR + LATICINIOS + OVOS + ["mel"], LIBERA_ORIGEM_ANIMAL),
    # Ovo é permitido para vegetariano: "ovo de galinha" não pode ser barrado por "galinha".
    "vegetariano": (
        CARNES + PEIXES_E_FRUTOS_DO_MAR,
        [*LIBERA_ORIGEM_ANIMAL, "ovo de galinha", "ovos de galinha", "ovo caipira"],
    ),
    "sem_lactose": (LATICINIOS, [*LIBERA_ORIGEM_ANIMAL, "zero lactose"]),
    "sem_gluten": (GLUTEN, LIBERA_GLUTEN),
}


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acentos: "Muçarela" e "mucarela" viram a mesma coisa."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def _contem(texto: str, termo: str) -> bool:
    """Palavra inteira: "mel" não pode casar com "melado" nem com "caramelo"."""
    return re.search(rf"\b{re.escape(termo)}\b", texto) is not None


def violacoes(prato: Prato, restricoes: set[str]) -> list[str]:
    """Lista legível do que impede o prato de atender cada restrição. Vazia = liberado."""
    encontradas = []
    for restricao in sorted(restricoes):
        if restricao not in REGRAS:
            continue
        proibidos, liberadores = REGRAS[restricao]
        for ingrediente in prato.ingredientes:
            texto = _normalizar(ingrediente)
            if any(_contem(texto, lib) for lib in liberadores):
                continue
            termo = next((t for t in proibidos if _contem(texto, t)), None)
            if termo:
                encontradas.append(f"{restricao}: '{ingrediente}' ({termo})")
    return encontradas

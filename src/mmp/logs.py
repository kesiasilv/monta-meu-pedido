import logging


def configurar_logs() -> None:
    """Logs do projeto em INFO; bibliotecas barulhentas só mostram avisos."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for biblioteca in ("httpx", "httpcore", "google_genai", "anthropic"):
        logging.getLogger(biblioteca).setLevel(logging.WARNING)

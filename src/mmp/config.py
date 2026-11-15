"""Configuração lida do .env. Nada que muda entre ambientes fica fixo no código."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    llm_provider: Literal["gemini", "claude"] = "gemini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    anthropic_api_key: str | None = None
    claude_model: str = "claude-haiku-5-5"

    classificador: Literal["baseline", "bertimbau"] = "baseline"
    hf_model_id: str = "seu-usuario/bertimbau-tags-pratos"
    embedding_model: str = "intfloat/multilingual-e5-small"

    data_dir: Path = RAIZ / "data"
    artifacts_dir: Path = RAIZ / "artifacts"

    llm_preco_entrada_usd_por_milhao: float = 0.30
    llm_preco_saida_usd_por_milhao: float = 2.50

    seed: int = 42

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def splits_dir(self) -> Path:
        return self.data_dir / "splits"


settings = Settings()

from mmp.config import Settings
from mmp.llm.base import ErroLLM, LLMClient, Uso

__all__ = ["ErroLLM", "LLMClient", "Uso", "criar_cliente"]


def criar_cliente(settings: Settings) -> LLMClient:
    """Escolhe o provedor pelo .env. É o único lugar do código que sabe qual LLM está em uso."""
    match settings.llm_provider:
        case "gemini":
            if not settings.gemini_api_key:
                raise ValueError("Defina GEMINI_API_KEY no .env")
            from mmp.llm.gemini import GeminiClient

            return GeminiClient(settings.gemini_api_key, settings.gemini_model)
        case "claude":
            if not settings.anthropic_api_key:
                raise ValueError("Defina ANTHROPIC_API_KEY no .env")
            from mmp.llm.claude import ClaudeClient

            return ClaudeClient(settings.anthropic_api_key, settings.claude_model)

from mmp.llm.base import ClienteBase


class GeminiClient(ClienteBase):
    def __init__(self, api_key: str, modelo: str) -> None:
        super().__init__()
        from google import genai

        self._cliente = genai.Client(api_key=api_key)
        self.modelo = modelo

    def _eh_definitivo(self, erro: Exception) -> bool:
        # Erros 4xx (chave inválida, modelo inexistente) não melhoram repetindo.
        # O 429 (limite de requisições) é a exceção: esse vale esperar e tentar de novo.
        from google.genai import errors

        return isinstance(erro, errors.ClientError) and erro.code != 429

    def _completar(self, system: str, user: str, json_mode: bool, temperatura: float) -> str:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperatura,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        resposta = self._cliente.models.generate_content(
            model=self.modelo, contents=user, config=config
        )
        uso = resposta.usage_metadata
        if uso:
            self.uso.tokens_entrada += uso.prompt_token_count or 0
            self.uso.tokens_saida += uso.candidates_token_count or 0
        return resposta.text or ""

from mmp.llm.base import ClienteBase


class ClaudeClient(ClienteBase):
    def __init__(self, api_key: str, modelo: str) -> None:
        super().__init__()
        import anthropic

        self._cliente = anthropic.Anthropic(api_key=api_key)
        self.modelo = modelo

    def _completar(self, system: str, user: str, json_mode: bool, temperatura: float) -> str:
        resposta = self._cliente.messages.create(
            model=self.modelo,
            max_tokens=4096,
            system=system,
            temperature=temperatura,
            messages=[{"role": "user", "content": user}],
        )
        self.uso.tokens_entrada += resposta.usage.input_tokens
        self.uso.tokens_saida += resposta.usage.output_tokens
        return "".join(bloco.text for bloco in resposta.content if bloco.type == "text")

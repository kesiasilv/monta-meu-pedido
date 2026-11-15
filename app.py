"""Demo Gradio: a porta de entrada para pessoas. Roda localmente e no Hugging Face Spaces.

Uso: make demo
"""

import sys
from pathlib import Path

# No HF Spaces o pacote não é instalado; o código vem direto da pasta src.
sys.path.insert(0, str(Path(__file__).parent / "src"))

import gradio as gr  # noqa: E402

from mmp.config import settings  # noqa: E402
from mmp.pipeline.workflow import criar_workflow  # noqa: E402
from mmp.schemas import Resposta  # noqa: E402

workflow = criar_workflow(settings)

EXEMPLOS = [
    "Tô com R$ 40, quero algo leve, sem lactose, que chegue em 40 min",
    "Sou vegana e quero um hambúrguer, tenho 50 reais",
    "Sou celíaca, quero comida japonesa até 70 reais",
    "Quero uma pizza",
]

AVISO = (
    "Projeto de portfólio com cardápios fictícios. Não use para alergias graves: "
    "o classificador pode errar."
)


def formatar(resposta: Resposta) -> str:
    if resposta.status == "precisa_info":
        return f"🤔 {resposta.mensagem}"
    if resposta.status == "sem_opcao":
        return f"😕 {resposta.mensagem}"
    return f"🛒 {resposta.mensagem}"


def responder(mensagem: str, historico: list, pendente: str):
    """Se o assistente pediu uma informação, junta a resposta do cliente ao pedido anterior."""
    texto = f"{pendente} {mensagem}".strip()
    resposta = workflow.processar(texto)
    novo_pendente = texto if resposta.status == "precisa_info" else ""
    historico = [
        *historico,
        {"role": "user", "content": mensagem},
        {"role": "assistant", "content": formatar(resposta)},
    ]
    return "", historico, novo_pendente


with gr.Blocks(title="Monta Meu Pedido") as demo:
    gr.Markdown(
        "# 🍱 Monta Meu Pedido\n"
        "Diga quanto quer gastar, o que não pode comer e quanto tempo pode esperar. "
        "O assistente monta o carrinho e explica a escolha.\n\n"
        f"<small>{AVISO}</small>"
    )
    chat = gr.Chatbot(height=420, label="Assistente")
    pendente = gr.State("")
    caixa = gr.Textbox(placeholder="Ex.: tenho R$ 40, quero algo vegano", label="Seu pedido")
    gr.Examples(EXEMPLOS, inputs=caixa)
    caixa.submit(responder, [caixa, chat, pendente], [caixa, chat, pendente])

if __name__ == "__main__":
    demo.launch()

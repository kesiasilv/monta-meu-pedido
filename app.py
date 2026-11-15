"""Demo Gradio: a porta de entrada para pessoas. Roda localmente e no Hugging Face Spaces.

Uso: make demo
"""

import sys
from pathlib import Path

# No HF Spaces o pacote não é instalado; o código vem direto da pasta src.
sys.path.insert(0, str(Path(__file__).parent / "src"))

import gradio as gr  # noqa: E402

from mmp.config import settings  # noqa: E402
from mmp.pipeline.steps import reais  # noqa: E402
from mmp.pipeline.workflow import criar_workflow  # noqa: E402
from mmp.schemas import Resposta  # noqa: E402

workflow = criar_workflow(settings)

EXEMPLOS = [
    "Sou celíaca e intolerante a lactose, quero comida japonesa até 70 reais",
    "Tô com R$ 40, quero algo leve, sem lactose, que chegue em 40 min",
    "Quero um hambúrguer vegano",
    "Uma pizza por 5 reais",
]

CABECALHO = """
<div class="cabecalho">
  <h1>🍱 Monta Meu Pedido</h1>
  <p>Diga quanto quer gastar, o que não pode comer e quanto tempo pode esperar.
  O assistente monta o carrinho e explica a escolha.</p>
  <div class="etapas">
    <span>1 · LLM entende o pedido</span>
    <span>2 · Busca semântica</span>
    <span>3 · Classificador próprio + trava de ingredientes</span>
    <span>4 · Código monta o carrinho</span>
    <span>5 · LLM explica</span>
  </div>
</div>
"""

CARRINHO_VAZIO = "### 🛒 Carrinho\nFaça um pedido para ver o carrinho aqui."
BASTIDORES_VAZIO = (
    "### 🔍 Bastidores\nAqui aparece o que o assistente entendeu e o tempo de cada etapa."
)

AVISO = (
    "Projeto de portfólio com cardápios fictícios. Não use para alergias graves. · "
    "[Código no GitHub](https://github.com/kesiasilv/monta-meu-pedido) · "
    "[Modelo no Hugging Face](https://huggingface.co/KesiaSilva/bertimbau-tags-pratos)"
)

NOMES_ETAPAS = {
    "1_interpretar": "Entender",
    "2_buscar": "Buscar",
    "3_filtrar": "Filtrar restrições",
    "4_montar": "Montar",
    "5_explicar": "Explicar",
}

CSS = """
.cabecalho h1 { margin-bottom: 4px; }
.cabecalho p { margin-top: 0; opacity: 0.85; }
.etapas { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.etapas span {
  font-size: 0.8rem; padding: 3px 10px; border-radius: 999px;
  background: var(--color-accent-soft); border: 1px solid var(--border-color-accent);
}
.painel { border: 1px solid var(--border-color-primary); border-radius: 12px; padding: 4px 14px; }
"""


def painel_carrinho(resposta: Resposta) -> str:
    c = resposta.carrinho
    if c is None:
        return CARRINHO_VAZIO
    linhas = [f"### 🛒 {c.restaurante_nome}", "", "| Item | Preço |", "|---|---:|"]
    linhas += [f"| {i.nome} | {reais(i.preco)} |" for i in c.itens]
    taxa = "grátis" if c.taxa_entrega == 0 else reais(c.taxa_entrega)
    linhas += [f"| Entrega | {taxa} |", f"| **Total** | **{reais(c.total)}** |", ""]
    linhas.append(f"⏱️ Chega em **{c.tempo_entrega_min} min**")
    return "\n".join(linhas)


def painel_bastidores(resposta: Resposta, tempos_ms: dict[str, float]) -> str:
    linhas = ["### 🔍 Bastidores"]
    p = resposta.pedido
    if p is not None:
        orcamento = reais(p.orcamento) if p.orcamento else "não informado"
        restricoes = ", ".join(r.value.replace("_", " ") for r in p.restricoes) or "nenhuma"
        preferencias = ", ".join(x.value for x in p.preferencias) or "nenhuma"
        prazo = f"{p.tempo_max_min} min" if p.tempo_max_min else "sem prazo"
        linhas += [
            "**O que o LLM entendeu**",
            f"- Quer: *{p.descricao_livre}*",
            f"- Orçamento: {orcamento} · Prazo: {prazo}",
            f"- Restrições: {restricoes} · Preferências: {preferencias}",
        ]
    if tempos_ms:
        etapas = " · ".join(f"{NOMES_ETAPAS.get(k, k)} {v:.0f} ms" for k, v in tempos_ms.items())
        linhas += ["", f"**Tempo por etapa:** {etapas}"]
    return "\n".join(linhas)


def responder(mensagem: str, historico: list, pendente: str):
    """Se o assistente pediu uma informação, junta a resposta do cliente ao pedido anterior."""
    mensagem = (mensagem or "").strip()
    if not mensagem:
        return "", historico, pendente, gr.skip(), gr.skip()
    texto = f"{pendente} {mensagem}".strip()
    resposta = workflow.processar(texto)
    novo_pendente = texto if resposta.status == "precisa_info" else ""
    icone = {"ok": "🛒", "precisa_info": "🤔", "sem_opcao": "😕"}[resposta.status]
    historico = [
        *historico,
        {"role": "user", "content": mensagem},
        {"role": "assistant", "content": f"{icone} {resposta.mensagem}"},
    ]
    return (
        "",
        historico,
        novo_pendente,
        painel_carrinho(resposta),
        painel_bastidores(resposta, dict(workflow.tempos_ms)),
    )


with gr.Blocks(title="Monta Meu Pedido") as demo:
    gr.HTML(CABECALHO)
    with gr.Row(equal_height=True):
        caixa = gr.Textbox(
            placeholder="Ex.: sou vegana, tenho R$ 50 e quero algo que chegue em 40 min",
            show_label=False,
            container=False,
            scale=5,
            autofocus=True,
        )
        botao = gr.Button("Montar pedido", variant="primary", scale=1)
    gr.Examples(EXEMPLOS, inputs=caixa, label="Experimente")

    with gr.Row(equal_height=False):
        with gr.Column(scale=3):
            chat = gr.Chatbot(label="Assistente", height=440)
        with gr.Column(scale=2):
            carrinho = gr.Markdown(CARRINHO_VAZIO, elem_classes="painel")
            bastidores = gr.Markdown(BASTIDORES_VAZIO, elem_classes="painel")

    gr.Markdown(f"<small>{AVISO}</small>")
    pendente = gr.State("")

    entradas = [caixa, chat, pendente]
    saidas = [caixa, chat, pendente, carrinho, bastidores]
    caixa.submit(responder, entradas, saidas)
    botao.click(responder, entradas, saidas)

if __name__ == "__main__":
    demo.launch(
        theme=gr.themes.Soft(primary_hue="orange", neutral_hue="slate"),
        css=CSS,
    )

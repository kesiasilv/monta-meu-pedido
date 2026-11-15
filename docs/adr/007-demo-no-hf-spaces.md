# ADR-007: Demo em Gradio no Hugging Face Spaces

**Status:** aceito · 15/11/2026

## Contexto
A demo precisa ser pública, gratuita e fácil de testar por qualquer pessoa, sem instalar nada.

## Decisão
Uma tela de chat em Gradio (`app.py`), hospedada no Hugging Face Spaces, ao lado do modelo.
`make space` monta a pasta com só o necessário.

## Alternativas
Streamlit Community Cloud; dashboard com insights gerados por IA; bot no Telegram via n8n
(deixados para a versão 2).

## Consequências
- **Revisão:** o Space foi publicado, mas não inicia porque a conta gratuita não tem cota de
  CPU. A demo aparece em vídeo no README, gravada rodando localmente.
- Modelo e demo ficam juntos no perfil do Hugging Face.
- A demo lembra o contexto quando pede o orçamento (junta as duas mensagens).
- A API FastAPI continua disponível para outros clientes, como um app iOS.

---
title: Monta Meu Pedido
emoji: 🍱
colorFrom: green
colorTo: yellow
sdk: gradio
sdk_version: 6.32.0
python_version: "3.12"
app_file: app.py
pinned: false
license: mit
short_description: Assistente de IA que monta pedidos de comida
---

# Monta Meu Pedido

Diga quanto quer gastar, o que não pode comer e quanto tempo pode esperar. O assistente monta o
carrinho e explica a escolha.

- Interpretação e explicação: Gemini
- Restrições alimentares: [BERTimbau ajustado](https://huggingface.co/KesiaSilva/bertimbau-tags-pratos)
- Busca semântica: `multilingual-e5-small` + ChromaDB
- Código: [github.com/kesiasilv/monta-meu-pedido](https://github.com/kesiasilv/monta-meu-pedido)

Cardápios fictícios, gerados para pesquisa. Não use para alergias graves.

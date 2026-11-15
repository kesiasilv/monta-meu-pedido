# Decisões de arquitetura (ADRs)

Cada arquivo registra uma decisão: o contexto, o que foi decidido, as alternativas descartadas e
as consequências. Quando uma decisão muda, um ADR novo substitui o antigo, e o antigo é marcado
como "substituído". Formato de Michael Nygard.

| ADR | Decisão | Status |
|---|---|---|
| [001](001-workflow-em-vez-de-agente.md) | Workflow em vez de agente autônomo | Aceito |
| [002](002-classificador-proprio.md) | Classificador próprio (BERTimbau) para as restrições | Aceito |
| [003](003-gemini-atras-de-interface.md) | Gemini como LLM, atrás de uma interface | Aceito (revisado) |
| [004](004-dados-sinteticos.md) | Dados sintéticos com revisão por amostragem | Aceito |
| [005](005-busca-semantica.md) | Busca semântica com ChromaDB e multilingual-e5-small | Aceito (revisado) |
| [006](006-montador-exaustivo.md) | Montador por busca exaustiva, com margem de relevância | Aceito |
| [007](007-demo-no-hf-spaces.md) | Demo em Gradio no Hugging Face Spaces | Aceito |
| [008](008-trava-de-ingredientes.md) | Trava de ingredientes como segunda camada | Aceito |

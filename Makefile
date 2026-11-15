.PHONY: setup lint format test data revisao concordancia baseline index eval eval-rapida api demo space

setup:          ## cria o ambiente e instala todas as dependências
	uv sync --all-extras

lint:           ## checa estilo e formatação
	uv run ruff check .
	uv run ruff format --check .

format:         ## corrige estilo e formatação
	uv run ruff format .
	uv run ruff check --fix .

test:           ## roda os testes (sem chamar nenhuma API)
	uv run pytest -q

data:           ## gera os cardápios com o LLM, valida e divide em treino/validação/teste
	uv run python -m mmp.data.generate
	uv run python -m mmp.data.split
	uv run python -m mmp.data.review amostrar

concordancia:   ## calcula a concordância entre o LLM e a sua revisão manual
	uv run python -m mmp.data.review calcular

baseline:       ## treina o TF-IDF + regressão logística
	uv run python -m mmp.models.baseline

index:          ## cria o índice de busca semântica
	uv run python -m mmp.search

eval:           ## roda o laboratório completo (classificadores + workflow)
	uv run python -m evals.run_eval

eval-rapida:    ## avaliação sem chamar o LLM
	uv run python -m evals.run_eval --sem-llm

api:            ## sobe a API em http://localhost:8000/docs
	uv run uvicorn mmp.api:app --reload

demo:           ## sobe a demo Gradio
	uv run python app.py

space:          ## monta a pasta dist/space para publicar no Hugging Face Spaces
	bash scripts/preparar_space.sh

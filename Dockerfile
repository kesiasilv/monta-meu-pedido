FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATA_DIR=/app/data \
    ARTIFACTS_DIR=/app/artifacts

# Dependências primeiro, para o Docker reaproveitar esta camada quando só o código muda.
# O índice extra traz o PyTorch só de CPU, bem menor que a versão com CUDA.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu ".[ml]"

COPY data/processed ./data/processed

# As chaves entram como variáveis de ambiente na hora de rodar, nunca na imagem:
# docker run -p 8000:8000 -e GEMINI_API_KEY=... -e CLASSIFICADOR=bertimbau monta-meu-pedido
EXPOSE 8000
CMD ["uvicorn", "mmp.api:app", "--host", "0.0.0.0", "--port", "8000"]

#!/usr/bin/env bash
# Monta dist/space/ com só o que a demo precisa para rodar no Hugging Face Spaces.
# Depois: cd dist/space && git init && git remote add origin <url do Space> && git push
set -euo pipefail

DESTINO="dist/space"
rm -rf "$DESTINO"
mkdir -p "$DESTINO/data"

cp app.py "$DESTINO/"
cp spaces/README.md spaces/requirements.txt "$DESTINO/"
cp -R src "$DESTINO/"
cp -R data/processed "$DESTINO/data/"
find "$DESTINO" -name "__pycache__" -type d -prune -exec rm -rf {} +

echo "Pronto: $DESTINO"
echo "No Space, configure em Settings -> Variables and secrets:"
echo "  GEMINI_API_KEY (secret), GEMINI_MODEL, CLASSIFICADOR=bertimbau, HF_MODEL_ID"

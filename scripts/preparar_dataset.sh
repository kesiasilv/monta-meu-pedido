#!/usr/bin/env bash
# Monta dist/dataset/ para publicar no Hugging Face Datasets e no Kaggle.
set -euo pipefail

DESTINO="dist/dataset"
rm -rf "$DESTINO"
mkdir -p "$DESTINO"

cp docs/dataset_card.md "$DESTINO/README.md"
cp data/processed/pratos.json data/processed/restaurantes.json data/processed/revisao_50.csv "$DESTINO/"
cp data/splits/train.jsonl data/splits/val.jsonl data/splits/test.jsonl "$DESTINO/"

echo "Pronto: $DESTINO"
ls "$DESTINO"

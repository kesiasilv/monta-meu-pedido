# ADR-005: Busca semântica com ChromaDB e multilingual-e5-small

**Status:** aceito, revisado no mesmo dia · 15/11/2026

## Contexto
O cliente descreve o que quer em linguagem livre ("algo leve", "comida japonesa"). A busca
precisa encontrar pratos parecidos em significado e aplicar filtros exatos de preço e tempo.

## Decisão
ChromaDB em disco com o modelo `intfloat/multilingual-e5-small`. O texto indexado inclui a
categoria do restaurante. Preço e tempo são filtros de metadado no banco, nunca decididos pelo LLM.

**Revisão durante a construção:** o plano previa `paraphrase-multilingual-MiniLM-L12-v2`. Em
testes, "comida japonesa" trouxe chili mexicano e esfiha. Incluir a categoria ajudou pouco. O
`multilingual-e5-small`, com os prefixos `query:` e `passage:` que ele exige, trouxe 3 sushis e
um bowl japonês entre os 5 primeiros.

## Alternativas
FAISS, Pinecone, busca só por palavra-chave.

## Consequências
- Zero infraestrutura: o índice é criado sozinho na primeira execução.
- Não escala para milhões de pratos (fora do escopo).
- As relevâncias do E5 ficam concentradas (0,77 a 0,89), o que influenciou a margem do ADR-006.

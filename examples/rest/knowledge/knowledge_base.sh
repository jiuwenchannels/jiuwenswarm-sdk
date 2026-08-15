#!/usr/bin/env bash
# 06_knowledge_base.sh — create a knowledge base, add documents, and query it.
#
# Prerequisites:
#   jiuwenswarm serve   (starts the gateway on port 19001 by default)

BASE=http://localhost:19001/v1

# Create a knowledge base
echo "=== Create knowledge base ==="
curl -X POST "$BASE/knowledge" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "company-docs",
    "embedding_model": "text-embedding-3-small",
    "vector_store": "chroma"
  }'

echo

# Add documents
echo "=== Add documents ==="
curl -X POST "$BASE/knowledge/company-docs/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"text": "Refunds are accepted within 30 days of purchase."},
      {"text": "Support hours are Monday\u2013Friday, 9am\u20135pm PST."}
    ]
  }'

echo

# Query
echo "=== Query ==="
curl -X POST "$BASE/knowledge/company-docs/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What are your support hours?", "top_k": 2}'

"""
REPLACED (25 Oct 2026). This was a Week 1 script that called an OpenAI-compatible embeddings API. It is no longer used.

  scripts/embed_content.py     computes the vectors OFFLINE with an open-weights model (BAAI/bge-m3, MIT) and writes db/seeds/content/embeddings.json
  scripts/load_embeddings.py   loads that file into any database (also run by the nightly job); needs no model and no key
  docs/SEMANTIC_RETRIEVAL.md   how it fits together

The running app never calls an embedding service.
"""
import sys

print(__doc__)
sys.exit(1)

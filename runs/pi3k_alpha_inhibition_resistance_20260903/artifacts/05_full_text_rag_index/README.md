# Full-Text RAG Index Artifacts

This stage flattens normalized Stage 5 full-text chunks into a run-local chunk manifest, mirrors chunk records into SQLite, builds a BM25 lexical index, and builds a required Qdrant semantic index with `text-embedding-3-small`.

- `01_chunks/`: chunk and paper manifests.
- `02_lexical/`: BM25 artifact and summary.
- `03_vector/`: Qdrant local store, embedding cache, and vector summary.
- `04_hybrid/`: retrieval configuration for paper-level hybrid ranking.
- `05_outputs/`: validation-ready stage summary.

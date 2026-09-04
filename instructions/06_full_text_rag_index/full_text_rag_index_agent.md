# Full-Text RAG Index Agent Instruction

## Purpose

Build the run-local retrieval substrate for evidence-grounded subsection
rewriting. This stage does not rewrite the review. It only prepares validated
chunk, lexical, vector, and hybrid-retrieval artifacts.

## Preconditions

Run only after Stage 5 primary full-text ingestion is complete and validation
has passed:

```bash
python3 tools/00_workflow_control/validate_step.py primary_full_text_ingestion runs/<run_id>
```

The SQLite `workflow_steps` row for `primary_full_text_ingestion` must have
`status = complete` and `validation_status = passed`.

## RAG Design Borrowed From raglab

Use the `raglab` retrieval-oriented pattern:

- retrieval chunk policy: `structure_aware_1000_150`
- embedding model: `text-embedding-3-small`
- lexical backend: BM25 over the same chunks
- semantic backend: local Qdrant collection when embeddings are enabled
- hybrid retrieval: reciprocal-rank fusion across semantic and BM25 candidates
- rank chunks first, then aggregate to papers
- prevent one paper from dominating chunk ranks with a per-paper chunk cap
- rewrite agents must receive paper-level evidence packets, not isolated chunks

## API Key Requirement

Stage 6 requires `OPENAI_API_KEY` because the semantic index uses
`text-embedding-3-small`. If the key is missing, stop and ask the user to add it
to the shell environment or provide an explicit `--env-file` path, preferably to
a private env file outside the repository. Do not continue to downstream
retrieval or rewriting without a completed vector index.

Recommended private env-file setup:

```bash
mkdir -p ~/.config/literature-due-diligence
cp .env.example ~/.config/literature-due-diligence/env
chmod 600 ~/.config/literature-due-diligence/env
```

Then edit `~/.config/literature-due-diligence/env` so it contains:

```text
OPENAI_API_KEY=sk-your-key-here
```

## Required Action

Run:

```bash
python3 tools/06_full_text_rag_index/build_full_text_rag_index.py runs/<run_id> --env-file ~/.config/literature-due-diligence/env
```

This creates a complete chunk manifest, BM25 index, and Qdrant vector index.
The vector index must use `text-embedding-3-small`.

## Required Outputs

- `artifacts/05_full_text_rag_index/README.md`
- `artifacts/05_full_text_rag_index/01_chunks/chunks.jsonl`
- `artifacts/05_full_text_rag_index/01_chunks/chunk_manifest.csv`
- `artifacts/05_full_text_rag_index/01_chunks/paper_manifest.csv`
- `artifacts/05_full_text_rag_index/02_lexical/bm25.pkl`
- `artifacts/05_full_text_rag_index/02_lexical/bm25_summary.json`
- `artifacts/05_full_text_rag_index/03_vector/vector_index_summary.json`
- `artifacts/05_full_text_rag_index/04_hybrid/retrieval_config.json`
- `artifacts/05_full_text_rag_index/05_outputs/rag_index_summary.md`

The same chunk/index state must be mirrored into SQLite:

- `full_text_chunks`
- `rag_index_artifacts`
- `workflow_steps`

## Validation

Run:

```bash
python3 tools/00_workflow_control/validate_step.py full_text_rag_index runs/<run_id>
```

Do not proceed to subsection retrieval or rewriting if validation fails.

## Boundaries

Do not create evidence packets, rewritten subsections, claim manifests, or final
review files in this stage. Those belong to later stages.

# Subsection RAG Retrieval Agent Instruction

## Purpose

Build paper-level evidence packets for every draft subsection using the Stage 6
full-text RAG index. This stage does not rewrite the review. It retrieves,
ranks, and packages papers so the rewriting stage has inspectable evidence.

## Preconditions

Run only after Stage 6 full-text RAG indexing is complete and validation has
passed:

```bash
python3 tools/00_workflow_control/validate_step.py full_text_rag_index runs/<run_id>
```

The SQLite `workflow_steps` row for `full_text_rag_index` must have
`status = complete` and `validation_status = passed`.

## API Key Requirement

Stage 7 embeds one query per subsection with the same embedding model used in
Stage 6, normally `text-embedding-3-small`. If `OPENAI_API_KEY` is missing, stop
and ask the user to add it to the shell environment or provide an explicit
`--env-file` path, preferably to a private env file outside the repository.

## Required Action

Run:

```bash
python3 tools/07_subsection_rag_retrieval/build_subsection_rag_retrieval.py runs/<run_id> --env-file ~/.config/literature-due-diligence/env
```

Default retrieval behavior:

- build one focused query per subsection from full draft subsection prose,
  draft citation clues, and subsection title
- retrieve BM25 and Qdrant semantic chunk hits
- fuse chunk hits with reciprocal-rank fusion
- aggregate chunk hits to paper-level rankings
- select about 10 papers per subsection by default
- force-include Stage 4 `primary_for_subsection` papers in their subsection
  packet whenever they appear in the paper ranking, even if below the default
  top-paper cutoff
- cap selected chunks per paper so one long paper cannot dominate the packet
- write one paper packet per subsection
- mirror query, hit, and ranking state into SQLite

## Required Outputs

- `artifacts/06_subsection_rag_retrieval/README.md`
- `artifacts/06_subsection_rag_retrieval/01_queries/subsection_rag_queries.csv`
- `artifacts/06_subsection_rag_retrieval/02_chunk_hits/subsection_chunk_hits.csv`
- `artifacts/06_subsection_rag_retrieval/03_paper_ranking/subsection_paper_rankings.csv`
- `artifacts/06_subsection_rag_retrieval/04_paper_packets/SUB###.md`
- `artifacts/06_subsection_rag_retrieval/05_outputs/subsection_rag_retrieval_summary.md`

The same state must be mirrored into SQLite:

- `subsection_rag_queries`
- `subsection_rag_chunk_hits`
- `subsection_rag_paper_rankings`
- `workflow_steps`

## Validation

Run:

```bash
python3 tools/00_workflow_control/validate_step.py subsection_rag_retrieval runs/<run_id>
```

Do not proceed to rewriting if validation fails.

## Boundaries

Do not rewrite subsections, create final review prose, or produce claim-level
verification tables in this stage. Those belong to later stages.

The packet is a retrieval handoff, not a truth judgment. A paper being retrieved
does not mean it supports the draft claim; the rewriting stage must still read
the packet scientifically and distinguish support, contradiction, context, and
irrelevance.

`selection_reason` must distinguish `top_ranked` from
`stage4_primary_force_included` and
`stage4_primary_recall_added_no_query_hit`, so rewrite agents can treat forced
papers as recall-preserving evidence candidates rather than high-confidence RAG
hits.

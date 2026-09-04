# Semantic Abstract Review Merge Report

## Overall Status

`complete`

## SQLite Merge

- reviewed batches merged: 24
- abstract review decisions stored in SQLite: 1482
- source table: `abstract_review_decisions`
- paper-level rollup table: `paper_review_rollup`
- final literature set and user full-text queue were regenerated from SQLite.

## LLM Review Provenance

- required review method: `llm_semantic_reading`
- `codex_llm_worker_A` reviewed rows: 398
- `codex_llm_worker_B` reviewed rows: 249
- `codex_llm_worker_C` reviewed rows: 384
- `codex_llm_worker_D` reviewed rows: 451

Heuristic, regex, or script-filled reviewed batches are not valid inputs to this merge step.

## Decision Counts

- `exclude_low_quality_or_blocked`: 18
- `exclude_off_scope`: 211
- `exclude_wrong_level`: 156
- `include_context`: 749
- `include_primary`: 191
- `uncertain_full_text_needed`: 157

## Deduped Draft-PMID Recall

- unique draft PMIDs: 8
- recovered in PubMed candidate set: 8 / 8 (1.000)
- retained as primary anywhere: 8 / 8 (1.000)
- retained as primary/context/uncertain anywhere: 8 / 8 (1.000)

## Paper-Level Rollup

- `globally_excluded`: 114
- `globally_excluded_low_quality_or_blocked`: 2
- `globally_included_context`: 189
- `globally_included_primary`: 145
- `globally_uncertain`: 92

## Next-Step Primary Cohort

- unique primary papers for full-text ingestion: 145
- Step 4 does not report PMC-vs-PDF counts.
- Full-text availability and useful XML/PDF resolution belong to the full-text ingestion step.

## Downstream Readiness

The next step should focus only on primary papers first. It should resolve whether usable full text is available through PMC XML, PDF, or user-provided files during that step rather than inferring it here.
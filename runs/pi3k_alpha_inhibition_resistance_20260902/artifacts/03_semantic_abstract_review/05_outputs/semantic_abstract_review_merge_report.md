# Semantic Abstract Review Merge Report

## Overall Status

`complete`

## SQLite Merge

- reviewed batches merged: 76
- abstract review decisions stored in SQLite: 5433
- source table: `abstract_review_decisions`
- paper-level rollup table: `paper_review_rollup`
- final literature set and user full-text queue were regenerated from SQLite.

## Decision Counts

- `exclude_low_quality_or_blocked`: 15
- `exclude_off_scope`: 3442
- `exclude_wrong_level`: 278
- `include_context`: 1543
- `include_primary`: 119
- `uncertain_full_text_needed`: 36

## Deduped Draft-PMID Recall

- unique draft PMIDs: 12
- recovered in PubMed candidate set: 12 / 12 (1.000)
- retained as primary anywhere: 11 / 12 (0.917)
- retained as primary/context/uncertain anywhere: 12 / 12 (1.000)
- draft PMIDs not in global primary cohort: 41999684

## Paper-Level Rollup

- `globally_excluded`: 2928
- `globally_excluded_low_quality_or_blocked`: 15
- `globally_included_context`: 1190
- `globally_included_primary`: 71
- `globally_uncertain`: 34

## Next-Step Primary Cohort

- unique primary papers for full-text ingestion: 71
- Step 4 does not report PMC-vs-PDF counts.
- Full-text availability and useful XML/PDF resolution belong to the full-text ingestion step.

## Downstream Readiness

The next step should focus only on primary papers first. It should resolve whether usable full text is available through PMC XML, PDF, or user-provided files during that step rather than inferring it here.
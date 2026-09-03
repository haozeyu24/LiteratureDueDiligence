# Semantic Abstract Review Agent Instruction

## Purpose

Run semantic title/abstract review after subsection PubMed retrieval has
completed. This step reduces broad PubMed candidate sets into smaller,
subsection-specific evidence sets.

Do not start this step until preflight passes:

```bash
python3 tools/00_workflow_control/validate_step.py semantic_abstract_review_preflight runs/<run_id>
```

## Setup

Prepare worker batches:

```bash
python3 tools/04_semantic_abstract_review/prepare_abstract_review_batches.py runs/<run_id>
```

Batch preparation must hydrate candidate title/abstract metadata from SQLite by
joining `subsection_papers` with `pubmed_records`. CSV files remain the
human-auditable exchange format, but SQLite is the durable local source for
candidate metadata and subsection-paper identity.

This creates:

- `logs/agent_screen_log.md`
- `artifacts/03_semantic_abstract_review/01_setup/reviewer_instructions.md`
- `artifacts/03_semantic_abstract_review/01_setup/batch_manifest.csv`
- `artifacts/03_semantic_abstract_review/01_setup/abstract_review_status.csv`
- `artifacts/03_semantic_abstract_review/02_context/SUB###.md`
- `artifacts/03_semantic_abstract_review/03_batches/SUB###-B###.csv`
- `artifacts/03_semantic_abstract_review/01_setup/semantic_abstract_review_setup_check.md`

## Screen Log

Append substantive screen-visible progress updates, worker assignments,
semantic-review decisions at summary level, validation results, and final
summaries to `logs/agent_screen_log.md`. Do not include hidden chain-of-thought,
credentials, paper full text, or large generated artifacts.

## Worker Task

Each worker receives one subsection context file and one batch CSV. The worker
must compare every candidate title and abstract directly with the subsection
prose. Review scientific semantic fit, not keyword overlap alone.

The purpose of this step is to preserve two different kinds of useful papers:

- `include_primary`: claim-direct experimental, clinical, translational,
  computational, or methods evidence that directly supports or challenges a
  specific subsection claim. The paper should usually have `semantic_fit_score`
  `3`, direct topic match, direct or clearly justified partial entity/context
  match, direct or clearly justified partial mechanism match, and non-background
  evidence directness.
- `include_context`: high-quality framing, review, assay, biological, clinical,
  or analogous-mechanism context that can improve writing but should not be
  treated as direct proof.

Use stricter venue expectations for context than for primary evidence. Context
papers usually need a reputable or likely reputable venue because they shape the
review narrative. Primary evidence may pass from uncertain venues if the
abstract reports concrete data, but the later full-text verification stage must
judge methods, controls, and causal interpretation. Hard-blocked venues are
excluded by default.

Fill every row with:

- `abstract_review_decision`
- `first_pass_rationale`
- `first_pass_confidence`
- `topic_match_type`
- `semantic_fit_score`
- `mechanism_match`
- `entity_context_match`
- `evidence_directness`
- `key_relevant_abstract_text`
- `missing_full_text_reason`
- `synthesis_role`

## Allowed Decisions

- `include_primary`
- `include_context`
- `exclude_off_scope`
- `exclude_wrong_level`
- `exclude_low_quality_or_blocked`
- `uncertain_full_text_needed`

## Parallelization

This step is safe to parallelize after setup because each batch is independent.
Use one worker per subsection or per subsection batch. The merge/controller step
must happen after all worker batch outputs exist.

## Merge And Completion

After every expected reviewed batch CSV exists, run:

```bash
python3 tools/04_semantic_abstract_review/merge_abstract_review_decisions.py runs/<run_id>
```

This writes review decisions into SQLite table
`abstract_review_decisions`, updates `abstract_review_batches`, updates the
paper-level `paper_review_rollup`, recomputes subsection metrics, and
regenerates the filtered `final_literature_sets.csv` and
`full_text_download_queue.csv` from SQLite.

The merge report must include deduplicated draft-PMID recall against the global
primary cohort:

```text
unique draft PMIDs retained as include_primary anywhere / unique draft PMIDs
```

The full-text queue generated at the end of Step 4 is a primary-paper target
export for the next step, not a proof of PMC/PDF availability.

- Include globally primary papers only.
- Do not report PMC-versus-PDF counts in Step 4.
- Do not infer full-text usability from PMCID presence alone.
- Context and uncertain papers remain retained in SQLite, but are deferred from
  the next full-text ingestion step unless the user expands scope.

Then run:

```bash
python3 tools/00_workflow_control/validate_step.py semantic_abstract_review_complete runs/<run_id>
```

Do not proceed to full-text retrieval, vector database construction, claim
verification, or rewriting until this validation passes.

## Forbidden Outputs

Do not create PDFs, evidence packets, claim manifests, rewritten sections, or
final reviews in this step.

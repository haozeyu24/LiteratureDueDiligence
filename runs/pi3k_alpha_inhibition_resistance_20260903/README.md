# Example Run: PI3K-alpha Inhibition Resistance

This directory is the repository example run for the Literature Due Diligence
workflow. It shows an end-to-end claim-verifiable biomedical review run on
resistance mechanisms to PI3K-alpha inhibition in cancer treatment.

The run starts from `original_user_prompt.md`, converts the prompt into a
structured instruction, drafts a scoped initial review, retrieves and screens
PubMed literature, ingests available full text, builds retrieval artifacts,
rewrites subsections from evidence packets, verifies citation-bearing claims,
applies corrections, and produces a final reader-facing review.

## Reader Starting Points

- `drafts/final_review.md`: final reader-facing review.
- `artifacts/12_final_review/02_outputs/references.csv`: deduplicated numbered
  reference table used by the final review.
- `artifacts/12_final_review/03_verification/final_review_check.csv`: final
  validation checks.
- `logs/agent_screen_log.md`: chronological run log with major decisions,
  pauses, validation gates, and completion notes.
- `inputs/structured_instruction.md`: normalized interpretation of the original
  review request.

## What This Example Demonstrates

- Scope-driven review planning rather than a fixed chapter or subsection count.
- PubMed-centered retrieval with abstract triage and primary evidence routing.
- A manual PDF gate: 40 unavailable full texts were explicitly deferred before
  downstream indexing.
- Full-text RAG indexing over the normalized full texts that were available.
- Evidence-packet-based subsection rewriting with traceable citation registers.
- Claim-level verification before final prose synthesis.
- A final article-level rewrite with numbered citations and deduplicated
  references.

## Included Artifact Trail

The visible artifact trail keeps compact, inspectable files that are useful for
reviewing how the final manuscript was produced:

- `artifacts/01_draft_validation/`: initial draft search and validation checks.
- `artifacts/02_subsection_retrieval/`: subsection scope, query planning, and
  retained literature sets.
- `artifacts/03_semantic_abstract_review/`: abstract-review setup, contexts,
  and merge report.
- `artifacts/04_primary_full_text_ingestion/`: primary full-text targets,
  discovery metadata, import status, PDF request queue, and ingestion summary.
- `artifacts/05_full_text_rag_index/`: compact RAG summaries and retrieval
  configuration.
- `artifacts/06_subsection_rag_retrieval/`: subsection queries, paper rankings,
  and evidence packets.
- `artifacts/07_subsection_rewrite/`: rewritten subsection work orders,
  outputs, and verification.
- `artifacts/08_terminology_normalization/`: normalized subsection copies.
- `artifacts/09_review_assembly/`: assembled review inputs and checks.
- `artifacts/10_claim_verification/`: claim manifest, per-subsection reviews,
  and verification summary.
- `artifacts/11_corrective_rewrite/`: correction manifest and corrected draft.
- `artifacts/12_final_review/`: final review, references, semantic synthesis
  attestation, and final checks.

## Intentionally Omitted From Git

Some run-local files remain on disk but are not published in Git because they
are bulky, derived, private, or not appropriate for a compact repository
example:

- `.env` and other local secrets.
- PDF files and user PDF dropbox contents.
- PMC XML, TEI, and parsed full-text source files.
- SQLite workflow state.
- BM25 pickle files, raw chunk dumps, vector index stores, and chunk-hit bulk.
- macOS `.DS_Store` metadata.

The final review is therefore reproducible as an audit trail example, but not
as a complete full-text corpus export.

## Run Outcome

The workflow completed through final review validation. The final review stage
recorded:

- `20` final-review sections in the manifest.
- `55` deduplicated references.
- `88` claim-verification rows before final correction.
- `5` claim corrections applied.
- Final review validation status: `pass`.

## Notes For Future Runs

Use this example as a directory-shape and artifact-trail reference, not as a
template that fixes the number of chapters or subsections. The workflow now
treats minimum chapter and subsection counts as validation floors, while the
drafting model is expected to choose a scope-driven structure.

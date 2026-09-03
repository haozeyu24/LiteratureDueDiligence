# Workflow Artifacts

This directory stores generated workflow artifacts for the run. The folder
layout is organized by workflow stage, and each stage folder may contain
numbered subfolders for setup material, intermediate handoffs, and compact
outputs.

- `00_workflow_control/`: canonical workflow database and exported state snapshots.
- `01_draft_validation/`: checks that the initial draft followed its instructions.
- `02_subsection_retrieval/`: PubMed retrieval, candidate staging, and recall
  checks by draft subsection.
- `03_semantic_abstract_review/`: semantic title/abstract screening batches and
  merged review outputs.
- `04_primary_full_text_ingestion/`: primary full-text acquisition and
  normalization.
- `05_full_text_rag_index/`: chunks, lexical index, vector index, and hybrid
  retrieval configuration.

The canonical state is the SQLite database in
`00_workflow_control/01_state/workflow_state.sqlite`. CSV and Markdown artifacts
are used for auditability, worker handoff, and human inspection.

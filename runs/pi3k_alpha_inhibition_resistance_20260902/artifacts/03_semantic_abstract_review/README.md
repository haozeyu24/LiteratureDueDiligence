# Semantic Abstract Review Artifacts

This folder stores Step 4 artifacts grouped by role. The canonical workflow
state remains in `artifacts/00_workflow_control/01_state/workflow_state.sqlite`.

- `01_setup/`: reviewer instructions, batch manifest, status tracker, and setup
  validation report.
- `02_context/`: one subsection context file per draft subsection.
- `03_batches/`: unreviewed subsection-paper CSV batches for workers.
- `04_reviewed_batches/`: reviewed CSV batches returned by workers.
- `05_outputs/`: merge report and compact outputs generated after review.

Reviewed batch CSVs are the worker handoff surface; merged decisions are stored
canonically in SQLite.

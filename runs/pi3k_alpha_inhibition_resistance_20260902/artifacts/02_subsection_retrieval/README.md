# Subsection Retrieval Artifacts

This folder stores Step 3 retrieval artifacts grouped by role. The canonical
workflow state remains in `artifacts/00_workflow_control/01_state/workflow_state.sqlite`;
the files here are compact human-facing outputs or audit exports generated
from that state.

- `01_scope/`: subsection manifest derived from the draft.
- `02_queries/`: controller policy, query plan, query diagnostics, and search
  iteration records.
- `03_pubmed/`: locally staged PubMed metadata and the PMID/PMCID/DOI index.
- `04_screening/`: deterministic first-pass and rescue-pass triage tables used
  before semantic abstract review.
- `05_recall/`: draft-citation recall checks.
- `06_outputs/`: metrics, final literature sets, primary full-text target list,
  and validation report.

`06_outputs/full_text_download_queue.csv` is a legacy filename. At this stage
it means the unique primary-paper cohort for the next full-text ingestion step;
it does not claim whether PMC XML or user-supplied PDF full text is available.

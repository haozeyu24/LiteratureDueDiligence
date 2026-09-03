# Runs

Run folders are local working directories for individual literature-review
projects. They are ignored by git by default.

Reusable workflow files should stay outside `runs/`. Topic-specific prompts,
drafts, PubMed records, full texts, indexes, and review artifacts belong inside
one run folder.

## Expected Structure

```text
runs/<run_id>/
  original_user_prompt.md
  logs/
    agent_screen_log.md
  inputs/
    structured_instruction.md
    run_config.md
    intake_self_check.md
  drafts/
    initial_review.md
  artifacts/
    README.md
    00_workflow_control/
      README.md
      01_state/
        workflow_state.sqlite
      02_snapshots/
        workflow_state_snapshot.json
    01_draft_validation/
      README.md
      01_checks/
        draft_instruction_check.md
    02_subsection_retrieval/
      README.md
      01_scope/
      02_queries/
      03_pubmed/
      04_screening/
      05_recall/
      06_outputs/
    03_semantic_abstract_review/
      README.md
      01_setup/
      02_context/
      03_batches/
      04_reviewed_batches/
      05_outputs/
    04_primary_full_text_ingestion/
      README.md
      01_targets/
      02_discovery/
      03_pmc/
      04_pdf/
      05_user_pdf_request/
      06_outputs/
    05_full_text_rag_index/
      README.md
      01_chunks/
      02_lexical/
      03_vector/
      04_hybrid/
      05_outputs/
    06_subsection_rag_retrieval/
      README.md
      01_queries/
      02_chunk_hits/
      03_paper_ranking/
      04_paper_packets/
      05_outputs/
```

## Validation

Validate the active stage before moving forward:

```bash
python3 tools/00_workflow_control/validate_step.py <step_name> runs/<run_id>
```

When auditing an older stage after later stages already exist:

```bash
python3 tools/00_workflow_control/validate_step.py <step_name> runs/<run_id> --allow-later-steps
```

Do not use `--allow-extra` to mark a production stage complete.

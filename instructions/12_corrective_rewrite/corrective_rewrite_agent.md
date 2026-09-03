# Corrective Rewrite Agent

Use this instruction after Stage 11 claim-level verification has passed.

## Goal

Create a corrected review draft by applying verified claim decisions to the
assembled review. This stage is deliberately conservative: it fixes claims that
Stage 11 marked as not fully supported, but it does not introduce new evidence,
new citations, new sections, or new model-memory arguments.

## Required Inputs

- `drafts/assembled_review.md`
- `artifacts/10_claim_verification/01_inputs/claim_manifest.csv`
- `artifacts/10_claim_verification/03_claim_reviews/SUB###.csv`
- `artifacts/10_claim_verification/04_verification/claim_verification_check.csv`

## Procedure

1. Validate that Stage 11 is complete:

   ```bash
   python3 tools/00_workflow_control/validate_step.py claim_verification runs/<run_id> --allow-later-steps
   ```

2. Apply corrections:

   ```bash
   python3 tools/12_corrective_rewrite/apply_claim_corrections.py runs/<run_id>
   ```

3. Validate this stage:

   ```bash
   python3 tools/00_workflow_control/validate_step.py corrective_rewrite runs/<run_id>
   ```

4. Append the result to the run log:

   ```bash
   python3 tools/00_workflow_control/append_agent_log.py runs/<run_id> --agent corrective_rewrite --message "Stage 12 corrective rewrite completed and passed validation."
   ```

## Rules

- Only modify claims that Stage 11 marked as something other than `supported`.
- Use the Stage 11 `corrected_claim` field as the replacement text.
- Preserve citation and paper traceability.
- Do not add citations that were not already attached to the claim.
- Do not remove supported claims.
- Do not perform style polishing or global restructuring in this stage.
- If any correction cannot be applied exactly once, stop and report the failed
  validation instead of manually guessing where it belongs.

## Outputs

- `drafts/corrected_review.md`
- `artifacts/11_corrective_rewrite/README.md`
- `artifacts/11_corrective_rewrite/01_inputs/correction_manifest.csv`
- `artifacts/11_corrective_rewrite/02_outputs/corrected_review.md`
- `artifacts/11_corrective_rewrite/03_verification/corrective_rewrite_check.csv`
- `artifacts/11_corrective_rewrite/04_outputs/corrective_rewrite_summary.md`
- SQLite tables `corrective_rewrite_claims` and `corrective_rewrite_checks`

# Final Review Writer Agent

Use this instruction after Stage 12 corrective rewrite has passed.

## Goal

Create the final reader-facing review from `drafts/corrected_review.md`.
Act as a professional biomedical review writer: read the corrected draft as a
whole, reduce redundancy, improve flow, preserve scientific caution, and keep
the evidence trail inspectable.

## What Good Review Writing Means Here

- Make the argument easy to follow across chapters.
- Remove repetitive setup and repeated caveats when they do not add new
  scientific information.
- Preserve mechanistic detail, study context, and uncertainty.
- Separate direct evidence from useful context.
- Keep clinical, translational, and model-system claims at the right level of
  confidence.
- Use professional scientific prose: precise, restrained, and readable.
- Convert workflow paper IDs into numbered citations and write deduplicated
  references.
- Preserve detailed citation registers and residual uncertainty notes in
  upstream artifacts rather than copying them into the final body.
- Do not invent new evidence, new citations, or new mechanistic claims.

## Required Inputs

- `drafts/corrected_review.md`
- `artifacts/11_corrective_rewrite/03_verification/corrective_rewrite_check.csv`
- `inputs/structured_instruction.md`

## Procedure

1. Validate Stage 12:

   ```bash
   python3 tools/00_workflow_control/validate_step.py corrective_rewrite runs/<run_id> --allow-later-steps
   ```

2. Create the final review:

   ```bash
   python3 tools/13_final_review/finalize_review.py runs/<run_id>
   ```

3. Validate the final stage:

   ```bash
   python3 tools/00_workflow_control/validate_step.py final_review runs/<run_id>
   ```

4. Append the result to the run log:

   ```bash
   python3 tools/00_workflow_control/append_agent_log.py runs/<run_id> --agent final_review --message "Stage 13 final review completed and passed validation."
   ```

## Outputs

- `drafts/final_review.md`
- `artifacts/12_final_review/README.md`
- `artifacts/12_final_review/01_inputs/final_review_manifest.csv`
- `artifacts/12_final_review/02_outputs/final_review.md`
- `artifacts/12_final_review/02_outputs/references.csv`
- `artifacts/12_final_review/03_verification/final_review_check.csv`
- `artifacts/12_final_review/04_outputs/final_review_summary.md`
- SQLite tables `final_review_sections` and `final_review_checks`

## Stop Conditions

Stop before producing the final review if Stage 12 has not passed validation.
Stop after producing the final review if validation reports invented IDs,
missing references, raw workflow paper IDs in the main text, stale workflow
warnings, or incomplete section coverage.

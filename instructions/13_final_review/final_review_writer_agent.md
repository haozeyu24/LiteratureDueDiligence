# Final Review Writer Agent

Use this instruction after Stage 12 corrective rewrite has passed.

## Goal

Create the final reader-facing review from `drafts/corrected_review.md`.
Act as a professional biomedical review writer: read the corrected draft,
reference list, and verification artifacts as a whole, perform an LLM-based
semantic global review, make an explicit judgment about the article, rewrite the
review at article level, reduce redundancy, improve flow, preserve scientific
caution, and keep the evidence trail inspectable.

## What Good Review Writing Means Here

- The final review should read like a publishable biomedical review article,
  not like a workflow report, task summary, validation memo, or audit log.
- Use a topic-specific title and abstract. Do not open with generic phrases such
  as "This review synthesizes verified evidence for the user-defined topic."
- Make the argument easy to follow across chapters.
- Do not simply concatenate or lightly clean up rewritten subsections. The final
  stage is a semantic article-level rewrite.
- Make an explicit global judgment about whether the review reads as a coherent
  paper, then rewrite the final draft according to that judgment.
- Let the final structure follow the scientific argument. You may merge, split,
  reorder, rename, or collapse sections; the final section count does not need
  to match the upstream subsection count.
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

2. Create the deterministic final-review scaffold and citation conversion:

   ```bash
   python3 tools/13_final_review/finalize_review.py runs/<run_id>
   ```

3. Perform the LLM semantic global review, judgment, and rewrite. Read
   `drafts/corrected_review.md`, `artifacts/12_final_review/02_outputs/references.csv`,
   the Stage 11 and Stage 12 verification artifacts, and the current
   `drafts/final_review.md` as one article. First judge whether the article
   structure, emphasis, transitions, and redundancy are acceptable. Then rewrite
   `drafts/final_review.md` and
   `artifacts/12_final_review/02_outputs/final_review.md` as a coherent
   reader-facing review according to that judgment. Preserve numbered citations
   and do not introduce new citations or unsupported claims.

4. Write
   `artifacts/12_final_review/03_verification/semantic_final_synthesis_attestation.md`
   with these headings:

   - `# LLM Semantic Final Synthesis Attestation`
   - `## Semantic Rewrite Scope`
   - `## Global Review Judgment`
   - `## Rewrite Actions`
   - `## Structure And Redundancy Review`
   - `## Citation And Evidence Guardrails`
   - `## Iteration Notes`

   The attestation must state what was semantically reread, the global judgment
   about article coherence, what rewrite actions were taken, how the article
   structure was handled, what redundancy was reduced, and how citation and
   evidence boundaries were preserved.

5. Refresh final-review checks after the LLM rewrite, then validate the final
   stage:

   ```bash
   python3 tools/13_final_review/finalize_review.py runs/<run_id> --refresh-checks
   python3 tools/00_workflow_control/validate_step.py final_review runs/<run_id>
   ```

6. Inspect the opening, transitions, final limitations/priorities section, and
   reference conversion. If the draft still contains machine-scaffold language,
   generic placeholders, leaked internal IDs, audit-oriented prose, or awkward
   deterministic formatting, polish the final review and rerun validation.
   Repeat this write-polish-validate loop until the final review is both
   traceable and reader-facing.

7. Append the result to the run log:

   ```bash
   python3 tools/00_workflow_control/append_agent_log.py runs/<run_id> --agent final_review --message "Stage 13 final review completed and passed validation."
   ```

## Outputs

- `drafts/final_review.md`
- `artifacts/12_final_review/README.md`
- `artifacts/12_final_review/01_inputs/final_review_manifest.csv`
- `artifacts/12_final_review/02_outputs/final_review.md`
- `artifacts/12_final_review/02_outputs/references.csv`
- `artifacts/12_final_review/03_verification/semantic_final_synthesis_attestation.md`
- `artifacts/12_final_review/03_verification/final_review_check.csv`
- `artifacts/12_final_review/04_summary/final_review_summary.md`
- SQLite tables `final_review_sections` and `final_review_checks`

## Stop Conditions

Stop before producing the final review if Stage 12 has not passed validation.
Stop after producing the final review if validation reports invented IDs,
missing references, raw workflow paper IDs in the main text, stale workflow
warnings, machine-scaffold language, generic placeholder language, or incomplete
section coverage. Stop if the semantic final synthesis attestation is missing
or does not show that an LLM semantic article-level rewrite was performed.

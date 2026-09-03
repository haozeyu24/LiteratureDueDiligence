# Review Assembly Agent Instruction

## Purpose

Assemble terminology-normalized rewritten subsections into one coherent review
draft while preserving traceability. This stage puts the review together; it
does not perform claim-level verification and does not add new scientific
claims.

## Preconditions

Run only after terminology normalization is complete and validation has passed:

```bash
python3 tools/00_workflow_control/validate_step.py terminology_normalization runs/<run_id>
```

## Run

```bash
python3 tools/10_review_assembly/assemble_review.py runs/<run_id>
python3 tools/00_workflow_control/validate_step.py review_assembly runs/<run_id>
```

## Source

Use normalized subsection copies from:

```text
artifacts/08_terminology_normalization/03_normalized_subsections/
```

Do not assemble from the original Stage 8 files unless Stage 9 is intentionally
skipped in a future workflow variant.

## Rules

- Preserve chapter and subsection order from the Stage 8 manifest.
- Preserve each subsection citation register.
- Preserve each subsection residual uncertainty note.
- Do not add new citations or new scientific claims.
- Do not remove citation IDs, paper IDs, PMIDs, or DOIs.
- Do not polish away uncertainty language.

## Outputs

```text
drafts/assembled_review.md
artifacts/09_review_assembly/01_inputs/review_assembly_manifest.csv
artifacts/09_review_assembly/02_sections/SUB###.assembled.md
artifacts/09_review_assembly/03_verification/review_assembly_check.csv
artifacts/09_review_assembly/04_outputs/review_assembly_summary.md
```

## Boundaries

Claim-level verification, section-level synthesis, and final polishing belong
to later stages.

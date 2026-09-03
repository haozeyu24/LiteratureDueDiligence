# Claim Verification Agent Instruction

## Purpose

Verify citation-bearing claims in the assembled review against their cited
paper evidence. This stage decides whether each claim is supported, too broad,
mismatched, contradicted, missing citation support, or should be removed.

## Preconditions

Run only after review assembly is complete and validation has passed:

```bash
python3 tools/00_workflow_control/validate_step.py review_assembly runs/<run_id>
```

Prepare claim work orders:

```bash
python3 tools/11_claim_verification/prepare_claim_verification.py runs/<run_id>
python3 tools/00_workflow_control/validate_step.py claim_verification_setup runs/<run_id>
```

## Review Workflow

For each work order in:

```text
artifacts/10_claim_verification/02_work_orders/
```

write the corresponding reviewed CSV to:

```text
artifacts/10_claim_verification/03_claim_reviews/SUB###.csv
```

Use the work order as the source of truth. Verify each claim against only the
listed cited papers for that claim. Read normalized narrative full text for
cited papers when available.

## Required Review CSV Header

```csv
claim_id,subsection_id,claim_text,cited_paper_ids,citation_ids,verification_status,corrected_claim,evidence_summary,mismatch_type,reviewer_notes
```

## Allowed Verification Statuses

- `supported`
- `partially_supported`
- `overgeneralized`
- `contradicted`
- `citation_mismatch`
- `citation_missing`
- `insufficient_evidence`
- `remove`

## Rules

- Judge the exact claim text, not the broader topic.
- Do not use model memory as evidence.
- Do not rescue a claim with uncited papers in this stage.
- If a claim is not fully supported, write a concise `corrected_claim`.
- `evidence_summary` must name the relevant evidence and its limitation.
- Preserve `claim_id`, `subsection_id`, `claim_text`, `cited_paper_ids`, and
  `citation_ids` exactly from the work order.
- Use `mismatch_type` to explain problems such as `scope_too_broad`,
  `wrong_model`, `wrong_population`, `causality_overstated`,
  `clinical_overstated`, `mechanism_overstated`, `citation_missing`, or
  `none`.

## Verification

After all reviewed CSV files are written, run:

```bash
python3 tools/11_claim_verification/verify_claim_verification.py runs/<run_id>
python3 tools/00_workflow_control/validate_step.py claim_verification runs/<run_id>
```

Do not proceed to corrective section rewrite until both commands pass.

# Claim Verification Artifacts

This stage verifies citation-bearing claims from the assembled review against the cited paper evidence. Preparation extracts claims and creates work orders. Review agents then write claim-review CSV files, which are checked before any corrective rewrite begins.

- `01_inputs/`: extracted claim manifest.
- `02_work_orders/`: one claim-verification work order per subsection.
- `03_claim_reviews/`: one reviewed CSV per subsection.
- `04_verification/`: setup and completion checks.
- `05_outputs/`: compact claim-verification summary.

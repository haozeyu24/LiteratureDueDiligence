# Subsection Rewrite Artifacts

This stage rewrites each draft subsection from its Stage 7 paper-level evidence packet and normalized narrative full text. It is agent-run: this script prepares work orders, and writing agents produce rewritten subsection files that are then checked against the rewrite contract. Agents may work in parallel on disjoint subsection files.

- `01_inputs/`: manifest and frozen original subsection text.
- `02_work_orders/`: one rewrite instruction packet per subsection.
- `03_rewritten_subsections/`: one rewritten subsection per subsection.
- `04_verification/`: rewrite instruction compliance checks.
- `05_outputs/`: compact rewrite summary.

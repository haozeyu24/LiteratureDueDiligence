# Semantic Abstract Review Setup Check

## Overall Status

`pass`

## Preflight Compliance

All subsections are marked `abstract_review_needed` before batch preparation.

## SQLite Source Compliance

Candidate batch rows were hydrated from SQLite by joining `subsection_papers`
with `pubmed_records`, with CSV artifacts used as coverage/audit references.

## Batch Coverage

Prepared `24` batches for `12` subsections and
`1482` subsection-paper candidates.

## Semantic Field Compliance

Batch files contain required semantic review fields.

## Worker Output Boundary

No reviewed batch outputs, claim manifests, evidence packets, PDFs, rewritten
sections, or final-review artifacts are created during setup. Workers should
write reviewed CSVs only after receiving a specific batch assignment. Reviewed
CSV rows must include `review_method=llm_semantic_reading`; heuristic or
script-filled decisions are not valid semantic abstract review.

## Parallelization Readiness

`yes`

## Ready For Worker Review

`yes`

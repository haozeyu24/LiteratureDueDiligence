# Subsection Retrieval Check

## Overall Status

`pass`

## Subsection Coverage

The scaffold covers 12 draft subsections parsed from
`drafts/initial_review.md`.

## Query Plan Compliance

Each subsection has one heuristic `semantic_seed` placeholder row. The LLM query
designer must replace that placeholder with one or two real initial semantic
query intents before PubMed execution. Use a second query only when it adds a
distinct scientific retrieval intent. Initial query intent labels must be
distinct within each subsection.

## Abstract Review Rule Compliance

`abstract_review_rule.md` defines allowed first-pass and rescue-pass decisions.

## Search Iteration Compliance

`search_iteration_log.csv` contains initial controller rows with `not_run`
status. This records the next action without pretending PubMed has already been
queried.

## Subsection Metrics Compliance

`subsection_metrics.csv` contains one row per subsection with query counts,
PubMed-returned counts, recall-rate fields, abstract-review counts, rejection
counts, rescue counts, final-set counts, full-text queue counts, and controller
status. Unknown values are explicit until PubMed execution and abstract triage
are performed.

## Draft Citation Recall Compliance

Known draft citations were copied into the recall-check scaffold. Final recall
status is pending PubMed execution and abstract collection.

## Final Literature Set Compliance

`final_literature_sets.csv` contains draft-anchor rows marked `not_reviewed`.
The file is structurally ready for abstract-review decisions, but its scientific
contents are not final.

## Full-Text Download Queue Compliance

`full_text_download_queue.csv` contains rows for draft citations that already
requested full-text verification.

## Issues To Fix

PubMed query execution, result counts, abstract collection, first-pass triage,
rescue triage, and verified full-text routing remain to be completed.

## Ready For PubMed Execution

`yes`

## PubMed Metadata Compliance

`pass`

Collected `542` unique PubMed metadata records locally and
mirrored them into SQLite `pubmed_records`.


## Ready For Abstract Review

`yes`

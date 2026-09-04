# Subsection Retrieval Controller Policy

## Purpose

The controller runs subsection-level PubMed retrieval loops from the initial
review draft. It accepts, revises, broadens, or narrows queries based on result
counts, sampled precision, noise classes, and draft-citation recall.

## Query Design And Count Heuristics

Each subsection should have one or two initial semantic PubMed queries. Use one
query when the subsection has a single coherent evidence target. Use two only
when the second query has a distinct scientific intent, such as mechanism plus
clinical context, primary mechanism plus citation recall, model/assay plus
therapy setting, or positive evidence plus negative/failed-result evidence.

Judge readiness at subsection level. The target candidate set is 10-300 unique
PubMed records per subsection.

- `0-9`: too few; broaden or replace the weakest unresolved leaf query.
- `10-300`: reviewable for semantic abstract review.
- `>300`: too many; tighten or replace the broadest contributing leaf query.

Diagnostic samples from overbroad queries are not retrieval coverage. They can
be used to diagnose noise and choose tighter keyword combinations, but they
must not be the only source passed into semantic abstract review.

Redesigned queries are not automatically executable keyword rewrites.
Query-level counts are diagnostics. When the subsection candidate set is too
sparse or too broad, the controller stages one redesign work order for the
weakest or broadest unresolved leaf query. An LLM query designer must
semantically read the subsection evidence need plus the count failure before
marking redesigned queries as executable.

Continue redesign loops without human review until the subsection candidate set
is 10-300 and all executable redesign rows have been run.

`subsection_metrics.csv` `controller_status` is the durable rollup: use
`query_revision_needed` when the subsection is outside 10-300 or has pending
redesign rows, and `abstract_review_needed` when candidates are ready for
semantic abstract review.

## Controller Actions

- `accept_for_abstract_review`
- `redesign_query_keywords`
- `diagnostic_only_subsection_covered`
- `recover_draft_citation`
- `finalize_subsection_set`

## Stop Rule

Finalize a subsection only after query iterations, abstract-review decisions,
draft-citation recall, and full-text routing are recorded. Placeholder or
`not_run` records are allowed only to show that the controller scaffold exists;
they do not establish that PubMed retrieval or abstract review is scientifically
complete. Any subsection outside the 10-300 candidate range must continue to a
semantic redesign row. The redesigned query must change the keyword strategy
through semantic LLM redesign, not merely raise collection limits or take a
larger subset from the original result count.

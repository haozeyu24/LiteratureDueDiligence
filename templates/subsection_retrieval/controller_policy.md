# Subsection Retrieval Controller Policy

## Purpose

Define how the controller creates, evaluates, and revises PubMed searches for
each draft subsection.

## Query Design And Count Heuristics

Each subsection should have one or two initial semantic queries. Use one query
when the subsection has a single clear evidence need; use two when a second
distinct intent is genuinely needed, such as mechanism plus clinical context or
primary mechanism plus citation recall.

Judge readiness at subsection level. The target candidate set is 10-300 unique
PubMed records per subsection. Query-level counts are diagnostics that guide
redesign; they are not independent stop rules. Overbroad query samples are
diagnostic only unless the subsection-level candidate set is reviewable through
specific retrieval queries.

When a subsection has fewer than 10 candidates, semantically broaden or replace
the weakest leaf query. When a subsection has more than 300 candidates,
semantically tighten or replace the broadest contributing leaf query. The
controller may continue redesign loops without human review until the subsection
candidate count is in range and all executable redesign rows have been run.

## Controller Actions

- `accept_for_abstract_review`
- `redesign_query_keywords`
- `diagnostic_only_subsection_covered`
- `recover_draft_citation`
- `finalize_subsection_set`

## Stop Rule

Finalize a subsection only after query iterations, semantic abstract-review
decisions, draft-citation recall, and full-text routing are recorded.

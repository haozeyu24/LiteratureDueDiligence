# Subsection Retrieval Controller Policy

## Purpose

Define how the controller creates, evaluates, and revises PubMed searches for
each draft subsection.

## Query Count Heuristics

- `0`: too few unless the subsection is explicitly speculative.
- `1-4`: usually too narrow unless recovered draft anchors make the subsection complete.
- `5-100`: target band for LLM semantic abstract review.
- `101-110`: acceptable tolerance when the query is semantically specific.
- `>110`: too many; collect at most a diagnostic sample and redesign query keywords before using the query as retrieval coverage.

Evaluate counts at query level. Each subsection should have as many initial
semantic queries as its evidence needs require, with distinct intent labels. Do
not redesign acceptable-count queries.

## Controller Actions

- `accept_for_abstract_review`
- `redesign_query_keywords`
- `recover_draft_citation`
- `finalize_subsection_set`

## Stop Rule

Finalize a subsection only after query iterations, semantic abstract-review
decisions, draft-citation recall, and full-text routing are recorded.

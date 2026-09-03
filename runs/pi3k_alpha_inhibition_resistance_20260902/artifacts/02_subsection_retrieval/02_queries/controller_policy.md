# Subsection Retrieval Controller Policy

## Purpose

The controller runs subsection-level PubMed retrieval loops from the initial
review draft. It accepts, revises, broadens, or manually routes queries based on
result counts, sampled precision, noise classes, and draft-citation recall.

## Query Count Heuristics

- `0`: too few unless the subsection is explicitly speculative.
- `1-5`: usually too narrow unless recovered draft anchors make the subsection complete.
- `6-200`: acceptable for semantic abstract review.
- `201-500`: collect a labeled sample and refine only if sampled abstracts are mostly noise.
- `>500`: usually too many; refine before abstract review unless the subsection is intentionally broad.

## Controller Actions

- `accept_for_abstract_review`
- `refine_query`
- `broaden_query`
- `recover_draft_citation`
- `manual_lookup`
- `finalize_subsection_set`

## Stop Rule

Finalize a subsection only after query iterations, abstract-review decisions,
draft-citation recall, and full-text routing are recorded. Placeholder or
`not_run` records are allowed only to show that the controller scaffold exists;
they do not establish that PubMed retrieval or abstract review is scientifically
complete.

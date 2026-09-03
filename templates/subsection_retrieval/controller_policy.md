# Subsection Retrieval Controller Policy

## Purpose

Define how the controller creates, evaluates, and revises PubMed searches for
each draft subsection.

## Query Count Heuristics

- `0`: too few unless the subsection is explicitly speculative.
- `1-5`: usually too narrow unless recovered draft anchors make the subsection complete.
- `6-200`: acceptable for LLM semantic abstract review.
- `201-500`: collect a labeled sample and refine only if sampled abstracts are mostly noise.
- `>500`: usually too many; refine before finalization unless the subsection is intentionally broad.

## Controller Actions

- `accept_for_abstract_review`
- `refine_query`
- `broaden_query`
- `recover_draft_citation`
- `manual_lookup`
- `finalize_subsection_set`

## Stop Rule

Finalize a subsection only after query iterations, semantic abstract-review
decisions, draft-citation recall, and full-text routing are recorded.

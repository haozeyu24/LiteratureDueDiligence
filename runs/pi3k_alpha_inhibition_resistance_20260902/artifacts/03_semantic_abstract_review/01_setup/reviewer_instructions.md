# Semantic Abstract Review Worker Instructions

## Purpose

Reduce broad PubMed candidate sets into subsection-specific scientific evidence
sets by reading titles and abstracts semantically.

## Inputs Per Worker

- one `subsection_context/SUB###.md` file
- one `batches/SUB###-B###.csv` file with up to `80` candidates

## Required Decisions

For every candidate row, fill:

- `abstract_review_decision`: one of `include_primary`, `include_context`,
  `exclude_off_scope`, `exclude_wrong_level`, `exclude_low_quality_or_blocked`,
  or `uncertain_full_text_needed`
- `first_pass_rationale`: one concise scientific reason tied to the subsection
- `first_pass_confidence`: `high`, `medium`, or `low`
- `topic_match_type`: `direct`, `partial`, `analogous`, `none`, or `unknown`
- `semantic_fit_score`: `0`, `1`, `2`, or `3`
- `mechanism_match`: `direct`, `partial`, `analogous`, `none`, or `unknown`
- `entity_context_match`: `direct`, `partial`, `analogous`, `none`, or
  `unknown`
- `evidence_directness`: `direct_experimental`, `direct_clinical`,
  `computational_or_indirect`, `background_review`, `not_evidence`, or
  `unknown`
- `key_relevant_abstract_text`: a brief phrase identifying the relevance signal
- `missing_full_text_reason`: `not_needed_for_abstract_triage` or a concise
  reason full text is needed

## Inclusion Standard

Include only papers whose title/abstract directly or usefully supports,
challenges, contextualizes, or narrows a scientific claim in the subsection.
Keyword overlap alone is insufficient. Exact entity mismatch is not by itself
exclusion when the abstract studies an allowed analogous mechanism or system.

Use `include_primary` only for claim-direct evidence. The abstract must show
that the paper directly supports or challenges a specific scientific claim in
the subsection, not merely that it is original research on a related topic.
Primary evidence should usually have all of the following:

- `semantic_fit_score` = `3`
- `topic_match_type` = `direct`
- `entity_context_match` = `direct` or a clearly justified `partial`
- `mechanism_match` = `direct` or a clearly justified `partial`
- `evidence_directness` is not `background_review`, `not_evidence`, or
  `unknown`

If a paper is original research but the abstract is adjacent, broad, only partly
aligned, missing the key entity/context, or useful mainly for plausibility or
landscape, use `include_context`. If it looks potentially primary but the
abstract does not expose timing, model, treatment exposure, assay result,
clinical endpoint, or causal interpretation, use `uncertain_full_text_needed`.

Use `include_context` for papers that help frame the subsection, define the
mechanism space, interpret plausibility, provide high-quality review context, or
explain an assay or clinical landscape. Context papers are useful for writing,
but they are not direct proof.

Apply venue quality asymmetrically:

- Context papers should usually come from `reputable_or_likely_reputable`
  venues. Retain context papers from `uncertain` venues only when the abstract
  is unusually useful, and state the lower weight in `first_pass_rationale`.
- Primary evidence may pass from `reputable_or_likely_reputable` or `uncertain`
  venues when the abstract reports concrete claim-direct data. Mark full text as
  needed when methods, controls, or causal interpretation cannot be judged from
  the abstract.
- `hard_blocked` venues should be marked `exclude_low_quality_or_blocked`
  unless a human override is documented.
- Preprints may be retained as emerging evidence or context, but do not let a
  preprint alone establish a settled claim.

## Output Rule

Write reviewed batch outputs under
`artifacts/03_semantic_abstract_review/reviewed_batches/` using the same filename
as the input batch. Do not create rewritten sections, evidence packets, PDFs, or
claim-verification artifacts in this step.

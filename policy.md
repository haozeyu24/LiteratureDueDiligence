# Workflow Policy

## Purpose

This file defines workflow-wide rules for the draft-first, claim-centered
biomedical literature due diligence workflow.

## Core Policy

1. Use the initial review as a hypothesis scaffold, not as evidence.
2. Search broadly enough to support later RAG and claim verification.
3. Prefer full-text review for claim verification.
4. If full text is unavailable, review title and abstract explicitly and mark
   the full text as unresolved.
5. Create a user-download queue for papers whose full text is needed but not
   available to the agent.
6. Distinguish searched literature from LLM memory. Citations recalled without
   explicit lookup must be labeled `llm_memory`.
7. Include preprints by default, but label them as non-peer-reviewed or
   preprint evidence.
8. Use PubMed as the required primary literature discovery source.
9. Prefer reputable venues, but do not pretend that venue reputation can be
   perfectly defined by a static rule.
10. Apply the hard journal blocklist in `resources/journal_blocklist.csv`.
11. Do not create side artifacts outside the current step contract.
12. Validate each workflow step before moving forward.

## Paper Count Policy

Most users will not specify a paper count. In that case, later retrieval agents
should find as many relevant papers as practical for downstream RAG and
verification rather than forcing an arbitrary small top-N list.

Paper counts may guide summaries or drafting, but they must not be used as a
scientific inclusion or exclusion rule.

## Full-Text Policy

Full text is preferred for claim verification.

If full text is available:

- review full text for mechanistic, biomedical, causal, comparative, and
  citation-sensitive claims
- record the full-text source and locator when possible

If full text is not available:

- review title and abstract
- mark evidence level as title/abstract-only
- do not treat absence of full text as scientific exclusion
- add the paper to a user-download queue when full text is needed for final
  claim confidence

## Preprint Policy

Preprints are included by default because they can be important for emerging
scientific areas.

However:

- label preprints clearly
- do not let preprints alone establish settled claims
- prefer peer-reviewed evidence when available
- route major preprint-dependent claims to human inspection

## Venue Quality Policy

The workflow uses three layers of venue quality control:

1. Hard blocklist: venues in `resources/journal_blocklist.csv` are excluded or
   flagged according to step-specific rules.
2. Venue reputation assessment: agents should label venues as
   `reputable_or_likely_reputable`, `uncertain`, `preprint_server`, or
   `hard_blocked`.
3. Human review: uncertain venue judgments should remain visible rather than
   hidden behind a false whitelist.

Agents must not invent a universal list of reputable venues. Reputation
judgments should be conservative, explicit, and revisable.

Context and primary evidence have different venue thresholds:

- Context papers shape the narrative, terminology, mechanism space, and
  plausibility framing. They should usually come from
  `reputable_or_likely_reputable` venues. Context papers from `uncertain`
  venues may be retained only as low-weight context with an explicit rationale.
- Primary evidence papers may pass from `reputable_or_likely_reputable` or
  `uncertain` venues when the abstract reports concrete data that directly
  supports or challenges a specific subsection claim. Original research that is
  broad, adjacent, or mainly useful for plausibility should be retained as
  context rather than primary evidence. Primary-evidence claims must be
  rechecked against full text before final writing.
- Hard-blocked venues are excluded by default for both context and primary
  evidence unless a human explicitly overrides the decision.
- Preprints may be retained as emerging context or primary evidence, but they
  must be labeled and cannot alone establish settled claims.

## Source Trust Policy

PubMed is the required primary literature discovery source for this workflow.

Other sources may be used later only when the workflow step explicitly allows
them or the user asks for them. Candidate papers found outside PubMed should be
clearly labeled by source and should receive extra venue and citation checks.

Patent searches, company websites, regulatory documents, investor materials, and
general web search are out of scope for the current workflow. They may be added
later as separate due-diligence modules.

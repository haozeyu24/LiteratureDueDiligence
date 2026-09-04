# Review Title

## Draft Status

This is an initial verification-ready draft. Claims and citations are not final
until later verification steps are complete.

`draft_access_status` values are provisional labels, not verified access states.
Later retrieval agents must verify full text, abstract-only, title-only,
unavailable, or user-download-needed status.

`discovery_provenance` values distinguish citations found by explicit search
from citations recalled by the drafting model. `searched_web` rows come from
the lightweight draft search and remain provisional until later retrieval
verifies them. Later agents must verify `llm_memory`, `unknown`, and
`citation_needed` rows before using them as support.

## Executive Summary

## Chapter 1: Title

### Subsection 1.1: Title

Draft prose with inline citations or `citation needed`.

#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
| S01-C001 | citation needed | unknown | unknown | citation_needed | full_text_needed_for_verification | unknown | citation_needed | Describe the claim this citation must support. |
| S01-C002 | citation needed | unknown | unknown | citation_needed | access_unknown | unknown | citation_needed | Add another missing evidence target for later PubMed search. |
| S01-C003 | citation needed | unknown | unknown | citation_needed | access_unknown | unknown | citation_needed | Add another missing evidence target for later PubMed search. |
| S01-C004 | citation needed | unknown | unknown | citation_needed | access_unknown | unknown | citation_needed | Add another missing evidence target for later PubMed search. |

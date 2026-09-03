# Draft Instruction Check

## Overall Status

`pass`

## Scope Compliance

The draft follows the structured instruction by focusing on resistance to
PI3K-alpha/PIK3CA inhibition in cancer treatment, including laboratory
mechanisms, patient-derived evidence, clinical trial outcomes, approved and
investigational inhibitors, failed or limited trials, and combination strategies.

## Structure Compliance

The draft contains a draft-status notice, executive summary, 6 chapters, 18
substantive subsections, and a citation register under every substantive
subsection.

## Breadth Compliance

The draft satisfies the expansive-draft policy: at least 6 chapters, at least 18
substantive subsections, and at least 4 citation-register rows per substantive
subsection. Where the drafting agent could not confidently name enough real
PubMed citations, it used `citation needed` rows with unknown PMID/DOI metadata
instead of inventing citation details.

## Subsection Substance Compliance

Each substantive subsection contains at least 150 words of prose and at least 2
paragraphs before the citation register. The prose develops the topic enough for
later claim extraction rather than acting as a bare outline.

## Citation Register Compliance

Each substantive subsection includes a `#### Citation Register` with the
required table header:

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|

Citation rows use stable local citation IDs. Known PMIDs and DOIs are included
where available. Uncertain metadata is marked `unknown`.

## Access Label Compliance

The draft explicitly states that `draft_access_status` values are provisional
labels, not verified access states. Citation rows use allowed draft access
labels such as `full_text_likely_available`, `abstract_only_likely`,
`access_unknown`, and `full_text_needed_for_verification`.

## Venue Label Compliance

The draft uses allowed venue-trust labels:
`reputable_or_likely_reputable`, `uncertain`, and `unknown`. No hard-blocked
venue is intentionally used to support a settled claim.

## Discovery Provenance Compliance

Each citation-register row includes a `discovery_provenance` value. Existing
known citations in this older example run are labeled `local_prior_run`;
explicit gap rows are labeled `citation_needed`.

## Metadata Uncertainty Compliance

The draft marks uncertain PMIDs and DOIs as `unknown` rather than fabricating
metadata. It uses `citation needed` rows to expose missing evidence targets for
later PubMed retrieval.

## Out-Of-Scope Source Check

The draft treats PubMed-indexed literature as the primary source universe and
does not use patents, company websites, investor materials, regulatory labels
outside PubMed-indexed approval-summary context, or general web sources as
literature evidence.

## Issues To Fix

- Many `citation needed` rows must be resolved by the next retrieval step.
- Draft access labels are provisional and must be verified.
- Several known citation rows still need DOI or title metadata verification.
- Scientific claims remain unverified until claim extraction, targeted PubMed
  retrieval, evidence packet construction, full-text review, and claim
  verification are complete.

## Ready For Claim Extraction

`yes`

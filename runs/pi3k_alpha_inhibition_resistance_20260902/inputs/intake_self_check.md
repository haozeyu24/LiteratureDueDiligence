# Intake Self-Check

## Prompt Clarity

Choose one:

- `broad_but_workable`

## Missing Information

- The user did not specify which cancer types should be prioritized.
- The user did not specify a target number of papers.
- The user did not specify a date range.
- The user did not specify citation style.
- The user did not specify whether the final review should be a full manuscript, mini-review, annotated outline, or evidence report.
- The user did not specify a formal definition of reputable journal.

## Inferences Made

- PIK3CA was treated as a key synonym/entity for PI3K-alpha inhibition.
- RLY-2608 was treated as an inferred spelling variant of RLy2608.
- Other approved or investigational PI3K-alpha/PIK3CA-directed agents were included because the user wrote "and so on."
- Combination therapy topics were treated as in scope only when connected to PI3K-alpha inhibitor resistance or clinical outcome.
- Related AKT, mTOR, MAPK, ERK, HER2, ERBB2, EGFR, endocrine therapy, CDK4/6, and PTEN topics were treated as allowed expansion terms only when anchored to PI3K-alpha/PIK3CA inhibitor evidence.
- Preprints were included by default under the generic workflow policy, with clear labeling and human inspection for important preprint-dependent claims.
- PubMed was selected as the trusted default discovery source for this biomedical review.
- Venue reputation was treated as a downstream evidence label rather than a rigid whitelist.

## Scope Risks

- The prompt is broad across all cancer types, all approved and investigational inhibitors, laboratory mechanisms, patient-derived evidence, and clinical trials.
- Without a paper-count target, retrieval may become large; this is acceptable for later RAG, but downstream steps will need batching, deduplication, and claim-centered filtering.
- There is risk of drifting into general PI3K pathway biology or general targeted therapy resistance.
- There is risk of confusing PI3K-alpha-specific evidence with pan-PI3K, AKT, mTOR, MAPK, or other pathway-inhibitor evidence.
- There is risk of overtrusting uncertain venues unless venue labels remain visible.

## Retrieval Risks

- Searches for PI3K resistance can retrieve pan-PI3K, other PI3K isoform, AKT, mTOR, MAPK, endocrine therapy, HER2, or general prognosis papers that are not directly about PI3K-alpha inhibitor resistance.
- Clinical trial searches may retrieve toxicity, dosing, pharmacokinetic, or formulation reports that need careful interpretation.
- Trial failure can reflect toxicity, study design, biomarker selection, dosing, line of therapy, or insufficient pathway suppression rather than biological resistance.
- Missing full text may prevent confident verification of mechanistic and trial-interpretation claims; such papers should enter a user-download queue.

## Verification Risks

- Mechanistic claims may be model-specific and not validated in patients.
- Patient biomarker associations may not prove causal resistance.
- Review articles may overstate mechanisms without primary evidence.
- Cross-trial comparisons can be misleading.
- Claims about investigational agents may depend on recent publications or preprints and need careful full-text verification.
- Preprint-only claims should remain tentative unless later peer-reviewed evidence supports them.
- Claims based on uncertain venues should be routed to human inspection if they materially affect the final review.

## Recommended Next Step

Proceed to initial review drafting. The drafting agent should use the structured instruction to produce a broad but organized draft, mark uncertain citations clearly, include preprints with labels, and avoid treating the draft as verified evidence. Later retrieval should seek broad relevant PubMed coverage for RAG and claim verification, apply the hard journal blocklist, preserve venue-trust labels, review full text when available, use title/abstract fallback when necessary, and create a user-download queue for relevant papers whose full text is needed but unavailable.


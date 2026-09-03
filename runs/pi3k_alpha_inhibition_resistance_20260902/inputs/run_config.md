# Run Config

- `workflow_mode`: `draft_first_claim_centered`
- `initial_review_goal`: `structured_review_draft`
- `claim_verification_mode`: `strict`
- `search_mode`: `claim_centered_targeted`
- `paper_count_policy`: `broad_relevant_coverage_when_unspecified`
- `paper_count_target`: `as_many_relevant_as_practical_unless_user_specified`
- `initial_draft_expansion_policy`: `expansive_topic_map`
- `min_initial_draft_chapters`: `6`
- `min_initial_draft_subsections`: `18`
- `min_words_per_substantive_subsection`: `150`
- `min_paragraphs_per_substantive_subsection`: `2`
- `min_citation_register_rows_per_subsection`: `4`
- `citation_gap_policy`: `add_citation_needed_rows_for_missing_evidence`
- `allow_reviews_as_sources`: `true`
- `allow_preprints`: `true`
- `full_text_policy`: `full_text_preferred_title_abstract_fallback`
- `missing_full_text_policy`: `create_user_download_queue`
- `primary_discovery_source`: `pubmed`
- `venue_quality_policy`: `hard_blocklist_plus_reputation_label`
- `venue_blocklist_path`: `resources/journal_blocklist.csv`
- `api_dependency`: `openai_embeddings_required_for_stage_6`
- `human_final_inspection_required`: `true`

## Notes

- The user did not specify a target paper count, so later retrieval should collect as many relevant PubMed papers as practical for downstream RAG and claim verification.
- The initial review draft should be expansive enough to support downstream RAG: at least 6 chapters, at least 18 substantive subsections, at least 150 words and 2 prose paragraphs per substantive subsection, and at least 4 citation-register rows per substantive subsection unless a later user instruction changes this.
- If the drafting agent cannot confidently identify enough real PubMed citations for a subsection, it should add `citation needed` rows instead of inventing metadata.
- Reviews are allowed for background, landscape, and structure, but primary mechanistic and clinical claims should be verified against primary studies where possible.
- Preprints are included by default, must be clearly labeled, and should not alone establish settled claims.
- Clinical trial papers across phases, including successful, negative, failed, discontinued, and combination trials, should be represented in the initial review draft and later verified claim by claim.
- Full text should be reviewed whenever available. If full text is unavailable, title and abstract should still be reviewed, and papers needing full text for confident verification should be added to a user-download queue.
- PubMed is the trusted default discovery source for this biomedical review.
- The hard blocklist at `resources/journal_blocklist.csv` must be applied.
- Venue reputation should be labeled conservatively as `reputable_or_likely_reputable`, `uncertain`, `preprint_server`, or `hard_blocked`; uncertain venue-dependent claims should remain visible for human inspection.
- No API dependency is assumed; this run should be executable by local agents operating over files and user-accessible tools.

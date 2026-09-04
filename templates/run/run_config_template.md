# Run Config

- `workflow_mode`: `draft_first_claim_centered`
- `initial_review_goal`: `structured_review_draft`
- `claim_verification_mode`: `strict`
- `search_mode`: `claim_centered_targeted`
- `paper_count_policy`: `broad_relevant_coverage_when_unspecified`
- `paper_count_target`: `as_many_relevant_as_practical_unless_user_specified`
- `initial_draft_expansion_policy`: `expansive_topic_map`
- `min_initial_draft_chapters`: `6`
- `initial_draft_subsection_policy`: `cover_major_entities_mechanisms_evidence_classes_and_clinical_contexts`
- `target_subsections_per_chapter_when_broad_unspecified`: `2-4`
- `min_initial_draft_subsections`: `adaptive_minimum_2_per_chapter`
- `min_words_per_substantive_subsection`: `150`
- `min_paragraphs_per_substantive_subsection`: `2`
- `min_citation_register_rows_per_subsection`: `4`
- `citation_discovery_provenance_required`: `true`
- `initial_draft_lightweight_search_required`: `true`
- `llm_memory_citations_allowed_with_label`: `true`
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

## Allowed Values

- `workflow_mode`
  - `draft_first_claim_centered`
- `initial_review_goal`
  - `structured_review_draft`
  - `outline_plus_key_claims`
- `claim_verification_mode`
  - `strict`
  - `balanced`
- `search_mode`
  - `claim_centered_targeted`
  - `section_centered_targeted`
- `paper_count_target`
  - `user_specified_or_model_suggested`
  - any explicit integer or range requested by the user
  - `as_many_relevant_as_practical_unless_user_specified`
- `paper_count_policy`
  - `broad_relevant_coverage_when_unspecified`
  - `user_specified_target`
- `initial_draft_expansion_policy`
  - `expansive_topic_map`
  - `compact_scaffold`
- `min_initial_draft_chapters`
  - any positive integer
- `min_initial_draft_subsections`
  - `adaptive_minimum_2_per_chapter`
  - any positive integer requested or justified by the run
- `min_words_per_substantive_subsection`
  - any positive integer
- `min_paragraphs_per_substantive_subsection`
  - any positive integer
- `min_citation_register_rows_per_subsection`
  - any positive integer
- `citation_gap_policy`
  - `add_citation_needed_rows_for_missing_evidence`
  - `only_list_known_citations`
- `initial_draft_lightweight_search_required`
  - `true`
  - `false`
- `allow_reviews_as_sources`
  - `true`
  - `false`
- `allow_preprints`
  - `true`
  - `false`
- `full_text_policy`
  - `retrieve_when_needed_for_claim_verification`
  - `abstract_first_then_full_text_if_uncertain`
  - `full_text_required_for_final_claims`
  - `full_text_preferred_title_abstract_fallback`
- `missing_full_text_policy`
  - `create_user_download_queue`
  - `record_access_gap_only`
- `primary_discovery_source`
  - `pubmed`
- `venue_quality_policy`
  - `hard_blocklist_plus_reputation_label`
  - `hard_blocklist_only`
- `venue_blocklist_path`
  - `resources/journal_blocklist.csv`
- `api_dependency`
  - `openai_embeddings_required_for_stage_6`
  - `none`
- `human_final_inspection_required`
  - `true`

## Notes

- When the user does not specify paper count, later retrieval should collect as
  many relevant papers as practical for RAG and verification.
- The initial draft should be expansive when the user does not specify a paper
  count: broad topic map, many subsections, and multiple citation candidates or
  citation-needed rows per subsection.
- The initial draft should be seeded by lightweight internet literature search
  for obvious scholarly anchors. This improves draft recall but does not replace
  later formal PubMed retrieval.
- Every substantive subsection should include enough prose to be useful as a
  review draft, not just a heading plus citations. The default minimum is 150
  words and 2 paragraphs before the citation register.
- Full text should be reviewed when available. If full text is unavailable,
  title and abstract should still be reviewed and the paper should be routed to
  a user-download queue when full text is needed.
- Preprints are included by default but must be clearly labeled.
- PubMed is the required primary literature discovery source.
- Patents, company websites, regulatory documents, investor materials, and
  general web sources are out of scope unless a later module explicitly adds
  them.
- The hard blocklist in `resources/journal_blocklist.csv` must be applied.
- Venue reputation should be labeled conservatively; do not invent a universal
  whitelist of reputable venues.

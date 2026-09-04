# Run Config

- `workflow_mode`: `draft_first_claim_centered`
- `initial_review_goal`: `structured_review_draft`
- `claim_verification_mode`: `strict`
- `search_mode`: `claim_centered_targeted`
- `paper_count_policy`: `broad_relevant_coverage_when_unspecified`
- `paper_count_target`: `as_many_relevant_as_practical_unless_user_specified`
- `initial_draft_expansion_policy`: `expansive_topic_map`
- `initial_draft_subsection_policy`: `cover_major_entities_mechanisms_evidence_classes_and_clinical_contexts`
- `target_subsections_per_chapter_when_broad_unspecified`: `scope_driven_multiple_when_needed`
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

## Notes

- The user did not specify a paper count, so later retrieval should collect broad relevant PubMed coverage for downstream RAG and verification.
- The initial draft should use a scope-driven outline broad enough to cover approved and investigational inhibitors, clinical trials, laboratory mechanisms, patient-derived evidence, and combination strategies.
- Clinical trial papers across phases, including successful, negative, failed, discontinued, and combination trials, are a user-stated priority.
- Named inhibitor anchors include alpelisib, inavolisib, STX478/STX-478, and RLy2608/RLY-2608.
- Reviews may support background and citation discovery, but primary mechanistic and clinical claims should be verified against primary studies where possible.
- Preprints are included by default but must be labeled clearly.
- Full text should be reviewed whenever available. If full text is unavailable, title and abstract may be reviewed and papers needing full text for confident verification should be added to a user-download queue.
- PubMed is the required primary discovery source.
- The hard blocklist at `resources/journal_blocklist.csv` must be applied.
- Venue reputation should be labeled conservatively and uncertain venue-dependent claims should remain visible for expert inspection.


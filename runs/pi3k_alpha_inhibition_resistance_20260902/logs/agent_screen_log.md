# Agent Screen Log

This file records substantive screen-visible agent output for this run:
progress updates, decisions, validation outcomes, handoff notes, and final
summaries. It must not include hidden chain-of-thought, credentials, paper full
text, or large generated artifacts.

## 2026-09-02T00:00:00Z - artifact-organization-retrospective

Organized the run artifacts into numbered stage folders. `subsection_retrieval`
now uses `01_scope`, `02_queries`, `03_pubmed`, `04_screening`, `05_recall`,
and `06_outputs`. `semantic_abstract_review` now uses `01_setup`,
`02_context`, `03_batches`, `04_reviewed_batches`, and `05_outputs`.
`workflow_control` now stores the canonical SQLite database in `01_state` and
snapshots in `02_snapshots`. `draft_validation` now stores draft checks in
`01_checks`. Validation passed for `semantic_abstract_review_complete` after
the reorganization.

## 2026-09-03T05:04:55Z - workflow-maintenance

Added a required run-level screen log at logs/agent_screen_log.md and added validator checks for screen-log presence plus artifact folder organization. Updated reusable instructions, workflow documentation, run README, and validation contract so future agents keep stage artifacts inside numbered folders.

## 2026-09-03T05:06:30Z - workflow-maintenance

Completed the run-level logging and artifact-layout validation update. The validator now requires logs/agent_screen_log.md and checks that artifact stage folders keep files inside numbered subfolders, with only README.md allowed at stage roots. Final validation passed for semantic_abstract_review_complete, and reusable workflow scans found no stale flat artifact paths or topic-specific wording.

## 2026-09-03T05:38:34Z - pipeline-health-check

Checked the pipeline after adding run-level screen logging and artifact-layout validation. Current PI3K run passes semantic_abstract_review_complete validation. Tool files compile, workflow_contract.json parses, required files are allowed by their contracts, reusable files have no stale flat artifact paths, reusable files have no PI3K/PAX/topic-specific wording, and the run artifact tree follows numbered stage subfolders. Stages 1-4 are implemented; Stage 5 and later are workflow-specified but not yet implemented with scripts/contracts.

## 2026-09-03T06:20:20Z - primary_full_text_ingestion

Updated Stage 5 workflow design: primary-only full-text ingestion from PMC XML/PDF, source discovery through PMC/Europe PMC/OpenAlex/Semantic Scholar/CORE, GROBID PDF normalization, SQLite mirroring, and a deliberate manual PDF pause gate.

## 2026-09-03T06:32:00Z - primary_full_text_ingestion

Ran Stage 5 on the PI3K primary cohort. Automated ingestion normalized 48 of 71 primary papers and produced a deliberate manual PDF queue for 23 unresolved primary papers; validation is being run before any downstream step.

## 2026-09-03T06:34:33Z - primary_full_text_ingestion

Stage 5 validation passed. The PI3K run is deliberately paused at blocked_user_pdf_required: 71 primary targets, 48 normalized full texts, 42 PMC XML, 6 PDF/GROBID, and 23 unresolved primary papers in the manual PDF queue.

## 2026-09-03T06:39:10Z - artifact_layout

Migrated artifact root stages to numbered folders: 00_workflow_control, 01_draft_validation, 02_subsection_retrieval, 03_semantic_abstract_review, and 04_primary_full_text_ingestion. Also numbered nested Stage 5 corpus folders and updated validation to reject unnumbered artifact directories recursively.

## 2026-09-03T17:12:01Z - primary_full_text_ingestion

User provided manually downloaded PDFs in the Stage 5 dropbox. Updated generic PDF staging to match title-like filenames in addition to PMID, PMCID, DOI, and paper_id.

## 2026-09-03T17:19:10Z - primary_full_text_ingestion

Refined Stage 5 generically: manual_pdf_queue.csv is now deduplicated as a user-action queue with linked paper IDs for exact title collisions; PDF normalization is explicitly enforced as GROBID TEI only, with chunks derived from normalized PMC/GROBID section text.

## 2026-09-03T17:23:11Z - primary_full_text_ingestion

Fixed Stage 5 manual PDF queue deduplication and GROBID enforcement. The manual queue now has 22 user-action rows covering 23 unresolved primary paper records, with the duplicate BYLieve title represented as one linked row. Validation now requires PDF-derived normalized JSON to come from cached GROBID TEI under 04_pdf/02_parser_cache/01_grobid and to include non-empty chunks derived from normalized full text. Reran Stage 5 with --skip-network; validation passed and the run remains deliberately paused because GROBID is not reachable for the 21 staged PDFs that still need TEI parsing.

## 2026-09-03T17:27:46Z - primary_full_text_ingestion

User added the two previously unmatched PDFs. PMID 40845250 matched directly from filename. The ScienceDirect-style file was staged as PMID_38986734.pdf based on the user's statement that these were the two missing papers. Updated Stage 5 generically so reruns recognize expected staged PDFs and route them to GROBID rather than requiring filename rematching. Reran Stage 5; all 23 unresolved paper records now have staged/user PDF status but remain blocked until GROBID TEI parsing is available.

## 2026-09-03T17:37:14Z - primary_full_text_ingestion

Continued Stage 5 after user provided the remaining PDFs. Started local GROBID in Docker on host port 8072 and reran primary_full_text_ingestion with GROBID_BASE_URL=http://127.0.0.1:8072. All 71 primary papers are now normalized: 42 from PMC XML and 29 from PDF parsed through cached GROBID TEI. Regenerated completion artifacts and Stage 5 validation passed.

## 2026-09-03T17:38:03Z - primary_full_text_ingestion

Stage 5 validation was rerun after completion and now writes validation_status=passed back to SQLite. Final audited state: 71/71 primary papers normalized, including 42 PMC XML normalized files and 29 PDF normalized files derived from cached GROBID TEI; manual_pdf_queue.csv has zero data rows.

## 2026-09-03T17:39:02Z - primary_full_text_ingestion

Repaired Stage 5 metadata consistency generically: normalized PDF rows now repair and validate pdf_status=normalized and parser_status=normalized when cached normalized JSON exists. Reran Stage 5 from cached GROBID TEI/JSON and validation passed with SQLite validation_status=passed.

## 2026-09-03T17:40:09Z - primary_full_text_ingestion

Fixed a rerun metadata bug: user PDF staging now skips already-normalized rows, so cached PDF/GROBID outputs no longer regress pdf_status/parser_status. Reran Stage 5 and validation passed.

## 2026-09-03T17:51:44Z - primary_full_text_ingestion

Updated full-text chunking to the retrieval-oriented structure_aware_1000_150 policy borrowed from raglab: preserve section/paragraph boundaries when possible, split oversized paragraphs sentence-safely with 150-character overlap, and apply the same rule to PMC XML and GROBID PDF normalized text. Regenerated Stage 5 normalized JSON chunks for the PI3K run.

## 2026-09-03T18:00:55Z - full_text_rag_index

Implemented and ran Stage 6 full-text RAG indexing. Borrowed raglab design: structure_aware_1000_150 chunks, BM25 over the same chunk records, optional Qdrant semantic index with text-embedding-3-small, reciprocal-rank fusion config, and paper-level aggregation for downstream subsection rewriting. Built chunks.jsonl/chunk_manifest/paper_manifest, BM25 artifact, retrieval_config, SQLite full_text_chunks and rag_index_artifacts. Validation passed with 71 papers and 4002 chunks. Vector index was not requested because no OPENAI_API_KEY was present in the shell.

## 2026-09-03T18:12:37Z - full_text_rag_index

Completed the required Stage 6 vector index after user confirmed RAG should be default. Loaded OPENAI_API_KEY from the provided .env path, embedded 4002 full-text chunks with text-embedding-3-small, built the local Qdrant collection full_text_primary_1000o150_te3_small, kept BM25 complete over the same chunk records, and validation passed. Validator now exempts Qdrant internal storage folders under the approved numbered vector artifact directory while keeping the rest of the artifact layout strict.

## 2026-09-03T18:26:37Z - workflow_health_check

Audited reusable workflow genericity and validation behavior after Stage 6 growth. Updated validator with --allow-later-steps for completed-run audits while preserving strict per-step gates; aligned API dependency markers with required OpenAI embeddings for Stage 6; refreshed artifact README naming to numbered stage folders. Validation passed for prompt_intake, initial_review_draft, subsection_retrieval, semantic_abstract_review_complete, primary_full_text_ingestion, and full_text_rag_index in completed-run audit mode; full_text_rag_index also passed strict validation.

## 2026-09-03T18:29:22Z - readme_cleanup

Cleaned the root README into a concise project orientation page and rewrote runs.README.md as a compact run-folder contract. Revalidated all implemented stages in completed-run audit mode and confirmed the latest strict full_text_rag_index gate still passes.

## 2026-09-03T18:44:04Z - subsection_rag_retrieval

Completed Stage 7 subsection RAG retrieval after user approval to embed full draft subsection queries. Generated 18 subsection paper packets, 2,494 fused chunk hits, 823 paper rankings, and 180 selected subsection-paper pairs. Validation passed; SQLite mirrors contain 18 queries, 2,494 chunk hits, and 823 paper rankings.

## 2026-09-03T19:04:53Z - narrative_core_normalization

Updated Stage 5 normalization to use a raglab-inspired narrative-core stream before chunking: keep abstract, introduction-like narrative, result-bearing sections, and discussion/conclusion synthesis; exclude methods, references, acknowledgements, figure/table captions, supplementary/end matter, procedural sections, and metadata-heavy sections. Raw parser text remains in normalized JSON for audit, but Stage 6/7 index `narrative_text` and chunks. Regenerated Stage 5 with 71/71 primary papers normalized and 2,862 narrative chunks; Stage 5 validation passed. Rebuilt Stage 6 embeddings/BM25 and reran Stage 7; Stage 6 and Stage 7 validation passed. Stage 7 selected 57 unique PMIDs from 71 Stage 4 primary PMIDs, giving 80.3% deduplicated primary recall. PMID 25409150 is now recovered in Stage 7 packets for SUB004, SUB010, and SUB018.

## 2026-09-03T19:13:38Z - narrative_qc_report

Added Stage 5 narrative QC reporting and excluded-section audit metadata. Normalized JSON now records `excluded_sections` with section title, class, reason, and character count, while RAG continues to use only `narrative_text` and `chunks`. Wrote `artifacts/04_primary_full_text_ingestion/06_outputs/narrative_qc_report.csv`; PI3K QC results were 64 pass, 6 watch, and 1 inspect_for_possible_overfiltering across 71 normalized primary papers. Validation now requires the QC report and excluded-section audit list; Stage 5, Stage 6, and Stage 7 validations passed.

## 2026-09-03T19:25:14Z - subsection_rewrite_setup

Audited reusable workflow files and logic after Stage 7. Added Stage 8 evidence-grounded subsection rewrite scaffolding: `prepare_subsection_rewrite.py`, `verify_subsection_rewrite.py`, Stage 8 SQLite tables, rewrite agent instructions, rewrite/verifier system prompts, validation rules, and workflow-contract entries for `subsection_rewrite_setup` and `subsection_rewrite`. Ran Stage 8 setup on the PI3K run and generated 18 original subsection snapshots, 18 work orders, a rewrite manifest, an initial rewrite check CSV, and a setup summary under `artifacts/07_subsection_rewrite/`. Validation passed through `subsection_rewrite_setup`; final `subsection_rewrite` remains intentionally incomplete until writing agents produce rewritten subsection files.

## 2026-09-03T19:37:04Z - stage7_primary_recall_policy

Updated Stage 7 packet selection so Stage 4 `primary_for_subsection` papers are always carried into their subsection packet. If a primary paper is ranked below the default top-10 cutoff, it is selected with `selection_reason=stage4_primary_force_included`; if it has normalized chunks but no subsection query hit, it is added with abstract/introduction/result fallback chunks and `selection_reason=stage4_primary_recall_added_no_query_hit`. Reran Stage 7 and refreshed Stage 8 work orders. Stage 7 now selects 71/71 Stage 4 primary PMIDs for 100.0% deduplicated primary recall, with 180 top-ranked pairs, 30 force-included pairs, and 10 no-query-hit recall-added pairs. Stage 7 and Stage 8 setup validations passed.

## 2026-09-03T19:53:51Z - subsection_rewrite

Updated Stage 8 rewrite contract: every packet paper must be triaged; rewrite prose must be at least 250 words and at least 1.5x original subsection length; cited papers must be traceable packet papers with inline citations and structured evidence details; normalized narrative full-text sources must be acknowledged.

## 2026-09-03T20:05:39Z - subsection_rewrite

Completed Stage 8 rewrite execution for 18 subsections using parallel workers. Controller verification passed for all 18 rewritten subsections under the stricter triage, expansion, inline citation, full-text acknowledgement, and structured evidence-detail checks.

## 2026-09-03T20:17:43Z - terminology_normalization

Completed Stage 9 terminology normalization with 13 run-specific alias entities and 18 normalized subsection copies. Validation passed; citation IDs were preserved and known aliases were normalized in downstream copies.

## 2026-09-03T20:22:45Z - review_assembly

Started Stage 10 review assembly from terminology-normalized subsection rewrites. Assembly preserves subsection order, citation registers, and residual uncertainty without adding new scientific claims.

## 2026-09-03T20:23:08Z - review_assembly

Completed Stage 10 review assembly. Assembled 18 terminology-normalized subsections into drafts/assembled_review.md, preserving 155 citation-register rows and residual uncertainty sections. Validation passed.

## 2026-09-03T20:30:03Z - claim_verification

Started Stage 11 claim-level verification setup from drafts/assembled_review.md. The setup extracts citation-bearing claims and prepares per-subsection work orders for evidence review against cited papers only.

## 2026-09-03T20:42:24Z - claim_verification

Completed Stage 11 claim-level verification. Controller verification and formal validation passed for 123/123 reviewed claims. Status counts: 118 supported, 5 partially_supported. These 5 claims should feed the next corrective rewrite queue.

## 2026-09-03T20:51:54Z - corrective_rewrite

Stage 12 corrective rewrite completed and passed validation. Five non-supported claim-verification decisions were applied to drafts/corrected_review.md without introducing new citation IDs or paper IDs.

## 2026-09-03T21:00:12Z - final_review

Stage 13 final review completed and passed validation. The final review writer pass produced drafts/final_review.md with continuous main prose, an evidence appendix, preserved citation IDs, and preserved paper IDs.

## 2026-09-03T21:09:22Z - final_review

Stage 13 final review regenerated with compact numbered citations and a deduplicated References section. The oversized evidence appendix was removed from the final draft; detailed citation registers remain in upstream audit artifacts. Final validation passed with 62 unique references.

## 2026-09-03T21:12:19Z - final_review

Stage 13 final review regenerated without an Orientation section. Final review now contains Abstract, Main Review, Synthesis For Human Inspection, and References; workflow citation IDs and paper IDs are absent from the main text. Final validation passed.

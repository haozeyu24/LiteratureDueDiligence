# Draft-First Claim-Centered Biomedical Literature Due Diligence Workflow

## Objective

Transform an initial LLM-generated biomedical or drug-discovery literature
review into an evidence-grounded, scientifically accurate review by verifying
and rewriting it claim by claim.

This workflow deliberately does not try to collect the entire literature before
writing. Instead, it uses the first review draft to expose the claims, chapters,
mechanisms, citations, and gaps that need targeted verification.

## Design Principles

1. Draft first, then interrogate the draft.
2. Treat the initial review as a hypothesis scaffold, not as evidence.
3. Preserve the original user prompt unchanged.
4. Convert the user prompt into explicit, structured workflow inputs.
5. Keep reusable workflow files generic across biomedical and drug-discovery
   topics.
6. Put topic-specific content only inside `runs/<run_id>/`.
7. Verify claims locally with targeted evidence packets.
8. Rewrite from verified evidence, not from model confidence.
9. Use human scientific inspection as the final authority.
10. Validate every step before moving forward.
11. Reject side artifacts that are not declared by the current workflow step.
12. Search broadly when users do not specify paper count, so later RAG and claim
    verification have enough evidence to work with.
13. Prefer full text for verification, but preserve title/abstract-only evidence
    and route missing full text into a user-download queue.
14. Include preprints by default while labeling them as preprint evidence.
15. Apply hard venue exclusions and keep uncertain venue-quality judgments
    visible.
16. Keep a run-level screen log so agent-visible progress text, decisions, and
    final summaries remain auditable.
17. Acknowledge draft-framing confirmation bias: because retrieval starts from
    the LLM-generated draft, the workflow primarily expands, verifies, and
    corrects that framing rather than performing adversarial
    contradiction-seeking retrieval. Human review should weight this limitation
    higher for novel, controversial, or weakly established mechanisms.

## Run-Level Logs

Every run must contain:

- `logs/agent_screen_log.md`

Agents should append the substantive words they show on screen: progress
updates, decisions, validation results, handoff notes, and final summaries.
This includes tooling bugs, compatibility repairs, validation failures,
workarounds, worker/subagent assignments, skipped steps, and pauses. If the
human saw the operational statement on screen, the run log should contain the
same substantive information.
This log is not the canonical scientific evidence store. It is an audit trail
for what the human and future agents saw during the run.

Agents may append consistently with:

```bash
python3 tools/00_workflow_control/append_agent_log.py runs/<run_id> --agent <step_name> --message "..."
```

Use this entry shape:

```markdown
## 2026-09-02T12:34:56Z - <agent-or-step-name>

<screen-visible message, decision, or final summary>
```

Do not store paper full text, hidden chain-of-thought, private credentials, or
large generated artifacts in the screen log.

`validate_step.py` writes validation pass/fail outcomes into the screen log
automatically. Agents must still log non-validation progress and decisions.

## Paper And Venue Policy

PubMed is the required primary literature discovery source for this workflow.
Later steps may use other sources only when explicitly declared by a workflow
module or requested by the user.

Out-of-scope sources for the current workflow include patents, company websites,
press releases, regulatory labels, investor decks, and general web pages. These
may matter for venture due diligence, but they should be separate modules rather
than mixed into the literature-review evidence base.

When no paper count is specified, retrieval should aim for broad relevant
coverage for downstream RAG and verification rather than forcing a small
arbitrary paper target.

The workflow includes preprints by default because emerging claims may appear
before peer-reviewed publication. Preprints must be labeled clearly and should
not by themselves establish settled claims when peer-reviewed evidence is
available.

Full text should be reviewed whenever available. When full text is unavailable,
agents should review title and abstract, label the evidence as
title/abstract-only, and add papers needing full text to a user-download queue.
Lack of full-text access is an access state, not a scientific exclusion.

Venue quality is handled conservatively:

- hard-block venues listed in `resources/journal_blocklist.csv`
- prefer reputable or likely reputable venues
- label uncertain venues rather than pretending a static whitelist is complete
- route uncertain venue-dependent claims to human inspection

## Validation Gate

Every workflow step must have a validation contract before it is considered
implemented.

Validation has two jobs:

- prevent premature stopping by checking that required files exist and are
  populated
- prevent workflow drift by rejecting files that the current step was not
  supposed to create

Run validation with:

```bash
python3 tools/00_workflow_control/validate_step.py <step_name> runs/<run_id>
```

A step is not complete unless validation exits with code `0`.
When auditing an already advanced run, add `--allow-later-steps` so the
validator still checks the selected step while accepting declared downstream
artifacts.

The declarative contract lives at `validation/workflow_contract.json`.

## Workflow Stages

### 1. Prompt Intake

Convert the user's free-form scientific request into structured inputs:

- scientific objective
- audience and downstream use
- desired review product
- primary entities
- biomedical system, disease area, population, method, model, treatment, target,
  or conceptual scope
- evidence goals
- retrieval boundaries
- paper preferences
- citation and verification requirements
- uncertainty and controversy priorities

Outputs:

- `original_user_prompt.md`
- `logs/agent_screen_log.md`
- `inputs/structured_instruction.md`
- `inputs/run_config.md`
- `inputs/intake_self_check.md`

Validation:

```bash
python3 tools/00_workflow_control/validate_step.py prompt_intake runs/<run_id>
```

### 2. Initial Review Draft

Use the current user-selected agent or model to generate the first review draft
from the structured instruction. A future workflow version may recommend the
most recent frontier model API for this stage to improve conceptual recall,
mechanism breadth, citation clues, and search-target coverage, but V1 must not
treat that API as a hard dependency.

The draft must be verification-ready, not merely polished prose. Every
substantive subsection must include a `#### Citation Register` table listing the
citations used or needed in that subsection, with PMID/DOI fields when known,
draft access status, venue trust label, discovery provenance, evidence role, and
notes for later agents.

The draft should also be expansive. Unless the run config overrides this, the
initial draft should include at least 6 chapters, at least 18 substantive
subsections, at least 150 words and 2 prose paragraphs per substantive
subsection, and at least 4 citation-register rows per substantive subsection.
When the drafting agent cannot confidently name enough real citations, it should
add `citation needed` rows with `PMID` and `DOI` set to `unknown` and notes
describing what later PubMed retrieval should search for.

`draft_access_status` is provisional. It tells downstream agents what the draft
believes about access or where full text may be needed. It does not prove that
full text is actually available. Later retrieval steps must resolve verified
access status.

`discovery_provenance` is also required. It tells downstream agents whether a
citation was found by explicit PubMed search, found by full-text search, carried
from an earlier local workflow artifact, recalled from LLM memory, or left as a
search target. This prevents searched literature from being silently mixed with
model memory.

Allowed draft access labels:

- `full_text_likely_available`
- `abstract_only_likely`
- `title_only_likely`
- `access_unknown`
- `full_text_needed_for_verification`

Allowed venue trust labels:

- `reputable_or_likely_reputable`
- `uncertain`
- `preprint_server`
- `hard_blocked`
- `unknown`

Allowed discovery provenance labels:

- `searched_pubmed`
- `searched_full_text`
- `local_prior_run`
- `llm_memory`
- `citation_needed`
- `unknown`

After the draft is written, a verifier agent must check that the draft follows
the drafting instructions before the workflow may continue.

Outputs:

- `drafts/initial_review.md`
- `logs/agent_screen_log.md`
- `artifacts/01_draft_validation/README.md`
- `artifacts/01_draft_validation/01_checks/draft_instruction_check.md`

Folder organization:

- `artifacts/01_draft_validation/01_checks/`: verifier reports for the initial
  draft. This folder should contain checks only, not retrieval outputs or
  rewritten review content.

Validation:

```bash
python3 tools/00_workflow_control/validate_step.py initial_review_draft runs/<run_id>
```

### 3. Subsection PubMed Retrieval And Metadata Staging

Convert the initial draft into subsection-level retrieval work. Each
subsection becomes its own controlled PubMed search loop with scientifically
constrained queries, metadata collection, draft-citation recall checks, and
full-text routing.

The controller reads each subsection and its citation register, creates at
least one high-precision query, one mechanism-expansion query, one
context-expansion query, and one recall-guard query, checks result-count
quality, downloads PubMed metadata locally, and verifies whether draft
citations were recovered.

This step should not download PDFs or build evidence packets yet. It should
record what is ready for semantic abstract review and what needs query
revision before abstract review can begin.

Outputs:

Canonical state:

- `artifacts/00_workflow_control/01_state/workflow_state.sqlite`

Workflow-control folder organization:

- `artifacts/00_workflow_control/01_state/`: canonical SQLite workflow database.
- `artifacts/00_workflow_control/02_snapshots/`: derived JSON state snapshots for
  audit and handoff.

Folder organization:

- `artifacts/02_subsection_retrieval/01_scope/`: subsection manifest.
- `artifacts/02_subsection_retrieval/02_queries/`: controller policy, query plan,
  query diagnostics, and search logs.
- `artifacts/02_subsection_retrieval/03_pubmed/`: locally staged PubMed metadata.
- `artifacts/02_subsection_retrieval/04_screening/`: deterministic abstract triage
  exports used before semantic review.
- `artifacts/02_subsection_retrieval/05_recall/`: draft-citation recall checks.
- `artifacts/02_subsection_retrieval/06_outputs/`: compact metrics, literature-set
  exports, primary full-text target list, and validation report.

Compact human-facing outputs:

- `artifacts/02_subsection_retrieval/02_queries/query_plan.csv`
- `artifacts/02_subsection_retrieval/02_queries/query_diagnostics.csv`
- `artifacts/02_subsection_retrieval/06_outputs/subsection_metrics.csv`
- `artifacts/02_subsection_retrieval/05_recall/draft_citation_recall_check.csv`
- `artifacts/02_subsection_retrieval/06_outputs/subsection_retrieval_check.md`

Detailed audit exports, generated from SQLite or used for agent handoff:

- `artifacts/00_workflow_control/02_snapshots/workflow_state_snapshot.json`
- `artifacts/02_subsection_retrieval/01_scope/subsection_manifest.csv`
- `artifacts/02_subsection_retrieval/03_pubmed/pubmed_records.jsonl`
- `artifacts/02_subsection_retrieval/03_pubmed/pubmed_record_index.csv`
- `artifacts/02_subsection_retrieval/02_queries/search_iteration_log.csv`
- `artifacts/02_subsection_retrieval/04_screening/abstract_triage_first_pass.csv`
- `artifacts/02_subsection_retrieval/04_screening/abstract_triage_rescue_pass.csv`
- `artifacts/02_subsection_retrieval/06_outputs/final_literature_sets.csv`
- `artifacts/02_subsection_retrieval/06_outputs/full_text_download_queue.csv`

Controller policy text can live in reusable instructions; per-run policy files
should be generated only when they help the worker handoff or human audit.

Validation:

```bash
python3 tools/00_workflow_control/validate_step.py subsection_retrieval runs/<run_id>
```

### 4. Semantic Abstract Review

Before semantic abstract review begins, run:

```bash
python3 tools/00_workflow_control/validate_step.py semantic_abstract_review_preflight runs/<run_id>
```

This preflight must pass. It blocks the next step when any subsection still has
`query_revision_needed`, `manual_search_needed`, `blocked`, `not_run`, or any
status other than `abstract_review_needed`.

Semantic abstract review is the primary precision filter. It reads each
subsection and its candidate PubMed titles/abstracts, compares each abstract
directly with the subsection prose, and fills semantic review fields including
mechanism match, entity/context match, evidence directness, semantic fit score,
and why full text is or is not needed.

Reviewed batch rows must be produced by LLM semantic reading of the subsection
context plus each title/abstract. Keyword filters, regex scripts, and
deterministic classifiers may prepare or audit candidates, but they must not
create final reviewed rows. Every reviewed row must include `reviewer_id`,
`review_method=llm_semantic_reading`, `reviewer_model_or_agent`, and
`reviewed_at`.

Prepare review batches:

```bash
python3 tools/04_semantic_abstract_review/prepare_abstract_review_batches.py runs/<run_id>
```

Folder organization:

- `artifacts/03_semantic_abstract_review/01_setup/`: reviewer instructions, batch
  manifest, status tracker, and setup validation report.
- `artifacts/03_semantic_abstract_review/02_context/`: one subsection context file
  per draft subsection.
- `artifacts/03_semantic_abstract_review/03_batches/`: unreviewed
  subsection-paper CSV batches for workers.
- `artifacts/03_semantic_abstract_review/04_reviewed_batches/`: reviewed CSV
  batches returned by workers.
- `artifacts/03_semantic_abstract_review/05_outputs/`: merge report and compact
  completion outputs.

Validate setup:

```bash
python3 tools/00_workflow_control/validate_step.py semantic_abstract_review_setup runs/<run_id>
```

Because subsections are independent after preflight, this stage is suitable for
parallel subagents: one worker per subsection or per subsection batch. Workers
must write only declared abstract-review artifacts, and a controller must merge
their decisions before the workflow advances.

Merge reviewed batches back into SQLite:

```bash
python3 tools/04_semantic_abstract_review/merge_abstract_review_decisions.py runs/<run_id>
```

The merge writes durable decisions to SQLite table
`abstract_review_decisions`, updates `abstract_review_batches`, recomputes
`subsection_metrics`, updates the paper-level `paper_review_rollup`, and
regenerates the filtered literature set and user-download queue from database
state.

The completion report must include deduplicated draft-PMID recall against the
global primary cohort:

```text
unique draft PMIDs retained as include_primary anywhere / unique draft PMIDs
```

Validate completion:

```bash
python3 tools/00_workflow_control/validate_step.py semantic_abstract_review_complete runs/<run_id>
```

This completion check must pass before full-text retrieval, vector database
construction, claim verification, or rewriting begins.

Output:

- SQLite table `abstract_review_decisions`
- SQLite table `abstract_review_batches`
- SQLite table `paper_review_rollup`
- `artifacts/03_semantic_abstract_review/05_outputs/semantic_abstract_review_merge_report.md`
- `artifacts/02_subsection_retrieval/06_outputs/final_literature_sets.csv`
- `artifacts/02_subsection_retrieval/06_outputs/full_text_download_queue.csv`
- `artifacts/02_subsection_retrieval/06_outputs/subsection_metrics.csv`

### 5. Primary Full-Text Ingestion

Build the first full-text corpus for later vector database construction and
claim-level verification. This step focuses only on globally primary papers
from `paper_review_rollup`.

Ingestion policy:

- Primary evidence: attempt PMC XML first, then open PDFs discovered through
  Europe PMC, OpenAlex, Semantic Scholar, and CORE when `CORE_API_KEY` is
  available.
- Only two corpus formats are stored: PMC XML and PDF.
- Do not infer full-text usability from PMCID presence alone; some PMCID records
  may lack useful XML for downstream verification.
- Context and uncertain papers are deferred by default. They can be ingested in
  a later expansion step if primary evidence is insufficient.
- Globally excluded or hard-blocked papers are not ingested unless a human
  explicitly overrides the exclusion.
- PDFs are normalized and chunked through the workflow's canonical GROBID TEI
  method: call `/api/processFulltextDocument`, cache the returned TEI XML,
  normalize body text and sections from TEI, then derive chunks from those
  normalized TEI sections/body text. Direct PDF text extraction,
  PDF-viewer copy/paste, OCR, or browser text extraction is not a valid Stage 5
  normalization fallback.
- PMC XML and GROBID TEI are converted into a narrative-core stream before
  chunking. Preserve title/abstract metadata, abstract text, introduction-like
  narrative, result-bearing sections/subsections, and discussion/conclusion
  synthesis. Exclude methods, references, acknowledgements, affiliations, figure
  legends, tables, supplementary/end matter, procedural sections, and
  metadata-heavy sections. When classification is uncertain, keep the section
  unless it is clearly methods/end matter, because over-filtering is more
  dangerous than retaining a small amount of extra narrative.
- Store raw XML, raw PDF, cached GROBID TEI, and normalized JSON for audit.
  Downstream RAG must index `narrative_text`/`chunks`, not the unfiltered
  parser `raw_text`.
- Write a narrative QC report after normalization. The report should flag papers
  with unusually low narrative/raw retention, low absolute narrative text, very
  few kept sections/chunks, or a large excluded fraction. These flags are an
  inspection queue, not automatic failure: an agent or human can decide whether
  the filter was correct, whether a generic rule should improve, or whether a
  paper-specific manual narrative override is needed.
- Full-text chunks use the `structure_aware_1000_150` policy for both PMC XML
  and GROBID PDF normalizations: `1000` character target size, `150` character
  overlap only when splitting oversized paragraphs, preserve whole sections and
  paragraphs when they fit, and split long paragraphs sentence-safely.
- If GROBID is unavailable, or a PDF cannot be parsed into usable TEI body text,
  the paper remains unresolved.
- `manual_pdf_queue.csv` is a user-action queue. It is deduplicated by stable
  paper identity and exact normalized title groups; title-collision groups keep
  all paper records in SQLite and `import_status.csv` through linked IDs.

The full-text ingestion step should read `paper_review_rollup` and
`abstract_review_decisions` from SQLite. It should not infer ingestion targets
from raw PubMed candidates or from PMCID metadata alone.

Preflight:

```bash
python3 tools/00_workflow_control/validate_step.py semantic_abstract_review_complete runs/<run_id>
```

Run:

```bash
python3 tools/05_primary_full_text_ingestion/primary_full_text_ingestion.py runs/<run_id>
```

If automated ingestion cannot normalize all primary papers, the step writes a
manual PDF queue and deliberately pauses with status
`blocked_user_pdf_required`.

To provide PDFs, place them in:

```text
runs/<run_id>/artifacts/04_primary_full_text_ingestion/05_user_pdf_request/01_user_pdf_dropbox/
```

Then rerun:

```bash
python3 tools/05_primary_full_text_ingestion/primary_full_text_ingestion.py runs/<run_id>
```

or use:

```bash
python3 tools/05_primary_full_text_ingestion/primary_full_text_ingestion.py runs/<run_id> --user-pdf-dropbox <folder>
```

To proceed without unresolved PDFs, the user must explicitly choose that route,
then the agent runs:

```bash
python3 tools/05_primary_full_text_ingestion/primary_full_text_ingestion.py runs/<run_id> --continue-without-user-pdfs
```

Validation:

```bash
python3 tools/00_workflow_control/validate_step.py primary_full_text_ingestion runs/<run_id>
```

Output:

- SQLite table `full_text_ingestion`
- SQLite table `full_text_source_candidates`
- `artifacts/04_primary_full_text_ingestion/01_targets/primary_fulltext_targets.csv`
- `artifacts/04_primary_full_text_ingestion/02_discovery/fulltext_source_candidates.csv`
- `artifacts/04_primary_full_text_ingestion/03_pmc/01_raw_xml/`
- `artifacts/04_primary_full_text_ingestion/03_pmc/02_normalized/`
- `artifacts/04_primary_full_text_ingestion/04_pdf/01_staged/`
- `artifacts/04_primary_full_text_ingestion/04_pdf/02_parser_cache/01_grobid/`
- `artifacts/04_primary_full_text_ingestion/04_pdf/03_normalized/`
- `artifacts/04_primary_full_text_ingestion/05_user_pdf_request/manual_pdf_queue.csv`
- `artifacts/04_primary_full_text_ingestion/05_user_pdf_request/user_pdf_pause.md`
- `artifacts/04_primary_full_text_ingestion/06_outputs/import_status.csv`
- `artifacts/04_primary_full_text_ingestion/06_outputs/pdf_parse_report.csv`
- `artifacts/04_primary_full_text_ingestion/06_outputs/narrative_qc_report.csv`
- `artifacts/04_primary_full_text_ingestion/06_outputs/ingestion_summary.md`

This validation may pass while the workflow is deliberately blocked for user
PDFs. Passing validation means the pause is explicit, auditable, and safe; it
does not authorize downstream RAG indexing until Stage 5 is complete or the user
explicitly chooses to continue with missing full text.

### 6. Full-Text RAG Index

Flatten the validated Stage 5 PMC/GROBID chunks into a run-local retrieval
corpus, mirror chunks into SQLite, build a BM25 lexical index, and build a local
Qdrant semantic index with `text-embedding-3-small`.

Borrowed `raglab` design choices:

- Use `structure_aware_1000_150` chunks.
- Keep BM25 and semantic retrieval over the same chunk records.
- Use reciprocal-rank fusion for hybrid retrieval.
- Rank chunks first, then aggregate to papers.
- Select paper-level evidence packets for rewriting rather than sending
  isolated chunks directly to the rewrite agent.

Run:

```bash
python3 tools/06_full_text_rag_index/build_full_text_rag_index.py runs/<run_id> --env-file .env
```

If `OPENAI_API_KEY` is missing, the agent must stop and ask the user to add an
API key. The workflow does not continue past Stage 6 without a completed vector
index.

Validation:

```bash
python3 tools/00_workflow_control/validate_step.py full_text_rag_index runs/<run_id>
```

Output:

- SQLite table `full_text_chunks`
- SQLite table `rag_index_artifacts`
- `artifacts/05_full_text_rag_index/01_chunks/chunks.jsonl`
- `artifacts/05_full_text_rag_index/01_chunks/chunk_manifest.csv`
- `artifacts/05_full_text_rag_index/01_chunks/paper_manifest.csv`
- `artifacts/05_full_text_rag_index/02_lexical/bm25.pkl`
- `artifacts/05_full_text_rag_index/02_lexical/bm25_summary.json`
- `artifacts/05_full_text_rag_index/03_vector/vector_index_summary.json`
- `artifacts/05_full_text_rag_index/04_hybrid/retrieval_config.json`
- `artifacts/05_full_text_rag_index/05_outputs/rag_index_summary.md`

### 7. Subsection RAG Retrieval

For every draft subsection, query the Stage 6 RAG index using the full draft
subsection prose, draft citation clues, and subsection title. Retrieve BM25 and
semantic chunk hits, fuse them with reciprocal-rank fusion, aggregate chunks to
paper-level rankings, and emit one paper packet per subsection.

Paper-packet selection should preserve Stage 4 recall. Select the default
top-ranked papers per subsection, and also force-include any Stage 4
`primary_for_subsection` paper for that same subsection whenever it appears in
the Stage 7 paper ranking. Label these with `selection_reason =
stage4_primary_force_included` so rewrite agents know they were included for
recall preservation rather than because they ranked in the top packet cutoff.
If a Stage 4 primary paper has normalized chunks but no subsection query hit,
add it with `selection_reason = stage4_primary_recall_added_no_query_hit` using
abstract/introduction/result chunks as a recall-preserving fallback.

This stage creates a retrieval handoff, not final prose. A retrieved paper is
not automatically treated as supporting evidence. The rewrite stage must still
judge whether each paper supports, contradicts, contextualizes, or fails to
address the subsection.

Required action:

```bash
python3 tools/07_subsection_rag_retrieval/build_subsection_rag_retrieval.py runs/<run_id> --env-file .env
```

Validation:

```bash
python3 tools/00_workflow_control/validate_step.py subsection_rag_retrieval runs/<run_id>
```

Output:

- SQLite table `subsection_rag_queries`
- SQLite table `subsection_rag_chunk_hits`
- SQLite table `subsection_rag_paper_rankings`
- `artifacts/06_subsection_rag_retrieval/README.md`
- `artifacts/06_subsection_rag_retrieval/01_queries/subsection_rag_queries.csv`
- `artifacts/06_subsection_rag_retrieval/02_chunk_hits/subsection_chunk_hits.csv`
- `artifacts/06_subsection_rag_retrieval/03_paper_ranking/subsection_paper_rankings.csv`
- `artifacts/06_subsection_rag_retrieval/04_paper_packets/SUB###.md`
- `artifacts/06_subsection_rag_retrieval/05_outputs/subsection_rag_retrieval_summary.md`

### 8. Evidence-Grounded Subsection Rewrite

Rewrite each subsection from its paper-level evidence packet and normalized
narrative full text, preserving useful draft framing while correcting
unsupported, overbroad, or hallucinated claims.

This stage is agent-run and does not require a custom API call. The preparation
script creates one work order per subsection. Writing agents may run in parallel
on disjoint subsection work orders. Each writing agent triages every packet paper
first, reads relevant narrative full-text files when available, then rewrites
the subsection into the required file shape. A verifier checks deterministic
contract compliance before claim-level verification begins.

Preflight:

```bash
python3 tools/00_workflow_control/validate_step.py subsection_rag_retrieval runs/<run_id>
```

Prepare rewrite work orders:

```bash
python3 tools/08_subsection_rewrite/prepare_subsection_rewrite.py runs/<run_id>
python3 tools/00_workflow_control/validate_step.py subsection_rewrite_setup runs/<run_id>
```

Writing agents read:

- `artifacts/07_subsection_rewrite/02_work_orders/SUB###.md`

and write:

- `artifacts/07_subsection_rewrite/03_rewritten_subsections/SUB###.md`

Each rewritten subsection must include:

- a paper triage table covering every selected paper in that subsection packet
- rewritten prose
- a citation register with `paper_id`, PMID, DOI, evidence use, support status,
  cited claim, and notes
- evidence-use notes explaining how the packet changed the draft
- residual uncertainty for missing, conflicting, or weak evidence

Rewrite rules:

- RAG limits the paper pile; it does not decide scientific truth.
- The writer must use chunk excerpts as navigation aids and inspect normalized
  narrative full text for papers that influence the subsection.
- The rewritten text must be at least 250 words and at least 1.5x the original
  subsection length unless the packet is genuinely empty or unusable.
- The prose should include biomedical evidence detail: study type, disease or
  model context, perturbation/exposure, assay/readout, direction of effect, and
  limitations.
- Every selected packet paper must appear in `## Paper Triage` as
  `core_support`, `partial_support`, `context_only`, `boundary_or_negative`, or
  `not_used`.
- The citation register may cite only packet papers that also appear in the
  triage table.
- Inline prose citations must use backticked packet paper IDs and must match the
  citation register exactly.
- The citation register must capture structured evidence detail for each cited
  paper: study context, model or population, perturbation or exposure, assay or
  endpoint, direction or result, and limitation.
- If fewer than two papers provide `core_support` or `partial_support`, the
  subsection must be framed as weak, emerging, speculative, or unresolved.

Verify rewritten subsections:

```bash
python3 tools/08_subsection_rewrite/verify_subsection_rewrite.py runs/<run_id>
python3 tools/00_workflow_control/validate_step.py subsection_rewrite runs/<run_id>
```

Output:

- SQLite table `subsection_rewrite_tasks`
- SQLite table `subsection_rewrite_checks`
- `artifacts/07_subsection_rewrite/README.md`
- `artifacts/07_subsection_rewrite/01_inputs/subsection_rewrite_manifest.csv`
- `artifacts/07_subsection_rewrite/01_inputs/SUB###.original.md`
- `artifacts/07_subsection_rewrite/02_work_orders/SUB###.md`
- `artifacts/07_subsection_rewrite/03_rewritten_subsections/SUB###.md`
- `artifacts/07_subsection_rewrite/04_verification/rewrite_instruction_check.csv`
- `artifacts/07_subsection_rewrite/05_outputs/subsection_rewrite_summary.md`

### 9. Terminology Normalization

Normalize entity aliases before review assembly and claim-level verification.
This stage is especially important after parallel subsection rewriting because
different agents may use different aliases for the same entity.

Preflight:

```bash
python3 tools/00_workflow_control/validate_step.py subsection_rewrite runs/<run_id>
```

Optional run-specific alias overrides:

```text
runs/<run_id>/inputs/terminology_alias_overrides.csv
```

Required override columns:

```csv
preferred_name,entity_type,aliases,first_mention_rule,notes
```

Generic rules:

- Preferred names are used consistently in downstream prose.
- Aliases are preserved only when they help at first mention, reflect historical
  naming in cited papers, or prevent reader confusion.
- Citation IDs, paper IDs, PMIDs, DOIs, URLs, file paths, and code identifiers
  must not be changed.
- The stage writes normalized copies; it does not mutate the Stage 8 rewritten
  files.
- No new scientific claims may be added.

Run:

```bash
python3 tools/09_terminology_normalization/normalize_terminology.py runs/<run_id>
python3 tools/00_workflow_control/validate_step.py terminology_normalization runs/<run_id>
```

Output:

- SQLite table `terminology_entities`
- SQLite table `terminology_normalization_checks`
- `artifacts/08_terminology_normalization/README.md`
- `artifacts/08_terminology_normalization/02_glossary/terminology_glossary.csv`
- `artifacts/08_terminology_normalization/03_normalized_subsections/SUB###.md`
- `artifacts/08_terminology_normalization/04_verification/terminology_normalization_check.csv`
- `artifacts/08_terminology_normalization/05_outputs/terminology_normalization_summary.md`

### 10. Review Assembly

Assemble the terminology-normalized subsection rewrites into one coherent review
draft while preserving traceability. This stage should not add scientific claims
or perform verification; it prepares a single document for claim-level checking.

Preflight:

```bash
python3 tools/00_workflow_control/validate_step.py terminology_normalization runs/<run_id>
```

Run:

```bash
python3 tools/10_review_assembly/assemble_review.py runs/<run_id>
python3 tools/00_workflow_control/validate_step.py review_assembly runs/<run_id>
```

Generic rules:

- Assemble from `artifacts/08_terminology_normalization/03_normalized_subsections/`.
- Preserve chapter and subsection order from the rewrite manifest.
- Preserve every subsection citation register and residual uncertainty note.
- Do not add new citations, claims, or interpretations.
- Do not remove citation IDs, paper IDs, PMIDs, or DOIs.
- The assembled draft is not final prose; it is the input to claim-level
  verification.

Output:

- SQLite table `review_assembly_sections`
- SQLite table `review_assembly_checks`
- `drafts/assembled_review.md`
- `artifacts/09_review_assembly/README.md`
- `artifacts/09_review_assembly/01_inputs/review_assembly_manifest.csv`
- `artifacts/09_review_assembly/02_sections/SUB###.assembled.md`
- `artifacts/09_review_assembly/03_verification/review_assembly_check.csv`
- `artifacts/09_review_assembly/04_outputs/review_assembly_summary.md`

### 11. Claim-Level Verification

After review assembly, parse the assembled review into reviewable scientific
claims and judge each claim against its cited paper evidence.

Preflight:

```bash
python3 tools/00_workflow_control/validate_step.py review_assembly runs/<run_id>
```

Prepare claim work orders:

```bash
python3 tools/11_claim_verification/prepare_claim_verification.py runs/<run_id>
python3 tools/00_workflow_control/validate_step.py claim_verification_setup runs/<run_id>
```

Review agents read:

- `artifacts/10_claim_verification/02_work_orders/SUB###.md`

and write:

- `artifacts/10_claim_verification/03_claim_reviews/SUB###.csv`

Generic rules:

- Verify the exact claim text against only the cited papers for that claim.
- Read normalized narrative full text for cited papers when available.
- Do not use model memory, uncited papers, or adjacent review prose as evidence.
- Do not add new citations in this stage.
- Every non-supported claim must include a corrected claim.
- Every claim must include a concrete evidence summary that names the study
  context, model or population, exposure, assay or endpoint, result direction,
  and limitation when available.

Verify reviewed claims:

```bash
python3 tools/11_claim_verification/verify_claim_verification.py runs/<run_id>
python3 tools/00_workflow_control/validate_step.py claim_verification runs/<run_id>
```

Output:

- SQLite table `claim_verification_claims`
- SQLite table `claim_verification_checks`
- `artifacts/10_claim_verification/README.md`
- `artifacts/10_claim_verification/01_inputs/claim_manifest.csv`
- `artifacts/10_claim_verification/02_work_orders/SUB###.md`
- `artifacts/10_claim_verification/03_claim_reviews/SUB###.csv`
- `artifacts/10_claim_verification/04_verification/claim_verification_setup_check.csv`
- `artifacts/10_claim_verification/04_verification/claim_verification_check.csv`
- `artifacts/10_claim_verification/05_outputs/claim_verification_summary.md`

Allowed verification statuses:

- `supported`
- `partially_supported`
- `overgeneralized`
- `contradicted`
- `citation_mismatch`
- `citation_missing`
- `insufficient_evidence`
- `remove`

### 12. Corrective Section Rewrite

Apply the Stage 11 claim-verification decisions to the assembled review. This
stage is a conservative correction pass, not a global prose-polishing pass.

Preflight:

```bash
python3 tools/00_workflow_control/validate_step.py claim_verification runs/<run_id> --allow-later-steps
```

Apply corrections:

```bash
python3 tools/12_corrective_rewrite/apply_claim_corrections.py runs/<run_id>
python3 tools/00_workflow_control/validate_step.py corrective_rewrite runs/<run_id>
```

Generic rules:

- Correct only claims with a Stage 11 status other than `supported`.
- Use each reviewed claim's `corrected_claim` as the replacement text.
- Preserve paper and citation traceability.
- Do not add new papers, PMIDs, paper IDs, citation IDs, sections, or claims.
- Stop if a problematic claim cannot be found exactly once in the assembled
  review.

Output:

- SQLite table `corrective_rewrite_claims`
- SQLite table `corrective_rewrite_checks`
- `drafts/corrected_review.md`
- `artifacts/11_corrective_rewrite/README.md`
- `artifacts/11_corrective_rewrite/01_inputs/correction_manifest.csv`
- `artifacts/11_corrective_rewrite/02_outputs/corrected_review.md`
- `artifacts/11_corrective_rewrite/03_verification/corrective_rewrite_check.csv`
- `artifacts/11_corrective_rewrite/04_outputs/corrective_rewrite_summary.md`

### 13. Global Review Rewrite

Create the reader-facing final review from the corrected draft. This is the
terminal automated writing stage. It should behave like a professional review
writer: read the full draft, reduce redundancy, improve flow, preserve
mechanistic and clinical detail, keep confidence proportional to evidence, and
replace workflow paper IDs with numbered citations plus a deduplicated
reference list.

Preflight:

```bash
python3 tools/00_workflow_control/validate_step.py corrective_rewrite runs/<run_id> --allow-later-steps
```

Create and validate the final review:

```bash
python3 tools/13_final_review/finalize_review.py runs/<run_id>
python3 tools/00_workflow_control/validate_step.py final_review runs/<run_id>
```

Generic rules:

- Improve readability and professional review structure.
- Remove redundancy without deleting substantive evidence or uncertainty.
- Preserve traceability by converting workflow paper IDs into numbered
  citations and writing a deduplicated reference list.
- Do not introduce new papers, PMIDs, citation IDs, or unsupported claims.
- Keep detailed citation registers and residual uncertainty available in
  upstream artifacts, not in the final review body.

Output:

- `drafts/final_review.md`
- SQLite table `final_review_sections`
- SQLite table `final_review_checks`
- `artifacts/12_final_review/README.md`
- `artifacts/12_final_review/01_inputs/final_review_manifest.csv`
- `artifacts/12_final_review/02_outputs/final_review.md`
- `artifacts/12_final_review/02_outputs/references.csv`
- `artifacts/12_final_review/03_verification/final_review_check.csv`
- `artifacts/12_final_review/04_outputs/final_review_summary.md`

### 14. Human Scientific Inspection

The human reviewer inspects unresolved claims, citation risks, scientific
framing, and final writing quality.

## Genericity Rule

Reusable workflow files must not mention a specific disease, entity, method,
model system, lab, paper, or review topic unless used as a clearly labeled
example.

Run-specific scientific content belongs only under `runs/<run_id>/`.

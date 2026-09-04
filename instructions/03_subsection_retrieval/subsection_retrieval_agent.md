# Subsection Retrieval Agent Instruction

## Purpose

Convert `drafts/initial_review.md` into subsection-level PubMed retrieval work.

This step creates the controller plan for a loop that runs once per substantive
subsection:

1. read the subsection prose and citation register;
2. create stringent PubMed queries;
3. inspect result counts and query sensitivity;
4. revise queries when the result set is too broad, too narrow, or misses known
   draft citations;
5. send candidate abstracts to abstract reviewers;
6. decide whether the subsection literature set is sufficient;
7. identify PMC/full-text retrieval targets and user-download-needed PDFs.

This workflow step is still agent-operated and file-based. It does not require
API access. The agent may use PubMed in a browser, CLI tool, downloaded result
files, or another local agent-capable interface, but all decisions must be
recorded in the required artifacts.

When running in a coding agent, prefer the local collector:

```bash
python3 tools/03_subsection_retrieval/execute_pubmed_queries.py runs/<run_id>
```

This executes `query_plan.csv`, records real PubMed hit counts, downloads
PubMed metadata and abstracts locally, and mirrors the records into SQLite.

## Inputs

- `runs/<run_id>/original_user_prompt.md`
- `runs/<run_id>/inputs/structured_instruction.md`
- `runs/<run_id>/inputs/run_config.md`
- `runs/<run_id>/drafts/initial_review.md`
- `prompts/03_subsection_retrieval/subsection_retrieval_system.md`

## Required Outputs

- `runs/<run_id>/logs/agent_screen_log.md`
- `runs/<run_id>/artifacts/00_workflow_control/01_state/workflow_state.sqlite`
- `runs/<run_id>/artifacts/00_workflow_control/02_snapshots/workflow_state_snapshot.json`
- `runs/<run_id>/artifacts/02_subsection_retrieval/01_scope/subsection_manifest.csv`
- `runs/<run_id>/artifacts/02_subsection_retrieval/02_queries/controller_policy.md`
- `runs/<run_id>/artifacts/02_subsection_retrieval/02_queries/abstract_review_rule.md`
- `runs/<run_id>/artifacts/02_subsection_retrieval/02_queries/query_plan.csv`
- `runs/<run_id>/artifacts/02_subsection_retrieval/02_queries/query_diagnostics.csv`
- `runs/<run_id>/artifacts/02_subsection_retrieval/03_pubmed/pubmed_records.jsonl`
- `runs/<run_id>/artifacts/02_subsection_retrieval/03_pubmed/pubmed_record_index.csv`
- `runs/<run_id>/artifacts/02_subsection_retrieval/02_queries/search_iteration_log.csv`
- `runs/<run_id>/artifacts/02_subsection_retrieval/06_outputs/subsection_metrics.csv`
- `runs/<run_id>/artifacts/02_subsection_retrieval/04_screening/abstract_triage_first_pass.csv`
- `runs/<run_id>/artifacts/02_subsection_retrieval/04_screening/abstract_triage_rescue_pass.csv`
- `runs/<run_id>/artifacts/02_subsection_retrieval/05_recall/draft_citation_recall_check.csv`
- `runs/<run_id>/artifacts/02_subsection_retrieval/06_outputs/final_literature_sets.csv`
- `runs/<run_id>/artifacts/02_subsection_retrieval/06_outputs/full_text_download_queue.csv`
- `runs/<run_id>/artifacts/02_subsection_retrieval/06_outputs/subsection_retrieval_check.md`
- `runs/<run_id>/artifacts/02_subsection_retrieval/02_queries/query_execution_report.md`

## Screen Log

Append substantive screen-visible progress updates, query-controller decisions,
validation results, and final summaries to
`runs/<run_id>/logs/agent_screen_log.md`. Do not include hidden
chain-of-thought, credentials, paper full text, or large generated artifacts.

## Subsection Manifest

Parse every `### Subsection` heading from the draft. Assign stable IDs:

- `SUB001`
- `SUB002`
- `SUB003`

The manifest must preserve chapter title, subsection title, subsection order,
and the draft citation IDs found under that subsection.

Initialize durable workflow state before query planning:

```bash
python3 tools/00_workflow_control/init_workflow_state.py runs/<run_id>
```

This creates `artifacts/00_workflow_control/01_state/workflow_state.sqlite`, writes a JSON
snapshot, and populates the subsection manifest from `drafts/initial_review.md`.
The SQLite database is a resume/deduplication mirror; the CSV and Markdown files
remain the human-auditable workflow artifacts.

After query planning, an LLM query designer must read each subsection and fill
the semantic query-design fields in `query_plan.csv`. The scaffolded queries are
seeds only; do not execute PubMed until the initial query rows have
`semantic_query_design_status=llm_semantic_designed`.

After semantic query design, execute PubMed queries and persist metadata:

```bash
python3 tools/03_subsection_retrieval/execute_pubmed_queries.py runs/<run_id>
```

The collector must write every locally collected PubMed record to
`pubmed_records.jsonl`, summarize those records in `pubmed_record_index.csv`,
and mirror them into SQLite `pubmed_records`. Later abstract review should read
from these local artifacts rather than re-running PubMed searches unless the
controller asks for query revision.

If execution stages `query_redesign` rows because a query returns too many or
too few records, those rows are also semantic LLM design tasks. They must not be
executed until an LLM reads the subsection evidence need, parent query,
diagnostic count failure, and false-positive risks, then rewrites or approves
the row with `semantic_query_design_status=llm_semantic_redesigned`.

## Query Plan Rules

For every subsection, replace the scaffolded `semantic_seed` row with real
initial PubMed queries, choosing the number the subsection semantically needs.
A narrow or simple subsection may need a small number of queries; complex
subsections with multiple entities, mechanisms, models, interventions, or
citation-recall needs may need more. The query designer must read the
subsection prose and citation-register notes as an evidence need, then identify:

- the claim or evidence need being searched;
- the entity, protein/gene family, intervention, disease, model, or assay
  anchors;
- the mechanism, endpoint, causal relation, perturbation, or evidence type;
- allowed synonyms and family analogs;
- likely false positives and overbroad words to avoid.

The query plan must fill these semantic fields for every initial query:

- `semantic_evidence_need`
- `semantic_entity_terms`
- `semantic_mechanism_terms`
- `semantic_endpoint_or_context_terms`
- `query_false_positive_risks`
- `semantic_query_design_status`
- `semantic_query_designer`

Use `semantic_query_design_status=llm_semantic_designed` only after an LLM has
read the subsection and generated, rewritten, or explicitly approved the query.
For controller-created `query_redesign` rows, use
`semantic_query_design_status=llm_semantic_redesigned` only after an LLM has
semantically redesigned that row from the parent query and count-failure
diagnostics. Controller-generated redesign seeds are work orders, not
executable PubMed queries.

Each initial query for a subsection must have a distinct `query_type` intent.
Choose intents from the subsection itself. Useful intents can include
`primary_mechanism`, `clinical_context`, `citation_recall`, `model_or_assay`,
`synonym_expansion`, `family_analog`, `negative_or_failed_result`,
`combination_rationale`, `biomarker_context`, or another explicit
subsection-specific intent. Use only intents that are genuinely needed.

Use PubMed syntax where useful:

- quoted phrases for exact entities or mechanisms;
- `[Title/Abstract]` for precise concept terms;
- `[MeSH Terms]` where a stable biomedical concept exists;
- OR blocks for synonyms;
- NOT blocks only for repeated false-positive patterns;
- date filters only when justified by the user prompt or field history.

Do not derive queries from the subsection title alone or from raw ranked tokens.
The title may orient the query, but the query design must come from semantic
interpretation of subsection prose, citation-register notes, and draft citation
anchors. Queries should be scientifically stringent but not over-encoded with
exact entity names. Prefer a small number of biologically meaningful OR blocks
over long chains of exact entity AND terms when that improves recall.

## Controller Loop Rules

For each executed query, the controller must classify the query count and decide
whether that query is acceptable or needs semantic redesign. Query counts are
evaluated at query level.

- `too_many`: likely noisy; redesign query keywords by mechanism, context,
  assay, population, intervention, endpoint, or false-positive exclusion.
- `too_few`: redesign query keywords by broadening synonyms, removing
  over-specific filters, or searching family analogs when allowed by the
  structured instruction.
- `acceptable`: enough for abstract review without overwhelming the subsection.

Default count guidance for one subsection:

- `0`: too few unless the subsection is explicitly speculative.
- `1-4`: usually too narrow unless draft citations are recovered and the
  subsection is intrinsically sparse.
- `5-100`: target band for LLM semantic abstract review.
- `101-110`: near-boundary counts are acceptable when the query is semantically
  specific.
- `>110`: too many; collect at most a diagnostic sample and redesign query
  keywords before using results for abstract-review coverage.

These are controller heuristics, not scientific inclusion rules.
Diagnostic samples from overbroad queries are not retrieval coverage and must
not be the only source passed into semantic abstract review.

Query redesign is an LLM semantic task, not a sampling task and not a mechanical
keyword shuffle. When an individual query is too sparse or too broad, the
controller may stage redesign seed rows. The LLM must read the subsection and
decide which biological meaning should be tightened, broadened, substituted
with synonyms, moved into OR blocks, moved out of the query, or excluded as a
false-positive source. Validation must fail if any bad-count query lacks a
redesign path, or if `controller_status` is inconsistent with unresolved
redesign work.

Do not redesign acceptable-count queries. Once a query has an acceptable count,
freeze that row and preserve its PubMed count, diagnostics, and candidate
source contribution. Later iterations should execute only newly
LLM-redesigned rows or rows that do not yet have a recorded count.

Use `subsection_metrics.csv` `controller_status` as the durable rollup of
query-level decisions:

- `query_revision_needed`: at least one query in the subsection still has
  unresolved bad-count redesign work, or the subsection-level candidate set is
  too large.
- `abstract_review_needed`: every executed query in the subsection is acceptable
  or has a resolved redesign path, and the candidate set is reviewable.

For every query that is run or estimated, record query diagnostics: raw hit
count, collected count, whether the result was truncated, sampling strategy,
sampled on-scope and noise counts, estimated precision, dominant noise classes,
missing concepts, recall signals, decision, and revision rationale.

For every subsection, maintain `subsection_metrics.csv`. This file is the
controller dashboard. It must summarize:

- how many queries were planned and run;
- how many PubMed records were returned;
- how many papers were collected for abstract review;
- how many known draft citations were recovered;
- draft-citation recall rate;
- how many abstracts were reviewed;
- how many were included as primary, included as context, uncertain/full-text
  needed, or rejected;
- abstract rejection rate;
- rescue-pass reviewed and promoted counts;
- final subsection literature-set size;
- full-text download queue count;
- controller status and notes.

Do not hide `unknown` values. Before real PubMed execution, use `unknown` or
`not_run`; after execution, replace them with real counts.

## Abstract Review Rules

Abstract reviewers judge each candidate paper for the subsection only. They
should not decide whether the whole review is correct.

The abstract review stage is the primary precision filter. Reviewers must read
each returned title and abstract and compare it directly with the subsection
prose in a comprehensive scientific semantic way. Inclusion is based on whether
the abstract addresses the same mechanism, perturbation, causal relation,
experimental system, patient context, intervention context, or evidence role
needed by that subsection.

Classify each abstract as:

- `include_primary`: directly supports or challenges a subsection claim.
- `include_context`: useful background, trial context, assay context, or review.
- `exclude_off_scope`: not about the subsection mechanism or population.
- `exclude_wrong_level`: evidence is at the wrong biological, technical,
  clinical, methodological, or causal level for the subsection.
- `exclude_low_quality_or_blocked`: venue or article type is unacceptable.
- `uncertain_full_text_needed`: abstract is promising but insufficient.

Record the reason in one sentence. Do not overinclude papers merely because they
contain the same entity names. Do not exclude a paper merely because it lacks
the exact entity name if the abstract studies a closely analogous mechanism or
model relationship allowed by the structured instruction.

For every reviewed abstract, fill:

- `semantic_fit_score`: `0`, `1`, `2`, or `3`, where `3` is direct subsection
  evidence and `0` is off-scope.
- `mechanism_match`: `direct`, `partial`, `analogous`, `none`, or `unknown`.
- `entity_context_match`: `direct`, `partial`, `analogous`, `none`, or
  `unknown`.
- `evidence_directness`: `direct_experimental`, `direct_clinical`,
  `computational_or_indirect`, `background_review`, `not_evidence`, or
  `unknown`.
- `key_relevant_abstract_text`: short phrase or sentence fragment explaining
  what made the abstract relevant; keep it brief.
- `missing_full_text_reason`: why full text is needed, or `not_needed_for_abstract_triage`.

Use a two-pass structure:

- first pass reviews all collected candidates;
- rescue pass reviews first-pass excludes and uncertain papers only;
- first-pass includes carry forward and should not be relitigated unless a
  hard-block or metadata error is discovered.

## Draft Citation Recall

For each subsection, check whether every non-`citation_needed` citation in the
draft citation register appears in the final candidate set.

If a draft citation is missing, the controller must decide:

- `recover_with_targeted_query`
- `drop_as_unverified_or_wrong`
- `defer_to_full_text_step`

This protects against accidentally losing the draft's useful anchors while also
allowing hallucinated or off-scope citations to be discarded.

## Literature Set Finalization

The controller may finalize a subsection literature set only when:

- at least one acceptable query iteration is logged, or the subsection is
  explicitly marked as needing manual search;
- included papers have abstract-review decisions;
- known draft citations are recalled, resolved, or explicitly rejected;
- PMC/full-text availability is recorded when known;
- papers needing user-provided PDFs are added to the download queue.

## Validation

Run:

```bash
python3 tools/00_workflow_control/validate_step.py subsection_retrieval runs/<run_id>
```

Do not report this step as complete unless validation passes.

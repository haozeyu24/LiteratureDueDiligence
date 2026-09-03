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

After query planning, execute PubMed queries and persist metadata:

```bash
python3 tools/03_subsection_retrieval/execute_pubmed_queries.py runs/<run_id>
```

The collector must write every locally collected PubMed record to
`pubmed_records.jsonl`, summarize those records in `pubmed_record_index.csv`,
and mirror them into SQLite `pubmed_records`. Later abstract review should read
from these local artifacts rather than re-running PubMed searches unless the
controller asks for query revision.

## Query Plan Rules

For every subsection, create at least four initial PubMed queries:

- `high_precision`: biologically constrained query derived primarily from
  subsection prose and citation-register notes
- `mechanism_expansion`: less entity-encoded expansion around the mechanism,
  perturbation, assay, or causal relationship discussed in the subsection
- `context_expansion`: less entity-encoded expansion around model, patient,
  disease, treatment, assay, comparator context, or analogous system discussed
  in the subsection
- `recall_guard`: query designed to recover known draft citations and close
  obvious synonym gaps

Use PubMed syntax where useful:

- quoted phrases for exact entities or mechanisms;
- `[Title/Abstract]` for precise concept terms;
- `[MeSH Terms]` where a stable biomedical concept exists;
- OR blocks for synonyms;
- NOT blocks only for repeated false-positive patterns;
- date filters only when justified by the user prompt or field history.

Do not derive queries from the subsection title alone. The title may orient the
query, but the query terms should come mainly from subsection prose,
citation-register notes, and draft citation anchors. Queries should be
scientifically stringent but not over-encoded with exact entity names. Prefer a
small number of biologically meaningful OR blocks over long chains of exact
entity AND terms when that improves recall.

## Controller Loop Rules

For each subsection, the controller must classify the result count:

- `too_many`: likely noisy; refine by mechanism, context, assay, population, or
  intervention.
- `too_few`: broaden synonyms, remove over-specific filters, or search family
  analogs when allowed by the structured instruction.
- `acceptable`: enough for abstract review without overwhelming the subsection.
- `needs_manual_search`: PubMed syntax or field terminology is failing.

Default count guidance for one subsection:

- `0`: too few unless the subsection is explicitly speculative.
- `1-5`: usually too narrow unless draft citations are recovered and the
  subsection is intrinsically sparse.
- `6-200`: generally acceptable for LLM semantic abstract review.
- `201-500`: collect a labeled top-relevance sample, then refine only if
  sampled abstracts show low semantic fit.
- `>500`: usually too many for one subsection; refine before finalization unless
  the subsection is intentionally broad.

These are controller heuristics, not scientific inclusion rules.

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
- `keep_for_manual_lookup`
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

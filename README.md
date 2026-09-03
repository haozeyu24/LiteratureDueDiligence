# Literature Due Diligence

A local, agent-run workflow for biomedical and drug-discovery literature
reviews.

The workflow starts with a broad frontier-model draft, then treats that draft as
a map of claims to verify. Later stages retrieve PubMed literature, review
abstracts semantically, ingest primary full text, build a RAG index, and perform
evidence-grounded subsection rewriting from paper packets and narrative full
text.

This repository is designed for Codex, Claude Code, or similar local agentic
coding environments. It does not require an end-to-end app or custom hosted
service. Agents operate by reading instructions, writing structured files, and
passing validation gates.

## Design Choices And Tradeoffs

- Draft-first workflow: the system starts from an LLM-generated review and then
  expands, checks, and corrects it. This is pragmatic, but it can under-surface
  evidence that contradicts the draft's original framing. Human review should
  weight this confirmation-bias risk higher for novel, controversial, or weakly
  established mechanisms.
- Correlated model bias: drafting, query construction, rewriting, and
  verification may be done by the same model or model family, so the verifier
  may share the generator's blind spots. This workflow deliberately avoids
  dual-model arbitration to reduce complexity. A stronger audit can rerun the
  same prompt in independent systems, such as Codex and Claude Code, then compare
  both reviews and verification decisions.
- Rigor versus operating cost: the workflow has many stages, many subsection-
  level agent calls, full-text parsing, embeddings, and manual PDF handling.
  That buys a more grounded review, but costs time, tokens, API spend, and more
  validation surface. Token and embedding costs are trending cheaper, yet each
  production run should still track approximate runtime, cost, and failure
  points before being used for time-sensitive diligence.

## Current Stages

| Stage | Name | Status | Main Output |
| --- | --- | --- | --- |
| 1 | Prompt intake | implemented | structured run instruction and config |
| 2 | Initial review draft | implemented | citation-heavy draft with subsection registers |
| 3 | Subsection PubMed retrieval | implemented | subsection queries, PubMed metadata, recall metrics |
| 4 | Semantic abstract review | implemented | primary/context/excluded decisions per subsection |
| 5 | Primary full-text ingestion | implemented | narrative-core PMC/PDF text, chunks, QC report |
| 6 | Full-text RAG index | implemented | chunks, BM25 index, Qdrant vector index, hybrid config |
| 7 | Subsection RAG retrieval | implemented | paper-level evidence packets per subsection |
| 8 | Evidence-grounded subsection rewrite | implemented | full-text-informed paper triage and checked rewritten subsections |
| 9 | Terminology normalization | implemented | entity glossary and normalized subsection copies |
| 10 | Review assembly | implemented | assembled review draft preserving registers |
| 11 | Claim-level verification | implemented | claim work orders and reviewed claim decisions |
| 12 | Corrective section rewrite | implemented | corrected review draft from verified claim decisions |
| 13 | Final review writer pass | implemented | reader-facing final review with deduplicated references |

Planned next work: human scientific inspection outside the automated workflow.

## Quick Start

Create or choose a run folder under `runs/`, then follow the stage instruction
files in order:

```text
instructions/01_prompt_intake/create_prompt_intake_run.md
instructions/01_prompt_intake/prompt_intake_agent.md
instructions/02_initial_review_draft/initial_review_draft_agent.md
instructions/03_subsection_retrieval/subsection_retrieval_agent.md
instructions/04_semantic_abstract_review/semantic_abstract_review_agent.md
instructions/05_primary_full_text_ingestion/primary_full_text_ingestion_agent.md
instructions/06_full_text_rag_index/full_text_rag_index_agent.md
instructions/07_subsection_rag_retrieval/subsection_rag_retrieval_agent.md
instructions/08_subsection_rewrite/subsection_rewrite_agent.md
instructions/09_terminology_normalization/terminology_normalization_agent.md
instructions/10_review_assembly/review_assembly_agent.md
instructions/11_claim_verification/claim_verification_agent.md
instructions/12_corrective_rewrite/corrective_rewrite_agent.md
instructions/13_final_review/final_review_writer_agent.md
```

The high-level workflow spec is [workflow.md](workflow.md). Shared literature
policy lives in [policy.md](policy.md).

## API Key

Most stages are file-based and do not need an API key. Stage 6 requires an
OpenAI API key because it builds embeddings with `text-embedding-3-small`.

Create a local `.env` file at the repository root:

```bash
cp .env.example .env
```

Then edit `.env`:

```text
OPENAI_API_KEY=sk-your-key-here
```

The real `.env` file is ignored by git. Do not commit it. If `OPENAI_API_KEY`
is missing, Stage 6 must stop and ask the user to provide one.

Cost should be modest for normal review-scale corpora. As of 2026-09-03,
`text-embedding-3-small` is listed at `$0.02 per 1M input tokens`. A rough
rule of thumb is `characters / 4 = tokens`; a 100-paper run is likely around
`$0.02-$0.05` unless papers are unusually long or repeatedly re-embedded.

## Validation

Every stage must pass validation before the next stage starts:

```bash
python3 tools/00_workflow_control/validate_step.py <step_name> runs/<run_id>
```

Implemented step names:

```text
prompt_intake
initial_review_draft
subsection_retrieval
semantic_abstract_review_preflight
semantic_abstract_review_setup
semantic_abstract_review_pilot
semantic_abstract_review_complete
primary_full_text_ingestion
full_text_rag_index
subsection_rag_retrieval
subsection_rewrite_setup
subsection_rewrite
terminology_normalization
review_assembly
claim_verification_setup
claim_verification
corrective_rewrite
final_review
```

For auditing an already advanced run, allow declared later-stage artifacts:

```bash
python3 tools/00_workflow_control/validate_step.py <step_name> runs/<run_id> --allow-later-steps
```

Use `--allow-extra` only for debugging; do not use it to mark a production
stage complete.

## Run Logs

Each run keeps a screen-visible log:

```text
runs/<run_id>/logs/agent_screen_log.md
```

Agents should append substantive progress updates, decisions, validation
results, handoff notes, and final summaries. A helper is provided:

```bash
python3 tools/00_workflow_control/append_agent_log.py runs/<run_id> --agent <step_name> --message "..."
```

Do not store paper full text, private credentials, or hidden reasoning in this
log.

## Repository Layout

```text
.
├── README.md
├── workflow.md
├── policy.md
├── instructions/       # numbered stage agent instructions
│   ├── 00_workflow_control/
│   ├── 01_prompt_intake/
│   └── ...
├── prompts/            # numbered stage system prompts
│   ├── 01_prompt_intake/
│   ├── 02_initial_review_draft/
│   └── ...
├── resources/
├── templates/
├── tools/              # numbered stage helper scripts
│   ├── 00_workflow_control/
│   ├── 03_subsection_retrieval/
│   └── ...
├── validation/
└── runs/              # local, ignored by git
```

Only reusable workflow files, prompts, templates, resources, validation
contracts, and tools should be committed. Topic-specific scientific content
belongs under `runs/<run_id>/`.

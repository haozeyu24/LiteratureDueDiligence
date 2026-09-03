# Subsection Rewrite Agent Instruction

## Purpose

Rewrite draft subsections from Stage 7 paper-level evidence packets. This stage
turns retrieval into evidence-grounded prose, but it is not the final
claim-level verification stage.

## Preconditions

Run only after Stage 7 subsection RAG retrieval is complete and validation has
passed:

```bash
python3 tools/00_workflow_control/validate_step.py subsection_rag_retrieval runs/<run_id>
```

Prepare work orders:

```bash
python3 tools/08_subsection_rewrite/prepare_subsection_rewrite.py runs/<run_id>
```

## Writing Workflow

For each file in:

```text
artifacts/07_subsection_rewrite/02_work_orders/
```

write the corresponding rewritten subsection to:

```text
artifacts/07_subsection_rewrite/03_rewritten_subsections/SUB###.md
```

Use the work order as the source of truth. It contains the original draft
subsection, the Stage 7 paper packet, and normalized narrative full-text paths
when available. Preserve useful framing from the draft, but correct claims when
the packet evidence is weaker, different, contradictory, or absent. Use chunk
excerpts as navigation aids; for papers that matter to the subsection, read the
relevant normalized narrative text before writing.

This is a substantive biomedical review-writing stage. The output should add
evidence detail, not just conclusions. Include the study context, model or
patient setting, perturbation/exposure, assay or endpoint, direction of effect,
and limitations when those details are relevant.

## Required Rewritten File Shape

```markdown
# Rewritten Subsection: SUB###

## Paper Triage

| paper_id | PMID | selection_reason | normalized_path | full_text_read_status | triage_role | support_status | key_evidence | use_in_rewrite |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Rewritten Text

<evidence-grounded prose with inline citations; minimum 250 words>

## Citation Register

| citation_id | paper_id | PMID | DOI | evidence_use | support_status | cited_claim | study_context | model_or_population | perturbation_or_exposure | assay_or_endpoint | direction_or_result | limitation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Evidence Use Notes

<brief notes on how packet papers changed the draft>

## Residual Uncertainty

<remaining uncertainty, missing evidence, or human-inspection notes>
```

## Citation Rules

- Triage every selected paper in the Stage 7 packet before writing prose.
- In `full_text_read_status`, use `read_relevant_narrative`,
  `no_normalized_full_text`, or `not_read_not_used`. Any cited paper with a
  normalized path must be marked `read_relevant_narrative`.
- Use `triage_role` values: `core_support`, `partial_support`,
  `context_only`, `boundary_or_negative`, or `not_used`.
- Use `support_status` values: `supports`, `partially_supports`,
  `context_only`, `contradicts`, or `insufficient_evidence`.
- Do not cite a paper unless its `paper_id` is listed in the Stage 7 packet and
  also appears in the `## Paper Triage` table.
- Do not introduce new citations in this stage. Missing papers should be noted
  under `## Residual Uncertainty` for later human or agent follow-up.
- Do not infer support from retrieval rank alone. The paper packet is a
  retrieval aid, not a truth judgment.
- If fewer than two packet papers provide `core_support` or `partial_support`,
  write the subsection as weak, emerging, speculative, or unresolved rather
  than established.
- Write at least 250 words of substantive review prose and at least 1.5x the
  original subsection length unless the evidence packet is genuinely empty or
  unusable.
- Put inline citations in the rewritten prose using backticked packet paper IDs,
  for example `pmid-12345678`. Every inline citation must appear in the
  citation register, and every register row must be cited inline.
- Do not put unescaped pipe characters in Markdown table cells; use semicolons
  or commas inside evidence notes.

## Parallelization

This stage is designed for subagents. Assign disjoint work orders to separate
agents, for example one agent per subsection or one agent per small block of
subsections. Each agent must write only its assigned files under
`artifacts/07_subsection_rewrite/03_rewritten_subsections/` and must not edit
shared manifests, verification files, previous-stage artifacts, or final review
files.

## Verification

After rewritten subsection files are written, run:

```bash
python3 tools/08_subsection_rewrite/verify_subsection_rewrite.py runs/<run_id>
python3 tools/00_workflow_control/validate_step.py subsection_rewrite runs/<run_id>
```

Do not proceed to claim-level verification until both commands pass.

## Boundaries

Do not write the final assembled review or claim-level verification table in
this stage. Those belong to later workflow stages.

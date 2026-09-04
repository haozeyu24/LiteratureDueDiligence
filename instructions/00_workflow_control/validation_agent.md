# Validation Agent Instruction

## Purpose

Validate that a workflow step produced the required files, populated them, and
did not create side artifacts outside the declared workflow contract.

This guard exists to prevent premature stopping and uncontrolled agent output.

## Run Screen Log

Every run must contain `logs/agent_screen_log.md`. Agents should append the
substantive words they show on screen, including progress updates, decisions,
validation outcomes, handoff notes, and final summaries.

Treat this as a troubleshooting transcript of visible agent behavior. If the
agent tells the user about a tooling bug, compatibility issue, validation
failure, repair, workaround, subagent assignment, skipped step, or pause, the
same substantive statement must be written to the screen log. Do not wait until
the end of a stage to summarize surprises that were visible earlier.

Use the helper when convenient:

```bash
python3 tools/00_workflow_control/append_agent_log.py runs/<run_id> --agent <step_name> --message "..."
```

Do not log hidden chain-of-thought, credentials, paper full text, or large
generated artifacts. The log is an audit trail of visible agent output, not the
scientific evidence database.

`validate_step.py` appends pass/fail validation outcomes automatically, but
agents remain responsible for logging non-validation visible updates and
decisions as they happen.

## Required Behavior

After every workflow step, run:

```bash
python3 tools/00_workflow_control/validate_step.py <step_name> runs/<run_id>
```

The step is not complete unless the validator exits with code `0`.
When auditing an already advanced run rather than gating the current step, use:

```bash
python3 tools/00_workflow_control/validate_step.py <step_name> runs/<run_id> --allow-later-steps
```

## Current Step Names

- `prompt_intake`
- `initial_review_draft`
- `subsection_retrieval`
- `semantic_abstract_review_preflight`
- `semantic_abstract_review_setup`
- `semantic_abstract_review_pilot`
- `semantic_abstract_review_complete`
- `primary_full_text_ingestion`
- `full_text_rag_index`

## What Validation Checks

- required files exist
- required files are populated above a minimum size
- required section markers are present
- `logs/agent_screen_log.md` exists and is populated
- unexpected files are rejected
- files from future steps are rejected
- artifact stage folders keep files inside numbered subfolders, with only
  `README.md` allowed at stage-folder roots
- topic-specific content stays under `runs/<run_id>/`
- Stage 5 either normalizes primary full text or records a deliberate manual
  PDF pause before downstream work can continue

## Failure Policy

If validation fails:

1. Read the error messages.
2. Fix only the missing, incomplete, or unexpected artifacts for the current
   step.
3. Rerun validation.
4. Do not proceed to the next workflow step until validation passes.

## Side Artifact Policy

Agents must not create extra summaries, draft reviews, search results, paper
lists, PDFs, scripts, or exports during a step unless the workflow contract
declares them for that step or the user explicitly asks for them.

For this reason, validation should fail closed by default. Use `--allow-extra`
only for debugging, never to mark a production workflow step complete.
Use `--allow-later-steps` only for completed-run audits; do not use it to pass a
current step before downstream work exists.

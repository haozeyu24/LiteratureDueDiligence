# Create A Prompt-Intake Run

Use this instruction when starting a new literature due diligence run from a
user's scientific review prompt.

## Inputs Needed

- `run_id`: a short filesystem-safe identifier for the run.
- `user_prompt`: the user's original scientific review request.

If the user did not provide a run ID, create one from the topic plus date, using
lowercase words separated by underscores. Keep it short and generic.

## Directory Structure

Create:

```text
runs/<run_id>/
  original_user_prompt.md
  logs/
    agent_screen_log.md
  inputs/
    structured_instruction.md
    run_config.md
    intake_self_check.md
```

## File Creation Steps

1. Create `runs/<run_id>/original_user_prompt.md`.
2. Copy the user's original prompt exactly into that file.
3. Create `logs/agent_screen_log.md` with `# Agent Screen Log` and append
   substantive screen-visible progress updates, decisions, validation outcomes,
   and final summaries as the run proceeds.
4. Read `prompts/01_prompt_intake/prompt_intake_system.md`.
5. Use that system prompt to produce `inputs/structured_instruction.md`.
6. Use `templates/run/run_config_template.md` as the base for
   `inputs/run_config.md`, changing only values justified by the user prompt.
7. Produce `inputs/intake_self_check.md` from the self-check structure.

## Do Not

- Do not call external APIs.
- Do not perform literature search.
- Do not generate the initial review yet.
- Do not create paper lists.
- Do not invent citations.
- Do not put topic-specific content outside `runs/<run_id>/`.

## Done Means

Prompt intake is done when the four required files exist and the self-check
states whether the next step should be:

- proceed to initial review drafting
- ask the user for clarification
- run a very small diagnostic scoping pass

Then run:

```bash
python3 tools/00_workflow_control/validate_step.py prompt_intake runs/<run_id>
```

Do not report prompt intake as complete unless validation passes.

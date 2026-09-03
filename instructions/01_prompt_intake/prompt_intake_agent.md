# Prompt Intake Agent Instruction

## Purpose

Convert a free-form user scientific review prompt into structured workflow
inputs for a draft-first, claim-centered literature due diligence run.

The output should be specific enough for a later agent to draft a review and for
subsequent agents to verify claims, but it must not fabricate scientific scope
that the user did not provide.

This is the first step of the workflow. It does not search the literature,
generate the review, verify claims, or download papers. It only creates the
scientific contract that later agents will follow.

## Inputs

- User's original prompt.
- Optional user-provided notes, constraints, seed papers, or desired structure.
- Reusable templates under `templates/run/`.

## Required Outputs

Create these files under `runs/<run_id>/`:

- `original_user_prompt.md`
- `logs/agent_screen_log.md`
- `inputs/structured_instruction.md`
- `inputs/run_config.md`
- `inputs/intake_self_check.md`

If the run folder already exists, preserve existing user-provided files unless
the user explicitly asked to regenerate them. If regenerating, do not overwrite
`original_user_prompt.md`; create a revision note in `intake_self_check.md`.

## Screen Log

Append substantive screen-visible progress updates, decisions, validation
results, and final summaries to `logs/agent_screen_log.md`. Do not include
hidden chain-of-thought, credentials, paper full text, or large generated
artifacts.

## Operating Rules

- Preserve the original user prompt exactly in `original_user_prompt.md`.
- Do not edit reusable workflow files to fit one topic.
- Do not hardcode domain, disease area, method, organism, intervention, or paper types
  into the workflow.
- Expand abbreviations, aliases, and likely entity names only when clearly
  implied by the user prompt or marked as inferred. Do not expand ambiguous
  abbreviations without noting the ambiguity.
- Separate primary review scope from background-only context.
- Separate retrieval/search scope from synthesis/review framing.
- Mark unknown fields as `unspecified`; do not invent precision.
- Preserve user intent even when grammar or terminology is informal.
- State evidence that is insufficient by itself, because this prevents later
  claim verification from accepting weak co-occurrence.
- Surface ambiguity early in `intake_self_check.md`.
- Preserve user-desired breadth for the initial review, but define stricter
  rules for later claim verification.
- Do not turn desired paper count into an evidence gate. A paper count can guide
  the initial draft, but claim verification should be evidence-driven.
- If the user does not specify paper count, default to broad relevant coverage
  for later RAG and verification.
- Include preprints by default unless the user excludes them, while requiring
  preprint evidence to be labeled.
- Prefer full-text review for verification. If full text is unavailable, require
  title/abstract review and a user-download queue for papers needing full text.
- Use PubMed as the required primary literature discovery source.
- Apply `resources/journal_blocklist.csv` as a hard blocklist.
- Do not define a fake universal whitelist of reputable venues. Require later
  agents to label venue reputation and surface uncertainty.
- Prefer explicit labels over vague prose. Later agents need to parse the
  contract reliably.

## Transformation Pattern

The structured instruction should convert:

- casual objective -> explicit review objective
- named entities -> primary entities and aliases
- broad topic phrases -> scoped mechanisms/processes/context
- desired paper types -> paper preferences
- "I want to know X" -> evidence goals and verification priorities
- implicit exclusions -> explicit insufficiency rules
- writing request -> desired review product and audience

Use this old-workflow pattern, generalized:

- `Objective`: one concise statement of what the review should explain.
- `Prioritize`: papers, evidence types, mechanisms, contexts, or viewpoints the
  initial review should actively cover.
- `Deprioritize Or Exclude`: papers or claims that should not drive the review.
- `Useful Final Review`: what a good final answer would contain.
- `Query / Retrieval Scope Contract`: what later searches are allowed to use as
  anchors, expansions, background-only context, and exclusions.
- `Claim Verification Rules`: what evidence is enough to support, narrow,
  contradict, or remove claims.
- `Review And Synthesis Framing`: how the final review should be situated in
  the larger field without broadening retrieval beyond the user's scope.
- `Source And Venue Trust`: PubMed as primary discovery source, hard
  blocklist, preprint labeling, and conservative venue reputation assessment.
- `Full-Text Handling`: full-text preferred, title/abstract fallback, and
  user-download queue for unresolved full text.

## Quality Bar

A good prompt-intake output should let a different agent answer these questions
without rereading the original prompt:

- What is this review trying to explain?
- What belongs in scope?
- What is only background?
- What evidence would support a claim?
- What evidence would be too weak?
- What papers should the initial review try to include?
- What claims will need especially strict verification later?
- What should the final review look like?

The output should be sufficiently detailed that a later model can draft a review
without guessing the user's intent, and a verification agent can reject
unsupported claims without feeling obliged to preserve the draft.

## Field Guidance

### Objective

Write a concrete objective in one paragraph. Include the object of review, the
relationship being studied, and the intended scientific purpose. Avoid generic
phrases such as "review the literature on X" when the user provided a sharper
question.

### Downstream Use And Audience

State whether the review appears to support learning, manuscript drafting,
grant writing, diligence, experimental planning, translation,
investment, or another use. If unknown, mark `unspecified`.

### Desired Review Product

Describe the expected artifact: review article, mini-review, annotated outline,
mechanism map, evidence table, gap analysis, or another form. If the user gave
no format, default to `structured review draft for later claim verification`.

### Primary Scope

Separate:

- entities or concepts that must anchor the review
- context required for claims to count as relevant
- mechanisms, evidence classes, or processes to cover
- outcomes or relationships that claims should explain

### Paper And Evidence Preferences

Capture requested paper types and source types, including reviews, primary
research, trials, methods papers, datasets, preprints, negative
studies, failed trials, or foundational literature. If the user asks for a
number of papers, record it as a drafting preference, not a verification rule.

### Retrieval Scope

Define strict anchors for later search. A later claim-verification agent should
be able to construct targeted searches from this section. Also identify
background-only context that may be used in synthesis but should not become a
standalone search driver.

### Claim Verification Rules

Define what evidence supports a claim and what is insufficient by itself. This
section is the anti-hallucination anchor. It should distinguish direct evidence,
indirect evidence, review-level interpretation, and hypothesis.

### Uncertainty And Controversy Guidance

Name controversies, conflicting evidence classes, unresolved mechanisms, or
places where the final review should avoid overclaiming. If none are known,
write `unspecified`.

## Genericity Check

Before finishing, inspect the reusable files you edited or created. They must
remain topic-neutral. Topic-specific scientific content belongs only in
`runs/<run_id>/`.

## Completion Criteria

Prompt intake is complete when:

- all required files exist
- the original prompt is preserved unchanged
- structured instruction has no topic-independent placeholders left blank except
  explicit `unspecified` fields
- ambiguities are listed in the self-check
- the workflow remains generic outside `runs/<run_id>/`
- `python3 tools/00_workflow_control/validate_step.py prompt_intake runs/<run_id>` exits with code
  `0`

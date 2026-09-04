# Initial Review Draft Agent Instruction

## Purpose

Create the first review draft from `inputs/structured_instruction.md`.

This draft is not the final review. It is a verification-ready scaffold for
later claim extraction, targeted PubMed retrieval, RAG, full-text review, and
human inspection.

## Inputs

- `runs/<run_id>/original_user_prompt.md`
- `runs/<run_id>/inputs/structured_instruction.md`
- `runs/<run_id>/inputs/run_config.md`
- `runs/<run_id>/inputs/intake_self_check.md`
- `prompts/02_initial_review_draft/initial_review_draft_system.md`

## Required Outputs

- `runs/<run_id>/drafts/initial_review.md`
- `runs/<run_id>/logs/agent_screen_log.md`
- `runs/<run_id>/artifacts/01_draft_validation/README.md`
- `runs/<run_id>/artifacts/01_draft_validation/01_checks/draft_instruction_check.md`

## Screen Log

Append substantive screen-visible progress updates, decisions, validation
results, and final summaries to `runs/<run_id>/logs/agent_screen_log.md`. Do
not include hidden chain-of-thought, credentials, paper full text, or large
generated artifacts.

## Draft Requirements

The draft must be organized into chapters and subsections.

The draft should be expansive. Unless `run_config.md` says otherwise, aim for:

- at least 6 chapters
- enough substantive subsections to separately cover the major entities,
  mechanisms, evidence classes, and clinical contexts in the structured
  instruction
- for broad prompts without a user-specified paper count, roughly 2-4
  substantive subsections per chapter, with at least 2 substantive subsections
  per chapter
- at least 150 words of prose per substantive subsection
- at least 2 prose paragraphs per substantive subsection
- at least 4 citation-register rows per substantive subsection

The goal is not a skeletal outline. The goal is a broad, readable topic map with
enough developed prose, citation candidates, and citation-needed targets for
downstream PubMed retrieval, RAG, and claim verification.

Each substantive subsection should develop:

- what the topic, mechanism, evidence area, or trial context is
- why it matters for the review
- what the draft-level evidence appears to suggest
- what later agents must verify
- where full text may be needed

Every substantive subsection must end with:

```markdown
#### Citation Register

| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |
|---|---|---|---|---|---|---|---|---|
```

Use local citation IDs that are stable within the draft:

- `S01-C001`
- `S01-C002`
- `S02-C001`

Allowed `draft_access_status` values:

- `full_text_likely_available`
- `abstract_only_likely`
- `title_only_likely`
- `access_unknown`
- `full_text_needed_for_verification`

Allowed `venue_trust_label` values:

- `reputable_or_likely_reputable`
- `uncertain`
- `preprint_server`
- `hard_blocked`
- `unknown`

Allowed `discovery_provenance` values:

- `searched_pubmed`
- `searched_full_text`
- `local_prior_run`
- `llm_memory`
- `citation_needed`
- `unknown`

Allowed `evidence_role` examples:

- `primary_mechanism`
- `clinical_or_translational`
- `trial_or_intervention`
- `review_or_background`
- `negative_or_failed_result`
- `hypothesis_or_emerging`
- `citation_needed`

If the drafting agent cannot confidently identify enough real citations for a
subsection, it must add `citation needed` rows. These rows should not invent
metadata; they should describe what later agents need to search for.

## Citation Rules

- Do not invent PMIDs, DOIs, titles, authors, trials, or publication metadata.
- Do not blur searched literature and LLM memory. A citation recalled from
  memory must be labeled `llm_memory` unless the agent explicitly searched and
  confirmed it during the current run.
- Use `unknown` when metadata is uncertain.
- Use `citation needed` when the draft needs support but no reliable citation is
  available to the drafting agent.
- Keep preprints clearly labeled.
- Do not use hard-blocked papers as support for settled claims.
- Treat venue and access labels as draft labels only. Later agents must verify
  them.
- Make it explicit that `draft_access_status` is provisional, not verified full
  text availability.

## Content Rules

- Follow the structured instruction.
- Do not broaden the review beyond the prompt-intake scope.
- Separate established evidence from hypotheses.
- Separate direct evidence from indirect or background evidence.
- Preserve uncertainties and controversies instead of smoothing them over.
- Include negative, failed, or conflicting evidence when requested or relevant.

## Draft Verification

After writing `drafts/initial_review.md`, read
`prompts/02_initial_review_draft/initial_review_draft_verification_system.md` and create
`artifacts/01_draft_validation/README.md` plus
`artifacts/01_draft_validation/01_checks/draft_instruction_check.md`.

The check must state whether the draft:

- follows the structured instruction
- includes citation registers under substantive subsections
- contains enough chapters, subsections, and citation-register rows to support
  later RAG and verification
- uses allowed access-status labels
- uses allowed venue-trust labels
- marks uncertain citations instead of fabricating metadata
- labels citation discovery provenance so downstream agents know what was
  searched and what was recalled from memory
- avoids out-of-scope sources unless explicitly requested
- is ready for claim extraction

## Validation

Run:

```bash
python3 tools/00_workflow_control/validate_step.py initial_review_draft runs/<run_id>
```

Do not report the drafting step as complete unless validation passes.

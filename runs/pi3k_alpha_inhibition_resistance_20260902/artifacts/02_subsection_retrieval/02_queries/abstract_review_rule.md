# Abstract Review Rule

## Purpose

Abstract reviewers decide whether candidate papers belong in one specific
subsection-level literature set. They must judge against the subsection scope,
not against the whole review topic.

## Allowed Decisions

- `include_primary`
- `include_context`
- `exclude_off_scope`
- `exclude_wrong_level`
- `exclude_low_quality_or_blocked`
- `uncertain_full_text_needed`

## Required Reason

Each decision must include a one-sentence reason tied to the subsection scope.
The reviewer must compare the abstract directly with the subsection prose:
mechanism match, entity/context match, evidence directness, and whether the
abstract supports a smaller scientific claim inside the subsection.

## Two-Pass Rule

First-pass includes carry forward. The rescue pass reviews first-pass excludes
and uncertain papers to catch overly narrow early triage, recover draft anchors,
and preserve plausible decision-relevant evidence before full-text routing.
Keyword overlap alone is not enough for inclusion, but absence of an exact
entity name is not enough for exclusion when the abstract tests the same
mechanism, assay logic, resistance class, or model relationship.

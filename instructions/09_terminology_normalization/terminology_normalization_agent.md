# Terminology Normalization Agent Instruction

## Purpose

Normalize entity aliases after subsection rewriting and before review assembly.
This stage prevents terms such as a drug name, development code, protein alias,
assay name, trial acronym, disease subtype, or institution name from appearing
in inconsistent ways across independently rewritten subsections.

## Preconditions

Run only after Stage 8 subsection rewrite is complete and validation has passed:

```bash
python3 tools/00_workflow_control/validate_step.py subsection_rewrite runs/<run_id>
```

## Generic Rule

Use a preferred name consistently in downstream prose. Preserve aliases only
when they are useful at first mention, historically important, or needed to
interpret a cited paper. Do not normalize inside citation IDs, PMIDs, DOIs,
URLs, file paths, or quoted identifiers.

## Alias Override Input

If the run has known aliases, create:

```text
runs/<run_id>/inputs/terminology_alias_overrides.csv
```

Required header:

```csv
preferred_name,entity_type,aliases,first_mention_rule,notes
```

Use semicolons inside the `aliases` cell:

```csv
preferred_name,entity_type,aliases,first_mention_rule,notes
preferred name,drug,alias one; alias two,Use preferred name in prose and clarify aliases at first relevant mention.,Run-specific example.
```

## Run

```bash
python3 tools/09_terminology_normalization/normalize_terminology.py runs/<run_id>
python3 tools/00_workflow_control/validate_step.py terminology_normalization runs/<run_id>
```

## Outputs

```text
artifacts/08_terminology_normalization/02_glossary/terminology_glossary.csv
artifacts/08_terminology_normalization/03_normalized_subsections/SUB###.md
artifacts/08_terminology_normalization/04_verification/terminology_normalization_check.csv
artifacts/08_terminology_normalization/05_outputs/terminology_normalization_summary.md
```

## Boundaries

Do not assemble the final review in this stage. Do not add new scientific
claims. Do not change citation support labels. Do not delete uncertainty
language.

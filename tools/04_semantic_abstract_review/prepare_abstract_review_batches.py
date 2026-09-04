#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_workflow_control"))

from init_workflow_state import parse_draft


SUBSECTION_DIR = Path("artifacts/02_subsection_retrieval")
SCREENING_DIR = SUBSECTION_DIR / "04_screening"
OUTPUT_DIR = SUBSECTION_DIR / "06_outputs"
REVIEW_DIR = Path("artifacts/03_semantic_abstract_review")
SETUP_DIR = REVIEW_DIR / "01_setup"
CONTEXT_DIR = REVIEW_DIR / "02_context"
BATCH_DIR = REVIEW_DIR / "03_batches"
REVIEWED_DIR = REVIEW_DIR / "04_reviewed_batches"
SEMANTIC_OUTPUT_DIR = REVIEW_DIR / "05_outputs"
SEMANTIC_FIELDS = [
    "semantic_fit_score",
    "mechanism_match",
    "entity_context_match",
    "evidence_directness",
    "key_relevant_abstract_text",
    "missing_full_text_reason",
    "reviewer_id",
    "review_method",
    "reviewer_model_or_agent",
    "reviewed_at",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare subsection-batched files for LLM semantic abstract review."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=80,
        help="Maximum subsection-paper rows per review batch.",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if args.batch_size <= 0:
        print("ERROR: --batch-size must be positive", file=sys.stderr)
        return 1
    errors = preflight_errors(run_dir)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    draft_path = run_dir / "drafts/initial_review.md"
    final_set_path = run_dir / OUTPUT_DIR / "final_literature_sets.csv"
    first_pass_path = run_dir / SCREENING_DIR / "abstract_triage_first_pass.csv"
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    review_dir = run_dir / REVIEW_DIR
    setup_dir = run_dir / SETUP_DIR
    batch_dir = run_dir / BATCH_DIR
    context_dir = run_dir / CONTEXT_DIR
    reviewed_dir = run_dir / REVIEWED_DIR
    output_dir = run_dir / SEMANTIC_OUTPUT_DIR
    for directory in (review_dir, setup_dir, batch_dir, context_dir, reviewed_dir, output_dir):
        directory.mkdir(parents=True, exist_ok=True)

    subsections = parse_draft(draft_path)
    final_rows = read_csv(final_set_path)
    rows_by_subsection = sqlite_candidate_rows_by_subsection(sqlite_path, final_rows)

    batch_rows: list[dict[str, str]] = []
    for subsection in subsections:
        subsection_id = str(subsection["subsection_id"])
        context_path = context_dir / f"{subsection_id}.md"
        write_subsection_context(context_path, subsection)
        subsection_rows = rows_by_subsection.get(subsection_id, [])
        for batch_index, batch in enumerate(chunks(subsection_rows, args.batch_size), start=1):
            batch_id = f"{subsection_id}-B{batch_index:03d}"
            batch_path = batch_dir / f"{batch_id}.csv"
            write_batch_csv(batch_path, batch)
            batch_rows.append(
                {
                    "batch_id": batch_id,
                    "subsection_id": subsection_id,
                    "batch_index": str(batch_index),
                    "candidate_count": str(len(batch)),
                    "context_path": context_path.relative_to(run_dir).as_posix(),
                    "batch_path": batch_path.relative_to(run_dir).as_posix(),
                    "review_status": "not_started",
                    "assigned_worker": "unassigned",
                    "output_path": "",
                    "notes": "Ready for LLM semantic abstract review.",
                }
            )

    write_folder_readme(review_dir / "README.md")
    write_reviewer_instructions(setup_dir / "reviewer_instructions.md", args.batch_size)
    write_csv(
        setup_dir / "batch_manifest.csv",
        batch_rows,
        [
            "batch_id",
            "subsection_id",
            "batch_index",
            "candidate_count",
            "context_path",
            "batch_path",
            "review_status",
            "assigned_worker",
            "output_path",
            "notes",
        ],
    )
    write_csv(
        setup_dir / "abstract_review_status.csv",
        batch_rows,
        [
            "batch_id",
            "subsection_id",
            "batch_index",
            "candidate_count",
            "context_path",
            "batch_path",
            "review_status",
            "assigned_worker",
            "output_path",
            "notes",
        ],
    )
    write_setup_check(setup_dir / "semantic_abstract_review_setup_check.md", batch_rows)
    update_sqlite_step(run_dir, len(batch_rows))
    print(
        f"Prepared {len(batch_rows)} semantic abstract-review batches "
        f"for {len(subsections)} subsections."
    )
    return 0


def preflight_errors(run_dir: Path) -> list[str]:
    errors: list[str] = []
    metrics_path = run_dir / OUTPUT_DIR / "subsection_metrics.csv"
    first_pass_path = run_dir / SCREENING_DIR / "abstract_triage_first_pass.csv"
    final_set_path = run_dir / OUTPUT_DIR / "final_literature_sets.csv"
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    for path in (metrics_path, first_pass_path, final_set_path, sqlite_path):
        if not path.exists():
            errors.append(f"missing preflight input: {path.relative_to(run_dir)}")
    if errors:
        return errors
    metrics = read_csv(metrics_path)
    non_ready = [
        row for row in metrics if row.get("controller_status") != "abstract_review_needed"
    ]
    if non_ready:
        details = ", ".join(
            f"{row.get('subsection_id')}={row.get('controller_status')}"
            for row in non_ready[:20]
        )
        errors.append(f"non-ready subsection retrieval status: {details}")
    first_pass_rows = read_csv(first_pass_path)
    if first_pass_rows:
        missing = sorted(set(SEMANTIC_FIELDS) - set(first_pass_rows[0]))
        if missing:
            errors.append("missing semantic fields in first-pass CSV: " + ", ".join(missing))
    final_rows = read_csv(final_set_path)
    if not final_rows:
        errors.append("final_literature_sets.csv has no candidates")
    elif any(row.get("abstract_review_decision") != "not_reviewed" for row in final_rows):
        errors.append("candidate final_literature_sets.csv must be unreviewed before setup")
    try:
        with sqlite3.connect(sqlite_path) as connection:
            sqlite_non_ready = connection.execute(
                """
                SELECT subsection_id, controller_status
                FROM subsection_metrics
                WHERE controller_status != 'abstract_review_needed'
                ORDER BY subsection_id
                """
            ).fetchall()
    except sqlite3.Error as exc:
        errors.append(f"could not inspect SQLite preflight state: {exc}")
        return errors
    if sqlite_non_ready:
        details = ", ".join(f"{row[0]}={row[1]}" for row in sqlite_non_ready[:20])
        errors.append(f"SQLite non-ready subsection retrieval status: {details}")
    return errors


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def chunks(rows: list[dict[str, str]], size: int) -> list[list[dict[str, str]]]:
    return [rows[index : index + size] for index in range(0, len(rows), size)]


def sqlite_candidate_rows_by_subsection(
    sqlite_path: Path, final_rows: list[dict[str, str]]
) -> dict[str, list[dict[str, str]]]:
    final_by_key = {
        (row.get("subsection_id", ""), row.get("paper_id", "")): row
        for row in final_rows
    }
    rows_by_subsection: dict[str, list[dict[str, str]]] = {}
    with sqlite3.connect(sqlite_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                sp.subsection_id,
                sp.paper_id,
                pr.pmid,
                pr.pmcid,
                pr.doi,
                pr.title,
                pr.journal,
                pr.publication_year,
                pr.publication_types_json,
                pr.abstract,
                sp.source_query_ids,
                sp.abstract_review_decision,
                sp.evidence_role,
                sp.draft_access_status,
                sp.verified_access_status,
                p.venue_trust_label
            FROM subsection_papers sp
            JOIN pubmed_records pr ON pr.paper_id = sp.paper_id
            LEFT JOIN papers p ON p.paper_id = sp.paper_id
            ORDER BY sp.subsection_id, CAST(pr.publication_year AS INTEGER) DESC, pr.pmid DESC
            """
        ).fetchall()
    for row in rows:
        key = (str(row["subsection_id"] or ""), str(row["paper_id"] or ""))
        final_row = final_by_key.get(key, {})
        publication_types = decode_json_list(row["publication_types_json"])
        candidate = {
            "subsection_id": key[0],
            "paper_id": key[1],
            "PMID": str(row["pmid"] or ""),
            "PMCID": str(row["pmcid"] or ""),
            "DOI": str(row["doi"] or ""),
            "title": str(row["title"] or ""),
            "journal": str(row["journal"] or ""),
            "publication_year": str(row["publication_year"] or ""),
            "article_type": ";".join(publication_types),
            "abstract": str(row["abstract"] or ""),
            "source_query_ids": str(row["source_query_ids"] or ""),
            "abstract_review_decision": str(row["abstract_review_decision"] or "not_reviewed"),
            "first_pass_rationale": "Await semantic abstract review.",
            "first_pass_confidence": "unknown",
            "topic_match_type": "unknown",
            "semantic_fit_score": "unknown",
            "mechanism_match": "unknown",
            "entity_context_match": "unknown",
            "evidence_directness": "unknown",
            "key_relevant_abstract_text": "not_reviewed",
            "missing_full_text_reason": "unknown",
            "synthesis_role": str(row["evidence_role"] or final_row.get("evidence_role", "unknown")),
            "venue_trust_label": str(row["venue_trust_label"] or final_row.get("venue_trust_label", "unknown")),
            "verified_access_status": str(row["verified_access_status"] or final_row.get("verified_access_status", "unknown")),
            "reviewer_id": "not_reviewed",
            "review_method": "not_reviewed",
            "reviewer_model_or_agent": "not_reviewed",
            "reviewed_at": "not_reviewed",
        }
        rows_by_subsection.setdefault(key[0], []).append(candidate)
    return rows_by_subsection


def decode_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]


def write_subsection_context(path: Path, subsection: dict[str, object]) -> None:
    citations = subsection.get("citations", [])
    citation_lines = []
    for citation in citations:
        citation_lines.append(
            "- "
            + "; ".join(
                [
                    f"citation_id={citation.get('citation_id', '')}",
                    f"citation={citation.get('citation', '')}",
                    f"PMID={citation.get('PMID', '')}",
                    f"evidence_role={citation.get('evidence_role', '')}",
                    f"notes={citation.get('notes', '')}",
                ]
            )
        )
    path.write_text(
        "\n".join(
            [
                f"# Semantic Abstract Review Context: {subsection['subsection_id']}",
                "",
                "## Chapter",
                "",
                str(subsection["chapter_title"]),
                "",
                "## Subsection",
                "",
                f"{subsection['subsection_index']}: {subsection['subsection_title']}",
                "",
                "## Subsection Prose",
                "",
                "\n".join(str(line) for line in subsection.get("prose_lines", [])),
                "",
                "## Draft Citation Anchors",
                "",
                "\n".join(citation_lines) if citation_lines else "No draft citations.",
                "",
                "## Review Task",
                "",
                "Compare each candidate title and abstract directly with this subsection. "
                "The decision should reflect scientific semantic fit, not keyword overlap alone.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_batch_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "subsection_id",
        "paper_id",
        "PMID",
        "PMCID",
        "DOI",
        "title",
        "journal",
        "publication_year",
        "article_type",
        "abstract",
        "source_query_ids",
        "abstract_review_decision",
        "first_pass_rationale",
        "first_pass_confidence",
        "topic_match_type",
        "semantic_fit_score",
        "mechanism_match",
        "entity_context_match",
        "evidence_directness",
        "key_relevant_abstract_text",
        "missing_full_text_reason",
        "synthesis_role",
        "venue_trust_label",
        "verified_access_status",
        "reviewer_id",
        "review_method",
        "reviewer_model_or_agent",
        "reviewed_at",
    ]
    normalized_rows = []
    for row in rows:
        normalized = {field: row.get(field, "") for field in fieldnames}
        normalized["abstract_review_decision"] = "not_reviewed"
        normalized["semantic_fit_score"] = "unknown"
        normalized["mechanism_match"] = "unknown"
        normalized["entity_context_match"] = "unknown"
        normalized["evidence_directness"] = "unknown"
        normalized["key_relevant_abstract_text"] = "not_reviewed"
        normalized["missing_full_text_reason"] = "unknown"
        normalized["reviewer_id"] = "not_reviewed"
        normalized["review_method"] = "not_reviewed"
        normalized["reviewer_model_or_agent"] = "not_reviewed"
        normalized["reviewed_at"] = "not_reviewed"
        normalized_rows.append(normalized)
    write_csv(path, normalized_rows, fieldnames)


def write_reviewer_instructions(path: Path, batch_size: int) -> None:
    path.write_text(
        f"""# Semantic Abstract Review Worker Instructions

## Purpose

Reduce broad PubMed candidate sets into subsection-specific scientific evidence
sets by reading titles and abstracts semantically.

## Inputs Per Worker

- one `02_context/SUB###.md` file
- one `03_batches/SUB###-B###.csv` file with up to `{batch_size}` candidates

## Required Decisions

For every candidate row, fill:

- `abstract_review_decision`: one of `include_primary`, `include_context`,
  `exclude_off_scope`, `exclude_wrong_level`, `exclude_low_quality_or_blocked`,
  or `uncertain_full_text_needed`
- `first_pass_rationale`: one concise scientific reason tied to the subsection
- `first_pass_confidence`: `high`, `medium`, or `low`
- `topic_match_type`: `direct`, `partial`, `analogous`, `none`, or `unknown`
- `semantic_fit_score`: `0`, `1`, `2`, or `3`
- `mechanism_match`: `direct`, `partial`, `analogous`, `none`, or `unknown`
- `entity_context_match`: `direct`, `partial`, `analogous`, `none`, or
  `unknown`
- `evidence_directness`: `direct_experimental`, `direct_clinical`,
  `computational_or_indirect`, `background_review`, `not_evidence`, or
  `unknown`
- `key_relevant_abstract_text`: a brief phrase identifying the relevance signal
- `missing_full_text_reason`: `not_needed_for_abstract_triage` or a concise
  reason full text is needed
- `reviewer_id`: stable identifier for the LLM worker or subagent that reviewed
  the row
- `review_method`: exactly `llm_semantic_reading`
- `reviewer_model_or_agent`: model, agent, or subagent name used for semantic
  reading
- `reviewed_at`: ISO-like timestamp or date when the row was reviewed

Do not use scripts, keyword filters, regex classifiers, or deterministic
heuristics to fill reviewed batch decisions. Such tools may prepare candidates
or summarize counts, but the reviewed CSV rows must be produced by LLM semantic
reading of the title, abstract, and subsection context.

## Inclusion Standard

Include only papers whose title/abstract directly or usefully supports,
challenges, contextualizes, or narrows a scientific claim in the subsection.
Keyword overlap alone is insufficient. Exact entity mismatch is not by itself
exclusion when the abstract studies an allowed analogous mechanism or system.

Use `include_primary` only for claim-direct evidence. The abstract must show
that the paper directly supports or challenges a specific scientific claim in
the subsection, not merely that it is original research on a related topic.
Primary evidence should usually have all of the following:

- `semantic_fit_score` = `3`
- `topic_match_type` = `direct`
- `entity_context_match` = `direct` or a clearly justified `partial`
- `mechanism_match` = `direct` or a clearly justified `partial`
- `evidence_directness` is not `background_review`, `not_evidence`, or
  `unknown`

If a paper is original research but the abstract is adjacent, broad, only partly
aligned, missing the key entity/context, or useful mainly for plausibility or
landscape, use `include_context`. If it looks potentially primary but the
abstract does not expose timing, model, treatment exposure, assay result,
clinical endpoint, or causal interpretation, use `uncertain_full_text_needed`.

Use `include_context` for papers that help frame the subsection, define the
mechanism space, interpret plausibility, provide high-quality review context, or
explain an assay or clinical landscape. Context papers are useful for writing,
but they are not direct proof.

Apply venue quality asymmetrically:

- Context papers should usually come from `reputable_or_likely_reputable`
  venues. Retain context papers from `uncertain` venues only when the abstract
  is unusually useful, and state the lower weight in `first_pass_rationale`.
- Primary evidence may pass from `reputable_or_likely_reputable` or `uncertain`
  venues when the abstract reports concrete claim-direct data. Mark full text as
  needed when methods, controls, or causal interpretation cannot be judged from
  the abstract.
- `hard_blocked` venues should be marked `exclude_low_quality_or_blocked`
  unless a human override is documented.
- Preprints may be retained as emerging evidence or context, but do not let a
  preprint alone establish a settled claim.

## Output Rule

Write reviewed batch outputs under
`artifacts/03_semantic_abstract_review/04_reviewed_batches/` using the same filename
as the input batch. Do not create rewritten sections, evidence packets, PDFs, or
claim-verification artifacts in this step.

Every reviewed output row must include row-level LLM provenance:
`reviewer_id`, `review_method=llm_semantic_reading`,
`reviewer_model_or_agent`, and `reviewed_at`.
""",
        encoding="utf-8",
    )


def write_folder_readme(path: Path) -> None:
    path.write_text(
        """# Semantic Abstract Review Artifacts

This folder stores Step 4 artifacts grouped by role. The canonical workflow
state remains in `artifacts/00_workflow_control/01_state/workflow_state.sqlite`.

- `01_setup/`: reviewer instructions, batch manifest, status tracker, and setup
  validation report.
- `02_context/`: one subsection context file per draft subsection.
- `03_batches/`: unreviewed subsection-paper CSV batches for workers.
- `04_reviewed_batches/`: reviewed CSV batches returned by workers.
- `05_outputs/`: merge report and compact outputs generated after review.

Reviewed batch CSVs are the worker handoff surface; merged decisions are stored
canonically in SQLite.
""",
        encoding="utf-8",
    )


def write_setup_check(path: Path, batch_rows: list[dict[str, str]]) -> None:
    subsection_count = len({row["subsection_id"] for row in batch_rows})
    candidate_count = sum(int(row["candidate_count"]) for row in batch_rows)
    path.write_text(
        f"""# Semantic Abstract Review Setup Check

## Overall Status

`pass`

## Preflight Compliance

All subsections are marked `abstract_review_needed` before batch preparation.

## SQLite Source Compliance

Candidate batch rows were hydrated from SQLite by joining `subsection_papers`
with `pubmed_records`, with CSV artifacts used as coverage/audit references.

## Batch Coverage

Prepared `{len(batch_rows)}` batches for `{subsection_count}` subsections and
`{candidate_count}` subsection-paper candidates.

## Semantic Field Compliance

Batch files contain required semantic review fields.

## Worker Output Boundary

No reviewed batch outputs, claim manifests, evidence packets, PDFs, rewritten
sections, or final-review artifacts are created during setup. Workers should
write reviewed CSVs only after receiving a specific batch assignment. Reviewed
CSV rows must include `review_method=llm_semantic_reading`; heuristic or
script-filled decisions are not valid semantic abstract review.

## Parallelization Readiness

`yes`

## Ready For Worker Review

`yes`
""",
        encoding="utf-8",
    )


def update_sqlite_step(run_dir: Path, batch_count: int) -> None:
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    now = timestamp()
    with sqlite3.connect(sqlite_path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO workflow_steps(
                step_name, status, started_at, completed_at, validation_status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "semantic_abstract_review_setup",
                "initialized",
                now,
                "",
                "not_validated",
                f"Prepared {batch_count} semantic abstract-review batches.",
            ),
        )
        connection.commit()


def timestamp() -> str:
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":
    raise SystemExit(main())

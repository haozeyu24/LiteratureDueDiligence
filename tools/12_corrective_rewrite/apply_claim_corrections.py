#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_workflow_control"))

from workflow_state import connect, timestamp


CLAIM_DIR = Path("artifacts/10_claim_verification")
CLAIM_INPUT_DIR = CLAIM_DIR / "01_inputs"
CLAIM_REVIEW_DIR = CLAIM_DIR / "03_claim_reviews"
CORRECTION_DIR = Path("artifacts/11_corrective_rewrite")
CORRECTION_INPUT_DIR = CORRECTION_DIR / "01_inputs"
CORRECTION_OUTPUT_DIR = CORRECTION_DIR / "02_outputs"
CORRECTION_VERIFY_DIR = CORRECTION_DIR / "03_verification"
CORRECTION_SUMMARY_DIR = CORRECTION_DIR / "04_outputs"
ASSEMBLED_REVIEW = Path("drafts/assembled_review.md")
CORRECTED_REVIEW = Path("drafts/corrected_review.md")

SUPPORTED_STATUS = "supported"
REMOVE_STATUS = "remove"

MANIFEST_FIELDS = [
    "claim_id",
    "subsection_id",
    "verification_status",
    "mismatch_type",
    "original_claim",
    "corrected_claim",
    "final_replacement",
    "cited_paper_ids",
    "citation_ids",
    "action",
    "replacement_status",
    "notes",
]

CHECK_FIELDS = ["check_name", "check_status", "observed_value", "notes"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply Stage 11 claim-verification decisions to create a corrected review draft."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        raise SystemExit(f"Run directory does not exist: {run_dir}")

    create_stage_dirs(run_dir)
    write_stage_readme(run_dir)

    assembled_path = run_dir / ASSEMBLED_REVIEW
    if not assembled_path.exists():
        raise SystemExit(f"Missing assembled review: {assembled_path}")
    assembled_text = assembled_path.read_text(encoding="utf-8")

    claim_rows = load_claim_reviews(run_dir)
    correction_rows, corrected_text = apply_corrections(assembled_text, claim_rows)
    check_rows = build_checks(assembled_text, corrected_text, claim_rows, correction_rows)

    write_csv(run_dir / CORRECTION_INPUT_DIR / "correction_manifest.csv", MANIFEST_FIELDS, correction_rows)
    corrected_review_path = run_dir / CORRECTED_REVIEW
    corrected_review_path.parent.mkdir(parents=True, exist_ok=True)
    corrected_review_path.write_text(corrected_text, encoding="utf-8")
    (run_dir / CORRECTION_OUTPUT_DIR / "corrected_review.md").write_text(corrected_text, encoding="utf-8")
    write_csv(run_dir / CORRECTION_VERIFY_DIR / "corrective_rewrite_check.csv", CHECK_FIELDS, check_rows)
    write_summary(run_dir, claim_rows, correction_rows, check_rows)
    write_sqlite(run_dir, correction_rows, check_rows)

    if any(row["check_status"] != "pass" for row in check_rows):
        raise SystemExit("Corrective rewrite finished with failed checks; inspect corrective_rewrite_check.csv")

    print(
        "Corrective rewrite complete: "
        f"{len(correction_rows)} non-supported claims handled; "
        f"corrected draft written to {corrected_review_path}"
    )
    return 0


def create_stage_dirs(run_dir: Path) -> None:
    for directory in (
        CORRECTION_INPUT_DIR,
        CORRECTION_OUTPUT_DIR,
        CORRECTION_VERIFY_DIR,
        CORRECTION_SUMMARY_DIR,
    ):
        (run_dir / directory).mkdir(parents=True, exist_ok=True)


def write_stage_readme(run_dir: Path) -> None:
    text = """# Corrective Rewrite Artifacts

Stage 12 applies completed claim-verification decisions to the assembled review.
It does not introduce new evidence, new citations, or model-memory claims.

Folders:

- `01_inputs`: correction manifest for non-supported claims
- `02_outputs`: corrected review copy
- `03_verification`: deterministic checks
- `04_outputs`: stage summary
"""
    (run_dir / CORRECTION_DIR / "README.md").write_text(text, encoding="utf-8")


def load_claim_reviews(run_dir: Path) -> list[dict[str, str]]:
    manifest_path = run_dir / CLAIM_INPUT_DIR / "claim_manifest.csv"
    review_dir = run_dir / CLAIM_REVIEW_DIR
    if not manifest_path.exists():
        raise SystemExit(f"Missing claim manifest: {manifest_path}")
    if not review_dir.exists():
        raise SystemExit(f"Missing claim review directory: {review_dir}")

    manifest_by_claim: dict[str, dict[str, str]] = {}
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            manifest_by_claim[row["claim_id"]] = row

    rows: list[dict[str, str]] = []
    for review_path in sorted(review_dir.glob("SUB*.csv")):
        with review_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                claim_id = row.get("claim_id", "")
                manifest_row = manifest_by_claim.get(claim_id, {})
                merged = dict(manifest_row)
                merged.update(row)
                merged["source_review_path"] = review_path.relative_to(run_dir).as_posix()
                rows.append(merged)

    if not rows:
        raise SystemExit("No claim review rows found.")
    return rows


def apply_corrections(
    assembled_text: str, claim_rows: list[dict[str, str]]
) -> tuple[list[dict[str, str]], str]:
    corrected_text = assembled_text
    correction_rows: list[dict[str, str]] = []

    for row in claim_rows:
        status = row.get("verification_status", "").strip()
        if status == SUPPORTED_STATUS:
            continue

        claim_id = row.get("claim_id", "")
        original = row.get("claim_text", "").strip()
        corrected_claim = row.get("corrected_claim", "").strip()
        cited_paper_ids = row.get("cited_paper_ids", "").strip()
        citation_ids = row.get("citation_ids", "").strip()
        action = "remove_claim" if status == REMOVE_STATUS else "replace_claim"
        replacement = "" if action == "remove_claim" else ensure_traceable_replacement(
            corrected_claim, cited_paper_ids, citation_ids
        )

        count = corrected_text.count(original)
        if not original:
            replacement_status = "fail"
            notes = "missing original claim text"
        elif action == "replace_claim" and not corrected_claim:
            replacement_status = "fail"
            notes = "non-supported claim has no corrected_claim"
        elif count != 1:
            replacement_status = "fail"
            notes = f"original claim occurrence count was {count}; expected 1"
        else:
            corrected_text = corrected_text.replace(original, replacement, 1)
            replacement_status = "applied"
            notes = "applied exact text replacement"

        correction_rows.append(
            {
                "claim_id": claim_id,
                "subsection_id": row.get("subsection_id", ""),
                "verification_status": status,
                "mismatch_type": row.get("mismatch_type", ""),
                "original_claim": original,
                "corrected_claim": corrected_claim,
                "final_replacement": replacement,
                "cited_paper_ids": cited_paper_ids,
                "citation_ids": citation_ids,
                "action": action,
                "replacement_status": replacement_status,
                "notes": notes,
            }
        )

    return correction_rows, corrected_text


def ensure_traceable_replacement(
    corrected_claim: str, cited_paper_ids: str, citation_ids: str
) -> str:
    replacement = corrected_claim.strip()
    for identifier in split_pipe_values(cited_paper_ids):
        token = f"`{identifier}`"
        if token not in replacement:
            replacement = f"{replacement} {token}".strip()
    for identifier in split_pipe_values(citation_ids):
        token = f"`{identifier}`"
        if token not in replacement:
            replacement = f"{replacement} {token}".strip()
    return replacement


def split_pipe_values(value: str) -> list[str]:
    return [part.strip() for part in value.split("|") if part.strip()]


def build_checks(
    assembled_text: str,
    corrected_text: str,
    claim_rows: list[dict[str, str]],
    correction_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    problem_claims = [
        row for row in claim_rows if row.get("verification_status", "").strip() != SUPPORTED_STATUS
    ]
    applied_rows = [row for row in correction_rows if row["replacement_status"] == "applied"]
    checks: list[dict[str, str]] = []

    checks.append(check_row(
        "all_non_supported_claims_have_actions",
        len(correction_rows) == len(problem_claims),
        f"{len(correction_rows)}/{len(problem_claims)}",
        "Every non-supported claim must have a correction manifest row.",
    ))
    checks.append(check_row(
        "all_replacements_applied_once",
        len(applied_rows) == len(correction_rows),
        f"{len(applied_rows)}/{len(correction_rows)}",
        "Each correction must apply exactly once to the assembled draft.",
    ))
    lingering = [
        row["claim_id"]
        for row in correction_rows
        if row["original_claim"] and row["original_claim"] in corrected_text
    ]
    checks.append(check_row(
        "no_problem_claim_text_remaining",
        not lingering,
        str(len(lingering)),
        ";".join(lingering) if lingering else "No original problem claim text remains.",
    ))
    checks.append(check_row(
        "corrected_review_populated",
        len(corrected_text.strip()) >= 1000,
        str(len(corrected_text.encode("utf-8"))),
        "Corrected review must be non-empty and review-scale.",
    ))
    before_citations = citation_like_ids(assembled_text)
    after_citations = citation_like_ids(corrected_text)
    new_citations = sorted(after_citations - before_citations)
    checks.append(check_row(
        "no_new_untraced_citations",
        not new_citations,
        str(len(new_citations)),
        ";".join(new_citations) if new_citations else "No new citation-like IDs introduced.",
    ))
    before_papers = paper_ids(assembled_text)
    after_papers = paper_ids(corrected_text)
    new_papers = sorted(after_papers - before_papers)
    checks.append(check_row(
        "no_new_untraced_paper_ids",
        not new_papers,
        str(len(new_papers)),
        ";".join(new_papers) if new_papers else "No new paper IDs introduced.",
    ))
    status_counts = Counter(row.get("verification_status", "") for row in problem_claims)
    checks.append(check_row(
        "problem_status_counts_recorded",
        True,
        ";".join(f"{key}:{value}" for key, value in sorted(status_counts.items())) or "none",
        "Non-supported status counts are recorded for audit.",
    ))
    return checks


def check_row(name: str, passed: bool, observed: str, notes: str) -> dict[str, str]:
    return {
        "check_name": name,
        "check_status": "pass" if passed else "fail",
        "observed_value": observed,
        "notes": notes,
    }


def citation_like_ids(text: str) -> set[str]:
    return set(re.findall(r"\bSUB\d{3}-C\d{3}\b", text))


def paper_ids(text: str) -> set[str]:
    return set(re.findall(r"\bPAPER-\d+\b", text))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_summary(
    run_dir: Path,
    claim_rows: list[dict[str, str]],
    correction_rows: list[dict[str, str]],
    check_rows: list[dict[str, str]],
) -> None:
    status_counts = Counter(row.get("verification_status", "") for row in claim_rows)
    correction_counts = Counter(row.get("verification_status", "") for row in correction_rows)
    check_status = "pass" if all(row["check_status"] == "pass" for row in check_rows) else "fail"
    lines = [
        "# Corrective Rewrite Summary",
        "",
        "## Counts",
        "",
        f"- total_claims_reviewed: {len(claim_rows)}",
        f"- non_supported_claims_corrected: {len(correction_rows)}",
        f"- check_status: {check_status}",
        "",
        "## Verification Status Counts",
        "",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Corrected Status Counts", ""])
    if correction_counts:
        for status, count in sorted(correction_counts.items()):
            lines.append(f"- {status}: {count}")
    else:
        lines.append("- none: 0")
    lines.extend(
        [
            "",
            "## Downstream Use",
            "",
            "Use `drafts/corrected_review.md` as the next review draft. It contains only",
            "deterministic corrections from Stage 11 and must not be treated as final prose",
            "polish. Any remaining scientific uncertainty should be handled by later human",
            "inspection or a separate final review pass.",
        ]
    )
    (run_dir / CORRECTION_SUMMARY_DIR / "corrective_rewrite_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def write_sqlite(
    run_dir: Path, correction_rows: list[dict[str, str]], check_rows: list[dict[str, str]]
) -> None:
    with connect(run_dir) as connection:
        now = timestamp()
        connection.execute("DELETE FROM corrective_rewrite_claims")
        connection.execute("DELETE FROM corrective_rewrite_checks")
        for row in correction_rows:
            connection.execute(
                """
                INSERT INTO corrective_rewrite_claims(
                    claim_id, subsection_id, verification_status, mismatch_type,
                    original_claim, corrected_claim, final_replacement, action,
                    replacement_status, cited_paper_ids, citation_ids, notes, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["claim_id"],
                    row["subsection_id"],
                    row["verification_status"],
                    row["mismatch_type"],
                    row["original_claim"],
                    row["corrected_claim"],
                    row["final_replacement"],
                    row["action"],
                    row["replacement_status"],
                    row["cited_paper_ids"],
                    row["citation_ids"],
                    row["notes"],
                    now,
                ),
            )
        for row in check_rows:
            connection.execute(
                """
                INSERT INTO corrective_rewrite_checks(check_name, check_status, observed_value, notes, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    row["check_name"],
                    row["check_status"],
                    row["observed_value"],
                    row["notes"],
                    now,
                ),
            )
        status = "complete" if all(row["check_status"] == "pass" for row in check_rows) else "needs_attention"
        connection.execute(
            """
            INSERT INTO workflow_steps(step_name, status, started_at, completed_at, validation_status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(step_name) DO UPDATE SET
                status = excluded.status,
                completed_at = excluded.completed_at,
                validation_status = excluded.validation_status,
                notes = excluded.notes
            """,
            (
                "corrective_rewrite",
                status,
                now,
                now,
                "not_run",
                f"{len(correction_rows)} non-supported claims handled.",
            ),
        )
        connection.commit()


if __name__ == "__main__":
    raise SystemExit(main())

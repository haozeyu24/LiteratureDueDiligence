#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_workflow_control"))

from workflow_state import connect, timestamp


STAGE_DIR = Path("artifacts/10_claim_verification")
INPUT_DIR = STAGE_DIR / "01_inputs"
REVIEW_DIR = STAGE_DIR / "03_claim_reviews"
VERIFY_DIR = STAGE_DIR / "04_verification"
OUTPUT_DIR = STAGE_DIR / "05_outputs"

CLAIM_MANIFEST = INPUT_DIR / "claim_manifest.csv"
CHECK_PATH = VERIFY_DIR / "claim_verification_check.csv"

REVIEW_FIELDS = [
    "claim_id",
    "subsection_id",
    "claim_text",
    "cited_paper_ids",
    "citation_ids",
    "verification_status",
    "corrected_claim",
    "evidence_summary",
    "mismatch_type",
    "reviewer_notes",
]

CHECK_FIELDS = [
    "check_name",
    "check_status",
    "observed_value",
    "notes",
]

ALLOWED_STATUSES = {
    "supported",
    "partially_supported",
    "overgeneralized",
    "contradicted",
    "citation_mismatch",
    "citation_missing",
    "insufficient_evidence",
    "remove",
}

PROBLEM_STATUSES = ALLOWED_STATUSES - {"supported"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify claim-review CSV outputs against the claim verification contract."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    manifest_path = run_dir / CLAIM_MANIFEST
    if not manifest_path.exists():
        print("ERROR: claim_manifest.csv is missing. Run prepare_claim_verification.py first.", file=sys.stderr)
        return 1
    claims = load_csv(manifest_path)
    review_rows, read_errors = load_review_rows(run_dir, claims)
    check_rows = build_checks(claims, review_rows, read_errors)
    write_csv(run_dir / CHECK_PATH, CHECK_FIELDS, check_rows)
    write_summary(run_dir, claims, review_rows, check_rows)
    with connect(run_dir) as connection:
        write_sqlite(connection, claims, review_rows, check_rows)

    failed = [row for row in check_rows if row["check_status"] != "pass"]
    if failed:
        print(f"Stage 11 claim verification incomplete: passed={len(check_rows)-len(failed)} failed={len(failed)}", file=sys.stderr)
        return 2
    print(f"Stage 11 claim verification complete: claims={len(claims)}")
    return 0


def load_review_rows(run_dir: Path, claims: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str]]:
    review_paths = sorted({row["review_path"] for row in claims})
    rows = []
    errors = []
    for review_path in review_paths:
        path = run_dir / review_path
        if not path.exists():
            errors.append(f"missing review CSV: {review_path}")
            continue
        file_rows = load_csv(path)
        if file_rows and list(file_rows[0].keys()) != REVIEW_FIELDS:
            errors.append(f"review CSV has unexpected columns: {review_path}")
            continue
        rows.extend(file_rows)
    return rows, errors


def build_checks(
    claims: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    read_errors: list[str],
) -> list[dict[str, str]]:
    expected_ids = {row["claim_id"] for row in claims}
    reviewed_ids = [row.get("claim_id", "") for row in review_rows]
    reviewed_id_set = set(reviewed_ids)
    duplicate_ids = sorted({claim_id for claim_id in reviewed_ids if reviewed_ids.count(claim_id) > 1})
    status_ok = all(row.get("verification_status", "") in ALLOWED_STATUSES for row in review_rows)
    evidence_summary_ok = all(len(row.get("evidence_summary", "").strip()) >= 40 for row in review_rows)
    corrections_ok = all(
        row.get("verification_status", "") not in PROBLEM_STATUSES
        or len(row.get("corrected_claim", "").strip()) >= 20
        for row in review_rows
    )
    citation_consistency_ok = True
    manifest_by_id = {row["claim_id"]: row for row in claims}
    for row in review_rows:
        claim = manifest_by_id.get(row.get("claim_id", ""))
        if not claim:
            citation_consistency_ok = False
            continue
        if row.get("cited_paper_ids", "") != claim.get("cited_paper_ids", ""):
            citation_consistency_ok = False
        if row.get("citation_ids", "") != claim.get("citation_ids", ""):
            citation_consistency_ok = False
    return [
        check_row("review_csv_files_readable", not read_errors, str(len(read_errors)), "; ".join(read_errors) if read_errors else "All review CSV files were readable."),
        check_row("all_claims_reviewed_once", reviewed_id_set == expected_ids and not duplicate_ids, f"{len(reviewed_id_set)}/{len(expected_ids)}", f"Duplicate claim IDs: {', '.join(duplicate_ids)}" if duplicate_ids else "Every claim has exactly one review row."),
        check_row("only_manifest_claims_reviewed", reviewed_id_set.issubset(expected_ids), str(len(reviewed_id_set - expected_ids)), "No extra claim IDs appear in review outputs."),
        check_row("allowed_verification_statuses", status_ok, str(sum(1 for row in review_rows if row.get("verification_status", "") in ALLOWED_STATUSES)), "All verification statuses are allowed."),
        check_row("evidence_summaries_populated", evidence_summary_ok, str(sum(1 for row in review_rows if len(row.get("evidence_summary", "").strip()) >= 40)), "Every claim has a substantive evidence summary."),
        check_row("problem_claims_have_corrections", corrections_ok, str(sum(1 for row in review_rows if row.get("verification_status", "") in PROBLEM_STATUSES)), "Every non-supported claim has a corrected claim suggestion."),
        check_row("citation_metadata_preserved", citation_consistency_ok, str(len(review_rows)), "Review rows preserve manifest cited paper IDs and citation IDs."),
    ]


def check_row(name: str, passed: bool, observed: str, note: str) -> dict[str, str]:
    return {
        "check_name": name,
        "check_status": "pass" if passed else "fail",
        "observed_value": observed,
        "notes": note if passed else f"Check failed: {name}. {note}",
    }


def write_summary(
    run_dir: Path,
    claims: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    check_rows: list[dict[str, str]],
) -> None:
    passed = sum(1 for row in check_rows if row["check_status"] == "pass")
    status = "complete" if passed == len(check_rows) and check_rows else "incomplete"
    status_counts: dict[str, int] = {}
    for row in review_rows:
        status_counts[row.get("verification_status", "")] = status_counts.get(row.get("verification_status", ""), 0) + 1
    status_lines = "\n".join(f"- {status or 'blank'}: `{count}`" for status, count in sorted(status_counts.items()))
    (run_dir / OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    (run_dir / OUTPUT_DIR / "claim_verification_summary.md").write_text(
        "# Claim Verification Summary\n\n"
        "## Overall Status\n\n"
        f"`{status}`\n\n"
        "## Counts\n\n"
        f"- claims in manifest: `{len(claims)}`\n"
        f"- reviewed claims: `{len(review_rows)}`\n"
        f"- completion checks passed: `{passed}/{len(check_rows)}`\n\n"
        "## Verification Status Counts\n\n"
        f"{status_lines if status_lines else '- none: `0`'}\n\n"
        "## Downstream Use\n\n"
        "Correction and section-level rewrite may begin only after every claim "
        "has a valid review row and this stage validates successfully.\n",
        encoding="utf-8",
    )


def write_sqlite(
    connection: sqlite3.Connection,
    claims: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    check_rows: list[dict[str, str]],
) -> None:
    now = timestamp()
    review_by_id = {row["claim_id"]: row for row in review_rows}
    for claim in claims:
        review = review_by_id.get(claim["claim_id"], {})
        connection.execute(
            """
            UPDATE claim_verification_claims
            SET verification_status = ?, corrected_claim = ?, evidence_summary = ?,
                reviewer_notes = ?, updated_at = ?
            WHERE claim_id = ?
            """,
            (
                review.get("verification_status", "missing_review"),
                review.get("corrected_claim", ""),
                review.get("evidence_summary", ""),
                review.get("reviewer_notes", ""),
                now,
                claim["claim_id"],
            ),
        )
    connection.execute("DELETE FROM claim_verification_checks")
    for row in check_rows:
        connection.execute(
            """
            INSERT OR REPLACE INTO claim_verification_checks(
                check_name, check_status, observed_value, notes, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (row["check_name"], row["check_status"], row["observed_value"], row["notes"], now),
        )
    passed = sum(1 for row in check_rows if row["check_status"] == "pass")
    status = "complete" if passed == len(check_rows) and check_rows else "incomplete"
    connection.execute(
        """
        INSERT OR REPLACE INTO workflow_steps(
            step_name, status, started_at, completed_at, validation_status, notes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "claim_verification",
            status,
            now,
            now if status == "complete" else "",
            "pending_validation",
            f"Stage 11 claim verification checks passed for {passed}/{len(check_rows)} checks.",
        ),
    )
    connection.commit()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fieldnames} for row in rows])


if __name__ == "__main__":
    raise SystemExit(main())

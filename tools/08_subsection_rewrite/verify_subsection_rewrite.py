#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_workflow_control"))

from workflow_state import connect, timestamp


STAGE_DIR = Path("artifacts/07_subsection_rewrite")
INPUT_DIR = STAGE_DIR / "01_inputs"
REWRITTEN_DIR = STAGE_DIR / "03_rewritten_subsections"
VERIFY_DIR = STAGE_DIR / "04_verification"
OUTPUT_DIR = STAGE_DIR / "05_outputs"

MANIFEST_PATH = INPUT_DIR / "subsection_rewrite_manifest.csv"
CHECK_PATH = VERIFY_DIR / "rewrite_instruction_check.csv"
MIN_REWRITE_WORDS = 250

CHECK_FIELDS = [
    "subsection_id",
    "rewritten_path",
    "check_status",
    "has_rewritten_text",
    "meets_expansion_floor",
    "has_paper_triage",
    "triages_all_packet_papers",
    "has_citation_register",
    "citation_register_traceable",
    "has_inline_citations",
    "inline_citations_registered",
    "registered_citations_used",
    "acknowledges_full_text_sources",
    "has_structured_evidence_details",
    "allowed_triage_roles",
    "allowed_support_statuses",
    "uses_packet_papers",
    "has_residual_uncertainty",
    "no_new_untraced_citations",
    "notes",
]

TRIAGE_FIELDS = [
    "paper_id",
    "PMID",
    "selection_reason",
    "normalized_path",
    "full_text_read_status",
    "triage_role",
    "support_status",
    "key_evidence",
    "use_in_rewrite",
]

CITATION_FIELDS = [
    "citation_id",
    "paper_id",
    "PMID",
    "DOI",
    "evidence_use",
    "support_status",
    "cited_claim",
    "study_context",
    "model_or_population",
    "perturbation_or_exposure",
    "assay_or_endpoint",
    "direction_or_result",
    "limitation",
]

ALLOWED_TRIAGE_ROLES = {
    "core_support",
    "partial_support",
    "context_only",
    "boundary_or_negative",
    "not_used",
}

ALLOWED_SUPPORT_STATUSES = {
    "supports",
    "partially_supports",
    "context_only",
    "contradicts",
    "insufficient_evidence",
}

ALLOWED_READ_STATUSES = {
    "read_relevant_narrative",
    "no_normalized_full_text",
    "not_read_not_used",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Stage 8 rewritten subsection files against the rewrite contract."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    manifest_path = run_dir / MANIFEST_PATH
    if not manifest_path.exists():
        print("ERROR: Stage 8 manifest is missing. Run prepare_subsection_rewrite.py first.", file=sys.stderr)
        return 1
    manifest_rows = load_csv(manifest_path)
    check_rows = [check_rewrite(run_dir, row) for row in manifest_rows]
    write_csv(run_dir / CHECK_PATH, CHECK_FIELDS, check_rows)
    write_summary(run_dir, manifest_rows, check_rows)

    with connect(run_dir) as connection:
        write_sqlite(connection, manifest_rows, check_rows)

    failed = [row for row in check_rows if row["check_status"] != "pass"]
    if failed:
        print(
            "Stage 8 subsection rewrite verification incomplete: "
            f"passed={len(check_rows)-len(failed)} failed_or_pending={len(failed)}",
            file=sys.stderr,
        )
        return 2
    print(f"Stage 8 subsection rewrite verification complete: passed={len(check_rows)}")
    return 0


def check_rewrite(run_dir: Path, row: dict[str, str]) -> dict[str, str]:
    subsection_id = row["subsection_id"]
    rewritten_path = run_dir / row["rewritten_path"]
    packet_path = run_dir / row["paper_packet_path"]
    original_path = run_dir / row["original_subsection_path"]
    notes: list[str] = []
    checks = {
        "has_rewritten_text": False,
        "meets_expansion_floor": False,
        "has_paper_triage": False,
        "triages_all_packet_papers": False,
        "has_citation_register": False,
        "citation_register_traceable": False,
        "has_inline_citations": False,
        "inline_citations_registered": False,
        "registered_citations_used": False,
        "acknowledges_full_text_sources": False,
        "has_structured_evidence_details": False,
        "allowed_triage_roles": False,
        "allowed_support_statuses": False,
        "uses_packet_papers": False,
        "has_residual_uncertainty": False,
        "no_new_untraced_citations": False,
    }
    if not rewritten_path.exists():
        notes.append("rewritten subsection file is missing")
    else:
        text = rewritten_path.read_text(encoding="utf-8")
        paper_triage = section_text(text, "## Paper Triage")
        rewritten_text = section_text(text, "## Rewritten Text")
        citation_register = section_text(text, "## Citation Register")
        residual_uncertainty = section_text(text, "## Residual Uncertainty")
        packet_paper_ids = packet_ids(packet_path)
        triage_rows = parse_markdown_table(paper_triage)
        citation_rows = parse_markdown_table(citation_register)
        triage_ids = {row.get("paper_id", "") for row in triage_rows}
        cited_ids = {row.get("paper_id", "") for row in citation_rows if row.get("paper_id", "")}
        inline_ids = set(re.findall(r"`(pmid-\d+|doi-[A-Za-z0-9._-]+|paper-[A-Za-z0-9._-]+)`", rewritten_text))
        original_words = word_count(original_path.read_text(encoding="utf-8")) if original_path.exists() else 0
        rewritten_words = word_count(rewritten_text)
        expansion_floor = max(MIN_REWRITE_WORDS, int(original_words * 1.5 + 0.999))
        new_untraced = re.findall(r"new_untraced_citation", text, flags=re.IGNORECASE)
        checks["has_rewritten_text"] = rewritten_words >= MIN_REWRITE_WORDS
        checks["meets_expansion_floor"] = rewritten_words >= expansion_floor
        checks["has_paper_triage"] = table_has_fields(triage_rows, TRIAGE_FIELDS)
        checks["triages_all_packet_papers"] = bool(packet_paper_ids) and packet_paper_ids.issubset(triage_ids)
        checks["has_citation_register"] = table_has_fields(citation_rows, CITATION_FIELDS)
        checks["citation_register_traceable"] = (
            checks["has_citation_register"]
            and bool(cited_ids)
            and cited_ids.issubset(packet_paper_ids)
            and cited_ids.issubset(triage_ids)
        )
        checks["has_inline_citations"] = bool(inline_ids)
        checks["inline_citations_registered"] = bool(inline_ids) and inline_ids.issubset(cited_ids)
        checks["registered_citations_used"] = bool(cited_ids) and cited_ids.issubset(inline_ids)
        checks["acknowledges_full_text_sources"] = checks["has_paper_triage"] and all(
            row.get("full_text_read_status", "") in ALLOWED_READ_STATUSES
            and (
                not row.get("normalized_path", "")
                or row.get("full_text_read_status", "") != "no_normalized_full_text"
            )
            and (
                row.get("paper_id", "") not in cited_ids
                or row.get("full_text_read_status", "") == "read_relevant_narrative"
                or not row.get("normalized_path", "")
            )
            for row in triage_rows
        )
        detail_fields = [
            "cited_claim",
            "study_context",
            "model_or_population",
            "perturbation_or_exposure",
            "assay_or_endpoint",
            "direction_or_result",
            "limitation",
        ]
        checks["has_structured_evidence_details"] = checks["has_citation_register"] and all(
            all(row.get(field, "").strip() for field in detail_fields) for row in citation_rows
        )
        checks["allowed_triage_roles"] = checks["has_paper_triage"] and all(
            row.get("triage_role", "") in ALLOWED_TRIAGE_ROLES for row in triage_rows
        )
        checks["allowed_support_statuses"] = (
            checks["has_paper_triage"]
            and checks["has_citation_register"]
            and all(row.get("support_status", "") in ALLOWED_SUPPORT_STATUSES for row in triage_rows)
            and all(row.get("support_status", "") in ALLOWED_SUPPORT_STATUSES for row in citation_rows)
        )
        checks["uses_packet_papers"] = bool(packet_paper_ids.intersection(inline_ids))
        checks["has_residual_uncertainty"] = len(residual_uncertainty.strip()) >= 20
        checks["no_new_untraced_citations"] = not new_untraced
        if not checks["has_rewritten_text"]:
            notes.append(f"rewritten text is missing or below {MIN_REWRITE_WORDS} words")
        if not checks["meets_expansion_floor"]:
            notes.append(
                f"rewritten text has {rewritten_words} words; required >= {expansion_floor} "
                f"(max of {MIN_REWRITE_WORDS} and 1.5x original {original_words})"
            )
        if not checks["has_paper_triage"]:
            notes.append("paper triage table is missing or has unexpected columns")
        if not checks["triages_all_packet_papers"]:
            missing = sorted(packet_paper_ids - triage_ids)
            notes.append(f"paper triage does not include every packet paper: missing={','.join(missing[:10])}")
        if not checks["has_citation_register"]:
            notes.append("citation register header is missing")
        if not checks["citation_register_traceable"]:
            untraced = sorted(cited_ids - packet_paper_ids)
            notes.append(f"citation register is not fully traceable to packet and triage: untraced={','.join(untraced[:10])}")
        if not checks["has_inline_citations"]:
            notes.append("rewritten text has no inline packet paper citations")
        if not checks["inline_citations_registered"]:
            missing = sorted(inline_ids - cited_ids)
            notes.append(f"inline citations are missing from citation register: missing={','.join(missing[:10])}")
        if not checks["registered_citations_used"]:
            unused = sorted(cited_ids - inline_ids)
            notes.append(f"citation register includes papers not cited inline: unused={','.join(unused[:10])}")
        if not checks["acknowledges_full_text_sources"]:
            notes.append("paper triage does not properly acknowledge normalized full-text read status")
        if not checks["has_structured_evidence_details"]:
            notes.append("citation register lacks required structured evidence-detail fields")
        if not checks["allowed_triage_roles"]:
            notes.append("paper triage contains unsupported triage_role values")
        if not checks["allowed_support_statuses"]:
            notes.append("triage or citation register contains unsupported support_status values")
        if not checks["uses_packet_papers"]:
            notes.append("no packet paper_id appears in rewritten file")
        if not checks["has_residual_uncertainty"]:
            notes.append("residual uncertainty section is missing or too short")
        if not checks["no_new_untraced_citations"]:
            notes.append("contains new_untraced_citation marker")
    passed = all(checks.values())
    return {
        "subsection_id": subsection_id,
        "rewritten_path": row["rewritten_path"],
        "check_status": "pass" if passed else "fail",
        **{key: "1" if value else "0" for key, value in checks.items()},
        "notes": "; ".join(notes) if notes else "All deterministic rewrite checks passed.",
    }


def section_text(text: str, heading: str) -> str:
    pattern = re.escape(heading) + r"\n(?P<body>.*?)(?=\n## |\Z)"
    match = re.search(pattern, text, flags=re.DOTALL)
    return match.group("body").strip() if match else ""


def packet_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"- paper_id: `(.*?)`", text))


def parse_markdown_table(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []
    headers = split_table_row(lines[0])
    separator = split_table_row(lines[1])
    if not headers or not all(set(cell) <= {"-", ":"} and "-" in cell for cell in separator):
        return []
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        cells = split_table_row(line)
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells, strict=True)))
    return rows


def split_table_row(line: str) -> list[str]:
    return [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]


def table_has_fields(rows: list[dict[str, str]], fields: list[str]) -> bool:
    return bool(rows) and list(rows[0].keys()) == fields


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def write_summary(run_dir: Path, manifest_rows: list[dict[str, str]], check_rows: list[dict[str, str]]) -> None:
    passed = sum(1 for row in check_rows if row["check_status"] == "pass")
    status = "complete" if passed == len(check_rows) and check_rows else "incomplete"
    (run_dir / OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    (run_dir / OUTPUT_DIR / "subsection_rewrite_summary.md").write_text(
        "# Subsection Rewrite Summary\n\n"
        "## Overall Status\n\n"
        f"`{status}`\n\n"
        "## Counts\n\n"
        f"- rewrite work orders: `{len(manifest_rows)}`\n"
        f"- rewritten subsections checked: `{len(check_rows)}`\n"
        f"- rewrite checks passed: `{passed}`\n\n"
        "## Downstream Use\n\n"
        "Claim-level verification may begin only when every rewritten subsection "
        "passes this deterministic rewrite check and Stage 8 validation passes.\n",
        encoding="utf-8",
    )


def write_sqlite(
    connection: sqlite3.Connection,
    manifest_rows: list[dict[str, str]],
    check_rows: list[dict[str, str]],
) -> None:
    now = timestamp()
    check_by_id = {row["subsection_id"]: row for row in check_rows}
    for row in manifest_rows:
        check = check_by_id[row["subsection_id"]]
        rewrite_status = "complete" if check["check_status"] == "pass" else "needs_revision"
        connection.execute(
            """
            UPDATE subsection_rewrite_tasks
            SET rewritten_path = ?, rewrite_status = ?, notes = ?, updated_at = ?
            WHERE subsection_id = ?
            """,
            (row["rewritten_path"], rewrite_status, check["notes"], now, row["subsection_id"]),
        )
        connection.execute(
            """
            INSERT OR REPLACE INTO subsection_rewrite_checks(
                subsection_id, rewritten_path, check_status,
                has_rewritten_text, meets_expansion_floor,
                has_paper_triage, triages_all_packet_papers,
                has_citation_register, citation_register_traceable,
                has_inline_citations, inline_citations_registered,
                registered_citations_used, acknowledges_full_text_sources,
                has_structured_evidence_details,
                allowed_triage_roles, allowed_support_statuses, uses_packet_papers,
                has_residual_uncertainty, no_new_untraced_citations, notes, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                check["subsection_id"],
                check["rewritten_path"],
                check["check_status"],
                int(check["has_rewritten_text"]),
                int(check["meets_expansion_floor"]),
                int(check["has_paper_triage"]),
                int(check["triages_all_packet_papers"]),
                int(check["has_citation_register"]),
                int(check["citation_register_traceable"]),
                int(check["has_inline_citations"]),
                int(check["inline_citations_registered"]),
                int(check["registered_citations_used"]),
                int(check["acknowledges_full_text_sources"]),
                int(check["has_structured_evidence_details"]),
                int(check["allowed_triage_roles"]),
                int(check["allowed_support_statuses"]),
                int(check["uses_packet_papers"]),
                int(check["has_residual_uncertainty"]),
                int(check["no_new_untraced_citations"]),
                check["notes"],
                now,
            ),
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
            "subsection_rewrite",
            status,
            now,
            now if status == "complete" else "",
            "pending_validation",
            f"Stage 8 rewrite checks passed for {passed}/{len(check_rows)} subsections.",
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

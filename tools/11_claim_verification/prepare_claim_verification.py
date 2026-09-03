#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_workflow_control"))

from workflow_state import connect, timestamp


STAGE_DIR = Path("artifacts/10_claim_verification")
INPUT_DIR = STAGE_DIR / "01_inputs"
WORK_ORDER_DIR = STAGE_DIR / "02_work_orders"
REVIEW_DIR = STAGE_DIR / "03_claim_reviews"
VERIFY_DIR = STAGE_DIR / "04_verification"
OUTPUT_DIR = STAGE_DIR / "05_outputs"

ASSEMBLED_REVIEW = Path("drafts/assembled_review.md")
PAPER_MANIFEST = Path("artifacts/05_full_text_rag_index/01_chunks/paper_manifest.csv")

CLAIM_FIELDS = [
    "claim_id",
    "subsection_id",
    "chapter_title",
    "subsection_title",
    "claim_text",
    "cited_paper_ids",
    "citation_ids",
    "work_order_path",
    "review_path",
    "verification_status",
    "notes",
]

CHECK_FIELDS = [
    "check_name",
    "check_status",
    "observed_value",
    "notes",
]

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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare claim-level verification work orders from the assembled review."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    with connect(run_dir) as connection:
        if not stage10_complete(connection):
            print("ERROR: Stage 10 review assembly must be complete and validation-passed first.", file=sys.stderr)
            return 1
        ensure_dirs(run_dir)
        write_stage_readme(run_dir)
        assembled = (run_dir / ASSEMBLED_REVIEW).read_text(encoding="utf-8")
        paper_manifest = load_paper_manifest(run_dir / PAPER_MANIFEST)
        subsection_blocks = extract_subsection_blocks(assembled)
        claims = extract_claims(assembled)
        if not claims:
            print("ERROR: no citation-bearing claims found in assembled review.", file=sys.stderr)
            return 1
        claims_by_subsection: dict[str, list[dict[str, str]]] = defaultdict(list)
        for claim in claims:
            claims_by_subsection[claim["subsection_id"]].append(claim)
        for subsection_id, rows in sorted(claims_by_subsection.items()):
            write_work_order(run_dir, subsection_id, rows, paper_manifest, subsection_blocks.get(subsection_id, ""))
        write_csv(run_dir / INPUT_DIR / "claim_manifest.csv", CLAIM_FIELDS, claims)
        setup_checks = setup_check_rows(claims, claims_by_subsection)
        write_csv(run_dir / VERIFY_DIR / "claim_verification_setup_check.csv", CHECK_FIELDS, setup_checks)
        write_summary(run_dir, claims, setup_checks, status="prepared")
        write_sqlite(connection, claims, setup_checks, status="prepared")

    failed = [row for row in setup_checks if row["check_status"] != "pass"]
    if failed:
        print(f"Stage 11 claim verification setup incomplete: passed={len(setup_checks)-len(failed)} failed={len(failed)}", file=sys.stderr)
        return 2
    print(f"Stage 11 claim verification prepared: claims={len(claims)} subsections={len(claims_by_subsection)}")
    return 0


def stage10_complete(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        """
        SELECT status, validation_status
        FROM workflow_steps
        WHERE step_name = 'review_assembly'
        """
    ).fetchone()
    return bool(row and row["status"] == "complete" and row["validation_status"] == "passed")


def ensure_dirs(run_dir: Path) -> None:
    for directory in (INPUT_DIR, WORK_ORDER_DIR, REVIEW_DIR, VERIFY_DIR, OUTPUT_DIR):
        (run_dir / directory).mkdir(parents=True, exist_ok=True)


def write_stage_readme(run_dir: Path) -> None:
    (run_dir / STAGE_DIR / "README.md").write_text(
        "# Claim Verification Artifacts\n\n"
        "This stage verifies citation-bearing claims from the assembled review "
        "against the cited paper evidence. Preparation extracts claims and "
        "creates work orders. Review agents then write claim-review CSV files, "
        "which are checked before any corrective rewrite begins.\n\n"
        "- `01_inputs/`: extracted claim manifest.\n"
        "- `02_work_orders/`: one claim-verification work order per subsection.\n"
        "- `03_claim_reviews/`: one reviewed CSV per subsection.\n"
        "- `04_verification/`: setup and completion checks.\n"
        "- `05_outputs/`: compact claim-verification summary.\n",
        encoding="utf-8",
    )


def extract_claims(text: str) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    chapter_title = ""
    subsection_title = ""
    subsection_id = ""
    in_register_or_uncertainty = False
    prose_lines: list[str] = []
    claim_counters: dict[str, int] = defaultdict(int)
    citation_registers: dict[str, dict[str, str]] = {}
    lines = text.splitlines()
    for line in lines + ["## END"]:
        if line.startswith("## ") and not line.startswith("### "):
            if subsection_id:
                claims.extend(claims_from_prose(prose_lines, subsection_id, chapter_title, subsection_title, citation_registers.get(subsection_id, {}), claim_counters))
            chapter_title = line.removeprefix("## ").strip()
            subsection_title = ""
            subsection_id = ""
            prose_lines = []
            in_register_or_uncertainty = False
            continue
        if line.startswith("### "):
            if subsection_id:
                claims.extend(claims_from_prose(prose_lines, subsection_id, chapter_title, subsection_title, citation_registers.get(subsection_id, {}), claim_counters))
            subsection_title = line.removeprefix("### ").strip()
            subsection_id = ""
            prose_lines = []
            in_register_or_uncertainty = False
            continue
        marker = re.search(r"source_subsection_id: (SUB\d{3})", line)
        if marker:
            subsection_id = marker.group(1)
            continue
        if line.strip() == "#### Citation Register":
            in_register_or_uncertainty = True
            continue
        if line.strip() == "#### Residual Uncertainty":
            in_register_or_uncertainty = True
            continue
        if subsection_id and in_register_or_uncertainty and line.startswith("| ") and not line.startswith("| ---") and not line.startswith("| citation_id"):
            cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 2:
                citation_registers.setdefault(subsection_id, {})[cells[1]] = cells[0]
            continue
        if subsection_id and not in_register_or_uncertainty:
            prose_lines.append(line)
    return claims


def extract_subsection_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    current_id = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## ") and not line.startswith("### "):
            if current_id:
                blocks[current_id] = "\n".join(current_lines).strip()
            current_id = ""
            current_lines = []
            continue
        if line.startswith("### "):
            if current_id:
                blocks[current_id] = "\n".join(current_lines).strip()
            current_id = ""
            current_lines = [line]
            continue
        marker = re.search(r"source_subsection_id: (SUB\d{3})", line)
        if marker:
            current_id = marker.group(1)
        if current_lines:
            current_lines.append(line)
    if current_id:
        blocks[current_id] = "\n".join(current_lines).strip()
    return blocks


def claims_from_prose(
    lines: list[str],
    subsection_id: str,
    chapter_title: str,
    subsection_title: str,
    citation_register: dict[str, str],
    counters: dict[str, int],
) -> list[dict[str, str]]:
    text = " ".join(line.strip() for line in lines if line.strip())
    sentences = split_sentences(text)
    rows = []
    for sentence in sentences:
        paper_ids = sorted(set(re.findall(r"`(pmid-\d+|doi-[A-Za-z0-9._-]+|paper-[A-Za-z0-9._-]+)`", sentence)))
        if not paper_ids:
            continue
        counters[subsection_id] += 1
        claim_id = f"{subsection_id}-CL{counters[subsection_id]:03d}"
        citation_ids = [citation_register.get(paper_id, "") for paper_id in paper_ids]
        review_path = REVIEW_DIR / f"{subsection_id}.csv"
        work_order_path = WORK_ORDER_DIR / f"{subsection_id}.md"
        rows.append(
            {
                "claim_id": claim_id,
                "subsection_id": subsection_id,
                "chapter_title": chapter_title,
                "subsection_title": subsection_title,
                "claim_text": sentence.strip(),
                "cited_paper_ids": "; ".join(paper_ids),
                "citation_ids": "; ".join(citation_id for citation_id in citation_ids if citation_id),
                "work_order_path": work_order_path.as_posix(),
                "review_path": review_path.as_posix(),
                "verification_status": "not_reviewed",
                "notes": "Extracted from assembled review citation-bearing prose.",
            }
        )
    return rows


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text) if part.strip()]


def write_work_order(
    run_dir: Path,
    subsection_id: str,
    claims: list[dict[str, str]],
    paper_manifest: dict[str, dict[str, str]],
    subsection_block: str,
) -> None:
    cited_paper_ids = sorted({paper_id for claim in claims for paper_id in split_semicolon(claim["cited_paper_ids"])})
    source_lines = [
        "| paper_id | PMID | source_format | normalized_path |",
        "| --- | --- | --- | --- |",
    ]
    for paper_id in cited_paper_ids:
        row = paper_manifest.get(paper_id, {})
        source_lines.append(
            "| "
            + " | ".join(
                [
                    f"`{paper_id}`",
                    f"`{row.get('pmid', '')}`" if row.get("pmid") else "",
                    row.get("source_format", ""),
                    f"`{row.get('normalized_path', '')}`" if row.get("normalized_path") else "",
                ]
            )
            + " |"
        )
    claim_lines = [
        "| claim_id | cited_paper_ids | citation_ids | claim_text |",
        "| --- | --- | --- | --- |",
    ]
    for claim in claims:
        claim_lines.append(
            "| "
            + " | ".join(
                [
                    claim["claim_id"],
                    claim["cited_paper_ids"],
                    claim["citation_ids"],
                    sanitize_table_cell(claim["claim_text"]),
                ]
            )
            + " |"
        )
    path = run_dir / WORK_ORDER_DIR / f"{subsection_id}.md"
    output_path = run_dir / REVIEW_DIR / f"{subsection_id}.csv"
    path.write_text(
        f"# Claim Verification Work Order: {subsection_id}\n\n"
        "## Task\n\n"
        "Verify each claim against its cited paper evidence. Use citation-register "
        "metadata and normalized narrative full text when available. Do not rely "
        "on model memory. Do not add new claims.\n\n"
        "## Required Output Path\n\n"
        f"`{output_path}`\n\n"
        "## Required CSV Header\n\n"
        "```csv\n"
        + ",".join(REVIEW_FIELDS)
        + "\n```\n\n"
        "## Allowed Verification Statuses\n\n"
        "- `supported`\n"
        "- `partially_supported`\n"
        "- `overgeneralized`\n"
        "- `contradicted`\n"
        "- `citation_mismatch`\n"
        "- `citation_missing`\n"
        "- `insufficient_evidence`\n"
        "- `remove`\n\n"
        "## Review Rules\n\n"
        "- Check the exact claim text, not the surrounding topic.\n"
        "- Judge only against the listed cited papers for that claim.\n"
        "- Read normalized narrative full text for cited papers when available.\n"
        "- Use `corrected_claim` when the original claim is overgeneralized, partially supported, contradicted, mismatched, or insufficiently evidenced.\n"
        "- Keep `evidence_summary` specific enough for a later correction agent.\n"
        "- Do not put unescaped commas in CSV fields unless fields are properly quoted by a CSV writer.\n\n"
        "## Narrative Full Text Sources\n\n"
        + "\n".join(source_lines)
        + "\n\n"
        "## Claims To Verify\n\n"
        + "\n".join(claim_lines)
        + "\n\n"
        "## Assembled Subsection Context\n\n"
        "Use this context to understand wording, but verify each claim only "
        "against its own cited papers.\n\n"
        "```markdown\n"
        f"{subsection_block}\n"
        "```\n"
        + "\n",
        encoding="utf-8",
    )


def setup_check_rows(
    claims: list[dict[str, str]],
    claims_by_subsection: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    return [
        check_row("claim_manifest_populated", bool(claims), str(len(claims)), "Claim manifest is populated."),
        check_row("work_orders_planned", bool(claims_by_subsection), str(len(claims_by_subsection)), "Claim work orders planned by subsection."),
        check_row(
            "all_claims_have_citations",
            all(row["cited_paper_ids"] for row in claims),
            str(sum(1 for row in claims if row["cited_paper_ids"])),
            "Every extracted claim has at least one cited paper ID.",
        ),
        check_row(
            "all_claims_have_review_paths",
            all(row["review_path"] for row in claims),
            str(sum(1 for row in claims if row["review_path"])),
            "Every extracted claim has a target review CSV path.",
        ),
    ]


def check_row(name: str, passed: bool, observed: str, pass_note: str) -> dict[str, str]:
    return {
        "check_name": name,
        "check_status": "pass" if passed else "fail",
        "observed_value": observed,
        "notes": pass_note if passed else f"Check failed: {name}",
    }


def write_summary(run_dir: Path, claims: list[dict[str, str]], check_rows: list[dict[str, str]], status: str) -> None:
    passed = sum(1 for row in check_rows if row["check_status"] == "pass")
    subsection_count = len({row["subsection_id"] for row in claims})
    (run_dir / OUTPUT_DIR / "claim_verification_summary.md").write_text(
        "# Claim Verification Summary\n\n"
        "## Overall Status\n\n"
        f"`{status}`\n\n"
        "## Counts\n\n"
        f"- extracted citation-bearing claims: `{len(claims)}`\n"
        f"- subsections with claims: `{subsection_count}`\n"
        f"- setup checks passed: `{passed}/{len(check_rows)}`\n\n"
        "## Downstream Use\n\n"
        "Run claim verification agents on the work orders, then run "
        "`tools/11_claim_verification/verify_claim_verification.py` and validate this stage before "
        "any corrective rewrite begins.\n",
        encoding="utf-8",
    )


def write_sqlite(
    connection: sqlite3.Connection,
    claims: list[dict[str, str]],
    check_rows: list[dict[str, str]],
    status: str,
) -> None:
    now = timestamp()
    connection.execute("DELETE FROM claim_verification_claims")
    connection.execute("DELETE FROM claim_verification_checks")
    for claim in claims:
        connection.execute(
            """
            INSERT OR REPLACE INTO claim_verification_claims(
                claim_id, subsection_id, chapter_title, subsection_title, claim_text,
                cited_paper_ids, citation_ids, work_order_path, review_path,
                verification_status, corrected_claim, evidence_summary, reviewer_notes, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim["claim_id"],
                claim["subsection_id"],
                claim["chapter_title"],
                claim["subsection_title"],
                claim["claim_text"],
                claim["cited_paper_ids"],
                claim["citation_ids"],
                claim["work_order_path"],
                claim["review_path"],
                "not_reviewed",
                "",
                "",
                claim["notes"],
                now,
            ),
        )
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
            "",
            "pending_validation",
            f"Stage 11 claim verification prepared with {len(claims)} claims; setup checks passed {passed}/{len(check_rows)}.",
        ),
    )
    connection.commit()


def load_paper_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    return {row.get("paper_id", ""): row for row in load_csv(path) if row.get("paper_id", "")}


def split_semicolon(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def sanitize_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


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

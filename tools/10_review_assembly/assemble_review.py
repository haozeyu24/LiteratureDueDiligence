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


STAGE_DIR = Path("artifacts/09_review_assembly")
INPUT_DIR = STAGE_DIR / "01_inputs"
SECTION_DIR = STAGE_DIR / "02_sections"
VERIFY_DIR = STAGE_DIR / "03_verification"
OUTPUT_DIR = STAGE_DIR / "04_outputs"

MANIFEST_PATH = Path("artifacts/07_subsection_rewrite/01_inputs/subsection_rewrite_manifest.csv")
NORMALIZED_DIR = Path("artifacts/08_terminology_normalization/03_normalized_subsections")
DRAFT_OUTPUT = Path("drafts/assembled_review.md")

MANIFEST_FIELDS = [
    "subsection_id",
    "chapter_title",
    "subsection_title",
    "normalized_path",
    "assembled_section_path",
    "citation_count",
    "assembly_status",
    "notes",
]

CHECK_FIELDS = [
    "check_name",
    "check_status",
    "observed_value",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble normalized rewritten subsections into a coherent review draft."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    with connect(run_dir) as connection:
        if not stage9_complete(connection):
            print("ERROR: Stage 9 terminology normalization must be complete and validation-passed first.", file=sys.stderr)
            return 1
        ensure_dirs(run_dir)
        write_stage_readme(run_dir)
        manifest_rows = load_csv(run_dir / MANIFEST_PATH)
        assembly_rows = []
        assembled_by_chapter: dict[str, list[str]] = defaultdict(list)
        for row in manifest_rows:
            subsection_id = row["subsection_id"]
            normalized_path = run_dir / NORMALIZED_DIR / f"{subsection_id}.md"
            if not normalized_path.exists():
                print(f"ERROR: missing normalized subsection: {normalized_path}", file=sys.stderr)
                return 1
            normalized_text = normalized_path.read_text(encoding="utf-8")
            section_text, citation_count = build_assembled_section(row, normalized_text)
            assembled_path = run_dir / SECTION_DIR / f"{subsection_id}.assembled.md"
            assembled_path.write_text(section_text, encoding="utf-8")
            chapter_title = row.get("chapter_title", "")
            assembled_by_chapter[chapter_title].append(section_text)
            assembly_rows.append(
                {
                    "subsection_id": subsection_id,
                    "chapter_title": chapter_title,
                    "subsection_title": row.get("subsection_title", ""),
                    "normalized_path": (NORMALIZED_DIR / f"{subsection_id}.md").as_posix(),
                    "assembled_section_path": assembled_path.relative_to(run_dir).as_posix(),
                    "citation_count": str(citation_count),
                    "assembly_status": "assembled",
                    "notes": "Assembled from normalized Stage 9 subsection without adding new scientific claims.",
                }
            )

        assembled_review = build_review(assembled_by_chapter)
        (run_dir / DRAFT_OUTPUT).parent.mkdir(parents=True, exist_ok=True)
        (run_dir / DRAFT_OUTPUT).write_text(assembled_review, encoding="utf-8")
        write_csv(run_dir / INPUT_DIR / "review_assembly_manifest.csv", MANIFEST_FIELDS, assembly_rows)
        check_rows = check_assembly(run_dir, assembly_rows, assembled_review)
        write_csv(run_dir / VERIFY_DIR / "review_assembly_check.csv", CHECK_FIELDS, check_rows)
        write_summary(run_dir, assembly_rows, check_rows)
        write_sqlite(connection, assembly_rows, check_rows)

    failed = [row for row in check_rows if row["check_status"] != "pass"]
    if failed:
        print(f"Stage 10 review assembly incomplete: passed={len(check_rows)-len(failed)} failed={len(failed)}", file=sys.stderr)
        return 2
    print(f"Stage 10 review assembly complete: sections={len(assembly_rows)}")
    return 0


def stage9_complete(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        """
        SELECT status, validation_status
        FROM workflow_steps
        WHERE step_name = 'terminology_normalization'
        """
    ).fetchone()
    return bool(row and row["status"] == "complete" and row["validation_status"] == "passed")


def ensure_dirs(run_dir: Path) -> None:
    for directory in (INPUT_DIR, SECTION_DIR, VERIFY_DIR, OUTPUT_DIR):
        (run_dir / directory).mkdir(parents=True, exist_ok=True)


def write_stage_readme(run_dir: Path) -> None:
    (run_dir / STAGE_DIR / "README.md").write_text(
        "# Review Assembly Artifacts\n\n"
        "This stage assembles normalized rewritten subsections into a single "
        "review draft. It does not add new scientific claims and does not "
        "perform claim-level verification.\n\n"
        "- `01_inputs/`: assembly manifest.\n"
        "- `02_sections/`: one assembled subsection file per normalized subsection.\n"
        "- `03_verification/`: deterministic assembly checks.\n"
        "- `04_outputs/`: compact assembly summary.\n"
        "- `drafts/assembled_review.md`: assembled review draft for the next stage.\n",
        encoding="utf-8",
    )


def build_assembled_section(row: dict[str, str], normalized_text: str) -> tuple[str, int]:
    subsection_id = row["subsection_id"]
    title = row.get("subsection_title", subsection_id)
    rewritten_text = section_text(normalized_text, "## Rewritten Text")
    citation_register = section_text(normalized_text, "## Citation Register")
    uncertainty = section_text(normalized_text, "## Residual Uncertainty")
    citation_count = len([line for line in citation_register.splitlines() if line.strip().startswith("|")]) - 2
    citation_count = max(citation_count, 0)
    section = (
        f"### {title}\n\n"
        f"<!-- source_subsection_id: {subsection_id} -->\n\n"
        f"{rewritten_text.strip()}\n\n"
        "#### Citation Register\n\n"
        f"{citation_register.strip()}\n\n"
        "#### Residual Uncertainty\n\n"
        f"{uncertainty.strip()}\n"
    )
    return section, citation_count


def build_review(assembled_by_chapter: dict[str, list[str]]) -> str:
    lines = [
        "# Assembled Review Draft",
        "",
        "> This draft is assembled from terminology-normalized subsection rewrites. Claim-level verification has not yet been performed.",
        "",
    ]
    for chapter_title, sections in assembled_by_chapter.items():
        lines.append(f"## {chapter_title}")
        lines.append("")
        lines.extend(sections)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def check_assembly(
    run_dir: Path,
    rows: list[dict[str, str]],
    assembled_review: str,
) -> list[dict[str, str]]:
    checks = []
    checks.append(
        check_row(
            "assembled_review_exists",
            (run_dir / DRAFT_OUTPUT).exists() and len(assembled_review.strip()) >= 1000,
            str(len(assembled_review)),
            "Assembled review exists and is populated.",
        )
    )
    subsection_markers = re.findall(r"source_subsection_id: (SUB\d{3})", assembled_review)
    checks.append(
        check_row(
            "all_subsections_present",
            len(set(subsection_markers)) == len(rows) and len(subsection_markers) == len(rows),
            f"{len(set(subsection_markers))}/{len(rows)}",
            "Every normalized subsection appears exactly once.",
        )
    )
    citation_register_count = assembled_review.count("#### Citation Register")
    checks.append(
        check_row(
            "citation_registers_preserved",
            citation_register_count == len(rows),
            f"{citation_register_count}/{len(rows)}",
            "Each assembled subsection preserves a citation register.",
        )
    )
    uncertainty_count = assembled_review.count("#### Residual Uncertainty")
    checks.append(
        check_row(
            "residual_uncertainty_preserved",
            uncertainty_count == len(rows),
            f"{uncertainty_count}/{len(rows)}",
            "Each assembled subsection preserves residual uncertainty.",
        )
    )
    new_untraced = re.findall(r"new_untraced_citation", assembled_review, flags=re.IGNORECASE)
    checks.append(
        check_row(
            "no_new_untraced_citations",
            not new_untraced,
            str(len(new_untraced)),
            "Assembly did not introduce new untraced citation markers.",
        )
    )
    source_citation_ids = set()
    for row in rows:
        normalized_path = run_dir / row["normalized_path"]
        source_citation_ids.update(citation_ids(normalized_path.read_text(encoding="utf-8")))
    assembled_citation_ids = citation_ids(assembled_review)
    checks.append(
        check_row(
            "citation_ids_preserved",
            source_citation_ids == assembled_citation_ids,
            f"{len(assembled_citation_ids)}/{len(source_citation_ids)}",
            "Assembled draft preserves all citation IDs from normalized subsections.",
        )
    )
    return checks


def check_row(name: str, passed: bool, observed: str, pass_note: str) -> dict[str, str]:
    return {
        "check_name": name,
        "check_status": "pass" if passed else "fail",
        "observed_value": observed,
        "notes": pass_note if passed else f"Check failed: {name}",
    }


def citation_ids(text: str) -> set[str]:
    return set(re.findall(r"\bSUB\d{3}-C\d{3}\b", text))


def write_summary(run_dir: Path, rows: list[dict[str, str]], check_rows: list[dict[str, str]]) -> None:
    passed = sum(1 for row in check_rows if row["check_status"] == "pass")
    status = "complete" if passed == len(check_rows) and check_rows else "incomplete"
    citation_count = sum(int(row["citation_count"]) for row in rows)
    (run_dir / OUTPUT_DIR / "review_assembly_summary.md").write_text(
        "# Review Assembly Summary\n\n"
        "## Overall Status\n\n"
        f"`{status}`\n\n"
        "## Counts\n\n"
        f"- assembled subsections: `{len(rows)}`\n"
        f"- preserved citation-register rows: `{citation_count}`\n"
        f"- assembly checks passed: `{passed}/{len(check_rows)}`\n\n"
        "## Downstream Use\n\n"
        "Use `drafts/assembled_review.md` as the input to claim-level "
        "verification. Do not treat it as final scientific prose until claim "
        "verification and human inspection are complete.\n",
        encoding="utf-8",
    )


def write_sqlite(
    connection: sqlite3.Connection,
    rows: list[dict[str, str]],
    check_rows: list[dict[str, str]],
) -> None:
    now = timestamp()
    connection.execute("DELETE FROM review_assembly_sections")
    connection.execute("DELETE FROM review_assembly_checks")
    for row in rows:
        connection.execute(
            """
            INSERT OR REPLACE INTO review_assembly_sections(
                subsection_id, chapter_title, subsection_title, normalized_path,
                assembled_section_path, citation_count, assembly_status, notes, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["subsection_id"],
                row["chapter_title"],
                row["subsection_title"],
                row["normalized_path"],
                row["assembled_section_path"],
                int(row["citation_count"]),
                row["assembly_status"],
                row["notes"],
                now,
            ),
        )
    for row in check_rows:
        connection.execute(
            """
            INSERT OR REPLACE INTO review_assembly_checks(
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
            "review_assembly",
            status,
            now,
            now if status == "complete" else "",
            "pending_validation",
            f"Stage 10 review assembly checks passed for {passed}/{len(check_rows)} checks.",
        ),
    )
    connection.commit()


def section_text(text: str, heading: str) -> str:
    pattern = re.escape(heading) + r"\n(?P<body>.*?)(?=\n## |\Z)"
    match = re.search(pattern, text, flags=re.DOTALL)
    return match.group("body").strip() if match else ""


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

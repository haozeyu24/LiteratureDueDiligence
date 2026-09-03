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


STAGE_DIR = Path("artifacts/08_terminology_normalization")
INPUT_DIR = STAGE_DIR / "01_inputs"
GLOSSARY_DIR = STAGE_DIR / "02_glossary"
NORMALIZED_DIR = STAGE_DIR / "03_normalized_subsections"
VERIFY_DIR = STAGE_DIR / "04_verification"
OUTPUT_DIR = STAGE_DIR / "05_outputs"

REWRITTEN_DIR = Path("artifacts/07_subsection_rewrite/03_rewritten_subsections")
DEFAULT_ALIAS_OVERRIDE = Path("inputs/terminology_alias_overrides.csv")

GLOSSARY_FIELDS = [
    "entity_id",
    "preferred_name",
    "entity_type",
    "aliases",
    "first_mention_rule",
    "normalization_status",
    "notes",
]

CHECK_FIELDS = [
    "subsection_id",
    "normalized_path",
    "check_status",
    "has_text",
    "applies_known_aliases",
    "preserves_citation_ids",
    "notes",
]

ALIAS_OVERRIDE_FIELDS = [
    "preferred_name",
    "entity_type",
    "aliases",
    "first_mention_rule",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize biomedical entity aliases in Stage 8 rewritten subsections."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    parser.add_argument(
        "--alias-overrides",
        default=None,
        help="Optional CSV path relative to the run directory. Defaults to inputs/terminology_alias_overrides.csv when present.",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    with connect(run_dir) as connection:
        if not stage8_complete(connection):
            print("ERROR: Stage 8 subsection rewrite must be complete and validation-passed first.", file=sys.stderr)
            return 1
        ensure_dirs(run_dir)
        write_stage_readme(run_dir)
        alias_path = resolve_alias_path(run_dir, args.alias_overrides)
        aliases = load_alias_overrides(alias_path)
        if not aliases:
            write_alias_template(run_dir / INPUT_DIR / "terminology_alias_overrides.template.csv")
        rewritten_paths = sorted((run_dir / REWRITTEN_DIR).glob("SUB*.md"))
        rows = build_glossary(aliases)
        check_rows = []
        for source_path in rewritten_paths:
            subsection_id = source_path.stem
            normalized_path = run_dir / NORMALIZED_DIR / source_path.name
            source_text = source_path.read_text(encoding="utf-8")
            normalized_text = apply_aliases(source_text, rows)
            normalized_path.write_text(normalized_text, encoding="utf-8")
            check_rows.append(check_normalization(source_text, normalized_text, subsection_id, normalized_path, run_dir, rows))

        write_csv(run_dir / GLOSSARY_DIR / "terminology_glossary.csv", GLOSSARY_FIELDS, rows)
        write_csv(run_dir / VERIFY_DIR / "terminology_normalization_check.csv", CHECK_FIELDS, check_rows)
        write_summary(run_dir, rows, check_rows, alias_path)
        write_sqlite(connection, rows, check_rows)

    failed = [row for row in check_rows if row["check_status"] != "pass"]
    if failed:
        print(f"Stage 9 terminology normalization incomplete: passed={len(check_rows)-len(failed)} failed={len(failed)}", file=sys.stderr)
        return 2
    print(f"Stage 9 terminology normalization complete: entities={len(rows)} subsections={len(check_rows)}")
    return 0


def stage8_complete(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        """
        SELECT status, validation_status
        FROM workflow_steps
        WHERE step_name = 'subsection_rewrite'
        """
    ).fetchone()
    return bool(row and row["status"] == "complete" and row["validation_status"] == "passed")


def ensure_dirs(run_dir: Path) -> None:
    for directory in (INPUT_DIR, GLOSSARY_DIR, NORMALIZED_DIR, VERIFY_DIR, OUTPUT_DIR):
        (run_dir / directory).mkdir(parents=True, exist_ok=True)


def write_stage_readme(run_dir: Path) -> None:
    (run_dir / STAGE_DIR / "README.md").write_text(
        "# Terminology Normalization Artifacts\n\n"
        "This stage normalizes entity aliases before review assembly. It keeps "
        "the original Stage 8 rewritten subsections unchanged and writes "
        "normalized copies for downstream assembly and claim verification.\n\n"
        "- `01_inputs/`: optional alias override template or copied run-specific input.\n"
        "- `02_glossary/`: machine-readable preferred-name and alias glossary.\n"
        "- `03_normalized_subsections/`: normalized copies of rewritten subsections.\n"
        "- `04_verification/`: per-subsection normalization checks.\n"
        "- `05_outputs/`: compact normalization summary.\n",
        encoding="utf-8",
    )


def resolve_alias_path(run_dir: Path, explicit: str | None) -> Path | None:
    if explicit:
        return run_dir / explicit
    default = run_dir / DEFAULT_ALIAS_OVERRIDE
    return default if default.exists() else None


def write_alias_template(path: Path) -> None:
    write_csv(path, ALIAS_OVERRIDE_FIELDS, [])


def load_alias_overrides(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    rows = load_csv(path)
    missing = set(ALIAS_OVERRIDE_FIELDS) - set(rows[0].keys() if rows else ALIAS_OVERRIDE_FIELDS)
    if missing:
        raise SystemExit(f"Alias override CSV missing columns: {', '.join(sorted(missing))}")
    return rows


def build_glossary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    glossary = []
    for index, row in enumerate(rows, start=1):
        preferred = row.get("preferred_name", "").strip()
        aliases = normalize_alias_list(row.get("aliases", ""))
        if not preferred or not aliases:
            continue
        glossary.append(
            {
                "entity_id": f"ENT{index:04d}",
                "preferred_name": preferred,
                "entity_type": row.get("entity_type", "unknown").strip() or "unknown",
                "aliases": "; ".join(aliases),
                "first_mention_rule": row.get("first_mention_rule", "").strip()
                or f"Use {preferred} as preferred name; clarify aliases at first relevant mention.",
                "normalization_status": "active",
                "notes": row.get("notes", "").strip(),
            }
        )
    return glossary


def normalize_alias_list(raw: str) -> list[str]:
    aliases = [alias.strip() for alias in re.split(r"[;|]", raw) if alias.strip()]
    deduped = []
    for alias in aliases:
        if alias not in deduped:
            deduped.append(alias)
    return deduped


def apply_aliases(text: str, glossary: list[dict[str, str]]) -> str:
    protected: list[str] = []

    def protect(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"@@PROTECTED{len(protected)-1}@@"

    working = re.sub(r"`[^`]+`", protect, text)
    working = re.sub(r"https?://\S+", protect, working)
    for row in glossary:
        preferred = row["preferred_name"]
        for alias in sorted(normalize_alias_list(row["aliases"]), key=len, reverse=True):
            if alias.lower() == preferred.lower():
                continue
            working = replace_alias(working, alias, preferred)
    for index, value in enumerate(protected):
        working = working.replace(f"@@PROTECTED{index}@@", value)
    return working


def replace_alias(text: str, alias: str, preferred: str) -> str:
    pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])")
    return pattern.sub(preferred, text)


def check_normalization(
    source_text: str,
    normalized_text: str,
    subsection_id: str,
    normalized_path: Path,
    run_dir: Path,
    glossary: list[dict[str, str]],
) -> dict[str, str]:
    has_text = len(normalized_text.strip()) >= 500
    applies_known_aliases = True
    for row in glossary:
        preferred = row["preferred_name"]
        for alias in normalize_alias_list(row["aliases"]):
            if alias.lower() == preferred.lower():
                continue
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", normalized_text):
                applies_known_aliases = False
    source_citations = set(re.findall(r"`(pmid-\d+|doi-[A-Za-z0-9._-]+|paper-[A-Za-z0-9._-]+)`", source_text))
    normalized_citations = set(re.findall(r"`(pmid-\d+|doi-[A-Za-z0-9._-]+|paper-[A-Za-z0-9._-]+)`", normalized_text))
    preserves_citation_ids = source_citations == normalized_citations
    checks = {
        "has_text": has_text,
        "applies_known_aliases": applies_known_aliases,
        "preserves_citation_ids": preserves_citation_ids,
    }
    notes = []
    if not has_text:
        notes.append("normalized subsection is missing or too small")
    if not applies_known_aliases:
        notes.append("one or more active aliases remain after normalization")
    if not preserves_citation_ids:
        notes.append("citation IDs changed during terminology normalization")
    return {
        "subsection_id": subsection_id,
        "normalized_path": normalized_path.relative_to(run_dir).as_posix(),
        "check_status": "pass" if all(checks.values()) else "fail",
        **{key: "1" if value else "0" for key, value in checks.items()},
        "notes": "; ".join(notes) if notes else "All deterministic terminology checks passed.",
    }


def write_summary(
    run_dir: Path,
    glossary_rows: list[dict[str, str]],
    check_rows: list[dict[str, str]],
    alias_path: Path | None,
) -> None:
    passed = sum(1 for row in check_rows if row["check_status"] == "pass")
    status = "complete" if passed == len(check_rows) and check_rows else "incomplete"
    (run_dir / OUTPUT_DIR / "terminology_normalization_summary.md").write_text(
        "# Terminology Normalization Summary\n\n"
        "## Overall Status\n\n"
        f"`{status}`\n\n"
        "## Counts\n\n"
        f"- active glossary entities: `{len(glossary_rows)}`\n"
        f"- normalized subsections checked: `{len(check_rows)}`\n"
        f"- normalization checks passed: `{passed}`\n\n"
        "## Alias Source\n\n"
        f"`{alias_path.relative_to(run_dir).as_posix() if alias_path else 'none; template created'}`\n\n"
        "## Downstream Use\n\n"
        "Use normalized subsection copies for assembly and claim-level "
        "verification. Keep original Stage 8 rewritten files unchanged for audit.\n",
        encoding="utf-8",
    )


def write_sqlite(
    connection: sqlite3.Connection,
    glossary_rows: list[dict[str, str]],
    check_rows: list[dict[str, str]],
) -> None:
    now = timestamp()
    connection.execute("DELETE FROM terminology_entities")
    connection.execute("DELETE FROM terminology_normalization_checks")
    for row in glossary_rows:
        connection.execute(
            """
            INSERT OR REPLACE INTO terminology_entities(
                entity_id, preferred_name, entity_type, aliases,
                first_mention_rule, normalization_status, notes, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["entity_id"],
                row["preferred_name"],
                row["entity_type"],
                row["aliases"],
                row["first_mention_rule"],
                row["normalization_status"],
                row["notes"],
                now,
            ),
        )
    for row in check_rows:
        connection.execute(
            """
            INSERT OR REPLACE INTO terminology_normalization_checks(
                subsection_id, normalized_path, check_status,
                has_text, applies_known_aliases, preserves_citation_ids,
                notes, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["subsection_id"],
                row["normalized_path"],
                row["check_status"],
                int(row["has_text"]),
                int(row["applies_known_aliases"]),
                int(row["preserves_citation_ids"]),
                row["notes"],
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
            "terminology_normalization",
            status,
            now,
            now if status == "complete" else "",
            "pending_validation",
            f"Stage 9 terminology checks passed for {passed}/{len(check_rows)} subsections.",
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

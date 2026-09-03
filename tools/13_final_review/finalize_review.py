#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_workflow_control"))

from workflow_state import connect, timestamp


STAGE_DIR = Path("artifacts/12_final_review")
INPUT_DIR = STAGE_DIR / "01_inputs"
OUTPUT_DIR = STAGE_DIR / "02_outputs"
VERIFY_DIR = STAGE_DIR / "03_verification"
SUMMARY_DIR = STAGE_DIR / "04_outputs"
CORRECTED_REVIEW = Path("drafts/corrected_review.md")
FINAL_REVIEW = Path("drafts/final_review.md")
PUBMED_INDEX = Path("artifacts/02_subsection_retrieval/03_pubmed/pubmed_record_index.csv")

MANIFEST_FIELDS = [
    "section_id",
    "section_type",
    "title",
    "source_subsection_id",
    "citation_count",
    "uncertainty_note_count",
    "section_status",
    "notes",
]

CHECK_FIELDS = ["check_name", "check_status", "observed_value", "notes"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create the final reader-facing review while preserving verified evidence traceability."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    corrected_path = run_dir / CORRECTED_REVIEW
    if not corrected_path.exists():
        raise SystemExit(f"Missing corrected review: {corrected_path}")

    create_dirs(run_dir)
    write_stage_readme(run_dir)
    source_text = corrected_path.read_text(encoding="utf-8")
    title = infer_title(run_dir)
    chapters = parse_corrected_review(source_text)
    reference_metadata = load_reference_metadata(run_dir)
    final_text, manifest_rows, reference_rows = build_final_review(
        title, chapters, reference_metadata
    )
    check_rows = build_checks(source_text, final_text, manifest_rows, reference_rows)

    (run_dir / FINAL_REVIEW).parent.mkdir(parents=True, exist_ok=True)
    (run_dir / FINAL_REVIEW).write_text(final_text, encoding="utf-8")
    (run_dir / OUTPUT_DIR / "final_review.md").write_text(final_text, encoding="utf-8")
    write_csv(run_dir / OUTPUT_DIR / "references.csv", reference_fields(), reference_rows)
    write_csv(run_dir / INPUT_DIR / "final_review_manifest.csv", MANIFEST_FIELDS, manifest_rows)
    write_csv(run_dir / VERIFY_DIR / "final_review_check.csv", CHECK_FIELDS, check_rows)
    write_summary(run_dir, manifest_rows, check_rows)
    write_sqlite(run_dir, manifest_rows, check_rows)

    failed = [row for row in check_rows if row["check_status"] != "pass"]
    if failed:
        raise SystemExit("Final review has failed checks; inspect final_review_check.csv")

    print(
        "Final review complete: "
        f"{len([row for row in manifest_rows if row['section_type'] == 'subsection'])} subsections; "
        f"written to {run_dir / FINAL_REVIEW}"
    )
    return 0


def create_dirs(run_dir: Path) -> None:
    for directory in (INPUT_DIR, OUTPUT_DIR, VERIFY_DIR, SUMMARY_DIR):
        (run_dir / directory).mkdir(parents=True, exist_ok=True)


def write_stage_readme(run_dir: Path) -> None:
    text = """# Final Review Artifacts

Stage 13 creates a reader-facing final review from the corrected review draft.
It performs editorial organization, replaces workflow paper IDs with numbered
citations, writes a deduplicated reference list, and validates citation
traceability.

Folders:

- `01_inputs`: final review section manifest
- `02_outputs`: final review copy and deduplicated references
- `03_verification`: deterministic final-review checks
- `04_outputs`: final-stage summary
"""
    (run_dir / STAGE_DIR / "README.md").write_text(text, encoding="utf-8")


def infer_title(run_dir: Path) -> str:
    structured = run_dir / "inputs/structured_instruction.md"
    if not structured.exists():
        return "Final Literature Review"
    text = structured.read_text(encoding="utf-8")
    match = re.search(r"^- objective:\s*(.+)$", text, flags=re.MULTILINE)
    if not match:
        return "Final Literature Review"
    objective = match.group(1).strip()
    review_match = re.search(r"review (?:on|of)\s+(.+?)(?:,\s+spanning|,\s+with|\.|$)", objective, flags=re.IGNORECASE)
    if review_match:
        topic = review_match.group(1).strip()
        topic = topic[0].upper() + topic[1:] if topic else topic
        return topic
    return "Final Literature Review"


def parse_corrected_review(source_text: str) -> list[dict]:
    chapters: list[dict] = []
    current_chapter: dict | None = None
    current_subsection: dict | None = None
    current_part = "prose"

    for line in source_text.splitlines():
        if line.startswith("# "):
            continue
        if line.startswith("> "):
            continue
        if line.startswith("## "):
            current_chapter = {"title": clean_heading(line[3:]), "subsections": []}
            chapters.append(current_chapter)
            current_subsection = None
            current_part = "prose"
            continue
        if line.startswith("### "):
            if current_chapter is None:
                current_chapter = {"title": "Review", "subsections": []}
                chapters.append(current_chapter)
            current_subsection = {
                "title": clean_heading(line[4:]),
                "source_subsection_id": "",
                "prose": [],
                "register": [],
                "uncertainty": [],
            }
            current_chapter["subsections"].append(current_subsection)
            current_part = "prose"
            continue
        if current_subsection is None:
            continue
        source_match = re.search(r"source_subsection_id:\s*(SUB\d{3})", line)
        if source_match:
            current_subsection["source_subsection_id"] = source_match.group(1)
            continue
        if line.startswith("#### Citation Register"):
            current_part = "register"
            continue
        if line.startswith("#### Residual Uncertainty"):
            current_part = "uncertainty"
            continue
        current_subsection[current_part].append(line)

    return chapters


def clean_heading(text: str) -> str:
    text = text.strip()
    return re.sub(r"^\d+:\s*", "", text)


def load_reference_metadata(run_dir: Path) -> dict[str, dict[str, str]]:
    path = run_dir / PUBMED_INDEX
    metadata: dict[str, dict[str, str]] = {}
    if not path.exists():
        return metadata
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            paper_id = row.get("paper_id", "").strip()
            if not paper_id:
                pmid = row.get("PMID", "").strip()
                paper_id = f"pmid-{pmid}" if pmid else ""
            if not paper_id:
                continue
            metadata[paper_id] = {
                "paper_id": paper_id,
                "authors": "",
                "PMID": row.get("PMID", "").strip(),
                "PMCID": row.get("PMCID", "").strip(),
                "DOI": row.get("DOI", "").strip(),
                "title": row.get("title", "").strip(),
                "journal": row.get("journal", "").strip(),
                "publication_year": row.get("publication_year", "").strip(),
                "publication_types": row.get("publication_types", "").strip(),
            }
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    if sqlite_path.exists():
        with sqlite3.connect(sqlite_path) as connection:
            connection.row_factory = sqlite3.Row
            for row in connection.execute("SELECT paper_id, authors_json FROM pubmed_records"):
                paper_id = row["paper_id"]
                if paper_id not in metadata:
                    metadata[paper_id] = {"paper_id": paper_id}
                metadata[paper_id]["authors"] = format_authors(row["authors_json"])
    return metadata


def format_authors(authors_json: str) -> str:
    try:
        authors = json.loads(authors_json)
    except json.JSONDecodeError:
        return ""
    if not isinstance(authors, list):
        return ""
    names = [str(author).strip() for author in authors if str(author).strip()]
    if not names:
        return ""
    if len(names) <= 6:
        return ", ".join(names)
    return ", ".join(names[:3]) + ", et al."


def build_final_review(
    title: str, chapters: list[dict], reference_metadata: dict[str, dict[str, str]]
) -> tuple[str, list[dict[str, str]], list[dict[str, str]]]:
    manifest_rows: list[dict[str, str]] = []
    reference_order: list[str] = []
    reference_numbers: dict[str, int] = {}
    lines: list[str] = []
    lines.extend(
        [
            f"# {title}",
            "",
            "## Abstract",
            "",
            build_abstract(title, chapters),
            "",
            "## Main Review",
            "",
        ]
    )
    manifest_rows.append(section_row("FRONT-ABSTRACT", "front_matter", "Abstract", "", 0, 0, "assembled", "Generated from structured objective and chapter map."))

    for chapter_index, chapter in enumerate(chapters, start=1):
        lines.append(f"### {chapter_index}. {chapter['title']}")
        lines.append("")
        manifest_rows.append(section_row(f"CH{chapter_index:02d}", "chapter", chapter["title"], "", 0, 0, "assembled", "Chapter heading preserved from corrected review."))
        for subsection in chapter["subsections"]:
            source_id = subsection.get("source_subsection_id", "")
            lines.append(f"#### {subsection['title']}")
            lines.append("")
            prose = polish_prose("\n".join(subsection["prose"]).strip())
            prose = replace_paper_ids_with_numbered_citations(
                prose, reference_order, reference_numbers
            )
            prose = remove_workflow_citation_ids(prose)
            lines.append(prose)
            lines.append("")
            manifest_rows.append(
                section_row(
                    source_id or f"SUBX-{len(manifest_rows):03d}",
                    "subsection",
                    subsection["title"],
                    source_id,
                    str(count_register_rows(subsection["register"])),
                    str(count_uncertainty_notes(subsection["uncertainty"])),
                    "assembled",
                    "Reader-facing subsection prose preserved and lightly polished from corrected review.",
                )
            )

    lines.extend(
        [
            "## Synthesis For Human Inspection",
            "",
            build_human_inspection_synthesis(chapters),
            "",
            "## References",
            "",
        ]
    )
    manifest_rows.append(section_row("BACK-HUMAN-INSPECTION", "back_matter", "Synthesis For Human Inspection", "", 0, 0, "assembled", "Consolidates uncertainty notes for human review."))
    manifest_rows.append(section_row("BACK-REFERENCES", "back_matter", "References", "", len(reference_order), 0, "assembled", "Deduplicated numbered reference list."))

    reference_rows = build_reference_rows(reference_order, reference_metadata)
    for row in reference_rows:
        lines.append(format_reference(row))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n", manifest_rows, reference_rows


def replace_paper_ids_with_numbered_citations(
    text: str, reference_order: list[str], reference_numbers: dict[str, int]
) -> str:
    def replace_group(match: re.Match[str]) -> str:
        paper_ids = re.findall(r"pmid-\d+|PAPER-\d+", match.group(0))
        numbers = []
        for paper_id in paper_ids:
            if paper_id not in reference_numbers:
                reference_numbers[paper_id] = len(reference_order) + 1
                reference_order.append(paper_id)
            numbers.append(reference_numbers[paper_id])
        return format_citation_numbers(numbers)

    text = re.sub(r"`([^`]*(?:pmid-\d+|PAPER-\d+)[^`]*)`", replace_group, text)
    return re.sub(r"(?:\[\d+(?:,\d+)*\]\s*){2,}", merge_adjacent_numbered_citations, text)


def merge_adjacent_numbered_citations(match: re.Match[str]) -> str:
    numbers = [int(value) for value in re.findall(r"\d+", match.group(0))]
    return format_citation_numbers(numbers)


def remove_workflow_citation_ids(text: str) -> str:
    text = re.sub(r"\s*`[^`]*(?:SUB|S)\d{2,3}-[CR]\d{3}[^`]*`", "", text)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    return text


def format_citation_numbers(numbers: list[int]) -> str:
    unique = sorted(dict.fromkeys(numbers))
    return "[" + ",".join(str(number) for number in unique) + "]"


def build_reference_rows(
    reference_order: list[str], metadata: dict[str, dict[str, str]]
) -> list[dict[str, str]]:
    rows = []
    for index, paper_id in enumerate(reference_order, start=1):
        row = metadata.get(paper_id, {})
        pmid_from_id = paper_id.removeprefix("pmid-") if paper_id.startswith("pmid-") else ""
        rows.append(
            {
                "reference_number": str(index),
                "paper_id": paper_id,
                "authors": row.get("authors", ""),
                "PMID": row.get("PMID", pmid_from_id),
                "PMCID": row.get("PMCID", ""),
                "DOI": row.get("DOI", ""),
                "title": row.get("title", ""),
                "journal": row.get("journal", ""),
                "publication_year": row.get("publication_year", ""),
                "publication_types": row.get("publication_types", ""),
            }
        )
    return rows


def reference_fields() -> list[str]:
    return [
        "reference_number",
        "paper_id",
        "authors",
        "PMID",
        "PMCID",
        "DOI",
        "title",
        "journal",
        "publication_year",
        "publication_types",
    ]


def format_reference(row: dict[str, str]) -> str:
    parts = [
        f"[{row['reference_number']}]",
    ]
    if row.get("authors", ""):
        parts.append(ensure_terminal_period(row["authors"]))
    parts.append(row.get("title", "") or row.get("paper_id", ""))
    journal = row.get("journal", "")
    year = row.get("publication_year", "")
    if journal or year:
        parts.append(f"{journal}. {year}.".strip())
    pmid = row.get("PMID", "")
    pmcid = row.get("PMCID", "")
    doi = row.get("DOI", "")
    identifiers = []
    if pmid:
        identifiers.append(f"PMID: {pmid}")
    if pmcid:
        identifiers.append(f"PMCID: {pmcid}")
    if doi and doi.lower() != "unknown":
        identifiers.append(f"DOI: {doi}")
    if identifiers:
        parts.append("; ".join(identifiers) + ".")
    return " ".join(part for part in parts if part).strip()


def ensure_terminal_period(text: str) -> str:
    text = text.strip()
    if not text:
        return text
    if text.endswith((".", "!", "?")):
        return text
    return text + "."


def build_abstract(title: str, chapters: list[dict]) -> str:
    chapter_titles = [chapter["title"] for chapter in chapters]
    subsection_titles = [
        subsection["title"]
        for chapter in chapters
        for subsection in chapter["subsections"]
    ]
    first_clause = (
        f"This review synthesizes verified evidence on {title[0].lower() + title[1:]}"
        if title != "Final Literature Review"
        else "This review synthesizes verified evidence for the user-defined biomedical review topic"
    )
    return (
        f"{first_clause}. It is organized around {serial_phrase(chapter_titles)}. "
        "The final interpretation emphasizes mechanism-specific evidence, clinical context, "
        "trial feasibility, and the difference between direct resistance evidence and useful "
        "biological context. The most important recurring topics are "
        f"{serial_phrase(subsection_titles[:8])}, with additional sections preserving clinical "
        "trial interpretation, biomarker strategy, and verification priorities. Claims are "
        "linked to a deduplicated numbered reference list, with detailed audit registers "
        "preserved in upstream workflow artifacts."
    )


def build_orientation(chapters: list[dict]) -> str:
    chapter_count = len(chapters)
    subsection_count = sum(len(chapter["subsections"]) for chapter in chapters)
    return (
        "This final pass converts the corrected, claim-verified draft into a reader-facing "
        "review. The main text is meant to be read continuously, with workflow paper IDs "
        "converted to numbered citations and detailed audit registers preserved upstream. The result is "
        f"structured into {chapter_count} chapters and {subsection_count} subsections. "
        "Interpretation should remain conservative where evidence is preclinical, indirect, "
        "or dependent on small clinical subgroups."
    )


def build_human_inspection_synthesis(chapters: list[dict]) -> str:
    notes = []
    for chapter in chapters:
        for subsection in chapter["subsections"]:
            uncertainty = polish_prose("\n".join(subsection["uncertainty"]).strip())
            if uncertainty:
                notes.append(f"{subsection['title']}: {uncertainty}")
    if not notes:
        return "No residual uncertainty notes were captured, but human scientific inspection remains required before external use."
    selected = notes[:10]
    text = (
        "Human inspection should focus on places where the evidence boundary matters most: "
        "claims extrapolated across model systems, trial settings, drug generations, or patient "
        "subgroups; claims based on preclinical mechanism without mature clinical confirmation; "
        "and claims where access limitations or heterogeneous specimens leave causal inference "
        "open. Detailed subsection-level uncertainty notes remain in the upstream audit artifacts. Priority examples are: "
    )
    return text + " ".join(selected)


def polish_prose(text: str) -> str:
    replacements = [
        ("The packet", "The evidence set"),
        ("the packet", "the evidence set"),
        ("The work order", "The source draft"),
        ("the work order", "the source draft"),
        ("Later claim verification should", "Interpretation should"),
        ("later claim verification should", "interpretation should"),
        ("Later verification should", "Interpretation should"),
        ("later verification should", "interpretation should"),
        ("later stages should", "human follow-up should"),
        ("Later stages should", "Human follow-up should"),
        ("this subsection should", "this review should"),
        ("This subsection should", "This review should"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def serial_phrase(values: list[str]) -> str:
    cleaned = [value for value in values if value]
    if not cleaned:
        return "the major evidence classes identified in the verified draft"
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return ", ".join(cleaned[:-1]) + f", and {cleaned[-1]}"


def trim_blank_edges(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def count_register_rows(lines: list[str]) -> int:
    count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(set(cell) <= {"-"} for cell in cells if cell):
            continue
        if cells and cells[0] == "citation_id":
            continue
        count += 1
    return count


def count_uncertainty_notes(lines: list[str]) -> int:
    text = "\n".join(lines).strip()
    if not text:
        return 0
    return max(1, len(re.findall(r"\.\s+", text)))


def section_row(
    section_id: str,
    section_type: str,
    title: str,
    source_subsection_id: str,
    citation_count: str | int,
    uncertainty_note_count: str | int,
    section_status: str,
    notes: str,
) -> dict[str, str]:
    return {
        "section_id": section_id,
        "section_type": section_type,
        "title": title,
        "source_subsection_id": source_subsection_id,
        "citation_count": str(citation_count),
        "uncertainty_note_count": str(uncertainty_note_count),
        "section_status": section_status,
        "notes": notes,
    }


def build_checks(
    source_text: str,
    final_text: str,
    manifest_rows: list[dict[str, str]],
    reference_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    checks = []
    source_citation_ids = citation_like_ids(source_text)
    final_citation_ids = citation_like_ids(final_text)
    source_paper_ids = paper_ids(main_prose_source(source_text))
    final_reference_ids = {row["paper_id"] for row in reference_rows}
    new_citations = sorted(final_citation_ids - source_citation_ids)
    raw_paper_ids_left = sorted(paper_ids(main_text_before_references(final_text)))
    workflow_citation_ids_left = sorted(citation_like_ids(main_text_before_references(final_text)))
    missing_papers = sorted(source_paper_ids - final_reference_ids)
    extra_reference_ids = sorted(final_reference_ids - source_paper_ids)
    checks.append(check_row("final_review_populated", len(final_text.strip()) >= 1000, str(len(final_text.encode("utf-8"))), "Final review is populated."))
    checks.append(check_row("has_required_reader_sections", all(marker in final_text for marker in ("## Abstract", "## Main Review", "## References")), "present", "Final review includes required reader-facing sections."))
    checks.append(check_row("no_orientation_section", "## Orientation" not in final_text, "absent", "Final review does not include workflow-oriented orientation prose."))
    checks.append(check_row("has_references", "## References" in final_text, "present" if "## References" in final_text else "missing", "Deduplicated reference list is present."))
    checks.append(check_row("no_evidence_appendix_in_final", "## Evidence Appendix" not in final_text and "##### Citation Register" not in final_text, "absent", "Final review does not include oversized audit appendix."))
    checks.append(check_row("no_stale_claim_verification_warning", "Claim-level verification has not yet been performed" not in final_text, "absent", "Stale assembly warning removed."))
    checks.append(check_row("no_source_html_comments", "<!-- source_subsection_id:" not in final_text, "absent", "Source comments removed from reader-facing draft."))
    checks.append(check_row("no_new_untraced_citations", not new_citations, str(len(new_citations)), ";".join(new_citations) if new_citations else "No new citation IDs introduced."))
    checks.append(check_row("no_workflow_citation_ids_in_main_text", not workflow_citation_ids_left, str(len(workflow_citation_ids_left)), ";".join(workflow_citation_ids_left) if workflow_citation_ids_left else "Workflow citation IDs were removed from main text."))
    checks.append(check_row("no_raw_paper_ids_in_main_text", not raw_paper_ids_left, str(len(raw_paper_ids_left)), ";".join(raw_paper_ids_left) if raw_paper_ids_left else "Workflow paper IDs were converted to numbered citations."))
    checks.append(check_row("reference_ids_match_main_text_sources", not missing_papers and not extra_reference_ids, f"missing={len(missing_papers)};extra={len(extra_reference_ids)}", "References match deduplicated paper IDs used by source main prose."))
    checks.append(check_row("references_deduplicated", len(final_reference_ids) == len(reference_rows), str(len(reference_rows)), "Reference list has one row per paper ID."))
    checks.append(check_row("references_have_pmids_or_titles", all(row.get("PMID") or row.get("title") for row in reference_rows), str(len(reference_rows)), "Every reference has at least a PMID or title."))
    subsection_rows = [row for row in manifest_rows if row["section_type"] == "subsection"]
    checks.append(check_row("subsection_manifest_populated", bool(subsection_rows), str(len(subsection_rows)), "Subsection rows recorded."))
    status_counts = Counter(row["section_status"] for row in manifest_rows)
    checks.append(check_row("section_status_counts_recorded", True, ";".join(f"{key}:{value}" for key, value in sorted(status_counts.items())), "Section status counts recorded."))
    return checks


def main_prose_source(text: str) -> str:
    prose_parts: list[str] = []
    in_register = False
    in_uncertainty = False
    for line in text.splitlines():
        if line.startswith("#### Citation Register"):
            in_register = True
            in_uncertainty = False
            continue
        if line.startswith("#### Residual Uncertainty"):
            in_register = False
            in_uncertainty = True
            continue
        if line.startswith("### ") or line.startswith("## "):
            in_register = False
            in_uncertainty = False
        if not in_register and not in_uncertainty:
            prose_parts.append(line)
    return "\n".join(prose_parts)


def main_text_before_references(text: str) -> str:
    return text.split("\n## References\n", 1)[0]


def check_row(name: str, passed: bool, observed: str, notes: str) -> dict[str, str]:
    return {
        "check_name": name,
        "check_status": "pass" if passed else "fail",
        "observed_value": observed,
        "notes": notes,
    }


def citation_like_ids(text: str) -> set[str]:
    return set(re.findall(r"\b(?:SUB|S)\d{2,3}-[CR]\d{3}\b", text))


def paper_ids(text: str) -> set[str]:
    return set(re.findall(r"\bpmid-\d+\b|\bPAPER-\d+\b", text))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_summary(
    run_dir: Path, manifest_rows: list[dict[str, str]], check_rows: list[dict[str, str]]
) -> None:
    type_counts = Counter(row["section_type"] for row in manifest_rows)
    check_status = "pass" if all(row["check_status"] == "pass" for row in check_rows) else "fail"
    lines = [
        "# Final Review Summary",
        "",
        "## Counts",
        "",
        f"- sections_recorded: {len(manifest_rows)}",
        f"- check_status: {check_status}",
    ]
    for section_type, count in sorted(type_counts.items()):
        lines.append(f"- {section_type}: {count}")
    lines.extend(
        [
            "",
            "## Writer Rule",
            "",
            "The final pass is a reader-facing synthesis over the corrected draft. It may",
            "improve organization, convert workflow paper IDs to numbered citations, and",
            "replace audit-table interruption with a deduplicated reference list.",
            "Detailed evidence registers remain in upstream artifacts.",
            "",
            "## Downstream Use",
            "",
            "Use `drafts/final_review.md` for human scientific inspection, manuscript",
            "polish, or conversion into a deliverable format.",
        ]
    )
    (run_dir / SUMMARY_DIR / "final_review_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def write_sqlite(
    run_dir: Path, manifest_rows: list[dict[str, str]], check_rows: list[dict[str, str]]
) -> None:
    with connect(run_dir) as connection:
        now = timestamp()
        connection.execute("DELETE FROM final_review_sections")
        connection.execute("DELETE FROM final_review_checks")
        for row in manifest_rows:
            connection.execute(
                """
                INSERT INTO final_review_sections(
                    section_id, section_type, title, source_subsection_id,
                    citation_count, uncertainty_note_count, section_status, notes, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["section_id"],
                    row["section_type"],
                    row["title"],
                    row["source_subsection_id"],
                    int(row["citation_count"]),
                    int(row["uncertainty_note_count"]),
                    row["section_status"],
                    row["notes"],
                    now,
                ),
            )
        for row in check_rows:
            connection.execute(
                """
                INSERT INTO final_review_checks(check_name, check_status, observed_value, notes, updated_at)
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
            ("final_review", status, now, now, "not_run", f"{len(manifest_rows)} final review sections recorded."),
        )
        connection.commit()


if __name__ == "__main__":
    raise SystemExit(main())

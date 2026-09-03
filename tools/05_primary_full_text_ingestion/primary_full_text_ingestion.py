#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
import os
import re
import shutil
import sqlite3
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_workflow_control"))

from workflow_state import connect, timestamp


STAGE_DIR = Path("artifacts/04_primary_full_text_ingestion")
TARGET_DIR = STAGE_DIR / "01_targets"
DISCOVERY_DIR = STAGE_DIR / "02_discovery"
PMC_DIR = STAGE_DIR / "03_pmc"
PMC_RAW_DIR = PMC_DIR / "01_raw_xml"
PMC_NORMALIZED_DIR = PMC_DIR / "02_normalized"
PDF_DIR = STAGE_DIR / "04_pdf"
PDF_STAGED_DIR = PDF_DIR / "01_staged"
PDF_GROBID_DIR = PDF_DIR / "02_parser_cache" / "01_grobid"
PDF_NORMALIZED_DIR = PDF_DIR / "03_normalized"
USER_DIR = STAGE_DIR / "05_user_pdf_request"
USER_DROPBOX_DIR = USER_DIR / "01_user_pdf_dropbox"
OUTPUT_DIR = STAGE_DIR / "06_outputs"

NCBI_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
EUROPE_PMC_XML_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
OPENALEX_WORKS_URL = "https://api.openalex.org/works/{work_id}"
SEMANTIC_SCHOLAR_PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
REQUEST_PAUSE_SECONDS = 0.34
MIN_BODY_CHARS = 1000
CHUNK_POLICY_NAME = "structure_aware_1000_150"
CHUNK_SIZE_CHARS = 1000
CHUNK_OVERLAP_CHARS = 150
MIN_CHUNK_CHARS = 50
NARRATIVE_POLICY_NAME = "raglab_narrative_core_v1"
NARRATIVE_POLICY_REVISION = "2026-09-03-qc-excluded-sections-v5"

INTRODUCTION_HEADINGS = {
    "introduction",
    "background",
}
RESULTS_CONTAINER_HEADINGS = {
    "results",
}
DISCUSSION_HEADINGS = {
    "discussion",
}
CONCLUSION_HEADINGS = {
    "conclusion",
    "conclusions",
}
MIXED_KEEP_HEADINGS = {
    "results and discussion",
    "results & discussion",
}
RESULTS_LIKE_HEADINGS = {
    "patients",
    "treatment",
    "efficacy",
    "safety",
    "response",
    "resistance",
    "clinical activity",
    "quality of life",
    "subsequent therapies",
}
METHODS_CONTAINER_HEADINGS = {
    "methods",
    "methods summary",
    "method details",
    "method detail",
    "materials and methods",
    "material and methods",
    "methods and materials",
    "experimental procedures",
    "supplementary methods",
    "methods details",
    "star methods",
    "star★methods",
}
METHODS_HEADINGS = {
    "study design and oversight",
    "human research participants",
    "study population",
    "randomisation and masking",
    "randomization and masking",
    "procedures",
    "materials and reagents",
    "statistics",
    "statistical analysis",
    "end points",
    "endpoints",
    "ethical statement",
    "cell culture",
    "cell culture, plasmids and antibodies",
    "rna interference",
    "western blotting analysis",
    "cell proliferation assay",
}
METHODS_HEADING_PREFIXES = {
    "materials",
    "materials and methods",
    "reagents",
    "reagents and antibodies",
    "patients and tissue samples",
    "patient samples",
    "eligibility criteria",
    "cell lines",
    "cell culture",
    "culture conditions",
    "patients and methods",
    "study treatment",
    "study design",
    "study design and participants",
    "randomisation and masking",
    "randomization and masking",
    "procedures",
    "definition of",
    "in vivo assay",
    "outcomes",
    "end points",
    "endpoints",
    "statistical analysis",
    "statistics",
    "experimental procedures",
    "establishment of",
    "assay",
    "western blot",
    "immunohistochemistry",
    "immunofluorescence",
    "rna extraction",
    "quantitative rt-pcr",
    "quantitative rt pcr",
    "animal studies",
    "mouse studies",
}
END_MATTER_HEADINGS = {
    "references",
    "acknowledgements",
    "acknowledgments",
    "author contributions",
    "competing interests",
    "conflict of interest",
    "data availability",
    "data and code availability",
    "data availability statement",
    "additional information",
    "supplementary information",
    "reporting summary",
    "number of patients at risk",
    "source data",
    "extended data",
    "online content",
    "role of the funding source",
    "funding",
    "publisher correction",
    "corrected",
}

TARGET_FIELDS = [
    "paper_id",
    "pmid",
    "pmcid",
    "doi",
    "title",
    "primary_subsection_count",
    "best_evidence_role",
]
SOURCE_FIELDS = [
    "paper_id",
    "pmid",
    "pmcid",
    "doi",
    "source_name",
    "source_format",
    "source_url",
    "discovery_status",
    "notes",
]
IMPORT_FIELDS = [
    "paper_id",
    "pmid",
    "pmcid",
    "doi",
    "title",
    "ingestion_status",
    "source_format",
    "access_source",
    "source_url",
    "source_path",
    "normalized_path",
    "text_char_count",
    "section_count",
    "pmc_xml_status",
    "pdf_status",
    "parser_status",
    "user_pdf_required",
    "notes",
]
MANUAL_PDF_FIELDS = [
    "paper_id",
    "pmid",
    "pmcid",
    "doi",
    "title",
    "linked_paper_ids",
    "linked_pmids",
    "linked_dois",
    "duplicate_group_size",
    "queue_reason",
    "preferred_source",
    "expected_filename",
    "dropbox_path",
    "notes",
]
PDF_PARSE_FIELDS = [
    "paper_id",
    "pmid",
    "doi",
    "title",
    "pdf_path",
    "tei_path",
    "normalized_path",
    "parse_status",
    "notes",
]
NARRATIVE_QC_FIELDS = [
    "paper_id",
    "pmid",
    "pmcid",
    "doi",
    "title",
    "source_format",
    "raw_chars",
    "narrative_chars",
    "retention_ratio",
    "kept_section_count",
    "excluded_section_count",
    "excluded_char_count",
    "chunk_count",
    "warning_flags",
    "review_recommendation",
    "kept_section_titles",
    "excluded_section_titles",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage and normalize primary full text from PMC XML or PDF."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    parser.add_argument(
        "--continue-without-user-pdfs",
        action="store_true",
        help="Mark Stage 5 complete with unresolved user-PDF items deferred.",
    )
    parser.add_argument(
        "--user-pdf-dropbox",
        help="Folder containing user-provided PDFs to stage before parsing.",
    )
    parser.add_argument(
        "--skip-network",
        action="store_true",
        help="Only parse already staged local PDFs and existing source files.",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    ensure_dirs(run_dir)
    append_stage_readme(run_dir)

    with connect(run_dir) as connection:
        targets = load_primary_targets(connection)
        if not targets:
            print("ERROR: no globally primary papers found in paper_review_rollup", file=sys.stderr)
            return 1
        write_csv(run_dir / TARGET_DIR / "primary_fulltext_targets.csv", TARGET_FIELDS, targets)

        import_rows = existing_or_new_import_rows(run_dir, targets)
        dropbox = Path(args.user_pdf_dropbox) if args.user_pdf_dropbox else run_dir / USER_DROPBOX_DIR
        stage_user_pdfs(dropbox, run_dir, import_rows)

        source_rows: list[dict[str, str]] = []
        for row in import_rows:
            if row["ingestion_status"] == "normalized":
                continue
            ingest_one(row, run_dir, source_rows, skip_network=args.skip_network)

        for row in import_rows:
            if row["ingestion_status"] != "normalized" and row["pdf_status"] in {
                "downloaded",
                "staged_from_user",
                "parser_pending",
                "parse_failed",
            }:
                parse_pdf(row, run_dir)
        pdf_report_path = run_dir / OUTPUT_DIR / "pdf_parse_report.csv"
        if not pdf_report_path.exists():
            write_csv(pdf_report_path, PDF_PARSE_FIELDS, [])

        manual_rows = build_manual_pdf_queue(import_rows, run_dir)
        status = "complete"
        notes = "Primary full-text ingestion completed."
        if manual_rows and not args.continue_without_user_pdfs:
            status = "blocked_user_pdf_required"
            notes = (
                "Automated PMC/PDF ingestion left unresolved primary papers. "
                "User must either provide PDFs or explicitly continue without them."
            )
        elif manual_rows:
            status = "complete_with_deferred_user_pdfs"
            notes = "User-PDF-needed papers were explicitly deferred."

        write_csv(run_dir / DISCOVERY_DIR / "fulltext_source_candidates.csv", SOURCE_FIELDS, source_rows)
        write_csv(run_dir / OUTPUT_DIR / "import_status.csv", IMPORT_FIELDS, import_rows)
        write_csv(run_dir / USER_DIR / "manual_pdf_queue.csv", MANUAL_PDF_FIELDS, manual_rows)
        write_csv(run_dir / OUTPUT_DIR / "narrative_qc_report.csv", NARRATIVE_QC_FIELDS, build_narrative_qc_report(import_rows, run_dir))
        write_pause_file(run_dir, manual_rows, status)
        write_summary(run_dir, import_rows, manual_rows, status)
        write_sqlite(connection, import_rows, source_rows, status, notes)

    print(
        "Stage 5 primary full-text ingestion "
        f"{status}: targets={len(import_rows)} normalized={count_status(import_rows, 'normalized')} "
        f"user_pdf_required={len(manual_rows)}"
    )
    return 0 if status != "blocked_user_pdf_required" else 2


def ensure_dirs(run_dir: Path) -> None:
    for directory in (
        TARGET_DIR,
        DISCOVERY_DIR,
        PMC_RAW_DIR,
        PMC_NORMALIZED_DIR,
        PDF_STAGED_DIR,
        PDF_GROBID_DIR,
        PDF_NORMALIZED_DIR,
        USER_DROPBOX_DIR,
        OUTPUT_DIR,
    ):
        (run_dir / directory).mkdir(parents=True, exist_ok=True)


def append_stage_readme(run_dir: Path) -> None:
    (run_dir / STAGE_DIR / "README.md").write_text(
        """# Primary Full-Text Ingestion Artifacts

This folder stores Stage 5 artifacts for globally primary papers only.

- `01_targets/`: deduplicated primary-paper target list from SQLite.
- `02_discovery/`: candidate PMC XML and open PDF source URLs.
- `03_pmc/`: raw PMC XML and normalized PMC JSON.
- `04_pdf/`: staged PDFs, GROBID TEI cache, and normalized PDF JSON.
- `05_user_pdf_request/`: manual PDF queue, pause notice, and user PDF dropbox.
- `06_outputs/`: import status, PDF parse report, and ingestion summary.

Only two full-text source formats are stored by this stage: PMC XML and PDF.
All normalized full text is emitted as JSON with `raw_text` and `sections`.
""",
        encoding="utf-8",
    )


def load_primary_targets(connection: sqlite3.Connection) -> list[dict[str, str]]:
    rows = connection.execute(
        """
        SELECT paper_id, pmid, pmcid, doi, title, primary_subsection_count,
               best_evidence_role
        FROM paper_review_rollup
        WHERE global_review_status = 'globally_included_primary'
           OR full_text_ingestion_route = 'primary_full_text_candidate'
        ORDER BY CAST(COALESCE(NULLIF(pmid, ''), '0') AS INTEGER), paper_id
        """
    ).fetchall()
    return [{field: clean_cell(row[field]) for field in TARGET_FIELDS} for row in rows]


def existing_or_new_import_rows(run_dir: Path, targets: list[dict[str, str]]) -> list[dict[str, str]]:
    path = run_dir / OUTPUT_DIR / "import_status.csv"
    existing = {row["paper_id"]: row for row in read_csv(path)} if path.exists() else {}
    rows: list[dict[str, str]] = []
    for target in targets:
        row = existing.get(target["paper_id"], {})
        if row.get("ingestion_status") == "normalized":
            merged = {field: row.get(field, "") for field in IMPORT_FIELDS}
        else:
            merged = {field: "" for field in IMPORT_FIELDS}
        for field in ("paper_id", "pmid", "pmcid", "doi", "title"):
            merged[field] = target.get(field, "")
        merged.setdefault("ingestion_status", "")
        if not merged["ingestion_status"]:
            merged["ingestion_status"] = "not_started"
        for field in ("source_format", "access_source", "source_url", "source_path", "normalized_path", "notes"):
            merged.setdefault(field, "")
        for field in ("text_char_count", "section_count"):
            merged[field] = merged.get(field) or "0"
        for field in ("pmc_xml_status", "pdf_status", "parser_status"):
            merged[field] = merged.get(field) or "not_attempted"
        merged["user_pdf_required"] = merged.get("user_pdf_required") or "0"
        staged_pdf = run_dir / PDF_STAGED_DIR / expected_pdf_filename(merged)
        if merged["ingestion_status"] != "normalized" and staged_pdf.exists():
            merged["source_format"] = "pdf"
            merged["access_source"] = "local_staged_pdf"
            merged["source_path"] = str(staged_pdf.relative_to(run_dir))
            merged["pdf_status"] = "staged_from_user"
            merged["user_pdf_required"] = "0"
        if merged["ingestion_status"] == "normalized":
            for path_field in ("source_path", "normalized_path"):
                merged[path_field] = normalize_stored_path(merged.get(path_field, ""), run_dir)
            repair_normalized_payload(merged, run_dir)
            repair_normalized_import_status(merged, run_dir)
        rows.append(merged)
    return rows


def repair_normalized_import_status(row: dict[str, str], run_dir: Path) -> None:
    normalized_path = resolve_run_path(row.get("normalized_path", ""), run_dir)
    if normalized_path.exists():
        try:
            payload = json.loads(normalized_path.read_text(encoding="utf-8"))
            row["text_char_count"] = str(len(str(payload.get("narrative_text") or payload.get("raw_text", ""))))
            row["section_count"] = str(len(payload.get("sections", [])))
        except (OSError, json.JSONDecodeError):
            pass
    if row.get("source_format") == "pdf" or PDF_NORMALIZED_DIR.as_posix() in row.get("normalized_path", ""):
        row["source_format"] = "pdf"
        row["pdf_status"] = "normalized" if normalized_path.exists() else row.get("pdf_status", "not_attempted")
        row["parser_status"] = "normalized" if normalized_path.exists() else row.get("parser_status", "not_attempted")
        row["user_pdf_required"] = "0"
    elif row.get("source_format") == "pmc_xml" or PMC_NORMALIZED_DIR.as_posix() in row.get("normalized_path", ""):
        row["source_format"] = "pmc_xml"
        row["pmc_xml_status"] = "usable" if normalized_path.exists() else row.get("pmc_xml_status", "not_attempted")
        row["user_pdf_required"] = "0"


def ingest_one(row: dict[str, str], run_dir: Path, source_rows: list[dict[str, str]], skip_network: bool) -> None:
    staged_pdf = run_dir / PDF_STAGED_DIR / expected_pdf_filename(row)
    if staged_pdf.exists():
        row["source_format"] = "pdf"
        row["access_source"] = row.get("access_source") or "user_pdf"
        row["source_url"] = row.get("source_url", "")
        row["source_path"] = relative_to_run(staged_pdf, run_dir)
        row["pdf_status"] = "staged_from_user"
        row["parser_status"] = "not_attempted"
        row["user_pdf_required"] = "0"
        row["notes"] = append_note(row.get("notes", ""), "Expected staged PDF found.")
        return

    candidates = source_candidates(row, skip_network=skip_network)
    source_rows.extend(candidates)
    pmc_candidates = [c for c in candidates if c["source_format"] == "pmc_xml"]
    pdf_candidates = [c for c in candidates if c["source_format"] == "pdf"]

    for candidate in pmc_candidates:
        ok = try_pmc_candidate(row, candidate, run_dir, skip_network=skip_network)
        if ok:
            return
    if row["pmc_xml_status"] == "not_attempted":
        row["pmc_xml_status"] = "missing"

    for candidate in pdf_candidates:
        if try_pdf_candidate(row, candidate, run_dir, skip_network=skip_network):
            break

    if row["ingestion_status"] != "normalized":
        row["ingestion_status"] = "user_pdf_required"
        if not row.get("source_format"):
            row["source_format"] = "none"
        row["user_pdf_required"] = "1"
        row["notes"] = append_note(
            row["notes"],
            "No usable PMC XML or automatically accessible PDF normalized.",
        )


def source_candidates(row: dict[str, str], skip_network: bool) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    pmcid = normalize_pmcid(row.get("pmcid", ""))
    if pmcid:
        add_source(candidates, row, "ncbi_pmc", "pmc_xml", ncbi_pmc_url(pmcid), "from_pmcid", "")
        add_source(
            candidates,
            row,
            "europe_pmc",
            "pmc_xml",
            EUROPE_PMC_XML_URL.format(pmcid=pmcid),
            "from_pmcid",
            "",
        )
    if skip_network:
        return candidates
    for source in (discover_europe_pmc_pdf, discover_openalex_pdf, discover_semantic_scholar_pdf, discover_core_pdf):
        try:
            candidates.extend(source(row))
        except Exception as exc:
            add_source(
                candidates,
                row,
                source.__name__.removeprefix("discover_"),
                "pdf",
                "",
                "discovery_failed",
                str(exc),
            )
    return dedupe_sources(candidates)


def try_pmc_candidate(
    row: dict[str, str], candidate: dict[str, str], run_dir: Path, skip_network: bool
) -> bool:
    pmcid = normalize_pmcid(row.get("pmcid", ""))
    if not pmcid:
        return False
    xml_path = run_dir / PMC_RAW_DIR / f"{pmcid}.xml"
    normalized_path = run_dir / PMC_NORMALIZED_DIR / f"{row['paper_id']}.json"
    if not xml_path.exists():
        if skip_network:
            return False
        ok, message = download_bytes(candidate["source_url"], xml_path, expect_pdf=False)
        if not ok:
            row["pmc_xml_status"] = "download_failed"
            row["notes"] = append_note(row["notes"], message)
            return False
    ok, message = normalize_pmc_xml(xml_path, normalized_path, row)
    if ok:
        mark_normalized(row, "pmc_xml", candidate["source_name"], candidate["source_url"], xml_path, normalized_path, run_dir)
        row["pmc_xml_status"] = "usable"
        return True
    row["pmc_xml_status"] = "unusable"
    row["notes"] = append_note(row["notes"], message)
    return False


def try_pdf_candidate(
    row: dict[str, str], candidate: dict[str, str], run_dir: Path, skip_network: bool
) -> bool:
    if not candidate.get("source_url"):
        return False
    pdf_path = run_dir / PDF_STAGED_DIR / expected_pdf_filename(row)
    if not pdf_path.exists():
        if skip_network:
            return False
        ok, message = download_bytes(candidate["source_url"], pdf_path, expect_pdf=True)
        if not ok:
            row["pdf_status"] = "download_failed"
            row["notes"] = append_note(row["notes"], message)
            return False
    row["source_format"] = "pdf"
    row["access_source"] = candidate["source_name"]
    row["source_url"] = candidate["source_url"]
    row["source_path"] = relative_to_run(pdf_path, run_dir)
    row["pdf_status"] = "downloaded"
    row["notes"] = append_note(row["notes"], "Open-access PDF staged.")
    return True


def stage_user_pdfs(dropbox: Path, run_dir: Path, import_rows: list[dict[str, str]]) -> None:
    if not dropbox.exists() or not dropbox.is_dir():
        print(f"WARNING: user PDF dropbox not found: {dropbox}", file=sys.stderr)
        return
    pdfs = sorted(path for path in dropbox.iterdir() if path.suffix.lower() == ".pdf")
    if not pdfs:
        return
    by_token = {}
    for row in import_rows:
        if row.get("ingestion_status") == "normalized":
            continue
        for token in tokens_for_row(row):
            by_token.setdefault(token.lower(), []).append(row)
    for pdf in pdfs:
        key = pdf.stem.lower()
        comparable_key = comparable_text(pdf.stem)
        rows = by_token.get(key, [])
        if not rows:
            rows = next((r for token, r in by_token.items() if token and token in key), [])
        if not rows:
            rows = next((r for token, r in by_token.items() if token and token in comparable_key), [])
        if not rows:
            continue
        for row in rows:
            staged = run_dir / PDF_STAGED_DIR / expected_pdf_filename(row)
            shutil.copy2(pdf, staged)
            row["source_format"] = "pdf"
            row["access_source"] = "user_pdf"
            row["source_url"] = ""
            row["source_path"] = relative_to_run(staged, run_dir)
            row["pdf_status"] = "staged_from_user"
            row["parser_status"] = "not_attempted"
            row["user_pdf_required"] = "0"
            row["notes"] = append_note(row["notes"], f"User PDF staged from {pdf.name}.")


def parse_pdf(row: dict[str, str], run_dir: Path) -> None:
    pdf_path = resolve_run_path(row.get("source_path", ""), run_dir)
    if not pdf_path.exists():
        pdf_path = run_dir / PDF_STAGED_DIR / expected_pdf_filename(row)
    report_path = run_dir / OUTPUT_DIR / "pdf_parse_report.csv"
    report_rows = read_csv(report_path)
    if not pdf_path.exists():
        row["pdf_status"] = "missing"
        row["parser_status"] = "missing_pdf"
        return
    tei_path = run_dir / PDF_GROBID_DIR / f"{row['paper_id']}.tei.xml"
    normalized_path = run_dir / PDF_NORMALIZED_DIR / f"{row['paper_id']}.json"
    if not is_valid_tei(tei_path):
        ok, message = request_grobid(pdf_path, tei_path)
        if not ok:
            row["parser_status"] = "parser_pending"
            row["ingestion_status"] = "user_pdf_required"
            row["user_pdf_required"] = "1"
            row["notes"] = append_note(row["notes"], message)
            add_pdf_report(report_rows, row, pdf_path, None, None, "parser_pending", message)
            write_csv(report_path, PDF_PARSE_FIELDS, report_rows)
            return
    ok, message = normalize_tei(tei_path, normalized_path, row)
    if ok:
        mark_normalized(row, "pdf", row.get("access_source", "pdf"), row.get("source_url", ""), pdf_path, normalized_path, run_dir)
        row["pdf_status"] = "normalized"
        row["parser_status"] = "normalized"
        add_pdf_report(report_rows, row, pdf_path, tei_path, normalized_path, "normalized", "PDF parsed and normalized through GROBID TEI.")
    else:
        row["parser_status"] = "parse_failed"
        row["ingestion_status"] = "user_pdf_required"
        row["user_pdf_required"] = "1"
        row["notes"] = append_note(row["notes"], message)
        add_pdf_report(report_rows, row, pdf_path, tei_path, None, "parse_failed", message)
    write_csv(report_path, PDF_PARSE_FIELDS, report_rows)


def normalize_pmc_xml(xml_path: Path, normalized_path: Path, row: dict[str, str]) -> tuple[bool, str]:
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as exc:
        return False, f"PMC XML parse error: {exc}"
    body = find_first(root, "body")
    if body is None:
        return False, "PMC XML body element is missing."
    raw_text = clean_text(" ".join(text for text in body.itertext() if text and text.strip()))
    if len(raw_text) < MIN_BODY_CHARS:
        return False, "PMC XML body text is too short for normalization."
    title = row.get("title", "")
    title_element = find_first(root, "article-title")
    if title_element is not None:
        candidate = clean_text("".join(title_element.itertext()))
        if candidate:
            title = candidate
    abstract = extract_pmc_abstract(root)
    sections, excluded_sections = filter_narrative_sections(extract_pmc_sections(root), title=title, abstract=abstract)
    payload = normalized_payload(row, title, "pmc_xml", xml_path, raw_text, sections, abstract, excluded_sections)
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return True, ""


def normalize_tei(tei_path: Path, normalized_path: Path, row: dict[str, str]) -> tuple[bool, str]:
    try:
        root = ET.parse(tei_path).getroot()
    except ET.ParseError as exc:
        return False, f"TEI parse error: {exc}"
    raw_text = tei_raw_text(root)
    if len(raw_text) < MIN_BODY_CHARS:
        return False, "GROBID TEI body text is too short for normalization."
    title = row.get("title", "")
    title_element = find_first(root, "title")
    if title_element is not None:
        candidate = clean_text("".join(title_element.itertext()))
        if candidate:
            title = candidate
    abstract = extract_tei_abstract(root)
    sections, excluded_sections = filter_narrative_sections(extract_tei_sections(root), title=title, abstract=abstract)
    payload = normalized_payload(row, title, "pdf", tei_path, raw_text, sections, abstract, excluded_sections)
    normalized_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return True, ""


def normalized_payload(
    row: dict[str, str],
    title: str,
    source_format: str,
    source_path: Path,
    raw_text: str,
    sections: list[dict[str, str]],
    abstract: str = "",
    excluded_sections: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    narrative_text = "\n\n".join(
        f"{section.get('title', '')}\n{section.get('text', '')}".strip()
        for section in sections
        if section.get("text")
    )
    chunks = build_chunks(sections, narrative_text)
    return {
        "paper_id": row.get("paper_id", ""),
        "pmid": row.get("pmid", ""),
        "pmcid": row.get("pmcid", ""),
        "doi": row.get("doi", ""),
        "title": title,
        "abstract": abstract,
        "source_format": source_format,
        "source_path": str(source_path),
        "raw_text": raw_text,
        "narrative_text": narrative_text,
        "narrative_policy": {
            "name": NARRATIVE_POLICY_NAME,
            "revision": NARRATIVE_POLICY_REVISION,
            "kept": (
                "title, abstract, introduction-like sections, result-bearing "
                "sections/subsections, discussion/conclusion-like synthesis, "
                "and cautious ambiguous narrative sections"
            ),
            "excluded": (
                "methods, references, acknowledgements, affiliations, figure "
                "legends, tables, supplementary/end matter, procedural sections, "
                "and metadata-heavy sections"
            ),
            "risk_note": (
                "The filter is conservative: if it cannot confidently classify "
                "a non-method non-end-matter section, it keeps the section rather "
                "than risking loss of scientific narrative."
            ),
        },
        "sections": sections,
        "excluded_sections": excluded_sections or [],
        "chunk_policy": {
            "name": CHUNK_POLICY_NAME,
            "chunk_size_chars": CHUNK_SIZE_CHARS,
            "chunk_overlap_chars": CHUNK_OVERLAP_CHARS,
            "boundary_rule": (
                "Preserve section and paragraph boundaries when possible; use "
                "sentence-aware overlap only when splitting oversized paragraphs."
            ),
        },
        "chunks": chunks,
        "sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
    }


def mark_normalized(
    row: dict[str, str],
    source_format: str,
    access_source: str,
    source_url: str,
    source_path: Path,
    normalized_path: Path,
    run_dir: Path,
) -> None:
    payload = json.loads(normalized_path.read_text(encoding="utf-8"))
    row["ingestion_status"] = "normalized"
    row["source_format"] = source_format
    row["access_source"] = access_source
    row["source_url"] = source_url
    row["source_path"] = relative_to_run(source_path, run_dir)
    row["normalized_path"] = relative_to_run(normalized_path, run_dir)
    row["text_char_count"] = str(len(str(payload.get("narrative_text") or payload.get("raw_text", ""))))
    row["section_count"] = str(len(payload.get("sections", [])))
    row["user_pdf_required"] = "0"
    row["notes"] = append_note(row["notes"], f"Normalized from {source_format}.")


def relative_to_run(path: Path, run_dir: Path) -> str:
    try:
        return str(path.relative_to(run_dir))
    except ValueError:
        return str(path)


def resolve_run_path(value: str, run_dir: Path) -> Path:
    path = Path(value)
    if path.exists() or path.is_absolute():
        return path
    return run_dir / path


def normalize_stored_path(value: str, run_dir: Path) -> str:
    if not value:
        return ""
    path = Path(value)
    try:
        return str(path.relative_to(run_dir))
    except ValueError:
        pass
    run_prefix = run_dir.as_posix().rstrip("/") + "/"
    if value.startswith(run_prefix):
        return value[len(run_prefix):]
    doubled = f"{run_dir.as_posix().rstrip('/')}/{run_prefix}"
    if value.startswith(doubled):
        return value[len(doubled):]
    return value


def build_chunks(
    sections: list[dict[str, str]] | object,
    raw_text: str,
    max_chars: int = CHUNK_SIZE_CHARS,
    overlap_chars: int = CHUNK_OVERLAP_CHARS,
) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    usable_sections = sections if isinstance(sections, list) else []
    for section_index, section in enumerate(usable_sections, start=1):
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or "")
        text = clean_text(str(section.get("text") or ""))
        if not text:
            continue
        for chunk_text in section_window_texts(title, str(section.get("text") or ""), max_chars, overlap_chars):
            chunks.append(make_chunk(chunk_text, title, section_index, len(chunks) + 1))
    if not chunks and raw_text:
        for chunk_text in section_window_texts("full text", raw_text, max_chars, overlap_chars):
            chunks.append(make_chunk(chunk_text, "full text", 1, len(chunks) + 1))
    return normalize_chunks(chunks)


def section_window_texts(
    section_title: str,
    text: str,
    max_chars: int,
    overlap_chars: int,
) -> list[str]:
    if not text.strip():
        return []
    paragraphs = paragraph_blocks(text)
    cleaned_section = "\n\n".join(paragraphs) if paragraphs else clean_text(text)
    if cleaned_section and len(cleaned_section) <= max_chars:
        return [cleaned_section]
    content_budget = max(200, max_chars - len(section_title) - 2 if section_title else max_chars)
    output: list[str] = []
    for paragraph in paragraphs or [clean_text(text)]:
        if len(paragraph) <= content_budget:
            output.append(paragraph)
            continue
        output.extend(split_long_paragraph(paragraph, content_budget, overlap_chars))
    return output


def make_chunk(text: str, section_title: str, section_index: int, chunk_index: int) -> dict[str, object]:
    cleaned = clean_text(text)
    return {
        "chunk_id": f"CH{chunk_index:04d}",
        "section_index": section_index,
        "section_title": section_title,
        "text": cleaned,
        "char_count": len(cleaned),
    }


def paragraph_blocks(text: str) -> list[str]:
    return [clean_text(part) for part in re.split(r"\n\s*\n+", text or "") if clean_text(part)]


def split_long_paragraph(paragraph: str, max_chars: int, overlap_chars: int) -> list[str]:
    sentences = sentence_like_units(paragraph)
    if len(sentences) <= 1:
        return split_text_fallback(paragraph, max_chars)
    expanded_sentences: list[str] = []
    for sentence in sentences:
        if len(sentence) > max_chars:
            expanded_sentences.extend(split_text_fallback(sentence, max_chars))
        else:
            expanded_sentences.append(sentence)
    return pack_text_units(expanded_sentences, max_chars, overlap_chars, joiner=" ")


def sentence_like_units(text: str) -> list[str]:
    stripped = clean_text(text)
    if not stripped:
        return []
    parts = re.split(r'(?<=[.!?])\s+(?=(?:["(\[]?[A-Z]))', stripped)
    return [part.strip() for part in parts if part.strip()] or [stripped]


def split_text_fallback(text: str, max_chars: int) -> list[str]:
    remaining = clean_text(text)
    if not remaining:
        return []
    if len(remaining) <= max_chars:
        return [remaining]
    chunks: list[str] = []
    while len(remaining) > max_chars:
        split_at = remaining.rfind(" ", 0, max_chars + 1)
        if split_at <= max_chars // 2:
            split_at = max_chars
        chunk = remaining[:split_at].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def pack_text_units(units: list[str], max_chars: int, overlap_chars: int, joiner: str) -> list[str]:
    cleaned_units = [unit.strip() for unit in units if unit and unit.strip()]
    if not cleaned_units:
        return []
    texts: list[str] = []
    start = 0
    while start < len(cleaned_units):
        current_units: list[str] = []
        current_length = 0
        index = start
        while index < len(cleaned_units):
            unit = cleaned_units[index]
            projected = current_length + (len(joiner) if current_units else 0) + len(unit)
            if current_units and projected > max_chars:
                break
            current_units.append(unit)
            current_length = projected
            index += 1
            if current_length >= max_chars:
                break
        if not current_units:
            current_units = [cleaned_units[start]]
            index = start + 1
        texts.append(joiner.join(current_units))
        if index >= len(cleaned_units):
            break
        overlap_units = overlap_unit_count(current_units, joiner, overlap_chars)
        next_start = max(start + 1, index - overlap_units)
        if next_start <= start:
            next_start = start + 1
        start = next_start
    return texts


def overlap_unit_count(units: list[str], joiner: str, overlap_chars: int) -> int:
    if overlap_chars <= 0 or len(units) <= 1:
        return 0
    overlap_units = 0
    accumulated = 0
    for unit in reversed(units):
        accumulated += len(unit)
        if overlap_units > 0:
            accumulated += len(joiner)
        overlap_units += 1
        if accumulated >= overlap_chars:
            break
    return min(overlap_units, len(units) - 1)


def normalize_chunks(chunks: list[dict[str, str]], min_chars: int = MIN_CHUNK_CHARS) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for chunk in chunks:
        text = clean_text(str(chunk.get("text") or ""))
        if not text:
            continue
        if len(text) < min_chars and normalized:
            previous = normalized[-1]
            previous["text"] = clean_text(f"{previous['text']} {text}")
            previous["char_count"] = len(previous["text"])
            continue
        normalized.append(
            {
                "chunk_id": f"CH{len(normalized) + 1:04d}",
                "section_index": int(chunk.get("section_index") or 1),
                "section_title": str(chunk.get("section_title") or "full text"),
                "text": text,
                "char_count": len(text),
            }
        )
    if len(normalized) > 1 and normalized[-1]["char_count"] < min_chars:
        tail = normalized.pop()
        previous = normalized[-1]
        previous["text"] = clean_text(f"{previous['text']} {tail['text']}")
        previous["char_count"] = len(previous["text"])
    return normalized


def repair_normalized_payload(row: dict[str, str], run_dir: Path) -> None:
    normalized_path = resolve_run_path(row.get("normalized_path", ""), run_dir)
    if not normalized_path.exists():
        return
    try:
        payload = json.loads(normalized_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    source_format = str(payload.get("source_format") or row.get("source_format") or "")
    source_path = resolve_run_path(str(payload.get("source_path") or row.get("source_path") or ""), run_dir)
    narrative_policy = payload.get("narrative_policy", {})
    if (
        (
            narrative_policy.get("name") != NARRATIVE_POLICY_NAME
            or narrative_policy.get("revision") != NARRATIVE_POLICY_REVISION
        )
        and source_path.exists()
    ):
        if source_format == "pmc_xml":
            normalize_pmc_xml(source_path, normalized_path, row)
            return
        if source_format == "pdf":
            normalize_tei(source_path, normalized_path, row)
            return
    changed = False
    if "source_format" not in payload:
        source_type = str(payload.get("source_type") or "")
        if source_type == "pdf_grobid":
            payload["source_format"] = "pdf"
        elif source_type == "pmc_xml":
            payload["source_format"] = "pmc_xml"
        else:
            payload["source_format"] = row.get("source_format", "")
        changed = True
    chunk_policy = payload.get("chunk_policy")
    expected_policy = {
        "name": CHUNK_POLICY_NAME,
        "chunk_size_chars": CHUNK_SIZE_CHARS,
        "chunk_overlap_chars": CHUNK_OVERLAP_CHARS,
        "boundary_rule": (
            "Preserve section and paragraph boundaries when possible; use "
            "sentence-aware overlap only when splitting oversized paragraphs."
        ),
    }
    if chunk_policy != expected_policy:
        payload["chunk_policy"] = expected_policy
        payload["chunks"] = build_chunks(payload.get("sections", []), str(payload.get("narrative_text") or payload.get("raw_text") or ""))
        changed = True
    chunks = payload.get("chunks")
    if not isinstance(chunks, list) or any(
        not isinstance(chunk, dict) or int(chunk.get("char_count") or 0) < MIN_CHUNK_CHARS for chunk in chunks
    ):
        payload["chunks"] = build_chunks(payload.get("sections", []), str(payload.get("narrative_text") or payload.get("raw_text") or ""))
        changed = True
    source_path = payload.get("source_path")
    if source_path:
        normalized_source_path = normalize_stored_path(str(source_path), run_dir)
        if normalized_source_path != source_path:
            payload["source_path"] = normalized_source_path
            changed = True
    if changed:
        normalized_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_manual_pdf_queue(rows: list[dict[str, str]], run_dir: Path) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    ordered_keys: list[str] = []
    dropbox = run_dir / USER_DROPBOX_DIR
    for row in rows:
        if row.get("ingestion_status") == "normalized":
            continue
        key = manual_queue_group_key(row)
        if key not in grouped:
            grouped[key] = []
            ordered_keys.append(key)
        grouped[key].append(row)
    manual_rows = []
    for key in ordered_keys:
        group = grouped[key]
        row = group[0]
        manual_rows.append(
            {
                "paper_id": row["paper_id"],
                "pmid": row["pmid"],
                "pmcid": row["pmcid"],
                "doi": row["doi"],
                "title": row["title"],
                "linked_paper_ids": ";".join(item["paper_id"] for item in group),
                "linked_pmids": ";".join(item["pmid"] for item in group if item.get("pmid")),
                "linked_dois": ";".join(item["doi"] for item in group if item.get("doi")),
                "duplicate_group_size": str(len(group)),
                "queue_reason": " | ".join(
                    row.get("notes", "") or "No normalized PMC XML or PDF full text."
                    for row in group
                ),
                "preferred_source": "publisher_pdf_or_user_download",
                "expected_filename": expected_pdf_filename(row),
                "dropbox_path": str(dropbox),
                "notes": (
                    "Place one PDF in the dropbox using the expected filename, PMID, "
                    "PMCID, DOI, paper_id, or title in the filename. If "
                    "duplicate_group_size is greater than 1, one PDF may satisfy all "
                    "linked paper IDs only when it is truly the same full-text article."
                ),
            }
        )
    return manual_rows


def manual_queue_group_key(row: dict[str, str]) -> str:
    title_key = comparable_text(row.get("title", ""))
    if title_key:
        return f"title:{title_key}"
    if row.get("doi"):
        return f"doi:{row['doi'].strip().lower()}"
    return f"paper:{row.get('paper_id', '')}"


def write_pause_file(run_dir: Path, manual_rows: list[dict[str, str]], status: str) -> None:
    path = run_dir / USER_DIR / "user_pdf_pause.md"
    if not manual_rows:
        text = (
            "# User PDF Pause\n\n"
            "No user PDF pause is required. All primary full-text targets were "
            "normalized or explicitly deferred according to the Stage 5 contract. "
            "Downstream agents may proceed only after validation confirms that "
            "`import_status.csv`, normalized full-text JSON, and SQLite state agree.\n"
        )
    else:
        text = (
            "# User PDF Pause\n\n"
            f"Stage 5 status: `{status}`\n\n"
            f"{len(manual_rows)} primary papers still need user-provided PDF full text or an explicit decision to continue without them.\n\n"
            "To provide PDFs, place them in:\n\n"
            f"`{run_dir / USER_DROPBOX_DIR}`\n\n"
            "Use filenames containing the expected filename, PMID, PMCID, DOI, or paper_id. Then rerun:\n\n"
            "```bash\n"
            f"python3 tools/05_primary_full_text_ingestion/primary_full_text_ingestion.py {run_dir}\n"
            "```\n\n"
            "To continue without unresolved PDFs, rerun with:\n\n"
            "```bash\n"
            f"python3 tools/05_primary_full_text_ingestion/primary_full_text_ingestion.py {run_dir} --continue-without-user-pdfs\n"
            "```\n"
        )
    path.write_text(text, encoding="utf-8")


def build_narrative_qc_report(import_rows: list[dict[str, str]], run_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in import_rows:
        if row.get("ingestion_status") != "normalized":
            continue
        normalized_path = resolve_run_path(row.get("normalized_path", ""), run_dir)
        try:
            payload = json.loads(normalized_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        raw_chars = len(str(payload.get("raw_text") or ""))
        narrative_chars = len(str(payload.get("narrative_text") or ""))
        kept_sections = payload.get("sections") if isinstance(payload.get("sections"), list) else []
        excluded_sections = payload.get("excluded_sections") if isinstance(payload.get("excluded_sections"), list) else []
        chunks = payload.get("chunks") if isinstance(payload.get("chunks"), list) else []
        excluded_char_count = sum(
            int(section.get("char_count") or 0)
            for section in excluded_sections
            if isinstance(section, dict)
        )
        retention_ratio = narrative_chars / raw_chars if raw_chars else 0.0
        flags = narrative_qc_flags(
            raw_chars=raw_chars,
            narrative_chars=narrative_chars,
            retention_ratio=retention_ratio,
            kept_section_count=len(kept_sections),
            excluded_char_count=excluded_char_count,
            chunk_count=len(chunks),
        )
        rows.append(
            {
                "paper_id": row.get("paper_id", ""),
                "pmid": row.get("pmid", ""),
                "pmcid": row.get("pmcid", ""),
                "doi": row.get("doi", ""),
                "title": row.get("title", ""),
                "source_format": row.get("source_format", ""),
                "raw_chars": str(raw_chars),
                "narrative_chars": str(narrative_chars),
                "retention_ratio": f"{retention_ratio:.3f}",
                "kept_section_count": str(len(kept_sections)),
                "excluded_section_count": str(len(excluded_sections)),
                "excluded_char_count": str(excluded_char_count),
                "chunk_count": str(len(chunks)),
                "warning_flags": ";".join(flags),
                "review_recommendation": narrative_qc_recommendation(flags),
                "kept_section_titles": "; ".join(
                    str(section.get("title") or "")
                    for section in kept_sections
                    if isinstance(section, dict)
                ),
                "excluded_section_titles": "; ".join(
                    f"{section.get('title') or 'Untitled'} [{section.get('exclusion_reason') or ''}]"
                    for section in excluded_sections
                    if isinstance(section, dict)
                ),
            }
        )
    rows.sort(key=lambda item: (item["review_recommendation"], float(item["retention_ratio"]), int(item["narrative_chars"])))
    return rows


def narrative_qc_flags(
    *,
    raw_chars: int,
    narrative_chars: int,
    retention_ratio: float,
    kept_section_count: int,
    excluded_char_count: int,
    chunk_count: int,
) -> list[str]:
    flags: list[str] = []
    if raw_chars and retention_ratio < 0.35:
        flags.append("low_retention_ratio")
    if narrative_chars < 10000:
        flags.append("low_narrative_chars")
    if kept_section_count <= 2:
        flags.append("few_kept_sections")
    if chunk_count < 15:
        flags.append("few_chunks")
    if raw_chars and excluded_char_count / raw_chars > 0.65:
        flags.append("large_excluded_fraction")
    if kept_section_count <= 2 and narrative_chars < 15000:
        flags.append("possible_abstract_or_body_only")
    return flags


def narrative_qc_recommendation(flags: list[str]) -> str:
    if not flags:
        return "pass"
    high_priority = {
        "low_retention_ratio",
        "low_narrative_chars",
        "few_kept_sections",
        "possible_abstract_or_body_only",
    }
    if len(high_priority.intersection(flags)) >= 2:
        return "inspect_for_possible_overfiltering"
    return "watch"


def write_summary(
    run_dir: Path, rows: list[dict[str, str]], manual_rows: list[dict[str, str]], status: str
) -> None:
    normalized = count_status(rows, "normalized")
    pmc = sum(1 for row in rows if row.get("ingestion_status") == "normalized" and row.get("source_format") == "pmc_xml")
    pdf = sum(1 for row in rows if row.get("ingestion_status") == "normalized" and row.get("source_format") == "pdf")
    text = f"""# Primary Full-Text Ingestion Summary

## Overall Status

`{status}`

## Counts

- primary targets: `{len(rows)}`
- normalized full text: `{normalized}`
- normalized PMC XML: `{pmc}`
- normalized PDF: `{pdf}`
- user PDF required: `{len(manual_rows)}`

## Manual PDF Gate

If `user_pdf_required` is greater than zero, the workflow must pause unless the
user explicitly chooses to continue without unresolved PDFs.
"""
    (run_dir / OUTPUT_DIR / "ingestion_summary.md").write_text(text, encoding="utf-8")


def write_sqlite(
    connection: sqlite3.Connection,
    import_rows: list[dict[str, str]],
    source_rows: list[dict[str, str]],
    status: str,
    notes: str,
) -> None:
    now = timestamp()
    connection.execute("DELETE FROM full_text_ingestion")
    connection.execute("DELETE FROM full_text_source_candidates")
    for row in import_rows:
        connection.execute(
            """
            INSERT OR REPLACE INTO full_text_ingestion(
                paper_id, pmid, pmcid, doi, title, ingestion_status, source_format,
                access_source, source_url, source_path, normalized_path,
                text_char_count, section_count, pmc_xml_status, pdf_status,
                parser_status, user_pdf_required, notes, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["paper_id"],
                row["pmid"],
                row["pmcid"],
                row["doi"],
                row["title"],
                row["ingestion_status"],
                row["source_format"],
                row["access_source"],
                row["source_url"],
                row["source_path"],
                row["normalized_path"],
                int(row.get("text_char_count") or 0),
                int(row.get("section_count") or 0),
                row["pmc_xml_status"],
                row["pdf_status"],
                row["parser_status"],
                int(row.get("user_pdf_required") or 0),
                row["notes"],
                now,
            ),
        )
    for row in source_rows:
        if not row.get("source_url"):
            continue
        connection.execute(
            """
            INSERT OR REPLACE INTO full_text_source_candidates(
                paper_id, pmid, pmcid, doi, source_name, source_format,
                source_url, discovery_status, notes, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["paper_id"],
                row["pmid"],
                row["pmcid"],
                row["doi"],
                row["source_name"],
                row["source_format"],
                row["source_url"],
                row["discovery_status"],
                row["notes"],
                now,
            ),
        )
    connection.execute(
        """
        INSERT OR REPLACE INTO workflow_steps(
            step_name, status, started_at, completed_at, validation_status, notes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("primary_full_text_ingestion", status, now, now if status != "blocked_user_pdf_required" else "", "pending_validation", notes),
    )
    connection.commit()


def discover_europe_pmc_pdf(row: dict[str, str]) -> list[dict[str, str]]:
    query = ""
    if row.get("pmid"):
        query = f"EXT_ID:{row['pmid']} SRC:MED"
    elif row.get("doi"):
        query = f'DOI:"{row["doi"]}"'
    if not query:
        return []
    url = EUROPE_PMC_SEARCH_URL + "?" + urllib.parse.urlencode({"query": query, "format": "json", "resultType": "core"})
    data = json.loads(fetch_text(url))
    rows: list[dict[str, str]] = []
    for result in data.get("resultList", {}).get("result", []):
        for item in result.get("fullTextUrlList", {}).get("fullTextUrl", []):
            candidate = item.get("url", "")
            if is_pdf_url(candidate) or item.get("documentStyle", "").lower() == "pdf":
                add_source(rows, row, "europe_pmc", "pdf", candidate, "found", "Europe PMC fullTextUrlList.")
    return rows


def discover_openalex_pdf(row: dict[str, str]) -> list[dict[str, str]]:
    doi = row.get("doi", "").strip()
    if not doi:
        return []
    work_id = "https://doi.org/" + doi
    url = OPENALEX_WORKS_URL.format(work_id=urllib.parse.quote(work_id, safe=":/"))
    data = json.loads(fetch_text(url))
    rows: list[dict[str, str]] = []
    for candidate in openalex_pdf_urls(data):
        add_source(rows, row, "openalex", "pdf", candidate, "found", "OpenAlex open-access PDF URL.")
    return rows


def discover_semantic_scholar_pdf(row: dict[str, str]) -> list[dict[str, str]]:
    paper_id = f"PMID:{row['pmid']}" if row.get("pmid") else ""
    if not paper_id and row.get("doi"):
        paper_id = f"DOI:{row['doi']}"
    if not paper_id:
        return []
    url = SEMANTIC_SCHOLAR_PAPER_URL.format(paper_id=urllib.parse.quote(paper_id, safe=":")) + "?fields=openAccessPdf"
    data = json.loads(fetch_text(url))
    pdf = data.get("openAccessPdf") or {}
    candidate = pdf.get("url", "")
    rows: list[dict[str, str]] = []
    if candidate:
        add_source(rows, row, "semantic_scholar", "pdf", candidate, "found", "Semantic Scholar openAccessPdf.")
    return rows


def discover_core_pdf(row: dict[str, str]) -> list[dict[str, str]]:
    api_key = os.environ.get("CORE_API_KEY", "").strip()
    doi = row.get("doi", "").strip()
    if not api_key or not doi:
        return []
    url = "https://api.core.ac.uk/v3/search/works?" + urllib.parse.urlencode({"q": f'doi:"{doi}"', "limit": "1"})
    text = fetch_text(url, headers={"Authorization": f"Bearer {api_key}"})
    data = json.loads(text)
    rows: list[dict[str, str]] = []
    for result in data.get("results", []):
        source_urls = result.get("sourceFulltextUrls") or []
        candidate = result.get("downloadUrl") or (source_urls[0] if source_urls else "")
        if candidate:
            add_source(rows, row, "core", "pdf", candidate, "found", "CORE API full-text URL.")
    return rows


def fetch_text(url: str, headers: dict[str, str] | None = None) -> str:
    request = urllib.request.Request(url, headers=headers or {"User-Agent": "LiteratureDueDiligence/0.1"})
    with urllib.request.urlopen(request, timeout=45, context=ssl_context()) as response:
        return response.read().decode("utf-8", errors="replace")


def download_bytes(url: str, path: Path, expect_pdf: bool) -> tuple[bool, str]:
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "LiteratureDueDiligence/0.1"})
        with urllib.request.urlopen(request, timeout=90, context=ssl_context()) as response:
            payload = response.read()
    except Exception as exc:
        return False, f"Download failed from {url}: {exc}"
    if not payload:
        return False, f"Download returned empty content from {url}."
    if expect_pdf and b"%PDF-" not in payload[:2048]:
        return False, f"URL did not return a valid PDF payload: {url}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    time.sleep(REQUEST_PAUSE_SECONDS)
    return True, ""


def ssl_context() -> ssl.SSLContext:
    if os.environ.get("LDD_INSECURE_SSL", "").strip() == "1":
        return ssl._create_unverified_context()
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def ncbi_pmc_url(pmcid: str) -> str:
    return NCBI_EFETCH_URL + "?" + urllib.parse.urlencode({"db": "pmc", "id": normalize_pmcid(pmcid), "retmode": "xml"})


def openalex_pdf_urls(data: dict[str, object]) -> list[str]:
    urls = []
    primary = data.get("primary_location") or {}
    if isinstance(primary, dict) and primary.get("pdf_url"):
        urls.append(str(primary["pdf_url"]))
    open_access = data.get("open_access") or {}
    if isinstance(open_access, dict) and open_access.get("oa_url") and is_pdf_url(str(open_access["oa_url"])):
        urls.append(str(open_access["oa_url"]))
    for location in data.get("locations") or []:
        if isinstance(location, dict) and location.get("pdf_url"):
            urls.append(str(location["pdf_url"]))
    return list(dict.fromkeys(urls))


def add_source(
    rows: list[dict[str, str]],
    paper: dict[str, str],
    source_name: str,
    source_format: str,
    source_url: str,
    discovery_status: str,
    notes: str,
) -> None:
    rows.append(
        {
            "paper_id": paper.get("paper_id", ""),
            "pmid": paper.get("pmid", ""),
            "pmcid": paper.get("pmcid", ""),
            "doi": paper.get("doi", ""),
            "source_name": source_name,
            "source_format": source_format,
            "source_url": source_url,
            "discovery_status": discovery_status,
            "notes": notes,
        }
    )


def dedupe_sources(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    deduped = []
    for row in rows:
        key = (row["paper_id"], row["source_name"], row["source_format"], row["source_url"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def request_grobid(pdf_path: Path, tei_path: Path) -> tuple[bool, str]:
    base_url, note = resolve_grobid_url()
    if not base_url:
        return False, note
    endpoint = base_url.rstrip("/") + "/api/processFulltextDocument"
    body, boundary = build_multipart_body(pdf_path)
    request = urllib.request.Request(
        endpoint,
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "application/xml"},
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        return False, f"GROBID request failed: HTTP {exc.code}"
    except Exception as exc:
        return False, f"GROBID request failed: {exc}"
    if not payload.strip():
        return False, "GROBID returned empty content."
    tei_path.parent.mkdir(parents=True, exist_ok=True)
    tei_path.write_bytes(payload)
    return True, note


def resolve_grobid_url() -> tuple[str, str]:
    tried = []
    for candidate in candidate_grobid_urls():
        tried.append(candidate)
        if is_reachable(candidate):
            return candidate, f"Using GROBID endpoint base {candidate}."
    return "", f"No reachable GROBID service discovered. Tried: {', '.join(tried)}."


def candidate_grobid_urls() -> list[str]:
    candidates = []
    for name in ("GROBID_URL", "GROBID_BASE_URL"):
        url = normalize_grobid_base_url(os.environ.get(name, ""))
        if url and url not in candidates:
            candidates.append(url)
    for url in ("http://localhost:8070", "http://127.0.0.1:8070", "http://localhost:8071", "http://127.0.0.1:8071"):
        if url not in candidates:
            candidates.append(url)
    return candidates


def normalize_grobid_base_url(value: str) -> str:
    url = value.strip()
    for suffix in ("/api/processFulltextDocument", "/processFulltextDocument", "/api/isalive", "/isalive", "/api"):
        url = re.sub(re.escape(suffix) + r"/?$", "", url)
    return url.rstrip("/")


def is_reachable(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/isalive", timeout=5) as response:
            payload = response.read().decode("utf-8", errors="ignore").strip().lower()
        return response.status == 200 and payload in {"true", '"true"', "ok"}
    except Exception:
        return False


def build_multipart_body(pdf_path: Path) -> tuple[bytes, str]:
    boundary = f"----LiteratureDueDiligence{uuid.uuid4().hex}"
    content_type = mimetypes.guess_type(pdf_path.name)[0] or "application/pdf"
    header = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="input"; filename="{pdf_path.name}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8")
    footer = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return header + pdf_path.read_bytes() + footer, boundary


def is_valid_tei(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 500:
        return False
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return False
    return len(tei_raw_text(root)) >= MIN_BODY_CHARS


def xml_local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def find_first(root: ET.Element, name: str) -> ET.Element | None:
    return next((element for element in root.iter() if xml_local_name(element.tag) == name), None)


def clean_text(value: str) -> str:
    return " ".join(value.split())


def extract_pmc_abstract(root: ET.Element) -> str:
    article = next((element for element in root.iter() if xml_local_name(element.tag) == "article"), root)
    abstracts = []
    for abstract in article.iter():
        if xml_local_name(abstract.tag) != "abstract":
            continue
        text = clean_text(" ".join(text for text in abstract.itertext() if text and text.strip()))
        if text:
            abstracts.append(text)
    return "\n\n".join(dict.fromkeys(abstracts))


def extract_tei_abstract(root: ET.Element) -> str:
    abstracts = []
    for abstract in root.iter():
        if xml_local_name(abstract.tag) != "abstract":
            continue
        paragraphs = [
            clean_text("".join(child.itertext()))
            for child in abstract.iter()
            if xml_local_name(child.tag) == "p" and clean_text("".join(child.itertext()))
        ]
        text = "\n\n".join(paragraphs) or clean_text(" ".join(abstract.itertext()))
        if text:
            abstracts.append(text)
    return "\n\n".join(dict.fromkeys(abstracts))


def extract_pmc_sections(root: ET.Element) -> list[dict[str, str]]:
    body = find_first(root, "body")
    if body is None:
        return []
    sections = []
    body_paragraphs = [
        clean_text("".join(child.itertext()))
        for child in body
        if xml_local_name(child.tag) == "p" and clean_text("".join(child.itertext()))
    ]
    if body_paragraphs:
        sections.append({"title": "Body", "text": "\n\n".join(body_paragraphs)})
    for sec in body.iter():
        if xml_local_name(sec.tag) != "sec":
            continue
        title_element = next((child for child in sec if xml_local_name(child.tag) == "title"), None)
        title = clean_text("".join(title_element.itertext())) if title_element is not None else ""
        paragraphs = [
            clean_text("".join(child.itertext()))
            for child in sec
            if xml_local_name(child.tag) == "p" and clean_text("".join(child.itertext()))
        ]
        if title or paragraphs:
            sections.append({"title": title, "text": "\n\n".join(paragraphs)})
    return sections


def extract_tei_sections(root: ET.Element) -> list[dict[str, str]]:
    body = find_first(root, "body")
    if body is None:
        return []
    sections = []
    for div in body.iter():
        if xml_local_name(div.tag) != "div":
            continue
        head = next((child for child in div if xml_local_name(child.tag) == "head"), None)
        title = clean_text("".join(head.itertext())) if head is not None else ""
        paragraphs = [
            clean_text("".join(child.itertext()))
            for child in div
            if xml_local_name(child.tag) == "p" and clean_text("".join(child.itertext()))
        ]
        if title or paragraphs:
            sections.append({"title": title, "text": "\n\n".join(paragraphs)})
    return sections


def filter_narrative_sections(
    sections: list[dict[str, str]],
    *,
    title: str,
    abstract: str,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    source_sections = suppress_container_sections(sections)
    filtered: list[dict[str, str]] = []
    excluded: list[dict[str, str]] = []
    if abstract:
        filtered.append({"title": "Abstract", "text": clean_text(abstract), "narrative_class": "abstract"})

    saw_intro_like = False
    saw_results_container = False
    saw_discussion = False
    in_methods_block = False
    for section in source_sections:
        heading = normalize_heading_text(str(section.get("title") or ""))
        original_text = str(section.get("text") or "")
        text = smooth_section_paragraphs(strip_nontext_tail(strip_caption_like_paragraphs(original_text)))
        if not text:
            if original_text:
                record_excluded_section(excluded, heading, "empty_after_caption_or_tail_filter", "skip", original_text)
            continue
        classification = classify_section_heading(heading)
        if classification == "skip":
            record_excluded_section(excluded, heading, "end_matter_or_non_narrative_heading", classification, original_text)
            continue
        if classification in {"methods_container", "methods"}:
            in_methods_block = True
            record_excluded_section(excluded, heading, "methods_heading", classification, original_text)
            continue
        if looks_like_methods_heading(heading) or looks_like_methods_text_prefix(text):
            in_methods_block = True
            record_excluded_section(excluded, heading, "methods_like_heading_or_text", classification, original_text)
            continue
        if in_methods_block and classification == "other" and not looks_like_results_heading(heading):
            record_excluded_section(excluded, heading, "inside_methods_block", classification, original_text)
            continue
        if saw_discussion and classification != "discussion":
            record_excluded_section(excluded, heading, "after_discussion_end_matter_guard", classification, original_text)
            continue
        if classification in {"introduction", "body"}:
            in_methods_block = False
            filtered.append({"title": "Introduction", "text": text, "narrative_class": classification})
            saw_intro_like = True
            continue
        if classification == "discussion":
            in_methods_block = False
            filtered.append({"title": "Discussion", "text": text, "narrative_class": classification})
            saw_discussion = True
            continue
        if classification == "results_container":
            in_methods_block = False
            filtered.append({"title": "Results", "text": text, "narrative_class": classification})
            saw_results_container = True
            continue
        if classification == "results":
            in_methods_block = False
            if not saw_results_container:
                filtered.append({"title": "Results", "text": "", "narrative_class": "results_container"})
                saw_results_container = True
            filtered.append({"title": heading or "Results", "text": text, "narrative_class": classification})
            continue

        if should_skip_protocol_like_section(heading, text, saw_results_container=saw_results_container):
            in_methods_block = True
            record_excluded_section(excluded, heading, "protocol_or_procedural_section", classification, original_text)
            continue
        if looks_like_results_heading(heading):
            if not saw_results_container:
                filtered.append({"title": "Results", "text": "", "narrative_class": "results_container"})
                saw_results_container = True
            filtered.append({"title": heading or "Results", "text": text, "narrative_class": "results"})
            continue
        if not saw_intro_like and not saw_results_container:
            filtered.append({"title": "Introduction", "text": text, "narrative_class": "other"})
            saw_intro_like = True
            continue
        if saw_intro_like and not saw_results_container:
            filtered.append({"title": "Results", "text": "", "narrative_class": "results_container"})
            saw_results_container = True
        filtered.append({"title": heading or "Narrative", "text": text, "narrative_class": "other"})

    return [section for section in filtered if section.get("text")], excluded


def record_excluded_section(
    excluded: list[dict[str, str]],
    heading: str,
    reason: str,
    classification: str,
    text: str,
) -> None:
    excluded.append(
        {
            "title": heading or "Untitled",
            "narrative_class": classification,
            "exclusion_reason": reason,
            "char_count": len(clean_text(text)),
        }
    )


def classify_section_heading(heading: str) -> str:
    normalized = heading_classification_key(heading)
    if not normalized:
        return "other"
    if normalized == "body":
        return "body"
    if normalized in INTRODUCTION_HEADINGS:
        return "introduction"
    if normalized in DISCUSSION_HEADINGS or normalized in CONCLUSION_HEADINGS:
        return "discussion"
    if normalized in RESULTS_CONTAINER_HEADINGS:
        return "results_container"
    if normalized in MIXED_KEEP_HEADINGS or normalized in RESULTS_LIKE_HEADINGS:
        return "results"
    if normalized in METHODS_CONTAINER_HEADINGS:
        return "methods_container"
    if normalized in METHODS_HEADINGS:
        return "methods"
    if normalized in END_MATTER_HEADINGS:
        return "skip"
    if looks_like_methods_heading(heading):
        return "methods"
    if looks_like_results_heading(heading):
        return "results"
    if re.match(r"^(fig\.?|figure|table|extended data|source data)\b", normalized):
        return "skip"
    if any(marker in normalized for marker in ("figure", "fig ", "table", "supplement", "reference")):
        return "skip"
    return "other"


def suppress_container_sections(sections: list[dict[str, str]]) -> list[dict[str, str]]:
    filtered = []
    for index, section in enumerate(sections):
        classification = classify_section_heading(str(section.get("title") or ""))
        if classification == "results_container" and has_following_same_group(
            sections, index, {"results", "other"}, stop_at={"discussion", "methods_container", "methods", "skip"}
        ):
            continue
        filtered.append(section)
    return filtered


def has_following_same_group(
    sections: list[dict[str, str]],
    start_index: int,
    allowed_group: set[str],
    *,
    stop_at: set[str],
) -> bool:
    for section in sections[start_index + 1 :]:
        classification = classify_section_heading(str(section.get("title") or ""))
        if classification in stop_at:
            return False
        if classification in allowed_group and classification != "other":
            return True
    return False


def normalize_heading_text(text: str) -> str:
    text = re.sub(r"^\s*\d+(?:\.\d+)*\s*", "", text or "")
    return clean_text(text.strip(" .:;-"))


def heading_classification_key(heading: str) -> str:
    normalized = normalize_heading_text(heading).lower()
    normalized = re.sub(r"^[ivxlcdm]+\.\s+", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def looks_like_methods_heading(heading: str) -> bool:
    normalized = heading_classification_key(heading)
    if not normalized:
        return False
    if normalized in METHODS_HEADINGS or normalized in METHODS_CONTAINER_HEADINGS:
        return True
    return any(normalized == prefix or normalized.startswith(f"{prefix} ") for prefix in METHODS_HEADING_PREFIXES)


def looks_like_methods_text_prefix(text: str) -> bool:
    prefix = clean_text(text).lower()[:360]
    if not prefix:
        return False
    method_prefixes = (
        "the present protocol conforms",
        "all enrolled patients provided informed written consent",
        "samples were collected from",
        "tissues were collected from",
        "were kindly provided by",
        "were purchased from",
        "were maintained in",
        "cells were maintained in",
        "software was employed for statistical analysis",
        "data are presented as mean",
    )
    return any(prefix.startswith(marker) for marker in method_prefixes)


def looks_like_results_heading(heading: str) -> bool:
    normalized = heading_classification_key(heading)
    if not normalized:
        return False
    result_markers = (
        "associated with",
        "correlates with",
        "promotes",
        "induces",
        "activates",
        "inhibits",
        "requires",
        "sensitizes",
        "sensitises",
        "enhances",
        "up-regulates",
        "up regulates",
        "down-regulates",
        "down regulates",
        "drives",
        "suppresses",
        "mediates",
        "confers",
        "resistance",
        "response",
        "efficacy",
        "safety",
        "patients",
        "treatment",
    )
    return any(marker in normalized for marker in result_markers)


def should_skip_protocol_like_section(heading: str, text: str, *, saw_results_container: bool) -> bool:
    normalized = heading_classification_key(heading)
    if looks_like_methods_heading(normalized):
        return True
    if saw_results_container and normalized in {"patients", "treatment"}:
        return False
    protocol_markers = (
        "eligibility",
        "dose escalation",
        "randomisation",
        "randomization",
        "statistical",
        "protocol",
        "assay",
        "sequencing",
        "immunoblot",
        "immunohistochemistry",
    )
    if any(marker in normalized for marker in protocol_markers):
        return True
    return looks_like_methods_text_prefix(text)


def strip_caption_like_paragraphs(text: str) -> str:
    paragraphs = paragraph_blocks(text)
    filtered = [paragraph for paragraph in paragraphs if not is_caption_like_paragraph(paragraph)]
    return "\n\n".join(filtered)


def is_caption_like_paragraph(paragraph: str) -> bool:
    lowered = clean_text(paragraph).lower()
    if lowered.startswith(("fig. ", "figure ", "table ", "source data", "extended data")):
        return True
    if "number of patients at risk" in lowered:
        return True
    return False


def strip_nontext_tail(text: str) -> str:
    paragraphs = paragraph_blocks(text)
    kept = []
    for paragraph in paragraphs:
        lowered = paragraph.lower()
        if lowered.startswith(("references ", "acknowledgements ", "acknowledgments ")):
            break
        if is_reference_like_paragraph(paragraph):
            continue
        kept.append(paragraph)
    return "\n\n".join(kept)


def is_reference_like_paragraph(paragraph: str) -> bool:
    lowered = clean_text(paragraph).lower()
    if re.match(r"^\d+\.\s+[A-Z][A-Za-z-]+", paragraph):
        return True
    if re.match(r"^\[\d+\]\s+", paragraph):
        return True
    if lowered.startswith(("doi:", "pmid:", "http://", "https://")):
        return True
    return False


def smooth_section_paragraphs(text: str) -> str:
    paragraphs = paragraph_blocks(text)
    if len(paragraphs) <= 1:
        return "\n\n".join(paragraphs)
    merged: list[str] = []
    for paragraph in paragraphs:
        normalized = clean_text(paragraph)
        if not normalized:
            continue
        if merged and should_merge_paragraph_with_previous(merged[-1], normalized):
            merged[-1] = f"{merged[-1]} {normalized}".strip()
        else:
            merged.append(normalized)
    return "\n\n".join(merged)


def should_merge_paragraph_with_previous(previous: str, current: str) -> bool:
    if len(current.split()) <= 35:
        return True
    if len(previous.split()) <= 18:
        return True
    if not re.search(r"[.!?:)]$", previous):
        return True
    if current[:1].islower():
        return True
    return False


def tei_raw_text(root: ET.Element) -> str:
    body = find_first(root, "body")
    if body is None:
        return ""
    return clean_text(" ".join(text for text in body.itertext() if text and text.strip()))


def add_pdf_report(
    rows: list[dict[str, str]],
    row: dict[str, str],
    pdf_path: Path,
    tei_path: Path | None,
    normalized_path: Path | None,
    parse_status: str,
    notes: str,
) -> None:
    item = {
        "paper_id": row["paper_id"],
        "pmid": row["pmid"],
        "doi": row["doi"],
        "title": row["title"],
        "pdf_path": str(pdf_path),
        "tei_path": str(tei_path or ""),
        "normalized_path": str(normalized_path or ""),
        "parse_status": parse_status,
        "notes": notes,
    }
    rows[:] = [existing for existing in rows if existing.get("paper_id") != row["paper_id"]]
    rows.append(item)


def expected_pdf_filename(row: dict[str, str]) -> str:
    if row.get("pmid"):
        return f"PMID_{safe_name(row['pmid'])}.pdf"
    return f"{safe_name(row.get('paper_id', 'paper'))}.pdf"


def tokens_for_row(row: dict[str, str]) -> list[str]:
    values = [row.get("paper_id"), row.get("pmid"), row.get("pmcid"), row.get("doi")]
    title = row.get("title", "")
    if title:
        values.extend([title, comparable_text(title)])
    return [value for value in values if value]


def normalize_pmcid(value: str) -> str:
    value = (value or "").strip()
    if value.upper().startswith("PMC"):
        return value[3:]
    return value


def is_pdf_url(url: str) -> bool:
    lower = (url or "").lower()
    return lower.endswith(".pdf") or ".pdf?" in lower or "/pdf" in lower


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "paper"


def comparable_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def append_note(existing: str, extra: str) -> str:
    existing = (existing or "").strip()
    extra = (extra or "").strip()
    if not existing:
        return extra
    if not extra or extra in existing:
        return existing
    return f"{existing} {extra}"


def clean_cell(value: object) -> str:
    return "" if value is None else str(value)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fieldnames} for row in rows])


def count_status(rows: list[dict[str, str]], status: str) -> int:
    return sum(1 for row in rows if row.get("ingestion_status") == status)


if __name__ == "__main__":
    raise SystemExit(main())

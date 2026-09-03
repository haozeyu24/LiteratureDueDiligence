#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from workflow_state import connect, db_path, timestamp


REGISTER_HEADER_9 = (
    "| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | "
    "venue_trust_label | discovery_provenance | notes |"
)
REGISTER_HEADER_8 = (
    "| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | "
    "venue_trust_label | notes |"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize workflow_state.sqlite from a run draft and subsection retrieval artifacts."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    draft_path = run_dir / "drafts" / "initial_review.md"
    if not draft_path.exists():
        print(f"ERROR: missing draft: {draft_path}", file=sys.stderr)
        return 1

    subsections = parse_draft(draft_path)
    now = timestamp()
    with connect(run_dir) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO workflow_steps(
                step_name, status, started_at, completed_at, validation_status, notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "subsection_retrieval",
                "initialized",
                now,
                "",
                "not_validated",
                "SQLite state initialized from initial_review.md.",
            ),
        )
        for subsection in subsections:
            connection.execute(
                """
                INSERT OR REPLACE INTO subsections(
                    subsection_id, chapter_index, chapter_title, subsection_index,
                    subsection_title, subsection_scope_note, retrieval_status, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    subsection["subsection_id"],
                    subsection["chapter_index"],
                    subsection["chapter_title"],
                    subsection["subsection_index"],
                    subsection["subsection_title"],
                    subsection["scope_note"],
                    "not_started",
                    now,
                ),
            )
            for citation in subsection["citations"]:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO draft_citations(
                        citation_id, subsection_id, citation, pmid, doi, evidence_role,
                        draft_access_status, venue_trust_label, discovery_provenance,
                        notes, recall_status, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        citation["citation_id"],
                        subsection["subsection_id"],
                        citation["citation"],
                        citation["PMID"],
                        citation["DOI"],
                        citation["evidence_role"],
                        citation["draft_access_status"],
                        citation["venue_trust_label"],
                        citation["discovery_provenance"],
                        citation["notes"],
                        "not_checked",
                        now,
                    ),
                )
            known_count = sum(
                1
                for citation in subsection["citations"]
                if citation.get("citation") != "citation needed"
            )
            full_text_needed_count = sum(
                1
                for citation in subsection["citations"]
                if citation.get("draft_access_status") == "full_text_needed_for_verification"
            )
            connection.execute(
                """
                INSERT OR REPLACE INTO subsection_metrics(
                    subsection_id, queries_planned, queries_run,
                    total_pubmed_returned, total_collected_for_review,
                    draft_known_citation_count, draft_citations_recovered,
                    draft_citation_recall_rate, abstracts_reviewed,
                    abstract_include_primary_count, abstract_include_context_count,
                    abstract_uncertain_full_text_needed_count, abstract_rejected_count,
                    abstract_rejection_rate, rescue_reviewed, rescue_promoted_count,
                    final_literature_set_count, full_text_download_queue_count,
                    controller_status, notes, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    subsection["subsection_id"],
                    0,
                    0,
                    "unknown",
                    "unknown",
                    known_count,
                    "unknown",
                    "unknown",
                    0,
                    0,
                    0,
                    0,
                    0,
                    "unknown",
                    0,
                    0,
                    0,
                    full_text_needed_count,
                    "not_run",
                    "Initialized from draft citation register.",
                    now,
                ),
            )
        connection.commit()

    write_manifest(run_dir, subsections)
    write_snapshot(run_dir, subsections)
    write_artifact_readmes(run_dir)
    print(f"Initialized {db_path(run_dir)} with {len(subsections)} subsections.")
    return 0


def parse_draft(draft_path: Path) -> list[dict[str, object]]:
    lines = draft_path.read_text(encoding="utf-8").splitlines()
    subsections: list[dict[str, object]] = []
    chapter_index = 0
    chapter_title = ""
    current: dict[str, object] | None = None
    in_register = False
    saw_header = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## Chapter "):
            if current:
                subsections.append(current)
                current = None
            chapter_index += 1
            chapter_title = stripped.removeprefix("## Chapter ").strip()
            in_register = False
            saw_header = False
            continue

        if stripped.startswith("### Subsection "):
            if current:
                subsections.append(current)
            match = re.match(r"### Subsection ([^:]+):\s*(.+)", stripped)
            subsection_index = match.group(1).strip() if match else str(len(subsections) + 1)
            subsection_title = match.group(2).strip() if match else stripped.removeprefix("### ").strip()
            current = {
                "subsection_id": f"SUB{len(subsections) + 1:03d}",
                "chapter_index": chapter_index,
                "chapter_title": chapter_title,
                "subsection_index": subsection_index,
                "subsection_title": subsection_title,
                "scope_note": subsection_title,
                "prose_lines": [],
                "citations": [],
            }
            in_register = False
            saw_header = False
            continue

        if current is None:
            continue

        if stripped == "#### Citation Register":
            in_register = True
            prose = " ".join(str(line).strip() for line in current["prose_lines"])
            current["scope_note"] = prose[:240] if prose else current["subsection_title"]
            saw_header = False
            continue
        if in_register and stripped in {REGISTER_HEADER_9, REGISTER_HEADER_8}:
            saw_header = True
            continue
        if in_register and stripped.startswith("|---"):
            continue
        if in_register and stripped.startswith("|") and saw_header:
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if len(cells) == 9:
                citation = dict(
                    zip(
                        [
                            "citation_id",
                            "citation",
                            "PMID",
                            "DOI",
                            "evidence_role",
                            "draft_access_status",
                            "venue_trust_label",
                            "discovery_provenance",
                            "notes",
                        ],
                        cells,
                    )
                )
            elif len(cells) == 8:
                citation = dict(
                    zip(
                        [
                            "citation_id",
                            "citation",
                            "PMID",
                            "DOI",
                            "evidence_role",
                            "draft_access_status",
                            "venue_trust_label",
                            "notes",
                        ],
                        cells,
                    )
                )
                citation["discovery_provenance"] = (
                    "citation_needed"
                    if citation["citation"] == "citation needed"
                    else "local_prior_run"
                )
            else:
                continue
            current["citations"].append(citation)
            continue
        if in_register and (stripped.startswith("### ") or stripped.startswith("## ")):
            in_register = False
            saw_header = False
        if not in_register and stripped:
            current["prose_lines"].append(line)

    if current:
        subsections.append(current)
    return subsections


def write_manifest(run_dir: Path, subsections: list[dict[str, object]]) -> None:
    path = (
        run_dir
        / "artifacts"
        / "subsection_retrieval"
        / "01_scope"
        / "subsection_manifest.csv"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "subsection_id",
                "chapter_index",
                "chapter_title",
                "subsection_index",
                "subsection_title",
                "draft_citation_ids",
                "draft_known_pmids",
                "subsection_scope_note",
            ],
        )
        writer.writeheader()
        for subsection in subsections:
            citations = subsection["citations"]
            writer.writerow(
                {
                    "subsection_id": subsection["subsection_id"],
                    "chapter_index": subsection["chapter_index"],
                    "chapter_title": subsection["chapter_title"],
                    "subsection_index": subsection["subsection_index"],
                    "subsection_title": subsection["subsection_title"],
                    "draft_citation_ids": ";".join(c["citation_id"] for c in citations),
                    "draft_known_pmids": ";".join(
                        c["PMID"] for c in citations if c["PMID"] and c["PMID"] != "unknown"
                    ),
                    "subsection_scope_note": subsection["scope_note"],
                }
            )


def write_snapshot(run_dir: Path, subsections: list[dict[str, object]]) -> None:
    path = (
        run_dir
        / "artifacts"
        / "00_workflow_control"
        / "02_snapshots"
        / "workflow_state_snapshot.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "run_dir": str(run_dir),
        "sqlite_path": str(db_path(run_dir)),
        "status": "initialized",
        "current_step": "subsection_retrieval",
        "subsection_count": len(subsections),
        "draft_citation_count": sum(len(s["citations"]) for s in subsections),
        "next_action": "create_query_plan_and_abstract_review_rules",
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_artifact_readmes(run_dir: Path) -> None:
    artifact_dir = run_dir / "artifacts"
    control_dir = artifact_dir / "00_workflow_control"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    control_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "README.md").write_text(
        """# Workflow Artifacts

This directory stores generated workflow artifacts for the run. The folder
layout is organized by workflow stage, and each stage folder may contain
numbered subfolders for setup material, intermediate handoffs, and compact
outputs.

- `00_workflow_control/`: canonical workflow database and exported state snapshots.
- `01_draft_validation/`: checks that the initial draft followed its instructions.
- `02_subsection_retrieval/`: PubMed retrieval, candidate staging, and recall
  checks by draft subsection.
- `03_semantic_abstract_review/`: semantic title/abstract screening batches and
  merged review outputs.
- `04_primary_full_text_ingestion/`: primary full-text acquisition and
  normalization.
- `05_full_text_rag_index/`: chunks, lexical index, vector index, and hybrid
  retrieval configuration.

The canonical state is the SQLite database in
`00_workflow_control/01_state/workflow_state.sqlite`. CSV and Markdown artifacts
are used for auditability, worker handoff, and human inspection.
""",
        encoding="utf-8",
    )
    (control_dir / "README.md").write_text(
        """# Workflow Control Artifacts

This folder stores run-level control state.

- `01_state/`: canonical SQLite workflow database.
- `02_snapshots/`: exported JSON snapshots for audit and handoff.

Treat the SQLite database as canonical. Snapshot files are derived exports and
may lag until the relevant workflow step regenerates them.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())

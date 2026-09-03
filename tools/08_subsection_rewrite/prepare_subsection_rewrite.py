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
WORK_ORDER_DIR = STAGE_DIR / "02_work_orders"
REWRITTEN_DIR = STAGE_DIR / "03_rewritten_subsections"
VERIFY_DIR = STAGE_DIR / "04_verification"
OUTPUT_DIR = STAGE_DIR / "05_outputs"

SUBSECTION_MANIFEST = Path("artifacts/02_subsection_retrieval/01_scope/subsection_manifest.csv")
PACKET_DIR = Path("artifacts/06_subsection_rag_retrieval/04_paper_packets")
PAPER_MANIFEST = Path("artifacts/05_full_text_rag_index/01_chunks/paper_manifest.csv")
DRAFT_PATH = Path("drafts/initial_review.md")

MANIFEST_FIELDS = [
    "subsection_id",
    "chapter_title",
    "subsection_title",
    "original_subsection_path",
    "paper_packet_path",
    "work_order_path",
    "rewritten_path",
    "rewrite_status",
    "notes",
]

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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare Stage 8 subsection rewrite work orders from Stage 7 paper packets."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    ensure_dirs(run_dir)
    write_stage_readme(run_dir)

    with connect(run_dir) as connection:
        if not stage7_complete(connection):
            print("ERROR: Stage 7 must be complete and validation-passed before Stage 8 preparation.", file=sys.stderr)
            return 1
        manifest_rows = load_csv(run_dir / SUBSECTION_MANIFEST)
        paper_manifest = load_paper_manifest(run_dir / PAPER_MANIFEST)
        draft_sections = extract_draft_subsections(run_dir / DRAFT_PATH)
        rows = []
        for manifest in manifest_rows:
            subsection_id = manifest["subsection_id"]
            original_path = run_dir / INPUT_DIR / f"{subsection_id}.original.md"
            packet_path = run_dir / PACKET_DIR / f"{subsection_id}.md"
            work_order_path = run_dir / WORK_ORDER_DIR / f"{subsection_id}.md"
            rewritten_path = run_dir / REWRITTEN_DIR / f"{subsection_id}.md"
            draft_text = draft_sections.get(subsection_id, "").strip()
            original_path.write_text(draft_text + "\n", encoding="utf-8")
            write_work_order(work_order_path, manifest, original_path, packet_path, rewritten_path, draft_text, paper_manifest)
            rows.append(
                {
                    "subsection_id": subsection_id,
                    "chapter_title": manifest.get("chapter_title", ""),
                    "subsection_title": manifest.get("subsection_title", ""),
                    "original_subsection_path": relative_to_run(original_path, run_dir),
                    "paper_packet_path": relative_to_run(packet_path, run_dir),
                    "work_order_path": relative_to_run(work_order_path, run_dir),
                    "rewritten_path": relative_to_run(rewritten_path, run_dir),
                    "rewrite_status": "prepared",
                    "notes": "Ready for a writing agent. Rewritten subsection not yet validated.",
                }
            )

        write_csv(run_dir / INPUT_DIR / "subsection_rewrite_manifest.csv", MANIFEST_FIELDS, rows)
        write_csv(run_dir / VERIFY_DIR / "rewrite_instruction_check.csv", CHECK_FIELDS, initial_check_rows(rows))
        write_summary(run_dir, rows, "prepared")
        write_sqlite(connection, rows, "prepared")

    print(f"Stage 8 subsection rewrite prepared: subsections={len(rows)}")
    return 0


def ensure_dirs(run_dir: Path) -> None:
    for directory in (INPUT_DIR, WORK_ORDER_DIR, REWRITTEN_DIR, VERIFY_DIR, OUTPUT_DIR):
        (run_dir / directory).mkdir(parents=True, exist_ok=True)


def write_stage_readme(run_dir: Path) -> None:
    (run_dir / STAGE_DIR / "README.md").write_text(
        "# Subsection Rewrite Artifacts\n\n"
        "This stage rewrites each draft subsection from its Stage 7 paper-level "
        "evidence packet and normalized narrative full text. It is agent-run: "
        "this script prepares work orders, and writing agents produce rewritten "
        "subsection files that are then checked against the rewrite contract. "
        "Agents may work in parallel on disjoint subsection files.\n\n"
        "- `01_inputs/`: manifest and frozen original subsection text.\n"
        "- `02_work_orders/`: one rewrite instruction packet per subsection.\n"
        "- `03_rewritten_subsections/`: one rewritten subsection per subsection.\n"
        "- `04_verification/`: rewrite instruction compliance checks.\n"
        "- `05_outputs/`: compact rewrite summary.\n",
        encoding="utf-8",
    )


def stage7_complete(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        """
        SELECT status, validation_status
        FROM workflow_steps
        WHERE step_name = 'subsection_rag_retrieval'
        """
    ).fetchone()
    return bool(row and row["status"] == "complete" and row["validation_status"] == "passed")


def write_work_order(
    path: Path,
    manifest: dict[str, str],
    original_path: Path,
    packet_path: Path,
    rewritten_path: Path,
    draft_text: str,
    paper_manifest: dict[str, dict[str, str]],
) -> None:
    packet_text = packet_path.read_text(encoding="utf-8") if packet_path.exists() else ""
    narrative_sources = narrative_source_section(packet_text, paper_manifest)
    path.write_text(
        f"# Rewrite Work Order: {manifest['subsection_id']}\n\n"
        "## Task\n\n"
        "Rewrite this subsection using the original draft as framing and the "
        "paper packet plus normalized narrative full text as the evidence source. "
        "Preserve useful structure, but correct unsupported, overbroad, "
        "contradictory, or hallucinated claims. Enrich the subsection with "
        "specific experimental, clinical, cohort, model-system, or mechanistic "
        "evidence from relevant papers. Do not introduce new citations in this "
        "stage.\n\n"
        "## Required Output Path\n\n"
        f"`{rewritten_path}`\n\n"
        "## Required Rewritten File Shape\n\n"
        "```markdown\n"
        f"# Rewritten Subsection: {manifest['subsection_id']}\n\n"
        "## Paper Triage\n\n"
        "| paper_id | PMID | selection_reason | normalized_path | full_text_read_status | triage_role | support_status | key_evidence | use_in_rewrite |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
        "## Rewritten Text\n\n"
        "<evidence-grounded prose with citations inline; minimum 250 words>\n\n"
        "## Citation Register\n\n"
        "| citation_id | paper_id | PMID | DOI | evidence_use | support_status | cited_claim | study_context | model_or_population | perturbation_or_exposure | assay_or_endpoint | direction_or_result | limitation |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
        "## Evidence Use Notes\n\n"
        "<brief notes on how packet papers changed the draft>\n\n"
        "## Residual Uncertainty\n\n"
        "<remaining uncertainty, missing evidence, or human-inspection notes>\n"
        "```\n\n"
        "## Rewrite Rules\n\n"
        "- Read the normalized narrative full-text source for each packet paper when available; use chunk excerpts only as navigation aids.\n"
        "- In `full_text_read_status`, use `read_relevant_narrative`, `no_normalized_full_text`, or `not_read_not_used`.\n"
        "- Use paper-level evidence from the packet, not isolated chunk snippets alone.\n"
        "- Fill `## Paper Triage` for every selected paper in the packet before writing prose.\n"
        "- Allowed `triage_role` values are `core_support`, `partial_support`, `context_only`, `boundary_or_negative`, and `not_used`.\n"
        "- Allowed `support_status` values are `supports`, `partially_supports`, `context_only`, `contradicts`, and `insufficient_evidence`.\n"
        "- Papers with `selection_reason` values such as `stage4_primary_force_included` or `stage4_primary_recall_added_no_query_hit` must be inspected; include them in the triage table even if they become `not_used`.\n"
        "- Cite only packet papers that are used in the rewrite; do not force citations for `not_used` papers.\n"
        "- Inline citations should use traceable packet paper IDs, for example `pmid-12345678`.\n"
        "- Write at least 250 words of substantive review prose and at least 1.5x the original subsection length unless the packet has no usable evidence; in that case, explain the thin evidence in `## Residual Uncertainty`.\n"
        "- Include enough biomedical detail for later claim verification: study type, disease or model context, perturbation/exposure, assay/readout, direction of effect, and limits.\n"
        "- If fewer than two papers provide `core_support` or `partial_support`, write the subsection as weak, emerging, or speculative rather than established.\n"
        "- Avoid claiming that a paper proves a mechanism unless the packet supports that directly.\n"
        "- Keep scope generic to the user's scientific question; do not add unrelated review sections.\n"
        "- Keep citation metadata traceable with paper_id and PMID/DOI when available.\n\n"
        "## Original Subsection Path\n\n"
        f"`{original_path}`\n\n"
        "## Original Subsection\n\n"
        "```markdown\n"
        f"{draft_text}\n"
        "```\n\n"
        "## Narrative Full Text Sources\n\n"
        f"{narrative_sources}\n\n"
        "## Paper Packet\n\n"
        f"{packet_text}\n",
        encoding="utf-8",
    )


def narrative_source_section(packet_text: str, paper_manifest: dict[str, dict[str, str]]) -> str:
    ids = re.findall(r"- paper_id: `(.*?)`", packet_text)
    if not ids:
        return "No packet paper IDs found."
    lines = [
        "| paper_id | PMID | source_format | normalized_path | chunk_count |",
        "| --- | --- | --- | --- | --- |",
    ]
    for paper_id in ids:
        row = paper_manifest.get(paper_id, {})
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{paper_id}`",
                    f"`{row.get('pmid', '')}`" if row.get("pmid", "") else "",
                    row.get("source_format", ""),
                    f"`{row.get('normalized_path', '')}`" if row.get("normalized_path", "") else "",
                    row.get("chunk_count", ""),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def initial_check_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "subsection_id": row["subsection_id"],
            "rewritten_path": row["rewritten_path"],
            "check_status": "not_run",
            "has_rewritten_text": "0",
            "meets_expansion_floor": "0",
            "has_paper_triage": "0",
            "triages_all_packet_papers": "0",
            "has_citation_register": "0",
            "citation_register_traceable": "0",
            "has_inline_citations": "0",
            "inline_citations_registered": "0",
            "registered_citations_used": "0",
            "acknowledges_full_text_sources": "0",
            "has_structured_evidence_details": "0",
            "allowed_triage_roles": "0",
            "allowed_support_statuses": "0",
            "uses_packet_papers": "0",
            "has_residual_uncertainty": "0",
            "no_new_untraced_citations": "0",
            "notes": "Prepared; rewritten subsection has not been produced or checked.",
        }
        for row in rows
    ]


def write_summary(run_dir: Path, rows: list[dict[str, str]], status: str) -> None:
    (run_dir / OUTPUT_DIR / "subsection_rewrite_summary.md").write_text(
        "# Subsection Rewrite Summary\n\n"
        "## Overall Status\n\n"
        f"`{status}`\n\n"
        "## Counts\n\n"
        f"- rewrite work orders: `{len(rows)}`\n"
        "- rewritten subsections completed: `0`\n"
        "- rewrite checks passed: `0`\n\n"
        "## Downstream Use\n\n"
        "Run writing agents on the work orders, then verify rewritten subsection "
        "files before claim-level verification begins.\n",
        encoding="utf-8",
    )


def write_sqlite(connection: sqlite3.Connection, rows: list[dict[str, str]], status: str) -> None:
    now = timestamp()
    connection.execute("DELETE FROM subsection_rewrite_tasks")
    connection.execute("DELETE FROM subsection_rewrite_checks")
    for row in rows:
        connection.execute(
            """
            INSERT OR REPLACE INTO subsection_rewrite_tasks(
                subsection_id, chapter_title, subsection_title,
                original_subsection_path, paper_packet_path, work_order_path,
                rewritten_path, rewrite_status, assigned_worker, notes, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["subsection_id"],
                row["chapter_title"],
                row["subsection_title"],
                row["original_subsection_path"],
                row["paper_packet_path"],
                row["work_order_path"],
                row["rewritten_path"],
                row["rewrite_status"],
                "",
                row["notes"],
                now,
            ),
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
                row["subsection_id"],
                row["rewritten_path"],
                "not_run",
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                "Prepared.",
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
        ("subsection_rewrite", status, now, "", "pending_validation", "Stage 8 rewrite work orders prepared."),
    )
    connection.commit()


def extract_draft_subsections(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    current_id = ""
    current_lines: list[str] = []
    counter = 0
    for line in text.splitlines():
        if line.startswith("### Subsection "):
            if current_id:
                sections[current_id] = "\n".join(current_lines).strip()
            counter += 1
            current_id = f"SUB{counter:03d}"
            current_lines = [line]
            continue
        if current_id and line.startswith("## Chapter "):
            sections[current_id] = "\n".join(current_lines).strip()
            current_id = ""
            current_lines = []
            continue
        if current_id:
            current_lines.append(line)
    if current_id:
        sections[current_id] = "\n".join(current_lines).strip()
    return sections


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_paper_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    return {row.get("paper_id", ""): row for row in load_csv(path) if row.get("paper_id", "")}


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fieldnames} for row in rows])


def relative_to_run(path: Path, run_dir: Path) -> str:
    try:
        return str(path.relative_to(run_dir))
    except ValueError:
        return str(path)


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "subsection"


if __name__ == "__main__":
    raise SystemExit(main())

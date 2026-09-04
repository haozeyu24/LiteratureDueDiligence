#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_workflow_control"))

from workflow_state import connect, timestamp


ALLOWED_DECISIONS = {
    "include_primary",
    "include_context",
    "exclude_off_scope",
    "exclude_wrong_level",
    "exclude_low_quality_or_blocked",
    "uncertain_full_text_needed",
}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_MATCH = {"direct", "partial", "analogous", "none", "unknown"}
ALLOWED_FIT = {"0", "1", "2", "3"}
ALLOWED_DIRECTNESS = {
    "direct_experimental",
    "direct_clinical",
    "computational_or_indirect",
    "background_review",
    "not_evidence",
    "unknown",
}
ALLOWED_ROLES = {
    "primary_mechanism",
    "clinical_or_translational",
    "review_or_background",
    "methods_or_assay",
    "negative_or_limiting",
    "analogous_context",
    "none",
    "unknown",
}
INCLUDED_DECISIONS = {
    "include_primary",
    "include_context",
    "uncertain_full_text_needed",
}
REQUIRED_REVIEW_FIELDS = [
    "abstract_review_decision",
    "first_pass_rationale",
    "first_pass_confidence",
    "topic_match_type",
    "semantic_fit_score",
    "mechanism_match",
    "entity_context_match",
    "evidence_directness",
    "key_relevant_abstract_text",
    "missing_full_text_reason",
    "synthesis_role",
    "reviewer_id",
    "review_method",
    "reviewer_model_or_agent",
    "reviewed_at",
]
FINAL_LITERATURE_FIELDS = [
    "subsection_id",
    "paper_id",
    "PMID",
    "PMCID",
    "DOI",
    "title",
    "journal",
    "publication_year",
    "article_type",
    "abstract_review_decision",
    "evidence_role",
    "draft_access_status",
    "verified_access_status",
    "venue_trust_label",
    "source_query_ids",
    "reason",
]
FULL_TEXT_QUEUE_FIELDS = [
    "subsection_id",
    "paper_id",
    "PMID",
    "PMCID",
    "DOI",
    "title",
    "why_full_text_needed",
    "download_priority",
    "user_action",
]
SUBSECTION_DIR = Path("artifacts/02_subsection_retrieval")
RECALL_DIR = SUBSECTION_DIR / "05_recall"
OUTPUT_DIR = SUBSECTION_DIR / "06_outputs"
REVIEW_DIR = Path("artifacts/03_semantic_abstract_review")
SETUP_DIR = REVIEW_DIR / "01_setup"
REVIEWED_DIR = REVIEW_DIR / "04_reviewed_batches"
SEMANTIC_OUTPUT_DIR = REVIEW_DIR / "05_outputs"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge reviewed semantic abstract-review CSV batches into workflow_state.sqlite."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    reviewed_dir = run_dir / REVIEWED_DIR
    if not reviewed_dir.exists():
        print(f"ERROR: missing reviewed batch directory: {reviewed_dir}", file=sys.stderr)
        return 1

    errors: list[str] = []
    manifest_path = run_dir / SETUP_DIR / "batch_manifest.csv"
    status_path = run_dir / SETUP_DIR / "abstract_review_status.csv"
    manifest_rows = read_csv(manifest_path)
    status_rows = read_csv(status_path)
    expected_batches = {row["batch_id"]: row for row in manifest_rows}
    reviewed_paths = {path.stem: path for path in sorted(reviewed_dir.glob("*.csv"))}

    missing = sorted(set(expected_batches) - set(reviewed_paths))
    if missing:
        errors.append(
            f"missing reviewed CSVs for {len(missing)} batches: " + ", ".join(missing[:20])
        )
    unexpected = sorted(set(reviewed_paths) - set(expected_batches))
    if unexpected:
        errors.append(
            f"unexpected reviewed CSVs not in batch_manifest.csv: " + ", ".join(unexpected[:20])
        )
    if errors:
        return fail(errors)

    with connect(run_dir) as connection:
        validate_against_sqlite(connection, expected_batches, reviewed_paths, errors)
        if errors:
            return fail(errors)
        merge_batches(connection, run_dir, manifest_rows, status_rows, reviewed_paths)
        write_final_literature_sets(connection, run_dir)
        write_paper_review_rollup(connection, run_dir)
        write_full_text_queue(connection, run_dir)
        write_subsection_metrics_csv(connection, run_dir)
        write_merge_report(connection, run_dir, len(reviewed_paths))
        connection.commit()

    print(f"Merged {len(reviewed_paths)} reviewed batches into SQLite.")
    return 0


def fail(errors: list[str]) -> int:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def validate_against_sqlite(
    connection: sqlite3.Connection,
    expected_batches: dict[str, dict[str, str]],
    reviewed_paths: dict[str, Path],
    errors: list[str],
) -> None:
    candidate_keys = {
        (str(row["subsection_id"]), str(row["paper_id"]))
        for row in connection.execute(
            "SELECT subsection_id, paper_id FROM subsection_papers"
        ).fetchall()
    }
    seen_keys: set[tuple[str, str]] = set()
    for batch_id, path in reviewed_paths.items():
        manifest_row = expected_batches[batch_id]
        rows = read_csv(path)
        expected_count = int(manifest_row["candidate_count"])
        if len(rows) != expected_count:
            errors.append(
                f"{path.name} has {len(rows)} rows; expected {expected_count}"
            )
        for index, row in enumerate(rows, start=2):
            row_label = f"{path.name} row {index}"
            subsection_id = row.get("subsection_id", "")
            paper_id = row.get("paper_id", "")
            key = (subsection_id, paper_id)
            if subsection_id != manifest_row["subsection_id"]:
                errors.append(f"{row_label} has wrong subsection_id: {subsection_id}")
            if key not in candidate_keys:
                errors.append(f"{row_label} is not present in SQLite subsection_papers")
            if key in seen_keys:
                errors.append(f"duplicate reviewed candidate across batches: {key}")
            seen_keys.add(key)
            validate_review_row(row, row_label, errors)
    if seen_keys != candidate_keys:
        errors.append(
            f"reviewed row identity set does not match SQLite subsection_papers: "
            f"{len(seen_keys)} reviewed vs {len(candidate_keys)} candidates"
        )


def validate_review_row(row: dict[str, str], row_label: str, errors: list[str]) -> None:
    if row.get("abstract_review_decision", "") not in ALLOWED_DECISIONS:
        errors.append(f"invalid abstract_review_decision on {row_label}")
    if row.get("first_pass_confidence", "") not in ALLOWED_CONFIDENCE:
        errors.append(f"invalid first_pass_confidence on {row_label}")
    if row.get("topic_match_type", "") not in ALLOWED_MATCH:
        errors.append(f"invalid topic_match_type on {row_label}")
    if row.get("semantic_fit_score", "") not in ALLOWED_FIT:
        errors.append(f"invalid semantic_fit_score on {row_label}")
    for field in ("mechanism_match", "entity_context_match"):
        if row.get(field, "") not in ALLOWED_MATCH:
            errors.append(f"invalid {field} on {row_label}")
    if row.get("evidence_directness", "") not in ALLOWED_DIRECTNESS:
        errors.append(f"invalid evidence_directness on {row_label}")
    if row.get("synthesis_role", "") not in ALLOWED_ROLES:
        errors.append(f"invalid synthesis_role on {row_label}")
    for field in REQUIRED_REVIEW_FIELDS:
        value = row.get(field, "").strip()
        if not value or value in {"unknown", "not_reviewed"}:
            errors.append(f"{field} is not filled on {row_label}")
    if row.get("review_method", "").strip() != "llm_semantic_reading":
        errors.append(
            f"review_method on {row_label} must be `llm_semantic_reading`; "
            "heuristic or script-filled abstract review is not accepted"
        )
    reviewer_id = row.get("reviewer_id", "").strip().lower()
    if reviewer_id in {"", "unknown", "not_reviewed", "heuristic", "script", "regex", "keyword_filter"}:
        errors.append(f"reviewer_id on {row_label} does not identify an LLM worker")
    reviewer_model = row.get("reviewer_model_or_agent", "").strip().lower()
    if reviewer_model in {"", "unknown", "not_reviewed", "heuristic", "script", "regex", "keyword_filter"}:
        errors.append(f"reviewer_model_or_agent on {row_label} does not identify an LLM worker")
    if (
        row.get("venue_trust_label") == "hard_blocked"
        and row.get("abstract_review_decision") in INCLUDED_DECISIONS
    ):
        errors.append(f"hard-blocked venue retained on {row_label}")
    if row.get("abstract_review_decision") == "include_primary":
        if row.get("semantic_fit_score") != "3":
            errors.append(f"include_primary without semantic_fit_score=3 on {row_label}")
        if row.get("topic_match_type") != "direct":
            errors.append(f"include_primary without direct topic_match_type on {row_label}")
        if row.get("mechanism_match") not in {"direct", "partial"}:
            errors.append(
                f"include_primary without direct/partial mechanism_match on {row_label}"
            )
        if row.get("entity_context_match") not in {"direct", "partial"}:
            errors.append(
                f"include_primary without direct/partial entity_context_match on {row_label}"
            )
        if row.get("evidence_directness") in {
            "background_review",
            "not_evidence",
            "unknown",
        }:
            errors.append(f"include_primary has non-primary evidence_directness on {row_label}")


def merge_batches(
    connection: sqlite3.Connection,
    run_dir: Path,
    manifest_rows: list[dict[str, str]],
    status_rows: list[dict[str, str]],
    reviewed_paths: dict[str, Path],
) -> None:
    now = timestamp()
    connection.execute("DELETE FROM abstract_review_batches")
    connection.execute("DELETE FROM abstract_review_decisions")
    for row in manifest_rows:
        batch_id = row["batch_id"]
        output_path = f"{REVIEWED_DIR.as_posix()}/{batch_id}.csv"
        row["review_status"] = "review_complete"
        row["output_path"] = output_path
        if not row.get("assigned_worker") or row["assigned_worker"] == "unassigned":
            first_reviewed_row = read_csv(reviewed_paths[batch_id])[0]
            row["assigned_worker"] = first_reviewed_row.get("reviewer_id", "")
        if not row["assigned_worker"] or row["assigned_worker"] == "unassigned":
            raise ValueError(f"{batch_id} has no assigned LLM worker")
        row["notes"] = "Reviewed batch merged into SQLite."
        connection.execute(
            """
            INSERT OR REPLACE INTO abstract_review_batches(
                batch_id, subsection_id, batch_index, candidate_count,
                context_path, batch_path, review_status, assigned_worker,
                output_path, notes, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                row["subsection_id"],
                int(row["batch_index"]),
                int(row["candidate_count"]),
                row["context_path"],
                row["batch_path"],
                row["review_status"],
                row["assigned_worker"],
                row["output_path"],
                row["notes"],
                now,
            ),
        )
        for decision in read_csv(reviewed_paths[batch_id]):
            insert_decision(connection, batch_id, decision, output_path, now)
            connection.execute(
                """
                UPDATE subsection_papers
                SET abstract_review_decision = ?,
                    evidence_role = ?,
                    verified_access_status = ?,
                    reason = ?,
                    updated_at = ?
                WHERE subsection_id = ? AND paper_id = ?
                """,
                (
                    decision["abstract_review_decision"],
                    decision["synthesis_role"],
                    decision.get("verified_access_status", ""),
                    decision["first_pass_rationale"],
                    now,
                    decision["subsection_id"],
                    decision["paper_id"],
                ),
            )

    write_csv(
        run_dir / SETUP_DIR / "batch_manifest.csv",
        manifest_rows,
        list(manifest_rows[0].keys()),
    )
    status_by_id = {row["batch_id"]: row for row in status_rows}
    for row in manifest_rows:
        status_by_id[row["batch_id"]] = dict(row)
    ordered_status = [status_by_id[row["batch_id"]] for row in manifest_rows]
    write_csv(
        run_dir / SETUP_DIR / "abstract_review_status.csv",
        ordered_status,
        list(manifest_rows[0].keys()),
    )
    recompute_subsection_metrics(connection, now)
    connection.execute(
        """
        INSERT OR REPLACE INTO workflow_steps(
            step_name, status, started_at, completed_at, validation_status, notes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "semantic_abstract_review",
            "complete",
            now,
            now,
            "pending_validation",
            "All reviewed batch CSVs merged into SQLite abstract_review_decisions.",
        ),
    )


def insert_decision(
    connection: sqlite3.Connection,
    batch_id: str,
    row: dict[str, str],
    source_csv_path: str,
    now: str,
) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO abstract_review_decisions(
            batch_id, subsection_id, paper_id, pmid, pmcid, doi,
            abstract_review_decision, first_pass_rationale,
            first_pass_confidence, topic_match_type, semantic_fit_score,
            mechanism_match, entity_context_match, evidence_directness,
            key_relevant_abstract_text, missing_full_text_reason, synthesis_role,
            venue_trust_label, verified_access_status, reviewer_id,
            source_csv_path, decision_version, reviewed_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            batch_id,
            row["subsection_id"],
            row["paper_id"],
            row.get("PMID", ""),
            row.get("PMCID", ""),
            row.get("DOI", ""),
            row["abstract_review_decision"],
            row["first_pass_rationale"],
            row["first_pass_confidence"],
            row["topic_match_type"],
            int(row["semantic_fit_score"]),
            row["mechanism_match"],
            row["entity_context_match"],
            row["evidence_directness"],
            row["key_relevant_abstract_text"],
            row["missing_full_text_reason"],
            row["synthesis_role"],
            row.get("venue_trust_label", "unknown"),
            row.get("verified_access_status", "unknown"),
            row.get("reviewer_id", "abstract_review_worker"),
            source_csv_path,
            1,
            now,
            now,
        ),
    )


def recompute_subsection_metrics(connection: sqlite3.Connection, now: str) -> None:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in connection.execute(
        "SELECT subsection_id, abstract_review_decision FROM abstract_review_decisions"
    ):
        counts[str(row["subsection_id"])][str(row["abstract_review_decision"])] += 1
    queue_counts = full_text_queue_counts(connection)
    for subsection_id, counter in counts.items():
        reviewed = sum(counter.values())
        rejected = (
            counter["exclude_off_scope"]
            + counter["exclude_wrong_level"]
            + counter["exclude_low_quality_or_blocked"]
        )
        included = (
            counter["include_primary"]
            + counter["include_context"]
            + counter["uncertain_full_text_needed"]
        )
        rejection_rate = f"{rejected / reviewed:.3f}" if reviewed else "unknown"
        connection.execute(
            """
            UPDATE subsection_metrics
            SET abstracts_reviewed = ?,
                abstract_include_primary_count = ?,
                abstract_include_context_count = ?,
                abstract_uncertain_full_text_needed_count = ?,
                abstract_rejected_count = ?,
                abstract_rejection_rate = ?,
                final_literature_set_count = ?,
                full_text_download_queue_count = ?,
                controller_status = ?,
                notes = ?,
                updated_at = ?
            WHERE subsection_id = ?
            """,
            (
                reviewed,
                counter["include_primary"],
                counter["include_context"],
                counter["uncertain_full_text_needed"],
                rejected,
                rejection_rate,
                included,
                queue_counts.get(subsection_id, 0),
                "semantic_abstract_review_complete",
                "Semantic abstract review decisions merged into SQLite.",
                now,
                subsection_id,
            ),
        )


def full_text_queue_counts(connection: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    rows = included_decision_rows(connection)
    for row in rows:
        if row["abstract_review_decision"] != "include_primary":
            continue
        counts[str(row["subsection_id"])] += 1
    return counts


def included_decision_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    placeholders = ",".join("?" for _ in INCLUDED_DECISIONS)
    return connection.execute(
        f"""
        SELECT d.*, p.title, p.journal, p.publication_year, p.article_type,
               sp.draft_access_status, sp.source_query_ids
        FROM abstract_review_decisions d
        JOIN papers p ON p.paper_id = d.paper_id
        JOIN subsection_papers sp
          ON sp.subsection_id = d.subsection_id AND sp.paper_id = d.paper_id
        WHERE d.abstract_review_decision IN ({placeholders})
        ORDER BY d.subsection_id, d.abstract_review_decision, d.paper_id
        """,
        tuple(sorted(INCLUDED_DECISIONS)),
    ).fetchall()


def write_final_literature_sets(connection: sqlite3.Connection, run_dir: Path) -> None:
    rows: list[dict[str, object]] = []
    for row in included_decision_rows(connection):
        rows.append(
            {
                "subsection_id": row["subsection_id"],
                "paper_id": row["paper_id"],
                "PMID": row["pmid"],
                "PMCID": row["pmcid"] or "unknown",
                "DOI": row["doi"] or "unknown",
                "title": row["title"],
                "journal": row["journal"],
                "publication_year": row["publication_year"],
                "article_type": row["article_type"],
                "abstract_review_decision": row["abstract_review_decision"],
                "evidence_role": row["synthesis_role"],
                "draft_access_status": row["draft_access_status"] or "unknown",
                "verified_access_status": row["verified_access_status"],
                "venue_trust_label": row["venue_trust_label"] or "unknown",
                "source_query_ids": row["source_query_ids"],
                "reason": row["first_pass_rationale"],
            }
        )
    write_csv(
        run_dir / OUTPUT_DIR / "final_literature_sets.csv",
        rows,
        FINAL_LITERATURE_FIELDS,
    )


def write_full_text_queue(connection: sqlite3.Connection, run_dir: Path) -> None:
    rows_by_paper: dict[str, dict[str, object]] = {}
    subsection_ids_by_paper: dict[str, set[str]] = defaultdict(set)
    for row in included_decision_rows(connection):
        if row["abstract_review_decision"] != "include_primary":
            continue
        paper_id = str(row["paper_id"])
        subsection_ids_by_paper[paper_id].add(str(row["subsection_id"]))
        if paper_id not in rows_by_paper:
            rows_by_paper[paper_id] = {
                "subsection_id": row["subsection_id"],
                "paper_id": row["paper_id"],
                "PMID": row["pmid"],
                "PMCID": row["pmcid"] or "unknown",
                "DOI": row["doi"] or "unknown",
                "title": row["title"],
                "why_full_text_needed": "Primary evidence selected by semantic abstract review; full-text availability and usefulness must be resolved in the next step.",
                "download_priority": "high",
                "user_action": "resolve_full_text_in_next_step",
            }
    rows = []
    for paper_id, row in sorted(rows_by_paper.items()):
        row["subsection_id"] = ";".join(sorted(subsection_ids_by_paper[paper_id]))
        rows.append(row)
    if not rows:
        rows.append(
            {
                "subsection_id": "none",
                "paper_id": "none",
                "PMID": "unknown",
                "PMCID": "unknown",
                "DOI": "unknown",
                "title": "none",
                "why_full_text_needed": "No primary papers were selected for full-text ingestion.",
                "download_priority": "unknown",
                "user_action": "none",
            }
        )
    write_csv(
        run_dir / OUTPUT_DIR / "full_text_download_queue.csv",
        rows,
        FULL_TEXT_QUEUE_FIELDS,
    )


def write_paper_review_rollup(connection: sqlite3.Connection, run_dir: Path) -> None:
    now = timestamp()
    connection.execute("DELETE FROM paper_review_rollup")
    rows = connection.execute(
        """
        SELECT d.paper_id, d.pmid, d.pmcid, d.doi, p.title,
               d.abstract_review_decision, d.synthesis_role,
               d.verified_access_status
        FROM abstract_review_decisions d
        JOIN papers p ON p.paper_id = d.paper_id
        """
    ).fetchall()
    grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        grouped[str(row["paper_id"])].append(row)
    for paper_id, paper_rows in grouped.items():
        decisions = Counter(str(row["abstract_review_decision"]) for row in paper_rows)
        first = paper_rows[0]
        included = (
            decisions["include_primary"]
            + decisions["include_context"]
            + decisions["uncertain_full_text_needed"]
        )
        if decisions["include_primary"]:
            status = "globally_included_primary"
            route = "primary_full_text_candidate"
        elif decisions["uncertain_full_text_needed"]:
            status = "globally_uncertain"
            route = "uncertain_deferred"
        elif decisions["include_context"]:
            status = "globally_included_context"
            route = "context_deferred"
        elif decisions["exclude_low_quality_or_blocked"] == len(paper_rows):
            status = "globally_excluded_low_quality_or_blocked"
            route = "exclude"
        else:
            status = "globally_excluded"
            route = "exclude"
        needs_pdf = 0
        best_role = best_evidence_role(paper_rows)
        connection.execute(
            """
            INSERT OR REPLACE INTO paper_review_rollup(
                paper_id, pmid, pmcid, doi, title, global_review_status,
                included_subsection_count, primary_subsection_count,
                context_subsection_count, uncertain_subsection_count,
                excluded_subsection_count, best_evidence_role,
                full_text_ingestion_route, needs_user_pdf, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper_id,
                first["pmid"],
                first["pmcid"],
                first["doi"],
                first["title"],
                status,
                included,
                decisions["include_primary"],
                decisions["include_context"],
                decisions["uncertain_full_text_needed"],
                len(paper_rows) - included,
                best_role,
                route,
                needs_pdf,
                now,
            ),
        )


def best_evidence_role(rows: list[sqlite3.Row]) -> str:
    priority = [
        "primary_mechanism",
        "clinical_or_translational",
        "methods_or_assay",
        "negative_or_limiting",
        "analogous_context",
        "review_or_background",
        "none",
        "unknown",
    ]
    roles = {str(row["synthesis_role"]) for row in rows}
    for role in priority:
        if role in roles:
            return role
    return "unknown"


def write_subsection_metrics_csv(connection: sqlite3.Connection, run_dir: Path) -> None:
    rows = [
        dict(row)
        for row in connection.execute(
            """
            SELECT subsection_id, queries_planned, queries_run,
                   total_pubmed_returned, total_collected_for_review,
                   draft_known_citation_count, draft_citations_recovered,
                   draft_citation_recall_rate, abstracts_reviewed,
                   abstract_include_primary_count,
                   abstract_include_context_count,
                   abstract_uncertain_full_text_needed_count,
                   abstract_rejected_count, abstract_rejection_rate,
                   rescue_reviewed, rescue_promoted_count,
                   final_literature_set_count, full_text_download_queue_count,
                   controller_status, notes
            FROM subsection_metrics
            ORDER BY subsection_id
            """
        ).fetchall()
    ]
    write_csv(
        run_dir / OUTPUT_DIR / "subsection_metrics.csv",
        rows,
        [
            "subsection_id",
            "queries_planned",
            "queries_run",
            "total_pubmed_returned",
            "total_collected_for_review",
            "draft_known_citation_count",
            "draft_citations_recovered",
            "draft_citation_recall_rate",
            "abstracts_reviewed",
            "abstract_include_primary_count",
            "abstract_include_context_count",
            "abstract_uncertain_full_text_needed_count",
            "abstract_rejected_count",
            "abstract_rejection_rate",
            "rescue_reviewed",
            "rescue_promoted_count",
            "final_literature_set_count",
            "full_text_download_queue_count",
            "controller_status",
            "notes",
        ],
    )


def write_merge_report(
    connection: sqlite3.Connection,
    run_dir: Path,
    batch_count: int,
) -> None:
    total = connection.execute(
        "SELECT COUNT(*) FROM abstract_review_decisions"
    ).fetchone()[0]
    decision_counts = connection.execute(
        """
        SELECT abstract_review_decision, COUNT(*)
        FROM abstract_review_decisions
        GROUP BY abstract_review_decision
        ORDER BY abstract_review_decision
        """
    ).fetchall()
    recall = compute_deduped_draft_pmid_recall(connection, run_dir)
    status_counts = connection.execute(
        """
        SELECT global_review_status, COUNT(*)
        FROM paper_review_rollup
        GROUP BY global_review_status
        ORDER BY global_review_status
        """
    ).fetchall()
    primary_target_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM paper_review_rollup
        WHERE global_review_status = 'globally_included_primary'
        """
    ).fetchone()[0]
    reviewer_counts = connection.execute(
        """
        SELECT reviewer_id, COUNT(*)
        FROM abstract_review_decisions
        GROUP BY reviewer_id
        ORDER BY reviewer_id
        """
    ).fetchall()
    lines = [
        "# Semantic Abstract Review Merge Report",
        "",
        "## Overall Status",
        "",
        "`complete`",
        "",
        "## SQLite Merge",
        "",
        f"- reviewed batches merged: {batch_count}",
        f"- abstract review decisions stored in SQLite: {total}",
        "- source table: `abstract_review_decisions`",
        "- paper-level rollup table: `paper_review_rollup`",
        "- final literature set and user full-text queue were regenerated from SQLite.",
        "",
        "## LLM Review Provenance",
        "",
        "- required review method: `llm_semantic_reading`",
    ]
    for reviewer_id, count in reviewer_counts:
        lines.append(f"- `{reviewer_id}` reviewed rows: {count}")
    lines.extend(
        [
            "",
            "Heuristic, regex, or script-filled reviewed batches are not valid inputs to this merge step.",
            "",
        ]
    )
    lines.extend(
        [
        "## Decision Counts",
        "",
        ]
    )
    for decision, count in decision_counts:
        lines.append(f"- `{decision}`: {count}")
    lines.extend(
        [
            "",
            "## Deduped Draft-PMID Recall",
            "",
            f"- unique draft PMIDs: {recall['unique_draft_pmids']}",
            f"- recovered in PubMed candidate set: {recall['candidate_hits']} / {recall['unique_draft_pmids']} ({recall['candidate_recall']})",
            f"- retained as primary anywhere: {recall['primary_hits']} / {recall['unique_draft_pmids']} ({recall['primary_recall']})",
            f"- retained as primary/context/uncertain anywhere: {recall['retained_hits']} / {recall['unique_draft_pmids']} ({recall['retained_recall']})",
        ]
    )
    if recall["missing_primary_pmids"]:
        lines.append(
            "- draft PMIDs not in global primary cohort: "
            + ", ".join(recall["missing_primary_pmids"])
        )
    lines.extend(["", "## Paper-Level Rollup", ""])
    for status, count in status_counts:
        lines.append(f"- `{status}`: {count}")
    lines.extend(
        [
            "",
            "## Next-Step Primary Cohort",
            "",
            f"- unique primary papers for full-text ingestion: {primary_target_count}",
            "- Step 4 does not report PMC-vs-PDF counts.",
            "- Full-text availability and useful XML/PDF resolution belong to the full-text ingestion step.",
        ]
    )
    lines.append("")
    lines.append("## Downstream Readiness")
    lines.append("")
    lines.append(
        "The next step should focus only on primary papers first. It should "
        "resolve whether usable full text is available through PMC XML, PDF, "
        "or user-provided files during that step rather than inferring it here."
    )
    report_path = (
        run_dir
        / SEMANTIC_OUTPUT_DIR
        / "semantic_abstract_review_merge_report.md"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def compute_deduped_draft_pmid_recall(
    connection: sqlite3.Connection, run_dir: Path
) -> dict[str, object]:
    recall_path = (
        run_dir
        / "artifacts"
        / "02_subsection_retrieval"
        / "05_recall"
        / "draft_citation_recall_check.csv"
    )
    draft_pmids: set[str] = set()
    if recall_path.exists():
        for row in read_csv(recall_path):
            pmid = str(row.get("PMID", "")).strip()
            if pmid and pmid.lower() != "unknown":
                draft_pmids.add(pmid)
    candidate_pmids = {
        str(row[0])
        for row in connection.execute(
            """
            SELECT DISTINCT pr.pmid
            FROM subsection_papers sp
            JOIN pubmed_records pr ON pr.paper_id = sp.paper_id
            WHERE pr.pmid IS NOT NULL AND pr.pmid != ''
            """
        ).fetchall()
    }
    primary_pmids = {
        str(row[0])
        for row in connection.execute(
            """
            SELECT DISTINCT pmid
            FROM abstract_review_decisions
            WHERE abstract_review_decision = 'include_primary'
              AND pmid IS NOT NULL AND pmid != ''
            """
        ).fetchall()
    }
    retained_pmids = {
        str(row[0])
        for row in connection.execute(
            """
            SELECT DISTINCT pmid
            FROM abstract_review_decisions
            WHERE abstract_review_decision IN (
                'include_primary',
                'include_context',
                'uncertain_full_text_needed'
            )
              AND pmid IS NOT NULL AND pmid != ''
            """
        ).fetchall()
    }
    total = len(draft_pmids)
    candidate_hits = len(draft_pmids & candidate_pmids)
    primary_hits = len(draft_pmids & primary_pmids)
    retained_hits = len(draft_pmids & retained_pmids)
    return {
        "unique_draft_pmids": total,
        "candidate_hits": candidate_hits,
        "primary_hits": primary_hits,
        "retained_hits": retained_hits,
        "candidate_recall": format_rate(candidate_hits, total),
        "primary_recall": format_rate(primary_hits, total),
        "retained_recall": format_rate(retained_hits, total),
        "missing_primary_pmids": sorted(draft_pmids - primary_pmids),
    }


def format_rate(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "unknown"
    return f"{numerator / denominator:.3f}"


if __name__ == "__main__":
    raise SystemExit(main())

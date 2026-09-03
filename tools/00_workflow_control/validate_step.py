#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "validation/workflow_contract.json"
SEMANTIC_REVIEW_DIR = Path("artifacts/03_semantic_abstract_review")
SEMANTIC_SETUP_DIR = SEMANTIC_REVIEW_DIR / "01_setup"
SEMANTIC_CONTEXT_DIR = SEMANTIC_REVIEW_DIR / "02_context"
SEMANTIC_BATCH_DIR = SEMANTIC_REVIEW_DIR / "03_batches"
SEMANTIC_REVIEWED_DIR = SEMANTIC_REVIEW_DIR / "04_reviewed_batches"
SEMANTIC_OUTPUT_DIR = SEMANTIC_REVIEW_DIR / "05_outputs"
FULLTEXT_DIR = Path("artifacts/04_primary_full_text_ingestion")
FULLTEXT_TARGET_DIR = FULLTEXT_DIR / "01_targets"
FULLTEXT_DISCOVERY_DIR = FULLTEXT_DIR / "02_discovery"
FULLTEXT_PMC_DIR = FULLTEXT_DIR / "03_pmc"
FULLTEXT_PDF_DIR = FULLTEXT_DIR / "04_pdf"
FULLTEXT_USER_DIR = FULLTEXT_DIR / "05_user_pdf_request"
FULLTEXT_OUTPUT_DIR = FULLTEXT_DIR / "06_outputs"
RAG_INDEX_DIR = Path("artifacts/05_full_text_rag_index")
RAG_CHUNK_DIR = RAG_INDEX_DIR / "01_chunks"
RAG_LEXICAL_DIR = RAG_INDEX_DIR / "02_lexical"
RAG_VECTOR_DIR = RAG_INDEX_DIR / "03_vector"
RAG_HYBRID_DIR = RAG_INDEX_DIR / "04_hybrid"
RAG_OUTPUT_DIR = RAG_INDEX_DIR / "05_outputs"
SUBSECTION_RAG_DIR = Path("artifacts/06_subsection_rag_retrieval")
SUBSECTION_RAG_QUERY_DIR = SUBSECTION_RAG_DIR / "01_queries"
SUBSECTION_RAG_HIT_DIR = SUBSECTION_RAG_DIR / "02_chunk_hits"
SUBSECTION_RAG_RANKING_DIR = SUBSECTION_RAG_DIR / "03_paper_ranking"
SUBSECTION_RAG_PACKET_DIR = SUBSECTION_RAG_DIR / "04_paper_packets"
SUBSECTION_RAG_OUTPUT_DIR = SUBSECTION_RAG_DIR / "05_outputs"
SUBSECTION_REWRITE_DIR = Path("artifacts/07_subsection_rewrite")
SUBSECTION_REWRITE_INPUT_DIR = SUBSECTION_REWRITE_DIR / "01_inputs"
SUBSECTION_REWRITE_WORK_ORDER_DIR = SUBSECTION_REWRITE_DIR / "02_work_orders"
SUBSECTION_REWRITE_REWRITTEN_DIR = SUBSECTION_REWRITE_DIR / "03_rewritten_subsections"
SUBSECTION_REWRITE_VERIFY_DIR = SUBSECTION_REWRITE_DIR / "04_verification"
SUBSECTION_REWRITE_OUTPUT_DIR = SUBSECTION_REWRITE_DIR / "05_outputs"
TERMINOLOGY_DIR = Path("artifacts/08_terminology_normalization")
TERMINOLOGY_INPUT_DIR = TERMINOLOGY_DIR / "01_inputs"
TERMINOLOGY_GLOSSARY_DIR = TERMINOLOGY_DIR / "02_glossary"
TERMINOLOGY_NORMALIZED_DIR = TERMINOLOGY_DIR / "03_normalized_subsections"
TERMINOLOGY_VERIFY_DIR = TERMINOLOGY_DIR / "04_verification"
TERMINOLOGY_OUTPUT_DIR = TERMINOLOGY_DIR / "05_outputs"
REVIEW_ASSEMBLY_DIR = Path("artifacts/09_review_assembly")
REVIEW_ASSEMBLY_INPUT_DIR = REVIEW_ASSEMBLY_DIR / "01_inputs"
REVIEW_ASSEMBLY_SECTION_DIR = REVIEW_ASSEMBLY_DIR / "02_sections"
REVIEW_ASSEMBLY_VERIFY_DIR = REVIEW_ASSEMBLY_DIR / "03_verification"
REVIEW_ASSEMBLY_OUTPUT_DIR = REVIEW_ASSEMBLY_DIR / "04_outputs"
CLAIM_VERIFICATION_DIR = Path("artifacts/10_claim_verification")
CLAIM_VERIFICATION_INPUT_DIR = CLAIM_VERIFICATION_DIR / "01_inputs"
CLAIM_VERIFICATION_WORK_ORDER_DIR = CLAIM_VERIFICATION_DIR / "02_work_orders"
CLAIM_VERIFICATION_REVIEW_DIR = CLAIM_VERIFICATION_DIR / "03_claim_reviews"
CLAIM_VERIFICATION_VERIFY_DIR = CLAIM_VERIFICATION_DIR / "04_verification"
CLAIM_VERIFICATION_OUTPUT_DIR = CLAIM_VERIFICATION_DIR / "05_outputs"
CORRECTIVE_REWRITE_DIR = Path("artifacts/11_corrective_rewrite")
CORRECTIVE_REWRITE_INPUT_DIR = CORRECTIVE_REWRITE_DIR / "01_inputs"
CORRECTIVE_REWRITE_OUTPUT_DIR = CORRECTIVE_REWRITE_DIR / "02_outputs"
CORRECTIVE_REWRITE_VERIFY_DIR = CORRECTIVE_REWRITE_DIR / "03_verification"
CORRECTIVE_REWRITE_SUMMARY_DIR = CORRECTIVE_REWRITE_DIR / "04_outputs"
FINAL_REVIEW_DIR = Path("artifacts/12_final_review")
FINAL_REVIEW_INPUT_DIR = FINAL_REVIEW_DIR / "01_inputs"
FINAL_REVIEW_OUTPUT_DIR = FINAL_REVIEW_DIR / "02_outputs"
FINAL_REVIEW_VERIFY_DIR = FINAL_REVIEW_DIR / "03_verification"
FINAL_REVIEW_SUMMARY_DIR = FINAL_REVIEW_DIR / "04_outputs"
FULLTEXT_CHUNK_POLICY_NAME = "structure_aware_1000_150"
FULLTEXT_CHUNK_SIZE_CHARS = 1000
FULLTEXT_CHUNK_OVERLAP_CHARS = 150
FULLTEXT_MIN_CHUNK_CHARS = 50
FULLTEXT_MAX_CHUNK_CHARS = 1100
FULLTEXT_NARRATIVE_POLICY_NAME = "raglab_narrative_core_v1"
FULLTEXT_NARRATIVE_POLICY_REVISION = "2026-09-03-qc-excluded-sections-v5"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate that a workflow step produced only the required run artifacts."
    )
    parser.add_argument("step", help="Workflow step name, e.g. prompt_intake.")
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    parser.add_argument(
        "--allow-extra",
        action="store_true",
        help="Report unexpected files as warnings instead of errors.",
    )
    parser.add_argument(
        "--allow-later-steps",
        action="store_true",
        help=(
            "Allow artifacts declared by later workflow steps. Use this for "
            "auditing a completed run; omit it for strict immediate step gates."
        ),
    )
    args = parser.parse_args()

    contract = load_contract()
    steps = contract.get("steps", {})
    if args.step not in steps:
        print(f"ERROR: unknown step `{args.step}`.", file=sys.stderr)
        print(f"Known steps: {', '.join(sorted(steps))}", file=sys.stderr)
        return 2

    run_dir = Path(args.run_dir)
    if not run_dir.exists() or not run_dir.is_dir():
        print(f"ERROR: run directory does not exist: {run_dir}", file=sys.stderr)
        return 2

    errors: list[str] = []
    warnings: list[str] = []
    step_contract = steps[args.step]

    check_required_files(run_dir, step_contract, errors)
    check_run_screen_log(run_dir, errors)
    check_artifact_folder_layout(run_dir, ignored_file_names=set(contract.get("ignored_file_names", [])), errors=errors)
    check_step_specific_rules(args.step, run_dir, errors, args.allow_later_steps)
    ignored_file_names = set(contract.get("ignored_file_names", []))
    check_unexpected_files(
        run_dir,
        steps,
        args.step,
        step_contract,
        errors,
        warnings,
        args.allow_extra,
        args.allow_later_steps,
        ignored_file_names,
    )

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Validation failed for step `{args.step}` in {run_dir}", file=sys.stderr)
        return 1

    mark_step_validation_passed(run_dir, args.step)
    print(f"Validation passed for step `{args.step}` in {run_dir}")
    return 0


def load_contract() -> dict:
    with CONTRACT_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def mark_step_validation_passed(run_dir: Path, step_name: str) -> None:
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    if not sqlite_path.exists():
        return
    try:
        with sqlite3.connect(sqlite_path) as connection:
            connection.execute(
                """
                UPDATE workflow_steps
                SET validation_status = 'passed'
                WHERE step_name = ?
                """,
                (step_name,),
            )
    except sqlite3.Error:
        return


def check_required_files(run_dir: Path, step_contract: dict, errors: list[str]) -> None:
    for file_rule in step_contract.get("required_files", []):
        relative_path = file_rule["path"]
        path = run_dir / relative_path
        if not path.exists():
            errors.append(f"missing required file: {relative_path}")
            continue
        if not path.is_file():
            errors.append(f"required path is not a file: {relative_path}")
            continue
        min_bytes = int(file_rule.get("min_bytes", 1))
        if path.stat().st_size < min_bytes:
            errors.append(
                f"required file is too small: {relative_path} "
                f"({path.stat().st_size} bytes; expected at least {min_bytes})"
            )
        if file_rule.get("binary"):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"required file is not UTF-8 text: {relative_path}")
            continue
        for marker in file_rule.get("required_markers", []):
            if marker not in content:
                errors.append(f"required marker missing from {relative_path}: {marker}")


def check_unexpected_files(
    run_dir: Path,
    steps: dict,
    step_name: str,
    step_contract: dict,
    errors: list[str],
    warnings: list[str],
    allow_extra: bool,
    allow_later_steps: bool,
    ignored_file_names: set[str],
) -> None:
    allowed = normalize_allowed_paths(step_contract.get("allowed_paths", []))
    allowed.add("README.md")
    allowed_prefixes = tuple(
        Path(path).as_posix().rstrip("/") + "/"
        for path in step_contract.get("allowed_path_prefixes", [])
    )
    later_allowed: set[str] = set()
    later_allowed_prefixes: tuple[str, ...] = ()
    if allow_later_steps:
        later_allowed, later_allowed_prefixes = get_later_step_allowed_paths(
            steps, step_name
        )
    disallowed_patterns = step_contract.get("disallowed_path_patterns", [])

    for path in sorted(run_dir.rglob("*")):
        if path.is_dir():
            continue
        if path.name in ignored_file_names:
            continue
        relative = path.relative_to(run_dir).as_posix()
        is_current_allowed = relative in allowed or relative.startswith(allowed_prefixes)
        is_later_allowed = (
            relative in later_allowed or relative.startswith(later_allowed_prefixes)
        )
        if is_later_allowed and not is_current_allowed:
            continue
        if not is_current_allowed:
            message = f"unexpected file for this step: {relative}"
            if allow_extra:
                warnings.append(message)
            else:
                errors.append(message)
        for pattern in disallowed_patterns:
            if pattern in relative:
                message = f"disallowed file for this step: {relative} matches `{pattern}`"
                if allow_extra:
                    warnings.append(message)
                else:
                    errors.append(message)


def normalize_allowed_paths(paths: list[str]) -> set[str]:
    return {Path(path).as_posix() for path in paths}


def get_later_step_allowed_paths(
    steps: dict, step_name: str
) -> tuple[set[str], tuple[str, ...]]:
    step_names = list(steps)
    try:
        step_index = step_names.index(step_name)
    except ValueError:
        return set(), ()

    allowed: set[str] = set()
    prefixes: list[str] = []
    for later_step_name in step_names[step_index + 1 :]:
        later_contract = steps[later_step_name]
        allowed.update(normalize_allowed_paths(later_contract.get("allowed_paths", [])))
        prefixes.extend(
            Path(path).as_posix().rstrip("/") + "/"
            for path in later_contract.get("allowed_path_prefixes", [])
        )
    return allowed, tuple(prefixes)


def check_step_specific_rules(
    step: str, run_dir: Path, errors: list[str], allow_later_steps: bool
) -> None:
    if step == "initial_review_draft":
        check_initial_review_draft(run_dir, errors)
    if step == "subsection_retrieval":
        check_subsection_retrieval(run_dir, errors, allow_later_steps)
    if step == "semantic_abstract_review_preflight":
        check_semantic_abstract_review_preflight(run_dir, errors, allow_later_steps)
    if step == "semantic_abstract_review_setup":
        check_semantic_abstract_review_setup(run_dir, errors, allow_later_steps)
    if step == "semantic_abstract_review_pilot":
        check_semantic_abstract_review_pilot(run_dir, errors)
    if step == "semantic_abstract_review_complete":
        check_semantic_abstract_review_complete(run_dir, errors)
    if step == "primary_full_text_ingestion":
        check_primary_full_text_ingestion(run_dir, errors)
    if step == "full_text_rag_index":
        check_full_text_rag_index(run_dir, errors)
    if step == "subsection_rag_retrieval":
        check_subsection_rag_retrieval(run_dir, errors)
    if step == "subsection_rewrite_setup":
        check_subsection_rewrite_setup(run_dir, errors, allow_later_steps)
    if step == "subsection_rewrite":
        check_subsection_rewrite(run_dir, errors)
    if step == "terminology_normalization":
        check_terminology_normalization(run_dir, errors)
    if step == "review_assembly":
        check_review_assembly(run_dir, errors)
    if step == "claim_verification_setup":
        check_claim_verification_setup(run_dir, errors, allow_later_steps)
    if step == "claim_verification":
        check_claim_verification(run_dir, errors)
    if step == "corrective_rewrite":
        check_corrective_rewrite(run_dir, errors)
    if step == "final_review":
        check_final_review(run_dir, errors)


def check_run_screen_log(run_dir: Path, errors: list[str]) -> None:
    log_path = run_dir / "logs" / "agent_screen_log.md"
    if not log_path.exists():
        errors.append("missing run screen log: logs/agent_screen_log.md")
        return
    if not log_path.is_file():
        errors.append("run screen log path is not a file: logs/agent_screen_log.md")
        return
    if log_path.stat().st_size < 80:
        errors.append("run screen log is too small: logs/agent_screen_log.md")
        return
    try:
        text = log_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append("run screen log is not UTF-8 text: logs/agent_screen_log.md")
        return
    if "# Agent Screen Log" not in text:
        errors.append("run screen log missing marker: # Agent Screen Log")
    if "## " not in text:
        errors.append("run screen log has no timestamped entries")


def check_artifact_folder_layout(
    run_dir: Path, ignored_file_names: set[str], errors: list[str]
) -> None:
    artifact_dir = run_dir / "artifacts"
    if not artifact_dir.exists():
        return
    if not artifact_dir.is_dir():
        errors.append("artifacts exists but is not a directory")
        return

    root_allowed_files = {"README.md"} | ignored_file_names
    for child in artifact_dir.iterdir():
        if child.is_file() and child.name not in root_allowed_files:
            errors.append(
                "artifact root has loose file outside README: "
                f"{child.relative_to(run_dir).as_posix()}"
            )
        if child.is_dir() and not re.match(r"^\d{2}_[a-z0-9_]+$", child.name):
            errors.append(
                "artifact root stage folder is not numbered snake_case: "
                f"{child.relative_to(run_dir).as_posix()}"
            )

    for stage_dir in sorted(path for path in artifact_dir.iterdir() if path.is_dir()):
        stage_allowed_files = {"README.md"} | ignored_file_names
        for child in stage_dir.iterdir():
            if child.is_file() and child.name not in stage_allowed_files:
                errors.append(
                    "artifact stage has loose file outside numbered folders: "
                    f"{child.relative_to(run_dir).as_posix()}"
                )
            if child.is_dir() and not re.match(r"^\d{2}_[a-z0-9_]+$", child.name):
                errors.append(
                    "artifact stage subfolder is not numbered snake_case: "
                    f"{child.relative_to(run_dir).as_posix()}"
                )

    for directory in sorted(path for path in artifact_dir.rglob("*") if path.is_dir()):
        relative = directory.relative_to(run_dir).as_posix()
        if relative.startswith("artifacts/05_full_text_rag_index/03_vector/01_qdrant/"):
            continue
        if not re.match(r"^\d{2}_[a-z0-9_]+$", directory.name):
            errors.append(
                "artifact directory is not numbered snake_case: "
                f"{relative}"
            )


def check_initial_review_draft(run_dir: Path, errors: list[str]) -> None:
    draft_path = run_dir / "drafts/initial_review.md"
    check_path = run_dir / "artifacts/01_draft_validation/01_checks/draft_instruction_check.md"
    if not draft_path.exists() or not check_path.exists():
        return

    draft = draft_path.read_text(encoding="utf-8")
    check = check_path.read_text(encoding="utf-8")

    allowed_access = {
        "full_text_likely_available",
        "abstract_only_likely",
        "title_only_likely",
        "access_unknown",
        "full_text_needed_for_verification",
    }
    allowed_venue = {
        "reputable_or_likely_reputable",
        "uncertain",
        "preprint_server",
        "hard_blocked",
        "unknown",
    }
    allowed_provenance = {
        "searched_pubmed",
        "searched_full_text",
        "local_prior_run",
        "llm_memory",
        "citation_needed",
        "unknown",
    }
    header = "| citation_id | citation | PMID | DOI | evidence_role | draft_access_status | venue_trust_label | discovery_provenance | notes |"
    min_chapters = 6
    min_subsections = 18
    min_rows_per_register = 4
    min_words_per_subsection = 150
    min_paragraphs_per_subsection = 2

    chapter_count = sum(
        1 for line in draft.splitlines() if line.startswith("## Chapter ")
    )
    subsection_count = sum(
        1 for line in draft.splitlines() if line.startswith("### Subsection ")
    )
    if chapter_count < min_chapters:
        errors.append(f"draft has {chapter_count} chapters; expected at least {min_chapters}")
    if subsection_count < min_subsections:
        errors.append(
            f"draft has {subsection_count} subsections; expected at least {min_subsections}"
        )

    subsection_blocks = extract_subsection_prose_blocks(draft)
    for index, block in enumerate(subsection_blocks, start=1):
        word_count = count_words(block)
        paragraph_count = count_paragraphs(block)
        if word_count < min_words_per_subsection:
            errors.append(
                f"subsection {index} has {word_count} prose words before citation register; "
                f"expected at least {min_words_per_subsection}"
            )
        if paragraph_count < min_paragraphs_per_subsection:
            errors.append(
                f"subsection {index} has {paragraph_count} prose paragraphs before citation register; "
                f"expected at least {min_paragraphs_per_subsection}"
            )

    register_row_counts = count_citation_register_rows(draft, header)
    for register_index, row_count in enumerate(register_row_counts, start=1):
        if row_count < min_rows_per_register:
            errors.append(
                f"citation register {register_index} has {row_count} rows; "
                f"expected at least {min_rows_per_register}"
            )

    for line_number, line in enumerate(draft.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("|") or stripped == header:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 9:
            continue
        if set(cells) == {"---"}:
            continue
        access_status = cells[5]
        venue_label = cells[6]
        discovery_provenance = cells[7]
        if access_status not in allowed_access:
            errors.append(
                f"invalid draft_access_status on line {line_number}: {access_status}"
            )
        if venue_label not in allowed_venue:
            errors.append(
                f"invalid venue_trust_label on line {line_number}: {venue_label}"
            )
        if discovery_provenance not in allowed_provenance:
            errors.append(
                f"invalid discovery_provenance on line {line_number}: {discovery_provenance}"
            )

    if "## Overall Status" in check and "- `fail`" in check:
        errors.append("draft instruction check reports `fail`")
    if "## Ready For Claim Extraction" in check and "- `no`" in check:
        errors.append("draft instruction check reports not ready for claim extraction")


def count_citation_register_rows(draft: str, header: str) -> list[int]:
    counts: list[int] = []
    in_register = False
    current_count = 0
    saw_header = False

    for line in draft.splitlines():
        stripped = line.strip()
        if stripped == "#### Citation Register":
            if in_register and saw_header:
                counts.append(current_count)
            in_register = True
            current_count = 0
            saw_header = False
            continue
        if not in_register:
            continue
        if stripped.startswith("### ") or stripped.startswith("## "):
            if saw_header:
                counts.append(current_count)
            in_register = False
            current_count = 0
            saw_header = False
            continue
        if stripped == header:
            saw_header = True
            continue
        if not saw_header or not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if all(set(cell) <= {"-"} and cell for cell in cells):
            continue
        if len(cells) != 9:
            continue
        current_count += 1

    if in_register and saw_header:
        counts.append(current_count)
    return counts


def extract_subsection_prose_blocks(draft: str) -> list[str]:
    blocks: list[str] = []
    in_subsection = False
    in_register = False
    current_lines: list[str] = []

    for line in draft.splitlines():
        stripped = line.strip()
        if stripped.startswith("### Subsection "):
            if in_subsection and current_lines:
                blocks.append("\n".join(current_lines).strip())
            in_subsection = True
            in_register = False
            current_lines = []
            continue
        if not in_subsection:
            continue
        if stripped == "#### Citation Register":
            in_register = True
            if current_lines:
                blocks.append("\n".join(current_lines).strip())
                current_lines = []
            continue
        if stripped.startswith("## Chapter "):
            if current_lines:
                blocks.append("\n".join(current_lines).strip())
            in_subsection = False
            in_register = False
            current_lines = []
            continue
        if in_register:
            continue
        current_lines.append(line)

    if in_subsection and current_lines:
        blocks.append("\n".join(current_lines).strip())
    return blocks


def count_words(text: str) -> int:
    words = []
    for token in text.replace("/", " ").replace("-", " ").split():
        if any(character.isalnum() for character in token):
            words.append(token)
    return len(words)


def count_paragraphs(text: str) -> int:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    return len(paragraphs)


def check_subsection_retrieval(
    run_dir: Path, errors: list[str], allow_downstream_mutation: bool = False
) -> None:
    draft_path = run_dir / "drafts/initial_review.md"
    artifact_dir = run_dir / "artifacts/02_subsection_retrieval"
    manifest_path = artifact_dir / "01_scope/subsection_manifest.csv"
    query_plan_path = artifact_dir / "02_queries/query_plan.csv"
    iteration_path = artifact_dir / "02_queries/search_iteration_log.csv"
    metrics_path = artifact_dir / "06_outputs/subsection_metrics.csv"
    recall_path = artifact_dir / "05_recall/draft_citation_recall_check.csv"
    final_set_path = artifact_dir / "06_outputs/final_literature_sets.csv"
    queue_path = artifact_dir / "06_outputs/full_text_download_queue.csv"
    pubmed_records_path = artifact_dir / "03_pubmed/pubmed_records.jsonl"
    pubmed_index_path = artifact_dir / "03_pubmed/pubmed_record_index.csv"
    sqlite_path = (
        run_dir
        / "artifacts"
        / "00_workflow_control"
        / "01_state"
        / "workflow_state.sqlite"
    )
    snapshot_path = (
        run_dir
        / "artifacts"
        / "00_workflow_control"
        / "02_snapshots"
        / "workflow_state_snapshot.json"
    )

    required_paths = [
        draft_path,
        manifest_path,
        query_plan_path,
        iteration_path,
        metrics_path,
        recall_path,
        final_set_path,
        queue_path,
        pubmed_records_path,
        pubmed_index_path,
        sqlite_path,
        snapshot_path,
    ]
    if any(not path.exists() for path in required_paths):
        return

    check_workflow_state_db(sqlite_path, errors)
    check_workflow_state_snapshot(snapshot_path, errors)

    draft = draft_path.read_text(encoding="utf-8")
    draft_subsection_count = sum(
        1 for line in draft.splitlines() if line.startswith("### Subsection ")
    )
    manifest_rows = read_csv_rows(manifest_path, errors)
    query_rows = read_csv_rows(query_plan_path, errors)
    iteration_rows = read_csv_rows(iteration_path, errors)
    metrics_rows = read_csv_rows(metrics_path, errors)
    recall_rows = read_csv_rows(recall_path, errors)
    final_rows = read_csv_rows(final_set_path, errors)
    queue_rows = read_csv_rows(queue_path, errors)
    pubmed_index_rows = read_csv_rows(pubmed_index_path, errors)
    pubmed_record_count = check_pubmed_records_jsonl(pubmed_records_path, errors)

    if not manifest_rows:
        errors.append("subsection_manifest.csv has no subsection rows")
        return

    manifest_ids = [row.get("subsection_id", "") for row in manifest_rows]
    if len(manifest_rows) != draft_subsection_count:
        errors.append(
            "subsection_manifest.csv row count does not match draft subsection count: "
            f"{len(manifest_rows)} manifest rows vs {draft_subsection_count} draft subsections"
        )
    if len(set(manifest_ids)) != len(manifest_ids):
        errors.append("subsection_manifest.csv contains duplicate subsection_id values")
    for expected_index, subsection_id in enumerate(manifest_ids, start=1):
        expected_id = f"SUB{expected_index:03d}"
        if subsection_id != expected_id:
            errors.append(
                f"subsection_manifest.csv expected subsection_id {expected_id}, found {subsection_id}"
            )

    query_types_by_subsection: dict[str, set[str]] = {
        subsection_id: set() for subsection_id in manifest_ids
    }
    for row in query_rows:
        subsection_id = row.get("subsection_id", "")
        query_type = row.get("query_type", "")
        if subsection_id in query_types_by_subsection:
            query_types_by_subsection[subsection_id].add(query_type)
    for subsection_id, query_types in query_types_by_subsection.items():
        if "high_precision" not in query_types:
            errors.append(f"{subsection_id} is missing a high_precision query")
        if "mechanism_expansion" not in query_types:
            errors.append(f"{subsection_id} is missing a mechanism_expansion query")
        if "context_expansion" not in query_types:
            errors.append(f"{subsection_id} is missing a context_expansion query")
        if "recall_guard" not in query_types:
            errors.append(f"{subsection_id} is missing a recall_guard query")

    allowed_count_status = {
        "too_many",
        "acceptable",
        "too_few",
        "needs_manual_search",
        "not_run",
        "unknown",
    }
    for row in iteration_rows:
        count_status = row.get("count_status", "")
        if count_status not in allowed_count_status:
            errors.append(f"invalid count_status in search_iteration_log.csv: {count_status}")

    if len(metrics_rows) != len(manifest_rows):
        errors.append(
            "subsection_metrics.csv row count does not match subsection_manifest.csv: "
            f"{len(metrics_rows)} metrics rows vs {len(manifest_rows)} manifest rows"
        )
    metric_ids = [row.get("subsection_id", "") for row in metrics_rows]
    if set(metric_ids) != set(manifest_ids):
        errors.append("subsection_metrics.csv subsection_id set does not match manifest")
    allowed_controller_status = {
        "not_run",
        "running",
        "query_revision_needed",
        "abstract_review_needed",
        "rescue_review_needed",
        "finalized",
        "semantic_abstract_review_complete",
        "manual_search_needed",
        "blocked",
        "unknown",
    }
    for row in metrics_rows:
        status = row.get("controller_status", "")
        if status not in allowed_controller_status:
            errors.append(f"invalid controller_status in subsection_metrics.csv: {status}")
        for field in (
            "draft_citation_recall_rate",
            "abstract_rejection_rate",
        ):
            value = row.get(field, "")
            if value in {"unknown", ""}:
                continue
            try:
                numeric = float(value)
            except ValueError:
                errors.append(f"{field} must be numeric or unknown: {value}")
                continue
            if numeric < 0 or numeric > 1:
                errors.append(f"{field} must be between 0 and 1: {value}")

    allowed_recall_decisions = {
        "recovered",
        "recover_with_targeted_query",
        "drop_as_unverified_or_wrong",
        "keep_for_manual_lookup",
        "defer_to_full_text_step",
        "not_applicable",
        "unknown",
    }
    for row in recall_rows:
        decision = row.get("controller_decision", "")
        if decision not in allowed_recall_decisions:
            errors.append(
                "invalid controller_decision in draft_citation_recall_check.csv: "
                f"{decision}"
            )

    allowed_abstract_decisions = {
        "include_primary",
        "include_context",
        "exclude_off_scope",
        "exclude_wrong_level",
        "exclude_low_quality_or_blocked",
        "uncertain_full_text_needed",
        "not_reviewed",
        "unknown",
    }
    for row in final_rows:
        decision = row.get("abstract_review_decision", "")
        if decision not in allowed_abstract_decisions:
            errors.append(
                f"invalid abstract_review_decision in final_literature_sets.csv: {decision}"
            )

    allowed_priorities = {"high", "medium", "low", "unknown"}
    for row in queue_rows:
        priority = row.get("download_priority", "")
        if priority and priority not in allowed_priorities:
            errors.append(
                f"invalid download_priority in full_text_download_queue.csv: {priority}"
            )

    if pubmed_record_count <= 0:
        errors.append("pubmed_records.jsonl has no PubMed metadata records")
    if pubmed_index_rows and pubmed_record_count != len(pubmed_index_rows):
        errors.append(
            "pubmed_record_index.csv row count does not match pubmed_records.jsonl: "
            f"{len(pubmed_index_rows)} index rows vs {pubmed_record_count} JSONL records"
        )
    if not allow_downstream_mutation:
        check_sqlite_collection_counts(
            sqlite_path, pubmed_record_count, len(final_rows), errors
        )
    else:
        check_sqlite_pubmed_record_count(sqlite_path, pubmed_record_count, errors)
    if (
        not allow_downstream_mutation
        and final_rows
        and not any(row.get("abstract_review_decision") == "not_reviewed" for row in final_rows)
    ):
        errors.append(
            "final_literature_sets.csv should contain collected candidates marked not_reviewed before abstract triage"
        )


def read_csv_rows(path: Path, errors: list[str]) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except csv.Error as exc:
        errors.append(f"could not parse CSV {path}: {exc}")
        return []


def check_pubmed_records_jsonl(path: Path, errors: list[str]) -> int:
    count = 0
    seen_pmids: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        errors.append(f"could not read pubmed_records.jsonl: {exc}")
        return 0
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSONL record on line {line_number}: {exc}")
            continue
        pmid = str(record.get("pmid") or "").strip()
        if not pmid:
            errors.append(f"pubmed_records.jsonl line {line_number} is missing pmid")
        if pmid in seen_pmids:
            errors.append(f"pubmed_records.jsonl duplicate PMID: {pmid}")
        seen_pmids.add(pmid)
        for field in ("paper_id", "title", "source_query_ids", "subsection_ids"):
            if field not in record:
                errors.append(
                    f"pubmed_records.jsonl line {line_number} is missing {field}"
                )
        count += 1
    return count


def check_workflow_state_db(path: Path, errors: list[str]) -> None:
    required_tables = {
        "metadata",
        "workflow_steps",
        "subsections",
        "draft_citations",
        "pubmed_queries",
        "query_iterations",
        "papers",
        "pubmed_records",
        "subsection_papers",
        "subsection_metrics",
        "full_text_queue",
    }
    try:
        with sqlite3.connect(path) as connection:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
    except sqlite3.Error as exc:
        errors.append(f"could not read workflow_state.sqlite: {exc}")
        return
    actual_tables = {str(row[0]) for row in rows}
    missing = sorted(required_tables - actual_tables)
    if missing:
        errors.append(
            "workflow_state.sqlite is missing required tables: "
            + ", ".join(missing)
        )


def check_sqlite_collection_counts(
    path: Path, expected_pubmed_records: int, expected_subsection_papers: int, errors: list[str]
) -> None:
    try:
        with sqlite3.connect(path) as connection:
            pubmed_count = connection.execute(
                "SELECT COUNT(*) FROM pubmed_records"
            ).fetchone()[0]
            subsection_paper_count = connection.execute(
                "SELECT COUNT(*) FROM subsection_papers"
            ).fetchone()[0]
    except sqlite3.Error as exc:
        errors.append(f"could not read SQLite collection counts: {exc}")
        return
    if pubmed_count != expected_pubmed_records:
        errors.append(
            "workflow_state.sqlite pubmed_records count does not match pubmed_records.jsonl: "
            f"{pubmed_count} SQLite rows vs {expected_pubmed_records} JSONL records"
        )
    if subsection_paper_count != expected_subsection_papers:
        errors.append(
            "workflow_state.sqlite subsection_papers count does not match final_literature_sets.csv: "
            f"{subsection_paper_count} SQLite rows vs {expected_subsection_papers} final-set rows"
        )


def check_sqlite_pubmed_record_count(
    path: Path, expected_pubmed_records: int, errors: list[str]
) -> None:
    try:
        with sqlite3.connect(path) as connection:
            pubmed_count = connection.execute(
                "SELECT COUNT(*) FROM pubmed_records"
            ).fetchone()[0]
    except sqlite3.Error as exc:
        errors.append(f"could not read SQLite PubMed record count: {exc}")
        return
    if pubmed_count != expected_pubmed_records:
        errors.append(
            "workflow_state.sqlite pubmed_records count does not match pubmed_records.jsonl: "
            f"{pubmed_count} SQLite rows vs {expected_pubmed_records} JSONL records"
        )


def check_semantic_abstract_review_preflight(
    run_dir: Path, errors: list[str], allow_later_steps: bool = False
) -> None:
    artifact_dir = run_dir / "artifacts/02_subsection_retrieval"
    metrics_path = artifact_dir / "06_outputs/subsection_metrics.csv"
    final_set_path = artifact_dir / "06_outputs/final_literature_sets.csv"
    first_pass_path = artifact_dir / "04_screening/abstract_triage_first_pass.csv"
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"

    required_paths = [metrics_path, final_set_path, first_pass_path, sqlite_path]
    if any(not path.exists() for path in required_paths):
        return

    metrics_rows = read_csv_rows(metrics_path, errors)
    if not metrics_rows:
        errors.append("subsection_metrics.csv has no rows for abstract-review preflight")
        return

    ready_status = "abstract_review_needed"
    later_ready_statuses = {
        "semantic_abstract_review_setup",
        "semantic_abstract_review_pilot",
        "semantic_abstract_review_complete",
    }
    acceptable_statuses = (
        {ready_status} | later_ready_statuses if allow_later_steps else {ready_status}
    )
    non_ready = [
        row
        for row in metrics_rows
        if row.get("controller_status", "").strip() not in acceptable_statuses
    ]
    if non_ready:
        details = ", ".join(
            f"{row.get('subsection_id', 'unknown')}={row.get('controller_status', '')}"
            for row in non_ready[:20]
        )
        errors.append(
            "semantic abstract review is blocked because not every subsection "
            f"is `{ready_status}`; non-ready subsections: {details}"
        )

    final_rows = read_csv_rows(final_set_path, errors)
    if not final_rows:
        errors.append("final_literature_sets.csv has no candidate rows for abstract review")
    elif (
        not allow_later_steps
        and not all(row.get("abstract_review_decision", "") == "not_reviewed" for row in final_rows)
    ):
        errors.append(
            "semantic abstract review preflight expects final_literature_sets.csv "
            "to contain only not_reviewed candidate rows before first-pass review"
        )

    first_pass_rows = read_csv_rows(first_pass_path, errors)
    required_semantic_fields = {
        "semantic_fit_score",
        "mechanism_match",
        "entity_context_match",
        "evidence_directness",
        "key_relevant_abstract_text",
        "missing_full_text_reason",
    }
    if first_pass_rows:
        actual_fields = set(first_pass_rows[0].keys())
        missing_fields = sorted(required_semantic_fields - actual_fields)
        if missing_fields:
            errors.append(
                "abstract_triage_first_pass.csv is missing semantic-review fields: "
                + ", ".join(missing_fields)
            )

    try:
        with sqlite3.connect(sqlite_path) as connection:
            sqlite_non_ready = connection.execute(
                """
                SELECT subsection_id, controller_status
                FROM subsection_metrics
                WHERE controller_status NOT IN ({})
                ORDER BY subsection_id
                """.format(",".join("?" for _ in acceptable_statuses)),
                tuple(acceptable_statuses),
            ).fetchall()
    except sqlite3.Error as exc:
        errors.append(f"could not check SQLite subsection readiness: {exc}")
        return
    if sqlite_non_ready:
        details = ", ".join(
            f"{row[0]}={row[1]}" for row in sqlite_non_ready[:20]
        )
        errors.append(
            "SQLite subsection_metrics also blocks semantic abstract review; "
            f"non-ready subsections: {details}"
        )


def check_semantic_abstract_review_setup(
    run_dir: Path, errors: list[str], allow_later_steps: bool = False
) -> None:
    check_semantic_abstract_review_preflight(run_dir, errors, allow_later_steps)
    batch_manifest_path = run_dir / SEMANTIC_SETUP_DIR / "batch_manifest.csv"
    status_path = run_dir / SEMANTIC_SETUP_DIR / "abstract_review_status.csv"
    final_set_path = run_dir / "artifacts/02_subsection_retrieval/06_outputs/final_literature_sets.csv"
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    if not batch_manifest_path.exists() or not status_path.exists() or not final_set_path.exists():
        return

    batch_rows = read_csv_rows(batch_manifest_path, errors)
    status_rows = read_csv_rows(status_path, errors)
    final_rows = read_csv_rows(final_set_path, errors)
    if not batch_rows:
        errors.append("batch_manifest.csv has no batch rows")
        return
    if len(batch_rows) != len(status_rows):
        errors.append(
            "abstract_review_status.csv row count does not match batch_manifest.csv: "
            f"{len(status_rows)} status rows vs {len(batch_rows)} batch rows"
        )
    batch_ids = [row.get("batch_id", "") for row in batch_rows]
    if len(set(batch_ids)) != len(batch_ids):
        errors.append("batch_manifest.csv contains duplicate batch_id values")

    total_batch_candidates = 0
    seen_pairs: set[tuple[str, str]] = set()
    required_batch_fields = {
        "subsection_id",
        "paper_id",
        "PMID",
        "title",
        "abstract",
        "abstract_review_decision",
        "semantic_fit_score",
        "mechanism_match",
        "entity_context_match",
        "evidence_directness",
        "key_relevant_abstract_text",
        "missing_full_text_reason",
    }
    for row in batch_rows:
        try:
            total_batch_candidates += int(row.get("candidate_count", ""))
        except ValueError:
            errors.append(f"invalid candidate_count for batch {row.get('batch_id', '')}")
        context_path = run_dir / row.get("context_path", "")
        batch_path = run_dir / row.get("batch_path", "")
        if not context_path.exists():
            errors.append(f"missing subsection context for batch {row.get('batch_id', '')}: {context_path}")
        if not batch_path.exists():
            errors.append(f"missing batch CSV for batch {row.get('batch_id', '')}: {batch_path}")
            continue
        batch_candidate_rows = read_csv_rows(batch_path, errors)
        if batch_candidate_rows:
            missing = sorted(required_batch_fields - set(batch_candidate_rows[0]))
            if missing:
                errors.append(
                    f"{batch_path.relative_to(run_dir)} is missing fields: "
                    + ", ".join(missing)
                )
        for candidate in batch_candidate_rows:
            key = (candidate.get("subsection_id", ""), candidate.get("paper_id", ""))
            if key in seen_pairs:
                errors.append(f"duplicate candidate across batches: {key[0]} {key[1]}")
            seen_pairs.add(key)
            if candidate.get("abstract_review_decision") != "not_reviewed":
                errors.append(
                    f"{batch_path.relative_to(run_dir)} contains reviewed row before worker review"
                )
                break
    if not allow_later_steps and total_batch_candidates != len(final_rows):
        errors.append(
            "batch_manifest.csv candidate total does not match final_literature_sets.csv: "
            f"{total_batch_candidates} batch candidates vs {len(final_rows)} final-set rows"
        )
    final_pairs = {(row.get("subsection_id", ""), row.get("paper_id", "")) for row in final_rows}
    if not allow_later_steps and seen_pairs != final_pairs:
        errors.append("batch candidate coverage does not exactly match final_literature_sets.csv")
    try:
        with sqlite3.connect(sqlite_path) as connection:
            sqlite_pairs = {
                (str(row[0]), str(row[1]))
                for row in connection.execute(
                    "SELECT subsection_id, paper_id FROM subsection_papers"
                ).fetchall()
            }
    except sqlite3.Error as exc:
        errors.append(f"could not check SQLite batch coverage: {exc}")
        return
    if not allow_later_steps and seen_pairs != sqlite_pairs:
        errors.append("batch candidate coverage does not exactly match SQLite subsection_papers")


def check_semantic_abstract_review_pilot(run_dir: Path, errors: list[str]) -> None:
    check_semantic_abstract_review_setup(run_dir, errors)
    reviewed_dir = run_dir / SEMANTIC_REVIEWED_DIR
    if not reviewed_dir.exists():
        errors.append("missing reviewed_batches directory for pilot")
        return
    reviewed_paths = sorted(reviewed_dir.glob("*.csv"))
    if not reviewed_paths:
        errors.append("semantic abstract review pilot has no reviewed batch CSV")
        return
    allowed_decisions = {
        "include_primary",
        "include_context",
        "exclude_off_scope",
        "exclude_wrong_level",
        "exclude_low_quality_or_blocked",
        "uncertain_full_text_needed",
    }
    allowed_confidence = {"high", "medium", "low"}
    allowed_match = {"direct", "partial", "analogous", "none", "unknown"}
    allowed_fit = {"0", "1", "2", "3"}
    allowed_directness = {
        "direct_experimental",
        "direct_clinical",
        "computational_or_indirect",
        "background_review",
        "not_evidence",
        "unknown",
    }
    allowed_roles = {
        "primary_mechanism",
        "clinical_or_translational",
        "review_or_background",
        "methods_or_assay",
        "negative_or_limiting",
        "analogous_context",
        "none",
        "unknown",
    }
    for reviewed_path in reviewed_paths:
        input_path = review_dir / "batches" / reviewed_path.name
        if not input_path.exists():
            errors.append(f"reviewed pilot batch has no matching input batch: {reviewed_path.name}")
            continue
        input_rows = read_csv_rows(input_path, errors)
        reviewed_rows = read_csv_rows(reviewed_path, errors)
        if len(input_rows) != len(reviewed_rows):
            errors.append(
                f"{reviewed_path.name} row count mismatch: "
                f"{len(reviewed_rows)} reviewed vs {len(input_rows)} input"
            )
        input_keys = {(row.get("subsection_id", ""), row.get("paper_id", "")) for row in input_rows}
        reviewed_keys = {(row.get("subsection_id", ""), row.get("paper_id", "")) for row in reviewed_rows}
        if input_keys != reviewed_keys:
            errors.append(f"{reviewed_path.name} identifying rows do not match input batch")

        for index, row in enumerate(reviewed_rows, start=2):
            row_label = f"{reviewed_path.name} row {index}"
            if row.get("abstract_review_decision", "") not in allowed_decisions:
                errors.append(f"invalid abstract_review_decision on {row_label}")
            if row.get("first_pass_confidence", "") not in allowed_confidence:
                errors.append(f"invalid first_pass_confidence on {row_label}")
            if row.get("topic_match_type", "") not in allowed_match:
                errors.append(f"invalid topic_match_type on {row_label}")
            if row.get("semantic_fit_score", "") not in allowed_fit:
                errors.append(f"invalid semantic_fit_score on {row_label}")
            for field in ("mechanism_match", "entity_context_match"):
                if row.get(field, "") not in allowed_match:
                    errors.append(f"invalid {field} on {row_label}")
            if row.get("evidence_directness", "") not in allowed_directness:
                errors.append(f"invalid evidence_directness on {row_label}")
            if row.get("synthesis_role", "") not in allowed_roles:
                errors.append(f"invalid synthesis_role on {row_label}")
            check_primary_evidence_threshold(row, row_label, errors)
            for field in (
                "first_pass_rationale",
                "key_relevant_abstract_text",
                "missing_full_text_reason",
            ):
                value = row.get(field, "").strip()
                if not value or value in {"unknown", "not_reviewed"}:
                    errors.append(f"{field} is not filled on {row_label}")


def check_semantic_abstract_review_complete(run_dir: Path, errors: list[str]) -> None:
    manifest_path = run_dir / SEMANTIC_SETUP_DIR / "batch_manifest.csv"
    status_path = run_dir / SEMANTIC_SETUP_DIR / "abstract_review_status.csv"
    reviewed_dir = run_dir / SEMANTIC_REVIEWED_DIR
    merge_report = run_dir / SEMANTIC_OUTPUT_DIR / "semantic_abstract_review_merge_report.md"
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    final_path = run_dir / "artifacts/02_subsection_retrieval/06_outputs/final_literature_sets.csv"
    queue_path = run_dir / "artifacts/02_subsection_retrieval/06_outputs/full_text_download_queue.csv"
    metrics_path = run_dir / "artifacts/02_subsection_retrieval/06_outputs/subsection_metrics.csv"

    for path in (merge_report, final_path, queue_path):
        if not path.exists() or path.stat().st_size == 0:
            errors.append(f"missing or empty complete-step artifact: {path.relative_to(run_dir)}")
            return

    manifest_rows = read_csv_rows(manifest_path, errors)
    status_rows = read_csv_rows(status_path, errors)
    final_rows = read_csv_rows(final_path, errors)
    queue_rows = read_csv_rows(queue_path, errors)
    metrics_rows = read_csv_rows(metrics_path, errors)
    if not manifest_rows:
        return

    reviewed_paths = sorted(reviewed_dir.glob("*.csv"))
    if not reviewed_paths:
        errors.append("complete semantic abstract review has no reviewed batch CSVs")
        return
    expected_batch_ids = {row.get("batch_id", "") for row in manifest_rows}
    reviewed_batch_ids = {path.stem for path in reviewed_paths}
    if expected_batch_ids != reviewed_batch_ids:
        errors.append(
            "complete semantic abstract review requires reviewed CSVs for exactly "
            "the batch_manifest.csv batch set"
        )
    for row in manifest_rows + status_rows:
        if row.get("review_status") != "review_complete":
            errors.append(f"{row.get('batch_id', 'unknown')} is not review_complete")
        if not row.get("output_path"):
            errors.append(f"{row.get('batch_id', 'unknown')} missing output_path")

    allowed_decisions = {
        "include_primary",
        "include_context",
        "exclude_off_scope",
        "exclude_wrong_level",
        "exclude_low_quality_or_blocked",
        "uncertain_full_text_needed",
    }
    allowed_confidence = {"high", "medium", "low"}
    allowed_match = {"direct", "partial", "analogous", "none", "unknown"}
    allowed_fit = {"0", "1", "2", "3"}
    allowed_directness = {
        "direct_experimental",
        "direct_clinical",
        "computational_or_indirect",
        "background_review",
        "not_evidence",
        "unknown",
    }
    allowed_roles = {
        "primary_mechanism",
        "clinical_or_translational",
        "review_or_background",
        "methods_or_assay",
        "negative_or_limiting",
        "analogous_context",
        "none",
        "unknown",
    }
    total_reviewed_rows = 0
    reviewed_pairs: set[tuple[str, str]] = set()
    for reviewed_path in reviewed_paths:
        input_path = run_dir / SEMANTIC_BATCH_DIR / reviewed_path.name
        if not input_path.exists():
            errors.append(f"reviewed batch has no matching input batch: {reviewed_path.name}")
            continue
        input_rows = read_csv_rows(input_path, errors)
        reviewed_rows = read_csv_rows(reviewed_path, errors)
        total_reviewed_rows += len(reviewed_rows)
        if len(input_rows) != len(reviewed_rows):
            errors.append(
                f"{reviewed_path.name} row count mismatch: "
                f"{len(reviewed_rows)} reviewed vs {len(input_rows)} input"
            )
        input_keys = {(row.get("subsection_id", ""), row.get("paper_id", "")) for row in input_rows}
        reviewed_keys = {(row.get("subsection_id", ""), row.get("paper_id", "")) for row in reviewed_rows}
        if input_keys != reviewed_keys:
            errors.append(f"{reviewed_path.name} identifying rows do not match input batch")
        for key in reviewed_keys:
            if key in reviewed_pairs:
                errors.append(f"duplicate reviewed pair across batches: {key[0]} {key[1]}")
            reviewed_pairs.add(key)
        for index, row in enumerate(reviewed_rows, start=2):
            row_label = f"{reviewed_path.name} row {index}"
            if row.get("abstract_review_decision", "") not in allowed_decisions:
                errors.append(f"invalid abstract_review_decision on {row_label}")
            if row.get("first_pass_confidence", "") not in allowed_confidence:
                errors.append(f"invalid first_pass_confidence on {row_label}")
            if row.get("topic_match_type", "") not in allowed_match:
                errors.append(f"invalid topic_match_type on {row_label}")
            if row.get("semantic_fit_score", "") not in allowed_fit:
                errors.append(f"invalid semantic_fit_score on {row_label}")
            for field in ("mechanism_match", "entity_context_match"):
                if row.get(field, "") not in allowed_match:
                    errors.append(f"invalid {field} on {row_label}")
            if row.get("evidence_directness", "") not in allowed_directness:
                errors.append(f"invalid evidence_directness on {row_label}")
            if row.get("synthesis_role", "") not in allowed_roles:
                errors.append(f"invalid synthesis_role on {row_label}")
            check_primary_evidence_threshold(row, row_label, errors)
            for field in (
                "first_pass_rationale",
                "key_relevant_abstract_text",
                "missing_full_text_reason",
            ):
                value = row.get(field, "").strip()
                if not value or value in {"unknown", "not_reviewed"}:
                    errors.append(f"{field} is not filled on {row_label}")

    try:
        with sqlite3.connect(sqlite_path) as connection:
            decision_count = connection.execute(
                "SELECT COUNT(*) FROM abstract_review_decisions"
            ).fetchone()[0]
            candidate_count = connection.execute(
                "SELECT COUNT(*) FROM subsection_papers"
            ).fetchone()[0]
            candidate_pairs = {
                (str(row[0]), str(row[1]))
                for row in connection.execute(
                    "SELECT subsection_id, paper_id FROM subsection_papers"
                ).fetchall()
            }
            included_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM abstract_review_decisions
                WHERE abstract_review_decision IN (
                    'include_primary',
                    'include_context',
                    'uncertain_full_text_needed'
                )
                """
            ).fetchone()[0]
            step = connection.execute(
                """
                SELECT status, validation_status
                FROM workflow_steps
                WHERE step_name = 'semantic_abstract_review'
                """
            ).fetchone()
            distinct_reviewed_papers = connection.execute(
                "SELECT COUNT(DISTINCT paper_id) FROM abstract_review_decisions"
            ).fetchone()[0]
            rollup_count = connection.execute(
                "SELECT COUNT(*) FROM paper_review_rollup"
            ).fetchone()[0]
            primary_target_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM paper_review_rollup
                WHERE global_review_status = 'globally_included_primary'
                """
            ).fetchone()[0]
            sqlite_metrics = {
                row[0]: row[1:]
                for row in connection.execute(
                    """
                    SELECT subsection_id, abstracts_reviewed,
                           abstract_include_primary_count,
                           abstract_include_context_count,
                           abstract_uncertain_full_text_needed_count,
                           abstract_rejected_count,
                           final_literature_set_count
                    FROM subsection_metrics
                    """
                ).fetchall()
            }
    except sqlite3.Error as exc:
        errors.append(f"could not validate SQLite semantic review completion: {exc}")
        return

    if decision_count != total_reviewed_rows:
        errors.append(
            "SQLite abstract_review_decisions row count does not match reviewed CSV rows: "
            f"{decision_count} SQLite vs {total_reviewed_rows} CSV"
        )
    if decision_count != candidate_count:
        errors.append(
            "SQLite abstract_review_decisions row count does not match subsection_papers: "
            f"{decision_count} decisions vs {candidate_count} candidates"
        )
    if reviewed_pairs != candidate_pairs:
        errors.append("reviewed CSV identity set does not match SQLite subsection_papers")
    if included_count != len(final_rows):
        errors.append(
            "final_literature_sets.csv row count does not match included SQLite decisions: "
            f"{len(final_rows)} CSV vs {included_count} SQLite"
        )
    if step is None or step[0] != "complete":
        errors.append("SQLite workflow_steps semantic_abstract_review is not complete")
    if rollup_count != distinct_reviewed_papers:
        errors.append(
            "paper_review_rollup row count does not match distinct reviewed papers: "
            f"{rollup_count} rollup vs {distinct_reviewed_papers} reviewed"
        )

    metrics_by_subsection = {row.get("subsection_id", ""): row for row in metrics_rows}
    for subsection_id, values in sqlite_metrics.items():
        if subsection_id not in metrics_by_subsection:
            errors.append(f"subsection_metrics.csv missing {subsection_id}")
            continue
        csv_row = metrics_by_subsection[subsection_id]
        csv_values = (
            int(csv_row.get("abstracts_reviewed", "0") or 0),
            int(csv_row.get("abstract_include_primary_count", "0") or 0),
            int(csv_row.get("abstract_include_context_count", "0") or 0),
            int(csv_row.get("abstract_uncertain_full_text_needed_count", "0") or 0),
            int(csv_row.get("abstract_rejected_count", "0") or 0),
            int(csv_row.get("final_literature_set_count", "0") or 0),
        )
        if tuple(values) != csv_values:
            errors.append(f"SQLite metrics do not match subsection_metrics.csv for {subsection_id}")

    allowed_priorities = {"high", "medium", "low", "unknown"}
    real_queue_rows = [
        row for row in queue_rows if row.get("paper_id") not in {"", "none", None}
    ]
    if len(real_queue_rows) != primary_target_count:
        errors.append(
            "full_text_download_queue.csv row count does not match SQLite primary "
            f"full-text target count: {len(real_queue_rows)} CSV vs "
            f"{primary_target_count} SQLite"
        )
    for row in queue_rows:
        if row.get("download_priority") not in allowed_priorities:
            errors.append(
                f"invalid download_priority in full_text_download_queue.csv: "
                f"{row.get('download_priority')}"
            )


def check_primary_evidence_threshold(
    row: dict[str, str], row_label: str, errors: list[str]
) -> None:
    if row.get("abstract_review_decision") != "include_primary":
        return
    if row.get("semantic_fit_score") != "3":
        errors.append(f"include_primary without semantic_fit_score=3 on {row_label}")
    if row.get("topic_match_type") != "direct":
        errors.append(f"include_primary without direct topic_match_type on {row_label}")
    if row.get("mechanism_match") not in {"direct", "partial"}:
        errors.append(f"include_primary without direct/partial mechanism_match on {row_label}")
    if row.get("entity_context_match") not in {"direct", "partial"}:
        errors.append(
            f"include_primary without direct/partial entity_context_match on {row_label}"
        )
    if row.get("evidence_directness") in {"background_review", "not_evidence", "unknown"}:
        errors.append(f"include_primary has non-primary evidence_directness on {row_label}")


def check_primary_full_text_ingestion(run_dir: Path, errors: list[str]) -> None:
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    targets_path = run_dir / FULLTEXT_TARGET_DIR / "primary_fulltext_targets.csv"
    candidates_path = run_dir / FULLTEXT_DISCOVERY_DIR / "fulltext_source_candidates.csv"
    import_path = run_dir / FULLTEXT_OUTPUT_DIR / "import_status.csv"
    pdf_report_path = run_dir / FULLTEXT_OUTPUT_DIR / "pdf_parse_report.csv"
    narrative_qc_path = run_dir / FULLTEXT_OUTPUT_DIR / "narrative_qc_report.csv"
    manual_queue_path = run_dir / FULLTEXT_USER_DIR / "manual_pdf_queue.csv"
    pause_path = run_dir / FULLTEXT_USER_DIR / "user_pdf_pause.md"
    summary_path = run_dir / FULLTEXT_OUTPUT_DIR / "ingestion_summary.md"

    for path in (
        targets_path,
        candidates_path,
        import_path,
        pdf_report_path,
        narrative_qc_path,
        manual_queue_path,
        pause_path,
        summary_path,
    ):
        if not path.exists():
            errors.append(f"missing Stage 5 artifact: {path.relative_to(run_dir)}")
            return

    target_rows = read_csv_rows(targets_path, errors)
    candidate_rows = read_csv_rows(candidates_path, errors)
    import_rows = read_csv_rows(import_path, errors)
    manual_rows = read_csv_rows(manual_queue_path, errors)
    narrative_qc_rows = read_csv_rows(narrative_qc_path, errors)

    expected_target_fields = {
        "paper_id",
        "pmid",
        "pmcid",
        "doi",
        "title",
        "primary_subsection_count",
        "best_evidence_role",
    }
    expected_import_fields = {
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
    }
    expected_manual_fields = {
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
    }
    expected_narrative_qc_fields = {
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
    }
    if target_rows and set(target_rows[0]) != expected_target_fields:
        errors.append("primary_fulltext_targets.csv has unexpected columns")
    if import_rows and set(import_rows[0]) != expected_import_fields:
        errors.append("import_status.csv has unexpected columns")
    if manual_rows and set(manual_rows[0]) != expected_manual_fields:
        errors.append("manual_pdf_queue.csv has unexpected columns")
    if narrative_qc_rows and set(narrative_qc_rows[0]) != expected_narrative_qc_fields:
        errors.append("narrative_qc_report.csv has unexpected columns")

    target_ids = {row.get("paper_id", "") for row in target_rows}
    import_ids = {row.get("paper_id", "") for row in import_rows}
    if not target_ids:
        errors.append("Stage 5 has no primary full-text targets")
    if target_ids != import_ids:
        errors.append("import_status.csv paper_id set does not match primary_fulltext_targets.csv")
    normalized_import_ids = {
        row.get("paper_id", "")
        for row in import_rows
        if row.get("ingestion_status") == "normalized"
    }
    narrative_qc_ids = {row.get("paper_id", "") for row in narrative_qc_rows}
    if narrative_qc_ids != normalized_import_ids:
        errors.append("narrative_qc_report.csv paper_id set must match normalized import rows")
    allowed_qc_recommendations = {"pass", "watch", "inspect_for_possible_overfiltering"}
    for row in narrative_qc_rows:
        label = row.get("paper_id") or "unknown"
        if row.get("review_recommendation") not in allowed_qc_recommendations:
            errors.append(f"invalid narrative QC recommendation for {label}: {row.get('review_recommendation')}")
        for field in ("raw_chars", "narrative_chars", "kept_section_count", "excluded_section_count", "excluded_char_count", "chunk_count"):
            try:
                int(row.get(field, ""))
            except ValueError:
                errors.append(f"narrative QC row {label} has non-integer {field}")
        try:
            ratio = float(row.get("retention_ratio", ""))
            if ratio < 0:
                errors.append(f"narrative QC row {label} has negative retention_ratio")
        except ValueError:
            errors.append(f"narrative QC row {label} has non-float retention_ratio")

    allowed_ingestion_status = {"normalized", "user_pdf_required", "not_started"}
    allowed_source_format = {"pmc_xml", "pdf", "none"}
    normalized_count = 0
    unresolved_count = 0
    for row in import_rows:
        label = row.get("paper_id") or "unknown"
        status = row.get("ingestion_status", "")
        if status not in allowed_ingestion_status:
            errors.append(f"invalid ingestion_status for {label}: {status}")
        if row.get("source_format", "") not in allowed_source_format:
            errors.append(f"invalid source_format for {label}: {row.get('source_format')}")
        if status == "normalized":
            normalized_count += 1
            normalized_path = row.get("normalized_path", "")
            if row.get("source_format") not in {"pmc_xml", "pdf"}:
                errors.append(f"normalized row {label} must use pmc_xml or pdf")
            if row.get("source_format") == "pdf":
                if row.get("pdf_status") != "normalized":
                    errors.append(f"normalized PDF row {label} must set pdf_status=normalized")
                if row.get("parser_status") != "normalized":
                    errors.append(f"normalized PDF row {label} must set parser_status=normalized")
            if not normalized_path:
                errors.append(f"normalized row {label} is missing normalized_path")
                continue
            check_normalized_full_text_json(run_dir / normalized_path, label, errors)
            try:
                if int(row.get("text_char_count", "0") or 0) < 1000:
                    errors.append(f"normalized row {label} has text_char_count below 1000")
            except ValueError:
                errors.append(f"normalized row {label} has non-integer text_char_count")
        else:
            unresolved_count += 1
            if row.get("user_pdf_required") != "1":
                errors.append(f"unresolved row {label} must set user_pdf_required=1")

    manual_ids = set()
    seen_manual_group_keys = set()
    for row in manual_rows:
        linked_ids = [
            value.strip()
            for value in row.get("linked_paper_ids", "").split(";")
            if value.strip()
        ]
        if linked_ids:
            manual_ids.update(linked_ids)
        elif row.get("paper_id"):
            manual_ids.add(row["paper_id"])
        group_key = row.get("title", "").strip().lower() or row.get("paper_id", "")
        if group_key in seen_manual_group_keys:
            errors.append(f"manual_pdf_queue.csv has duplicate manual request group: {group_key}")
        seen_manual_group_keys.add(group_key)
        try:
            group_size = int(row.get("duplicate_group_size", "0") or 0)
        except ValueError:
            errors.append("manual_pdf_queue.csv duplicate_group_size must be an integer")
            group_size = 0
        if linked_ids and group_size != len(linked_ids):
            errors.append(
                "manual_pdf_queue.csv duplicate_group_size does not match linked_paper_ids "
                f"for {row.get('paper_id')}"
            )
    unresolved_ids = {
        row.get("paper_id", "")
        for row in import_rows
        if row.get("ingestion_status") != "normalized"
    }
    if manual_ids != unresolved_ids:
        errors.append("manual_pdf_queue.csv paper_id set does not match unresolved imports")

    for row in candidate_rows:
        if row.get("source_format") not in {"pmc_xml", "pdf"}:
            errors.append(
                f"fulltext_source_candidates.csv has unsupported source_format: {row.get('source_format')}"
            )
        if row.get("paper_id") and row.get("paper_id") not in target_ids:
            errors.append(
                "fulltext_source_candidates.csv contains non-primary target paper_id: "
                f"{row.get('paper_id')}"
            )

    try:
        pause_text = pause_path.read_text(encoding="utf-8")
        summary_text = summary_path.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"could not read Stage 5 pause/summary artifact: {exc}")
        return
    if manual_rows and "continue without unresolved PDFs" not in pause_text:
        errors.append("user_pdf_pause.md must describe the explicit continue-without-PDF option")
    if "# Primary Full-Text Ingestion Summary" not in summary_text:
        errors.append("ingestion_summary.md missing summary marker")

    try:
        with sqlite3.connect(sqlite_path) as connection:
            primary_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM paper_review_rollup
                WHERE global_review_status = 'globally_included_primary'
                   OR full_text_ingestion_route = 'primary_full_text_candidate'
                """
            ).fetchone()[0]
            sqlite_import_count = connection.execute(
                "SELECT COUNT(*) FROM full_text_ingestion"
            ).fetchone()[0]
            sqlite_candidate_count = connection.execute(
                "SELECT COUNT(*) FROM full_text_source_candidates"
            ).fetchone()[0]
            step = connection.execute(
                """
                SELECT status, validation_status
                FROM workflow_steps
                WHERE step_name = 'primary_full_text_ingestion'
                """
            ).fetchone()
    except sqlite3.Error as exc:
        errors.append(f"could not validate SQLite full-text ingestion state: {exc}")
        return

    if len(target_rows) != primary_count:
        errors.append(
            "primary_fulltext_targets.csv row count does not match SQLite primary cohort: "
            f"{len(target_rows)} CSV vs {primary_count} SQLite"
        )
    if sqlite_import_count != len(import_rows):
        errors.append(
            "SQLite full_text_ingestion row count does not match import_status.csv: "
            f"{sqlite_import_count} SQLite vs {len(import_rows)} CSV"
        )
    discovered_source_rows = [row for row in candidate_rows if row.get("source_url")]
    if sqlite_candidate_count != len(discovered_source_rows):
        errors.append(
            "SQLite full_text_source_candidates count must match discovered candidate rows: "
            f"{sqlite_candidate_count} SQLite vs {len(discovered_source_rows)} CSV"
        )
    if step is None:
        errors.append("SQLite workflow_steps missing primary_full_text_ingestion")
        return
    allowed_step_status = {
        "complete",
        "complete_with_deferred_user_pdfs",
        "blocked_user_pdf_required",
    }
    if step[0] not in allowed_step_status:
        errors.append(f"invalid SQLite primary_full_text_ingestion status: {step[0]}")
    if unresolved_count and step[0] == "complete":
        errors.append("Stage 5 cannot be complete while unresolved manual PDF rows remain")
    if not unresolved_count and step[0] != "complete":
        errors.append("Stage 5 should be complete when no unresolved manual PDF rows remain")
    if normalized_count + unresolved_count != len(import_rows):
        errors.append("Stage 5 normalized plus unresolved counts do not cover all imports")


def check_normalized_full_text_json(path: Path, label: str, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"normalized file for {label} does not exist: {path}")
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"could not parse normalized full-text JSON for {label}: {exc}")
        return
    raw_text = str(payload.get("raw_text") or "")
    source_format = str(payload.get("source_format") or "")
    if source_format not in {"pmc_xml", "pdf"}:
        errors.append(f"normalized JSON for {label} has unsupported source_format: {source_format}")
    source_path = str(payload.get("source_path") or "")
    if source_format == "pdf":
        if "02_parser_cache/01_grobid" not in source_path or not source_path.endswith(".tei.xml"):
            errors.append(
                f"normalized PDF JSON for {label} must use GROBID TEI as source_path"
            )
    if len(raw_text) < 1000:
        errors.append(f"normalized JSON for {label} raw_text is below 1000 characters")
    narrative_text = str(payload.get("narrative_text") or "")
    if len(narrative_text) < 200:
        errors.append(f"normalized JSON for {label} narrative_text is too short")
    narrative_policy = payload.get("narrative_policy")
    if not isinstance(narrative_policy, dict):
        errors.append(f"normalized JSON for {label} must include narrative_policy")
    elif narrative_policy.get("name") != FULLTEXT_NARRATIVE_POLICY_NAME:
        errors.append(f"normalized JSON for {label} has wrong narrative policy")
    elif narrative_policy.get("revision") != FULLTEXT_NARRATIVE_POLICY_REVISION:
        errors.append(f"normalized JSON for {label} has stale narrative policy revision")
    if "sections" not in payload or not isinstance(payload["sections"], list):
        errors.append(f"normalized JSON for {label} must include a sections list")
    else:
        for section in payload["sections"]:
            section_title = str(section.get("title") or "").lower()
            section_class = str(section.get("narrative_class") or "").lower()
            if section_class in {"methods", "methods_container", "skip"}:
                errors.append(f"normalized JSON for {label} contains excluded narrative_class {section_class}")
            if re.match(
                r"^(methods?|materials(?: and methods)?|methods and materials|patients and methods|"
                r"material and methods|method details?|star methods|star★methods|references|"
                r"acknowledg(?:e)?ments?|supplementary|supplement|figure|fig\.?|table)\b",
                section_title,
            ):
                errors.append(f"normalized JSON for {label} contains excluded section title: {section_title}")
    excluded_sections = payload.get("excluded_sections")
    if not isinstance(excluded_sections, list):
        errors.append(f"normalized JSON for {label} must include excluded_sections audit list")
    else:
        for index, section in enumerate(excluded_sections, start=1):
            if not isinstance(section, dict):
                errors.append(f"excluded section {index} for {label} is not an object")
                continue
            for field in ("title", "narrative_class", "exclusion_reason", "char_count"):
                if field not in section:
                    errors.append(f"excluded section {index} for {label} is missing {field}")
    chunk_policy = payload.get("chunk_policy")
    if not isinstance(chunk_policy, dict):
        errors.append(f"normalized JSON for {label} must include chunk_policy")
    else:
        if chunk_policy.get("name") != FULLTEXT_CHUNK_POLICY_NAME:
            errors.append(f"normalized JSON for {label} has wrong chunk policy")
        if chunk_policy.get("chunk_size_chars") != FULLTEXT_CHUNK_SIZE_CHARS:
            errors.append(f"normalized JSON for {label} has wrong chunk_size_chars")
        if chunk_policy.get("chunk_overlap_chars") != FULLTEXT_CHUNK_OVERLAP_CHARS:
            errors.append(f"normalized JSON for {label} has wrong chunk_overlap_chars")
    chunks = payload.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        errors.append(f"normalized JSON for {label} must include non-empty chunks")
        return
    for index, chunk in enumerate(chunks, start=1):
        if not isinstance(chunk, dict):
            errors.append(f"chunk {index} for {label} is not an object")
            continue
        for field in ("chunk_id", "section_index", "section_title", "text", "char_count"):
            if field not in chunk:
                errors.append(f"chunk {index} for {label} is missing {field}")
        text_length = len(str(chunk.get("text") or ""))
        if text_length < FULLTEXT_MIN_CHUNK_CHARS:
            errors.append(f"chunk {index} for {label} is too short")
        if text_length > FULLTEXT_MAX_CHUNK_CHARS:
            errors.append(f"chunk {index} for {label} is too long for 1000/150 policy")


def check_full_text_rag_index(run_dir: Path, errors: list[str]) -> None:
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    chunk_jsonl_path = run_dir / RAG_CHUNK_DIR / "chunks.jsonl"
    chunk_manifest_path = run_dir / RAG_CHUNK_DIR / "chunk_manifest.csv"
    paper_manifest_path = run_dir / RAG_CHUNK_DIR / "paper_manifest.csv"
    bm25_path = run_dir / RAG_LEXICAL_DIR / "bm25.pkl"
    bm25_summary_path = run_dir / RAG_LEXICAL_DIR / "bm25_summary.json"
    vector_summary_path = run_dir / RAG_VECTOR_DIR / "vector_index_summary.json"
    retrieval_config_path = run_dir / RAG_HYBRID_DIR / "retrieval_config.json"

    try:
        chunks = [json.loads(line) for line in chunk_jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"could not parse chunks.jsonl: {exc}")
        return
    chunk_manifest_rows = read_csv_rows(chunk_manifest_path, errors)
    paper_manifest_rows = read_csv_rows(paper_manifest_path, errors)
    if not chunks:
        errors.append("chunks.jsonl has no chunk records")
        return
    if len(chunk_manifest_rows) != len(chunks):
        errors.append(
            "chunk_manifest.csv row count does not match chunks.jsonl: "
            f"{len(chunk_manifest_rows)} CSV vs {len(chunks)} JSONL"
        )
    paper_ids = {str(chunk.get("paper_id", "")) for chunk in chunks if chunk.get("paper_id")}
    if len(paper_manifest_rows) != len(paper_ids):
        errors.append(
            "paper_manifest.csv row count does not match unique chunk papers: "
            f"{len(paper_manifest_rows)} CSV vs {len(paper_ids)} unique papers"
        )
    for index, chunk in enumerate(chunks, start=1):
        for field in (
            "chunk_uid",
            "paper_id",
            "chunk_id",
            "chunk_index",
            "source_format",
            "normalized_path",
            "section_title",
            "char_count",
            "chunk_policy",
            "text",
        ):
            if field not in chunk:
                errors.append(f"chunk record {index} is missing {field}")
        if chunk.get("chunk_policy") != FULLTEXT_CHUNK_POLICY_NAME:
            errors.append(f"chunk record {index} has wrong chunk policy")
        text = str(chunk.get("text") or "")
        if len(text) < FULLTEXT_MIN_CHUNK_CHARS:
            errors.append(f"chunk record {index} text is too short")
        if len(text) > FULLTEXT_MAX_CHUNK_CHARS:
            errors.append(f"chunk record {index} text is too long")
        if chunk.get("source_format") not in {"pmc_xml", "pdf"}:
            errors.append(f"chunk record {index} has unsupported source_format")

    if not bm25_path.exists() or bm25_path.stat().st_size < 1000:
        errors.append("bm25.pkl is missing or too small")
    try:
        bm25_summary = json.loads(bm25_summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"could not parse bm25_summary.json: {exc}")
        bm25_summary = {}
    if bm25_summary.get("status") != "complete":
        errors.append("bm25_summary.json status must be complete")
    if int(bm25_summary.get("chunk_count") or 0) != len(chunks):
        errors.append("bm25_summary.json chunk_count does not match chunks.jsonl")

    try:
        vector_summary = json.loads(vector_summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"could not parse vector_index_summary.json: {exc}")
        vector_summary = {}
    if vector_summary.get("embedding_model") != "text-embedding-3-small":
        errors.append("vector_index_summary.json must use text-embedding-3-small")
    if vector_summary.get("status") != "complete":
        errors.append("vector_index_summary.json status must be complete; Stage 6 cannot pass without API embeddings")
    if int(vector_summary.get("embedded_count") or 0) != len(chunks):
        errors.append("complete vector index must embed every chunk")

    try:
        retrieval_config = json.loads(retrieval_config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"could not parse retrieval_config.json: {exc}")
        retrieval_config = {}
    if retrieval_config.get("hybrid_fusion") != "reciprocal_rank_fusion":
        errors.append("retrieval_config.json must specify reciprocal_rank_fusion")
    paper_level = retrieval_config.get("paper_level_selection", {})
    if not isinstance(paper_level, dict) or not paper_level.get("rewrite_uses_paper_packets_not_isolated_chunks"):
        errors.append("retrieval_config.json must require paper packets for rewriting")

    try:
        with sqlite3.connect(sqlite_path) as connection:
            sqlite_chunk_count = connection.execute("SELECT COUNT(*) FROM full_text_chunks").fetchone()[0]
            sqlite_paper_count = connection.execute("SELECT COUNT(DISTINCT paper_id) FROM full_text_chunks").fetchone()[0]
            full_text_count = connection.execute(
                "SELECT COUNT(*) FROM full_text_ingestion WHERE ingestion_status = 'normalized'"
            ).fetchone()[0]
            bm25_artifact = connection.execute(
                "SELECT status, record_count FROM rag_index_artifacts WHERE artifact_name = 'bm25'"
            ).fetchone()
            step = connection.execute(
                """
                SELECT status, validation_status
                FROM workflow_steps
                WHERE step_name = 'full_text_rag_index'
                """
            ).fetchone()
    except sqlite3.Error as exc:
        errors.append(f"could not validate SQLite RAG index state: {exc}")
        return
    if sqlite_chunk_count != len(chunks):
        errors.append(f"SQLite full_text_chunks count mismatch: {sqlite_chunk_count} vs {len(chunks)}")
    if sqlite_paper_count != len(paper_ids):
        errors.append(f"SQLite full_text_chunks unique paper count mismatch: {sqlite_paper_count} vs {len(paper_ids)}")
    if full_text_count != len(paper_ids):
        errors.append(f"RAG index paper count does not match normalized full-text papers: {len(paper_ids)} vs {full_text_count}")
    if bm25_artifact is None or bm25_artifact[0] != "complete" or int(bm25_artifact[1]) != len(chunks):
        errors.append("SQLite rag_index_artifacts bm25 row is missing or inconsistent")
    if step is None:
        errors.append("SQLite workflow_steps missing full_text_rag_index")
        return
    if step[0] != "complete":
        errors.append(f"invalid SQLite full_text_rag_index status: {step[0]}")


def check_subsection_rag_retrieval(run_dir: Path, errors: list[str]) -> None:
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    manifest_path = run_dir / "artifacts/02_subsection_retrieval/01_scope/subsection_manifest.csv"
    queries_path = run_dir / SUBSECTION_RAG_QUERY_DIR / "subsection_rag_queries.csv"
    hits_path = run_dir / SUBSECTION_RAG_HIT_DIR / "subsection_chunk_hits.csv"
    rankings_path = run_dir / SUBSECTION_RAG_RANKING_DIR / "subsection_paper_rankings.csv"
    summary_path = run_dir / SUBSECTION_RAG_OUTPUT_DIR / "subsection_rag_retrieval_summary.md"
    required = [sqlite_path, manifest_path, queries_path, hits_path, rankings_path, summary_path]
    if any(not path.exists() for path in required):
        return

    manifest_rows = read_csv_rows(manifest_path, errors)
    query_rows = read_csv_rows(queries_path, errors)
    hit_rows = read_csv_rows(hits_path, errors)
    ranking_rows = read_csv_rows(rankings_path, errors)
    if not manifest_rows:
        errors.append("subsection_manifest.csv has no rows for Stage 7")
        return

    manifest_ids = {row.get("subsection_id", "") for row in manifest_rows}
    query_ids = {row.get("subsection_id", "") for row in query_rows}
    if query_ids != manifest_ids:
        errors.append("subsection_rag_queries.csv subsection coverage does not match manifest")

    if not hit_rows:
        errors.append("subsection_chunk_hits.csv has no retrieval hits")
    if not ranking_rows:
        errors.append("subsection_paper_rankings.csv has no paper rankings")
    expected_ranking_fields = {
        "subsection_id",
        "paper_rank",
        "paper_id",
        "pmid",
        "pmcid",
        "doi",
        "title",
        "source_format",
        "hybrid_score",
        "lexical_score",
        "semantic_score",
        "evidence_role_hint",
        "selected_for_packet",
        "selection_reason",
        "top_chunk_uids",
    }
    if ranking_rows and set(ranking_rows[0]) != expected_ranking_fields:
        errors.append("subsection_paper_rankings.csv has unexpected columns")

    selected_counts: dict[str, int] = {subsection_id: 0 for subsection_id in manifest_ids}
    allowed_selection_reasons = {
        "top_ranked",
        "stage4_primary_force_included",
        "stage4_primary_recall_added_no_query_hit",
        "not_selected",
    }
    for row in ranking_rows:
        subsection_id = row.get("subsection_id", "")
        if row.get("selected_for_packet") == "1":
            selected_counts[subsection_id] = selected_counts.get(subsection_id, 0) + 1
        if row.get("selection_reason") not in allowed_selection_reasons:
            errors.append(f"invalid selection_reason in subsection_paper_rankings.csv: {row.get('selection_reason')}")
        if row.get("evidence_role_hint") == "primary_for_subsection" and row.get("selected_for_packet") != "1":
            errors.append(
                f"primary_for_subsection paper must be selected: {subsection_id} {row.get('paper_id')}"
            )
        for numeric_field in ("hybrid_score", "lexical_score", "semantic_score"):
            value = row.get(numeric_field, "")
            try:
                numeric = float(value)
            except ValueError:
                errors.append(f"{numeric_field} must be numeric in subsection_paper_rankings.csv: {value}")
                continue
            if not (numeric >= 0):
                errors.append(f"{numeric_field} must be non-negative in subsection_paper_rankings.csv: {value}")

    for subsection_id in sorted(manifest_ids):
        packet_path = run_dir / SUBSECTION_RAG_PACKET_DIR / f"{subsection_id}.md"
        if not packet_path.exists():
            errors.append(f"missing Stage 7 paper packet: {packet_path.relative_to(run_dir).as_posix()}")
            continue
        if packet_path.stat().st_size < 500:
            errors.append(f"Stage 7 paper packet is too small: {packet_path.relative_to(run_dir).as_posix()}")
        text = packet_path.read_text(encoding="utf-8")
        for marker in ("# Paper Packet:", "## Retrieval Query", "## Selected Papers", "selection_reason", "## Rewrite Boundary"):
            if marker not in text:
                errors.append(
                    f"Stage 7 paper packet missing marker `{marker}`: "
                    f"{packet_path.relative_to(run_dir).as_posix()}"
                )
        if selected_counts.get(subsection_id, 0) <= 0:
            errors.append(f"{subsection_id} has no selected papers in subsection_paper_rankings.csv")

    selected_hit_count = sum(1 for row in hit_rows if row.get("selected_for_packet") == "1")
    if selected_hit_count <= 0:
        errors.append("subsection_chunk_hits.csv has no selected packet chunks")

    try:
        with sqlite3.connect(sqlite_path) as connection:
            sqlite_query_count = connection.execute("SELECT COUNT(*) FROM subsection_rag_queries").fetchone()[0]
            sqlite_hit_count = connection.execute("SELECT COUNT(*) FROM subsection_rag_chunk_hits").fetchone()[0]
            sqlite_ranking_count = connection.execute("SELECT COUNT(*) FROM subsection_rag_paper_rankings").fetchone()[0]
            step = connection.execute(
                """
                SELECT status, validation_status
                FROM workflow_steps
                WHERE step_name = 'subsection_rag_retrieval'
                """
            ).fetchone()
    except sqlite3.Error as exc:
        errors.append(f"could not validate SQLite Stage 7 state: {exc}")
        return

    if sqlite_query_count != len(query_rows):
        errors.append(f"SQLite subsection_rag_queries count mismatch: {sqlite_query_count} vs {len(query_rows)}")
    if sqlite_hit_count != len(hit_rows):
        errors.append(f"SQLite subsection_rag_chunk_hits count mismatch: {sqlite_hit_count} vs {len(hit_rows)}")
    if sqlite_ranking_count != len(ranking_rows):
        errors.append(f"SQLite subsection_rag_paper_rankings count mismatch: {sqlite_ranking_count} vs {len(ranking_rows)}")
    if step is None:
        errors.append("SQLite workflow_steps missing subsection_rag_retrieval")
    elif step[0] != "complete":
        errors.append(f"invalid SQLite subsection_rag_retrieval status: {step[0]}")


def check_subsection_rewrite(run_dir: Path, errors: list[str]) -> None:
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    manifest_path = run_dir / SUBSECTION_REWRITE_INPUT_DIR / "subsection_rewrite_manifest.csv"
    checks_path = run_dir / SUBSECTION_REWRITE_VERIFY_DIR / "rewrite_instruction_check.csv"
    summary_path = run_dir / SUBSECTION_REWRITE_OUTPUT_DIR / "subsection_rewrite_summary.md"
    stage_readme_path = run_dir / SUBSECTION_REWRITE_DIR / "README.md"
    subsection_manifest_path = run_dir / "artifacts/02_subsection_retrieval/01_scope/subsection_manifest.csv"

    required = [sqlite_path, stage_readme_path, manifest_path, checks_path, summary_path, subsection_manifest_path]
    for path in required:
        if not path.exists():
            errors.append(f"missing Stage 8 artifact: {path.relative_to(run_dir).as_posix()}")
            return

    manifest_rows = read_csv_rows(manifest_path, errors)
    check_rows = read_csv_rows(checks_path, errors)
    subsection_rows = read_csv_rows(subsection_manifest_path, errors)
    expected_manifest_fields = {
        "subsection_id",
        "chapter_title",
        "subsection_title",
        "original_subsection_path",
        "paper_packet_path",
        "work_order_path",
        "rewritten_path",
        "rewrite_status",
        "notes",
    }
    expected_check_fields = {
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
    }
    if manifest_rows and set(manifest_rows[0]) != expected_manifest_fields:
        errors.append("subsection_rewrite_manifest.csv has unexpected columns")
    if check_rows and set(check_rows[0]) != expected_check_fields:
        errors.append("rewrite_instruction_check.csv has unexpected columns")

    subsection_ids = {row.get("subsection_id", "") for row in subsection_rows}
    manifest_ids = {row.get("subsection_id", "") for row in manifest_rows}
    check_ids = {row.get("subsection_id", "") for row in check_rows}
    if manifest_ids != subsection_ids:
        errors.append("subsection_rewrite_manifest.csv subsection coverage does not match subsection_manifest.csv")
    if check_ids != subsection_ids:
        errors.append("rewrite_instruction_check.csv subsection coverage does not match subsection_manifest.csv")

    for row in manifest_rows:
        subsection_id = row.get("subsection_id", "")
        for field in ("original_subsection_path", "paper_packet_path", "work_order_path"):
            path_value = row.get(field, "")
            if not path_value:
                errors.append(f"{field} missing for {subsection_id}")
                continue
            path = run_dir / path_value
            if not path.exists() or path.stat().st_size < 200:
                errors.append(f"{field} missing or too small for {subsection_id}: {path_value}")
        rewritten_path = run_dir / row.get("rewritten_path", "")
        if not rewritten_path.exists():
            errors.append(f"rewritten subsection missing for {subsection_id}: {row.get('rewritten_path', '')}")
            continue
        text = rewritten_path.read_text(encoding="utf-8")
        for marker in (
            f"# Rewritten Subsection: {subsection_id}",
            "## Paper Triage",
            "## Rewritten Text",
            "## Citation Register",
            "## Evidence Use Notes",
            "## Residual Uncertainty",
        ):
            if marker not in text:
                errors.append(f"rewritten subsection {subsection_id} missing marker `{marker}`")

    for row in check_rows:
        subsection_id = row.get("subsection_id", "")
        if row.get("check_status") != "pass":
            errors.append(f"rewrite check for {subsection_id} is not pass: {row.get('check_status')}")
        for field in (
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
        ):
            if row.get(field) != "1":
                errors.append(f"rewrite check for {subsection_id} failed {field}")

    try:
        with sqlite3.connect(sqlite_path) as connection:
            sqlite_task_count = connection.execute("SELECT COUNT(*) FROM subsection_rewrite_tasks").fetchone()[0]
            sqlite_check_count = connection.execute("SELECT COUNT(*) FROM subsection_rewrite_checks").fetchone()[0]
            sqlite_pass_count = connection.execute(
                "SELECT COUNT(*) FROM subsection_rewrite_checks WHERE check_status = 'pass'"
            ).fetchone()[0]
            step = connection.execute(
                """
                SELECT status, validation_status
                FROM workflow_steps
                WHERE step_name = 'subsection_rewrite'
                """
            ).fetchone()
    except sqlite3.Error as exc:
        errors.append(f"could not validate SQLite Stage 8 state: {exc}")
        return

    if sqlite_task_count != len(manifest_rows):
        errors.append(f"SQLite subsection_rewrite_tasks count mismatch: {sqlite_task_count} vs {len(manifest_rows)}")
    if sqlite_check_count != len(check_rows):
        errors.append(f"SQLite subsection_rewrite_checks count mismatch: {sqlite_check_count} vs {len(check_rows)}")
    if sqlite_pass_count != len(check_rows):
        errors.append(f"SQLite subsection_rewrite_checks pass count mismatch: {sqlite_pass_count} vs {len(check_rows)}")
    if step is None:
        errors.append("SQLite workflow_steps missing subsection_rewrite")
    elif step[0] != "complete":
        errors.append(f"invalid SQLite subsection_rewrite status: {step[0]}")


def check_subsection_rewrite_setup(
    run_dir: Path, errors: list[str], allow_later_steps: bool = False
) -> None:
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    manifest_path = run_dir / SUBSECTION_REWRITE_INPUT_DIR / "subsection_rewrite_manifest.csv"
    checks_path = run_dir / SUBSECTION_REWRITE_VERIFY_DIR / "rewrite_instruction_check.csv"
    summary_path = run_dir / SUBSECTION_REWRITE_OUTPUT_DIR / "subsection_rewrite_summary.md"
    stage_readme_path = run_dir / SUBSECTION_REWRITE_DIR / "README.md"
    subsection_manifest_path = run_dir / "artifacts/02_subsection_retrieval/01_scope/subsection_manifest.csv"
    required = [sqlite_path, stage_readme_path, manifest_path, checks_path, summary_path, subsection_manifest_path]
    for path in required:
        if not path.exists():
            errors.append(f"missing Stage 8 setup artifact: {path.relative_to(run_dir).as_posix()}")
            return

    manifest_rows = read_csv_rows(manifest_path, errors)
    check_rows = read_csv_rows(checks_path, errors)
    subsection_rows = read_csv_rows(subsection_manifest_path, errors)
    expected_check_fields = {
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
    }
    if check_rows and set(check_rows[0]) != expected_check_fields:
        errors.append("Stage 8 setup rewrite_instruction_check.csv has unexpected columns")
    subsection_ids = {row.get("subsection_id", "") for row in subsection_rows}
    manifest_ids = {row.get("subsection_id", "") for row in manifest_rows}
    check_ids = {row.get("subsection_id", "") for row in check_rows}
    if manifest_ids != subsection_ids:
        errors.append("Stage 8 setup manifest coverage does not match subsection manifest")
    if check_ids != subsection_ids:
        errors.append("Stage 8 setup check coverage does not match subsection manifest")
    for row in manifest_rows:
        subsection_id = row.get("subsection_id", "")
        if row.get("rewrite_status") != "prepared":
            errors.append(f"Stage 8 setup row {subsection_id} must have rewrite_status=prepared")
        for field in ("original_subsection_path", "paper_packet_path", "work_order_path"):
            path = run_dir / row.get(field, "")
            if not path.exists() or path.stat().st_size < 200:
                errors.append(f"Stage 8 setup {field} missing or too small for {subsection_id}")
                continue
            if field == "work_order_path":
                text = path.read_text(encoding="utf-8")
                for marker in (
                    "## Paper Triage",
                    "## Narrative Full Text Sources",
                    "minimum 250 words",
                    "Allowed `triage_role` values",
                ):
                    if marker not in text:
                        errors.append(f"Stage 8 setup work order {subsection_id} missing marker `{marker}`")
    for row in check_rows:
        subsection_id = row.get("subsection_id", "")
        allowed_check_statuses = {"not_run", "pass"} if allow_later_steps else {"not_run"}
        if row.get("check_status") not in allowed_check_statuses:
            errors.append(f"Stage 8 setup check row {subsection_id} must have check_status=not_run")

    try:
        with sqlite3.connect(sqlite_path) as connection:
            task_count = connection.execute("SELECT COUNT(*) FROM subsection_rewrite_tasks").fetchone()[0]
            check_count = connection.execute("SELECT COUNT(*) FROM subsection_rewrite_checks").fetchone()[0]
            step = connection.execute(
                """
                SELECT status
                FROM workflow_steps
                WHERE step_name = 'subsection_rewrite'
                """
            ).fetchone()
    except sqlite3.Error as exc:
        errors.append(f"could not validate SQLite Stage 8 setup state: {exc}")
        return
    if task_count != len(manifest_rows):
        errors.append(f"SQLite subsection_rewrite_tasks setup count mismatch: {task_count} vs {len(manifest_rows)}")
    if check_count != len(check_rows):
        errors.append(f"SQLite subsection_rewrite_checks setup count mismatch: {check_count} vs {len(check_rows)}")
    allowed_step_statuses = {"prepared", "complete"} if allow_later_steps else {"prepared"}
    if step is None or step[0] not in allowed_step_statuses:
        errors.append("SQLite workflow_steps subsection_rewrite must have status=prepared for setup validation")


def check_terminology_normalization(run_dir: Path, errors: list[str]) -> None:
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    stage_readme_path = run_dir / TERMINOLOGY_DIR / "README.md"
    glossary_path = run_dir / TERMINOLOGY_GLOSSARY_DIR / "terminology_glossary.csv"
    checks_path = run_dir / TERMINOLOGY_VERIFY_DIR / "terminology_normalization_check.csv"
    summary_path = run_dir / TERMINOLOGY_OUTPUT_DIR / "terminology_normalization_summary.md"
    rewritten_dir = run_dir / SUBSECTION_REWRITE_REWRITTEN_DIR
    normalized_dir = run_dir / TERMINOLOGY_NORMALIZED_DIR
    required = [sqlite_path, stage_readme_path, glossary_path, checks_path, summary_path]
    for path in required:
        if not path.exists():
            errors.append(f"missing Stage 9 artifact: {path.relative_to(run_dir).as_posix()}")
            return
    glossary_rows = read_csv_rows(glossary_path, errors)
    check_rows = read_csv_rows(checks_path, errors)
    expected_glossary_fields = {
        "entity_id",
        "preferred_name",
        "entity_type",
        "aliases",
        "first_mention_rule",
        "normalization_status",
        "notes",
    }
    expected_check_fields = {
        "subsection_id",
        "normalized_path",
        "check_status",
        "has_text",
        "applies_known_aliases",
        "preserves_citation_ids",
        "notes",
    }
    if glossary_rows and set(glossary_rows[0]) != expected_glossary_fields:
        errors.append("terminology_glossary.csv has unexpected columns")
    if check_rows and set(check_rows[0]) != expected_check_fields:
        errors.append("terminology_normalization_check.csv has unexpected columns")
    if not glossary_rows:
        errors.append("terminology_glossary.csv has no active rows; provide alias overrides or rerun setup intentionally")
    rewritten_ids = {path.stem for path in rewritten_dir.glob("SUB*.md")}
    normalized_ids = {path.stem for path in normalized_dir.glob("SUB*.md")}
    check_ids = {row.get("subsection_id", "") for row in check_rows}
    if not rewritten_ids:
        errors.append("Stage 9 cannot find rewritten Stage 8 subsections")
    if normalized_ids != rewritten_ids:
        errors.append("normalized subsection coverage does not match Stage 8 rewritten subsection coverage")
    if check_ids != rewritten_ids:
        errors.append("terminology check coverage does not match Stage 8 rewritten subsection coverage")
    for row in check_rows:
        subsection_id = row.get("subsection_id", "")
        if row.get("check_status") != "pass":
            errors.append(f"terminology normalization check for {subsection_id} is not pass: {row.get('check_status')}")
        for field in ("has_text", "applies_known_aliases", "preserves_citation_ids"):
            if row.get(field) != "1":
                errors.append(f"terminology normalization check for {subsection_id} failed {field}")
        path_value = row.get("normalized_path", "")
        if path_value:
            path = run_dir / path_value
            if not path.exists() or path.stat().st_size < 500:
                errors.append(f"normalized subsection missing or too small for {subsection_id}: {path_value}")
    try:
        with sqlite3.connect(sqlite_path) as connection:
            entity_count = connection.execute("SELECT COUNT(*) FROM terminology_entities").fetchone()[0]
            check_count = connection.execute("SELECT COUNT(*) FROM terminology_normalization_checks").fetchone()[0]
            pass_count = connection.execute(
                "SELECT COUNT(*) FROM terminology_normalization_checks WHERE check_status = 'pass'"
            ).fetchone()[0]
            step = connection.execute(
                """
                SELECT status, validation_status
                FROM workflow_steps
                WHERE step_name = 'terminology_normalization'
                """
            ).fetchone()
    except sqlite3.Error as exc:
        errors.append(f"could not validate SQLite Stage 9 state: {exc}")
        return
    if entity_count != len(glossary_rows):
        errors.append(f"SQLite terminology_entities count mismatch: {entity_count} vs {len(glossary_rows)}")
    if check_count != len(check_rows):
        errors.append(f"SQLite terminology_normalization_checks count mismatch: {check_count} vs {len(check_rows)}")
    if pass_count != len(check_rows):
        errors.append(f"SQLite terminology pass count mismatch: {pass_count} vs {len(check_rows)}")
    if step is None:
        errors.append("SQLite workflow_steps missing terminology_normalization")
    elif step[0] != "complete":
        errors.append(f"invalid SQLite terminology_normalization status: {step[0]}")


def check_review_assembly(run_dir: Path, errors: list[str]) -> None:
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    stage_readme_path = run_dir / REVIEW_ASSEMBLY_DIR / "README.md"
    manifest_path = run_dir / REVIEW_ASSEMBLY_INPUT_DIR / "review_assembly_manifest.csv"
    checks_path = run_dir / REVIEW_ASSEMBLY_VERIFY_DIR / "review_assembly_check.csv"
    summary_path = run_dir / REVIEW_ASSEMBLY_OUTPUT_DIR / "review_assembly_summary.md"
    assembled_path = run_dir / "drafts/assembled_review.md"
    normalized_dir = run_dir / TERMINOLOGY_NORMALIZED_DIR
    required = [sqlite_path, stage_readme_path, manifest_path, checks_path, summary_path, assembled_path]
    for path in required:
        if not path.exists():
            errors.append(f"missing Stage 10 artifact: {path.relative_to(run_dir).as_posix()}")
            return
    manifest_rows = read_csv_rows(manifest_path, errors)
    check_rows = read_csv_rows(checks_path, errors)
    expected_manifest_fields = {
        "subsection_id",
        "chapter_title",
        "subsection_title",
        "normalized_path",
        "assembled_section_path",
        "citation_count",
        "assembly_status",
        "notes",
    }
    expected_check_fields = {
        "check_name",
        "check_status",
        "observed_value",
        "notes",
    }
    if manifest_rows and set(manifest_rows[0]) != expected_manifest_fields:
        errors.append("review_assembly_manifest.csv has unexpected columns")
    if check_rows and set(check_rows[0]) != expected_check_fields:
        errors.append("review_assembly_check.csv has unexpected columns")
    normalized_ids = {path.stem for path in normalized_dir.glob("SUB*.md")}
    manifest_ids = {row.get("subsection_id", "") for row in manifest_rows}
    if manifest_ids != normalized_ids:
        errors.append("review assembly manifest coverage does not match normalized subsection coverage")
    assembled_text = assembled_path.read_text(encoding="utf-8")
    markers = re.findall(r"source_subsection_id: (SUB\d{3})", assembled_text)
    if len(markers) != len(normalized_ids) or set(markers) != normalized_ids:
        errors.append("assembled_review.md subsection markers do not match normalized subsection coverage")
    if assembled_text.count("#### Citation Register") != len(normalized_ids):
        errors.append("assembled_review.md does not preserve one citation register per subsection")
    if assembled_text.count("#### Residual Uncertainty") != len(normalized_ids):
        errors.append("assembled_review.md does not preserve one residual uncertainty section per subsection")
    if re.search(r"new_untraced_citation", assembled_text, flags=re.IGNORECASE):
        errors.append("assembled_review.md contains new_untraced_citation marker")
    source_citation_ids = set()
    for path in normalized_dir.glob("SUB*.md"):
        source_citation_ids.update(re.findall(r"\bSUB\d{3}-C\d{3}\b", path.read_text(encoding="utf-8")))
    assembled_citation_ids = set(re.findall(r"\bSUB\d{3}-C\d{3}\b", assembled_text))
    if source_citation_ids != assembled_citation_ids:
        errors.append(
            "assembled_review.md citation ID set does not match normalized subsection citation ID set "
            f"({len(assembled_citation_ids)} vs {len(source_citation_ids)})"
        )
    for row in manifest_rows:
        subsection_id = row.get("subsection_id", "")
        if row.get("assembly_status") != "assembled":
            errors.append(f"review assembly row {subsection_id} must have assembly_status=assembled")
        path_value = row.get("assembled_section_path", "")
        if path_value:
            section_path = run_dir / path_value
            if not section_path.exists() or section_path.stat().st_size < 500:
                errors.append(f"assembled section missing or too small for {subsection_id}: {path_value}")
    for row in check_rows:
        if row.get("check_status") != "pass":
            errors.append(f"review assembly check {row.get('check_name', '')} is not pass")
    check_names = {row.get("check_name", "") for row in check_rows}
    if "citation_ids_preserved" not in check_names:
        errors.append("review assembly checks missing citation_ids_preserved")
    try:
        with sqlite3.connect(sqlite_path) as connection:
            section_count = connection.execute("SELECT COUNT(*) FROM review_assembly_sections").fetchone()[0]
            check_count = connection.execute("SELECT COUNT(*) FROM review_assembly_checks").fetchone()[0]
            pass_count = connection.execute(
                "SELECT COUNT(*) FROM review_assembly_checks WHERE check_status = 'pass'"
            ).fetchone()[0]
            step = connection.execute(
                """
                SELECT status, validation_status
                FROM workflow_steps
                WHERE step_name = 'review_assembly'
                """
            ).fetchone()
    except sqlite3.Error as exc:
        errors.append(f"could not validate SQLite Stage 10 state: {exc}")
        return
    if section_count != len(manifest_rows):
        errors.append(f"SQLite review_assembly_sections count mismatch: {section_count} vs {len(manifest_rows)}")
    if check_count != len(check_rows):
        errors.append(f"SQLite review_assembly_checks count mismatch: {check_count} vs {len(check_rows)}")
    if pass_count != len(check_rows):
        errors.append(f"SQLite review assembly pass count mismatch: {pass_count} vs {len(check_rows)}")
    if step is None:
        errors.append("SQLite workflow_steps missing review_assembly")
    elif step[0] != "complete":
        errors.append(f"invalid SQLite review_assembly status: {step[0]}")


def check_claim_verification_setup(
    run_dir: Path, errors: list[str], allow_later_steps: bool = False
) -> None:
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    stage_readme_path = run_dir / CLAIM_VERIFICATION_DIR / "README.md"
    manifest_path = run_dir / CLAIM_VERIFICATION_INPUT_DIR / "claim_manifest.csv"
    checks_path = run_dir / CLAIM_VERIFICATION_VERIFY_DIR / "claim_verification_setup_check.csv"
    summary_path = run_dir / CLAIM_VERIFICATION_OUTPUT_DIR / "claim_verification_summary.md"
    required = [sqlite_path, stage_readme_path, manifest_path, checks_path, summary_path]
    for path in required:
        if not path.exists():
            errors.append(f"missing Stage 11 setup artifact: {path.relative_to(run_dir).as_posix()}")
            return
    manifest_rows = read_csv_rows(manifest_path, errors)
    check_rows = read_csv_rows(checks_path, errors)
    expected_manifest_fields = {
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
    }
    expected_check_fields = {"check_name", "check_status", "observed_value", "notes"}
    if manifest_rows and set(manifest_rows[0]) != expected_manifest_fields:
        errors.append("claim_manifest.csv has unexpected columns")
    if check_rows and set(check_rows[0]) != expected_check_fields:
        errors.append("claim_verification_setup_check.csv has unexpected columns")
    if not manifest_rows:
        errors.append("claim_manifest.csv has no extracted claims")
    claim_ids = [row.get("claim_id", "") for row in manifest_rows]
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("claim_manifest.csv contains duplicate claim IDs")
    for row in manifest_rows:
        claim_id = row.get("claim_id", "")
        if row.get("verification_status") != "not_reviewed":
            errors.append(f"claim {claim_id} must have verification_status=not_reviewed during setup")
        for field in ("claim_text", "cited_paper_ids", "work_order_path", "review_path"):
            if not row.get(field, ""):
                errors.append(f"claim {claim_id} missing {field}")
        work_order_path = run_dir / row.get("work_order_path", "")
        if not work_order_path.exists() or work_order_path.stat().st_size < 500:
            errors.append(f"claim work order missing or too small for {claim_id}: {row.get('work_order_path', '')}")
    for row in check_rows:
        if row.get("check_status") != "pass":
            errors.append(f"claim verification setup check {row.get('check_name', '')} is not pass")
    try:
        with sqlite3.connect(sqlite_path) as connection:
            claim_count = connection.execute("SELECT COUNT(*) FROM claim_verification_claims").fetchone()[0]
            check_count = connection.execute("SELECT COUNT(*) FROM claim_verification_checks").fetchone()[0]
            step = connection.execute(
                """
                SELECT status, validation_status
                FROM workflow_steps
                WHERE step_name = 'claim_verification'
                """
            ).fetchone()
    except sqlite3.Error as exc:
        errors.append(f"could not validate SQLite Stage 11 setup state: {exc}")
        return
    if claim_count != len(manifest_rows):
        errors.append(f"SQLite claim_verification_claims count mismatch: {claim_count} vs {len(manifest_rows)}")
    if not allow_later_steps and check_count != len(check_rows):
        errors.append(f"SQLite claim_verification_checks setup count mismatch: {check_count} vs {len(check_rows)}")
    if step is None:
        errors.append("SQLite workflow_steps missing claim_verification")
    elif step[0] not in ({"prepared", "complete"} if allow_later_steps else {"prepared"}):
        errors.append(f"SQLite workflow_steps claim_verification must be prepared during setup, found {step[0]}")


def check_claim_verification(run_dir: Path, errors: list[str]) -> None:
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    manifest_path = run_dir / CLAIM_VERIFICATION_INPUT_DIR / "claim_manifest.csv"
    checks_path = run_dir / CLAIM_VERIFICATION_VERIFY_DIR / "claim_verification_check.csv"
    summary_path = run_dir / CLAIM_VERIFICATION_OUTPUT_DIR / "claim_verification_summary.md"
    review_dir = run_dir / CLAIM_VERIFICATION_REVIEW_DIR
    required = [sqlite_path, manifest_path, checks_path, summary_path]
    for path in required:
        if not path.exists():
            errors.append(f"missing Stage 11 artifact: {path.relative_to(run_dir).as_posix()}")
            return
    manifest_rows = read_csv_rows(manifest_path, errors)
    check_rows = read_csv_rows(checks_path, errors)
    review_files = sorted(review_dir.glob("SUB*.csv"))
    if not review_files:
        errors.append("claim verification has no reviewed subsection CSV files")
    expected_check_fields = {"check_name", "check_status", "observed_value", "notes"}
    if check_rows and set(check_rows[0]) != expected_check_fields:
        errors.append("claim_verification_check.csv has unexpected columns")
    for row in check_rows:
        if row.get("check_status") != "pass":
            errors.append(f"claim verification check {row.get('check_name', '')} is not pass")
    try:
        with sqlite3.connect(sqlite_path) as connection:
            claim_count = connection.execute("SELECT COUNT(*) FROM claim_verification_claims").fetchone()[0]
            reviewed_count = connection.execute(
                "SELECT COUNT(*) FROM claim_verification_claims WHERE verification_status != 'not_reviewed'"
            ).fetchone()[0]
            check_count = connection.execute("SELECT COUNT(*) FROM claim_verification_checks").fetchone()[0]
            pass_count = connection.execute(
                "SELECT COUNT(*) FROM claim_verification_checks WHERE check_status = 'pass'"
            ).fetchone()[0]
            step = connection.execute(
                """
                SELECT status, validation_status
                FROM workflow_steps
                WHERE step_name = 'claim_verification'
                """
            ).fetchone()
    except sqlite3.Error as exc:
        errors.append(f"could not validate SQLite Stage 11 state: {exc}")
        return
    if claim_count != len(manifest_rows):
        errors.append(f"SQLite claim_verification_claims count mismatch: {claim_count} vs {len(manifest_rows)}")
    if reviewed_count != len(manifest_rows):
        errors.append(f"SQLite reviewed claim count mismatch: {reviewed_count} vs {len(manifest_rows)}")
    if check_count != len(check_rows):
        errors.append(f"SQLite claim_verification_checks count mismatch: {check_count} vs {len(check_rows)}")
    if pass_count != len(check_rows):
        errors.append(f"SQLite claim verification pass count mismatch: {pass_count} vs {len(check_rows)}")
    if step is None:
        errors.append("SQLite workflow_steps missing claim_verification")
    elif step[0] != "complete":
        errors.append(f"invalid SQLite claim_verification status: {step[0]}")


def check_corrective_rewrite(run_dir: Path, errors: list[str]) -> None:
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    claim_manifest_path = run_dir / CLAIM_VERIFICATION_INPUT_DIR / "claim_manifest.csv"
    claim_review_dir = run_dir / CLAIM_VERIFICATION_REVIEW_DIR
    correction_manifest_path = run_dir / CORRECTIVE_REWRITE_INPUT_DIR / "correction_manifest.csv"
    checks_path = run_dir / CORRECTIVE_REWRITE_VERIFY_DIR / "corrective_rewrite_check.csv"
    summary_path = run_dir / CORRECTIVE_REWRITE_SUMMARY_DIR / "corrective_rewrite_summary.md"
    corrected_path = run_dir / "drafts/corrected_review.md"
    artifact_copy_path = run_dir / CORRECTIVE_REWRITE_OUTPUT_DIR / "corrected_review.md"
    required = [
        sqlite_path,
        claim_manifest_path,
        correction_manifest_path,
        checks_path,
        summary_path,
        corrected_path,
        artifact_copy_path,
    ]
    for path in required:
        if not path.exists():
            errors.append(f"missing Stage 12 artifact: {path.relative_to(run_dir).as_posix()}")
            return

    correction_rows = read_csv_rows(correction_manifest_path, errors)
    check_rows = read_csv_rows(checks_path, errors)
    claim_review_rows = []
    for review_path in sorted(claim_review_dir.glob("SUB*.csv")):
        claim_review_rows.extend(read_csv_rows(review_path, errors))

    expected_manifest_fields = {
        "claim_id",
        "subsection_id",
        "verification_status",
        "mismatch_type",
        "original_claim",
        "corrected_claim",
        "final_replacement",
        "cited_paper_ids",
        "citation_ids",
        "action",
        "replacement_status",
        "notes",
    }
    expected_check_fields = {"check_name", "check_status", "observed_value", "notes"}
    if correction_rows and set(correction_rows[0]) != expected_manifest_fields:
        errors.append("correction_manifest.csv has unexpected columns")
    if check_rows and set(check_rows[0]) != expected_check_fields:
        errors.append("corrective_rewrite_check.csv has unexpected columns")

    problem_claim_ids = {
        row.get("claim_id", "")
        for row in claim_review_rows
        if row.get("verification_status", "") != "supported"
    }
    correction_claim_ids = {row.get("claim_id", "") for row in correction_rows}
    if correction_claim_ids != problem_claim_ids:
        errors.append(
            "correction_manifest.csv claim coverage does not match non-supported Stage 11 claims "
            f"({len(correction_claim_ids)} vs {len(problem_claim_ids)})"
        )
    if len(correction_claim_ids) != len(correction_rows):
        errors.append("correction_manifest.csv contains duplicate claim IDs")
    for row in correction_rows:
        claim_id = row.get("claim_id", "")
        if row.get("replacement_status") != "applied":
            errors.append(f"corrective rewrite row {claim_id} was not applied")
        if row.get("verification_status") == "supported":
            errors.append(f"corrective rewrite row {claim_id} should not target a supported claim")
        if row.get("action") == "replace_claim" and not row.get("final_replacement", ""):
            errors.append(f"corrective rewrite row {claim_id} has empty final_replacement")

    for row in check_rows:
        if row.get("check_status") != "pass":
            errors.append(f"corrective rewrite check {row.get('check_name', '')} is not pass")
    check_names = {row.get("check_name", "") for row in check_rows}
    required_checks = {
        "all_non_supported_claims_have_actions",
        "all_replacements_applied_once",
        "no_problem_claim_text_remaining",
        "corrected_review_populated",
        "no_new_untraced_citations",
        "no_new_untraced_paper_ids",
        "problem_status_counts_recorded",
    }
    missing_checks = required_checks - check_names
    if missing_checks:
        errors.append(f"corrective rewrite checks missing: {', '.join(sorted(missing_checks))}")

    corrected_text = corrected_path.read_text(encoding="utf-8")
    artifact_text = artifact_copy_path.read_text(encoding="utf-8")
    if corrected_text != artifact_text:
        errors.append("drafts/corrected_review.md and artifact copy differ")
    for row in correction_rows:
        original = row.get("original_claim", "")
        if original and original in corrected_text:
            errors.append(f"corrected_review.md still contains original problem claim {row.get('claim_id', '')}")
    if "# Assembled Review Draft" not in corrected_text:
        errors.append("corrected_review.md does not preserve assembled review header")
    if "#### Citation Register" not in corrected_text:
        errors.append("corrected_review.md does not preserve citation registers")

    try:
        with sqlite3.connect(sqlite_path) as connection:
            correction_count = connection.execute("SELECT COUNT(*) FROM corrective_rewrite_claims").fetchone()[0]
            check_count = connection.execute("SELECT COUNT(*) FROM corrective_rewrite_checks").fetchone()[0]
            pass_count = connection.execute(
                "SELECT COUNT(*) FROM corrective_rewrite_checks WHERE check_status = 'pass'"
            ).fetchone()[0]
            step = connection.execute(
                """
                SELECT status, validation_status
                FROM workflow_steps
                WHERE step_name = 'corrective_rewrite'
                """
            ).fetchone()
    except sqlite3.Error as exc:
        errors.append(f"could not validate SQLite Stage 12 state: {exc}")
        return
    if correction_count != len(correction_rows):
        errors.append(f"SQLite corrective_rewrite_claims count mismatch: {correction_count} vs {len(correction_rows)}")
    if check_count != len(check_rows):
        errors.append(f"SQLite corrective_rewrite_checks count mismatch: {check_count} vs {len(check_rows)}")
    if pass_count != len(check_rows):
        errors.append(f"SQLite corrective rewrite pass count mismatch: {pass_count} vs {len(check_rows)}")
    if step is None:
        errors.append("SQLite workflow_steps missing corrective_rewrite")
    elif step[0] != "complete":
        errors.append(f"invalid SQLite corrective_rewrite status: {step[0]}")


def check_final_review(run_dir: Path, errors: list[str]) -> None:
    sqlite_path = run_dir / "artifacts/00_workflow_control/01_state/workflow_state.sqlite"
    corrected_path = run_dir / "drafts/corrected_review.md"
    final_path = run_dir / "drafts/final_review.md"
    artifact_copy_path = run_dir / FINAL_REVIEW_OUTPUT_DIR / "final_review.md"
    references_path = run_dir / FINAL_REVIEW_OUTPUT_DIR / "references.csv"
    manifest_path = run_dir / FINAL_REVIEW_INPUT_DIR / "final_review_manifest.csv"
    checks_path = run_dir / FINAL_REVIEW_VERIFY_DIR / "final_review_check.csv"
    summary_path = run_dir / FINAL_REVIEW_SUMMARY_DIR / "final_review_summary.md"
    stage_readme_path = run_dir / FINAL_REVIEW_DIR / "README.md"
    required = [
        sqlite_path,
        corrected_path,
        final_path,
        artifact_copy_path,
        references_path,
        manifest_path,
        checks_path,
        summary_path,
        stage_readme_path,
    ]
    for path in required:
        if not path.exists():
            errors.append(f"missing final-review artifact: {path.relative_to(run_dir).as_posix()}")
            return

    manifest_rows = read_csv_rows(manifest_path, errors)
    check_rows = read_csv_rows(checks_path, errors)
    expected_manifest_fields = {
        "section_id",
        "section_type",
        "title",
        "source_subsection_id",
        "citation_count",
        "uncertainty_note_count",
        "section_status",
        "notes",
    }
    expected_check_fields = {"check_name", "check_status", "observed_value", "notes"}
    if manifest_rows and set(manifest_rows[0]) != expected_manifest_fields:
        errors.append("final_review_manifest.csv has unexpected columns")
    if check_rows and set(check_rows[0]) != expected_check_fields:
        errors.append("final_review_check.csv has unexpected columns")
    if not manifest_rows:
        errors.append("final_review_manifest.csv has no rows")
    for row in manifest_rows:
        if row.get("section_status") != "assembled":
            errors.append(f"final review section {row.get('section_id', '')} is not assembled")
    for row in check_rows:
        if row.get("check_status") != "pass":
            errors.append(f"final review check {row.get('check_name', '')} is not pass")
    required_checks = {
        "final_review_populated",
        "has_required_reader_sections",
        "no_orientation_section",
        "has_references",
        "no_evidence_appendix_in_final",
        "no_stale_claim_verification_warning",
        "no_source_html_comments",
        "no_new_untraced_citations",
        "no_workflow_citation_ids_in_main_text",
        "no_raw_paper_ids_in_main_text",
        "reference_ids_match_main_text_sources",
        "references_deduplicated",
        "references_have_pmids_or_titles",
        "subsection_manifest_populated",
        "section_status_counts_recorded",
    }
    check_names = {row.get("check_name", "") for row in check_rows}
    missing_checks = required_checks - check_names
    if missing_checks:
        errors.append(f"final review checks missing: {', '.join(sorted(missing_checks))}")

    final_text = final_path.read_text(encoding="utf-8")
    artifact_text = artifact_copy_path.read_text(encoding="utf-8")
    corrected_text = corrected_path.read_text(encoding="utf-8")
    if final_text != artifact_text:
        errors.append("drafts/final_review.md and artifact copy differ")
    for marker in ("## Abstract", "## Main Review", "## References"):
        if marker not in final_text:
            errors.append(f"final_review.md missing marker: {marker}")
    if "## Orientation" in final_text:
        errors.append("final_review.md should not include an Orientation section")
    if "## Evidence Appendix" in final_text:
        errors.append("final_review.md should not include oversized Evidence Appendix")
    if "##### Citation Register" in final_text:
        errors.append("final_review.md should not include full citation-register tables")
    if "Claim-level verification has not yet been performed" in final_text:
        errors.append("final_review.md contains stale claim-verification warning")
    if "<!-- source_subsection_id:" in final_text:
        errors.append("final_review.md contains source subsection HTML comments")

    reference_rows = read_csv_rows(references_path, errors)
    source_citations = set(re.findall(r"\b(?:SUB|S)\d{2,3}-[CR]\d{3}\b", corrected_text))
    final_citations = set(re.findall(r"\b(?:SUB|S)\d{2,3}-[CR]\d{3}\b", final_text))
    if final_citations - source_citations:
        errors.append("final_review.md introduced new citation-like IDs")
    main_text = final_text.split("\n## References\n", 1)[0]
    raw_paper_ids = set(re.findall(r"\bpmid-\d+\b|\bPAPER-\d+\b", main_text))
    if raw_paper_ids:
        errors.append("final_review.md main text still contains workflow paper IDs")
    workflow_citation_ids = set(re.findall(r"\b(?:SUB|S)\d{2,3}-[CR]\d{3}\b", main_text))
    if workflow_citation_ids:
        errors.append("final_review.md main text still contains workflow citation IDs")
    reference_ids = [row.get("paper_id", "") for row in reference_rows]
    if len(reference_ids) != len(set(reference_ids)):
        errors.append("references.csv contains duplicate paper IDs")
    if not reference_rows:
        errors.append("references.csv has no references")
    for row in reference_rows:
        if not row.get("PMID", "") and not row.get("title", ""):
            errors.append(f"reference row missing PMID and title: {row.get('paper_id', '')}")
    subsection_rows = [row for row in manifest_rows if row.get("section_type") == "subsection"]
    corrected_subsection_ids = set(re.findall(r"source_subsection_id:\s*(SUB\d{3})", corrected_text))
    manifest_subsection_ids = {row.get("source_subsection_id", "") for row in subsection_rows}
    if corrected_subsection_ids != manifest_subsection_ids:
        errors.append("final review manifest subsection coverage does not match corrected review")

    try:
        with sqlite3.connect(sqlite_path) as connection:
            section_count = connection.execute("SELECT COUNT(*) FROM final_review_sections").fetchone()[0]
            check_count = connection.execute("SELECT COUNT(*) FROM final_review_checks").fetchone()[0]
            pass_count = connection.execute(
                "SELECT COUNT(*) FROM final_review_checks WHERE check_status = 'pass'"
            ).fetchone()[0]
            step = connection.execute(
                """
                SELECT status, validation_status
                FROM workflow_steps
                WHERE step_name = 'final_review'
                """
            ).fetchone()
    except sqlite3.Error as exc:
        errors.append(f"could not validate SQLite final-review state: {exc}")
        return
    if section_count != len(manifest_rows):
        errors.append(f"SQLite final_review_sections count mismatch: {section_count} vs {len(manifest_rows)}")
    if check_count != len(check_rows):
        errors.append(f"SQLite final_review_checks count mismatch: {check_count} vs {len(check_rows)}")
    if pass_count != len(check_rows):
        errors.append(f"SQLite final review pass count mismatch: {pass_count} vs {len(check_rows)}")
    if step is None:
        errors.append("SQLite workflow_steps missing final_review")
    elif step[0] != "complete":
        errors.append(f"invalid SQLite final_review status: {step[0]}")


def check_workflow_state_snapshot(path: Path, errors: list[str]) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"could not parse workflow_state_snapshot.json: {exc}")
        return
    if payload.get("current_step") != "subsection_retrieval":
        errors.append(
            "workflow_state_snapshot.json current_step is not subsection_retrieval"
        )
    subsection_count = payload.get("subsection_count")
    if not isinstance(subsection_count, int) or subsection_count <= 0:
        errors.append("workflow_state_snapshot.json subsection_count must be positive")


if __name__ == "__main__":
    raise SystemExit(main())

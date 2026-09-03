#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
import time
from pathlib import Path


SCHEMA_VERSION = 14


def timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def db_path(run_dir: Path) -> Path:
    return run_dir / "artifacts" / "00_workflow_control" / "01_state" / "workflow_state.sqlite"


def connect(run_dir: Path) -> sqlite3.Connection:
    path = db_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    initialize(connection)
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS workflow_steps (
            step_name TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            validation_status TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS subsections (
            subsection_id TEXT PRIMARY KEY,
            chapter_index INTEGER NOT NULL,
            chapter_title TEXT NOT NULL,
            subsection_index TEXT NOT NULL,
            subsection_title TEXT NOT NULL,
            subsection_scope_note TEXT,
            retrieval_status TEXT NOT NULL DEFAULT 'not_started',
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS draft_citations (
            citation_id TEXT PRIMARY KEY,
            subsection_id TEXT NOT NULL,
            citation TEXT NOT NULL,
            pmid TEXT,
            doi TEXT,
            evidence_role TEXT,
            draft_access_status TEXT,
            venue_trust_label TEXT,
            discovery_provenance TEXT,
            notes TEXT,
            recall_status TEXT NOT NULL DEFAULT 'not_checked',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS pubmed_queries (
            query_id TEXT PRIMARY KEY,
            subsection_id TEXT NOT NULL,
            query_type TEXT NOT NULL,
            pubmed_query TEXT NOT NULL,
            required_terms TEXT,
            optional_terms TEXT,
            excluded_terms TEXT,
            expected_result_band TEXT,
            recall_targets TEXT,
            query_rationale TEXT,
            latest_count_status TEXT DEFAULT 'not_run',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS query_iterations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subsection_id TEXT NOT NULL,
            query_id TEXT NOT NULL,
            iteration INTEGER NOT NULL,
            run_status TEXT NOT NULL,
            result_count TEXT,
            count_status TEXT NOT NULL,
            controller_action TEXT NOT NULL,
            next_query_id TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(query_id, iteration),
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE,
            FOREIGN KEY(query_id) REFERENCES pubmed_queries(query_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS papers (
            paper_id TEXT PRIMARY KEY,
            pmid TEXT,
            pmcid TEXT,
            doi TEXT,
            title TEXT,
            journal TEXT,
            publication_year TEXT,
            article_type TEXT,
            venue_trust_label TEXT,
            first_seen_subsection_id TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_papers_pmid ON papers(pmid);
        CREATE INDEX IF NOT EXISTS idx_papers_pmcid ON papers(pmcid);

        CREATE TABLE IF NOT EXISTS pubmed_records (
            paper_id TEXT PRIMARY KEY,
            pmid TEXT UNIQUE,
            pmcid TEXT,
            doi TEXT,
            title TEXT,
            journal TEXT,
            publication_year TEXT,
            authors_json TEXT NOT NULL,
            publication_types_json TEXT NOT NULL,
            abstract TEXT,
            source_query_ids_json TEXT NOT NULL,
            subsection_ids_json TEXT NOT NULL,
            retrieval_batch TEXT,
            raw_json TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(paper_id) REFERENCES papers(paper_id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_pubmed_records_pmid
            ON pubmed_records(pmid);
        CREATE INDEX IF NOT EXISTS idx_pubmed_records_pmcid
            ON pubmed_records(pmcid);

        CREATE TABLE IF NOT EXISTS subsection_papers (
            subsection_id TEXT NOT NULL,
            paper_id TEXT NOT NULL,
            abstract_review_decision TEXT NOT NULL,
            evidence_role TEXT,
            draft_access_status TEXT,
            verified_access_status TEXT,
            source_query_ids TEXT,
            reason TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(subsection_id, paper_id),
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE,
            FOREIGN KEY(paper_id) REFERENCES papers(paper_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS abstract_review_batches (
            batch_id TEXT PRIMARY KEY,
            subsection_id TEXT NOT NULL,
            batch_index INTEGER NOT NULL,
            candidate_count INTEGER NOT NULL,
            context_path TEXT NOT NULL,
            batch_path TEXT NOT NULL,
            review_status TEXT NOT NULL,
            assigned_worker TEXT,
            output_path TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS abstract_review_decisions (
            batch_id TEXT NOT NULL,
            subsection_id TEXT NOT NULL,
            paper_id TEXT NOT NULL,
            pmid TEXT,
            pmcid TEXT,
            doi TEXT,
            abstract_review_decision TEXT NOT NULL,
            first_pass_rationale TEXT NOT NULL,
            first_pass_confidence TEXT NOT NULL,
            topic_match_type TEXT NOT NULL,
            semantic_fit_score INTEGER NOT NULL,
            mechanism_match TEXT NOT NULL,
            entity_context_match TEXT NOT NULL,
            evidence_directness TEXT NOT NULL,
            key_relevant_abstract_text TEXT NOT NULL,
            missing_full_text_reason TEXT NOT NULL,
            synthesis_role TEXT NOT NULL,
            venue_trust_label TEXT,
            verified_access_status TEXT,
            reviewer_id TEXT,
            source_csv_path TEXT NOT NULL,
            decision_version INTEGER NOT NULL DEFAULT 1,
            reviewed_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(batch_id, subsection_id, paper_id),
            FOREIGN KEY(subsection_id, paper_id)
                REFERENCES subsection_papers(subsection_id, paper_id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_abstract_review_decisions_subsection
            ON abstract_review_decisions(subsection_id);
        CREATE INDEX IF NOT EXISTS idx_abstract_review_decisions_decision
            ON abstract_review_decisions(abstract_review_decision);

        CREATE TABLE IF NOT EXISTS subsection_metrics (
            subsection_id TEXT PRIMARY KEY,
            queries_planned INTEGER NOT NULL DEFAULT 0,
            queries_run INTEGER NOT NULL DEFAULT 0,
            total_pubmed_returned TEXT,
            total_collected_for_review TEXT,
            draft_known_citation_count INTEGER NOT NULL DEFAULT 0,
            draft_citations_recovered TEXT,
            draft_citation_recall_rate TEXT,
            abstracts_reviewed INTEGER NOT NULL DEFAULT 0,
            abstract_include_primary_count INTEGER NOT NULL DEFAULT 0,
            abstract_include_context_count INTEGER NOT NULL DEFAULT 0,
            abstract_uncertain_full_text_needed_count INTEGER NOT NULL DEFAULT 0,
            abstract_rejected_count INTEGER NOT NULL DEFAULT 0,
            abstract_rejection_rate TEXT,
            rescue_reviewed INTEGER NOT NULL DEFAULT 0,
            rescue_promoted_count INTEGER NOT NULL DEFAULT 0,
            final_literature_set_count INTEGER NOT NULL DEFAULT 0,
            full_text_download_queue_count INTEGER NOT NULL DEFAULT 0,
            controller_status TEXT NOT NULL DEFAULT 'not_run',
            notes TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS full_text_queue (
            subsection_id TEXT NOT NULL,
            paper_id TEXT NOT NULL,
            pmid TEXT,
            pmcid TEXT,
            doi TEXT,
            title TEXT,
            why_full_text_needed TEXT,
            download_priority TEXT,
            user_action TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(subsection_id, paper_id),
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS paper_review_rollup (
            paper_id TEXT PRIMARY KEY,
            pmid TEXT,
            pmcid TEXT,
            doi TEXT,
            title TEXT,
            global_review_status TEXT NOT NULL,
            included_subsection_count INTEGER NOT NULL DEFAULT 0,
            primary_subsection_count INTEGER NOT NULL DEFAULT 0,
            context_subsection_count INTEGER NOT NULL DEFAULT 0,
            uncertain_subsection_count INTEGER NOT NULL DEFAULT 0,
            excluded_subsection_count INTEGER NOT NULL DEFAULT 0,
            best_evidence_role TEXT,
            full_text_ingestion_route TEXT NOT NULL,
            needs_user_pdf INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(paper_id) REFERENCES papers(paper_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS full_text_ingestion (
            paper_id TEXT PRIMARY KEY,
            pmid TEXT,
            pmcid TEXT,
            doi TEXT,
            title TEXT,
            ingestion_status TEXT NOT NULL,
            source_format TEXT NOT NULL,
            access_source TEXT,
            source_url TEXT,
            source_path TEXT,
            normalized_path TEXT,
            text_char_count INTEGER NOT NULL DEFAULT 0,
            section_count INTEGER NOT NULL DEFAULT 0,
            pmc_xml_status TEXT NOT NULL DEFAULT 'not_attempted',
            pdf_status TEXT NOT NULL DEFAULT 'not_attempted',
            parser_status TEXT NOT NULL DEFAULT 'not_attempted',
            user_pdf_required INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(paper_id) REFERENCES papers(paper_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS full_text_source_candidates (
            paper_id TEXT NOT NULL,
            pmid TEXT,
            pmcid TEXT,
            doi TEXT,
            source_name TEXT NOT NULL,
            source_format TEXT NOT NULL,
            source_url TEXT NOT NULL,
            discovery_status TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(paper_id, source_name, source_format, source_url),
            FOREIGN KEY(paper_id) REFERENCES papers(paper_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS full_text_chunks (
            chunk_uid TEXT PRIMARY KEY,
            paper_id TEXT NOT NULL,
            chunk_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            pmid TEXT,
            pmcid TEXT,
            doi TEXT,
            title TEXT,
            source_format TEXT NOT NULL,
            source_path TEXT,
            normalized_path TEXT NOT NULL,
            section_index INTEGER,
            section_title TEXT,
            chunk_text TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            chunk_policy TEXT NOT NULL,
            embedding_model TEXT,
            embedding_status TEXT NOT NULL DEFAULT 'pending',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(paper_id) REFERENCES papers(paper_id)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_full_text_chunks_paper
            ON full_text_chunks(paper_id);
        CREATE INDEX IF NOT EXISTS idx_full_text_chunks_pmid
            ON full_text_chunks(pmid);

        CREATE TABLE IF NOT EXISTS rag_index_artifacts (
            artifact_name TEXT PRIMARY KEY,
            artifact_type TEXT NOT NULL,
            path TEXT NOT NULL,
            status TEXT NOT NULL,
            embedding_model TEXT,
            chunk_policy TEXT,
            record_count INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS subsection_rag_queries (
            subsection_id TEXT PRIMARY KEY,
            query_text TEXT NOT NULL,
            query_source TEXT NOT NULL,
            embedding_model TEXT NOT NULL,
            lexical_limit INTEGER NOT NULL,
            semantic_limit INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS subsection_rag_paper_rankings (
            subsection_id TEXT NOT NULL,
            paper_rank INTEGER NOT NULL,
            paper_id TEXT NOT NULL,
            pmid TEXT,
            pmcid TEXT,
            doi TEXT,
            title TEXT,
            hybrid_score REAL NOT NULL,
            lexical_score REAL NOT NULL,
            semantic_score REAL NOT NULL,
            evidence_role_hint TEXT,
            selected_for_packet INTEGER NOT NULL DEFAULT 0,
            selection_reason TEXT,
            top_chunk_uids TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(subsection_id, paper_id),
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE,
            FOREIGN KEY(paper_id) REFERENCES papers(paper_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS subsection_rag_chunk_hits (
            subsection_id TEXT NOT NULL,
            chunk_uid TEXT NOT NULL,
            paper_id TEXT NOT NULL,
            bm25_rank TEXT,
            bm25_score REAL,
            semantic_rank TEXT,
            semantic_score REAL,
            rrf_score REAL NOT NULL,
            selected_for_packet INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(subsection_id, chunk_uid),
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE,
            FOREIGN KEY(chunk_uid) REFERENCES full_text_chunks(chunk_uid)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS subsection_rewrite_tasks (
            subsection_id TEXT PRIMARY KEY,
            chapter_title TEXT NOT NULL,
            subsection_title TEXT NOT NULL,
            original_subsection_path TEXT NOT NULL,
            paper_packet_path TEXT NOT NULL,
            work_order_path TEXT NOT NULL,
            rewritten_path TEXT,
            rewrite_status TEXT NOT NULL,
            assigned_worker TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS subsection_rewrite_checks (
            subsection_id TEXT PRIMARY KEY,
            rewritten_path TEXT NOT NULL,
            check_status TEXT NOT NULL,
            has_rewritten_text INTEGER NOT NULL DEFAULT 0,
            meets_expansion_floor INTEGER NOT NULL DEFAULT 0,
            has_paper_triage INTEGER NOT NULL DEFAULT 0,
            triages_all_packet_papers INTEGER NOT NULL DEFAULT 0,
            has_citation_register INTEGER NOT NULL DEFAULT 0,
            citation_register_traceable INTEGER NOT NULL DEFAULT 0,
            has_inline_citations INTEGER NOT NULL DEFAULT 0,
            inline_citations_registered INTEGER NOT NULL DEFAULT 0,
            registered_citations_used INTEGER NOT NULL DEFAULT 0,
            acknowledges_full_text_sources INTEGER NOT NULL DEFAULT 0,
            has_structured_evidence_details INTEGER NOT NULL DEFAULT 0,
            allowed_triage_roles INTEGER NOT NULL DEFAULT 0,
            allowed_support_statuses INTEGER NOT NULL DEFAULT 0,
            uses_packet_papers INTEGER NOT NULL DEFAULT 0,
            has_residual_uncertainty INTEGER NOT NULL DEFAULT 0,
            no_new_untraced_citations INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS terminology_entities (
            entity_id TEXT PRIMARY KEY,
            preferred_name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            aliases TEXT NOT NULL,
            first_mention_rule TEXT NOT NULL,
            normalization_status TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS terminology_normalization_checks (
            subsection_id TEXT PRIMARY KEY,
            normalized_path TEXT NOT NULL,
            check_status TEXT NOT NULL,
            has_text INTEGER NOT NULL DEFAULT 0,
            applies_known_aliases INTEGER NOT NULL DEFAULT 0,
            preserves_citation_ids INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS review_assembly_sections (
            subsection_id TEXT PRIMARY KEY,
            chapter_title TEXT NOT NULL,
            subsection_title TEXT NOT NULL,
            normalized_path TEXT NOT NULL,
            assembled_section_path TEXT NOT NULL,
            citation_count INTEGER NOT NULL DEFAULT 0,
            assembly_status TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS review_assembly_checks (
            check_name TEXT PRIMARY KEY,
            check_status TEXT NOT NULL,
            observed_value TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS claim_verification_claims (
            claim_id TEXT PRIMARY KEY,
            subsection_id TEXT NOT NULL,
            chapter_title TEXT NOT NULL,
            subsection_title TEXT NOT NULL,
            claim_text TEXT NOT NULL,
            cited_paper_ids TEXT NOT NULL,
            citation_ids TEXT NOT NULL,
            work_order_path TEXT NOT NULL,
            review_path TEXT NOT NULL,
            verification_status TEXT NOT NULL DEFAULT 'not_reviewed',
            corrected_claim TEXT,
            evidence_summary TEXT,
            reviewer_notes TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(subsection_id) REFERENCES subsections(subsection_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS claim_verification_checks (
            check_name TEXT PRIMARY KEY,
            check_status TEXT NOT NULL,
            observed_value TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS corrective_rewrite_claims (
            claim_id TEXT PRIMARY KEY,
            subsection_id TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            mismatch_type TEXT,
            original_claim TEXT NOT NULL,
            corrected_claim TEXT,
            final_replacement TEXT,
            action TEXT NOT NULL,
            replacement_status TEXT NOT NULL,
            cited_paper_ids TEXT NOT NULL,
            citation_ids TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(claim_id) REFERENCES claim_verification_claims(claim_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS corrective_rewrite_checks (
            check_name TEXT PRIMARY KEY,
            check_status TEXT NOT NULL,
            observed_value TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS final_review_sections (
            section_id TEXT PRIMARY KEY,
            section_type TEXT NOT NULL,
            title TEXT NOT NULL,
            source_subsection_id TEXT,
            citation_count INTEGER NOT NULL DEFAULT 0,
            uncertainty_note_count INTEGER NOT NULL DEFAULT 0,
            section_status TEXT NOT NULL,
            notes TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS final_review_checks (
            check_name TEXT PRIMARY KEY,
            check_status TEXT NOT NULL,
            observed_value TEXT,
            notes TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    ensure_column(connection, "subsection_rag_paper_rankings", "selection_reason", "TEXT")
    ensure_column(connection, "subsection_rewrite_checks", "meets_expansion_floor", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(connection, "subsection_rewrite_checks", "has_paper_triage", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(connection, "subsection_rewrite_checks", "triages_all_packet_papers", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(connection, "subsection_rewrite_checks", "citation_register_traceable", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(connection, "subsection_rewrite_checks", "has_inline_citations", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(connection, "subsection_rewrite_checks", "inline_citations_registered", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(connection, "subsection_rewrite_checks", "registered_citations_used", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(connection, "subsection_rewrite_checks", "acknowledges_full_text_sources", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(connection, "subsection_rewrite_checks", "has_structured_evidence_details", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(connection, "subsection_rewrite_checks", "allowed_triage_roles", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(connection, "subsection_rewrite_checks", "allowed_support_statuses", "INTEGER NOT NULL DEFAULT 0")
    connection.commit()


def ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

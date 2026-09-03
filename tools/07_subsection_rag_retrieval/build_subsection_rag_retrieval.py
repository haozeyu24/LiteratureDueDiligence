#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import pickle
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from qdrant_client import QdrantClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "06_full_text_rag_index"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_workflow_control"))

from build_full_text_rag_index import embed_texts, load_env_file, tokenize
from workflow_state import connect, timestamp


STAGE_DIR = Path("artifacts/06_subsection_rag_retrieval")
QUERY_DIR = STAGE_DIR / "01_queries"
HIT_DIR = STAGE_DIR / "02_chunk_hits"
RANKING_DIR = STAGE_DIR / "03_paper_ranking"
PACKET_DIR = STAGE_DIR / "04_paper_packets"
OUTPUT_DIR = STAGE_DIR / "05_outputs"

SUBSECTION_MANIFEST = Path("artifacts/02_subsection_retrieval/01_scope/subsection_manifest.csv")
FINAL_LITERATURE_SETS = Path("artifacts/02_subsection_retrieval/06_outputs/final_literature_sets.csv")
CHUNKS_JSONL = Path("artifacts/05_full_text_rag_index/01_chunks/chunks.jsonl")
BM25_PICKLE = Path("artifacts/05_full_text_rag_index/02_lexical/bm25.pkl")
RETRIEVAL_CONFIG = Path("artifacts/05_full_text_rag_index/04_hybrid/retrieval_config.json")
DRAFT_PATH = Path("drafts/initial_review.md")

DEFAULT_TARGET_PAPERS = 10
DEFAULT_LEXICAL_LIMIT = 80
DEFAULT_SEMANTIC_LIMIT = 80
DEFAULT_CHUNKS_PER_PAPER = 3
RRF_K = 60

QUERY_FIELDS = [
    "subsection_id",
    "chapter_title",
    "subsection_title",
    "query_source",
    "query_text",
    "embedding_model",
    "lexical_limit",
    "semantic_limit",
]

CHUNK_HIT_FIELDS = [
    "subsection_id",
    "chunk_uid",
    "paper_id",
    "pmid",
    "title",
    "section_title",
    "bm25_rank",
    "bm25_score",
    "semantic_rank",
    "semantic_score",
    "rrf_score",
    "selected_for_packet",
    "chunk_text_preview",
]

PAPER_RANKING_FIELDS = [
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
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build subsection-level hybrid RAG retrieval and paper packets."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    parser.add_argument("--env-file", type=Path, help="Path to .env containing OPENAI_API_KEY.")
    parser.add_argument("--target-papers", type=int, default=DEFAULT_TARGET_PAPERS)
    parser.add_argument("--lexical-limit", type=int, default=DEFAULT_LEXICAL_LIMIT)
    parser.add_argument("--semantic-limit", type=int, default=DEFAULT_SEMANTIC_LIMIT)
    parser.add_argument("--chunks-per-paper", type=int, default=DEFAULT_CHUNKS_PER_PAPER)
    args = parser.parse_args()

    if args.env_file:
        load_env_file(args.env_file)
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: OPENAI_API_KEY is required for subsection RAG retrieval.", file=os.sys.stderr)
        return 2

    run_dir = Path(args.run_dir)
    ensure_dirs(run_dir)
    write_stage_readme(run_dir)

    with connect(run_dir) as connection:
        if not stage6_complete(connection):
            print("ERROR: Stage 6 must be complete and validation-passed before Stage 7.", file=os.sys.stderr)
            return 1

        config = load_json(run_dir / RETRIEVAL_CONFIG)
        embedding_model = str(config.get("embedding_model") or "text-embedding-3-small")
        collection_name = str(config.get("collection_name") or "full_text_primary_1000o150_te3_small")
        chunks = load_chunks(run_dir / CHUNKS_JSONL)
        chunks_by_uid = {str(chunk["chunk_uid"]): chunk for chunk in chunks}
        chunks_by_paper = group_chunks_by_paper(chunks)
        bm25_payload = load_pickle(run_dir / BM25_PICKLE)
        subsections = load_subsections(run_dir)
        draft_sections = extract_draft_subsections(run_dir / DRAFT_PATH)
        subsection_roles = load_subsection_roles(run_dir)

        queries = build_queries(
            subsections,
            draft_sections,
            embedding_model,
            args.lexical_limit,
            args.semantic_limit,
        )
        query_embeddings = embed_texts([row["query_text"] for row in queries], embedding_model, api_key)
        qdrant = QdrantClient(path=str(run_dir / "artifacts/05_full_text_rag_index/03_vector/01_qdrant"))

        all_hits: list[dict[str, str]] = []
        all_rankings: list[dict[str, str]] = []
        packet_count = 0
        for query, vector in zip(queries, query_embeddings):
            subsection_id = query["subsection_id"]
            bm25_hits = run_bm25(query["query_text"], bm25_payload, chunks_by_uid, args.lexical_limit)
            semantic_hits = run_qdrant(qdrant, collection_name, vector, args.semantic_limit)
            fused_hits = fuse_chunk_hits(bm25_hits, semantic_hits)
            rankings = aggregate_to_papers(
                subsection_id,
                fused_hits,
                chunks_by_uid,
                chunks_by_paper,
                subsection_roles.get(subsection_id, {}),
                args.target_papers,
                args.chunks_per_paper,
            )
            selected_chunk_uids = {
                uid
                for ranking in rankings
                if ranking["selected_for_packet"] == "1"
                for uid in ranking["top_chunk_uids"].split(";")
                if uid
            }
            all_hits.extend(chunk_hit_rows(subsection_id, fused_hits, chunks_by_uid, selected_chunk_uids))
            all_rankings.extend(rankings)
            write_packet(run_dir, query, rankings, chunks_by_uid)
            packet_count += 1

        write_csv(run_dir / QUERY_DIR / "subsection_rag_queries.csv", QUERY_FIELDS, queries)
        write_csv(run_dir / HIT_DIR / "subsection_chunk_hits.csv", CHUNK_HIT_FIELDS, all_hits)
        write_csv(run_dir / RANKING_DIR / "subsection_paper_rankings.csv", PAPER_RANKING_FIELDS, all_rankings)
        write_summary(run_dir, queries, all_hits, all_rankings, packet_count, args)
        write_sqlite(connection, queries, all_hits, all_rankings)
        upsert_step(connection)

    print(
        "Stage 7 subsection RAG retrieval complete: "
        f"subsections={len(queries)} packets={packet_count} "
        f"paper_rankings={len(all_rankings)} chunk_hits={len(all_hits)}"
    )
    return 0


def ensure_dirs(run_dir: Path) -> None:
    for directory in (QUERY_DIR, HIT_DIR, RANKING_DIR, PACKET_DIR, OUTPUT_DIR):
        (run_dir / directory).mkdir(parents=True, exist_ok=True)


def write_stage_readme(run_dir: Path) -> None:
    path = run_dir / STAGE_DIR / "README.md"
    path.write_text(
        "# Subsection RAG Retrieval Artifacts\n\n"
        "This stage retrieves from the Stage 6 full-text RAG index for every draft "
        "subsection, fuses BM25 and semantic hits, aggregates chunks to paper-level "
        "rankings, and writes paper packets for downstream rewriting.\n\n"
        "- `01_queries/`: subsection retrieval queries derived from subsection content.\n"
        "- `02_chunk_hits/`: fused chunk-level retrieval hits.\n"
        "- `03_paper_ranking/`: paper-level rankings after chunk aggregation.\n"
        "- `04_paper_packets/`: one evidence packet per subsection.\n"
        "- `05_outputs/`: compact retrieval summary.\n",
        encoding="utf-8",
    )


def stage6_complete(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        """
        SELECT status, validation_status
        FROM workflow_steps
        WHERE step_name = 'full_text_rag_index'
        """
    ).fetchone()
    return bool(row and row["status"] == "complete" and row["validation_status"] == "passed")


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_pickle(path: Path) -> dict[str, object]:
    with path.open("rb") as handle:
        return pickle.load(handle)


def load_chunks(path: Path) -> list[dict[str, object]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_subsections(run_dir: Path) -> list[dict[str, str]]:
    with (run_dir / SUBSECTION_MANIFEST).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_subsection_roles(run_dir: Path) -> dict[str, dict[str, str]]:
    roles: dict[str, dict[str, str]] = defaultdict(dict)
    path = run_dir / FINAL_LITERATURE_SETS
    if not path.exists():
        return roles
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("abstract_review_decision") == "include_primary":
                roles[row.get("subsection_id", "")][row.get("paper_id", "")] = "primary_for_subsection"
            elif row.get("abstract_review_decision") == "include_context":
                roles[row.get("subsection_id", "")][row.get("paper_id", "")] = "context_for_subsection"
    return roles


def build_queries(
    subsections: list[dict[str, str]],
    draft_sections: dict[str, dict[str, str]],
    embedding_model: str,
    lexical_limit: int,
    semantic_limit: int,
) -> list[dict[str, str]]:
    rows = []
    for row in subsections:
        subsection_id = row["subsection_id"]
        draft_section = draft_sections.get(subsection_id, {})
        draft_prose = draft_section.get("prose", "")
        fallback_scope = "" if draft_prose else row.get("subsection_scope_note", "")
        query_text = normalize_space(
            " ".join(
                [
                    draft_prose,
                    draft_section.get("citation_clues", ""),
                    row.get("subsection_title", ""),
                    row.get("chapter_title", ""),
                    fallback_scope,
                ]
            )
        )
        rows.append(
            {
                "subsection_id": subsection_id,
                "chapter_title": row.get("chapter_title", ""),
                "subsection_title": row.get("subsection_title", ""),
                "query_source": "draft_subsection_prose + citation_clues + subsection_title + chapter_title",
                "query_text": query_text,
                "embedding_model": embedding_model,
                "lexical_limit": str(lexical_limit),
                "semantic_limit": str(semantic_limit),
            }
        )
    return rows


def extract_draft_subsections(path: Path) -> dict[str, dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    sections: dict[str, dict[str, str]] = {}
    current_id = ""
    current_lines: list[str] = []
    subsection_counter = 0

    for line in text.splitlines():
        if line.startswith("### Subsection "):
            if current_id:
                sections[current_id] = parse_draft_subsection(current_lines)
            subsection_counter += 1
            current_id = f"SUB{subsection_counter:03d}"
            current_lines = [line]
            continue
        if current_id and line.startswith("## Chapter "):
            sections[current_id] = parse_draft_subsection(current_lines)
            current_id = ""
            current_lines = []
            continue
        if current_id:
            current_lines.append(line)

    if current_id:
        sections[current_id] = parse_draft_subsection(current_lines)
    return sections


def parse_draft_subsection(lines: list[str]) -> dict[str, str]:
    prose_lines: list[str] = []
    citation_clues: list[str] = []
    in_register = False
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "#### Citation Register":
            in_register = True
            continue
        if not in_register:
            prose_lines.append(line)
            continue
        if not stripped.startswith("|") or stripped.startswith("|---"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 4 or cells[0] == "citation_id":
            continue
        citation = cells[1]
        pmid = cells[2]
        doi = cells[3]
        if citation.lower() != "citation needed":
            citation_clues.append(citation)
        if pmid and pmid.lower() != "unknown":
            citation_clues.append(f"PMID {pmid}")
        if doi and doi.lower() != "unknown":
            citation_clues.append(f"DOI {doi}")
    return {
        "prose": normalize_space("\n".join(prose_lines)),
        "citation_clues": normalize_space(" ".join(citation_clues)),
    }


def run_bm25(
    query_text: str,
    bm25_payload: dict[str, object],
    chunks_by_uid: dict[str, dict[str, object]],
    limit: int,
) -> list[dict[str, object]]:
    bm25 = bm25_payload["bm25"]
    chunk_uids = [str(uid) for uid in bm25_payload["chunk_uids"]]
    scores = bm25.get_scores(tokenize(query_text))
    ranked = sorted(enumerate(scores), key=lambda item: float(item[1]), reverse=True)[:limit]
    hits = []
    for rank, (index, score) in enumerate(ranked, start=1):
        uid = chunk_uids[index]
        if uid not in chunks_by_uid:
            continue
        hits.append({"chunk_uid": uid, "rank": rank, "score": float(score)})
    return hits


def run_qdrant(
    client: QdrantClient,
    collection_name: str,
    vector: list[float],
    limit: int,
) -> list[dict[str, object]]:
    result = client.query_points(
        collection_name=collection_name,
        query=vector,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    hits = []
    for rank, point in enumerate(result.points, start=1):
        payload = point.payload or {}
        hits.append(
            {
                "chunk_uid": str(payload.get("chunk_uid", "")),
                "rank": rank,
                "score": float(point.score or 0.0),
            }
        )
    return hits


def fuse_chunk_hits(
    bm25_hits: list[dict[str, object]], semantic_hits: list[dict[str, object]]
) -> dict[str, dict[str, object]]:
    fused: dict[str, dict[str, object]] = {}
    for hit in bm25_hits:
        uid = str(hit["chunk_uid"])
        fused.setdefault(uid, {"chunk_uid": uid, "bm25_rank": "", "bm25_score": 0.0, "semantic_rank": "", "semantic_score": 0.0, "rrf_score": 0.0})
        fused[uid]["bm25_rank"] = int(hit["rank"])
        fused[uid]["bm25_score"] = float(hit["score"])
        fused[uid]["rrf_score"] = float(fused[uid]["rrf_score"]) + 1.0 / (RRF_K + int(hit["rank"]))
    for hit in semantic_hits:
        uid = str(hit["chunk_uid"])
        fused.setdefault(uid, {"chunk_uid": uid, "bm25_rank": "", "bm25_score": 0.0, "semantic_rank": "", "semantic_score": 0.0, "rrf_score": 0.0})
        fused[uid]["semantic_rank"] = int(hit["rank"])
        fused[uid]["semantic_score"] = float(hit["score"])
        fused[uid]["rrf_score"] = float(fused[uid]["rrf_score"]) + 1.0 / (RRF_K + int(hit["rank"]))
    return fused


def aggregate_to_papers(
    subsection_id: str,
    fused_hits: dict[str, dict[str, object]],
    chunks_by_uid: dict[str, dict[str, object]],
    chunks_by_paper: dict[str, list[dict[str, object]]],
    subsection_roles: dict[str, str],
    target_papers: int,
    chunks_per_paper: int,
) -> list[dict[str, str]]:
    by_paper: dict[str, list[dict[str, object]]] = defaultdict(list)
    for uid, hit in fused_hits.items():
        chunk = chunks_by_uid.get(uid)
        if not chunk:
            continue
        by_paper[str(chunk["paper_id"])].append(hit)

    rankings = []
    for paper_id, hits in by_paper.items():
        hits.sort(key=lambda hit: float(hit["rrf_score"]), reverse=True)
        top_hits = hits[:chunks_per_paper]
        chunk = chunks_by_uid[str(top_hits[0]["chunk_uid"])]
        lexical_score = sum(float(hit.get("bm25_score") or 0.0) for hit in top_hits)
        semantic_score = sum(float(hit.get("semantic_score") or 0.0) for hit in top_hits)
        hybrid_score = sum(float(hit["rrf_score"]) for hit in top_hits)
        role = subsection_roles.get(paper_id, "global_primary_retrieved")
        if role == "primary_for_subsection":
            hybrid_score += 0.02
        rankings.append(
            {
                "subsection_id": subsection_id,
                "paper_id": paper_id,
                "pmid": str(chunk.get("pmid", "")),
                "pmcid": str(chunk.get("pmcid", "")),
                "doi": str(chunk.get("doi", "")),
                "title": str(chunk.get("title", "")),
                "source_format": str(chunk.get("source_format", "")),
                "hybrid_score": f"{hybrid_score:.6f}",
                "lexical_score": f"{lexical_score:.6f}",
                "semantic_score": f"{semantic_score:.6f}",
                "evidence_role_hint": role,
                "selected_for_packet": "0",
                "top_chunk_uids": ";".join(str(hit["chunk_uid"]) for hit in top_hits),
            }
        )

    ranked_paper_ids = {row["paper_id"] for row in rankings}
    for paper_id, role in subsection_roles.items():
        if role != "primary_for_subsection" or paper_id in ranked_paper_ids:
            continue
        fallback_chunks = recall_fallback_chunks(chunks_by_paper.get(paper_id, []), chunks_per_paper)
        if not fallback_chunks:
            continue
        chunk = fallback_chunks[0]
        rankings.append(
            {
                "subsection_id": subsection_id,
                "paper_id": paper_id,
                "pmid": str(chunk.get("pmid", "")),
                "pmcid": str(chunk.get("pmcid", "")),
                "doi": str(chunk.get("doi", "")),
                "title": str(chunk.get("title", "")),
                "source_format": str(chunk.get("source_format", "")),
                "hybrid_score": "0.020000",
                "lexical_score": "0.000000",
                "semantic_score": "0.000000",
                "evidence_role_hint": "primary_for_subsection",
                "selected_for_packet": "1",
                "top_chunk_uids": ";".join(str(item["chunk_uid"]) for item in fallback_chunks),
            }
        )

    rankings.sort(
        key=lambda row: (
            float(row["hybrid_score"]),
            1 if row["evidence_role_hint"] == "primary_for_subsection" else 0,
        ),
        reverse=True,
    )
    for rank, row in enumerate(rankings, start=1):
        row["paper_rank"] = str(rank)
        if rank <= target_papers:
            row["selected_for_packet"] = "1"
        elif row["evidence_role_hint"] == "primary_for_subsection":
            row["selected_for_packet"] = "1"
    for row in rankings:
        row["selection_reason"] = selection_reason(row, target_papers)
    return rankings


def selection_reason(row: dict[str, str], target_papers: int) -> str:
    if row["selected_for_packet"] != "1":
        return "not_selected"
    if (
        row["evidence_role_hint"] == "primary_for_subsection"
        and float(row.get("lexical_score") or 0.0) == 0.0
        and float(row.get("semantic_score") or 0.0) == 0.0
    ):
        return "stage4_primary_recall_added_no_query_hit"
    try:
        rank = int(row["paper_rank"])
    except ValueError:
        rank = target_papers + 1
    if rank <= target_papers:
        return "top_ranked"
    if row["evidence_role_hint"] == "primary_for_subsection":
        return "stage4_primary_force_included"
    return "selected"


def group_chunks_by_paper(chunks: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for chunk in chunks:
        grouped[str(chunk.get("paper_id", ""))].append(chunk)
    for paper_chunks in grouped.values():
        paper_chunks.sort(key=lambda chunk: int(chunk.get("chunk_index") or 0))
    return grouped


def recall_fallback_chunks(chunks: list[dict[str, object]], limit: int) -> list[dict[str, object]]:
    if not chunks:
        return []
    section_priority = {
        "abstract": 0,
        "introduction": 1,
        "results": 2,
        "discussion": 3,
    }
    ranked = sorted(
        chunks,
        key=lambda chunk: (
            section_priority.get(str(chunk.get("section_title", "")).strip().lower(), 4),
            int(chunk.get("chunk_index") or 0),
        ),
    )
    return ranked[:limit]


def chunk_hit_rows(
    subsection_id: str,
    fused_hits: dict[str, dict[str, object]],
    chunks_by_uid: dict[str, dict[str, object]],
    selected_chunk_uids: set[str],
) -> list[dict[str, str]]:
    rows = []
    for uid, hit in sorted(fused_hits.items(), key=lambda item: float(item[1]["rrf_score"]), reverse=True):
        chunk = chunks_by_uid.get(uid)
        if not chunk:
            continue
        rows.append(
            {
                "subsection_id": subsection_id,
                "chunk_uid": uid,
                "paper_id": str(chunk.get("paper_id", "")),
                "pmid": str(chunk.get("pmid", "")),
                "title": str(chunk.get("title", "")),
                "section_title": str(chunk.get("section_title", "")),
                "bm25_rank": str(hit.get("bm25_rank", "")),
                "bm25_score": f"{float(hit.get('bm25_score') or 0.0):.6f}",
                "semantic_rank": str(hit.get("semantic_rank", "")),
                "semantic_score": f"{float(hit.get('semantic_score') or 0.0):.6f}",
                "rrf_score": f"{float(hit.get('rrf_score') or 0.0):.6f}",
                "selected_for_packet": "1" if uid in selected_chunk_uids else "0",
                "chunk_text_preview": preview(str(chunk.get("text", "")), 260),
            }
        )
    return rows


def write_packet(
    run_dir: Path,
    query: dict[str, str],
    rankings: list[dict[str, str]],
    chunks_by_uid: dict[str, dict[str, object]],
) -> None:
    selected = [row for row in rankings if row["selected_for_packet"] == "1"]
    lines = [
        f"# Paper Packet: {query['subsection_id']}",
        "",
        "## Subsection",
        "",
        f"- chapter: {query['chapter_title']}",
        f"- subsection: {query['subsection_title']}",
        "",
        "## Retrieval Query",
        "",
        query["query_text"],
        "",
        "## Selected Papers",
        "",
    ]
    for row in selected:
        lines.extend(
            [
                f"### {row['paper_rank']}. {row['title']}",
                "",
                f"- paper_id: `{row['paper_id']}`",
                f"- PMID: `{row['pmid'] or 'unknown'}`",
                f"- PMCID: `{row['pmcid'] or 'unknown'}`",
                f"- DOI: `{row['doi'] or 'unknown'}`",
                f"- source_format: `{row['source_format']}`",
                f"- evidence_role_hint: `{row['evidence_role_hint']}`",
                f"- selection_reason: `{row['selection_reason']}`",
                f"- hybrid_score: `{row['hybrid_score']}`",
                "",
                "Relevant chunks:",
                "",
            ]
        )
        for uid in row["top_chunk_uids"].split(";"):
            chunk = chunks_by_uid.get(uid)
            if not chunk:
                continue
            lines.extend(
                [
                    f"- `{uid}` | section: {chunk.get('section_title', '')}",
                    "",
                    "```text",
                    preview(str(chunk.get("text", "")), 1200),
                    "```",
                    "",
                ]
            )
    lines.extend(
        [
            "## Rewrite Boundary",
            "",
            "Use this packet as retrieval evidence for subsection rewriting. The rewrite "
            "agent must inspect the cited papers and should not treat isolated chunk text "
            "as sufficient proof when the surrounding paper context changes the meaning.",
            "",
        ]
    )
    (run_dir / PACKET_DIR / f"{query['subsection_id']}.md").write_text("\n".join(lines), encoding="utf-8")


def write_summary(
    run_dir: Path,
    queries: list[dict[str, str]],
    hits: list[dict[str, str]],
    rankings: list[dict[str, str]],
    packet_count: int,
    args: argparse.Namespace,
) -> None:
    selected_papers = {
        (row["subsection_id"], row["paper_id"])
        for row in rankings
        if row["selected_for_packet"] == "1"
    }
    forced_primary = [
        row
        for row in rankings
        if row["selection_reason"] == "stage4_primary_force_included"
    ]
    recall_added_primary = [
        row
        for row in rankings
        if row["selection_reason"] == "stage4_primary_recall_added_no_query_hit"
    ]
    ranked_primary_pmids = {
        row["pmid"]
        for row in rankings
        if row["evidence_role_hint"] == "primary_for_subsection" and row.get("pmid")
    }
    selected_primary_pmids = {
        row["pmid"]
        for row in rankings
        if row["evidence_role_hint"] == "primary_for_subsection"
        and row["selected_for_packet"] == "1"
        and row.get("pmid")
    }
    primary_recall = (len(selected_primary_pmids) / len(ranked_primary_pmids) * 100.0) if ranked_primary_pmids else 0.0
    text = f"""# Subsection RAG Retrieval Summary

## Overall Status

`complete`

## Counts

- subsections queried: `{len(queries)}`
- paper packets written: `{packet_count}`
- chunk hits recorded: `{len(hits)}`
- paper rankings recorded: `{len(rankings)}`
- selected subsection-paper pairs: `{len(selected_papers)}`
- Stage 4 primary force-included pairs: `{len(forced_primary)}`
- Stage 4 primary no-query-hit recall-added pairs: `{len(recall_added_primary)}`
- target papers per subsection: `{args.target_papers}`
- lexical limit per subsection: `{args.lexical_limit}`
- semantic limit per subsection: `{args.semantic_limit}`
- chunks per selected paper: `{args.chunks_per_paper}`

## Retrieval Method

Queries are derived primarily from full draft subsection prose, then augmented
with draft citation clues and subsection titles. Stage 7 retrieves BM25 and
Qdrant semantic chunk hits, fuses them with reciprocal-rank fusion, aggregates
chunk evidence to paper-level rankings, and writes one paper packet per
subsection.

Stage 4 `primary_for_subsection` papers are force-included in their subsection
packet whenever they are present in the paper ranking, even if their hybrid rank
falls below the default top-paper cutoff. This preserves abstract-review primary
recall while still exposing RAG rank for rewrite triage.

## Recall Against Stage 4 Primary Cohort

- ranked Stage 4 primary PMIDs: `{len(ranked_primary_pmids)}`
- selected Stage 4 primary PMIDs: `{len(selected_primary_pmids)}`
- Stage 4 primary recall within Stage 7 packets: `{primary_recall:.1f}%`

## Downstream Use

Stage 8 should rewrite subsections from these paper packets, not from raw chunk
lists alone.
"""
    (run_dir / OUTPUT_DIR / "subsection_rag_retrieval_summary.md").write_text(text, encoding="utf-8")


def write_sqlite(
    connection: sqlite3.Connection,
    queries: list[dict[str, str]],
    hits: list[dict[str, str]],
    rankings: list[dict[str, str]],
) -> None:
    now = timestamp()
    connection.execute("DELETE FROM subsection_rag_queries")
    connection.execute("DELETE FROM subsection_rag_chunk_hits")
    connection.execute("DELETE FROM subsection_rag_paper_rankings")
    for query in queries:
        connection.execute(
            """
            INSERT INTO subsection_rag_queries(
                subsection_id, query_text, query_source, embedding_model,
                lexical_limit, semantic_limit, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query["subsection_id"],
                query["query_text"],
                query["query_source"],
                query["embedding_model"],
                int(query["lexical_limit"]),
                int(query["semantic_limit"]),
                now,
                now,
            ),
        )
    for hit in hits:
        connection.execute(
            """
            INSERT INTO subsection_rag_chunk_hits(
                subsection_id, chunk_uid, paper_id, bm25_rank, bm25_score,
                semantic_rank, semantic_score, rrf_score, selected_for_packet,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                hit["subsection_id"],
                hit["chunk_uid"],
                hit["paper_id"],
                hit["bm25_rank"],
                float(hit["bm25_score"]),
                hit["semantic_rank"],
                float(hit["semantic_score"]),
                float(hit["rrf_score"]),
                int(hit["selected_for_packet"]),
                now,
            ),
        )
    for row in rankings:
        connection.execute(
            """
            INSERT INTO subsection_rag_paper_rankings(
                subsection_id, paper_rank, paper_id, pmid, pmcid, doi, title,
                hybrid_score, lexical_score, semantic_score, evidence_role_hint,
                selected_for_packet, selection_reason, top_chunk_uids, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["subsection_id"],
                int(row["paper_rank"]),
                row["paper_id"],
                row["pmid"],
                row["pmcid"],
                row["doi"],
                row["title"],
                float(row["hybrid_score"]),
                float(row["lexical_score"]),
                float(row["semantic_score"]),
                row["evidence_role_hint"],
                int(row["selected_for_packet"]),
                row["selection_reason"],
                row["top_chunk_uids"],
                now,
            ),
        )
    connection.commit()


def upsert_step(connection: sqlite3.Connection) -> None:
    now = timestamp()
    connection.execute(
        """
        INSERT OR REPLACE INTO workflow_steps(
            step_name, status, started_at, completed_at, validation_status, notes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "subsection_rag_retrieval",
            "complete",
            now,
            now,
            "pending_validation",
            "Hybrid full-text retrieval completed and paper packets created for each subsection.",
        ),
    )
    connection.commit()


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def preview(text: str, limit: int) -> str:
    text = normalize_space(text)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


if __name__ == "__main__":
    raise SystemExit(main())

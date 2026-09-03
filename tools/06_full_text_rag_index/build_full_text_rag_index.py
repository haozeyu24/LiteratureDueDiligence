#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import pickle
import re
import sqlite3
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from rank_bm25 import BM25Okapi
from qdrant_client import QdrantClient
from qdrant_client import models as qmodels

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_workflow_control"))

from workflow_state import connect, timestamp


STAGE_DIR = Path("artifacts/05_full_text_rag_index")
CHUNK_DIR = STAGE_DIR / "01_chunks"
LEXICAL_DIR = STAGE_DIR / "02_lexical"
VECTOR_DIR = STAGE_DIR / "03_vector"
HYBRID_DIR = STAGE_DIR / "04_hybrid"
OUTPUT_DIR = STAGE_DIR / "05_outputs"
FULLTEXT_DIR = Path("artifacts/04_primary_full_text_ingestion")
IMPORT_STATUS = FULLTEXT_DIR / "06_outputs" / "import_status.csv"

CHUNK_POLICY_NAME = "structure_aware_1000_150"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIM = 1536
DEFAULT_COLLECTION_NAME = "full_text_primary_1000o150_te3_small"

CHUNK_FIELDS = [
    "chunk_uid",
    "paper_id",
    "pmid",
    "pmcid",
    "doi",
    "title",
    "source_format",
    "source_path",
    "normalized_path",
    "chunk_id",
    "chunk_index",
    "section_index",
    "section_title",
    "char_count",
    "chunk_policy",
    "embedding_model",
    "embedding_status",
]

PAPER_FIELDS = [
    "paper_id",
    "pmid",
    "pmcid",
    "doi",
    "title",
    "source_format",
    "normalized_path",
    "chunk_count",
    "total_chunk_chars",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the required run-local full-text RAG index: chunks, BM25, and Qdrant vectors."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    parser.add_argument("--embedding-model", default=DEFAULT_EMBEDDING_MODEL)
    parser.add_argument("--collection-name", default=DEFAULT_COLLECTION_NAME)
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Path to a .env file containing OPENAI_API_KEY for required vector indexing.",
    )
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--recreate-vector-index", action="store_true")
    args = parser.parse_args()

    if args.env_file:
        load_env_file(args.env_file)

    run_dir = Path(args.run_dir)
    ensure_dirs(run_dir)
    append_stage_readme(run_dir)

    with connect(run_dir) as connection:
        if not stage5_complete(connection):
            print("ERROR: Stage 5 must be complete and validation-passed before building the RAG index.", file=sys.stderr)
            return 1
        import_rows = load_import_rows(run_dir)
        chunks, papers = load_chunks(run_dir, import_rows, embedding_model=args.embedding_model)
        if not chunks:
            print("ERROR: no full-text chunks found in normalized Stage 5 JSON.", file=sys.stderr)
            return 1

        write_jsonl(run_dir / CHUNK_DIR / "chunks.jsonl", chunks)
        write_csv(run_dir / CHUNK_DIR / "chunk_manifest.csv", CHUNK_FIELDS, chunk_manifest_rows(chunks))
        write_csv(run_dir / CHUNK_DIR / "paper_manifest.csv", PAPER_FIELDS, paper_manifest_rows(papers))
        write_sqlite_chunks(connection, chunks, papers, args.embedding_model)

        bm25_path = run_dir / LEXICAL_DIR / "bm25.pkl"
        bm25_summary = build_bm25(chunks, bm25_path)
        write_json(run_dir / LEXICAL_DIR / "bm25_summary.json", bm25_summary)
        upsert_artifact(
            connection,
            artifact_name="bm25",
            artifact_type="lexical",
            path=relative_to_run(bm25_path, run_dir),
            status="complete",
            embedding_model="",
            record_count=len(chunks),
            notes="BM25Okapi lexical index over the same full-text chunks used for semantic retrieval.",
        )

        vector_summary = build_qdrant_index(
            run_dir=run_dir,
            chunks=chunks,
            embedding_model=args.embedding_model,
            collection_name=args.collection_name,
            batch_size=args.batch_size,
            recreate=args.recreate_vector_index,
        )
        if vector_summary["status"] == "complete":
            write_sqlite_chunks(connection, chunks, papers, args.embedding_model)
        write_json(run_dir / VECTOR_DIR / "vector_index_summary.json", vector_summary)
        upsert_artifact(
            connection,
            artifact_name="qdrant_vector_index",
            artifact_type="vector",
            path=str(VECTOR_DIR / "01_qdrant"),
            status=str(vector_summary["status"]),
            embedding_model=args.embedding_model,
            record_count=len(chunks) if vector_summary["status"] == "complete" else 0,
            notes=str(vector_summary.get("notes", "")),
        )

        retrieval_config = {
            "chunk_policy": CHUNK_POLICY_NAME,
            "embedding_model": args.embedding_model,
            "semantic_backend": "qdrant_local",
            "collection_name": args.collection_name,
            "lexical_backend": "rank_bm25.BM25Okapi",
            "hybrid_fusion": "reciprocal_rank_fusion",
            "paper_level_selection": {
                "target_papers_per_subsection": 10,
                "max_chunks_per_paper_for_initial_ranking": 2,
                "rank_chunks_first_then_aggregate_to_papers": True,
                "rewrite_uses_paper_packets_not_isolated_chunks": True,
            },
        }
        write_json(run_dir / HYBRID_DIR / "retrieval_config.json", retrieval_config)
        write_summary(run_dir, chunks, papers, bm25_summary, vector_summary)
        upsert_step(connection, vector_summary)

    print(
        "Stage 6 full-text RAG index "
        f"{step_status(vector_summary)}: papers={len(papers)} chunks={len(chunks)} "
        f"bm25=complete vector={vector_summary['status']}"
    )
    return 0 if vector_summary["status"] == "complete" else 2


def ensure_dirs(run_dir: Path) -> None:
    for directory in (CHUNK_DIR, LEXICAL_DIR, VECTOR_DIR / "01_qdrant", VECTOR_DIR / "02_embedding_cache", HYBRID_DIR, OUTPUT_DIR):
        (run_dir / directory).mkdir(parents=True, exist_ok=True)


def append_stage_readme(run_dir: Path) -> None:
    path = run_dir / STAGE_DIR / "README.md"
    if path.exists():
        return
    path.write_text(
        "# Full-Text RAG Index Artifacts\n\n"
        "This stage flattens normalized Stage 5 full-text chunks into a run-local "
        "chunk manifest, mirrors chunk records into SQLite, builds a BM25 lexical "
        "index, and builds a required Qdrant semantic index with "
        "`text-embedding-3-small`.\n\n"
        "- `01_chunks/`: chunk and paper manifests.\n"
        "- `02_lexical/`: BM25 artifact and summary.\n"
        "- `03_vector/`: Qdrant local store, embedding cache, and vector summary.\n"
        "- `04_hybrid/`: retrieval configuration for paper-level hybrid ranking.\n"
        "- `05_outputs/`: validation-ready stage summary.\n",
        encoding="utf-8",
    )


def stage5_complete(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        """
        SELECT status, validation_status
        FROM workflow_steps
        WHERE step_name = 'primary_full_text_ingestion'
        """
    ).fetchone()
    return bool(row and row["status"] == "complete" and row["validation_status"] == "passed")


def load_import_rows(run_dir: Path) -> list[dict[str, str]]:
    path = run_dir / IMPORT_STATUS
    with path.open(encoding="utf-8") as handle:
        return [row for row in csv.DictReader(handle) if row.get("ingestion_status") == "normalized"]


def load_chunks(run_dir: Path, import_rows: list[dict[str, str]], embedding_model: str) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    chunks: list[dict[str, object]] = []
    papers: dict[str, dict[str, object]] = {}
    for row in import_rows:
        normalized_path = run_dir / row["normalized_path"]
        payload = json.loads(normalized_path.read_text(encoding="utf-8"))
        policy = payload.get("chunk_policy", {})
        if policy.get("name") != CHUNK_POLICY_NAME:
            raise ValueError(f"{row['paper_id']} uses unexpected chunk policy: {policy}")
        paper_chunks = payload.get("chunks", [])
        paper = {
            "paper_id": row["paper_id"],
            "pmid": row.get("pmid", ""),
            "pmcid": row.get("pmcid", ""),
            "doi": row.get("doi", ""),
            "title": row.get("title", ""),
            "source_format": row.get("source_format", ""),
            "source_path": row.get("source_path", ""),
            "normalized_path": row.get("normalized_path", ""),
            "chunk_count": len(paper_chunks),
            "total_chunk_chars": 0,
        }
        for index, chunk in enumerate(paper_chunks, start=1):
            text = " ".join(str(chunk.get("text", "")).split())
            if not text:
                continue
            chunk_uid = f"{row['paper_id']}:{chunk.get('chunk_id') or f'CH{index:04d}'}"
            record = {
                "chunk_uid": chunk_uid,
                "paper_id": row["paper_id"],
                "pmid": row.get("pmid", ""),
                "pmcid": row.get("pmcid", ""),
                "doi": row.get("doi", ""),
                "title": row.get("title", ""),
                "source_format": row.get("source_format", ""),
                "source_path": row.get("source_path", ""),
                "normalized_path": row.get("normalized_path", ""),
                "chunk_id": str(chunk.get("chunk_id") or f"CH{index:04d}"),
                "chunk_index": index,
                "section_index": int(chunk.get("section_index") or 0),
                "section_title": str(chunk.get("section_title") or ""),
                "char_count": len(text),
                "chunk_policy": CHUNK_POLICY_NAME,
                "embedding_model": embedding_model,
                "embedding_status": "pending",
                "text": text,
            }
            chunks.append(record)
            paper["total_chunk_chars"] = int(paper["total_chunk_chars"]) + len(text)
        papers[row["paper_id"]] = paper
    return chunks, papers


def chunk_manifest_rows(chunks: list[dict[str, object]]) -> list[dict[str, str]]:
    return [{field: str(chunk.get(field, "")) for field in CHUNK_FIELDS} for chunk in chunks]


def paper_manifest_rows(papers: dict[str, dict[str, object]]) -> list[dict[str, str]]:
    return [{field: str(paper.get(field, "")) for field in PAPER_FIELDS} for paper in papers.values()]


def build_bm25(chunks: list[dict[str, object]], artifact_path: Path) -> dict[str, object]:
    tokenized = [tokenize(str(chunk["text"])) for chunk in chunks]
    bm25 = BM25Okapi(tokenized)
    payload = {
        "bm25": bm25,
        "chunk_uids": [chunk["chunk_uid"] for chunk in chunks],
        "paper_ids": [chunk["paper_id"] for chunk in chunks],
        "tokenizer": "lowercase_alphanumeric_min2",
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_path.open("wb") as handle:
        pickle.dump(payload, handle)
    lengths = [len(tokens) for tokens in tokenized]
    return {
        "status": "complete",
        "artifact_path": str(artifact_path),
        "chunk_count": len(chunks),
        "paper_count": len({chunk["paper_id"] for chunk in chunks}),
        "token_count_min": min(lengths) if lengths else 0,
        "token_count_mean": round(sum(lengths) / len(lengths), 2) if lengths else 0,
        "token_count_max": max(lengths) if lengths else 0,
    }


def build_qdrant_index(
    run_dir: Path,
    chunks: list[dict[str, object]],
    embedding_model: str,
    collection_name: str,
    batch_size: int,
    recreate: bool,
) -> dict[str, object]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "blocked_missing_api_key",
            "embedding_model": embedding_model,
            "collection_name": collection_name,
            "chunk_count": len(chunks),
            "notes": "OPENAI_API_KEY is required for text-embedding-3-small embeddings.",
        }
    qdrant_path = run_dir / VECTOR_DIR / "01_qdrant"
    client = QdrantClient(path=str(qdrant_path))
    if recreate and client.collection_exists(collection_name):
        client.delete_collection(collection_name)
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(size=DEFAULT_EMBEDDING_DIM, distance=qmodels.Distance.COSINE),
        )

    embedded = 0
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        vectors = embed_texts([str(chunk["text"]) for chunk in batch], embedding_model, api_key)
        points = []
        for chunk, vector in zip(batch, vectors):
            chunk["embedding_status"] = "embedded"
            points.append(
                qmodels.PointStruct(
                    id=stable_point_id(str(chunk["chunk_uid"])),
                    vector=vector,
                    payload={key: chunk[key] for key in chunk if key != "text"} | {"chunk_text": chunk["text"]},
                )
            )
        client.upsert(collection_name=collection_name, points=points)
        embedded += len(points)

    return {
        "status": "complete",
        "embedding_model": embedding_model,
        "collection_name": collection_name,
        "qdrant_path": str(qdrant_path),
        "chunk_count": len(chunks),
        "embedded_count": embedded,
        "notes": "Qdrant local semantic index built from full-text chunks.",
    }


def embed_texts(texts: list[str], model: str, api_key: str) -> list[list[float]]:
    payload = json.dumps({"model": model, "input": texts}).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120, context=ssl_context()) as response:
        data = json.loads(response.read().decode("utf-8"))
    ordered = sorted(data["data"], key=lambda item: item["index"])
    return [normalize_vector(item["embedding"]) for item in ordered]


def normalize_vector(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in values))
    if not norm:
        return values
    return [value / norm for value in values]


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def stable_point_id(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:16], 16)


def load_env_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f".env file not found: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = strip_env_quotes(value.strip())


def strip_env_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9_-]+", text.lower())


def write_sqlite_chunks(
    connection: sqlite3.Connection,
    chunks: list[dict[str, object]],
    papers: dict[str, dict[str, object]],
    embedding_model: str,
) -> None:
    now = timestamp()
    connection.execute("DELETE FROM full_text_chunks")
    for chunk in chunks:
        connection.execute(
            """
            INSERT INTO full_text_chunks(
                chunk_uid, paper_id, chunk_id, chunk_index, pmid, pmcid, doi, title,
                source_format, source_path, normalized_path, section_index,
                section_title, chunk_text, char_count, chunk_policy,
                embedding_model, embedding_status, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chunk["chunk_uid"],
                chunk["paper_id"],
                chunk["chunk_id"],
                int(chunk["chunk_index"]),
                chunk["pmid"],
                chunk["pmcid"],
                chunk["doi"],
                chunk["title"],
                chunk["source_format"],
                chunk["source_path"],
                chunk["normalized_path"],
                int(chunk["section_index"]),
                chunk["section_title"],
                chunk["text"],
                int(chunk["char_count"]),
                chunk["chunk_policy"],
                embedding_model,
                chunk["embedding_status"],
                now,
            ),
        )
    connection.commit()


def upsert_artifact(
    connection: sqlite3.Connection,
    *,
    artifact_name: str,
    artifact_type: str,
    path: str,
    status: str,
    embedding_model: str,
    record_count: int,
    notes: str,
) -> None:
    connection.execute(
        """
        INSERT OR REPLACE INTO rag_index_artifacts(
            artifact_name, artifact_type, path, status, embedding_model,
            chunk_policy, record_count, notes, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (artifact_name, artifact_type, path, status, embedding_model, CHUNK_POLICY_NAME, record_count, notes, timestamp()),
    )
    connection.commit()


def upsert_step(connection: sqlite3.Connection, vector_summary: dict[str, object]) -> None:
    status = step_status(vector_summary)
    notes = "Full-text chunks and BM25 index built."
    if vector_summary["status"] == "complete":
        notes += " Semantic Qdrant index built."
    else:
        notes += " Semantic Qdrant index is required and blocked because OPENAI_API_KEY is missing."
    now = timestamp()
    connection.execute(
        """
        INSERT OR REPLACE INTO workflow_steps(
            step_name, status, started_at, completed_at, validation_status, notes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("full_text_rag_index", status, now, now, "pending_validation", notes),
    )
    connection.commit()


def step_status(vector_summary: dict[str, object]) -> str:
    if vector_summary["status"] == "complete":
        return "complete"
    return "blocked_missing_api_key"


def write_summary(
    run_dir: Path,
    chunks: list[dict[str, object]],
    papers: dict[str, dict[str, object]],
    bm25_summary: dict[str, object],
    vector_summary: dict[str, object],
) -> None:
    source_counts = Counter(str(chunk["source_format"]) for chunk in chunks)
    text_lengths = [int(chunk["char_count"]) for chunk in chunks]
    text = f"""# Full-Text RAG Index Summary

## Overall Status

`{step_status(vector_summary)}`

## Counts

- papers indexed: `{len(papers)}`
- chunks indexed: `{len(chunks)}`
- PMC XML chunks: `{source_counts.get('pmc_xml', 0)}`
- PDF/GROBID chunks: `{source_counts.get('pdf', 0)}`
- chunk policy: `{CHUNK_POLICY_NAME}`
- chunk chars min/mean/max: `{min(text_lengths)}` / `{round(sum(text_lengths) / len(text_lengths), 1)}` / `{max(text_lengths)}`

## Indexes

- BM25 lexical index: `{bm25_summary['status']}`
- semantic vector index: `{vector_summary['status']}`
- embedding model: `{vector_summary.get('embedding_model', DEFAULT_EMBEDDING_MODEL)}`

## Downstream Use

Retrieval should rank chunks first, aggregate scores to papers, select paper-level
evidence packets for each subsection, and rewrite from paper packets rather than
isolated chunks.
"""
    (run_dir / OUTPUT_DIR / "rag_index_summary.md").write_text(text, encoding="utf-8")


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def relative_to_run(path: Path, run_dir: Path) -> str:
    try:
        return str(path.relative_to(run_dir))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())

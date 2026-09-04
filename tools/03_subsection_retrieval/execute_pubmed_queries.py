#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_workflow_control"))

from workflow_state import connect, timestamp


ARTIFACT_DIR = Path("artifacts/02_subsection_retrieval")
SCOPE_DIR = ARTIFACT_DIR / "01_scope"
QUERY_DIR = ARTIFACT_DIR / "02_queries"
PUBMED_DIR = ARTIFACT_DIR / "03_pubmed"
SCREENING_DIR = ARTIFACT_DIR / "04_screening"
RECALL_DIR = ARTIFACT_DIR / "05_recall"
OUTPUT_DIR = ARTIFACT_DIR / "06_outputs"
PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
NCBI_RATE_LIMIT_SECONDS = 0.34
USER_AGENT = "LiteratureDueDiligence/0.1 subsection pubmed metadata collector"
BATCH_SIZE = 100
TRANSIENT_CURL_EXIT_CODES = {18, 22, 28, 35, 52, 55, 56, 92}
ACCEPTABLE_MIN_COUNT = 10
ACCEPTABLE_MAX_COUNT = 300
DEFAULT_REDESIGN_WORK_ORDERS_PER_BAD_QUERY = 1
MIN_CANDIDATES_PER_SUBSECTION = 10
MAX_CANDIDATES_PER_SUBSECTION = 300


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run subsection PubMed queries and store metadata locally and in SQLite."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    parser.add_argument(
        "--retmax-per-query",
        type=int,
        default=200,
        help="Maximum PMIDs collected per query for diagnostic sampling and abstract-review staging.",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    artifact_dir = run_dir / ARTIFACT_DIR
    for directory in (SCOPE_DIR, QUERY_DIR, PUBMED_DIR, SCREENING_DIR, RECALL_DIR, OUTPUT_DIR):
        (run_dir / directory).mkdir(parents=True, exist_ok=True)
    query_plan_path = run_dir / QUERY_DIR / "query_plan.csv"
    if not query_plan_path.exists():
        print(f"ERROR: missing query plan: {query_plan_path}", file=sys.stderr)
        return 1

    query_rows = read_csv(query_plan_path)
    if not query_rows:
        print(f"ERROR: no query rows found in {query_plan_path}", file=sys.stderr)
        return 1
    semantic_errors = semantic_query_design_errors(query_rows)
    if semantic_errors:
        for error in semantic_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    query_results, pmid_sources = load_existing_query_results(run_dir, query_rows)
    existing_query_ids = {row.get("query_id", "").strip() for row in query_rows}
    executed_query_rows = rows_requiring_execution(query_rows, query_results)
    for row in executed_query_rows:
        query_id = row["query_id"].strip()
        subsection_id = row["subsection_id"].strip()
        query = row["pubmed_query"].strip()
        pmids, raw_count = pubmed_search(query, args.retmax_per_query)
        query_results[query_id] = {
            "row": row,
            "pmids": pmids,
            "raw_count": raw_count,
            "truncated": raw_count > len(pmids),
            "next_query_ids": child_query_ids(query_rows, query_id),
        }
        if count_status(raw_count) != "too_many":
            for pmid in pmids:
                source = pmid_sources.setdefault(
                    pmid, {"query_ids": set(), "subsection_ids": set()}
                )
                source["query_ids"].add(query_id)
                source["subsection_ids"].add(subsection_id)
        time.sleep(NCBI_RATE_LIMIT_SECONDS)
    pending_redesign_rows = stage_redesign_rows_for_bad_query_counts(
        query_rows, query_results, existing_query_ids
    )
    query_rows.extend(pending_redesign_rows)
    result_query_rows = [
        row
        for row in query_rows
        if row.get("query_id", "").strip() in query_results
    ]

    write_csv(query_plan_path, query_rows)

    records = fetch_pubmed_records(sorted(pmid_sources))
    for record in records:
        source = pmid_sources.get(record["pmid"], {"query_ids": set(), "subsection_ids": set()})
        record["source_query_ids"] = sorted(source["query_ids"])
        record["subsection_ids"] = sorted(source["subsection_ids"])
        record["retrieval_batch"] = time.strftime("%Y%m%d")
        record["links"] = {
            "pubmed": f"https://pubmed.ncbi.nlm.nih.gov/{record['pmid']}/",
            "pmc": f"https://pmc.ncbi.nlm.nih.gov/articles/{record['pmcid']}/"
            if record.get("pmcid")
            else "",
            "publisher": f"https://doi.org/{record['doi']}" if record.get("doi") else "",
        }

    records_by_pmid = {record["pmid"]: record for record in records}
    write_pubmed_records_jsonl(run_dir / PUBMED_DIR / "pubmed_records.jsonl", records)
    write_pubmed_record_index(run_dir / PUBMED_DIR / "pubmed_record_index.csv", records)
    write_query_diagnostics(run_dir / QUERY_DIR / "query_diagnostics.csv", result_query_rows, query_results)
    write_iteration_log(run_dir / QUERY_DIR / "search_iteration_log.csv", result_query_rows, query_results)
    write_triage_tables(run_dir / SCREENING_DIR, query_rows, query_results, records_by_pmid)
    write_recall_check(run_dir / RECALL_DIR / "draft_citation_recall_check.csv", records_by_pmid)
    write_final_literature_sets(
        run_dir / OUTPUT_DIR / "final_literature_sets.csv", query_rows, query_results, records_by_pmid
    )
    write_full_text_queue(
        run_dir / OUTPUT_DIR / "full_text_download_queue.csv", query_rows, query_results, records_by_pmid
    )
    write_metrics(run_dir / ARTIFACT_DIR, query_rows, query_results)
    write_report(
        run_dir / QUERY_DIR / "query_execution_report.md",
        query_rows,
        query_results,
        len(records),
        len(pending_redesign_rows),
        len(executed_query_rows),
    )
    update_sqlite(run_dir, result_query_rows, query_results, records)
    update_check(
        run_dir / OUTPUT_DIR / "subsection_retrieval_check.md",
        len(records),
        len(pending_redesign_rows),
    )

    print(
        f"Ran {len(executed_query_rows)} PubMed queries and stored {len(records)} unique PubMed records."
    )
    if pending_redesign_rows:
        print(
            f"Staged {len(pending_redesign_rows)} query-redesign work-order rows; "
            "an LLM must semantically redesign them before execution."
        )
    print(f"Wrote local metadata to {run_dir / PUBMED_DIR / 'pubmed_records.jsonl'}")
    print(f"Updated SQLite at {run_dir / 'artifacts/00_workflow_control/01_state/workflow_state.sqlite'}")
    return 0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_existing_query_results(
    run_dir: Path, query_rows: list[dict[str, str]]
) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, set[str]]]]:
    query_by_id = {row.get("query_id", ""): row for row in query_rows}
    query_results: dict[str, dict[str, object]] = {}
    pmid_sources: dict[str, dict[str, set[str]]] = {}
    pmids_by_query: dict[str, set[str]] = {}
    records_path = run_dir / PUBMED_DIR / "pubmed_records.jsonl"
    if records_path.exists():
        with records_path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                record = json.loads(line)
                pmid = str(record.get("pmid", "")).strip()
                if not pmid:
                    continue
                query_ids = {str(value) for value in record.get("source_query_ids", [])}
                subsection_ids = {str(value) for value in record.get("subsection_ids", [])}
                pmid_sources[pmid] = {
                    "query_ids": set(query_ids),
                    "subsection_ids": set(subsection_ids),
                }
                for query_id in query_ids:
                    pmids_by_query.setdefault(query_id, set()).add(pmid)

    diagnostics_path = run_dir / QUERY_DIR / "query_diagnostics.csv"
    if not diagnostics_path.exists():
        return query_results, pmid_sources
    next_query_ids_by_query: dict[str, list[str]] = {}
    iteration_path = run_dir / QUERY_DIR / "search_iteration_log.csv"
    if iteration_path.exists():
        for row in read_csv(iteration_path):
            query_id = row.get("query_id", "").strip()
            if not query_id:
                continue
            next_query_ids_by_query[query_id] = [
                value.strip()
                for value in row.get("next_query_id", "").split(";")
                if value.strip() and value.strip() != "controller_to_assign"
            ]
    for diagnostic in read_csv(diagnostics_path):
        query_id = diagnostic.get("query_id", "").strip()
        row = query_by_id.get(query_id)
        if not row:
            continue
        if diagnostic.get("query", "").strip() != row.get("pubmed_query", "").strip():
            continue
        raw_count = numeric_count(diagnostic.get("raw_hit_count", ""))
        if raw_count is None:
            continue
        query_results[query_id] = {
            "row": row,
            "pmids": sorted(pmids_by_query.get(query_id, set())),
            "raw_count": raw_count,
            "truncated": diagnostic.get("truncated_by_constraint") == "true",
            "next_query_ids": next_query_ids_by_query.get(query_id, []),
        }
    return query_results, pmid_sources


def numeric_count(value: str) -> int | None:
    value = str(value).strip()
    if not value.isdigit():
        return None
    return int(value)


def rows_requiring_execution(
    query_rows: list[dict[str, str]], query_results: dict[str, dict[str, object]]
) -> list[dict[str, str]]:
    return [
        row
        for row in query_rows
        if row.get("query_id", "").strip() not in query_results
    ]


def stage_redesign_rows_for_bad_query_counts(
    query_rows: list[dict[str, str]],
    query_results: dict[str, dict[str, object]],
    existing_query_ids: set[str],
) -> list[dict[str, str]]:
    staged: list[dict[str, str]] = []
    candidates_by_subsection = query_ids_by_subsection(query_results, query_rows)
    rows_by_subsection: dict[str, list[dict[str, str]]] = {}
    for row in query_rows:
        rows_by_subsection.setdefault(row.get("subsection_id", "").strip(), []).append(row)
    for subsection_id, subsection_rows in rows_by_subsection.items():
        candidate_count = len(candidates_by_subsection.get(subsection_id, {}))
        if subsection_candidate_count_is_reviewable(candidate_count):
            continue
        redesign_candidates = rows_for_subsection_redesign(
            subsection_rows, query_results, candidate_count
        )
        for row in redesign_candidates:
            query_id = row.get("query_id", "").strip()
            result = query_results.get(query_id)
            if not result:
                continue
            if child_query_ids(query_rows, query_id):
                continue
            if redesign_batch_has_acceptable_sibling(row, query_rows, query_results):
                continue
            forced_status = row_redesign_trigger_status(
                row, query_results, candidate_count
            )
            redesigned_rows = [
                redesigned
                for redesigned in redesign_queries_for_count(
                    row, int(result["raw_count"]), forced_status=forced_status
                )
                if redesigned["query_id"] not in existing_query_ids
            ]
            for redesigned in redesigned_rows:
                existing_query_ids.add(redesigned["query_id"])
            if redesigned_rows:
                result["next_query_ids"] = result.get("next_query_ids", []) + [
                    redesigned["query_id"] for redesigned in redesigned_rows
                ]
            staged.extend(redesigned_rows)
    return staged


def subsection_candidate_count_is_reviewable(candidate_count: int) -> bool:
    return MIN_CANDIDATES_PER_SUBSECTION <= candidate_count <= MAX_CANDIDATES_PER_SUBSECTION


def subsection_redesign_trigger_status(candidate_count: int) -> str:
    if candidate_count > MAX_CANDIDATES_PER_SUBSECTION:
        return "too_many"
    return "too_few"


def row_redesign_trigger_status(
    row: dict[str, str],
    query_results: dict[str, dict[str, object]],
    candidate_count: int,
) -> str:
    raw_status = count_status(int(query_results[row["query_id"]]["raw_count"]))
    if raw_status in {"too_many", "too_few"}:
        return raw_status
    return subsection_redesign_trigger_status(candidate_count)


def rows_for_subsection_redesign(
    subsection_rows: list[dict[str, str]],
    query_results: dict[str, dict[str, object]],
    candidate_count: int,
) -> list[dict[str, str]]:
    executed_leaf_rows = []
    for row in subsection_rows:
        query_id = row.get("query_id", "").strip()
        result = query_results.get(query_id)
        if not result:
            continue
        if child_query_ids(subsection_rows, query_id):
            continue
        if row.get("semantic_query_design_status") == "needs_llm_semantic_redesign":
            continue
        executed_leaf_rows.append(row)
    if candidate_count < MIN_CANDIDATES_PER_SUBSECTION:
        sparse_rows = [
            row
            for row in executed_leaf_rows
            if count_status(int(query_results[row["query_id"]]["raw_count"])) == "too_few"
        ]
        return sparse_rows or executed_leaf_rows
    if candidate_count > MAX_CANDIDATES_PER_SUBSECTION:
        return sorted(
            executed_leaf_rows,
            key=lambda row: int(query_results[row["query_id"]]["raw_count"]),
            reverse=True,
        )[:1]
    return []


def child_query_ids(query_rows: list[dict[str, str]], parent_query_id: str) -> list[str]:
    return [
        candidate.get("query_id", "").strip()
        for candidate in query_rows
        if candidate.get("redesign_parent_query_id", "").strip() == parent_query_id
    ]


def redesign_batch_has_acceptable_sibling(
    row: dict[str, str],
    query_rows: list[dict[str, str]],
    query_results: dict[str, dict[str, object]],
) -> bool:
    parent_query_id = row.get("redesign_parent_query_id", "").strip()
    if not parent_query_id:
        return False
    for candidate in query_rows:
        if candidate.get("redesign_parent_query_id", "").strip() != parent_query_id:
            continue
        candidate_id = candidate.get("query_id", "").strip()
        result = query_results.get(candidate_id)
        if result and count_status(int(result["raw_count"])) == "acceptable":
            return True
    return False


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def semantic_query_design_errors(query_rows: list[dict[str, str]]) -> list[str]:
    required_fields = {
        "semantic_evidence_need",
        "semantic_entity_terms",
        "semantic_mechanism_terms",
        "semantic_endpoint_or_context_terms",
        "query_false_positive_risks",
        "semantic_query_design_status",
        "semantic_query_designer",
    }
    errors: list[str] = []
    if not query_rows:
        return ["query_plan.csv has no query rows"]
    missing_fields = sorted(required_fields - set(query_rows[0]))
    if missing_fields:
        errors.append(
            "query_plan.csv is missing semantic query-design fields: "
            + ", ".join(missing_fields)
        )
        return errors
    acceptable_status_by_type = {
        "query_redesign": {"llm_semantic_redesigned"},
    }
    for row in query_rows:
        query_id = row.get("query_id", "unknown")
        status = row.get("semantic_query_design_status", "").strip()
        accepted_statuses = acceptable_status_by_type.get(
            row.get("query_type", ""), {"llm_semantic_designed"}
        )
        if status not in accepted_statuses:
            errors.append(
                f"{query_id} is not LLM semantic-designed for execution; "
                f"semantic_query_design_status={status or 'missing'}"
            )
        for field in sorted(required_fields - {"semantic_query_design_status"}):
            value = row.get(field, "").strip()
            if not value or value in {
                "unknown",
                "unassigned",
                "needs_llm_semantic_design",
                "needs_llm_semantic_redesign",
            }:
                errors.append(f"{query_id} has unfilled semantic query-design field: {field}")
        rationale = row.get("query_rationale", "").lower()
        if "heuristic seed only" in rationale or "work-order seed" in rationale:
            errors.append(f"{query_id} still has heuristic-seed rationale")
        if row.get("query_type") == "query_redesign":
            for field in (
                "redesign_parent_query_id",
                "redesign_trigger_count_status",
                "redesign_semantic_work_order",
            ):
                if not row.get(field, "").strip():
                    errors.append(f"{query_id} has unfilled redesign provenance field: {field}")
    return errors


def fetch_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except urllib.error.URLError as exc:
            if "CERTIFICATE_VERIFY_FAILED" in str(exc):
                return fetch_url_with_curl(url)
            if attempt == 3:
                raise
            time.sleep(attempt * 2)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(attempt * 2)
    raise RuntimeError("unreachable")


def fetch_url_with_curl(url: str) -> bytes:
    command = [
        "curl",
        "--http1.1",
        "--silent",
        "--show-error",
        "--fail",
        "--location",
        "--max-time",
        "60",
        "--user-agent",
        USER_AGENT,
        url,
    ]
    last_error: subprocess.CalledProcessError | None = None
    for attempt in range(1, 4):
        try:
            result = subprocess.run(command, check=True, capture_output=True)
            return result.stdout
        except subprocess.CalledProcessError as exc:
            last_error = exc
            if exc.returncode not in TRANSIENT_CURL_EXIT_CODES or attempt == 3:
                raise
            time.sleep(attempt * 2)
    assert last_error is not None
    raise last_error


def pubmed_search(query: str, retmax: int) -> tuple[list[str], int]:
    count_params = {
        "db": "pubmed",
        "term": query,
        "retmax": "0",
        "retmode": "json",
        "sort": "relevance",
    }
    count_url = f"{PUBMED_SEARCH_URL}?{urllib.parse.urlencode(count_params)}"
    count_payload = json.loads(fetch_url(count_url).decode("utf-8"))
    raw_count = int(count_payload["esearchresult"].get("count", "0"))
    if raw_count == 0:
        return [], raw_count

    fetch_params = {
        "db": "pubmed",
        "term": query,
        "retmax": str(min(retmax, raw_count)),
        "retmode": "json",
        "sort": "relevance",
    }
    fetch_url_value = f"{PUBMED_SEARCH_URL}?{urllib.parse.urlencode(fetch_params)}"
    payload = json.loads(fetch_url(fetch_url_value).decode("utf-8"))
    return [str(pmid) for pmid in payload["esearchresult"].get("idlist", [])], raw_count


def fetch_pubmed_records(pmids: list[str]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for batch in batched(pmids, BATCH_SIZE):
        if not batch:
            continue
        params = {"db": "pubmed", "id": ",".join(batch), "retmode": "xml"}
        url = f"{PUBMED_FETCH_URL}?{urllib.parse.urlencode(params)}"
        root = ET.fromstring(fetch_url(url))
        for article in root.findall(".//PubmedArticle"):
            record = parse_pubmed_article(article)
            if record.get("pmid"):
                records.append(record)
        time.sleep(NCBI_RATE_LIMIT_SECONDS)
    return records


def batched(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def text_or_none(value: str | None) -> str:
    return value.strip() if value else ""


def flatten(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def flatten_abstract(article: ET.Element) -> str:
    parts: list[str] = []
    for abstract_text in article.findall(".//Article/Abstract/AbstractText"):
        label = text_or_none(abstract_text.attrib.get("Label"))
        text = " ".join("".join(abstract_text.itertext()).split())
        if not text:
            continue
        parts.append(f"{label}: {text}" if label else text)
    return "\n\n".join(parts)


def parse_pubmed_article(article: ET.Element) -> dict[str, object]:
    medline = article.find(".//MedlineCitation")
    article_node = medline.find("Article") if medline is not None else None
    journal_node = article_node.find("Journal") if article_node is not None else None
    pmid = article.findtext(".//MedlineCitation/PMID", default="").strip()
    title = flatten(article_node.find("ArticleTitle") if article_node is not None else None)
    journal = (
        text_or_none(journal_node.findtext("Title", default="")) if journal_node is not None else ""
    )
    if not journal and journal_node is not None:
        journal = text_or_none(journal_node.findtext("ISOAbbreviation", default=""))
    doi = ""
    pmcid = ""
    for article_id in article.findall(".//PubmedData/ArticleIdList/ArticleId"):
        id_type = article_id.attrib.get("IdType", "")
        value = text_or_none(article_id.text)
        if id_type == "doi":
            doi = value
        elif id_type == "pmc":
            pmcid = value
    authors = []
    for author in article.findall(".//Article/AuthorList/Author"):
        collective = text_or_none(author.findtext("CollectiveName", default=""))
        if collective:
            authors.append(collective)
            continue
        last = text_or_none(author.findtext("LastName", default=""))
        initials = text_or_none(author.findtext("Initials", default=""))
        if last:
            authors.append(f"{last} {initials}".strip())
    publication_types = [
        text_or_none(node.text)
        for node in article.findall(".//PublicationTypeList/PublicationType")
        if text_or_none(node.text)
    ]
    year = publication_year(article)
    return {
        "paper_id": paper_id_from_pmid(pmid),
        "pmid": pmid,
        "pmcid": pmcid,
        "doi": doi,
        "title": title,
        "journal": journal,
        "publication_year": year,
        "authors": authors,
        "publication_types": publication_types,
        "abstract": flatten_abstract(article),
    }


def publication_year(article: ET.Element) -> str:
    paths = [
        ".//Article/ArticleDate/Year",
        ".//Article/Journal/JournalIssue/PubDate/Year",
        ".//PubMedPubDate[@PubStatus='pubmed']/Year",
    ]
    for path in paths:
        value = article.findtext(path, default="").strip()
        if re.match(r"^(19|20)\d\d$", value):
            return value
    medline_date = article.findtext(".//Article/Journal/JournalIssue/PubDate/MedlineDate", default="")
    match = re.search(r"(19|20)\d\d", medline_date)
    return match.group(0) if match else ""


def paper_id_from_pmid(pmid: str) -> str:
    return f"pmid-{pmid.strip()}" if pmid else ""


def quote_term(term: str) -> str:
    escaped = term.replace('"', "").strip()
    if re.search(r"[^A-Za-z0-9]", escaped):
        return f'"{escaped}"[Title/Abstract]'
    return f'{escaped}[Title/Abstract]'


def or_group(terms: list[str]) -> str:
    unique = list(dict.fromkeys(term for term in terms if term))
    if not unique:
        return ""
    if len(unique) == 1:
        return quote_term(unique[0])
    return "(" + " OR ".join(quote_term(term) for term in unique) + ")"


def and_join(parts: list[str]) -> str:
    return " AND ".join(part for part in parts if part)


def count_status(raw_count: int) -> str:
    if raw_count == 0:
        return "too_few"
    if raw_count < ACCEPTABLE_MIN_COUNT:
        return "too_few"
    if raw_count <= ACCEPTABLE_MAX_COUNT:
        return "acceptable"
    return "too_many"


def controller_action(raw_count: int) -> str:
    if raw_count == 0:
        return "redesign_query_keywords"
    if raw_count < ACCEPTABLE_MIN_COUNT:
        return "redesign_query_keywords"
    if raw_count <= ACCEPTABLE_MAX_COUNT:
        return "accept_for_abstract_review"
    return "redesign_query_keywords"


def redesign_queries_for_count(
    row: dict[str, str], raw_count: int, forced_status: str | None = None
) -> list[dict[str, str]]:
    status = forced_status or count_status(raw_count)
    if status == "acceptable":
        return []
    terms = query_terms(row)
    if status == "too_many":
        queries = tightened_queries(terms)
        if not queries:
            queries = semantic_fallback_redesign_queries(row, status)
        action = "tightened"
        rationale = (
            "Redesigned after an overbroad count; diagnostic samples from the parent "
            "must not be treated as retrieval coverage."
        )
        expected = f"{ACCEPTABLE_MIN_COUNT}-{ACCEPTABLE_MAX_COUNT}"
    else:
        queries = broadened_queries(terms)
        if not queries:
            queries = semantic_fallback_redesign_queries(row, status)
        action = "broadened"
        rationale = (
            "Redesigned after a sparse count; the new query removes brittle constraints "
            "or broadens closely related keyword variants."
        )
        expected = f"{ACCEPTABLE_MIN_COUNT}-{ACCEPTABLE_MAX_COUNT}"
    rows = []
    for offset, query in enumerate(queries[:DEFAULT_REDESIGN_WORK_ORDERS_PER_BAD_QUERY], start=1):
        rows.append(
            {
                "subsection_id": row["subsection_id"],
                "query_id": f"{row['query_id']}-R{offset:03d}",
                "query_type": "query_redesign",
                "pubmed_query": query,
                "required_terms": ";".join(terms[:4]),
                "optional_terms": ";".join(terms[4:]),
                "excluded_terms": row.get("excluded_terms", ""),
                "expected_result_band": expected,
                "recall_targets": row.get("recall_targets", ""),
                "semantic_evidence_need": row.get("semantic_evidence_need", ""),
                "semantic_entity_terms": row.get("semantic_entity_terms", ""),
                "semantic_mechanism_terms": row.get("semantic_mechanism_terms", ""),
                "semantic_endpoint_or_context_terms": row.get(
                    "semantic_endpoint_or_context_terms", ""
                ),
                "query_false_positive_risks": row.get("query_false_positive_risks", ""),
                "semantic_query_design_status": "needs_llm_semantic_redesign",
                "semantic_query_designer": "unassigned",
                "redesign_parent_query_id": row["query_id"],
                "redesign_trigger_count_status": status,
                "redesign_trigger_raw_hit_count": str(raw_count),
                "redesign_semantic_work_order": (
                    f"LLM must read the parent subsection evidence need, inspect this "
                    f"{status} count failure, and semantically {action} the query before execution."
                ),
                "query_rationale": (
                    f"Controller work-order seed for parent {row['query_id']}. {rationale} "
                    "Not executable until semantic_query_design_status is llm_semantic_redesigned."
                ),
            }
        )
    return rows


def semantic_fallback_redesign_queries(row: dict[str, str], status: str) -> list[str]:
    """Create a non-manual semantic redesign seed when token extraction is sparse."""
    entities = semantic_terms(
        row,
        [
            "semantic_entity_terms",
            "required_terms",
            "recall_targets",
        ],
    )
    concepts = semantic_terms(
        row,
        [
            "semantic_mechanism_terms",
            "semantic_endpoint_or_context_terms",
            "optional_terms",
            "semantic_evidence_need",
        ],
    )
    false_positive_terms = semantic_terms(row, ["query_false_positive_risks"])
    queries: list[str] = []
    if status == "too_many":
        primary = and_join([or_group(entities[:3]), or_group(concepts[:3])])
        if primary:
            queries.append(primary)
        narrower = and_join(
            [quote_term(term) for term in (entities[:1] + concepts[:2]) if term]
        )
        if narrower:
            queries.append(narrower)
        if false_positive_terms and queries:
            excluded = " NOT " + or_group(false_positive_terms[:3])
            queries = [query + excluded for query in queries]
    else:
        broader = or_group((entities + concepts)[:6])
        if broader:
            queries.append(broader)
        if entities:
            queries.append(or_group(entities[:4]))
        if concepts:
            queries.append(or_group(concepts[:4]))
    parent_query = row.get("pubmed_query", "").strip()
    return [
        query
        for query in dict.fromkeys(queries)
        if query and query != parent_query
    ]


def semantic_terms(row: dict[str, str], fields: list[str]) -> list[str]:
    terms: list[str] = []
    blocked_values = {
        "",
        "unknown",
        "unassigned",
        "none",
        "needs_llm_semantic_design",
        "needs_llm_semantic_redesign",
    }
    for field in fields:
        value = row.get(field, "")
        for token in re.split(r"[;,|]", value):
            term = token.strip().strip(".")
            lowered = term.lower()
            if lowered in blocked_values or looks_generic_query_word(term):
                continue
            if term and term not in terms:
                terms.append(term)
    return terms


def query_terms(row: dict[str, str]) -> list[str]:
    pieces = [
        row.get("required_terms", ""),
        row.get("optional_terms", ""),
        row.get("pubmed_query", ""),
    ]
    terms: list[str] = []
    for piece in pieces:
        for token in re.findall(r'"([^"]+)"\[Title/Abstract\]|([A-Za-z0-9][A-Za-z0-9+/.-]*)\[Title/Abstract\]|([A-Za-z0-9][A-Za-z0-9+/.-]*)', piece):
            term = next((part for part in token if part), "").strip().strip(".")
            if not term:
                continue
            lowered = term.lower()
            if lowered in {"and", "or", "not", "title", "abstract", "pmid"}:
                continue
            if lowered in {"title/abstract", "pubmed", "query"}:
                continue
            if looks_generic_query_word(term):
                continue
            if term not in terms:
                terms.append(term)
    return terms


def tightened_queries(terms: list[str]) -> list[str]:
    entities = [
        term for term in terms if looks_like_entity(term) and not looks_generic_query_word(term)
    ]
    concepts = sorted(
        [term for term in terms if term not in entities and not looks_generic_query_word(term)],
        key=concept_specificity_score,
        reverse=True,
    )
    if not entities:
        entities = [term for term in terms if not looks_generic_query_word(term)][:2]
    if not concepts:
        concepts = [term for term in terms if term not in entities][:3]
    queries: list[str] = []
    for concept in concepts[:5]:
        for entity in entities[:4]:
            if entity == concept:
                continue
            query = and_join([quote_term(entity), quote_term(concept)])
            if query and query not in queries:
                queries.append(query)
    if len(queries) < DEFAULT_REDESIGN_WORK_ORDERS_PER_BAD_QUERY:
        for entity in entities[:2]:
            focus = [term for term in concepts if term != entity][:2]
            query = and_join([quote_term(entity), *[quote_term(term) for term in focus]])
            if query and query not in queries:
                queries.append(query)
    return queries


def broadened_queries(terms: list[str]) -> list[str]:
    non_generic = [term for term in terms if not looks_generic_query_word(term)]
    entities = [term for term in non_generic if looks_like_entity(term)]
    concepts = [term for term in non_generic if term not in entities]
    queries: list[str] = []
    if entities and concepts:
        queries.append(and_join([or_group(entities[:3]), or_group(concepts[:3])]))
    if entities:
        queries.append(or_group(entities[:4]))
    if concepts:
        queries.append(or_group(concepts[:4]))
    if non_generic:
        queries.append(or_group(non_generic[:5]))
    return list(dict.fromkeys(query for query in queries if query))


def looks_like_entity(term: str) -> bool:
    return (
        term.isupper()
        or any(char.isdigit() for char in term)
        or any(char in term for char in "+/")
        or term.lower().endswith(("inib", "mab"))
    )


def looks_generic_query_word(term: str) -> bool:
    return term.lower().strip(".") in {
        "abstract",
        "activity",
        "analysis",
        "clinical",
        "context",
        "effect",
        "effects",
        "evidence",
        "expression",
        "function",
        "gene",
        "genes",
        "mechanism",
        "mechanisms",
        "may",
        "might",
        "model",
        "models",
        "nuclear",
        "paper",
        "papers",
        "protein",
        "proteins",
        "ptm",
        "ptms",
        "review",
        "search",
        "study",
        "studies",
        "target",
        "targets",
        "that",
        "region",
        "regions",
    }


def concept_specificity_score(term: str) -> int:
    lowered = term.lower().strip(".")
    score = 0
    if any(char in term for char in "-+/"):
        score += 6
    if any(char.isdigit() for char in term):
        score += 3
    if lowered.endswith(("ylation", "ation", "tion", "sion", "ase", "lysis")):
        score += 3
    if lowered in {
        "stability",
        "turnover",
        "degradation",
        "destabilization",
        "half-life",
        "localization",
        "retention",
        "mobility",
    }:
        score += 5
    if lowered in {"direct", "accumulation", "abundance", "activation", "perturbation"}:
        score -= 3
    return score


def subsection_controller_status(
    subsection_id: str,
    query_rows: list[dict[str, str]],
    query_results: dict[str, dict[str, object]],
    candidate_count: int,
) -> str:
    rows = [row for row in query_rows if row.get("subsection_id") == subsection_id]
    if any(
        row.get("semantic_query_design_status") == "needs_llm_semantic_redesign"
        for row in rows
    ):
        return "query_revision_needed"
    if any(row.get("query_id", "").strip() not in query_results for row in rows):
        return "query_revision_needed"
    if subsection_candidate_count_is_reviewable(candidate_count):
        return "abstract_review_needed"
    return "query_revision_needed"


def write_pubmed_records_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in sorted(records, key=lambda item: str(item.get("pmid", ""))):
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")


def write_pubmed_record_index(path: Path, records: list[dict[str, object]]) -> None:
    rows = []
    for record in records:
        rows.append(
            {
                "paper_id": record.get("paper_id", ""),
                "PMID": record.get("pmid", ""),
                "PMCID": record.get("pmcid", ""),
                "DOI": record.get("doi", ""),
                "title": record.get("title", ""),
                "journal": record.get("journal", ""),
                "publication_year": record.get("publication_year", ""),
                "publication_types": ";".join(record.get("publication_types", [])),
                "source_query_ids": ";".join(record.get("source_query_ids", [])),
                "subsection_ids": ";".join(record.get("subsection_ids", [])),
                "record_path": f"sqlite://pubmed_records/{record.get('paper_id', '')}",
            }
        )
    write_csv(
        path,
        sorted(rows, key=lambda row: (row["publication_year"], row["PMID"]), reverse=True),
        [
            "paper_id",
            "PMID",
            "PMCID",
            "DOI",
            "title",
            "journal",
            "publication_year",
            "publication_types",
            "source_query_ids",
            "subsection_ids",
            "record_path",
        ],
    )


def write_query_diagnostics(
    path: Path, query_rows: list[dict[str, str]], query_results: dict[str, dict[str, object]]
) -> None:
    rows = []
    for row in query_rows:
        result = query_results[row["query_id"]]
        raw_count = int(result["raw_count"])
        pmids = result["pmids"]
        rows.append(
            {
                "subsection_id": row["subsection_id"],
                "query_id": row["query_id"],
                "query": row["pubmed_query"],
                "raw_hit_count": str(raw_count),
                "collected_count": str(len(pmids)),
                "truncated_by_constraint": "true" if result["truncated"] else "false",
                "sample_size": str(len(pmids)),
                "sample_strategy": sample_strategy(raw_count, bool(result["truncated"])),
                "sampled_on_scope_count": "unknown",
                "sampled_noise_count": "unknown",
                "estimated_precision": "unknown",
                "dominant_noise_classes": "unknown",
                "missing_concepts": "unknown",
                "recall_signals": recall_signals(row, set(pmids)),
                "decision": controller_action(raw_count),
                "revision_rationale": revision_rationale(raw_count, len(pmids)),
            }
        )
    write_csv(path, rows)


def recall_signals(row: dict[str, str], pmids: set[str]) -> str:
    targets = [target.strip() for target in row.get("recall_targets", "").split(";") if target.strip()]
    if not targets:
        return "no_draft_targets"
    recovered = [target for target in targets if target in pmids]
    return f"target_rows={len(targets)};recovered_pmids={len(recovered)}"


def revision_rationale(raw_count: int, collected: int) -> str:
    if raw_count == 0:
        return "No PubMed records returned; controller should semantically broaden or redesign terms."
    if raw_count < ACCEPTABLE_MIN_COUNT:
        return "Sparse result count; controller should broaden unless known draft anchors are recovered."
    if raw_count <= ACCEPTABLE_MAX_COUNT:
        return "Result count is suitable for abstract-review staging."
    return (
        f"Query returned {raw_count} records; {collected} were collected only as a diagnostic sample. "
        "The controller must redesign query keywords and use acceptable-count redesigned queries "
        "for abstract-review coverage."
    )


def sample_strategy(raw_count: int, truncated: bool) -> str:
    if count_status(raw_count) == "too_many":
        return "diagnostic_sample_only"
    return "all_results" if not truncated else "top_relevance_sample"


def write_iteration_log(
    path: Path, query_rows: list[dict[str, str]], query_results: dict[str, dict[str, object]]
) -> None:
    rows = []
    candidates_by_subsection = query_ids_by_subsection(query_results, query_rows)
    for row in query_rows:
        raw_count = int(query_results[row["query_id"]]["raw_count"])
        subsection_id = row["subsection_id"]
        candidate_count = len(candidates_by_subsection.get(subsection_id, {}))
        rows.append(
            {
                "subsection_id": subsection_id,
                "query_id": row["query_id"],
                "iteration": "1",
                "run_status": "run",
                "result_count": str(raw_count),
                "count_status": count_status(raw_count),
                "controller_action": iteration_controller_action(
                    row, query_results, candidate_count
                ),
                "next_query_id": ";".join(query_results[row["query_id"]].get("next_query_ids", [])),
                "notes": iteration_notes(
                    raw_count,
                    len(query_results[row["query_id"]]["pmids"]),
                    candidate_count,
                ),
            }
        )
    write_csv(path, rows)


def iteration_controller_action(
    row: dict[str, str],
    query_results: dict[str, dict[str, object]],
    subsection_candidate_count: int,
) -> str:
    query_id = row.get("query_id", "").strip()
    result = query_results.get(query_id)
    if not result:
        return "run_query_or_estimate_count"
    if subsection_candidate_count_is_reviewable(subsection_candidate_count):
        if count_status(int(result["raw_count"])) == "too_many":
            return "diagnostic_only_subsection_covered"
        return "accept_for_abstract_review"
    status = count_status(int(result["raw_count"]))
    if status == "acceptable":
        return "accept_for_abstract_review_pending_subsection_balance"
    if result.get("next_query_ids"):
        return "redesign_query_keywords"
    if redesign_batch_has_acceptable_sibling(row, [result["row"] for result in query_results.values()], query_results):
        return "resolved_by_acceptable_redesign_sibling"
    return "redesign_query_keywords"


def iteration_notes(raw_count: int, collected: int, subsection_candidate_count: int) -> str:
    base = revision_rationale(raw_count, collected)
    return (
        f"{base} Subsection unique candidate count is {subsection_candidate_count}; "
        f"target range is {MIN_CANDIDATES_PER_SUBSECTION}-{MAX_CANDIDATES_PER_SUBSECTION}."
    )


def query_ids_by_subsection(
    query_results: dict[str, dict[str, object]],
    query_rows: list[dict[str, str]] | None = None,
) -> dict[str, dict[str, set[str]]]:
    by_subsection: dict[str, dict[str, set[str]]] = {}
    superseded_query_ids = set()
    if query_rows is not None:
        superseded_query_ids = {
            row.get("redesign_parent_query_id", "").strip()
            for row in query_rows
            if row.get("redesign_parent_query_id", "").strip()
        }
    for query_id, result in query_results.items():
        if query_id in superseded_query_ids:
            continue
        if count_status(int(result["raw_count"])) == "too_many":
            continue
        subsection_id = str(result["row"]["subsection_id"])
        for pmid in result["pmids"]:
            by_subsection.setdefault(subsection_id, {}).setdefault(str(pmid), set()).add(query_id)
    return by_subsection


def candidate_rows(
    query_rows: list[dict[str, str]],
    query_results: dict[str, dict[str, object]],
    records_by_pmid: dict[str, dict[str, object]],
) -> list[dict[str, str]]:
    rows = []
    for subsection_id, pmid_map in query_ids_by_subsection(query_results, query_rows).items():
        for pmid, query_ids in sorted(pmid_map.items()):
            record = records_by_pmid.get(pmid)
            if not record:
                continue
            rows.append(
                {
                    "subsection_id": subsection_id,
                    "paper_id": str(record.get("paper_id", paper_id_from_pmid(pmid))),
                    "PMID": pmid,
                    "PMCID": str(record.get("pmcid", "")),
                    "DOI": str(record.get("doi", "")),
                    "title": str(record.get("title", "")),
                    "abstract": str(record.get("abstract", "")),
                    "publication_types": ";".join(record.get("publication_types", [])),
                    "year": str(record.get("publication_year", "")),
                    "journal": str(record.get("journal", "")),
                    "source_query_ids": ";".join(sorted(query_ids)),
                    "verified_access_status": "pmc_available" if record.get("pmcid") else "abstract_available",
                    "venue_trust_label": "unknown",
                }
            )
    return rows


def write_triage_tables(
    artifact_dir: Path,
    query_rows: list[dict[str, str]],
    query_results: dict[str, dict[str, object]],
    records_by_pmid: dict[str, dict[str, object]],
) -> None:
    base_rows = candidate_rows(query_rows, query_results, records_by_pmid)
    first_rows = []
    rescue_rows = []
    for row in base_rows:
        first_rows.append(
            {
                **row,
                "first_pass_decision": "not_reviewed",
                "first_pass_rationale": "PubMed metadata collected; abstract triage not yet performed.",
                "first_pass_confidence": "unknown",
                "topic_match_type": "unknown",
                "semantic_fit_score": "unknown",
                "mechanism_match": "unknown",
                "entity_context_match": "unknown",
                "evidence_directness": "unknown",
                "key_relevant_abstract_text": "not_reviewed",
                "missing_full_text_reason": "unknown",
                "triage_actor": "not_started",
                "synthesis_role": "unknown",
                "reviewer_id": "not_reviewed",
                "review_method": "not_reviewed",
                "reviewer_model_or_agent": "not_reviewed",
                "reviewed_at": "not_reviewed",
                "prescreen_hint": "pubmed_candidate",
                "prescreen_rationale": "Returned by subsection-level PubMed query.",
                "prescreen_overlap_terms": "unknown",
            }
        )
        rescue_rows.append(
            {
                **row,
                "first_pass_decision": "not_reviewed",
                "first_pass_rationale": "PubMed metadata collected; first pass not yet performed.",
                "rescue_pass_decision": "not_reviewed",
                "rescue_pass_rationale": "Rescue pass not eligible until first-pass triage exists.",
                "rescue_pass_confidence": "unknown",
                "semantic_fit_score": "unknown",
                "mechanism_match": "unknown",
                "entity_context_match": "unknown",
                "evidence_directness": "unknown",
                "key_relevant_abstract_text": "not_reviewed",
                "missing_full_text_reason": "unknown",
                "promotion_decision": "not_promoted",
                "synthesis_role": "unknown",
                "reviewer_id": "not_reviewed",
                "review_method": "not_reviewed",
                "reviewer_model_or_agent": "not_reviewed",
                "reviewed_at": "not_reviewed",
            }
        )
    write_csv(
        artifact_dir / "abstract_triage_first_pass.csv",
        first_rows,
        [
            "subsection_id",
            "paper_id",
            "PMID",
            "DOI",
            "title",
            "abstract",
            "publication_types",
            "year",
            "source_query_ids",
            "first_pass_decision",
            "first_pass_rationale",
            "first_pass_confidence",
            "topic_match_type",
            "semantic_fit_score",
            "mechanism_match",
            "entity_context_match",
            "evidence_directness",
            "key_relevant_abstract_text",
            "missing_full_text_reason",
            "triage_actor",
            "synthesis_role",
            "prescreen_hint",
            "prescreen_rationale",
            "prescreen_overlap_terms",
            "reviewer_id",
            "review_method",
            "reviewer_model_or_agent",
            "reviewed_at",
        ],
    )
    write_csv(
        artifact_dir / "abstract_triage_rescue_pass.csv",
        rescue_rows,
        [
            "subsection_id",
            "paper_id",
            "PMID",
            "DOI",
            "title",
            "abstract",
            "publication_types",
            "year",
            "source_query_ids",
            "first_pass_decision",
            "first_pass_rationale",
            "rescue_pass_decision",
            "rescue_pass_rationale",
            "rescue_pass_confidence",
            "semantic_fit_score",
            "mechanism_match",
            "entity_context_match",
            "evidence_directness",
            "key_relevant_abstract_text",
            "missing_full_text_reason",
            "promotion_decision",
            "synthesis_role",
            "reviewer_id",
            "review_method",
            "reviewer_model_or_agent",
            "reviewed_at",
        ],
    )


def write_recall_check(path: Path, records_by_pmid: dict[str, dict[str, object]]) -> None:
    existing = read_csv(path) if path.exists() else []
    seen_pmids = set(records_by_pmid)
    rows = []
    for row in existing:
        pmid = row.get("PMID", "").strip()
        if row.get("controller_decision", "").strip() == "not_applicable":
            rows.append(
                {
                    **row,
                    "found_in_final_set": "not_applicable",
                    "controller_decision": "not_applicable",
                    "notes": "Initial draft contained no known citation anchors; recall is not applicable for this row.",
                }
            )
            continue
        found = bool(pmid and pmid in seen_pmids)
        rows.append(
            {
                **row,
                "found_in_final_set": "yes" if found else "no",
                "controller_decision": "recovered" if found else "recover_with_targeted_query",
                "notes": "Recovered in PubMed candidate set." if found else "Not recovered by current query set; needs targeted semantic query redesign.",
            }
        )
    if not rows:
        rows.append(
            {
                "subsection_id": "none",
                "citation_id": "none",
                "citation": "none",
                "PMID": "unknown",
                "DOI": "unknown",
                "discovery_provenance": "citation_needed",
                "found_in_final_set": "not_applicable",
                "controller_decision": "not_applicable",
                "notes": "Initial draft contained no known citation anchors; recall is not applicable until retrieval finds candidates.",
            }
        )
    write_csv(
        path,
        rows,
        [
            "subsection_id",
            "citation_id",
            "citation",
            "PMID",
            "DOI",
            "discovery_provenance",
            "found_in_final_set",
            "controller_decision",
            "notes",
        ],
    )


def write_final_literature_sets(
    path: Path,
    query_rows: list[dict[str, str]],
    query_results: dict[str, dict[str, object]],
    records_by_pmid: dict[str, dict[str, object]],
) -> None:
    rows = []
    for row in candidate_rows(query_rows, query_results, records_by_pmid):
        rows.append(
            {
                "subsection_id": row["subsection_id"],
                "paper_id": row["paper_id"],
                "PMID": row["PMID"],
                "PMCID": row["PMCID"],
                "DOI": row["DOI"],
                "title": row["title"],
                "journal": row["journal"],
                "publication_year": row["year"],
                "article_type": row["publication_types"],
                "abstract_review_decision": "not_reviewed",
                "evidence_role": "unknown",
                "draft_access_status": "unknown",
                "verified_access_status": row["verified_access_status"],
                "venue_trust_label": row["venue_trust_label"],
                "source_query_ids": row["source_query_ids"],
                "reason": "Collected from PubMed and awaiting subsection abstract review.",
            }
        )
    write_csv(
        path,
        rows,
        [
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
        ],
    )


def write_full_text_queue(
    path: Path,
    query_rows: list[dict[str, str]],
    query_results: dict[str, dict[str, object]],
    records_by_pmid: dict[str, dict[str, object]],
) -> None:
    rows = []
    for row in candidate_rows(query_rows, query_results, records_by_pmid):
        if row["verified_access_status"] == "pmc_available":
            continue
        rows.append(
            {
                "subsection_id": row["subsection_id"],
                "paper_id": row["paper_id"],
                "PMID": row["PMID"],
                "PMCID": row["PMCID"] or "unknown",
                "DOI": row["DOI"],
                "title": row["title"],
                "why_full_text_needed": "No PMCID found in PubMed metadata; full text may be needed for claim verification after abstract triage.",
                "download_priority": "unknown",
                "user_action": "await_abstract_triage_before_pdf_request",
            }
        )
    if not rows:
        rows.append(
            {
                "subsection_id": "none",
                "paper_id": "none",
                "PMID": "unknown",
                "PMCID": "unknown",
                "DOI": "unknown",
                "title": "none",
                "why_full_text_needed": "All collected PubMed candidates have PMCID metadata or no candidates were collected.",
                "download_priority": "unknown",
                "user_action": "none",
            }
        )
    write_csv(
        path,
        rows,
        [
            "subsection_id",
            "paper_id",
            "PMID",
            "PMCID",
            "DOI",
            "title",
            "why_full_text_needed",
            "download_priority",
            "user_action",
        ],
    )


def write_metrics(
    artifact_dir: Path, query_rows: list[dict[str, str]], query_results: dict[str, dict[str, object]]
) -> None:
    path = artifact_dir / "06_outputs" / "subsection_metrics.csv"
    existing = {row.get("subsection_id", ""): row for row in read_csv(path)} if path.exists() else {}
    rows = []
    final_rows = read_csv(artifact_dir / "06_outputs" / "final_literature_sets.csv")
    final_pmids_by_subsection: dict[str, set[str]] = {}
    for row in final_rows:
        final_pmids_by_subsection.setdefault(row.get("subsection_id", ""), set()).add(
            row.get("PMID", "")
        )
    planned_by_sub: dict[str, list[str]] = {}
    for row in query_rows:
        planned_by_sub.setdefault(row["subsection_id"], []).append(row["query_id"])
    for subsection_id, query_ids in planned_by_sub.items():
        executed_query_ids = [qid for qid in query_ids if qid in query_results]
        counts = [int(query_results[qid]["raw_count"]) for qid in executed_query_ids]
        unique_pmids = {
            pmid
            for pmid in final_pmids_by_subsection.get(subsection_id, set())
            if pmid
        }
        prior = existing.get(subsection_id, {})
        known_count = int(prior.get("draft_known_citation_count", "0") or "0")
        known_pmids = draft_known_pmids_for_subsection(artifact_dir, subsection_id)
        known_denominator = len(known_pmids) or known_count
        recovered = len(known_pmids & unique_pmids) if known_pmids else 0
        recall_rate = "unknown"
        if known_denominator:
            recall_rate = f"{min(recovered, known_denominator) / known_denominator:.3f}"
        status = subsection_controller_status(
            subsection_id, query_rows, query_results, len(unique_pmids)
        )
        rows.append(
            {
                "subsection_id": subsection_id,
                "queries_planned": str(len(query_ids)),
                "queries_run": str(len(executed_query_ids)),
                "total_pubmed_returned": str(sum(counts)),
                "total_collected_for_review": str(len(unique_pmids)),
                "draft_known_citation_count": str(known_count),
                "draft_citations_recovered": str(recovered),
                "draft_citation_recall_rate": recall_rate,
                "abstracts_reviewed": "0",
                "abstract_include_primary_count": "0",
                "abstract_include_context_count": "0",
                "abstract_uncertain_full_text_needed_count": "0",
                "abstract_rejected_count": "0",
                "abstract_rejection_rate": "unknown",
                "rescue_reviewed": "0",
                "rescue_promoted_count": "0",
                "final_literature_set_count": str(len(unique_pmids)),
                "full_text_download_queue_count": str(full_text_queue_count(artifact_dir, subsection_id)),
                "controller_status": status,
                "notes": "PubMed metadata collected locally; abstract review remains pending.",
            }
        )
    write_csv(path, rows)


def draft_known_pmids_for_subsection(artifact_dir: Path, subsection_id: str) -> set[str]:
    recall_path = artifact_dir / "05_recall" / "draft_citation_recall_check.csv"
    if not recall_path.exists():
        return set()
    return {
        row.get("PMID", "").strip()
        for row in read_csv(recall_path)
        if row.get("subsection_id") == subsection_id
        and row.get("PMID", "").strip()
        and row.get("PMID", "").strip().lower() != "unknown"
    }


def full_text_queue_count(artifact_dir: Path, subsection_id: str) -> int:
    queue_path = artifact_dir / "06_outputs" / "full_text_download_queue.csv"
    if not queue_path.exists():
        return 0
    return sum(1 for row in read_csv(queue_path) if row.get("subsection_id") == subsection_id)


def write_report(
    path: Path,
    query_rows: list[dict[str, str]],
    query_results: dict[str, dict[str, object]],
    unique_record_count: int,
    pending_redesign_count: int = 0,
    executed_this_pass: int = 0,
) -> None:
    by_sub: dict[str, list[str]] = {}
    for row in query_rows:
        by_sub.setdefault(row["subsection_id"], []).append(row["query_id"])
    lines = [
        "# PubMed Query Execution Report",
        "",
        "## Overall Status",
        "",
        "`query_redesign_required`" if pending_redesign_count else "`pass`",
        "",
        "## Metadata Store",
        "",
        f"Collected `{unique_record_count}` unique PubMed records into `pubmed_records.jsonl` and SQLite `pubmed_records`.",
        f"Executed `{executed_this_pass}` query rows in this pass and preserved prior counted rows.",
        "",
        "## Subsection Counts",
        "",
        "| subsection_id | queries_run | total_raw_hits | unique_candidates | controller_status |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    by_sub_candidates = final_record_counts_by_subsection(path)
    for subsection_id, query_ids in sorted(by_sub.items()):
        executed_query_ids = [qid for qid in query_ids if qid in query_results]
        counts = [int(query_results[qid]["raw_count"]) for qid in executed_query_ids]
        unique = by_sub_candidates.get(subsection_id, 0)
        status = subsection_controller_status(subsection_id, query_rows, query_results, unique)
        lines.append(
            f"| {subsection_id} | {len(executed_query_ids)} | {sum(counts)} | {unique} | {status} |"
        )
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            (
                f"Resolve `{pending_redesign_count}` pending query-redesign rows by LLM semantic redesign, "
                "then rerun PubMed execution."
                if pending_redesign_count
                else "Run subsection abstract review on `abstract_triage_first_pass.csv`; broad or empty queries should be revised before treating any subsection as finalized."
            ),
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def final_record_counts_by_subsection(report_path: Path) -> dict[str, int]:
    artifact_dir = report_path.parent.parent
    final_set_path = artifact_dir / "06_outputs" / "final_literature_sets.csv"
    if not final_set_path.exists():
        return {}
    counts: dict[str, set[str]] = {}
    for row in read_csv(final_set_path):
        subsection_id = row.get("subsection_id", "").strip()
        pmid = row.get("PMID", "").strip()
        if subsection_id and pmid:
            counts.setdefault(subsection_id, set()).add(pmid)
    return {subsection_id: len(pmids) for subsection_id, pmids in counts.items()}


def update_check(path: Path, unique_record_count: int, pending_redesign_count: int = 0) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else "# Subsection Retrieval Check\n"
    ready = "no" if pending_redesign_count else "yes"
    status = "query_redesign_required" if pending_redesign_count else "pass"
    pending_line = (
        f"\nPending semantic query redesign rows: `{pending_redesign_count}`.\n"
        if pending_redesign_count
        else ""
    )
    block = f"""

## PubMed Metadata Compliance

`{status}`

Collected `{unique_record_count}` unique PubMed metadata records locally and
mirrored them into SQLite `pubmed_records`.
{pending_line}

## Ready For Abstract Review

`{ready}`
"""
    if "## PubMed Metadata Compliance" not in text:
        text = text.rstrip() + block
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def update_sqlite(
    run_dir: Path,
    query_rows: list[dict[str, str]],
    query_results: dict[str, dict[str, object]],
    records: list[dict[str, object]],
) -> None:
    now = timestamp()
    with connect(run_dir) as connection:
        connection.execute("DELETE FROM subsection_papers")
        connection.execute("DELETE FROM pubmed_records")
        connection.execute("DELETE FROM papers")
        connection.execute("DELETE FROM query_iterations")
        connection.execute("DELETE FROM pubmed_queries")
        for row in query_rows:
            result = query_results[row["query_id"]]
            raw_count = int(result["raw_count"])
            connection.execute(
                """
                INSERT INTO pubmed_queries(
                    query_id, subsection_id, query_type, pubmed_query,
                    required_terms, optional_terms, excluded_terms, expected_result_band,
                    recall_targets, query_rationale, latest_count_status, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(query_id) DO UPDATE SET
                    pubmed_query = excluded.pubmed_query,
                    required_terms = excluded.required_terms,
                    optional_terms = excluded.optional_terms,
                    excluded_terms = excluded.excluded_terms,
                    expected_result_band = excluded.expected_result_band,
                    recall_targets = excluded.recall_targets,
                    query_rationale = excluded.query_rationale,
                    latest_count_status = excluded.latest_count_status,
                    updated_at = excluded.updated_at
                """,
                (
                    row["query_id"],
                    row["subsection_id"],
                    row["query_type"],
                    row["pubmed_query"],
                    row.get("required_terms", ""),
                    row.get("optional_terms", ""),
                    row.get("excluded_terms", ""),
                    row.get("expected_result_band", ""),
                    row.get("recall_targets", ""),
                    row.get("query_rationale", ""),
                    count_status(raw_count),
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO query_iterations(
                    subsection_id, query_id, iteration, run_status, result_count,
                    count_status, controller_action, next_query_id, notes, created_at
                )
                VALUES (?, ?, 1, 'run', ?, ?, ?, ?, ?, ?)
                ON CONFLICT(query_id, iteration) DO UPDATE SET
                    run_status = excluded.run_status,
                    result_count = excluded.result_count,
                    count_status = excluded.count_status,
                    controller_action = excluded.controller_action,
                    next_query_id = excluded.next_query_id,
                    notes = excluded.notes,
                    created_at = excluded.created_at
                """,
                (
                    row["subsection_id"],
                    row["query_id"],
                    str(raw_count),
                    count_status(raw_count),
                    controller_action(raw_count),
                    ";".join(result.get("next_query_ids", [])),
                    revision_rationale(raw_count, len(result["pmids"])),
                    now,
                ),
            )
        for record in records:
            raw_json = json.dumps(record, ensure_ascii=True, sort_keys=True)
            paper_id = str(record.get("paper_id", ""))
            connection.execute(
                """
                INSERT INTO papers(
                    paper_id, pmid, pmcid, doi, title, journal,
                    publication_year, article_type, venue_trust_label,
                    first_seen_subsection_id, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'unknown', ?, ?)
                ON CONFLICT(paper_id) DO UPDATE SET
                    pmid = excluded.pmid,
                    pmcid = excluded.pmcid,
                    doi = excluded.doi,
                    title = excluded.title,
                    journal = excluded.journal,
                    publication_year = excluded.publication_year,
                    article_type = excluded.article_type,
                    updated_at = excluded.updated_at
                """,
                (
                    paper_id,
                    record.get("pmid", ""),
                    record.get("pmcid", ""),
                    record.get("doi", ""),
                    record.get("title", ""),
                    record.get("journal", ""),
                    record.get("publication_year", ""),
                    ";".join(record.get("publication_types", [])),
                    ";".join(record.get("subsection_ids", [])[:1]),
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO pubmed_records(
                    paper_id, pmid, pmcid, doi, title, journal, publication_year,
                    authors_json, publication_types_json, abstract,
                    source_query_ids_json, subsection_ids_json, retrieval_batch,
                    raw_json, sha256, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(paper_id) DO UPDATE SET
                    pmid = excluded.pmid,
                    pmcid = excluded.pmcid,
                    doi = excluded.doi,
                    title = excluded.title,
                    journal = excluded.journal,
                    publication_year = excluded.publication_year,
                    authors_json = excluded.authors_json,
                    publication_types_json = excluded.publication_types_json,
                    abstract = excluded.abstract,
                    source_query_ids_json = excluded.source_query_ids_json,
                    subsection_ids_json = excluded.subsection_ids_json,
                    retrieval_batch = excluded.retrieval_batch,
                    raw_json = excluded.raw_json,
                    sha256 = excluded.sha256,
                    updated_at = excluded.updated_at
                """,
                (
                    paper_id,
                    record.get("pmid", ""),
                    record.get("pmcid", ""),
                    record.get("doi", ""),
                    record.get("title", ""),
                    record.get("journal", ""),
                    record.get("publication_year", ""),
                    json.dumps(record.get("authors", []), ensure_ascii=True),
                    json.dumps(record.get("publication_types", []), ensure_ascii=True),
                    record.get("abstract", ""),
                    json.dumps(record.get("source_query_ids", []), ensure_ascii=True),
                    json.dumps(record.get("subsection_ids", []), ensure_ascii=True),
                    record.get("retrieval_batch", ""),
                    raw_json,
                    hashlib.sha256(raw_json.encode("utf-8")).hexdigest(),
                    now,
                ),
            )
        for row in candidate_rows(
            query_rows, query_results, {str(record["pmid"]): record for record in records}
        ):
            connection.execute(
                """
                INSERT INTO subsection_papers(
                    subsection_id, paper_id, abstract_review_decision,
                    evidence_role, draft_access_status, verified_access_status,
                    source_query_ids, reason, updated_at
                )
                VALUES (?, ?, 'not_reviewed', 'unknown', 'unknown', ?, ?, ?, ?)
                ON CONFLICT(subsection_id, paper_id) DO UPDATE SET
                    verified_access_status = excluded.verified_access_status,
                    source_query_ids = excluded.source_query_ids,
                    reason = excluded.reason,
                    updated_at = excluded.updated_at
                """,
                (
                    row["subsection_id"],
                    row["paper_id"],
                    row["verified_access_status"],
                    row["source_query_ids"],
                    "Collected from PubMed and awaiting subsection abstract review.",
                    now,
                ),
            )
        for metric in read_csv(run_dir / OUTPUT_DIR / "subsection_metrics.csv"):
            connection.execute(
                """
                INSERT INTO subsection_metrics(
                    subsection_id, queries_planned, queries_run, total_pubmed_returned,
                    total_collected_for_review, draft_known_citation_count,
                    draft_citations_recovered, draft_citation_recall_rate,
                    abstracts_reviewed, abstract_include_primary_count,
                    abstract_include_context_count,
                    abstract_uncertain_full_text_needed_count,
                    abstract_rejected_count, abstract_rejection_rate,
                    rescue_reviewed, rescue_promoted_count, final_literature_set_count,
                    full_text_download_queue_count, controller_status, notes, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(subsection_id) DO UPDATE SET
                    queries_planned = excluded.queries_planned,
                    queries_run = excluded.queries_run,
                    total_pubmed_returned = excluded.total_pubmed_returned,
                    total_collected_for_review = excluded.total_collected_for_review,
                    draft_known_citation_count = excluded.draft_known_citation_count,
                    draft_citations_recovered = excluded.draft_citations_recovered,
                    draft_citation_recall_rate = excluded.draft_citation_recall_rate,
                    final_literature_set_count = excluded.final_literature_set_count,
                    full_text_download_queue_count = excluded.full_text_download_queue_count,
                    controller_status = excluded.controller_status,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (
                    metric["subsection_id"],
                    int(metric["queries_planned"]),
                    int(metric["queries_run"]),
                    metric["total_pubmed_returned"],
                    metric["total_collected_for_review"],
                    int(metric["draft_known_citation_count"]),
                    metric["draft_citations_recovered"],
                    metric["draft_citation_recall_rate"],
                    int(metric["abstracts_reviewed"]),
                    int(metric["abstract_include_primary_count"]),
                    int(metric["abstract_include_context_count"]),
                    int(metric["abstract_uncertain_full_text_needed_count"]),
                    int(metric["abstract_rejected_count"]),
                    metric["abstract_rejection_rate"],
                    int(metric["rescue_reviewed"]),
                    int(metric["rescue_promoted_count"]),
                    int(metric["final_literature_set_count"]),
                    int(metric["full_text_download_queue_count"]) if metric["full_text_download_queue_count"].isdigit() else 0,
                    metric["controller_status"],
                    metric["notes"],
                    now,
                ),
            )
        connection.commit()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: PubMed query execution failed: {exc}", file=sys.stderr)
        raise

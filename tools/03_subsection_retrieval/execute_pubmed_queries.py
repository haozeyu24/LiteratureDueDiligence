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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run subsection PubMed queries and store metadata locally and in SQLite."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    parser.add_argument(
        "--retmax-per-query",
        type=int,
        default=200,
        help="Maximum PMIDs collected per query for abstract-review staging.",
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

    query_results: dict[str, dict[str, object]] = {}
    pmid_sources: dict[str, dict[str, set[str]]] = {}
    for row in query_rows:
        query_id = row["query_id"].strip()
        subsection_id = row["subsection_id"].strip()
        query = row["pubmed_query"].strip()
        pmids, raw_count = pubmed_search(query, args.retmax_per_query)
        query_results[query_id] = {
            "row": row,
            "pmids": pmids,
            "raw_count": raw_count,
            "truncated": raw_count > len(pmids),
        }
        for pmid in pmids:
            source = pmid_sources.setdefault(
                pmid, {"query_ids": set(), "subsection_ids": set()}
            )
            source["query_ids"].add(query_id)
            source["subsection_ids"].add(subsection_id)
        time.sleep(NCBI_RATE_LIMIT_SECONDS)

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
    write_query_diagnostics(run_dir / QUERY_DIR / "query_diagnostics.csv", query_rows, query_results)
    write_iteration_log(run_dir / QUERY_DIR / "search_iteration_log.csv", query_rows, query_results)
    write_triage_tables(run_dir / SCREENING_DIR, query_results, records_by_pmid)
    write_recall_check(run_dir / RECALL_DIR / "draft_citation_recall_check.csv", records_by_pmid)
    write_final_literature_sets(
        run_dir / OUTPUT_DIR / "final_literature_sets.csv", query_results, records_by_pmid
    )
    write_full_text_queue(run_dir / OUTPUT_DIR / "full_text_download_queue.csv", query_results, records_by_pmid)
    write_metrics(run_dir / ARTIFACT_DIR, query_rows, query_results)
    write_report(run_dir / QUERY_DIR / "query_execution_report.md", query_rows, query_results, len(records))
    update_sqlite(run_dir, query_rows, query_results, records)
    update_check(run_dir / OUTPUT_DIR / "subsection_retrieval_check.md", len(records))

    print(
        f"Ran {len(query_rows)} PubMed queries and stored {len(records)} unique PubMed records."
    )
    print(f"Wrote local metadata to {run_dir / PUBMED_DIR / 'pubmed_records.jsonl'}")
    print(f"Updated SQLite at {run_dir / 'artifacts/00_workflow_control/01_state/workflow_state.sqlite'}")
    return 0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


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


def count_status(raw_count: int) -> str:
    if raw_count == 0:
        return "too_few"
    if raw_count <= 5:
        return "too_few"
    if raw_count <= 200:
        return "acceptable"
    if raw_count <= 500:
        return "too_many"
    return "too_many"


def controller_action(raw_count: int) -> str:
    if raw_count == 0:
        return "broaden_query"
    if raw_count <= 5:
        return "broaden_query"
    if raw_count <= 200:
        return "accept_for_abstract_review"
    return "refine_query"


def subsection_controller_status(candidate_count: int) -> str:
    if candidate_count == 0:
        return "manual_search_needed"
    if candidate_count <= 5:
        return "query_revision_needed"
    if candidate_count <= 600:
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
                "sample_strategy": "all_results" if not result["truncated"] else "top_relevance_sample",
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
        return "No PubMed records returned; controller should broaden terms or use manual lookup."
    if raw_count <= 5:
        return "Sparse result count; controller should broaden unless known draft anchors are recovered."
    if raw_count <= 200:
        return "Result count is suitable for abstract-review staging."
    return (
        f"Query returned {raw_count} records; {collected} were staged as a top-relevance sample "
        "and the controller should refine before treating the subsection set as complete."
    )


def write_iteration_log(
    path: Path, query_rows: list[dict[str, str]], query_results: dict[str, dict[str, object]]
) -> None:
    rows = []
    for row in query_rows:
        raw_count = int(query_results[row["query_id"]]["raw_count"])
        rows.append(
            {
                "subsection_id": row["subsection_id"],
                "query_id": row["query_id"],
                "iteration": "1",
                "run_status": "run",
                "result_count": str(raw_count),
                "count_status": count_status(raw_count),
                "controller_action": controller_action(raw_count),
                "next_query_id": "controller_to_assign" if raw_count == 0 or raw_count <= 5 or raw_count > 200 else "",
                "notes": revision_rationale(raw_count, len(query_results[row["query_id"]]["pmids"])),
            }
        )
    write_csv(path, rows)


def query_ids_by_subsection(query_results: dict[str, dict[str, object]]) -> dict[str, dict[str, set[str]]]:
    by_subsection: dict[str, dict[str, set[str]]] = {}
    for query_id, result in query_results.items():
        subsection_id = str(result["row"]["subsection_id"])
        for pmid in result["pmids"]:
            by_subsection.setdefault(subsection_id, {}).setdefault(str(pmid), set()).add(query_id)
    return by_subsection


def candidate_rows(
    query_results: dict[str, dict[str, object]], records_by_pmid: dict[str, dict[str, object]]
) -> list[dict[str, str]]:
    rows = []
    for subsection_id, pmid_map in query_ids_by_subsection(query_results).items():
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
    query_results: dict[str, dict[str, object]],
    records_by_pmid: dict[str, dict[str, object]],
) -> None:
    base_rows = candidate_rows(query_results, records_by_pmid)
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
        ],
    )


def write_recall_check(path: Path, records_by_pmid: dict[str, dict[str, object]]) -> None:
    existing = read_csv(path) if path.exists() else []
    seen_pmids = set(records_by_pmid)
    rows = []
    for row in existing:
        pmid = row.get("PMID", "").strip()
        found = bool(pmid and pmid in seen_pmids)
        rows.append(
            {
                **row,
                "found_in_final_set": "yes" if found else "no",
                "controller_decision": "recovered" if found else "recover_with_targeted_query",
                "notes": "Recovered in PubMed candidate set." if found else "Not recovered by current query set; needs targeted query or manual lookup.",
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
    query_results: dict[str, dict[str, object]],
    records_by_pmid: dict[str, dict[str, object]],
) -> None:
    rows = []
    for row in candidate_rows(query_results, records_by_pmid):
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
    query_results: dict[str, dict[str, object]],
    records_by_pmid: dict[str, dict[str, object]],
) -> None:
    rows = []
    for row in candidate_rows(query_results, records_by_pmid):
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
        counts = [int(query_results[qid]["raw_count"]) for qid in query_ids]
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
        status = subsection_controller_status(len(unique_pmids))
        rows.append(
            {
                "subsection_id": subsection_id,
                "queries_planned": str(len(query_ids)),
                "queries_run": str(len(query_ids)),
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
) -> None:
    by_sub: dict[str, list[str]] = {}
    for row in query_rows:
        by_sub.setdefault(row["subsection_id"], []).append(row["query_id"])
    lines = [
        "# PubMed Query Execution Report",
        "",
        "## Overall Status",
        "",
        "`pass`",
        "",
        "## Metadata Store",
        "",
        f"Collected `{unique_record_count}` unique PubMed records into `pubmed_records.jsonl` and SQLite `pubmed_records`.",
        "",
        "## Subsection Counts",
        "",
        "| subsection_id | queries_run | total_raw_hits | unique_candidates | controller_status |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    by_sub_candidates = query_ids_by_subsection(query_results)
    for subsection_id, query_ids in sorted(by_sub.items()):
        counts = [int(query_results[qid]["raw_count"]) for qid in query_ids]
        unique = len(by_sub_candidates.get(subsection_id, {}))
        status = subsection_controller_status(unique)
        lines.append(
            f"| {subsection_id} | {len(query_ids)} | {sum(counts)} | {unique} | {status} |"
        )
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "Run subsection abstract review on `abstract_triage_first_pass.csv`; broad or empty queries should be revised before treating any subsection as finalized.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_check(path: Path, unique_record_count: int) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else "# Subsection Retrieval Check\n"
    block = f"""

## PubMed Metadata Compliance

`pass`

Collected `{unique_record_count}` unique PubMed metadata records locally and
mirrored them into SQLite `pubmed_records`.

## Ready For Abstract Review

`yes`
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
                    "controller_to_assign" if raw_count == 0 or raw_count <= 5 or raw_count > 200 else "",
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
        for row in candidate_rows(query_results, {str(record["pmid"]): record for record in records}):
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

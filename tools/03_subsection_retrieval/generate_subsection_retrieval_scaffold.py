#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "00_workflow_control"))

from init_workflow_state import parse_draft, write_manifest


ARTIFACT_DIR = Path("artifacts/02_subsection_retrieval")
SCOPE_DIR = ARTIFACT_DIR / "01_scope"
QUERY_DIR = ARTIFACT_DIR / "02_queries"
PUBMED_DIR = ARTIFACT_DIR / "03_pubmed"
SCREENING_DIR = ARTIFACT_DIR / "04_screening"
RECALL_DIR = ARTIFACT_DIR / "05_recall"
OUTPUT_DIR = ARTIFACT_DIR / "06_outputs"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate subsection retrieval scaffold artifacts from an initial review draft."
    )
    parser.add_argument("run_dir", help="Path to runs/<run_id>.")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    draft_path = run_dir / "drafts" / "initial_review.md"
    if not draft_path.exists():
        print(f"ERROR: missing draft: {draft_path}", file=sys.stderr)
        return 1

    subsections = parse_draft(draft_path)
    if not subsections:
        print(f"ERROR: no subsections parsed from {draft_path}", file=sys.stderr)
        return 1

    artifact_dir = run_dir / ARTIFACT_DIR
    for directory in (SCOPE_DIR, QUERY_DIR, PUBMED_DIR, SCREENING_DIR, RECALL_DIR, OUTPUT_DIR):
        (run_dir / directory).mkdir(parents=True, exist_ok=True)

    write_folder_readme(artifact_dir / "README.md")
    write_manifest(run_dir, subsections)
    write_controller_policy(run_dir / QUERY_DIR / "controller_policy.md")
    write_abstract_review_rule(run_dir / QUERY_DIR / "abstract_review_rule.md")
    write_semantic_query_design_work_order(
        run_dir / QUERY_DIR / "semantic_query_design_work_order.md", subsections
    )
    write_query_plan(run_dir / QUERY_DIR / "query_plan.csv", subsections)
    write_query_diagnostics(run_dir / QUERY_DIR / "query_diagnostics.csv", subsections)
    write_search_iteration_log(run_dir / QUERY_DIR / "search_iteration_log.csv", subsections)
    write_subsection_metrics(run_dir / OUTPUT_DIR / "subsection_metrics.csv", subsections)
    write_abstract_triage_first_pass(
        run_dir / SCREENING_DIR / "abstract_triage_first_pass.csv", subsections
    )
    write_abstract_triage_rescue_pass(
        run_dir / SCREENING_DIR / "abstract_triage_rescue_pass.csv", subsections
    )
    write_draft_citation_recall_check(
        run_dir / RECALL_DIR / "draft_citation_recall_check.csv", subsections
    )
    write_final_literature_sets(run_dir / OUTPUT_DIR / "final_literature_sets.csv", subsections)
    write_full_text_download_queue(
        run_dir / OUTPUT_DIR / "full_text_download_queue.csv", subsections
    )
    write_subsection_retrieval_check(
        run_dir / OUTPUT_DIR / "subsection_retrieval_check.md", subsections
    )

    print(f"Generated subsection retrieval scaffold for {len(subsections)} subsections.")
    return 0


def write_folder_readme(path: Path) -> None:
    path.write_text(
        """# Subsection Retrieval Artifacts

Canonical state for this stage lives in `../00_workflow_control/01_state/workflow_state.sqlite`.
This folder is organized into compact human-facing exports and agent handoff
files.

- `01_scope/`: subsection manifest and scope mapping.
- `02_queries/`: query plan, diagnostics, controller policy, and iteration log.
- `03_pubmed/`: locally downloaded PubMed metadata exports.
- `04_screening/`: pre-review abstract-screening scaffolds.
- `05_recall/`: draft citation recall checks.
- `06_outputs/`: metrics, retained literature export, primary full-text target
  export, and validation report.
""",
        encoding="utf-8",
    )


def subsection_text(subsection: dict[str, object]) -> str:
    prose = " ".join(str(line) for line in subsection.get("prose_lines", []))
    citation_notes = " ".join(
        f"{citation.get('citation', '')} {citation.get('notes', '')}"
        for citation in subsection.get("citations", [])
    )
    # Title is context, but prose and citation notes are the primary query source.
    return f"{prose} {citation_notes} {subsection.get('subsection_title', '')}"


def content_terms(subsection: dict[str, object], limit: int = 12) -> list[str]:
    text = subsection_text(subsection)
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9+/.-]*", text)
    stop = {
        "and",
        "or",
        "as",
        "a",
        "an",
        "the",
        "to",
        "of",
        "in",
        "for",
        "with",
        "by",
        "from",
        "about",
        "after",
        "also",
        "another",
        "available",
        "because",
        "before",
        "between",
        "broad",
        "citation",
        "citations",
        "claim",
        "claims",
        "clinical",
        "context",
        "could",
        "detail",
        "details",
        "draft",
        "during",
        "evidence",
        "evidence-priority",
        "example",
        "explain",
        "final",
        "first",
        "full",
        "full-text",
        "full-text-needed",
        "important",
        "include",
        "including",
        "interpretation",
        "later",
        "likely",
        "mechanism",
        "mechanisms",
        "may",
        "might",
        "metadata",
        "needed",
        "paper",
        "papers",
        "pass",
        "primary",
        "review",
        "search",
        "section",
        "should",
        "source",
        "specific",
        "subsection",
        "support",
        "text",
        "targeted",
        "therefore",
        "these",
        "they",
        "this",
        "those",
        "through",
        "treatment",
        "unknown",
        "using",
        "verify",
        "verification",
        "workflow",
        "abstract-level",
        "clinical",
        "biological",
        "doi",
        "metadata",
        "needs",
        "rationale",
        "questions",
        "priorities",
        "future",
        "emerging",
        "emerging/preprint",
        "preprint",
        "preprints",
        "patient-derived",
        "investigational",
        "approved",
        "phase",
        "i",
        "i/ii",
        "ii",
        "ii/iii",
        "iii",
        "iv",
    }
    scores: dict[str, int] = {}
    canonical: dict[str, str] = {}
    for token in tokens:
        lowered = token.lower().strip(".")
        if lowered in stop or len(lowered) <= 2:
            continue
        if any(fragment in lowered for fragment in ("preprint", "emerging/")):
            continue
        if lowered.isdigit() and len(lowered) == 4 and 1900 <= int(lowered) <= 2100:
            continue
        score = 1
        if any(char.isdigit() for char in token):
            score += 4
        if any(char in token for char in "-+/"):
            score += 3
        if token.isupper() and len(token) >= 3:
            score += 4
        if token[:1].isupper():
            score += 1
        if lowered.endswith(("ase", "inib", "mab", "tion", "sion", "ance")):
            score += 1
        scores[lowered] = scores.get(lowered, 0) + score
        canonical.setdefault(lowered, token.strip("."))

    ranked = sorted(scores, key=lambda term: (-scores[term], term))
    return [canonical[term] for term in ranked[:limit]] or ["biomedical"]


def terms_matching(subsection: dict[str, object], patterns: tuple[str, ...], fallback: int) -> list[str]:
    terms = content_terms(subsection, limit=24)
    selected = [
        term
        for term in terms
        if any(pattern in term.lower() for pattern in patterns)
    ]
    return selected[:4] or terms[:fallback]


GENERIC_QUERY_TERMS = {
    "acquired",
    "adaptation",
    "alteration",
    "biomarker",
    "combination",
    "compensation",
    "escape",
    "inhibition",
    "loss",
    "model",
    "models",
    "mutation",
    "mutations",
    "patient",
    "patients",
    "pathway",
    "plasticity",
    "reactivation",
    "resistance",
    "secondary",
    "therapy",
    "trial",
    "trials",
}


def nongeneric_terms(terms: list[str]) -> list[str]:
    return [term for term in terms if term.lower().strip(".") not in GENERIC_QUERY_TERMS]


def mechanism_terms(subsection: dict[str, object], terms: list[str]) -> list[str]:
    matched = terms_matching(
        subsection,
        (
            "resistance",
            "acquired",
            "mutation",
            "loss",
            "bypass",
            "reactivation",
            "compensation",
            "escape",
            "inhibition",
            "adaptation",
            "plasticity",
        ),
        4,
    )
    return [term for term in matched if term in terms]


def quote_term(term: str) -> str:
    escaped = term.replace('"', "")
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


def high_precision_query(subsection: dict[str, object]) -> str:
    terms = content_terms(subsection, limit=12)
    entities = nongeneric_terms(entity_like_terms(terms))[:2]
    mechanisms = mechanism_terms(subsection, terms)[:3]
    specific = [term for term in nongeneric_terms(terms) if term not in entities and term not in mechanisms][:3]
    if entities and mechanisms:
        return and_join([or_group(entities), or_group(mechanisms), or_group(specific[:2])])
    if entities and specific:
        return and_join([or_group(entities), or_group(specific[:3])])
    return and_join([or_group(nongeneric_terms(terms[:5]))])


def mechanism_expansion_query(subsection: dict[str, object]) -> str:
    terms = content_terms(subsection, limit=16)
    entity_terms = nongeneric_terms(entity_like_terms(terms))[:3] or nongeneric_terms(terms)[:3]
    mechanisms = mechanism_terms(subsection, terms)[:4]
    supporting_terms = [
        term
        for term in nongeneric_terms(terms)
        if term not in entity_terms and term not in mechanisms
    ][:3]
    return and_join([or_group(entity_terms), or_group(mechanisms), or_group(supporting_terms)])


def context_expansion_query(subsection: dict[str, object]) -> str:
    terms = content_terms(subsection, limit=18)
    context = [
        term
        for term in terms
        if term.lower()
        in {"trial", "trials", "patient", "patients", "cohort", "model", "models", "biomarker", "assay", "therapy", "combination"}
        or term.lower().endswith(("inib", "mab"))
    ]
    selected = context[:2] + [term for term in terms if term not in context][:3]
    selected = list(dict.fromkeys(selected))[:5]
    context_block = or_group(context[:3])
    focus_terms = [
        term
        for term in nongeneric_terms(selected)
        if term not in context
    ][:3]
    entities = nongeneric_terms(entity_like_terms(terms))[:3]
    mechanisms = mechanism_terms(subsection, terms)[:2]
    if context_block:
        return and_join([context_block, or_group(entities or focus_terms), or_group(mechanisms or focus_terms)])
    non_entities = [
        term for term in nongeneric_terms(terms) if term not in entities
    ]
    return and_join([or_group(entities), or_group(mechanisms), or_group(non_entities[:3])])


def entity_like_terms(terms: list[str]) -> list[str]:
    return [
        term
        for term in terms
        if term.isupper()
        or any(char.isdigit() for char in term)
        or any(char in term for char in "-+/")
        or term.lower().endswith(("inib", "mab"))
    ]


def query_ids_for_subsection(subsection_id: str) -> list[str]:
    return [f"{subsection_id}-Q001"]


def recall_guard_query(subsection: dict[str, object]) -> str:
    citations = subsection["citations"]
    pmids = list(dict.fromkeys([
        citation["PMID"]
        for citation in citations
        if citation.get("PMID") and citation["PMID"] != "unknown"
    ]))
    if pmids:
        return " OR ".join(f"{pmid}[PMID]" for pmid in pmids)
    terms = content_terms(subsection, limit=12)
    entities = nongeneric_terms(entity_like_terms(terms))[:3]
    mechanisms = mechanism_terms(subsection, terms)[:3]
    non_entities = [
        term for term in nongeneric_terms(terms) if term not in entities and term not in mechanisms
    ]
    fallback = and_join([or_group(entities), or_group(mechanisms), or_group(non_entities[:3])])
    return fallback or high_precision_query(subsection)


def recall_targets(subsection: dict[str, object]) -> str:
    return ";".join(
        citation["citation_id"]
        for citation in subsection["citations"]
        if citation.get("citation") != "citation needed"
    )


def write_controller_policy(path: Path) -> None:
    path.write_text(
        """# Subsection Retrieval Controller Policy

## Purpose

The controller runs subsection-level PubMed retrieval loops from the initial
review draft. It accepts, revises, broadens, or narrows queries based on result
counts, sampled precision, noise classes, and draft-citation recall.

## Query Design And Count Heuristics

Each subsection should have one or two initial semantic PubMed queries. Use one
query when the subsection has a single coherent evidence target. Use two only
when the second query has a distinct scientific intent, such as mechanism plus
clinical context, primary mechanism plus citation recall, model/assay plus
therapy setting, or positive evidence plus negative/failed-result evidence.

Judge readiness at subsection level. The target candidate set is 10-300 unique
PubMed records per subsection.

- `0-9`: too few; broaden or replace the weakest unresolved leaf query.
- `10-300`: reviewable for semantic abstract review.
- `>300`: too many; tighten or replace the broadest contributing leaf query.

Diagnostic samples from overbroad queries are not retrieval coverage. They can
be used to diagnose noise and choose tighter keyword combinations, but they
must not be the only source passed into semantic abstract review.

Redesigned queries are not automatically executable keyword rewrites.
Query-level counts are diagnostics. When the subsection candidate set is too
sparse or too broad, the controller stages one redesign work order for the
weakest or broadest unresolved leaf query. An LLM query designer must
semantically read the subsection evidence need plus the count failure before
marking redesigned queries as executable.

Continue redesign loops without human review until the subsection candidate set
is 10-300 and all executable redesign rows have been run.

`subsection_metrics.csv` `controller_status` is the durable rollup: use
`query_revision_needed` when the subsection is outside 10-300 or has pending
redesign rows, and `abstract_review_needed` when candidates are ready for
semantic abstract review.

## Controller Actions

- `accept_for_abstract_review`
- `redesign_query_keywords`
- `diagnostic_only_subsection_covered`
- `recover_draft_citation`
- `finalize_subsection_set`

## Stop Rule

Finalize a subsection only after query iterations, abstract-review decisions,
draft-citation recall, and full-text routing are recorded. Placeholder or
`not_run` records are allowed only to show that the controller scaffold exists;
they do not establish that PubMed retrieval or abstract review is scientifically
complete. Any subsection outside the 10-300 candidate range must continue to a
semantic redesign row. The redesigned query must change the keyword strategy
through semantic LLM redesign, not merely raise collection limits or take a
larger subset from the original result count.
""",
        encoding="utf-8",
    )


def write_abstract_review_rule(path: Path) -> None:
    path.write_text(
        """# Abstract Review Rule

## Purpose

Abstract reviewers decide whether candidate papers belong in one specific
subsection-level literature set. They must judge against the subsection scope,
not against the whole review topic.

## Allowed Decisions

- `include_primary`
- `include_context`
- `exclude_off_scope`
- `exclude_wrong_level`
- `exclude_low_quality_or_blocked`
- `uncertain_full_text_needed`

## Required Reason

Each decision must include a one-sentence reason tied to the subsection scope.
The reviewer must compare the abstract directly with the subsection prose:
mechanism match, entity/context match, evidence directness, and whether the
abstract supports a smaller scientific claim inside the subsection.

## Two-Pass Rule

First-pass includes carry forward. The rescue pass reviews first-pass excludes
and uncertain papers to catch overly narrow early triage, recover draft anchors,
and preserve plausible decision-relevant evidence before full-text routing.
Keyword overlap alone is not enough for inclusion, but absence of an exact
entity name is not enough for exclusion when the abstract tests the same
mechanism, assay logic, resistance class, or model relationship.
""",
        encoding="utf-8",
    )


def write_semantic_query_design_work_order(path: Path, subsections: list[dict[str, object]]) -> None:
    lines = [
        "# Semantic Query Design Work Order",
        "",
        "Before PubMed execution, an LLM query designer must read each subsection",
        "context as an evidence need and rewrite `query_plan.csv` into executable",
        "semantic PubMed queries. The heuristic scaffold is only a seed.",
        "",
        "For each subsection, identify:",
        "",
        "- the claim or evidence need being searched;",
        "- primary entity/family terms and allowed synonyms;",
        "- mechanism, endpoint, assay, model, disease, or population terms;",
        "- likely false-positive meanings and exclusions;",
        "- query intents, choosing the number needed for the subsection complexity;",
        "- query intents such as primary mechanism, context/model, method/readout,",
        "  synonym/family analog, or citation recall only when scientifically needed.",
        "",
        "Replace each scaffolded `semantic_seed` row with real initial queries",
        "before PubMed execution. Narrow/simple subsections may use a small",
        "number of queries; complex subsections with multiple entities,",
        "mechanisms, models, interventions, or citation-recall needs may use",
        "more. Each initial query in a subsection must have a distinct",
        "`query_type` intent label.",
        "",
        "Set `semantic_query_design_status` to `llm_semantic_designed` only after",
        "the LLM has performed this reading and written the executable query.",
        "",
        "If PubMed execution later stages `query_redesign` rows, treat them as a",
        "second semantic design work order. The LLM must read the parent",
        "subsection, parent query, count status, diagnostic rationale, and false",
        "positive risks, then rewrite the row and set",
        "`semantic_query_design_status=llm_semantic_redesigned` before execution.",
        "",
        "## Subsections",
        "",
    ]
    for subsection in subsections:
        sid = str(subsection["subsection_id"])
        lines.extend(
            [
                f"### {sid}: {subsection.get('subsection_title', '')}",
                "",
                "Draft prose:",
                "",
                " ".join(str(line) for line in subsection.get("prose_lines", [])),
                "",
                "Citation/search notes:",
                "",
            ]
        )
        for citation in subsection.get("citations", []):
            lines.append(
                f"- {citation.get('citation_id', '')}: {citation.get('citation', '')}; "
                f"PMID={citation.get('PMID', '')}; DOI={citation.get('DOI', '')}; "
                f"notes={citation.get('notes', '')}"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_query_plan(path: Path, subsections: list[dict[str, object]]) -> None:
    rows = []
    for subsection in subsections:
        sid = str(subsection["subsection_id"])
        terms = content_terms(subsection, limit=12)
        rows.append(
            {
                "subsection_id": sid,
                "query_id": f"{sid}-Q001",
                "query_type": "semantic_seed",
                "pubmed_query": high_precision_query(subsection),
                "required_terms": ";".join(terms[:4]),
                "optional_terms": ";".join(terms[4:]),
                "excluded_terms": "",
                "expected_result_band": "subsection target 10-300 unique candidates",
                "recall_targets": recall_targets(subsection),
                "semantic_evidence_need": "needs_llm_semantic_design",
                "semantic_entity_terms": "needs_llm_semantic_design",
                "semantic_mechanism_terms": "needs_llm_semantic_design",
                "semantic_endpoint_or_context_terms": "needs_llm_semantic_design",
                "query_false_positive_risks": "needs_llm_semantic_design",
                "semantic_query_design_status": "needs_llm_semantic_design",
                "semantic_query_designer": "unassigned",
                "redesign_parent_query_id": "",
                "redesign_trigger_count_status": "",
                "redesign_trigger_raw_hit_count": "",
                "redesign_semantic_work_order": "",
                "query_rationale": "Heuristic seed only; LLM must semantically redesign or approve before PubMed execution.",
            }
        )
    write_csv(path, rows)


def write_query_diagnostics(path: Path, subsections: list[dict[str, object]]) -> None:
    rows = []
    for subsection in subsections:
        sid = str(subsection["subsection_id"])
        for query_id in query_ids_for_subsection(sid):
            rows.append(
                {
                    "subsection_id": sid,
                    "query_id": query_id,
                    "query": high_precision_query(subsection),
                    "raw_hit_count": "unknown",
                    "collected_count": "unknown",
                    "truncated_by_constraint": "false",
                    "sample_size": "unknown",
                    "sample_strategy": "not_sampled",
                    "sampled_on_scope_count": "unknown",
                    "sampled_noise_count": "unknown",
                    "estimated_precision": "unknown",
                    "dominant_noise_classes": "unknown",
                    "missing_concepts": "unknown",
                    "recall_signals": "unknown",
                    "decision": "not_run",
                    "revision_rationale": "Await PubMed execution and controller review.",
                }
            )
    write_csv(path, rows)


def write_search_iteration_log(path: Path, subsections: list[dict[str, object]]) -> None:
    rows = []
    for subsection in subsections:
        sid = str(subsection["subsection_id"])
        for query_id in query_ids_for_subsection(sid):
            rows.append(
                {
                    "subsection_id": sid,
                    "query_id": query_id,
                    "iteration": "1",
                    "run_status": "not_run",
                    "result_count": "unknown",
                    "count_status": "not_run",
                    "controller_action": "run_query_or_estimate_count",
                    "next_query_id": "unknown",
                    "notes": "Initial scaffold row; execute PubMed query next.",
                }
            )
    write_csv(path, rows)


def write_subsection_metrics(path: Path, subsections: list[dict[str, object]]) -> None:
    rows = []
    for subsection in subsections:
        sid = str(subsection["subsection_id"])
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
        rows.append(
            {
                "subsection_id": sid,
                "queries_planned": "1",
                "queries_run": "0",
                "total_pubmed_returned": "unknown",
                "total_collected_for_review": "unknown",
                "draft_known_citation_count": str(known_count),
                "draft_citations_recovered": "unknown",
                "draft_citation_recall_rate": "unknown",
                "abstracts_reviewed": "0",
                "abstract_include_primary_count": "0",
                "abstract_include_context_count": "0",
                "abstract_uncertain_full_text_needed_count": "0",
                "abstract_rejected_count": "0",
                "abstract_rejection_rate": "unknown",
                "rescue_reviewed": "0",
                "rescue_promoted_count": "0",
                "final_literature_set_count": "0",
                "full_text_download_queue_count": str(full_text_needed_count),
                "controller_status": "not_run",
                "notes": "Metrics initialized; replace unknowns after PubMed execution and abstract triage.",
            }
        )
    write_csv(path, rows)


def known_citation_rows(subsections: list[dict[str, object]]) -> list[dict[str, str]]:
    rows = []
    for subsection in subsections:
        sid = str(subsection["subsection_id"])
        for citation in subsection["citations"]:
            if citation["citation"] == "citation needed":
                continue
            rows.append(
                {
                    "subsection_id": sid,
                    "citation": citation["citation"],
                    "PMID": citation["PMID"],
                    "DOI": citation["DOI"],
                    "evidence_role": citation["evidence_role"],
                    "draft_access_status": citation["draft_access_status"],
                    "venue_trust_label": citation["venue_trust_label"],
                    "source_query_ids": f"{sid}-Q001",
                    "reason": "Known draft citation carried into subsection retrieval scaffold.",
                }
            )
    return rows


def write_abstract_triage_first_pass(path: Path, subsections: list[dict[str, object]]) -> None:
    rows = []
    counter = 1
    for row in known_citation_rows(subsections):
        rows.append(
            {
                "subsection_id": row["subsection_id"],
                "paper_id": paper_id(row["PMID"], counter),
                "PMID": row["PMID"],
                "DOI": row["DOI"],
                "title": row["citation"],
                "abstract": "not_collected",
                "publication_types": "unknown",
                "year": "unknown",
                "source_query_ids": row["source_query_ids"],
                "first_pass_decision": "not_reviewed",
                "first_pass_rationale": "Await abstract collection before triage.",
                "first_pass_confidence": "unknown",
                "topic_match_type": "unknown",
                "semantic_fit_score": "unknown",
                "mechanism_match": "unknown",
                "entity_context_match": "unknown",
                "evidence_directness": "unknown",
                "key_relevant_abstract_text": "not_reviewed",
                "missing_full_text_reason": "unknown",
                "triage_actor": "not_started",
                "synthesis_role": row["evidence_role"],
                "prescreen_hint": "draft_anchor",
                "prescreen_rationale": "Present in draft citation register.",
                "prescreen_overlap_terms": "unknown",
            }
        )
        counter += 1
    write_csv(path, rows)


def write_abstract_triage_rescue_pass(path: Path, subsections: list[dict[str, object]]) -> None:
    rows = []
    counter = 1
    for row in known_citation_rows(subsections):
        rows.append(
            {
                "subsection_id": row["subsection_id"],
                "paper_id": paper_id(row["PMID"], counter),
                "PMID": row["PMID"],
                "DOI": row["DOI"],
                "title": row["citation"],
                "abstract": "not_collected",
                "publication_types": "unknown",
                "year": "unknown",
                "source_query_ids": row["source_query_ids"],
                "first_pass_decision": "not_reviewed",
                "first_pass_rationale": "Await abstract collection before first-pass triage.",
                "rescue_pass_decision": "not_reviewed",
                "rescue_pass_rationale": "Rescue pass not eligible until first-pass excludes exist.",
                "rescue_pass_confidence": "unknown",
                "semantic_fit_score": "unknown",
                "mechanism_match": "unknown",
                "entity_context_match": "unknown",
                "evidence_directness": "unknown",
                "key_relevant_abstract_text": "not_reviewed",
                "missing_full_text_reason": "unknown",
                "promotion_decision": "not_promoted",
                "synthesis_role": row["evidence_role"],
            }
        )
        counter += 1
    write_csv(path, rows)


def write_draft_citation_recall_check(path: Path, subsections: list[dict[str, object]]) -> None:
    rows = []
    for subsection in subsections:
        sid = str(subsection["subsection_id"])
        for citation in subsection["citations"]:
            if citation["citation"] == "citation needed":
                continue
            rows.append(
                {
                    "subsection_id": sid,
                    "citation_id": citation["citation_id"],
                    "citation": citation["citation"],
                    "PMID": citation["PMID"],
                    "DOI": citation["DOI"],
                    "discovery_provenance": citation["discovery_provenance"],
                    "found_in_final_set": "pending",
                    "controller_decision": "recover_with_targeted_query",
                    "notes": "Recall check scaffolded; final status requires PubMed execution.",
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
    write_csv(path, rows)


def write_final_literature_sets(path: Path, subsections: list[dict[str, object]]) -> None:
    rows = []
    counter = 1
    for row in known_citation_rows(subsections):
        rows.append(
            {
                "subsection_id": row["subsection_id"],
                "paper_id": paper_id(row["PMID"], counter),
                "PMID": row["PMID"],
                "PMCID": "unknown",
                "DOI": row["DOI"],
                "title": row["citation"],
                "journal": "unknown",
                "publication_year": "unknown",
                "article_type": "unknown",
                "abstract_review_decision": "not_reviewed",
                "evidence_role": row["evidence_role"],
                "draft_access_status": row["draft_access_status"],
                "verified_access_status": "unknown",
                "venue_trust_label": row["venue_trust_label"],
                "source_query_ids": row["source_query_ids"],
                "reason": row["reason"],
            }
        )
        counter += 1
    write_csv(path, rows)


def write_full_text_download_queue(path: Path, subsections: list[dict[str, object]]) -> None:
    rows = []
    counter = 1
    for subsection in subsections:
        sid = str(subsection["subsection_id"])
        for citation in subsection["citations"]:
            if citation["draft_access_status"] != "full_text_needed_for_verification":
                continue
            rows.append(
                {
                    "subsection_id": sid,
                    "paper_id": paper_id(citation["PMID"], counter),
                    "PMID": citation["PMID"],
                    "PMCID": "unknown",
                    "DOI": citation["DOI"],
                    "title": citation["citation"],
                    "why_full_text_needed": citation["notes"],
                    "download_priority": "high",
                    "user_action": "user_download_pdf_or_agent_find_pmc",
                }
            )
            counter += 1
    if not rows:
        rows.append(
            {
                "subsection_id": "none",
                "paper_id": "none",
                "PMID": "unknown",
                "PMCID": "unknown",
                "DOI": "unknown",
                "title": "none",
                "why_full_text_needed": "No full-text-needed draft rows found yet.",
                "download_priority": "unknown",
                "user_action": "none",
            }
        )
    write_csv(path, rows)


def write_subsection_retrieval_check(path: Path, subsections: list[dict[str, object]]) -> None:
    path.write_text(
        f"""# Subsection Retrieval Check

## Overall Status

`pass`

## Subsection Coverage

The scaffold covers {len(subsections)} draft subsections parsed from
`drafts/initial_review.md`.

## Query Plan Compliance

Each subsection has one heuristic `semantic_seed` placeholder row. The LLM query
designer must replace that placeholder with one or two real initial semantic
query intents before PubMed execution. Use a second query only when it adds a
distinct scientific retrieval intent. Initial query intent labels must be
distinct within each subsection.

## Abstract Review Rule Compliance

`abstract_review_rule.md` defines allowed first-pass and rescue-pass decisions.

## Search Iteration Compliance

`search_iteration_log.csv` contains initial controller rows with `not_run`
status. This records the next action without pretending PubMed has already been
queried.

## Subsection Metrics Compliance

`subsection_metrics.csv` contains one row per subsection with query counts,
PubMed-returned counts, recall-rate fields, abstract-review counts, rejection
counts, rescue counts, final-set counts, full-text queue counts, and controller
status. Unknown values are explicit until PubMed execution and abstract triage
are performed.

## Draft Citation Recall Compliance

Known draft citations were copied into the recall-check scaffold. Final recall
status is pending PubMed execution and abstract collection.

## Final Literature Set Compliance

`final_literature_sets.csv` contains draft-anchor rows marked `not_reviewed`.
The file is structurally ready for abstract-review decisions, but its scientific
contents are not final.

## Full-Text Download Queue Compliance

`full_text_download_queue.csv` contains rows for draft citations that already
requested full-text verification.

## Issues To Fix

PubMed query execution, result counts, abstract collection, first-pass triage,
rescue triage, and verified full-text routing remain to be completed.

## Ready For PubMed Execution

`yes`
""",
        encoding="utf-8",
    )


def paper_id(pmid: str, counter: int) -> str:
    if pmid and pmid != "unknown":
        return f"PMID-{pmid}"
    return f"DRAFT-CITATION-{counter:04d}"


EMPTY_CSV_HEADERS = {
    "abstract_triage_first_pass.csv": [
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
    "abstract_triage_rescue_pass.csv": [
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
    "draft_citation_recall_check.csv": [
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
    "final_literature_sets.csv": [
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
}


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = list(rows[0]) if rows else EMPTY_CSV_HEADERS.get(path.name)
    if not fieldnames:
        raise ValueError(f"no rows or known header for {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())

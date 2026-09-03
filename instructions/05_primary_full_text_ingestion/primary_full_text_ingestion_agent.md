# Primary Full-Text Ingestion Agent Instructions

Use this instruction for Stage 5 of a run after semantic abstract review has
completed.

## Purpose

Build the first full-text corpus for globally primary papers only. The corpus is
for later vector search, evidence packet construction, and claim verification.
Do not ingest context, uncertain, excluded, or hard-blocked papers in this stage
unless the user explicitly requests a separate expansion.

## Preflight

Run:

```bash
python3 tools/00_workflow_control/validate_step.py semantic_abstract_review_complete runs/<run_id>
```

Do not proceed if semantic abstract review is incomplete, if any subsection
batch still needs review, or if `paper_review_rollup` has not been populated in
SQLite.

## Target Source

Read targets from SQLite, not from raw PubMed CSVs:

- `paper_review_rollup.global_review_status = globally_included_primary`
- or `paper_review_rollup.full_text_ingestion_route = primary_full_text_candidate`

The Stage 4 file
`artifacts/02_subsection_retrieval/06_outputs/full_text_download_queue.csv` is a
primary-cohort handoff, not proof that full text is available.

## Accepted Formats

Store and normalize only:

- PMC XML
- PDF

Do not store HTML full text, publisher landing pages, screenshots, citation
manager exports, or generic web captures as full-text corpus artifacts.

## Automated Retrieval Order

For each primary paper:

1. Try PMC XML from NCBI by PMCID.
2. Try Europe PMC XML by PMCID.
3. If PMC XML is missing or not usable, search for open PDFs through Europe PMC,
   OpenAlex, Semantic Scholar, and CORE when `CORE_API_KEY` is available.
4. Stage downloaded PDFs under
   `artifacts/04_primary_full_text_ingestion/04_pdf/01_staged/`.
5. Parse PDFs through the workflow's canonical GROBID TEI route: call
   `/api/processFulltextDocument`, cache the returned TEI XML, normalize body
   text and sections from that TEI, and derive chunks from those normalized TEI
   sections/body text.

PMC XML is usable only if it yields a meaningful body text. PMCID presence alone
is not enough.

## Normalization Rules

Normalize PMC XML and GROBID TEI into JSON with:

- `paper_id`
- `pmid`
- `pmcid`
- `doi`
- `title`
- `source_format`
- `source_path`
- `raw_text`
- `narrative_text`
- `narrative_policy`
- `sections`
- `chunk_policy`
- `chunks`
- `excluded_sections`

The normalized JSON must preserve unfiltered parser `raw_text` for audit, but
`sections`, `narrative_text`, and `chunks` must contain only the narrative core
used for downstream RAG. Preserve abstract text, introduction-like narrative,
result-bearing sections/subsections, and discussion/conclusion synthesis. Remove
methods, references, acknowledgements, affiliations, figure legends, tables,
supplementary/end matter, procedural sections, and metadata-heavy sections.
When uncertain, keep ambiguous scientific narrative unless it is clearly methods
or end matter; over-filtering is the larger risk.

Also write `narrative_qc_report.csv` after normalization. Use it as a triage
queue for possible over-filtering, not as an automatic failure list. Flag papers
with low narrative/raw retention, low absolute narrative characters, very few
kept sections/chunks, or a large excluded fraction. For flagged papers, a later
agent may inspect the raw source and either confirm the filter, improve a generic
rule, or create a paper-specific manual narrative extraction override.

The normalized narrative text must be long enough for downstream verification.
If body text is missing or too short, treat that source as unusable and try PDF.
For PDF-derived JSON, `source_path` must point to the cached GROBID TEI file,
not to a direct PDF text extraction output. Do not use `pypdf`, `pdfplumber`,
OCR, or browser/PDF viewer text as a fallback parser for Stage 5 normalization.
Those tools may not satisfy the workflow contract.

Use the same retrieval-oriented chunking policy for PMC XML and GROBID PDF
normalizations:

- `chunk_policy.name = structure_aware_1000_150`
- `chunk_size_chars = 1000`
- `chunk_overlap_chars = 150`
- Preserve section and paragraph boundaries when possible.
- If a whole section fits under the target size, keep it as one chunk.
- Otherwise keep each paragraph as one chunk when it fits.
- Use sentence-aware overlap only when a single paragraph is too large and must
  be split.

## Manual PDF Gate

If automated PMC/PDF ingestion cannot normalize all primary papers, write:

- `artifacts/04_primary_full_text_ingestion/05_user_pdf_request/manual_pdf_queue.csv`
- `artifacts/04_primary_full_text_ingestion/05_user_pdf_request/user_pdf_pause.md`
- `artifacts/04_primary_full_text_ingestion/05_user_pdf_request/01_user_pdf_dropbox/`

Then stop with the Stage 5 status `blocked_user_pdf_required` unless the user
has explicitly chosen to continue without unresolved PDFs.

If the user provides PDFs, help place them in the dropbox or pass their folder
with:

```bash
python3 tools/05_primary_full_text_ingestion/primary_full_text_ingestion.py runs/<run_id> --user-pdf-dropbox <folder>
```

Parse and normalize those PDFs immediately. After ingestion, ask for a clear
user signal before moving to vector database construction or claim extraction.

If the user explicitly chooses to continue without unresolved PDFs, run:

```bash
python3 tools/05_primary_full_text_ingestion/primary_full_text_ingestion.py runs/<run_id> --continue-without-user-pdfs
```

This records `complete_with_deferred_user_pdfs`; downstream steps must carry
the missing-full-text limitation.

## Required Outputs

- `artifacts/04_primary_full_text_ingestion/01_targets/primary_fulltext_targets.csv`
- `artifacts/04_primary_full_text_ingestion/02_discovery/fulltext_source_candidates.csv`
- `artifacts/04_primary_full_text_ingestion/03_pmc/01_raw_xml/`
- `artifacts/04_primary_full_text_ingestion/03_pmc/02_normalized/`
- `artifacts/04_primary_full_text_ingestion/04_pdf/01_staged/`
- `artifacts/04_primary_full_text_ingestion/04_pdf/02_parser_cache/01_grobid/`
- `artifacts/04_primary_full_text_ingestion/04_pdf/03_normalized/`
- `artifacts/04_primary_full_text_ingestion/05_user_pdf_request/manual_pdf_queue.csv`
- `artifacts/04_primary_full_text_ingestion/05_user_pdf_request/user_pdf_pause.md`
- `artifacts/04_primary_full_text_ingestion/05_user_pdf_request/01_user_pdf_dropbox/`
- `artifacts/04_primary_full_text_ingestion/06_outputs/import_status.csv`
- `artifacts/04_primary_full_text_ingestion/06_outputs/pdf_parse_report.csv`
- `artifacts/04_primary_full_text_ingestion/06_outputs/narrative_qc_report.csv`
- `artifacts/04_primary_full_text_ingestion/06_outputs/ingestion_summary.md`

The same records must be mirrored into SQLite tables:

- `full_text_ingestion`
- `full_text_source_candidates`
- `workflow_steps`

`manual_pdf_queue.csv` is a user-action queue. It must be deduplicated by
stable paper identity and exact normalized title groups. If multiple unresolved
paper records share the same title, emit one queue row with `linked_paper_ids`,
`linked_pmids`, `linked_dois`, and `duplicate_group_size` populated, while
preserving each individual paper row in SQLite and `import_status.csv`.

## Validation

Run:

```bash
python3 tools/00_workflow_control/validate_step.py primary_full_text_ingestion runs/<run_id>
```

The validation may pass while Stage 5 is deliberately blocked for user PDFs.
That means the queue and pause instruction are well formed. Do not proceed to
later stages until the user provides PDFs or explicitly chooses to continue
without them.

## Do Not Create

Do not create claim manifests, evidence packets, vector databases, rewritten
sections, final reviews, slide decks, or manuscript files in Stage 5.

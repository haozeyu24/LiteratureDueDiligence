# PubMed Query Execution Report

## Overall Status

`pass`

## Metadata Store

Collected `542` unique PubMed records into `pubmed_records.jsonl` and SQLite `pubmed_records`.
Executed `12` query rows in this pass and preserved prior counted rows.

## Subsection Counts

| subsection_id | queries_run | total_raw_hits | unique_candidates | controller_status |
| --- | ---: | ---: | ---: | --- |
| SUB001 | 1 | 283 | 199 | abstract_review_needed |
| SUB002 | 1 | 243 | 199 | abstract_review_needed |
| SUB003 | 1 | 51 | 50 | abstract_review_needed |
| SUB004 | 1 | 25 | 25 | abstract_review_needed |
| SUB005 | 1 | 35 | 35 | abstract_review_needed |
| SUB006 | 1 | 140 | 139 | abstract_review_needed |
| SUB007 | 1 | 130 | 130 | abstract_review_needed |
| SUB008 | 1 | 113 | 113 | abstract_review_needed |
| SUB009 | 1 | 144 | 141 | abstract_review_needed |
| SUB010 | 1 | 53 | 53 | abstract_review_needed |
| SUB011 | 1 | 293 | 199 | abstract_review_needed |
| SUB012 | 1 | 235 | 199 | abstract_review_needed |

## Next Step

Run subsection abstract review on `abstract_triage_first_pass.csv`; broad or empty queries should be revised before treating any subsection as finalized.

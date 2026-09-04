# Subsection RAG Retrieval Artifacts

This stage retrieves from the Stage 6 full-text RAG index for every draft subsection, fuses BM25 and semantic hits, aggregates chunks to paper-level rankings, and writes paper packets for downstream rewriting.

- `01_queries/`: subsection retrieval queries derived from subsection content.
- `02_chunk_hits/`: fused chunk-level retrieval hits.
- `03_paper_ranking/`: paper-level rankings after chunk aggregation.
- `04_paper_packets/`: one evidence packet per subsection.
- `05_outputs/`: compact retrieval summary.

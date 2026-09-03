# Full-Text RAG Index Summary

## Overall Status

`complete`

## Counts

- papers indexed: `71`
- chunks indexed: `2862`
- PMC XML chunks: `1829`
- PDF/GROBID chunks: `1033`
- chunk policy: `structure_aware_1000_150`
- chunk chars min/mean/max: `75` / `708.5` / `1001`

## Indexes

- BM25 lexical index: `complete`
- semantic vector index: `complete`
- embedding model: `text-embedding-3-small`

## Downstream Use

Retrieval should rank chunks first, aggregate scores to papers, select paper-level
evidence packets for each subsection, and rewrite from paper packets rather than
isolated chunks.

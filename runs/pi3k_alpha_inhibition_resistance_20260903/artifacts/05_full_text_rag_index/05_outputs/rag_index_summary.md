# Full-Text RAG Index Summary

## Overall Status

`complete`

## Counts

- papers indexed: `104`
- chunks indexed: `4073`
- PMC XML chunks: `3820`
- PDF/GROBID chunks: `253`
- chunk policy: `structure_aware_1000_150`
- chunk chars min/mean/max: `57` / `705.3` / `1011`

## Indexes

- BM25 lexical index: `complete`
- semantic vector index: `complete`
- embedding model: `text-embedding-3-small`

## Downstream Use

Retrieval should rank chunks first, aggregate scores to papers, select paper-level
evidence packets for each subsection, and rewrite from paper packets rather than
isolated chunks.

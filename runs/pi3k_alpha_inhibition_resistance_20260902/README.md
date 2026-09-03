# PI3K Alpha Inhibition Resistance Example Run

This run is included as a visible example of the workflow audit trail and final
review outputs.

Large or access-sensitive generated artifacts are intentionally not committed:

- local SQLite workflow state
- bulk PubMed JSONL/abstract screening exports
- raw PMC XML
- staged user PDFs
- GROBID TEI parser cache
- normalized full-text JSON
- chunk JSONL, BM25 pickle, and Qdrant vector storage

The committed files preserve the review drafts, structured inputs, run log,
controller decisions, summaries, metrics, citation lists, and final review.

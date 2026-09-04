# Primary Full-Text Ingestion Artifacts

This folder stores Stage 5 artifacts for globally primary papers only.

- `01_targets/`: deduplicated primary-paper target list from SQLite.
- `02_discovery/`: candidate PMC XML and open PDF source URLs.
- `03_pmc/`: raw PMC XML and normalized PMC JSON.
- `04_pdf/`: staged PDFs, GROBID TEI cache, and normalized PDF JSON.
- `05_user_pdf_request/`: manual PDF queue, pause notice, and user PDF dropbox.
- `06_outputs/`: import status, PDF parse report, and ingestion summary.

Only two full-text source formats are stored by this stage: PMC XML and PDF.
All normalized full text is emitted as JSON with `raw_text` and `sections`.

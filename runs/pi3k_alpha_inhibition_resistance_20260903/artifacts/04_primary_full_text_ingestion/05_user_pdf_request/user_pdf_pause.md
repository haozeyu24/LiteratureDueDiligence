# User PDF Pause

Stage 5 status: `complete_with_deferred_user_pdfs`

40 primary papers still need user-provided PDF full text or an explicit decision to continue without them.

To provide PDFs, place them in:

`runs/pi3k_alpha_inhibition_resistance_20260903/artifacts/04_primary_full_text_ingestion/05_user_pdf_request/01_user_pdf_dropbox`

Use filenames containing the expected filename, PMID, PMCID, DOI, or paper_id. Then rerun:

```bash
python3 tools/05_primary_full_text_ingestion/primary_full_text_ingestion.py runs/pi3k_alpha_inhibition_resistance_20260903
```

To continue without unresolved PDFs, rerun with:

```bash
python3 tools/05_primary_full_text_ingestion/primary_full_text_ingestion.py runs/pi3k_alpha_inhibition_resistance_20260903 --continue-without-user-pdfs
```

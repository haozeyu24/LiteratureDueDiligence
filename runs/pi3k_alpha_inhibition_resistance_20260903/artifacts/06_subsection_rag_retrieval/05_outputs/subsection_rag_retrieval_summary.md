# Subsection RAG Retrieval Summary

## Overall Status

`complete`

## Counts

- subsections queried: `12`
- paper packets written: `12`
- chunk hits recorded: `1620`
- paper rankings recorded: `587`
- selected subsection-paper pairs: `196`
- Stage 4 primary force-included pairs: `58`
- Stage 4 primary no-query-hit recall-added pairs: `18`
- target papers per subsection: `10`
- lexical limit per subsection: `80`
- semantic limit per subsection: `80`
- chunks per selected paper: `3`

## Retrieval Method

Queries are derived primarily from full draft subsection prose, then augmented
with draft citation clues and subsection titles. Stage 7 retrieves BM25 and
Qdrant semantic chunk hits, fuses them with reciprocal-rank fusion, aggregates
chunk evidence to paper-level rankings, and writes one paper packet per
subsection.

Stage 4 `primary_for_subsection` papers are force-included in their subsection
packet whenever they are present in the paper ranking, even if their hybrid rank
falls below the default top-paper cutoff. This preserves abstract-review primary
recall while still exposing RAG rank for rewrite triage.

## Recall Against Stage 4 Primary Cohort

- ranked Stage 4 primary PMIDs: `104`
- selected Stage 4 primary PMIDs: `104`
- Stage 4 primary recall within Stage 7 packets: `100.0%`

## Downstream Use

Stage 8 should rewrite subsections from these paper packets, not from raw chunk
lists alone.

# Changelog

All notable changes, tracked by CalVer date tags.

## Unreleased

## v2026.6.2

First CalVer snapshot. memex-kb is a mixed document-workflow toolkit
(ingestion, conversion, proposal authoring, publishing templates).

### Features

- **MinerU → org → EPUB pipeline**: `scripts/mineru2org.py` post-processes
  MinerU VLM markdown into clean Org — heading-hierarchy reconstruction,
  footnote ref/definition linking (from `content_list.json`), image and
  LaTeX-equation links, HTML-residue cleanup (`<details>`/`<table>`/mermaid).
  Book config under `scripts/corrections/*.json` drives corrections, structure,
  and EPUB metadata. Validated end-to-end (epubcheck 0 errors).
- **MinerU VLM client**: reproducible thin client (`mineru-client/`, `run.sh
  mineru-setup`/`mineru-parse`) talking to a remote vLLM MinerU server.
- **diff-review QA**: engine-agnostic conflict extractor (`scripts/diff_review.py`,
  `run.sh diff-review`) for comparing two transcriptions.
- **scanpdf2org**: scanned PDF → page render → vision transcription → Org.
- **org → EPUB**: `run.sh org2epub-build` thin wrapper over the local ox-epub fork.
- **Proposal pipeline**: Google Docs → Markdown → Org → ODT/DOC deliverables.
- **Publishing templates**: Org→ACM paper PDF, Quarto/Reveal.js slides,
  Org→PPTX injection (`org2pptx`).
- **Backends**: Google Docs export, Threads archive, Confluence cleanup,
  GitHub Stars → BibTeX, Naver Blog crawler.

### Changed

- Retired the marker (surya OCR) engine — MinerU VLM wins on speed and accuracy.
  `diff_review.py` preserved into `scripts/`; `run.sh` rewired to `diff-review`.
- EPUB export delegates fully to the ox-epub fork (no in-repo post-processing stack).

# memex-kb

A document conversion and publishing toolkit for an org-centric knowledge workflow.

**memex-kb** started as a Google Docs → Denote knowledge base converter and has grown into a broader toolbox for turning legacy or platform-bound content into plain-text, version-controlled, and AI-friendly formats.

Today the repository combines three layers:

1. **Knowledge ingestion** — Google Docs, Threads, Confluence, GitHub Stars, and blog exports
2. **Structured document pipelines** — proposal workflows, Org/ODT/HWP-oriented transformations
3. **Reusable publishing templates** — paper, presentation, and PowerPoint template injection workflows

The guiding idea is simple:

> Legacy content → structured text → reproducible artifacts → human + AI collaboration

---

## What this repository is for

memex-kb is useful when you want to:

- convert documents into **Markdown**, **Org-mode**, **BibTeX**, **ODT**, **DOC**, **PDF**, or **PPTX-adjacent workflows**
- preserve structure well enough for **search**, **versioning**, and **AI-assisted editing**
- standardize output with **Denote-style naming**, **rule-based classification**, and **template-driven publishing**
- keep the whole workflow reproducible with **Nix Flakes** and CLI-first tooling

---

## Current capabilities

### Ingestion / conversion backends

| Backend / Source | Status | Main entry point | Output |
|---|---|---|---|
| Google Docs | Stable | `scripts/gdocs_md_processor.py`, `./run.sh gdocs-export` | Markdown, DOCX, PDF, HTML, TXT |
| Threads | Stable | `scripts/threads_exporter.py`, `./run.sh threads-export` | Org-mode + images |
| Confluence export (`.doc` MIME HTML) | Stable | `scripts/confluence_to_markdown.py` | Clean Markdown |
| GitHub Stars | Stable | `scripts/gh_starred_to_bib.sh`, `./run.sh github-starred-export` | BibTeX |
| Naver Blog | Active | `scripts/naver_blog_crawler.py`, `./run.sh naver-*` | Denote-style Org + assets |
| Anthropic Distill HTML papers | Active | `scripts/anthropic_paper_to_org.py`, `./run.sh paper2org` | Org (math/figure/citation-aware, HTML round-trippable) |
| HWPX / OWPML related workflows | Active | `hwpx2org/`, `orgadoc2odt/`, `proposal-pipeline/` | Org, ODT, DOC, HWP-oriented outputs |

### Publishing / template workflows

| Template / Pipeline | Purpose |
|---|---|
| `templates/arxiv-acm/` | Org-mode → ACM `acmart` → PDF / ArXiv-ready source workflow |
| `templates/presentation/` | Quarto / Reveal.js HTML presentation template |
| `templates/presentation-pptx/` | **org2pptx**: inject Org-mode content into an existing PPTX template while preserving layout/design |
| `proposal-pipeline/` | Google Docs → Markdown → Org-mode → ODT/DOC proposal workflow |
| `.claude/skills/syndicate/` + `scripts/syndicate.py` / `./run.sh syndicate` | **ROSSE syndication** (issue #4): one garden canonical note → one copy-paste bundle per surface (raw / full / summary classes) for Facebook, LinkedIn, Naver Blog, Tistory, Threads, X, Bluesky, Instagram. Copy-paste / browser-Claude first, not full API automation |
| `.claude/skills/scanbook/` | Repo-local operating manual for scanned-book work. New agents should read this first for MinerU server checks, per-book config, correction strategy, and EPUB gotchas |
| `./run.sh mineru-setup` / `mineru-parse` | Scanned PDF → MinerU VLM Markdown + `content_list.json` + images, using the remote gpu2i vLLM server through an SSH tunnel |
| `scripts/mineru2org.py` + `scripts/corrections/*.json` | MinerU Markdown → clean Org: structure recovery, footnotes, images, LaTeX, EPUB metadata, and book-specific corrections |
| `./run.sh diff-review` | Engine-agnostic QA helper for comparing two transcriptions and surfacing only conflicts |
| `./run.sh org2epub-build` | Org → clean **EPUB 3.0** using the maintained local `~/repos/gh/ox-epub` fork directly; supports images, LaTeX→SVG math, tables, footnotes, TOC, Korean, and `epubcheck` validation |
| `scanpdf2org/` | Older page-render + vision-transcription surface; kept as a fallback/oracle path, not the primary scanned-book pipeline |

---

## Repository structure

```text
memex-kb/
├── README.md
├── AGENTS.md
├── BACKENDS.md
├── DEVELOPMENT.md
├── DENOTE-RULES.md
├── run.sh                         # Primary command entry point
├── flake.nix                      # Reproducible dev environment
├── .claude/skills/syndicate/      # Repo-local ROSSE syndication operating manual
├── .claude/skills/scanbook/       # Repo-local scanned-book → EPUB operating manual
├── .pi/settings.json              # Loads repo-local skills for pi sessions
├── config/                        # Local env/config templates
├── scripts/                       # Main backend and utility scripts
│   ├── adapters/
│   ├── gdocs_md_processor.py
│   ├── threads_exporter.py
│   ├── confluence_to_markdown.py
│   ├── gh_starred_to_bib.sh
│   ├── md_to_gdocs.py
│   ├── md_to_gdocs_html.py
│   ├── mineru2org.py
│   └── naver_blog_crawler.py
├── mineru-client/                 # Thin local client for remote gpu2i MinerU vLLM
├── templates/
│   ├── arxiv-acm/
│   ├── presentation/
│   └── presentation-pptx/
├── proposal-pipeline/            # Proposal authoring and export pipeline
├── scanpdf2org/                  # Older scanned PDF → page render → vision fallback
├── epub2org/                     # EPUB → Org (reverse direction)
├── hwpx2org/                     # HWPX/Org-related conversion utilities
├── orgadoc2odt/                  # AsciiDoc/ODT conversion utilities
├── office/                       # Real project working materials and samples
├── docs/                         # Converted output and project notes
└── logs/                         # Execution logs
```

### Notes on key directories

- **`scripts/`**: the main place for backend integrations and conversion entry points
- **`templates/`**: reusable starter templates for papers and presentations
- **`proposal-pipeline/`**: the most opinionated end-to-end workflow in the repo
- **`.claude/skills/scanbook/`**: the durable operating guide for scanned-book → EPUB work; read before touching `scanpdf/work/<book>/`
- **`mineru-client/`, `scripts/mineru2org.py`, `scripts/corrections/*.json`**: the current MinerU → Org → EPUB path
- **`office/`**: practical working examples and proposal artifacts
- **`hwpx2org/` and `orgadoc2odt/`**: lower-level format conversion experiments and tools

---

## Development environment

This project uses **Nix Flakes**.

Use one of the following:

```bash
# interactive shell
nix develop

# one-off command
nix develop --command python scripts/threads_exporter.py --download-images

# recommended for regular work
direnv allow
```

### Why Nix here?

- reproducible dependencies
- no ad-hoc `pip install`
- consistent Python / Pandoc / CLI tooling
- easier agent automation

---

## Quick start

### 1) Inspect available commands

```bash
./run.sh
```

### 2) Export a Google Doc by document ID

```bash
./run.sh gdocs-export <DOC_ID>
./run.sh gdocs-export <DOC_ID> --format md
./run.sh gdocs-export <DOC_ID> --format docx --depth 0
```

### 3) Export Threads posts into a single Org file

```bash
./run.sh threads-export --download-images
./run.sh threads-export --max-posts 5 --download-images
```

### 4) Convert Confluence export files to clean Markdown

```bash
./run.sh confluence-convert document.doc
./run.sh confluence-batch ./input-dir ./output-dir
```

### 5) Export GitHub Stars to BibTeX

```bash
./run.sh github-starred-export
./run.sh github-starred-export ~/org/resources/github-starred.bib
```

### 6) Run the proposal pipeline

```bash
./run.sh proposal-build --export-md
./run.sh proposal-merge --strip-hwpx-idx --org-tables
./run.sh proposal-export-odt
```

### 7) Build the ArXiv ACM sample

```bash
./run.sh arxiv-build
./run.sh arxiv-build templates/arxiv-acm/sample.org
```

---

## Templates

### `templates/arxiv-acm/`

A complete sample for:

- Org-mode authoring
- ACM `acmart` LaTeX export
- PDF generation suitable for paper drafting / ArXiv submission workflows

See: [`templates/arxiv-acm/README.md`](templates/arxiv-acm/README.md)

### `templates/presentation/`

A Quarto / Reveal.js presentation starter for browser-based slide decks.

See: [`templates/presentation/README.md`](templates/presentation/README.md)

### `templates/presentation-pptx/`

A newer **org2pptx** pipeline for teams that must submit or reuse a branded **PowerPoint template**.

Instead of rendering slides from scratch, it:

- parses an Org file
- injects content into an existing `.pptx` template
- preserves original slide backgrounds, logos, layouts, and branding

This is especially useful when `pandoc --reference-doc` or layout-name-based approaches fail on localized corporate templates.

See: [`templates/presentation-pptx/README.md`](templates/presentation-pptx/README.md)

---

## How to choose the right tool

- Need **Google Docs tabs exported cleanly** → use `gdocs-export`
- Need **social writing archived into Org** → use `threads-export`
- Need **legacy Confluence exports cleaned up** → use `confluence-convert`
- Need **citation-ready GitHub Stars** → use `github-starred-export`
- Need **proposal submission artifacts** → use `proposal-pipeline/`
- Need **a paper PDF from Org** → use `templates/arxiv-acm/`
- Need **HTML slides** → use `templates/presentation/`
- Need **content injected into an existing company PPTX** → use `templates/presentation-pptx/`

---

## Documentation

| File | Purpose |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Working guidance for coding agents and maintainers |
| [`BACKENDS.md`](BACKENDS.md) | Backend-specific notes and usage details |
| [`DEVELOPMENT.md`](DEVELOPMENT.md) | Development guidance for extending the project |
| [`DENOTE-RULES.md`](DENOTE-RULES.md) | Naming and structuring rules for Denote-style output |
| [`proposal-pipeline/README.md`](proposal-pipeline/README.md) | Detailed proposal workflow documentation |
| [`office/README.md`](office/README.md) | Real-world working context and example materials |

---

## Changelog

### 2026-04-03 — org2pptx presentation template added

- Added `templates/presentation-pptx/`
- Introduced an Org-mode → PPTX template injection workflow using `python-pptx`
- Preserves branded PowerPoint templates instead of recreating slides from scratch

### 2026-04-02 — ArXiv ACM paper template added

- Added `templates/arxiv-acm/`
- Added Org-mode → `acmart` → PDF sample pipeline
- Exposed `./run.sh arxiv-build`

### 2026-03-31 — Markdown to Google Docs helpers expanded

- Added `md_to_gdocs.py` and `md_to_gdocs_html.py`
- Optimized the Markdown → Org/HTML/Docx path for Google Docs import workflows

### 2026-03-31 — Naver Blog crawler expanded

- Added listing, crawling, verification, retry, title-fix, and wordmap commands
- Improved image handling, slug normalization, and title cleanup

### 2026-02-15 — GitHub Stars backend added

- Added `scripts/gh_starred_to_bib.sh`
- Added `./run.sh github-starred-export`
- Preserved `starred_at`, `pushed_at`, and `updated_at` metadata for BibTeX output

### 2026-02-03 — format conversion toolkit broadened

- Added HWPX/AsciiDoc-related tooling
- Added EPUB → Org workflows
- Added HTML → EPUB → Org experiments

### 2026-01-29 — Confluence conversion pipeline stabilized

- Added MIME-aware Confluence export parsing
- Normalized UTF-8/NFC issues and cleaned noisy markup

### 2026-01-21 — development environment modernized

- Migrated from `shell.nix` to `flake.nix`
- Added `direnv` integration
- Replaced secretlint with gitleaks
- Improved Threads OAuth token management

### Earlier foundation

- Project began as a Google Docs → Denote knowledge base converter
- Evolved toward a multi-backend, template-oriented, AI-friendly document workflow toolkit

---

## License

MIT

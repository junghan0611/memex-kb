# AGENTS

This file explains how coding agents should work inside the `memex-kb` repository.

It is written for maintainers, local coding agents, and any automation that needs to inspect, edit, or extend the repo safely.

---

## 1. Repository snapshot

`memex-kb` is no longer just a knowledge-base converter.
It is now a mixed toolkit for:

- document ingestion from external systems
- format conversion into Markdown / Org / BibTeX / ODT / DOC / PDF
- proposal-authoring pipelines
- reusable publishing templates for papers and presentations

### Current high-value areas

- **Google Docs export** with tab-aware Markdown extraction
- **Threads export** into a single Org archive with images and replies
- **Confluence export cleanup** for AI-friendly Markdown
- **GitHub Stars → BibTeX** export
- **Naver Blog crawling** into Denote-style outputs
- **Anthropic HTML paper → Org** for Distill (`transformer-circuits.pub`) papers, math/figure/citation-aware, round-trippable to HTML
- **Proposal pipeline** for Google Docs → Markdown → Org → ODT/DOC workflows
- **Template workflows**:
  - Org → ACM paper PDF (`templates/arxiv-acm/`)
  - Quarto presentation template (`templates/presentation/`)
  - Org → branded PPTX injection (`templates/presentation-pptx/`)

---

## 2. Working rules

### Always use the Nix environment for Python-based work

Preferred:

```bash
nix develop --command python scripts/threads_exporter.py --download-images
```

Also acceptable after `direnv allow`:

```bash
python scripts/threads_exporter.py --download-images
```

Avoid running Python scripts outside the flake environment unless the task is explicitly trivial and dependency-free.

### Use `run.sh` first when a command already exists

`./run.sh` is the main human/agent entry point.
Before adding a new script path to documentation, check whether the same workflow already has a `run.sh` command.

### Do not commit unless explicitly asked

When updating docs or code:

- make the edits
- show the diff / summary
- stop before commit unless the user asks for commit and/or push

### Keep documentation synchronized

If you add or change a backend, pipeline, or template, update the relevant docs in the same task:

- `README.md`
- `AGENTS.md`
- `BACKENDS.md` if backend-related
- `run.sh` if it should be a public command

---

## 3. Repo map for agents

```text
memex-kb/
├── README.md
├── AGENTS.md
├── BACKENDS.md
├── DEVELOPMENT.md
├── DENOTE-RULES.md
├── run.sh
├── flake.nix
├── config/
├── scripts/
├── templates/
│   ├── arxiv-acm/
│   ├── presentation/
│   └── presentation-pptx/
├── proposal-pipeline/
├── scanpdf2org/
├── epub2org/
├── hwpx2org/
├── orgadoc2odt/
├── office/
├── docs/
└── logs/
```

### Directory guidance

#### `scripts/`
Primary location for backend integrations and small conversion tools.
Important files include:

- `gdocs_md_processor.py`
- `threads_exporter.py`
- `refresh_threads_token.py`
- `confluence_to_markdown.py`
- `gh_starred_to_bib.sh`
- `md_to_gdocs.py`
- `md_to_gdocs_html.py`
- `naver_blog_crawler.py`
- `syndicate.py` — ROSSE 배포 묶음 생성기 (이슈 #4). **`.claude/skills/syndicate/` 먼저 읽기.**
- `anthropic_paper_to_org.py` — Anthropic Distill HTML 논문 → Org (수식/그림/인용/각주 보존). **`.claude/skills/anthropic-paper2org/` 먼저 읽기.**

#### `templates/`
Reusable publishing starters.

- `arxiv-acm/` — Org → ACM paper workflow
- `presentation/` — Quarto / Reveal.js presentation template
- `presentation-pptx/` — Org → PPTX template injection using `python-pptx`

#### `proposal-pipeline/`
The most end-to-end workflow in the repository.
Used for proposal documents that move through:

Google Docs → Markdown → Org-mode → ODT → DOC/HWP-oriented deliverables

#### Scan-to-EPUB pipeline — **see the `scanbook` skill**

Primary path (2026-06): **MinerU VLM → `scripts/mineru2org.py` → Org → ox-epub**.
The full operating procedure (remote gpu2i MinerU server, per-book config authoring,
correction strategy, gotchas, new-book checklist) lives in the repo-local skill
**`.claude/skills/scanbook/SKILL.md`** — read it before any scanbook work. run.sh alone
does not cover the remote server orchestration or the correction judgment.

- **MinerU** is the primary transcription engine. Vision/Opus full transcription is **retired**
  (kept only as a gold oracle for books that already have a `scanpdf/work/<book>/org/` vision draft).
  The marker (surya OCR) engine is removed; `scripts/diff_review.py` (`./run.sh diff-review`) is
  the engine-agnostic QA tool that survived it.
- `scanpdf2org/` — older scanned PDF → page render → vision transcription surface (`README.org`).
- `~/repos/gh/ox-epub` — maintained local fork for Org → **clean EPUB 3.0** (EPUB3 native + headless).
  memex-kb must not reintroduce an internal `epub_upgrade.py` / `org2epub.el` post-processing stack.
- `./run.sh org2epub-build <book.org>` is a thin wrapper that loads the ox-epub fork directly
  and runs `epubcheck`.
- Book data + outputs live in the nested private repo `scanpdf/` (Forgejo `glg-bot/scanpdf`).

Together: scanned PDF → Org → EPUB. `epub2org/` is the reverse (EPUB → Org, conventions in `PATTERNS.org`).

#### `hwpx2org/` and `orgadoc2odt/`
Lower-level conversion tooling and experiments related to HWPX, AsciiDoc, Org, and ODT workflows.

#### `office/`
Contains real-world working artifacts and examples.
Treat this as practical context, not as a general-purpose public API.

---

## 4. Main commands agents should know

Use `./run.sh` when possible.

### Google Docs

```bash
./run.sh gdocs-export <DOC_ID>
./run.sh gdocs-export-kiat
./run.sh gdocs-wrapper <DOC_ID>
```

### Threads

```bash
./run.sh threads-export --download-images
./run.sh threads-token-exchange <SHORT_TOKEN>
./run.sh threads-token-test
./run.sh threads-token-refresh
```

### GitHub Stars

```bash
./run.sh github-starred-export
```

### Confluence

```bash
./run.sh confluence-convert <INPUT.doc> [OUTPUT.md]
./run.sh confluence-batch <INPUT_DIR> [OUTPUT_DIR]
```

### Proposal pipeline

```bash
./run.sh proposal-build
./run.sh proposal-convert <INPUT.md>
./run.sh proposal-merge
./run.sh proposal-odt-fix <INPUT.odt>
./run.sh proposal-export-odt [ORG_FILE]
```

### Naver Blog

```bash
./run.sh naver-list <BLOG_ID>
./run.sh naver-get <BLOG_ID> <LOG_NO>
./run.sh naver-crawl <BLOG_ID>
./run.sh naver-verify
./run.sh naver-retry <BLOG_ID>
./run.sh naver-wordmap
```

### ROSSE 배포 (syndicate) — **see the `syndicate` skill**

가든 canonical 노트 → 매체별 복붙 묶음 1파일. 면별 포맷 규칙·복붙 함정·워크플로는
repo-local 스킬 `.claude/skills/syndicate/SKILL.md`가 SSOT (run.sh는 명령만 덮는다).
전략 SSOT는 autholog 노트 `20250324T110312`. 이슈 #4.

```bash
./run.sh syndicate <INPUT.md>           # → out/syndicate/<name>.bundle.md
./run.sh syndicate-specs                 # 매체 포맷 명세 표
```

### Anthropic HTML 논문 → Org (paper2org) — **see the `anthropic-paper2org` skill**

Anthropic Distill(`transformer-circuits.pub`) HTML 공개논문 → Org. **범용 HTML 아님**(Distill `<d-article>` 전용).
수식은 `<d-math>` LaTeX 소스 무손실, 인용 org-cite, 각주 보존, 그림은 정적 PNG 임베드 + JS 인터랙티브는
캡션+라이브링크 대체. org→HTML 왕복으로 "논문 쓰기 포맷=org" 실증. 산출물은 `out/anthropic-paper/`(gitignore,
원문 저작권=Anthropic). 판단·함정은 `.claude/skills/anthropic-paper2org/SKILL.md`가 SSOT.

org(SSOT) → **ArXiv급 PDF** export 는 `paper2org-pdf`. 브리지(`--acmart`)가 저자 N명→acmart 프리앰블,
`[cite:@k]`→natbib `\cite{}` 로 바꿔 `templates/arxiv-acm` 파이프(+`scripts/paper_build.el`, texlive nix-shell)에 물린다.
J-space 검증: 93쪽·인용 155개 bibtex 해석. (web HTML=ox-html, docx=pandoc 은 후속 — NEXT 참조.)

```bash
./run.sh paper2org <URL> [--name NAME] [--fetch]   # → out/anthropic-paper/<name>/<name>.org
./run.sh paper2org-pdf <URL> [--name NAME]         # → out/anthropic-paper/<name>/<name>.acmart.pdf
# 예: ./run.sh paper2org-pdf https://transformer-circuits.pub/2026/workspace/index.html --name jspace
```

### Other conversion helpers

```bash
./run.sh md-to-gdocs <INPUT.md>
./run.sh md-to-gdocs-html <INPUT.md>
./run.sh arxiv-build [ORG_FILE]
```

### Utility

```bash
./run.sh env-check
./run.sh secret-scan
./run.sh categorize-test
./run.sh denote-test
```

---

## 5. Current documentation state

When you update docs, reflect the repository as it exists now, not as it existed during the original Google Docs-only phase.

Important current realities:

1. The repository includes **multiple pipelines**, not only backends.
2. `templates/presentation-pptx/` is now a first-class template area.
3. `templates/arxiv-acm/` is also a first-class template area.
4. `proposal-pipeline/`, `hwpx2org/`, `orgadoc2odt/`, and `office/` are part of the meaningful repo surface.
5. `README.md` should describe the repository as a **document workflow toolkit**, not just a KB converter.

---

## 6. Validation guidance

There is no single formal test suite yet.
Use targeted validation based on what you changed.

### Safe checks

```bash
./run.sh env-check
./run.sh secret-scan
nix develop --command python scripts/refresh_threads_token.py --test
nix develop --command python scripts/denote_namer.py
nix develop --command python scripts/categorizer.py
```

### For documentation-only changes

Usually enough:

- verify file paths exist
- verify command names match `run.sh`
- verify links in README / AGENTS are correct
- run `git diff --stat`

---

## 7. Known pitfalls

### 7.1 Nix first

If a Python script depends on packages from `flake.nix`, do not assume the global Python environment is correct.

### 7.2 `run.sh` is the public interface

If a workflow already exists in `run.sh`, document that first.
Only document raw script invocation when it adds useful detail.

### 7.3 Denote timestamp uses capital `T`

Correct:

```text
20250913T150000
```

Incorrect:

```text
20250913t150000
```

### 7.4 Org-mode export requires careful escaping

For Org output, special characters like `*`, `[`, `]`, `_`, `~`, and `=` can break rendering if not escaped correctly.

### 7.5 Google Docs export is tab-aware

Prefer `gdocs_md_processor.py export` and the corresponding `run.sh gdocs-export` workflow instead of older ad-hoc paths.

### 7.6 PPTX template injection is not the same as HTML slide generation

- `templates/presentation/` → Quarto / Reveal.js HTML slides
- `templates/presentation-pptx/` → inject Org content into an existing PowerPoint template

Do not confuse these two in docs or implementation notes.

### 7.7 `pandoc --reference-doc` is not enough for localized PPTX templates

The repo now contains `org2pptx` specifically because layout-name-based approaches fail on many real-world templates with non-English layout names.

---

## 8. If you add or change a backend/template

Update all relevant surfaces before finishing:

### Backend changes

- implementation in `scripts/` or another relevant directory
- command exposure in `run.sh`
- `BACKENDS.md`
- `README.md`
- `AGENTS.md`

### Template changes

- template directory under `templates/`
- local `README.md` inside that template directory
- root `README.md`
- `AGENTS.md`
- `run.sh` if a convenient command should exist

---

## 9. Style expectations

### Python

- follow existing script style
- prefer type hints where practical
- use logging for non-trivial scripts
- keep conversion logic explicit and inspectable

### Bash

- keep `set -e`-style safety
- use readable command wrappers
- prefer clear usage/help comments inside `run.sh`

### Documentation

- write clear English when updating shared project docs
- prefer accurate, current descriptions over aspirational ones
- avoid stale paths and outdated architecture summaries

---

## 10. Important files to read before larger edits

- `README.md`
- `BACKENDS.md`
- `DEVELOPMENT.md`
- `DENOTE-RULES.md`
- `proposal-pipeline/README.md`
- template-local READMEs under `templates/`

---

## 11. Contact

- Developer: **Junghan Kim** (`junghanacs`)
- GitHub: <https://github.com/junghan0611>
- Blog: <https://notes.junghanacs.com>

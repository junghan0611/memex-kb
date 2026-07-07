# Changelog

All notable changes, tracked by CalVer date tags.

## Unreleased

## v2026.7.7 — Anthropic paper2org exports + ROSSE handoff

### Anthropic Distill papers

- Added `paper2org`: Anthropic Distill HTML (`transformer-circuits.pub`) → reproducible Org capture with preserved LaTeX math, org-cite citations, footnotes, static PNG figures, and interactive-figure source links.
- Added `paper2org-html`: Org → Pandoc citeproc HTML with rendered author-year citations, a CSL bibliography, MathJax, and static image references.
- Added `paper2org-pdf`: Org → acmart PDF through an acmart bridge, Emacs batch export, TeX Live, BibTeX, and natbib citations.
- Restored resolvable figure references from source `data-fignum` metadata before HTML/PDF export.
- Added and hardened `.claude/skills/anthropic-paper2org/SKILL.md` as the operating guide for the proven command set and validation checks.
- Verified the J-space paper end-to-end: Org capture with zero leftover sentinels, HTML with 173 CSL bibliography entries, and a 93-page acmart PDF.

### ROSSE syndication

- Added LinkedIn `link=comment` output so the garden link can be posted as a first-comment block while keeping the body link-free.
- Documented the current hand-publishing mode and kept the existing syndication bundle generator ready for later reuse.

### Docs

- Updated README and AGENTS surfaces for the paper2org command set.
- Trimmed completed paper2org work from NEXT while leaving only consumer handoff and optional follow-ups.

## v2026.6.15 — scanbook 5권 + OCR 멀티엔진 + ROSSE 배포

### ROSSE 배포 (syndicate, 이슈 #4)

- **`syndicate` 스킬 + 묶음 생성기**: 가든 canonical 노트 1개 → 매체별 복붙용 포맷 묶음 1파일. 원문형(페북·링크드인)/전문형(네이버·티스토리)/요약형(스레드·트위터·블루스카이·인스타) 3종 클래스. 개인 프로필 발행이라 공식 쓰기 API가 막혔거나 없음 → 복붙·브라우저 클로드 소비 1차. `scripts/syndicate.py`의 `PLATFORMS` dict가 포맷 규격 런타임 SSOT, `.claude/skills/syndicate/`가 운영 SSOT, autholog 노트 `20250324T110312`가 전략 SSOT.
- `./run.sh syndicate` / `syndicate-specs` 명령, 입력 예시 `samples/syndicate-sample.md`.

### Scanbook / OCR 파이프라인

- **감독형 page-split 문단 봉합**: `detect_para_splits.py` 탐지기 + `mineru2org.py` `_seam_for`(josa/fusion/mid-어절 seam, digit/caption/pageref/enum skip). 책별 samepage 판단(자유형 오염=카테고리 드롭, 규칙형=skip 규칙). 5권에 적용.
- **구조 핸들러 확장**: 3-level(부/강/소절), chapsec(장/고정마커절/소절), chapters 2단 + 일반규칙(중복장→소절, 강번호줄 드롭, 단일 한글음절 헤딩 강등). `body_bounds` back_matter fallback, structural-label skip 규칙, demath.
- **5권 전사 완료** → clean EPUB(epubcheck 0/0/0): 물질생명인간·물리학강의·자연철학강의·물리의정석·인공지능시대. 인공지능시대는 heading 파편 극심 → 책 전용 `assemble.py`.
- **OCR 멀티엔진 평가**: DeepSeek-OCR / PaddleOCR-VL / PP-StructureV3 / GLM thin-client. 모델 layer(글자정확도) vs 도구 layer(layout·asset픽셀·수식LaTeX·구조라벨) 2층 비교. 벤치 = 물리학강의 5강 고정구간.
- flake: ox-epub 패키징용 zip/unzip, nodejs_24.

### textlint-ko

- **textlint ↔ kime 연결고리** 실증 — 띄어쓰기 붕괴 복원(형태소)이 scanbook PP-StructureV3 채택의 전제로 두 작업축이 만남.

### Docs

- Repo-local `scanbook` skill + `.pi/settings.json` 스킬 로딩 (이전 스냅샷부터 누적).
- MinerU를 scan→EPUB primary로 정렬, vision/Opus 전사·marker/surya OCR은 retired/fallback로 표기.
- README/AGENTS/BACKENDS에 syndicate 백엔드·스킬 동기화.

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

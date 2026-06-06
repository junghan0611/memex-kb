---
name: scanbook
description: "Turn a scanned Korean book PDF into a clean EPUB via the MinerU→post-process→org→ox-epub pipeline in ~/repos/gh/memex-kb. Use when working on any book under scanpdf/work/<book>/ — parsing a scan with MinerU, writing/extending a book correction config, fixing OCR misreads, reconstructing heading/footnote/paragraph structure, merging page-split paragraphs, building or validating the EPUB, or starting a NEW book (e.g. 물리학강의, 물리의정석, 자연철학강의, 인공지능시대). Triggers: 'scanbook', 'mineru', '물리학강의', '스캔책', '스캔북', 'epub 만들', 'epub 빌드', 'mineru-parse', 'mineru2org', '책 전사', 'OCR 책', 'org2epub', '용어집 만들', 'diff-review', 'para-splits', '문단 잘림', '문단 봉합', '감독형 봉합'. This skill carries the tribal knowledge run.sh and docs cannot: the remote GPU dependency, the correction strategy, the paragraph-merge judgment, and the hard-won gotchas."
user_invocable: true
---

# scanbook — scanned book → EPUB pipeline

Repo: `~/repos/gh/memex-kb`. Book data + outputs live in the **nested private repo**
`scanpdf/` (Forgejo `glg-bot/scanpdf`). This skill is the operating surface; `run.sh`
covers the *local* commands, this file covers the rest (remote GPU server, per-book config,
correction + paragraph-merge judgment, gotchas).

Mental model: **MinerU lays down ~95% (chars + layout). The last 5% is judgment** — char
misreads and **page-split paragraphs**. Both are fixed by *detect-then-supervise* tools,
never by blind blanket automation.

## Pipeline

```
PDF ──①MinerU VLM (REMOTE gpu2i)──▶ md + content_list.json + images/
    ──②mineru2org.py (post-process)─▶ clean .org  (headings/footnotes/eq/images
    │                                  + corrections + supervised paragraph-merge)
    ──③ox-epub──────────────────────▶ .epub (epubcheck 0/0/0)
    QA: ④diff-review · para-splits        config: ⑤scripts/corrections/<book>.json
```

- **Stage ① is the only non-local part**, not fully expressible in `run.sh`.
- vision/Opus full transcription is **retired**. Do not spin Opus agents on page images.
- Two classes of last-5% work, each with a detect→supervise tool:
  - char misreads → `corrections/<book>.json` (`safe_regex`/`literal`/`candidate_regex`)
  - page-split paragraphs → `para-splits` detector + supervised merge (§Paragraph splits)

## ⚠️ Stage ① — remote MinerU server (run.sh can't own this)

Inference runs on **gpu2i** (RTX 5080), a vLLM server serving `MinerU2.5-Pro` on port 30000.
This is **nixos 담당's domain** — a tmux session, not a memex-kb artifact.

```bash
ssh gpu2i 'tmux ls | grep mineru-vllm'    # alive? do this FIRST every parse session
# Missing → it is down. Ask GLG/nixos to bring it up. Do NOT start the vLLM from here.
```

- `run.sh mineru-parse` **auto-tunnels** `localhost:30000 → gpu2i:30000`; only needs the
  server already running. Health = `curl -sf localhost:30000/health` (vLLM returns 200 with
  empty body — the `-sf` exit code is truth, not the empty output).
- Client install (one-time): `./run.sh mineru-setup` (uv sync; opencv-headless override).
  The client (`mineru-client/`) is a thin http-client; weights live on gpu2i.
- A 261-page book parses in **~3 min**. Background it for big books.

```bash
./run.sh mineru-parse scanpdf/<book>001.pdf mineru-client/out
# → out/<book>001/vlm/{<book>001.md, _content_list.json, images/}
# MOVE useful artifacts under scanpdf/ for commit (Forgejo):
#   <book>001.md, _content_list.json, images/ → scanpdf/work/<book>/mineru/
#   DROP heavy *_origin.pdf / *_layout.pdf / *_model.json / *_middle.json
```

## OCR engine choice — 4 engines, **model layer vs tool layer** (measured 2026-06)

The single most important frame: an engine is **two layers**. Compare *within* a layer.

- **Tool** (layout + **asset 픽셀 crop** + **formula LaTeX** + structure labels): MinerU pipeline,
  PaddleOCR **PP-StructureV3**. These give what a pure OCR model cannot.
- **Model** (page→text only): MinerU2.5-VLM, DeepSeek-OCR, PaddleOCR-VL.

| | MinerU | PP-StructureV3 | DeepSeek-OCR | PaddleOCR-VL | GLM-OCR |
|---|---|---|---|---|---|
| layer | tool+model | **tool** | model | model | model |
| serving | gpu2i:30000 | gpu3i:8118 (PaddleX `/layout-parsing`) | gpu1i:8000 | gpu3i:8000 | gpu3i:8101 |
| run.sh | `mineru-parse` | `ppstructure-parse` | `deepseek-parse` | `paddleocr-parse` | (재측정: paddleocr 클라 `--url …:8101 --model glm-ocr --prompt "Text Recognition:"`) |
| image px crop | ✓ 9 | ✓ 9 (크롭10) | bbox만 | ✗ | ✗ |
| formula LaTeX | ✓ `\mathrm{}` | ✓ **inline까지** | ✓ `H_2` | ✗ 평문 `2H2` | ✗ |
| structure | content_list | parsing_res_list (동급) | grounding(부분) | ✗ | ✗ |
| spacing 공백비율 | 정상 | **0.12 붕괴** | 0.21 | 0.23 | 0.22 |
| 한국어 글자 | mosaic/焮 환각 | 보통(mobile-rec) | 우수 | 우수 | **최악 + 한자환각(磊嚣螽)** |

**Measured on 물리학강의 5강 (PDF p121–137).** Proper-noun failures **DON'T overlap** —
this is the key: 톰슨 = MinerU `톈슨`(+mosaic환각)·Paddle 4변형·PP `통슨`·GLM `통속` / **DeepSeek ✓**;
돌턴 = **DeepSeek `돌탄`✗**·GLM✗전멸 / MinerU·Paddle·PP ✓; 찐빵 = MinerU 6변형·Paddle✗ / DeepSeek·PP ✓.

**⚠️ GLM-OCR 함정**: OmniDocBench 94.6%(5엔진 중 SOTA 1등)인데 **한국어 스캔책에선 꼴찌** —
돌턴/톰슨/볼츠만 정상표기 0건, 한자 환각. 띄어쓰기만 보존. **한국어 책 제외.** OmniDocBench
점수 ≠ 한국어 충실도의 결정적 반례. 영문 문서엔 SOTA일 것.

**★ PaddleOCR-VL has TWO serving modes** — 같은 모델, 다른 출력:
- **모델 모드** (vLLM `/v1/chat/completions`, gpu3i:8000/8001): 순수 텍스트만. asset·구조·수식 없음.
- **도구 모드** (PaddleX `/layout-parsing`, gpu3i:8119, `ppstructure_client.py --url …:8119`):
  **모델+도구 동시** — 텍스트 우수+띄어쓰기 보존(0.202)+asset 12개+구조 9종(vision_footnote/
  display_formula/reference_content). 돌턴·볼츠만·굽은 ✓(GLM/DeepSeek/MinerU가 깨먹은 곳 맞힘).
  약점: 느림(8.5s/p), 톰슨→통슨. **현 시점 단일 최강 base.**

**현재 최선 (decision rule, the method):**
- **Tool base = PaddleOCR-VL 도구모드(:8119)** — MinerU 환각도 PP mobile-rec 띄어쓰기붕괴(0.12)도
  둘 다 회피하는 단일 최강. **MinerU = 빠른 대안 base**(asset+content_list, 속도 ↑; 텍스트는
  oracle 교정). PP-StructureV3(mobile-rec)는 **kime 띄어쓰기 복원 전제**라 후순위
  (scanbook ↔ textlint-ko 연결점).
- **Body char oracle = DeepSeek** (이 구간 garble 최소) 또는 PaddleOCR-VL(환각 없고 본문 깨끗).
  MinerU 깨진 span만 `deepseek-parse --pages N` → 정확 토큰 → `corrections/<book>.json`.
  Proven: Guq은→굽은, mosaic→톰슨, 짧빵→찐빵.
- **고유명사 = multi-engine voting.** 엔진 불일치 토큰 = 오독 의심점 → 교정후보 자동생성
  (차기 `engine_vote.py`). 한 엔진의 *반복* 오독은 못 잡지만(예: 시간펼침→시간필침 ×14),
  엔진 *불일치* 는 그 자체로 신호. consistency≠accuracy 의 역(逆)활용.
- **MEASURE first** on one chapter — predictions were wrong repeatedly. 점수표(OmniDocBench)
  ≠ 한국어 스캔책 고유명사 충실도.

DeepSeek serving: `ssh gpu1i 'tmux ls | grep deepseek-ocr'`; `deepseek-parse` auto-tunnels
`localhost:8000 → gpu1i:8000`. grounding prompt = `<image>\n<|grounding|>Convert the document to markdown.`

## Stage ② — post-process: `scripts/mineru2org.py`

Deterministic structure-recovery converter (same input → byte-identical output), driven by
the per-book config (`--corrections`) + `--content-list`.

```bash
python3 scripts/mineru2org.py scanpdf/work/<book>/mineru/<book>001.md \
  -o scanpdf/work/<book>/mineru/<book>-mineru.org \
  --corrections scripts/corrections/<book>.json \
  --content-list scanpdf/work/<book>/mineru/<book>001_content_list.json
# Emits: <book>-mineru.org + .changes.log    (every transform, counted)
#                            + .candidates.log (uncertain char fixes, NOT applied)
#                            + .merges.log     (paragraph-merge decisions; §Paragraph splits)
```

Passes (all logged): surface (image `![]()`→`[[file:]]`, block `$$`→`\[\]`, inline `$$`→`\(\)`,
footnote `$^{n}$` + unicode superscript `⁵⁸²³`→`[fn:n]`); HTML cleanup (`<details>`/mermaid
removed, `<table>`→org table); **structure recovery** (chapter `*` / section `**` num+title
merge / subsection `***` / false-heading demotion / front-matter+TOC cut / preface kept);
**footnote defs** from `content_list.page_footnote` → `* 각주` section + orphan numeric
paragraphs absorbed; **supervised paragraph-merge** (opt-in); corrections; epub header from meta.

## Stage ⑤ — the per-book config (the real per-book work)

`scripts/corrections/<book>.json`. Copy `물질생명인간.json` as template:

```jsonc
{
  "meta":   { title, author, date, language, publisher, subject, uid },   // → epub #+keywords
  "structure": {
    "body_start": "<first chapter title>",      // everything before = front matter, cut (preface kept)
    "chapters": [ { "num": "1장", "title": "..." }, ... ],
    "chapter_title_variants": { "<ocr/dash variant>": "<canonical>" },
    "back_matter": ["참고문헌", "찾아보기"]      // become * level; 찾아보기 internal headings dropped
  },
  "safe_regex":      [ { pattern, replace, desc } ],   // AUTO. Must be PROVABLY safe (see strategy).
  "literal":         [ { from, to, desc } ],           // AUTO exact-string fixes (heading OCR, LaTeX).
  "candidate_regex": [ { pattern, desc } ],            // LOG ONLY (.candidates.log). Never edits body.
  "paragraph_merge": {                                 // OPT-IN supervised merge
    "enabled": false,                                  // off until validated per book
    "categories": ["page_boundary", "samepage_break"], // never eq/image/table by default
    "overrides": [ { "tail": "<suffix>", "seam": "space|nospace|skip" } ]
  }
}
```

Author it by **reading the parsed md**: heading layout, section numbering, recurring OCR
misreads, index/reference layout.

## 🎯 Char-correction strategy (hard-won — do not regress)

Central vocabulary is the highest-priority target: a key term mangled in the index is mangled
in the body too.

- **Blanket regex is unsafe in general**: a misread char collides with real words (`않은`/`앉은`/
  `읽은` are valid; `암` can be 暗/癌).
- **Safe rule** = "misread char + a particle the misread char can NEVER take as a verb ending":
  `(앉|않|읽|얇)(이|의|과|와|도|만|에|으로…)` → `앎`; exclude `은/을/음` (valid endings).
- **Anything ambiguous → `candidate_regex`** → `.candidates.log`, body untouched.
- **`candidate_regex` only sees its own pattern's blind spot.** The latin-in-hangul pattern
  `[가-힣]*[a-zA-Z]+[가-힣]+` floods on legit physics-variable + 조사 (`H이다`, `Q라`, `t로`,
  `σ가`) — 물리의정석 logged 547, ~all false. Narrow it to `[가-힣][a-zA-Z]{2,}[가-힣]` (2+ fused
  latin = real garble). But the bigger lesson: **pure-hangul misreads carry no latin at all**
  (`써으니까→썼으니까`, `무거위서→무거워서`, `묶이다→몫이다`, `범칙→법칙`) so NO latin regex catches
  them. Two surfaces find these instead: (1) **`.merges.log`** — its clean page/para-joint prose
  is the best window onto body garbles (the merge just surfaces them at the seam); (2) **active
  suspect-syllable scan** for mid-page ones (`grep` non-word syllables like 쏸/위서/짧수, then
  verify each in context). A whole non-word syllable (`쏸`, `멜타`) that is invalid Korean
  everywhere → `safe_regex` after confirming every occurrence is the same fix (물리의정석 쏸→쓸 ×15).
- **General finisher = a LIGHT LLM pass** (you, reading context). MinerU did 95%; you fix the
  flagged 5% by reading the sentence. The lightweight replacement for full vision transcription.
- **Book-specific promotion**: promote a candidate to `safe`/`literal` only after verifying the
  whole class in that book (물질생명인간 has no 暗/癌, so `암+조사`→`앎` verified safe, 22 epistemic
  occurrences). Never copy a rule across books blindly.
- **OCR consistency ≠ accuracy**: a frequent term mis-read the *same way* by both engines
  (물리학강의 `시간펼침`→`시간필침` ×14) won't show via engine comparison. Catch by vision
  spot-check of one page, then one `literal` rule covers the class.
- **Oracle**: if a vision transcription exists (`scanpdf/work/<book>/org/`), use it as gold via
  `diff-review`. New books have no oracle → candidates log + LLM pass + page-image spot-checks.

## 📐 Paragraph splits + supervised merge (감독형 봉합)

MinerU (every page-at-a-time OCR) reads **each page independently**, so a paragraph crossing a
page boundary or interrupted by a figure/table/equation is emitted as **separate paragraphs**.
This is **outside OCR accuracy** — chars are right, the boundary is wrong. Confirmed across
물리학강의 · 자연철학강의 · 물질생명인간. Unavoidable; handled as know-how, never as a blind merge.

### Detection is automatic; the seam is supervised (the core split)

`scripts/detect_para_splits.py` (= `./run.sh para-splits <book>`) classifies candidates from
`content_list.json` + a Korean terminal-punctuation heuristic, and **only lists** them (body
untouched). Rule: a text block ending without terminal punctuation (`.?!…。`/closing quote or
bracket) followed by a text block not starting a paragraph marker = continuation candidate.
front matter (TOC) / back matter (찾아보기) excluded — their lines end in page numbers and flood
false positives.

> **`body_bounds` running-head fallback (hard-won, 물리의정석).** The back-matter cut is found by
> the first block whose `text_level` is set AND text starts with a `back_matter` name. But MinerU
> sometimes emits the index title **only as a running head** (`type:'header'`, `text_level:None`)
> with no `#` heading at all — then `ei` stays at end-of-book and the **whole index + colophon get
> merged** (판권 glued into one line `2018년…지은이…옵긴이…`). Fix already in `body_bounds`: if the
> text_level search finds nothing, fall back to "first block of the first page that carries that
> running head" (the index starts on that page). Same root cause makes the index 자모 dividers
> become garbage `**` headings (the `in_index` drop also keys off a `#` 찾아보기 heading that
> doesn't exist) — handled by the **single-syllable hangul heading demote** in `reconstruct`
> (no real heading is one syllable). Both are shared SSOT → verify byte-identical on the other books.

```bash
./run.sh para-splits <book>                                      # summary counts
./run.sh para-splits <book> --category page_boundary --limit 0   # full target list
./run.sh para-splits <book> --json                               # machine-readable
```

Measured (body region only, 2026-06-04):

| book | total | eq | page_boundary | image | table | samepage |
|---|---|---|---|---|---|---|
| 물리학강의 | 701 | 58 | 392 | 130 | 17 | 104 |
| 자연철학강의 | 473 | 101 | 198 | 40 | 0 | 134 |
| 물질생명인간 | 202 | 11 | 139 | 0 | 0 | 52 |

### Reliability tiers = how deep automation can safely go

- **page_boundary** — detection HIGH; **the seam space is NOT auto-decidable.**
  Measured on the 392 page-boundary cases: ~65% need **no space** (mid-어절 wrap, `물`+`리과학`→
  `물리과학`), ~30% need **a space** (어절 boundary, `그것을`+`특별히`→`그것을 특별히`), ~5%
  ambiguous (digit/latin/symbol). Collapsing one way breaks 30%. → merge the two `\n\n`-separated
  blocks into one paragraph, decide the seam by heuristic **+ log every decision + review**.
  Cleanest category — only cross-page prose continuation lands here.
- **samepage_break — PER-BOOK decision, NOT a default-on category.** Detection is HIGH but the
  category conflates prose-continuation with *structured single-page blocks*: verse lines, classical
  quotations (한문), diagram/schema box labels, formula variable legends, reproduced ads. A
  prose-heavy book (물질생명인간) merges these safely; a structure-heavy book does NOT. **자연철학강의
  (십우도 verse + 한문 + `[지식N]`/처음·나중 boxes + formula legends): samepage_break dry-run glued
  ~77 of 264 wrongly** (`돌아와 보니`+`소는`→`보니소는`, `않습`+`人爲能知`). **Always read the full
  dry-run `.merges.log` first.** Then the fork:
  - **Verse/한문/free-form-label heavy → drop the category** (`categories: ["page_boundary"]`). The
    contamination is too varied to detect cleanly. This is 자연철학강의.
  - **Contamination falls into a few *regular* label shapes → keep samepage, add a skip rule** for
    each shape in `_seam_for` (caption-head / pageref-tail / enum-circled cover 도판 캡션 / `…NNN쪽`
    cross-refs / `①` box titles). This is 물리학강의 — 45 labels auto-skipped, 43 prose merges kept.
    Prefer this when the labels are *systematic* (textbook callouts, figure captions), because it
    rescues the genuine same-page prose the blanket drop would lose. **Verify zero regression on
    already-committed books** (`_seam_for` is shared SSOT) before trusting a new skip rule.
- **eq_interrupt** — text + display-equation + text. **Do NOT merge.** A display equation belongs
  on its own line (current render is correct); only blemish is the continuation text looking
  indented — low priority.
- **image_interrupt / table_interrupt** — MEDIUM. The block after a figure may be a **caption /
  variable legend** (text_image auto-OCR), not the prose continuation (`…이 크기에서` + `위쪽
  왼편부터…` is a figure description; `…이것` + `m: 물체의 질량…` is a variable legend). Same vein
  as GPT review P4 "suppress text_image". Judge by the page image.

### The supervised merge pass in `mineru2org.py`

Opt-in (`paragraph_merge.enabled: true`, or `--merge-paragraphs`). Default OFF so reproducibility
is unchanged until a book is validated. Mechanism:

1. Re-run detection over `content_list` for the configured `categories` (`page_boundary`,
   `samepage_break` only — never eq/image/table).
2. For each candidate, locate `tail\n\nhead` in the md and join it, deciding the seam. The
   `_seam_for()` rule order in `mineru2org.py` is the **SSOT** (refined book-by-book); current:
   override → **digit-head skip** → **caption-head skip** → **pageref-tail skip** →
   **enum-circled skip** → comma→space → non-hangul tail skip → **josa-head**(head is a
   bare josa → no space, `사이`+`에`=사이에) → **latin-head**→space → **conj-head**(및/또는)→space →
   **adv-tail**(물론/특히)→space → **jeok-tail**(X적 + noun)→space → **이-fusion**(이+란/며/든/었/는/
   들/라/러/루/른/렇/를)→no space → josa/ending suffix→space → else mid-어절→no space.
   - **The 3 structural-label skips let a structure-heavy book KEEP samepage_break** (instead of
     dropping the whole category like 자연철학강의). They suppress *labels masquerading as prose*:
     **caption-head** (head = `그림/표/사진 N-N:` 도판 캡션), **pageref-tail** (tail ends `\d+쪽` —
     a `더 알아보기 ① … 202쪽` cross-ref; `\d` before 쪽 so 왼쪽/양쪽 are exempt), **enum-circled**
     (tail starts `①②③…` AND ≤24 chars = a box subtitle `① 로렌츠 변환식`). The ≤24 gate is
     load-bearing: 물리학강의 box titles ≤21, but 물질생명인간's ①-prefixed Kant *quotation
     paragraphs* are ≥27 and genuinely continue — so the gate skips titles, merges prose. Proven on
     물리학강의 (45 samepage labels skipped, 43 prose merges kept; zero regression on the 2 committed books).
3. **digit-head skip is load-bearing** (hard-won, caused a build failure): a footnote-definition
   orphan (`19 이러한…` paragraph) merged into the prior paragraph becomes `…그19…`, so
   `footnote_defs` can no longer absorb it as a standalone `^\d+ ` line → `[fn:19]` loses its
   definition → ox-epub export errors `Definition not found for footnote 19`. Any digit-starting
   head (footnote def / numbered list / ⑦) is left split.
4. Heading guard: a candidate whose head OR tail (≤40 chars) is a plain chapter/section marker
   (NUMHEAD regex `제?N[부강장절편]` or an exact `structure` title / section_marker) is skipped —
   else the merge swallows a plain-text 강 marker and the heading vanishes (was: 4·13·18강).
5. `paragraph_merge.overrides` force a seam for a tail suffix
   (`{"tail":"그것을","seam":"space"|"nospace"|"skip"}`). Surgical one-off glues (관형형 `된 연유`,
   의존명사 `세계 안에는` — too ambiguous to generalize) go in `literal` instead (runs after merge).
6. Every action → **`.merges.log`**: `MERGE(seam,reason)` / `SKIP(reason)` / `MISS(n=…)` with
   page + tail + head. This log is the review surface. MISS (joint not unique in md, e.g. a
   repeated diagram label) is a safe refusal.

**Workflow (list → apply → grow the logic, repeated):**

1. `./run.sh para-splits <book> --category page_boundary --limit 0` — capture the full list.
2. Enable merge for page_boundary + samepage_break; rebuild; **read `.merges.log` end to end.**
3. Fix wrong seams via `overrides`, glued words via `literal`. Feed recurring mis-classes back
   into the detector/merge logic. **Trust the detect list, review the seam.**
4. Re-run; confirm `.merges.log` clean and epubcheck still 0/0/0. eq/image stay manual.

> NEVER blanket-merge all 700 with one space policy — 30% would glue or split words. The detect
> list is trusted; the seam is reviewed. That separation IS the know-how.

## GPT structure review (for post-process improvements)

Throw an entwurf to **gpt-5.4** (`cwd: ~/repos/gh/memex-kb`) to diff the post-processed org
against the vision oracle (body region only) and classify *structural* gaps (headings,
footnotes, tables, paragraphs) — not char typos. It writes a review md. This is how
`mineru2org.py` grew from a string-replacer into a structure-recoverer. Reference:
`scanpdf/work/물질생명인간/mineru/REVIEW-gpt.md` (conflict-type table + P0–P5 plan).

## Stage ③ — build + validate EPUB

```bash
./run.sh org2epub-build scanpdf/work/<book>/mineru/<book>-mineru.org
# thin wrapper → loads ~/repos/gh/ox-epub/ox-epub.el directly (no in-repo post-proc).
# LaTeX → SVG (dvisvgm), embeds images, runs epubcheck (EPUBCHECK=1). Goal: 0/0/0.
```

ox-epub is a maintained local fork (`~/repos/gh/ox-epub`). memex-kb must NOT reintroduce an
internal `epub_upgrade.py` / `org2epub.el` stack. Known fact: SVG sizing uses
`max-width: 90%; height: auto` on `.org-svg` so inline math stays natural-size and only
over-wide display math/figures cap at 90%.

## 🐛 Gotchas

- **`ltximg/` is a build cache.** epubcheck missing-SVG (`RSC-007`) = stale cache →
  `rm -rf <book-dir>/ltximg <book>.epub` and rebuild. `ltximg/` is gitignored.
- **`zip`/`unzip` required** by ox-epub packaging (in flake devShell). Fresh box → run via
  `nix develop --command ./run.sh org2epub-build …`.
- **Non-standard LaTeX breaks dvisvgm silently.** MinerU emits `\leqq`/`\geqq` (needs amssymb)
  → normalize to `\leq`/`\geq` via `literal`. Failed equation = missing SVG = epubcheck error.
- **Index 자모 dividers (ㄱㄴㄷ…)** come out as garbage headings (`# 7`, `# □`, `# 人`,
  `# $\Rightarrow$`). Inside 찾아보기 the converter drops all `#` headings; an equation-only
  heading `** \(\Rightarrow\)` also fails packaging — drop, don't keep.
- **Images are already inline** in the md at the right spot (`![](images/x.jpg)`), next to their
  `<그림 N>` caption. Convert syntax only; `content_list` page_idx is a backup.
- **`content_list.json` is the structure SSOT**: `page_footnote` (defs, number-prefixed),
  `page_number` (page_idx→printed), `list` (TOC/list → spot false headings), `table`,
  `image.sub_type` (text_image/flowchart/natural_image). Also SSOT for the paragraph-split
  detector (page_idx + block-type adjacency).
- **Footnote refs MinerU misses** (7, 11) → "definition without ref" — logged, acceptable; flag.
- **`#+options: ^:{}`** in the header is required so a stray `^` (10^{10}) doesn't break export.
- EPUB header **`tex:dvisvgm`** so equations render to SVG (not MathML/png).
- **DeepSeek oracle `page` = page_idx (0-based)** = content_list. `--pages` is 1-based (page_idx+1).
- **Don't touch intentional 병기 / coined terms.** Some `한자/latin`-glued tokens are deliberate
  (물리학강의: `기氣차라`=Star-Trek "Energize!" pun, `훑기궤뚫기현미경`=STM coinage, `짝even`,
  `보오손boson`). Verify against index/context before "fixing" — a wrong fix corrupts the voice.

## ✅ Reproducibility

From `<book>001.md` + `<book>.json` + `content_list.json`, stages ②③ regenerate org and epub
deterministically (epubcheck 0). Each book gets a `scanpdf/work/<book>/mineru/README.md` with
the exact recipe + inventory. Before committing: delete org/epub/ltximg, re-run ②③, confirm 0.

## 🚀 New book checklist (e.g. 물리학강의 — equation-heavy)

1. `ssh gpu2i 'tmux ls | grep mineru-vllm'` — server up? else ask GLG/nixos.
2. `pdfinfo`/`mutool info scanpdf/<book>001.pdf` — page count sanity.
3. `./run.sh mineru-parse scanpdf/<book>001.pdf mineru-client/out` (background big books).
4. Move artifacts → `scanpdf/work/<book>/mineru/` (md + content_list + images; drop heavy files).
5. **Read the md** → write `scripts/corrections/<book>.json` (meta + chapters + first corrections).
6. `python3 scripts/mineru2org.py …` → inspect `.changes.log` (heading/footnote counts) + `.candidates.log`.
7. LLM light correction pass over candidates + typos (promote verified classes to config).
8. `./run.sh para-splits <book>` → assess split load → enable supervised merge, review `.merges.log`.
9. (optional) GPT structure review if quality unclear / book structurally complex.
10. `./run.sh org2epub-build …` → fix any epubcheck error → 0/0/0.
11. Update per-book `README.md` + repo `NEXT.md`. Commit memex-kb (tooling/config) + scanpdf
    (data); GLG approves push/tag.

> 물리학강의: **many equations + figures**. Expect `image.sub_type == text_image` math crops.
> Per GPT review P4, low-confidence `text_image` OCR should be *suppressed/isolated* (keep the
> image, drop the noisy auto-OCR). Extend `mineru2org.py` if needed.

## Where the durable facts live (not docs that rot)

- This skill = how to operate the pipeline (incl. the two detect→supervise tools).
- `NEXT.md` = the volatile next step.
- `scanpdf/work/<book>/mineru/README.md` = per-book reproduce recipe + inventory.
- `scripts/corrections/<book>.json` = per-book structure + char-correction + paragraph-merge SSOT.
- `CHANGELOG.md` / commit history = what changed when.

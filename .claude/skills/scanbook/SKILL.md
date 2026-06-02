---
name: scanbook
description: "Turn a scanned Korean book PDF into a clean EPUB via the MinerU→post-process→org→ox-epub pipeline in ~/repos/gh/memex-kb. Use when working on any book under scanpdf/work/<book>/ — parsing a scan with MinerU, writing/extending a book correction config, fixing OCR misreads, reconstructing heading/footnote structure, building or validating the EPUB, or starting a NEW book (e.g. 물리학강의, 물리의정석, 자연철학강의, 인공지능시대). Triggers: 'scanbook', 'mineru', '물리학강의', '스캔책', '스캔북', 'epub 만들', 'epub 빌드', 'mineru-parse', 'mineru2org', '책 전사', 'OCR 책', 'org2epub', '용어집 만들', 'diff-review'. This skill carries the tribal knowledge that run.sh and docs cannot: the remote GPU server dependency, the correction strategy, and the hard-won gotchas."
user_invocable: true
---

# scanbook — scanned book → EPUB pipeline

Repo: `~/repos/gh/memex-kb`. Book data + outputs live in the **nested private repo**
`scanpdf/` (Forgejo `glg-bot/scanpdf`). This skill is the operating surface for the
whole pipeline. `run.sh` covers the *local* commands; this file covers everything else
(remote GPU server, per-book config authoring, correction judgment, gotchas).

## The pipeline (5 stages)

```
PDF ──①MinerU VLM (REMOTE gpu2i)──▶ md + content_list.json + images/
    ──②mineru2org.py (post-process)─▶ clean .org (headings/footnotes/eq/images)
    ──③ox-epub──────────────────────▶ .epub (epubcheck 0 errors)
    QA: ④diff-review   config: ⑤scripts/corrections/<book>.json
```

- **Stage ① is the only non-local part** and is NOT fully expressible in `run.sh`.
- vision/Opus full transcription is **retired**. Do not spin parallel Opus agents to
  transcribe page images. MinerU does 95%; a *light* correction pass does the last 5%.

## ⚠️ Stage ① — remote MinerU server (the part run.sh can't own)

Inference runs on **gpu2i** (RTX 5080), a vLLM server serving `MinerU2.5-Pro` on port 30000.
This is **nixos 담당's domain** — a tmux session, not a memex-kb artifact.

```bash
# Is it alive?  (do this FIRST, every new session that needs to parse)
ssh gpu2i 'tmux ls | grep mineru-vllm'
# If missing → it is down. Ask GLG / nixos 담당 to bring it up. Do NOT try to start
# the vLLM yourself from here — wrong repo, wrong machine.
```

- `run.sh mineru-parse` **auto-creates the SSH tunnel** (`localhost:30000 → gpu2i:30000`)
  and only needs the server to be already running. Health = `curl -sf localhost:30000/health`
  (vLLM returns 200 with empty body — empty output is normal, the `-sf` exit code is truth).
- Client install (one-time, reproducible): `./run.sh mineru-setup` (uv sync; opencv-headless
  via pyproject override). The client (`mineru-client/`) is a thin http-client; the model
  weights live on gpu2i.
- A full 261-page book parses in **~3 minutes**. Run it backgrounded for big books.

```bash
# Stage ① — parse the whole book at once (faster than chapter-by-chapter)
./run.sh mineru-parse scanpdf/<book>001.pdf mineru-client/out
# → out/<book>001/vlm/{<book>001.md, _content_list.json, images/}
# Then MOVE the useful artifacts under scanpdf/ so they can be committed (Forgejo):
#   <book>001.md, _content_list.json, images/  →  scanpdf/work/<book>/mineru/
#   (DROP the heavy redundant *_origin.pdf / *_layout.pdf / *_model.json / *_middle.json)
```

## Stage ② — post-process: `scripts/mineru2org.py`

Deterministic structure-recovery converter (same input → byte-identical output).
Driven by the per-book config (`--corrections`) and `--content-list`.

```bash
python3 scripts/mineru2org.py scanpdf/work/<book>/mineru/<book>001.md \
  -o scanpdf/work/<book>/mineru/<book>-mineru.org \
  --corrections scripts/corrections/<book>.json \
  --content-list scanpdf/work/<book>/mineru/<book>001_content_list.json
# Emits: <book>-mineru.org + .changes.log (every transform, counted)
#                            + .candidates.log (uncertain corrections, NOT applied)
```

What it does (passes, all logged): surface (image `![]()`→`[[file:]]`, block `$$`→`\[\]`,
inline `$$`→`\(\)`, footnote `$^{n}$` + unicode superscript `⁵⁸²³`→`[fn:n]`); HTML cleanup
(`<details>`/mermaid removed, `<table>`→org table); **structure recovery** (chapter `*` /
section `**` merging number+title / subsection `***` / false-heading demotion / front-matter
+ TOC cut / preface kept); **footnote definitions** from `content_list.page_footnote` collected
into a `* 각주` section + orphan numeric paragraphs absorbed; corrections; epub header from config meta.

## Stage ⑤ — the per-book config (the real per-book work)

`scripts/corrections/<book>.json`. Copy `물질생명인간.json` as the template. Four blocks:

```jsonc
{
  "meta":   { title, author, date, language, publisher, subject, uid },   // → #+keywords for epub
  "structure": {
    "body_start": "<first chapter title text>",        // everything before = front matter, cut (preface kept)
    "chapters": [ { "num": "1장", "title": "..." }, ... ],
    "chapter_title_variants": { "<ocr/dash variant>": "<canonical>" },
    "back_matter": ["참고문헌", "찾아보기"]            // become * level; 찾아보기 internal headings dropped
  },
  "safe_regex":      [ { pattern, replace, desc } ],   // AUTO-applied. Must be PROVABLY safe (see strategy).
  "literal":         [ { from, to, desc } ],           // AUTO-applied exact-string fixes (incl. heading OCR, LaTeX).
  "candidate_regex": [ { pattern, desc } ]             // LOG ONLY (.candidates.log). Never edits the body.
}
```

To author it for a new book you must **read the parsed md** to learn that book's:
heading layout (chapter title as heading vs plain `N장`+title line), section numbering,
the recurring OCR misreads, and the index/reference layout.

## 🎯 Correction strategy (hard-won — do not regress this)

The book's central vocabulary is the highest-priority correction target: if a key term is
mangled in the index/glossary, it is mangled in the body too.

- **Blanket regex substitution is unsafe in general.** A misread char often collides with a
  real word: `않은`/`앉은`/`읽은` are valid; `앞의` is valid; `암` can be 暗/癌.
- **Safe rule** = "misread char + a particle that the misread char can NEVER take as a verb
  ending." e.g. `(앉|않|읽|얇)(이|의|과|와|도|만|에|으로…)` → `앎`. Exclude `은/을/음` (valid endings).
- **Everything ambiguous goes to `candidate_regex`** → `.candidates.log`, body untouched.
- **The general finisher = a LIGHT LLM correction pass** (you, reading context). MinerU laid
  down 95%; you fix the flagged 5% by reading the sentence. This is the lightweight replacement
  for "torturing Opus with full vision transcription."
- **Book-specific promotion**: only promote a candidate to `safe`/`literal` after verifying the
  whole class in that book (e.g. 물질생명인간 has no 暗/癌, so `암+조사`→`앎` was verified safe — 22
  occurrences all epistemic). Never copy that rule to another book blindly.
- **Oracle**: if a vision transcription exists for this book (`scanpdf/work/<book>/org/`), use it
  as the gold standard via `diff-review` to measure/drive corrections. New books have no oracle —
  rely on the candidates log + LLM pass + spot-checking page images.

## GPT structure review (when you want post-process improvements)

Throw an entwurf to **gpt-5.4** with `cwd: ~/repos/gh/memex-kb` asking it to diff the
post-processed org against the vision oracle (body region only) and classify the *structural*
gaps (headings, footnotes, tables, paragraphs) — not the char typos. It writes a review md.
This is how `mineru2org.py` grew from a string-replacer into a structure-recoverer.
Reference output: `scanpdf/work/물질생명인간/mineru/REVIEW-gpt.md` (conflict-type table + P0–P5 plan).

## Stage ③ — build + validate EPUB

```bash
./run.sh org2epub-build scanpdf/work/<book>/mineru/<book>-mineru.org
# thin wrapper → loads ~/repos/gh/ox-epub/ox-epub.el directly (no in-repo post-proc).
# Renders LaTeX → SVG (dvisvgm), embeds images, runs epubcheck (EPUBCHECK=1 default).
# Goal: 0 fatals / 0 errors / 0 warnings.
```

## 🐛 Gotchas (the삽질, so you don't repeat it)

- **`ltximg/` is a build cache.** If epubcheck reports a missing SVG (`RSC-007`), the cache is
  stale → `rm -rf <book-dir>/ltximg <book>.epub` and rebuild clean. `ltximg/` is gitignored.
- **Non-standard LaTeX breaks dvisvgm silently.** MinerU emits `\leqq`/`\geqq` (needs amssymb) →
  normalize to `\leq`/`\geq` via a `literal` rule. A failed equation = a missing SVG = epubcheck error.
- **Index (찾아보기) 자모 dividers** (ㄱㄴㄷ…) come out of MinerU as garbage headings (`# 7`, `# □`,
  `# 人`, `# $\Rightarrow$`). Inside 찾아보기 the converter drops all `#` headings. An equation-only
  heading like `** \(\Rightarrow\)` will also fail epub packaging — must be dropped, not kept.
- **Images are already inline** in the MinerU md at the right spot (`![](images/x.jpg)`), usually next
  to their `<그림 N>` caption. You only convert the syntax; `content_list` page_idx is a backup.
- **`content_list.json` is the structure SSOT**: `page_footnote` (footnote definitions, prefixed with
  the number), `page_number` (page_idx→printed page), `list` (TOC + list items → spot false headings),
  `table`, `image.sub_type` (text_image/flowchart/natural_image). Prefer it over guessing from md.
- **Footnote refs MinerU misses** (e.g. 7, 11) end up as "definition without ref" — logged, acceptable;
  flag for the human/LLM pass.
- **`#+options: ^:{}`** in the header is required so a stray `^` (superscripts, 10^{10}) doesn't break export.
- Use the EPUB header **`tex:dvisvgm`** so equations render to SVG (not MathML/png).

## ✅ Reproducibility

The set reproduces from committed files: from `<book>001.md` + `<book>.json` + `content_list.json`,
stages ②③ regenerate the org and epub deterministically (epubcheck 0). Each book gets a
`scanpdf/work/<book>/mineru/README.md` with the exact 3-command recipe + file inventory.
Verify before committing: delete org/epub/ltximg, re-run ②③, confirm epubcheck 0.

## 🚀 New book checklist (e.g. 물리학강의 — equation-heavy)

1. `ssh gpu2i 'tmux ls | grep mineru-vllm'` — server up? If not, ask GLG/nixos.
2. `pdfinfo`/`mutool info scanpdf/<book>001.pdf` — page count, sanity.
3. `./run.sh mineru-parse scanpdf/<book>001.pdf mineru-client/out` (background for big books).
4. Move artifacts → `scanpdf/work/<book>/mineru/` (md + content_list + images; drop heavy pdfs/jsons).
5. **Read the md** → write `scripts/corrections/<book>.json` (meta + structure.chapters + first corrections).
6. `python3 scripts/mineru2org.py …` → inspect `.changes.log` (heading/footnote counts sane?) and `.candidates.log`.
7. LLM light correction pass over candidates + remaining typos (read context; promote verified classes to config).
8. (optional) GPT structure review if quality is unclear or the book is structurally complex.
9. `./run.sh org2epub-build …` → fix any epubcheck error (see Gotchas) → 0 errors.
10. Update `scanpdf/work/<book>/mineru/README.md` and the repo `NEXT.md`. Commit memex-kb (tooling/config)
    + scanpdf (data); GLG approves push/tag.

> 물리학강의 specifically: **many equations + figures**. Expect `image.sub_type == text_image` math
> crops. Per GPT review (P4), low-confidence `text_image` OCR text should be *suppressed/isolated*
> (don't dump it into body) — keep the image, drop the noisy auto-OCR. Extend `mineru2org.py` if needed.

## Where the durable facts live (not docs that rot)

- This skill = how to operate the pipeline.
- `NEXT.md` = the volatile next step.
- `scanpdf/work/<book>/mineru/README.md` = per-book reproduce recipe + inventory.
- `scripts/corrections/<book>.json` = per-book structure + correction SSOT.
- `CHANGELOG.md` / commit history = what changed when.

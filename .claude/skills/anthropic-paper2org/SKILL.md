---
name: anthropic-paper2org
description: "Convert Anthropic Distill-style transformer-circuits.pub papers into reproducible Org archives, then export them to HTML and acmart PDF. Preserves <d-math> LaTeX source, org-cite citations, footnotes, static PNG figures, and replaces interactive JS figures with captions plus source links. This is not a general HTML-to-Org converter; use it only for Anthropic Distill papers such as J-space / jacobian-lens. Triggers: paper2org, transformer-circuits, Anthropic paper to Org, J-space paper, jacobian-lens, Distill paper conversion, Org HTML roundtrip."
user_invocable: true
---

# anthropic-paper2org — Anthropic Distill HTML paper → Org / HTML / PDF

Repo: `~/repos/gh/memex-kb`.

Runtime source of truth:

- `scripts/anthropic_paper_to_org.py` — capture and Org assembly
- `scripts/paper_build.el` — acmart PDF build helper
- `run.sh` — public command surface
- `NEXT.md` — short-lived roadmap / handoff state

This skill records the **proven command set and validation rules**. Do not expand it into a general HTML converter.

## Scope

Supported input:

- Anthropic Distill-style papers on `transformer-circuits.pub`
- Pages with `<d-article>`, `<d-math>`, `<d-cite>`, and `<d-footnote>`

Out of scope:

- General HTML → Org conversion
- Recreating JavaScript interactive figures inside Org
- Writing commentary or interpretation of the paper

If `_isolate()` cannot find `<d-article>`, stop instead of broadening the parser.

## Proven pipeline

```text
fetch
  → isolate <d-article>
  → strip visual table-of-contents thumbnails
  → protect Distill tags as sentinels
  → pandoc HTML → Org skeleton
  → restore math / citations / footnotes
  → fix image paths, heading levels, figure references
  → assemble web Org and optional acmart Org
```

Key rules:

- Use `pandoc --wrap=none` while converting protected HTML to Org; wrapped sentinels break restoration.
- Preserve `<d-math>` contents as LaTeX source:
  - inline: `\(...\)`
  - display: `\[...\]`
- Convert `<d-cite key="a,b">` to `[cite:@a;@b]`.
- Convert `<d-footnote>` to inline Org footnotes, after protecting nested math/citations.
- Lift original heading IDs into `CUSTOM_ID` so source anchors survive.
- Convert static image links to `[[file:png/...]]`.
- Replace non-image interactive figures with caption text plus a live source link.

## Capture command — `paper2org`

```bash
./run.sh paper2org https://transformer-circuits.pub/2026/workspace/index.html \
  --name jspace --fetch
```

Default output:

```text
out/anthropic-paper/jspace/
├── jspace.org
├── bibliography.bib
├── paper.html
└── png/
```

Use `--outdir DIR` to write somewhere else:

```bash
./run.sh paper2org "$URL" --name jspace --outdir "$PWD/papers/anthropic" --fetch
```

Expected J-space capture baseline:

- headings: 77
- inline math: 230
- display math: 7
- citations: 155
- footnotes: 9
- embedded static images: 10
- interactive figure placeholders: 84
- leftover sentinels / Distill tags: 0

## HTML export — `paper2org-html`

Production HTML uses Pandoc citeproc:

```bash
./run.sh paper2org-html https://transformer-circuits.pub/2026/workspace/index.html \
  --name jspace
```

Equivalent export step inside the paper directory:

```bash
pandoc -f org -t html5 -s \
  --citeproc \
  --bibliography=bibliography.bib \
  --mathjax \
  -o jspace.html jspace.org
```

Output:

```text
out/anthropic-paper/jspace/jspace.html
```

Properties of the proven HTML path:

- Parses `[cite:@key]` from Org.
- Renders citations as author-year spans.
- Renders a CSL bibliography into the `References` section.
- Renders math through MathJax.
- Keeps static image references under `png/`.
- Requires Pandoc only; no Emacs or TeX Live.

Required HTML validation for J-space:

```bash
python - <<'PY'
from pathlib import Path
html = Path('out/anthropic-paper/jspace/jspace.html').read_text(errors='ignore')
print('raw [cite: count =', html.count('[cite:'))
print('csl-entry count =', html.count('csl-entry'))
print('citation span count =', html.count('<span class="citation"'))
print('png refs =', html.count('png/'))
print('spot-check =', 'Block 1995' in html and 'Weiskrantz 1986' in html)
PY
```

Expected:

- raw `[cite:` count: `0`
- `csl-entry` count: `173`
- citation spans: about `120`
- PNG references: `10`
- spot-check includes `Block 1995` and `Weiskrantz 1986`

## PDF export — `paper2org-pdf`

```bash
./run.sh paper2org-pdf https://transformer-circuits.pub/2026/workspace/index.html \
  --name jspace
```

Output:

```text
out/anthropic-paper/jspace/jspace.acmart.pdf
```

What the acmart bridge does:

- Generates `<name>.acmart.org` beside the web Org file.
- Uses `#+LATEX_CLASS: acmart` with `[manuscript, nonacm]`.
- Generates `\title`, all authors, fixed `Anthropic` affiliations, and `\maketitle`.
- Converts `[cite:@a;@b]` to natbib `\cite{a,b}`.
- Adds `\bibliographystyle{ACM-Reference-Format}` and `\bibliography{bibliography}`.
- Sets image width to `\linewidth` with `keepaspectratio`.

Build environment:

- `run.sh` invokes `nix-shell` with Emacs and TeX Live `scheme-full`.
- The large TeX Live download is a one-time cache cost.

Expected J-space PDF baseline:

```bash
pdfinfo out/anthropic-paper/jspace/jspace.acmart.pdf | rg '^(Title|Pages|File size)'
```

- title: `Verbalizable Representations Form a Global Workspace in Language Models`
- pages: `93`
- authors in acmart Org: `16`
- natbib `\cite{...}` commands: `155`
- bibliography resolved by BibTeX

## Figure references

The published source contains unresolved `??` figure references. The converter restores figure references when the target figure exists in the source:

```text
[[#fig-x][??]] → Figure N
```

If the surrounding prose already says `Figure`, `Fig.`, or a list separator, only the number is inserted to avoid `Figure Figure N`.

J-space baseline:

- restored figure references: about `222`
- remaining `??`: references whose target figure is not present in the captured source

This restoration is applied before both HTML and PDF export.

## Interactive capsule — `paper2org-capsule`

The static `paper2org` path preserves the paper **text**. Distill papers also ship
**interactive JS figures** — `public/bundle.js` hydrates empty `<figure data-fignum=N>`
containers by fetching `parquet` / `json` data at runtime. The capsule path recovers that
**web-document liveness** into a local, reproducible mirror so a reader hydrates the paper
**offline, without crossing back to the original URL**.

```bash
./run.sh paper2org-capsule https://transformer-circuits.pub/2026/workspace/index.html \
  --name jspace
```

Output:

```text
out/anthropic-paper/jspace/capsule/
├── 2026/workspace/          # paper-specific: index.html, public/(bundle.js, per-figure css), data/, png/
├── anthropic-serve/         # shared runtime: distill template + KaTeX (generic across Distill papers)
└── capsule-manifest.json    # provenance + per-asset sha256/bytes/content-type
```

How it works (`scripts/paper_capsule_sweep.mjs`):

- Headless Chrome via **CDP directly** — no Playwright, no npm deps. Uses the flake's
  `nodejs_24` (global `WebSocket`/`fetch`/`crypto`) plus the host `google-chrome-stable`
  (override with `CHROME_BIN`).
- **load + full-scroll network sweep** enumerates every asset the runtime actually fetches
  (including runtime-assembled URLs like `data/lens-slice-ranks-s2/count_introspect_ranks/*.parquet`
  that static grep cannot find).
- Downloads **same-origin** assets preserving server paths; records everything in the manifest.
- Default `--serve-check` re-sweeps the local docroot and **asserts zero external requests**
  (the offline-completeness guarantee). Use `--no-verify` to skip.

Two-layer runtime (confirmed for J-space):

- `/anthropic-serve/` — generic shared runtime (distill template + KaTeX fonts). Same for
  every `transformer-circuits.pub` Distill paper.
- `/2026/workspace/` — paper-specific: `bundle.js` (jspace lens/jlens/modulation logic),
  per-figure `public/*/style.css`, and the `data/` + `png/` assets.

J-space capsule baseline:

- assets: **219 files / ~11.3 MB**
- sweep request count: about `220`
- `external_requests`: `[]`
- `failed_requests`: `[]`
- offline re-sweep: **PASS** (0 external, 0 4xx/5xx)

Serve + inspect manually:

```bash
python3 -m http.server 8877 --bind 127.0.0.1 \
  --directory out/anthropic-paper/jspace/capsule
# open http://localhost:8877/2026/workspace/index.html
```

Copyright: the capsule is Anthropic source material and stays under `out/` (gitignored).
Only the sweep logic (`scripts/paper_capsule_sweep.mjs`) and `run.sh` wiring are durable repo
assets. This must **not** be widened into a general web-archiver; it targets Distill papers.

## Interactive HTML from Org — `paper2org-interactive`

Proves GLG's thesis: **Org is the SSOT, and an interactive scientific document is generated with
`pandoc -f org` alone — no LaTeX, no Typst, no Quarto.** The paper's live JS figures hydrate offline
from the capsule.

```bash
./run.sh paper2org-interactive https://transformer-circuits.pub/2026/workspace/index.html \
  --name jspace
```

Pipeline:

1. `anthropic_paper_to_org.py --interactive` → `<name>.interactive.org`. Interactive (img-less) figures
   are protected **before** math/cite so their `<figcaption>` `<d-cite>`/`<d-math>` stay pristine, then
   restored as `#+begin_export html` blocks holding the **verbatim original `<figure data-fignum=N>`
   outerHTML**. The original head runtime (`distill.template`, `d3`, `bundle.js`, css) is emitted as
   single-line `#+HTML_HEAD_EXTRA:` tags (redirect/JSON-config inline scripts skipped). The
   `<d-article>`/`<d-contents>` wrapper is itself an Org raw block — so no pandoc template file is needed.
2. If the capsule is missing, it is built first (`paper2org-capsule`).
3. `pandoc -f org -t html5 -s --citeproc --bibliography=bibliography.bib --katex=/anthropic-serve/katex/`
   writes `<name>.interactive.html` **inside the capsule tree** at the paper's original URL path
   (`capsule/2026/workspace/jspace.interactive.html`). Local KaTeX (not the MathJax CDN) keeps external
   requests at zero and matches the paper's own math engine.

Serve and open:

```bash
cd out/anthropic-paper/jspace/capsule && python3 -m http.server 8877
# open http://localhost:8877/2026/workspace/jspace.interactive.html
```

J-space interactive baseline (proven):

- raw figure export blocks: `84` (== source interactive figures == exported `figure[data-fignum]`)
- HTML_HEAD_EXTRA: `11` (10 original runtime script/link tags + 1 layout reset `<style>`)
- browser: **external requests 0, 4xx/5xx 0** (favicon excepted), **39 parquet fetched locally**,
  math via local KaTeX, no console errors, prose column full width (`d-article` ≈ viewport).

Design notes / SSOT terminology (per GPT review):

- SSOT = `interactive.org` (structure/placement) + `capsule-manifest.json` (runtime bytes/provenance).
  The capsule is a **resource bundle**, not the SSOT.
- Round-trip that matters = `original interactive HTML → Org capture → pandoc export → offline hydrate`.
  Lossless `html → org` reverse parsing of raw blocks is **not** a v1 requirement.
- Prose layout: pandoc's default `body{max-width:36em}` (≈576px) traps distill's `d-article` grid and
  clips the prose column. The converter appends a final `#+HTML_HEAD_EXTRA` reset `<style>`
  (`_INTERACTIVE_RESET_STYLE`) that removes only the document-width constraint and returns the viewport
  width to the grid — distill grid/figure CSS is left intact. This keeps the "Org-only, no template" path.
- Keep raw figure `outerHTML` verbatim — do not rewrite figcaption or mount `div` classes (mount-class
  mismatch is the main hydration risk). Do not send raw DOM into the acmart PDF path.
- Math must stay local: use `--katex=/anthropic-serve/katex/` (capsule KaTeX), never plain `--mathjax`
  (it injects a jsdelivr CDN script and breaks the external-requests-zero guarantee).

## jacobian-lens consumer workflow

For `~/repos/gh/jacobian-lens`, the consumer-facing procedure belongs in that repo's `AGENTS.md`. The division of responsibility is:

- `memex-kb`: conversion logic and reproducible commands
- `jacobian-lens`: stored paper artifacts near the companion code

**Protect the destination first.** The consumer writes into a tracked git repo, and the artifacts are
Anthropic source material (paper text, PNGs, the ~13 MB capsule). Before running anything, gitignore them:

```bash
cd ~/repos/gh/jacobian-lens
grep -qxF 'papers/anthropic/' .gitignore || echo 'papers/anthropic/' >> .gitignore
```

Then run from the repo root:

```bash
MEMEX_KB="${MEMEX_KB:-$HOME/repos/gh/memex-kb}"
URL="https://transformer-circuits.pub/2026/workspace/index.html"
OUT="$PWD/papers/anthropic"

# static archive (Org SSOT + HTML + acmart PDF)
"$MEMEX_KB/run.sh" paper2org       "$URL" --name jspace --outdir "$OUT" --fetch
"$MEMEX_KB/run.sh" paper2org-html  "$URL" --name jspace --outdir "$OUT"
"$MEMEX_KB/run.sh" paper2org-pdf   "$URL" --name jspace --outdir "$OUT"

# interactive: offline-hydrating capsule + Org-derived interactive HTML (the live figures)
"$MEMEX_KB/run.sh" paper2org-capsule     "$URL" --name jspace --outdir "$OUT"
"$MEMEX_KB/run.sh" paper2org-interactive "$URL" --name jspace --outdir "$OUT"
```

Expected destination layout:

```text
papers/anthropic/jspace/
├── jspace.org                 # static archive (SSOT for text/math/cite)
├── jspace.acmart.pdf          # ArXiv-style PDF
├── jspace.html                # static HTML (citations + math)
├── jspace.interactive.org     # interactive SSOT (raw figure blocks + head runtime)
├── bibliography.bib
├── paper.html
├── png/
└── capsule/                   # offline runtime bundle (Anthropic assets; do NOT commit)
    ├── anthropic-serve/…       # distill template + KaTeX (shared runtime)
    └── 2026/workspace/
        ├── jspace.interactive.html   # ← open this to see the live figures offline
        ├── public/ data/ png/ …
        └── capsule-manifest.json
```

View the interactive document (no boundary crossing, no external requests):

```bash
cd papers/anthropic/jspace/capsule && python3 -m http.server 8877
# open http://localhost:8877/2026/workspace/jspace.interactive.html
```

Consumer validation:

- `jspace.org`, `bibliography.bib`, `png/` exist; `jspace.acmart.pdf` has 93 pages; `jspace.html` has `csl-entry`.
- `capsule/capsule-manifest.json` shows `external_requests: []` and `failed_requests: []`.
- `jspace.interactive.html` under the capsule tree opens and hydrates figures with **zero external requests**.
- Sentinel check `rg 'ZZ(MB|MI|CI|FN)[0-9]+ZZ|<d-[a-z]+'` applies to **`jspace.org` only** — the
  interactive Org legitimately contains `<d-…>` custom elements inside raw figure blocks.

Public repo safety:

- Do not add private handoff notes, secrets, tokens, or local-only details to tracked files.
- Preserve source links and provenance.
- Keep `papers/anthropic/` gitignored; commit generated paper artifacts only when explicitly requested.

## Copyright and artifact policy

The paper text and figures are Anthropic source material.

- Do not commit generated paper artifacts to `memex-kb`.
- `out/anthropic-paper/` is gitignored.
- The converter and instructions are the durable repo assets.
- Generated Org / HTML / PDF / PNG files are reproducible local artifacts unless a target repo explicitly decides to store them.

## Quick validation checklist

After a full J-space run:

```bash
# Org
rg -n 'ZZ(MB|MI|CI|FN)[0-9]+ZZ|<d-[a-z]+' out/anthropic-paper/jspace/jspace.org || true

# HTML
python - <<'PY'
from pathlib import Path
html = Path('out/anthropic-paper/jspace/jspace.html').read_text(errors='ignore')
assert html.count('[cite:') == 0
assert html.count('csl-entry') == 173
assert html.count('png/') == 10
assert 'Block 1995' in html and 'Weiskrantz 1986' in html
print('HTML OK')
PY

# PDF
pdfinfo out/anthropic-paper/jspace/jspace.acmart.pdf | rg '^(Title|Pages|File size)'
```

A run is acceptable when:

- Org has no leftover sentinels / Distill tags.
- HTML citations and bibliography are rendered.
- HTML math and images survive.
- PDF has 93 pages and resolved bibliography.

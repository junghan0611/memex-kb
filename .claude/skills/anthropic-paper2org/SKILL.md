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

## jacobian-lens consumer workflow

For `~/repos/gh/jacobian-lens`, the consumer-facing procedure belongs in that repo's `AGENTS.md`. The division of responsibility is:

- `memex-kb`: conversion logic and reproducible commands
- `jacobian-lens`: stored paper artifacts near the companion code

Run from the `jacobian-lens` repo root:

```bash
cd ~/repos/gh/jacobian-lens
MEMEX_KB="${MEMEX_KB:-$HOME/repos/gh/memex-kb}"
URL="https://transformer-circuits.pub/2026/workspace/index.html"
OUT="$PWD/papers/anthropic"

"$MEMEX_KB/run.sh" paper2org "$URL" --name jspace --outdir "$OUT" --fetch
"$MEMEX_KB/run.sh" paper2org-pdf "$URL" --name jspace --outdir "$OUT"
"$MEMEX_KB/run.sh" paper2org-html "$URL" --name jspace --outdir "$OUT"
```

Expected destination layout:

```text
papers/anthropic/jspace/
├── jspace.org
├── jspace.acmart.org
├── jspace.acmart.pdf
├── jspace.html
├── bibliography.bib
├── paper.html
└── png/
```

Consumer validation:

- `jspace.org` exists
- `bibliography.bib` exists
- `png/` exists and contains the static figures
- `jspace.acmart.pdf` exists and has 93 pages
- `jspace.html` exists and has `csl-entry` bibliography entries
- leftover sentinels / Distill tags in Org: 0

Public repo safety:

- Do not add private handoff notes, secrets, tokens, or local-only details to tracked files.
- Preserve source links and provenance.
- Commit generated paper artifacts only when explicitly requested.

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

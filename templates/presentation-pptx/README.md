# org2pptx — Org-mode → PowerPoint Template Injector

Write presentation content in **org-mode**, inject it into any **pptx template**
while preserving the original design (backgrounds, logos, fonts, layouts).

## Architecture

```
[content.org]  →  [org2pptx.py]  →  [output.pptx]
  (content)       orgparse parse       ↑
                  python-pptx inject  [template.pptx]
```

**Why not pandoc?** `pandoc --reference-doc` fails when template layouts use
non-English names (e.g. Korean `2_제목만` instead of `Title and Content`).
All layouts fall back to defaults, losing backgrounds and logos entirely.

**Why org-mode?** It's the meta-format — plain text, version-controllable,
Emacs-native, and trivially parseable. Content lives in org; styling lives
in the pptx template.

## Quick Start

```bash
# 1. Copy this template to your project
cp -r templates/presentation-pptx/ my-presentation/
cd my-presentation/

# 2. Place your pptx template
cp /path/to/company-template.pptx template.pptx

# 3. Edit template.org (or rename to your-topic.org)
#    - Adjust SLIDE_INDEX to match your template's slide count
#    - Fill in content under each heading

# 4. Run
nix-shell -p python312Packages.orgparse python312Packages.python-pptx \
  --run "python3 org2pptx.py template.org -t template.pptx"

# 5. Open output
libreoffice --impress template.pptx
# or: open template.pptx  (macOS)
```

## Org Conventions

Each **level 1 heading** maps to one slide:

```org
* Slide Title
:PROPERTIES:
:SLIDE_INDEX: 2
:LAYOUT: Title and Content
:END:

** Sub-section A
- Bullet 1
- Bullet 2

** Data Table
| Column 1 | Column 2 |
|----------+----------|
| Value A  | Value B  |
```

### Properties Reference

| Property | Required | Description |
|----------|----------|-------------|
| `SLIDE_INDEX` | ✅ | Template slide number (1-based) |
| `LAYOUT` | ❌ | Informational label (not used by injector) |
| `SKIP` | ❌ | `true` = keep template slide unchanged |
| `REPLACE_TEXT` | ❌ | `old=new` text replacement. Multiple: `old1=new1;;old2=new2` |

### Content Elements

| Org syntax | PPTX output |
|------------|-------------|
| `- item` | • Bullet point (TextBox) |
| `\| col \| col \|` | Table shape |
| Level 2 heading | ▶ Sub-section title (bold) |
| Level 1 body text | Direct content (no sub-section header) |

### SKIP + REPLACE_TEXT

For title/ending slides that should keep the template design but need
small text changes (e.g. presenter name, date):

```org
* Title Slide
:PROPERTIES:
:SLIDE_INDEX: 1
:SKIP: true
:REPLACE_TEXT: Presenter Name=Jane Doe;;2024=2025
:END:
```

## Removing Decoration Shapes

Some templates have decorative shapes (colored rectangles with duplicated
slide titles) that overlap injected content. Use `--remove-decorations`:

```bash
python3 org2pptx.py slides.org -t template.pptx -r "직사각형"
```

This removes non-placeholder shapes whose name starts with the given prefix.
You can specify multiple prefixes: `-r "직사각형,Rectangle"`.

To discover shape names in your template:

```python
from pptx import Presentation
prs = Presentation("template.pptx")
for i, sldId in enumerate(prs.slides._sldIdLst):
    slide = prs.slides.part.related_slide(sldId.rId)
    print(f"--- Slide {i+1} ---")
    for shape in slide.shapes:
        print(f"  {shape.name}: placeholder={shape.is_placeholder}")
```

## Dependencies

- **Python 3.10+**
- **orgparse** — org-mode parser
- **python-pptx** — PowerPoint manipulation

### NixOS

```bash
nix-shell -p python312Packages.orgparse python312Packages.python-pptx \
  --run "python3 org2pptx.py ..."
```

### pip

```bash
pip install orgparse python-pptx
python3 org2pptx.py ...
```

## CLI Reference

```
usage: org2pptx.py [-h] --template FILE [-o FILE] [-r PREFIXES] org_file

positional arguments:
  org_file              Input org file

options:
  -t, --template FILE   PowerPoint template file (.pptx) [required]
  -o, --output FILE     Output pptx path (default: <org_stem>.pptx)
  -r, --remove-decorations PREFIXES
                        Comma-separated shape name prefixes to remove
```

## Starting a New Project

```bash
# From memex-kb root
cp -r templates/presentation-pptx/ projects/my-presentation/
cd projects/my-presentation/

# Inspect your template
nix-shell -p python312Packages.python-pptx --run "python3 -c \"
from pptx import Presentation
prs = Presentation('template.pptx')
for i, sldId in enumerate(prs.slides._sldIdLst):
    slide = prs.slides.part.related_slide(sldId.rId)
    layout = slide.slide_layout.name
    print(f'Slide {i+1} ({layout})')
    for ph in slide.placeholders:
        print(f'  ph[{ph.placeholder_format.idx}]: {ph.text[:60]}')
\""

# → Use the output to set SLIDE_INDEX values in your org file
```

## Limitations

- **Images**: Not yet supported. Workaround: place images directly in the
  template and use SKIP slides, or add via LibreOffice after generation.
- **Font sizes**: Hardcoded (13pt bullets, 16pt sub-section titles).
  Override planned via `:FONT_SIZE:` property.
- **Multi-column layouts**: Not supported. Use the template's built-in
  layouts or add columns manually.
- **Slide creation**: Cannot add new slides beyond what the template has.
  The template must already contain the right number of slides.

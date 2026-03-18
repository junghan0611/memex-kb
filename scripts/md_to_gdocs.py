#!/usr/bin/env python3
"""
md_to_gdocs.py — Markdown → Google Docs 붙여넣기용 DOCX 변환기

파이프라인: MD → Org-mode → ODT (Emacs ox-odt) → DOCX (LibreOffice)

이 경로를 쓰는 이유:
1. Org의 #+BEGIN_SRC 블록이 ODT에서 OrgSrcBlock 스타일로 변환됨
2. reference.odt의 Preformatted_20_Text 스타일에 Courier New가 지정됨
3. ASCII 아트가 모노스페이스로 정확히 렌더링됨
4. 테이블, 헤딩, 리스트 모두 ODT 스타일로 깔끔하게 처리됨

사용법:
    python scripts/md_to_gdocs.py INPUT.md [-o OUTPUT.docx] [--open] [--keep]
    python scripts/md_to_gdocs.py README.md --open  # 변환 + LibreOffice로 열기

단계별:
    --step org    → Org까지만 (디버깅)
    --step odt    → ODT까지만
    --step docx   → DOCX까지 (기본값)
"""

import argparse
import logging
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# 프로젝트 루트
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
PROPOSAL_DIR = PROJECT_DIR / "proposal-pipeline"
EXPORT_EL = PROPOSAL_DIR / "proposal-export.el"
REFERENCE_ODT = PROPOSAL_DIR / "templates" / "reference.odt"


# ── MD → Org 변환 ───────────────────────────────────────────────────

def md_to_org(md_path: Path) -> str:
    """Markdown을 Org-mode 텍스트로 변환한다.

    제안서용 md_to_org.py와 달리 HWPX 레벨/글머리표를 넣지 않는다.
    범용 문서에 맞게 깔끔하게 변환한다.
    """
    content = md_path.read_text(encoding='utf-8')
    lines = content.split('\n')
    org_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 빈 줄
        if not line.strip():
            org_lines.append('')
            i += 1
            continue

        # HTML 주석 스킵
        if re.match(r'^\s*<!--.*?-->\s*$', line):
            i += 1
            continue
        if re.match(r'^\s*<!--', line) and '-->' not in line:
            i += 1
            while i < len(lines) and '-->' not in lines[i]:
                i += 1
            i += 1
            continue

        # 구분선 → org 수평선
        if re.match(r'^-{3,}\s*$', line.strip()):
            org_lines.append('-----')
            i += 1
            continue

        # 헤딩
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            text = _clean_md_inline(text)
            stars = '*' * level
            org_lines.append(f'{stars} {text}')
            org_lines.append('')
            i += 1
            continue

        # 코드 블록 → #+BEGIN_SRC
        code_match = re.match(r'^```(\w*)(.*)$', line)
        if code_match:
            lang = code_match.group(1) or ''
            code_lines = []
            i += 1
            while i < len(lines) and not re.match(r'^```\s*$', lines[i]):
                code_lines.append(lines[i])
                i += 1
            if lang:
                org_lines.append(f'#+BEGIN_SRC {lang}')
            else:
                org_lines.append('#+BEGIN_EXAMPLE')
            org_lines.extend(code_lines)
            if lang:
                org_lines.append('#+END_SRC')
            else:
                org_lines.append('#+END_EXAMPLE')
            org_lines.append('')
            i += 1  # 닫는 ```
            continue

        # 테이블
        if line.strip().startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            org_table = _convert_table(table_lines)
            org_lines.extend(org_table)
            org_lines.append('')
            continue

        # 블록쿼트
        if line.strip().startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                text = re.sub(r'^>\s?', '', lines[i])
                quote_lines.append(text)
                i += 1
            org_lines.append('#+BEGIN_QUOTE')
            org_lines.extend(quote_lines)
            org_lines.append('#+END_QUOTE')
            org_lines.append('')
            continue

        # 일반 텍스트 (리스트 포함 — 그대로 유지)
        org_lines.append(_clean_md_inline(line))
        i += 1

    return '\n'.join(org_lines)


def _clean_md_inline(text: str) -> str:
    """Markdown 인라인 서식을 Org 서식으로 변환."""
    # **볼드** → *볼드*
    text = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', text)
    # `인라인코드` → ~인라인코드~
    text = re.sub(r'`([^`]+)`', r'~\1~', text)
    # [링크](url) → [[url][링크]]
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'[[\2][\1]]', text)
    # ![alt](img) → [[file:img]]
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'[[file:\2]]', text)
    return text


def _convert_table(lines: list) -> list:
    """Markdown 테이블을 Org 테이블로 변환."""
    result = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        # 구분선 (|---|---|)
        if re.match(r'^\|[\s\-:]+\|$', stripped) or re.match(r'^\|(\s*-+\s*\|)+\s*$', stripped):
            # Org 구분선
            cells = stripped.split('|')
            ncols = len([c for c in cells if c.strip()])
            result.append('|' + '+'.join(['-' * 10] * ncols) + '|')
        else:
            # 셀 내부 인라인 서식 변환
            result.append(_clean_md_inline(stripped))
    return result


# ── Org → ODT (Emacs batch) ─────────────────────────────────────────

def org_to_odt(org_path: Path) -> Path:
    """Emacs batch로 Org → ODT 변환.

    reference.odt 스타일을 적용하여 모노스페이스 코드블록을 보장한다.
    """
    ref_odt = str(REFERENCE_ODT) if REFERENCE_ODT.exists() else ""

    elisp = f'''(progn
      (require 'ox-odt)
      (setq org-export-with-toc nil)
      (setq org-export-with-author nil)
      (setq org-export-headline-levels 6)
      (setq org-export-use-babel nil)
      (setq org-export-with-broken-links t)
      {f'(setq org-odt-styles-file "{ref_odt}")' if ref_odt else ''}
      (find-file "{org_path}")
      (org-odt-export-to-odt))'''

    cmd = ["emacs", "--batch", "--eval", elisp]

    logger.info(f"Org → ODT: emacs --batch ...")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        logger.error(f"Emacs ODT 내보내기 실패:\n{result.stderr[-500:]}")
        sys.exit(1)

    odt_path = org_path.with_suffix('.odt')
    if not odt_path.exists():
        logger.error(f"ODT 파일이 생성되지 않았습니다: {odt_path}")
        sys.exit(1)

    logger.info(f"  → {odt_path}")
    return odt_path


# ── ODT → DOCX (LibreOffice) ────────────────────────────────────────

def odt_to_docx(odt_path: Path) -> Path:
    """LibreOffice로 ODT → DOCX 변환."""
    outdir = odt_path.parent

    cmd = [
        "libreoffice", "--headless", "--convert-to", "docx",
        "--outdir", str(outdir),
        str(odt_path),
    ]

    logger.info(f"ODT → DOCX: libreoffice --headless ...")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        logger.error(f"LibreOffice 변환 실패:\n{result.stderr[-500:]}")
        sys.exit(1)

    docx_path = odt_path.with_suffix('.docx')
    if not docx_path.exists():
        logger.error(f"DOCX 파일이 생성되지 않았습니다: {docx_path}")
        sys.exit(1)

    logger.info(f"  → {docx_path}")
    return docx_path


# ── 메인 파이프라인 ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Markdown → Google Docs용 DOCX 변환기 (MD → Org → ODT → DOCX)",
        epilog="예시: python scripts/md_to_gdocs.py README.md --open",
    )
    parser.add_argument("input", help="입력 파일 (MD 또는 Org)")
    parser.add_argument("-o", "--output", help="출력 파일 경로")
    parser.add_argument("--open", action="store_true", help="변환 후 LibreOffice로 열기")
    parser.add_argument("--keep", action="store_true", help="중간 파일(Org, ODT) 유지")
    parser.add_argument("--step", choices=["org", "odt", "docx"],
                        default="docx", help="어디까지 변환할지 (기본: docx)")

    args = parser.parse_args()
    input_path = Path(args.input).resolve()

    if not input_path.exists():
        logger.error(f"파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)

    # 작업 디렉토리
    work_dir = Path(tempfile.mkdtemp(prefix="md2gdocs_"))
    stem = input_path.stem

    # ── Step 1: MD → Org ────────────────────────
    if input_path.suffix.lower() in ('.md', '.markdown', '.mkd'):
        logger.info(f"[1/3] MD → Org: {input_path.name}")
        org_content = md_to_org(input_path)

        # Org 헤더 추가
        title = stem.replace('-', ' ').replace('_', ' ').title()
        header = f"""#+TITLE: {title}
#+OPTIONS: toc:nil author:nil num:t
#+STARTUP: overview
"""
        # reference.odt 스타일 사용
        if REFERENCE_ODT.exists():
            header += f"#+ODT_STYLES_FILE: {REFERENCE_ODT}\n"

        org_path = work_dir / f"{stem}.org"
        org_path.write_text(header + '\n' + org_content, encoding='utf-8')
        logger.info(f"  → {org_path}")
    elif input_path.suffix.lower() == '.org':
        org_path = work_dir / input_path.name
        import shutil
        shutil.copy2(input_path, org_path)
    else:
        logger.error(f"지원하지 않는 형식: {input_path.suffix}")
        sys.exit(1)

    if args.step == 'org':
        final = org_path
        _finish(final, args, work_dir)
        return

    # ── Step 2: Org → ODT ───────────────────────
    logger.info(f"[2/3] Org → ODT")
    odt_path = org_to_odt(org_path)

    if args.step == 'odt':
        final = odt_path
        _finish(final, args, work_dir)
        return

    # ── Step 3: ODT → DOCX ──────────────────────
    logger.info(f"[3/3] ODT → DOCX")
    docx_path = odt_to_docx(odt_path)

    final = docx_path
    _finish(final, args, work_dir)


def _finish(final: Path, args, work_dir: Path):
    """최종 파일 복사 및 정리."""
    # 출력 경로 결정
    if args.output:
        out = Path(args.output)
    else:
        out = Path(f"/tmp/{final.name}")

    import shutil
    shutil.copy2(final, out)
    logger.info(f"✅ 완료: {out} ({out.stat().st_size / 1024:.0f}KB)")
    logger.info(f"   LibreOffice에서 열고 → Ctrl+A → Ctrl+C → Google Docs에 Ctrl+V")

    if args.open:
        subprocess.Popen(
            ["xdg-open", str(out)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(f"   🌐 열었습니다.")

    # 중간 파일 정리
    if not args.keep:
        shutil.rmtree(work_dir, ignore_errors=True)
    else:
        logger.info(f"   중간 파일: {work_dir}")


if __name__ == "__main__":
    main()

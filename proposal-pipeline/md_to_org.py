#!/usr/bin/env python3
"""
Markdown → Org-mode 변환기 (HWPX 메타포맷 호환)

Google Docs에서 내보낸 Markdown 파일을 hwpx_to_org.py의 출력 형식과 호환되는
Org-mode 형식으로 변환합니다.

HWPX 템플릿 레벨 체계:
- Level 1 (*): 장 번호 (1., 2., 3.) - MD H1
- Level 2 (**): 절 번호 (1-1., 2-1., 2.1) - MD H2
- Level 3 (***): □ 소절, 2.1.1 등 - MD H3
- Level 4 (****): o 항목, (1), (2) 등 - MD H4
- Level 5 (*****): - 세부항목 - MD H5
- Level 5 (*****): - 세부 (H6은 후처리에서 L5로 통합) - MD H5/H6
- Level 7 (*******): <테이블 캡션>

사용법:
    python md_to_org.py 고퀄.md -o 고퀄.org
    python md_to_org.py *.md --output-dir output/
"""

import argparse
import logging
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class MdElement:
    """Markdown 요소 기본 클래스"""
    hwpx_idx: int = -1


@dataclass
class MdHeading(MdElement):
    """Markdown 헤딩"""
    level: int = 0          # MD 원본 레벨
    org_level: int = 0      # HWPX 호환 Org 레벨
    text: str = ""
    bullet_prefix: str = "" # HWPX 글머리표 접두어


@dataclass
class MdParagraph(MdElement):
    """Markdown 일반 문단"""
    text: str = ""


@dataclass
class MdTable(MdElement):
    """Markdown 테이블"""
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    title: str = ""
    is_guide: bool = False  # 작성요령 테이블 여부


@dataclass
class MdBlockquote(MdElement):
    """Markdown 블록쿼트 (그림 캡션 등)"""
    text: str = ""


@dataclass
class MdCodeBlock(MdElement):
    """Markdown 코드 블록"""
    language: str = ""
    content: str = ""


@dataclass
class MdDocument:
    """파싱된 Markdown 문서"""
    title: str = ""
    elements: List[MdElement] = field(default_factory=list)


def detect_hwpx_level(text: str, md_level: int) -> Tuple[int, str, str]:
    """헤딩 텍스트에서 HWPX 호환 레벨과 글머리표를 감지

    MD 레벨을 기본으로 사용하고, 텍스트 패턴으로 글머리표 접두어를 결정합니다.

    핵심 원칙:
    - MD H1 → Org Level 1 (장)
    - MD H2 → Org Level 2 (절)
    - MD H3 → Org Level 3 (□ 소절)
    - MD H4 → Org Level 4 (o 항목)
    - MD H5 → Org Level 5 (- 세부)
    - MD H6 → Org Level 6 (⋅ 상세)

    Returns:
        (org_level, bullet_prefix, cleaned_text)
    """
    text = text.strip()

    # 볼드 마크다운 제거 (**text**)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)

    # 글머리표 패턴 감지 및 제거
    bullet_prefix = ""
    cleaned_text = text

    # □ 글머리표
    match = re.match(r'^□\s*(.+)$', text)
    if match:
        bullet_prefix = '□ '
        cleaned_text = match.group(1)

    # o 글머리표
    elif re.match(r'^[oO○]\s+(.+)$', text):
        match = re.match(r'^[oO○]\s+(.+)$', text)
        bullet_prefix = 'o '
        cleaned_text = match.group(1)

    # (1), (가) 등 괄호 번호
    elif re.match(r'^\((\d+|[가-힣])\)\s*(.+)$', text):
        match = re.match(r'^\((\d+|[가-힣])\)\s*(.+)$', text)
        bullet_prefix = f'({match.group(1)}) '
        cleaned_text = match.group(2)

    # - 글머리표
    elif re.match(r'^[-–—]\s+(.+)$', text):
        match = re.match(r'^[-–—]\s+(.+)$', text)
        bullet_prefix = '- '
        cleaned_text = match.group(1)

    # ⋅ · 글머리표
    elif re.match(r'^[⋅·•]\s*(.+)$', text):
        match = re.match(r'^[⋅·•]\s*(.+)$', text)
        bullet_prefix = '·'
        cleaned_text = match.group(1)

    # <테이블 캡션>
    elif re.match(r'^<([^>]+)>$', text):
        # 테이블 캡션은 상위 레벨의 하위로 들어감
        return md_level + 1, '', text

    # MD 레벨에 따라 Org 레벨 결정
    # 기본 매핑: MD 레벨 = Org 레벨
    org_level = md_level

    # 글머리표가 없는 경우, MD 레벨에 맞는 기본 글머리표 추가
    if not bullet_prefix:
        bullet_map = {
            1: '',      # 장 번호는 그대로
            2: '',      # 절 번호는 그대로
            3: '□ ',   # 소절
            4: 'o ',   # 항목
            5: '- ',   # 세부
            6: '·',   # 상세 (후처리에서 L5로 통합)
        }

        # 숫자 번호 패턴 확인 (1., 2., 1-1., 2.1.1 등)
        # 이미 번호가 있으면 글머리표 추가 안함
        has_number = bool(re.match(r'^(\d+[\.-])+\d*\.?\s+', text))

        if not has_number and md_level in bullet_map:
            bullet_prefix = bullet_map[md_level]

    return org_level, bullet_prefix, cleaned_text


def parse_md_file(md_path: Path) -> MdDocument:
    """Markdown 파일을 파싱하여 구조화된 문서 객체 반환"""
    doc = MdDocument()

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    i = 0
    hwpx_idx = 0

    while i < len(lines):
        line = lines[i]

        # 빈 줄 스킵
        if not line.strip():
            i += 1
            continue

        # HTML 주석 제거 (<!-- tab-id: ... --> 등)
        if re.match(r'^\s*<!--.*?-->\s*$', line):
            i += 1
            continue
        # 여러 줄 HTML 주석
        if re.match(r'^\s*<!--', line) and '-->' not in line:
            i += 1
            while i < len(lines) and '-->' not in lines[i]:
                i += 1
            i += 1  # --> 줄 스킵
            continue

        # 구분선 (---) 스킵
        if re.match(r'^-{3,}$', line.strip()):
            i += 1
            continue

        # 헤딩 감지 (# ~ ######)
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            md_level = len(heading_match.group(1))
            text = heading_match.group(2).strip()

            # 첫 번째 H1은 문서 제목으로
            if md_level == 1 and not doc.title:
                doc.title = text

            # HWPX 호환 레벨 감지
            org_level, bullet_prefix, cleaned_text = detect_hwpx_level(text, md_level)

            elem = MdHeading(
                level=md_level,
                org_level=org_level,
                text=cleaned_text,
                bullet_prefix=bullet_prefix,
                hwpx_idx=hwpx_idx
            )

            # Google Docs TOC 중복 헤딩 제거:
            # 목차 항목 "# 2 . 제목"과 실제 헤딩 "# 2. 제목"이 연속 → 뒤의 것만 유지
            if doc.elements and isinstance(doc.elements[-1], MdHeading):
                prev = doc.elements[-1]
                if prev.level == md_level:
                    norm = lambda s: re.sub(r'\s+', '', s)
                    if norm(prev.text) == norm(cleaned_text):
                        logger.info(f'TOC 중복 헤딩 제거: "{prev.text}" (idx {prev.hwpx_idx})')
                        doc.elements[-1] = elem
                        hwpx_idx += 1
                        i += 1
                        continue

            doc.elements.append(elem)
            hwpx_idx += 1
            i += 1
            continue

        # 코드 블록 (```)
        code_match = re.match(r'^```(\w*)$', line)
        if code_match:
            language = code_match.group(1)
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            elem = MdCodeBlock(language=language, content='\n'.join(code_lines), hwpx_idx=hwpx_idx)
            doc.elements.append(elem)
            hwpx_idx += 1
            i += 1  # 닫는 ``` 스킵
            continue

        # 테이블 감지 (| 로 시작)
        if line.strip().startswith('|'):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1

            table = parse_md_table(table_lines, hwpx_idx)
            if table:
                doc.elements.append(table)
                hwpx_idx += 1
            continue

        # 블록쿼트 (> 로 시작)
        if line.strip().startswith('>'):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                # > 제거
                quote_text = re.sub(r'^>\s*', '', lines[i])
                quote_lines.append(quote_text)
                i += 1

            elem = MdBlockquote(text='\n'.join(quote_lines), hwpx_idx=hwpx_idx)
            doc.elements.append(elem)
            hwpx_idx += 1
            continue

        # 이미지 줄 감지 (![alt](path) 또는 ![alt](path) <캡션>)
        if line.strip().startswith('!['):
            # 다음 줄이 <캡션>이면 합쳐서 처리
            img_text = line.strip()
            i += 1
            if i < len(lines) and re.match(r'^<[^>]+>\s*$', lines[i].strip()):
                img_text += '   ' + lines[i].strip()
                i += 1
            img_text = clean_md_text(img_text)
            if img_text:
                elem = MdParagraph(text=img_text, hwpx_idx=hwpx_idx)
                doc.elements.append(elem)
                hwpx_idx += 1
            continue

        # 독립 <캡션> 줄 (이미지 없이 남은 경우)
        if re.match(r'^<[^>]+>\s*$', line.strip()):
            caption = line.strip()[1:-1]
            elem = MdParagraph(text=f"#+CAPTION: {caption}", hwpx_idx=hwpx_idx)
            doc.elements.append(elem)
            hwpx_idx += 1
            i += 1
            continue

        # MD 리스트 항목 감지 (- item, * item, 1. item 등)
        list_match = re.match(r'^(\s*)([-*+]|\d+\.)\s+', line)
        if list_match:
            list_lines = [line]
            i += 1
            while i < len(lines):
                next_line = lines[i]
                if not next_line.strip():
                    break
                # 다른 요소 시작이면 리스트 종료
                if (next_line.strip().startswith('#') or
                    next_line.strip().startswith('|') or
                    next_line.strip().startswith('>') or
                    next_line.strip().startswith('```') or
                    next_line.strip().startswith('![') or
                    re.match(r'^<[^>]+>\s*$', next_line.strip()) or
                    re.match(r'^-{3,}$', next_line.strip()) or
                    re.match(r'^\s*<!--', next_line)):
                    break
                list_lines.append(next_line)
                i += 1

            # 각 리스트 항목을 줄바꿈으로 연결 (합치지 않음)
            text = '\n'.join(list_lines).strip()
            if text:
                elem = MdParagraph(text=text, hwpx_idx=hwpx_idx)
                doc.elements.append(elem)
                hwpx_idx += 1
            continue

        # 일반 문단
        para_lines = [line]
        i += 1
        while i < len(lines):
            next_line = lines[i]
            # 빈 줄이면 문단 종료
            if not next_line.strip():
                break
            # 다른 요소 시작이면 문단 종료
            if (next_line.strip().startswith('#') or
                next_line.strip().startswith('|') or
                next_line.strip().startswith('>') or
                next_line.strip().startswith('```') or
                next_line.strip().startswith('![') or
                re.match(r'^<[^>]+>\s*$', next_line.strip()) or
                re.match(r'^-{3,}$', next_line.strip()) or
                re.match(r'^\s*<!--', next_line) or
                re.match(r'^(\s*)([-*+]|\d+\.)\s+', next_line)):
                break
            para_lines.append(next_line)
            i += 1

        text = ' '.join(para_lines).strip()
        if text:
            elem = MdParagraph(text=text, hwpx_idx=hwpx_idx)
            doc.elements.append(elem)
            hwpx_idx += 1

    return doc


def parse_md_table(lines: List[str], hwpx_idx: int) -> Optional[MdTable]:
    """Markdown 테이블 라인을 파싱"""
    if len(lines) < 2:
        return None

    table = MdTable(hwpx_idx=hwpx_idx)

    # 첫 줄: 헤더
    header_line = lines[0]
    table.headers = parse_table_row(header_line)

    # 두 번째 줄: 구분선 (|------|------|) - 스킵
    # 나머지: 데이터 행
    for line in lines[2:]:
        row = parse_table_row(line)
        if row:
            table.rows.append(row)

    # 작성요령 테이블 감지
    all_text = ' '.join(table.headers) + ' '.join(' '.join(r) for r in table.rows)
    if re.search(r'작성\s*요령|작성요령', all_text[:200]):
        table.is_guide = True

    return table


def parse_table_row(line: str) -> List[str]:
    """테이블 행 파싱 (| cell1 | cell2 | → ['cell1', 'cell2'])"""
    # 앞뒤 | 제거
    line = line.strip()
    if line.startswith('|'):
        line = line[1:]
    if line.endswith('|'):
        line = line[:-1]

    cells = [cell.strip() for cell in line.split('|')]
    return cells


def convert_md_images(text: str) -> str:
    """Markdown 이미지를 Org-mode 형식으로 변환

    패턴 1: ![alt](path)   <캡션>
      → #+CAPTION: 캡션\n[[file:path]]

    패턴 2: ![alt](path)
      → [[file:path]]

    한 줄에 여러 이미지가 있을 수 있음 (tab08 등)
    """
    # 패턴 1: 이미지 + 캡션
    def replace_img_caption(m):
        path = m.group(2)
        caption = m.group(3).strip()
        # 앞뒤에 텍스트가 있을 수 있으므로 줄바꿈으로 분리
        return f"\n#+CAPTION: {caption}\n[[file:{path}]]\n"

    # 패턴: ![alt](path)   <캡션 텍스트>
    # 캡션 안에 > 문자가 있을 수 있으므로 마지막 >까지 매칭
    text = re.sub(
        r'!\[([^\]]*)\]\(([^)]+)\)\s*<(.+)>',
        replace_img_caption,
        text
    )

    # 패턴 2: 남은 이미지 (캡션 없음)
    text = re.sub(
        r'!\[([^\]]*)\]\(([^)]+)\)',
        r'\n[[file:\2]]\n',
        text
    )

    # 독립 줄의 <캡션> 패턴 → #+CAPTION (이미지 다음 줄에 캡션만 있는 경우)
    text = re.sub(
        r'\n<([^>]+)>\s*\n',
        r'\n#+CAPTION: \1\n',
        text
    )

    # 연속 줄바꿈 정리
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def clean_md_text(text: str) -> str:
    """Markdown 문법 정리 (볼드, 이탤릭, 이미지 등)"""
    # MD 이미지 → Org 이미지
    text = convert_md_images(text)
    # **볼드** → 볼드
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    # *이탤릭* → 이탤릭
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    # <br> → 줄바꿈
    text = re.sub(r'<br\s*/?>', '\n', text)
    # 특수 문자 정규화
    text = text.replace('•', '·')

    return text


def escape_org_table_cell(text: str) -> str:
    """Org 테이블 셀 내 파이프 이스케이프"""
    if not text:
        return ""
    return text.replace("|", "/")


def table_to_org(table: MdTable) -> str:
    """Markdown 테이블을 Org 네이티브 테이블로 변환"""
    lines = []

    # 헤더 행
    header_cells = [clean_md_text(c) for c in table.headers]
    header_cells = [escape_org_table_cell(c) for c in header_cells]
    lines.append("| " + " | ".join(header_cells) + " |")

    # 구분선
    lines.append("|" + "+".join(["-" * (len(c) + 2) for c in header_cells]) + "|")

    # 데이터 행
    for row in table.rows:
        cells = [clean_md_text(c) for c in row]
        cells = [escape_org_table_cell(c) for c in cells]
        # 컬럼 수 맞추기
        while len(cells) < len(header_cells):
            cells.append("")
        lines.append("| " + " | ".join(cells) + " |")

    return '\n'.join(lines)


def convert_to_org(doc: MdDocument) -> str:
    """MdDocument를 Org-mode 형식으로 변환"""
    lines = []

    # 문서 헤더
    lines.append(f"#+TITLE: {doc.title or 'Untitled'}")
    lines.append(f"#+DATE: [{datetime.now().strftime('%Y-%m-%d %a %H:%M')}]")
    lines.append("#+STARTUP: overview")
    lines.append("")

    for elem in doc.elements:
        if isinstance(elem, MdHeading):
            stars = '*' * elem.org_level
            heading_text = clean_md_text(elem.text)

            # 글머리표 접두어가 있으면 추가
            if elem.bullet_prefix:
                heading_text = f"{elem.bullet_prefix}{heading_text}"

            lines.append(f"{stars} {heading_text}")
            lines.append(":PROPERTIES:")
            lines.append(f":HWPX_IDX: {elem.hwpx_idx}")
            lines.append(":END:")
            lines.append("")

        elif isinstance(elem, MdTable):
            org_table = table_to_org(elem)

            if elem.title:
                lines.append(f"#+CAPTION: {elem.title}")
            lines.append(f"#+HWPX: {elem.hwpx_idx}")
            if elem.is_guide:
                lines.append("#+BEGIN_EXAMPLE :name 작성요령")
                lines.append(org_table)
                lines.append("#+END_EXAMPLE")
            else:
                lines.append(org_table)
            lines.append("")

        elif isinstance(elem, MdBlockquote):
            # 그림 캡션은 주석으로 처리
            quote_text = clean_md_text(elem.text)
            lines.append(f"#+HWPX: {elem.hwpx_idx}")
            lines.append(f"# {quote_text}")
            lines.append("")

        elif isinstance(elem, MdCodeBlock):
            # Mermaid 등 코드 블록은 그대로 유지
            lines.append(f"#+HWPX: {elem.hwpx_idx}")
            if elem.language:
                lines.append(f"#+BEGIN_SRC {elem.language}")
            else:
                lines.append("#+BEGIN_SRC")
            lines.append(elem.content)
            lines.append("#+END_SRC")
            lines.append("")

        elif isinstance(elem, MdParagraph):
            para_text = clean_md_text(elem.text)
            # 빈 문단 스킵
            if not para_text.strip():
                continue
            lines.append(f"#+HWPX: {elem.hwpx_idx}")
            lines.append(para_text)
            lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Markdown → Org-mode 변환기 (HWPX 메타포맷 호환)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    python md_to_org.py 고퀄.md -o 고퀄.org
    python md_to_org.py *.md --output-dir output/

HWPX 레벨 체계 (MD 레벨 기반):
    MD H1 → Level 1 (*):   장 번호
    MD H2 → Level 2 (**):  절 번호
    MD H3 → Level 3 (***): □ 소절
    MD H4 → Level 4 (****): o 항목
    MD H5 → Level 5 (*****): - 세부
    MD H6 → Level 6 (******): · 상세 (후처리에서 L5로 통합)
"""
    )
    parser.add_argument('input', nargs='+', help='입력 Markdown 파일(들)')
    parser.add_argument('-o', '--output', help='출력 Org 파일 (단일 파일 변환 시)')
    parser.add_argument('--output-dir', help='출력 디렉토리 (다중 파일 변환 시)')
    parser.add_argument('-v', '--verbose', action='store_true', help='상세 로그')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    for input_file in args.input:
        input_path = Path(input_file)

        if not input_path.exists():
            logger.error(f"파일이 존재하지 않습니다: {input_path}")
            continue

        # 출력 경로 결정
        if args.output and len(args.input) == 1:
            output_path = Path(args.output)
        elif args.output_dir:
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / input_path.with_suffix('.org').name
        else:
            output_path = input_path.with_suffix('.org')

        logger.info(f"변환 중: {input_path} → {output_path}")

        # 파싱
        doc = parse_md_file(input_path)

        # 통계
        headings = sum(1 for e in doc.elements if isinstance(e, MdHeading))
        tables = sum(1 for e in doc.elements if isinstance(e, MdTable))
        paragraphs = sum(1 for e in doc.elements if isinstance(e, MdParagraph))
        blockquotes = sum(1 for e in doc.elements if isinstance(e, MdBlockquote))
        codeblocks = sum(1 for e in doc.elements if isinstance(e, MdCodeBlock))

        logger.info(f"  제목: {doc.title}")
        logger.info(f"  헤딩: {headings}개, 표: {tables}개, 문단: {paragraphs}개")
        logger.info(f"  블록쿼트: {blockquotes}개, 코드블록: {codeblocks}개")

        # 변환
        org_content = convert_to_org(doc)

        # 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(org_content)

        logger.info(f"  저장 완료: {output_path}")


if __name__ == '__main__':
    main()

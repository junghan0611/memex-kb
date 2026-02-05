#!/usr/bin/env python3
"""
HWPX → Org-mode 변환기 (국가과제 제안서용)

본문(1-5장)만 추출, 글머리표를 헤딩으로, 표는 AsciiDoc 형식으로 변환합니다.
역변환(org_to_hwpx.py)과 호환되는 구조를 생성합니다.

사용법:
    python hwpx_to_org.py input.hwpx -o output.org
"""

import argparse
import logging
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# HWPX XML 네임스페이스
NS = {
    'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hs': 'http://www.hancom.co.kr/hwpml/2011/section',
    'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
}


@dataclass
class TableCell:
    """테이블 셀 데이터"""
    text: str = ""
    col_span: int = 1
    row_span: int = 1
    col_addr: int = 0
    row_addr: int = 0


@dataclass
class Table:
    """테이블 데이터"""
    cells: List[TableCell] = field(default_factory=list)
    col_count: int = 0
    row_count: int = 0
    title: str = ""  # 표 제목 (있는 경우)
    is_guide: bool = False  # 작성요령 표


@dataclass
class Paragraph:
    """문단 데이터"""
    text: str
    style_id: int = 0
    is_heading: bool = False
    heading_level: int = 0
    is_table: bool = False
    table_data: Optional[Table] = None
    is_guide: bool = False  # 작성요령


@dataclass
class Section:
    """섹션 데이터"""
    name: str
    paragraphs: List[Paragraph] = field(default_factory=list)


def extract_text_from_paragraph(p_elem) -> str:
    """문단 요소에서 텍스트 추출"""
    texts = []
    for t in p_elem.findall('.//hp:t', NS):
        if t.text:
            texts.append(t.text)
    return ''.join(texts)


def parse_table(tbl_elem) -> Table:
    """테이블 파싱 (셀 병합 계산 포함)"""
    table = Table()

    # 테이블 메타데이터에서 행/열 개수 추출
    table.row_count = int(tbl_elem.get('rowCnt', 0))
    table.col_count = int(tbl_elem.get('colCnt', 0))

    # 모든 셀 수집
    for tc_elem in tbl_elem.findall(f".//{{{NS['hp']}}}tc"):
        cell = TableCell()

        # 셀 주소 추출
        cell_addr = tc_elem.find(f"{{{NS['hp']}}}cellAddr")
        if cell_addr is not None:
            cell.col_addr = int(cell_addr.get('colAddr', 0))
            cell.row_addr = int(cell_addr.get('rowAddr', 0))

        # 셀 텍스트 추출
        texts = []
        for t_elem in tc_elem.iter(f"{{{NS['hp']}}}t"):
            if t_elem.text:
                texts.append(t_elem.text)
        cell.text = ' '.join(texts)

        table.cells.append(cell)

    # 병합 정보 계산
    calculate_spans(table)

    # 작성요령 감지
    all_text = ' '.join(c.text for c in table.cells)
    if re.search(r'작성\s*요령|작성요령', all_text[:200]):
        table.is_guide = True

    return table


def calculate_spans(table: Table) -> None:
    """셀 주소 기반으로 colspan/rowspan 계산"""
    if not table.cells:
        return

    # 행/열 개수: 메타데이터 우선, 없으면 셀 주소에서 계산
    if table.col_count == 0 or table.row_count == 0:
        max_col = max(c.col_addr for c in table.cells) if table.cells else 0
        max_row = max(c.row_addr for c in table.cells) if table.cells else 0
        if table.col_count == 0:
            table.col_count = max_col + 1
        if table.row_count == 0:
            table.row_count = max_row + 1

    # 셀을 (row, col) 기준으로 정렬
    table.cells.sort(key=lambda c: (c.row_addr, c.col_addr))

    # 같은 행의 셀들로 그룹화
    rows_map: Dict[int, List[TableCell]] = {}
    for cell in table.cells:
        if cell.row_addr not in rows_map:
            rows_map[cell.row_addr] = []
        rows_map[cell.row_addr].append(cell)

    # 각 행 내에서 colspan 계산
    for row_addr, row_cells in rows_map.items():
        row_cells.sort(key=lambda c: c.col_addr)
        for i, cell in enumerate(row_cells):
            if i + 1 < len(row_cells):
                next_col = row_cells[i + 1].col_addr
                cell.col_span = next_col - cell.col_addr
            else:
                cell.col_span = table.col_count - cell.col_addr

    # 같은 열의 셀들로 그룹화
    cols_map: Dict[int, List[TableCell]] = {}
    for cell in table.cells:
        if cell.col_addr not in cols_map:
            cols_map[cell.col_addr] = []
        cols_map[cell.col_addr].append(cell)

    # 각 열 내에서 rowspan 계산
    for col_addr, col_cells in cols_map.items():
        col_cells.sort(key=lambda c: c.row_addr)
        for i, cell in enumerate(col_cells):
            if i + 1 < len(col_cells):
                next_row = col_cells[i + 1].row_addr
                cell.row_span = next_row - cell.row_addr
            else:
                cell.row_span = table.row_count - cell.row_addr


def table_to_asciidoc(table: Table) -> str:
    """테이블을 AsciiDoc 형식으로 변환"""
    lines = []

    # 열 너비 지정
    lines.append(f"[cols=\"{','.join(['1'] * table.col_count)}\"]")
    lines.append("|===")

    # 셀을 행별로 그룹화
    rows_map: Dict[int, List[TableCell]] = {}
    for cell in table.cells:
        if cell.row_addr not in rows_map:
            rows_map[cell.row_addr] = []
        rows_map[cell.row_addr].append(cell)

    # 행 순서대로 출력
    for row_addr in sorted(rows_map.keys()):
        row_cells = sorted(rows_map[row_addr], key=lambda c: c.col_addr)
        row_parts = []

        for cell in row_cells:
            prefix = format_merge_prefix(cell.col_span, cell.row_span)
            text = escape_asciidoc(cell.text)
            row_parts.append(f"{prefix}{text}")

        lines.append('\n'.join(row_parts))
        lines.append('')  # 행 구분

    lines.append("|===")

    return '\n'.join(lines)


def format_merge_prefix(col_span: int, row_span: int) -> str:
    """AsciiDoc 셀 병합 접두사 생성"""
    if col_span > 1 and row_span > 1:
        return f"{col_span}.{row_span}+|"
    elif col_span > 1:
        return f"{col_span}+|"
    elif row_span > 1:
        return f".{row_span}+|"
    return "|"


def escape_asciidoc(text: str) -> str:
    """AsciiDoc 특수 문자 이스케이프"""
    if not text:
        return ""

    replacements = [
        ("|", "\\|"),
        ("*", "\\*"),
        ("_", "\\_"),
        ("`", "\\`"),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    return text




def strip_memo_prefix(text: str) -> str:
    """헤딩 감지를 위해 메모 접두어 제거 (변환 시에는 원본 유지)"""
    text = re.sub(r'^고퀄\s*작성', '', text)
    text = re.sub(r'^고퀄,?\s*TTA\s*작성', '', text)
    text = re.sub(r'^\[.*?작성.*?\]', '', text)
    # "...작성" 형태가 숫자 헤딩 앞에 붙은 경우
    text = re.sub(r'^.+작성(?=\d+\.)', '', text)
    return text.strip()


def detect_heading(text: str, style_id: int) -> Tuple[bool, int]:
    """텍스트가 헤딩인지 감지 (글머리표 포함)"""
    # 메모 접두어 제거 후 헤딩 감지
    text = strip_memo_prefix(text.strip())

    # 1. 숫자 기반 헤딩 (장/절) - 레벨 조정: 1장이 level 1
    number_patterns = [
        (r'^(\d+)\.\s+(.+)$', 1),              # "1. 제목" → level 1
        (r'^(\d+)-(\d+)\.\s+(.+)$', 2),        # "1-1. 제목" → level 2
        (r'^(\d+)-(\d+)-(\d+)\.\s+(.+)$', 3),  # "1-1-1. 제목" → level 3
    ]

    for pattern, level in number_patterns:
        if re.match(pattern, text):
            return True, level

    # 2. 글머리표 기반 헤딩
    bullet_patterns = [
        (r'^□\s*(.+)$', 3),           # □ → level 3
        (r'^○\s*(.+)$', 4),           # ○ → level 4
        (r'^o\s+(.+)$', 4),           # o → level 4
        (r'^-\s+(.+)$', 5),           # - → level 5
        (r'^⋅\s*(.+)$', 6),           # ⋅ → level 6
        (r'^·\s*(.+)$', 6),           # · (middle dot) → level 6
        (r'^<([^>]+)>$', 7),          # <제목> → level 7 (표 제목)
    ]

    for pattern, level in bullet_patterns:
        if re.match(pattern, text):
            return True, level

    # 3. 한글 기반 (가, 나, 다...)
    korean_patterns = [
        (r'^[가-힣]\.\s+(.+)$', 3),    # "가. 제목" → level 3
        (r'^\([가-힣]\)\s+(.+)$', 4),  # "(가) 제목" → level 4
        (r'^\(\d+\)\s+(.+)$', 4),     # "(1) 제목" → level 4
    ]

    for pattern, level in korean_patterns:
        if re.match(pattern, text):
            return True, level

    return False, 0


def is_excluded_chapter(text: str) -> bool:
    """제외할 장인지 확인 (6, 7, 8장)"""
    if re.match(r'^[6-8]\.\s+', text.strip()):
        return True
    if re.match(r'^[6-8]-\d+\.', text.strip()):
        return True
    return False


def parse_hwpx_section(section_path: Path, include_tables: bool = True) -> Section:
    """HWPX 섹션 XML 파싱"""
    section = Section(name=section_path.stem)

    tree = ET.parse(section_path)
    root = tree.getroot()

    # 표 제목 추적 (직전 헤딩 참조)
    last_table_title = ""

    # 최상위 요소 순회 (문단과 테이블)
    for elem in root:
        # 문단 처리
        if elem.tag == '{http://www.hancom.co.kr/hwpml/2011/paragraph}p':
            text = extract_text_from_paragraph(elem)
            if not text.strip():
                continue

            # 너무 긴 텍스트는 건너뛰기
            if len(text) > 1000:
                continue

            style_id = int(elem.get('styleIDRef', '0'))
            is_heading, level = detect_heading(text, style_id)

            # 표 제목 감지 (<표 제목> 형식)
            table_title_match = re.match(r'^<(.+)>$', text.strip())
            if table_title_match:
                last_table_title = table_title_match.group(1)

            para = Paragraph(
                text=text.strip(),
                style_id=style_id,
                is_heading=is_heading,
                heading_level=level
            )
            section.paragraphs.append(para)

            # 문단 내 테이블 처리
            if include_tables:
                for tbl in elem.findall('.//hp:tbl', NS):
                    table = parse_table(tbl)
                    if table.cells:
                        # 표 제목 연결
                        if last_table_title:
                            table.title = last_table_title
                            last_table_title = ""

                        tbl_para = Paragraph(
                            text="",  # AsciiDoc 형식으로 변환
                            is_table=True,
                            table_data=table,
                            is_guide=table.is_guide
                        )
                        section.paragraphs.append(tbl_para)

    return section


def parse_hwpx(hwpx_path: Path, include_tables: bool = True) -> List[Section]:
    """HWPX 파일 파싱"""
    sections = []

    with zipfile.ZipFile(hwpx_path, 'r') as zf:
        # 섹션 파일 목록
        section_files = sorted([
            n for n in zf.namelist()
            if n.startswith('Contents/section') and n.endswith('.xml')
        ])

        for section_file in section_files:
            section_name = Path(section_file).stem

            # 참고: section0, section1이 매크로 표인 경우도 있지만
            # 편집된 문서에서는 본문이 section0에 있을 수 있음
            # 목차/본문 구분은 convert_to_org에서 처리

            logger.info(f"섹션 파싱: {section_file}")

            # 임시 추출
            content = zf.read(section_file)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)

            section = parse_hwpx_section(tmp_path, include_tables=include_tables)
            section.name = section_name
            sections.append(section)

            tmp_path.unlink()

    return sections


def convert_to_org(sections: List[Section], title: str = "") -> str:
    """섹션 리스트를 Org 형식으로 변환"""
    lines = []

    # 헤더
    lines.append(f"#+TITLE: {title or 'HWPX 변환 문서'}")
    lines.append(f"#+DATE: [{datetime.now().strftime('%Y-%m-%d %a %H:%M')}]")
    lines.append(f"#+STARTUP: overview")
    lines.append("")

    # 본문 처리
    in_excluded = False
    found_first_chapter = False

    for section in sections:
        for para in section.paragraphs:
            # "목 차" 텍스트는 건너뛰기
            if para.text.strip() in ['목  차', '목 차', '목차']:
                continue

            text = para.text.strip()
            clean_text = strip_memo_prefix(text)  # 헤딩 감지용

            # 제외할 장 체크 (6, 7, 8장)
            if is_excluded_chapter(clean_text):
                in_excluded = True
                continue

            if in_excluded:
                # 다음 장(1-5) 시작하면 다시 포함
                if para.is_heading and para.heading_level == 1:
                    if re.match(r'^[1-5]\.\s+', clean_text):
                        in_excluded = False
                    else:
                        continue
                else:
                    continue

            # 첫 번째 "1. 연구개발" 찾기
            if not found_first_chapter and para.is_heading and para.heading_level == 1:
                if re.match(r'^1\.\s+연구개발', clean_text):
                    found_first_chapter = True

            # 본문 시작 전은 건너뛰기
            if not found_first_chapter:
                continue

            # 테이블 처리
            if para.is_table and para.table_data:
                table = para.table_data
                asciidoc_table = table_to_asciidoc(table)

                if para.is_guide:
                    # 작성요령 → EXAMPLE
                    lines.append("#+BEGIN_EXAMPLE :name 작성요령")
                    lines.append(asciidoc_table)
                    lines.append("#+END_EXAMPLE")
                else:
                    # 일반 표 → SRC asciidoc
                    name_attr = f" :name {table.title}" if table.title else ""
                    lines.append(f"#+BEGIN_SRC asciidoc{name_attr}")
                    lines.append(asciidoc_table)
                    lines.append("#+END_SRC")
                lines.append("")
                continue

            # 헤딩 처리
            if para.is_heading:
                org_level = para.heading_level  # 1장이 level 1
                stars = '*' * org_level
                # 메모 접두어 제거 후 출력
                heading_text = strip_memo_prefix(text)
                lines.append(f"{stars} {heading_text}")
                lines.append("")
            else:
                # 일반 문단
                lines.append(text)
                lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='HWPX → Org-mode 변환기 (국가과제 제안서용)')
    parser.add_argument('input', help='입력 HWPX 파일')
    parser.add_argument('-o', '--output', help='출력 Org 파일')
    parser.add_argument('-t', '--title', default='', help='문서 제목')
    parser.add_argument('--no-tables', action='store_true', help='표 제외')
    parser.add_argument('-v', '--verbose', action='store_true', help='상세 로그')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix('.org')

    # HWPX 파싱
    logger.info(f"HWPX 파싱: {input_path}")
    sections = parse_hwpx(input_path, include_tables=not args.no_tables)

    total_paras = sum(len(s.paragraphs) for s in sections)
    logger.info(f"파싱 완료: {len(sections)}개 섹션, {total_paras}개 문단")

    # Org 변환
    title = args.title or input_path.stem
    org_content = convert_to_org(sections, title)

    # 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(org_content)

    logger.info(f"저장 완료: {output_path}")


if __name__ == '__main__':
    main()

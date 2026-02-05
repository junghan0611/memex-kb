#!/usr/bin/env python3
"""
HWPX → Org-mode 변환기 (장별 변환용)

단일 장(chapter) HWPX 파일을 Org-mode로 변환합니다.
hwpx2asciidoc/hwpx_to_org.py에서 장 필터링 로직을 제거한 버전입니다.

사용법:
    python hwpx_to_org.py ch1.hwpx -o ch1.org
    python hwpx_to_org.py ch2.hwpx -o ch2.org
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

NS = {
    'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hs': 'http://www.hancom.co.kr/hwpml/2011/section',
    'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
}


@dataclass
class TableCell:
    text: str = ""
    col_span: int = 1
    row_span: int = 1
    col_addr: int = 0
    row_addr: int = 0


@dataclass
class Table:
    cells: List[TableCell] = field(default_factory=list)
    col_count: int = 0
    row_count: int = 0
    title: str = ""
    is_guide: bool = False


@dataclass
class Paragraph:
    text: str
    style_id: int = 0
    is_heading: bool = False
    heading_level: int = 0
    is_table: bool = False
    table_data: Optional[Table] = None
    is_guide: bool = False
    hwpx_idx: int = -1


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
    table.row_count = int(tbl_elem.get('rowCnt', 0))
    table.col_count = int(tbl_elem.get('colCnt', 0))

    for tc_elem in tbl_elem.findall(f".//{{{NS['hp']}}}tc"):
        cell = TableCell()
        cell_addr = tc_elem.find(f"{{{NS['hp']}}}cellAddr")
        if cell_addr is not None:
            cell.col_addr = int(cell_addr.get('colAddr', 0))
            cell.row_addr = int(cell_addr.get('rowAddr', 0))

        texts = []
        for t_elem in tc_elem.iter(f"{{{NS['hp']}}}t"):
            if t_elem.text:
                texts.append(t_elem.text)
        cell.text = ' '.join(texts)
        table.cells.append(cell)

    calculate_spans(table)

    all_text = ' '.join(c.text for c in table.cells)
    if re.search(r'작성\s*요령|작성요령', all_text[:200]):
        table.is_guide = True

    return table


def calculate_spans(table: Table) -> None:
    """셀 주소 기반으로 colspan/rowspan 계산"""
    if not table.cells:
        return

    if table.col_count == 0 or table.row_count == 0:
        max_col = max(c.col_addr for c in table.cells) if table.cells else 0
        max_row = max(c.row_addr for c in table.cells) if table.cells else 0
        if table.col_count == 0:
            table.col_count = max_col + 1
        if table.row_count == 0:
            table.row_count = max_row + 1

    table.cells.sort(key=lambda c: (c.row_addr, c.col_addr))

    rows_map: Dict[int, List[TableCell]] = {}
    for cell in table.cells:
        if cell.row_addr not in rows_map:
            rows_map[cell.row_addr] = []
        rows_map[cell.row_addr].append(cell)

    for row_addr, row_cells in rows_map.items():
        row_cells.sort(key=lambda c: c.col_addr)
        for i, cell in enumerate(row_cells):
            if i + 1 < len(row_cells):
                next_col = row_cells[i + 1].col_addr
                cell.col_span = next_col - cell.col_addr
            else:
                cell.col_span = table.col_count - cell.col_addr

    cols_map: Dict[int, List[TableCell]] = {}
    for cell in table.cells:
        if cell.col_addr not in cols_map:
            cols_map[cell.col_addr] = []
        cols_map[cell.col_addr].append(cell)

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
    lines.append(f"[cols=\"{','.join(['1'] * table.col_count)}\"]")
    lines.append("|===")

    rows_map: Dict[int, List[TableCell]] = {}
    for cell in table.cells:
        if cell.row_addr not in rows_map:
            rows_map[cell.row_addr] = []
        rows_map[cell.row_addr].append(cell)

    for row_addr in sorted(rows_map.keys()):
        row_cells = sorted(rows_map[row_addr], key=lambda c: c.col_addr)
        row_parts = []
        for cell in row_cells:
            prefix = format_merge_prefix(cell.col_span, cell.row_span)
            text = escape_asciidoc(cell.text)
            row_parts.append(f"{prefix}{text}")
        lines.append('\n'.join(row_parts))
        lines.append('')

    lines.append("|===")
    return '\n'.join(lines)


def format_merge_prefix(col_span: int, row_span: int) -> str:
    if col_span > 1 and row_span > 1:
        return f"{col_span}.{row_span}+|"
    elif col_span > 1:
        return f"{col_span}+|"
    elif row_span > 1:
        return f".{row_span}+|"
    return "|"


def escape_asciidoc(text: str) -> str:
    if not text:
        return ""
    for old, new in [("|", "\\|"), ("*", "\\*"), ("_", "\\_"), ("`", "\\`")]:
        text = text.replace(old, new)
    return text


def strip_memo_prefix(text: str) -> str:
    """헤딩 감지를 위해 메모 접두어 제거"""
    text = re.sub(r'^고퀄\s*작성', '', text)
    text = re.sub(r'^고퀄,?\s*TTA\s*작성', '', text)
    text = re.sub(r'^\[.*?작성.*?\]', '', text)
    text = re.sub(r'^.+작성(?=\d+\.)', '', text)
    return text.strip()


def detect_heading(text: str, style_id: int) -> Tuple[bool, int]:
    """텍스트가 헤딩인지 감지 (글머리표 포함)"""
    text = strip_memo_prefix(text.strip())

    number_patterns = [
        (r'^(\d+)\.\s+(.+)$', 1),
        (r'^(\d+)-(\d+)\.\s+(.+)$', 2),
        (r'^(\d+)-(\d+)-(\d+)\.\s+(.+)$', 3),
    ]
    for pattern, level in number_patterns:
        if re.match(pattern, text):
            return True, level

    bullet_patterns = [
        (r'^□\s*(.+)$', 3),
        (r'^○\s*(.+)$', 4),
        (r'^o\s+(.+)$', 4),
        (r'^-\s+(.+)$', 5),
        (r'^⋅\s*(.+)$', 6),
        (r'^·\s*(.+)$', 6),
        (r'^<([^>]+)>$', 7),
    ]
    for pattern, level in bullet_patterns:
        if re.match(pattern, text):
            return True, level

    korean_patterns = [
        (r'^[가-힣]\.\s+(.+)$', 3),
        (r'^\([가-힣]\)\s+(.+)$', 4),
        (r'^\(\d+\)\s+(.+)$', 4),
    ]
    for pattern, level in korean_patterns:
        if re.match(pattern, text):
            return True, level

    return False, 0


def parse_hwpx(hwpx_path: Path, include_tables: bool = True) -> List[Paragraph]:
    """HWPX 파일을 파싱하여 문단 리스트 반환 (장 필터링 없음)"""
    paragraphs = []

    with zipfile.ZipFile(hwpx_path, 'r') as zf:
        section_files = sorted([
            n for n in zf.namelist()
            if n.startswith('Contents/section') and n.endswith('.xml')
        ])

        para_idx = 0
        for section_file in section_files:
            logger.info(f"섹션 파싱: {section_file}")
            content = zf.read(section_file)
            root = ET.fromstring(content)

            last_table_title = ""

            for elem in root:
                if elem.tag == f"{{{NS['hp']}}}p":
                    current_idx = para_idx
                    para_idx += 1

                    text = extract_text_from_paragraph(elem)
                    if not text.strip():
                        continue

                    if len(text) > 1000:
                        continue

                    style_id = int(elem.get('styleIDRef', '0'))
                    is_heading, level = detect_heading(text, style_id)

                    table_title_match = re.match(r'^<(.+)>$', text.strip())
                    if table_title_match:
                        last_table_title = table_title_match.group(1)

                    para = Paragraph(
                        text=text.strip(),
                        style_id=style_id,
                        is_heading=is_heading,
                        heading_level=level,
                        hwpx_idx=current_idx
                    )
                    paragraphs.append(para)

                    if include_tables:
                        for tbl in elem.findall('.//hp:tbl', NS):
                            table = parse_table(tbl)
                            if table.cells:
                                if last_table_title:
                                    table.title = last_table_title
                                    last_table_title = ""
                                tbl_para = Paragraph(
                                    text="",
                                    is_table=True,
                                    table_data=table,
                                    is_guide=table.is_guide,
                                    hwpx_idx=current_idx
                                )
                                paragraphs.append(tbl_para)

    return paragraphs


def convert_to_org(paragraphs: List[Paragraph], title: str = "") -> str:
    """문단 리스트를 Org 형식으로 변환 (장 필터링 없음 — 모든 문단 출력)"""
    lines = []

    lines.append(f"#+TITLE: {title or 'HWPX 변환 문서'}")
    lines.append(f"#+DATE: [{datetime.now().strftime('%Y-%m-%d %a %H:%M')}]")
    lines.append(f"#+STARTUP: overview")
    lines.append("")

    for para in paragraphs:
        if para.text.strip() in ['목  차', '목 차', '목차']:
            continue

        text = para.text.strip()

        # 테이블 처리
        if para.is_table and para.table_data:
            table = para.table_data
            asciidoc_table = table_to_asciidoc(table)

            if para.is_guide:
                if para.hwpx_idx >= 0:
                    lines.append(f"#+HWPX: {para.hwpx_idx}")
                lines.append("#+BEGIN_EXAMPLE :name 작성요령")
                lines.append(asciidoc_table)
                lines.append("#+END_EXAMPLE")
            else:
                name_attr = f" :name {table.title}" if table.title else ""
                if para.hwpx_idx >= 0:
                    lines.append(f"#+HWPX: {para.hwpx_idx}")
                lines.append(f"#+BEGIN_SRC asciidoc{name_attr}")
                lines.append(asciidoc_table)
                lines.append("#+END_SRC")
            lines.append("")
            continue

        # 헤딩 처리
        if para.is_heading:
            org_level = para.heading_level
            stars = '*' * org_level
            heading_text = strip_memo_prefix(text)
            lines.append(f"{stars} {heading_text}")
            if para.hwpx_idx >= 0:
                lines.append(":PROPERTIES:")
                lines.append(f":HWPX_IDX: {para.hwpx_idx}")
                lines.append(":END:")
            lines.append("")
        else:
            # 일반 문단
            if para.hwpx_idx >= 0:
                lines.append(f"#+HWPX: {para.hwpx_idx}")
            lines.append(text)
            lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='HWPX → Org-mode 변환기 (장별)')
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

    logger.info(f"HWPX 파싱: {input_path}")
    paragraphs = parse_hwpx(input_path, include_tables=not args.no_tables)

    headings = sum(1 for p in paragraphs if p.is_heading)
    tables = sum(1 for p in paragraphs if p.is_table)
    normals = sum(1 for p in paragraphs if not p.is_heading and not p.is_table)
    logger.info(f"파싱 완료: 헤딩 {headings}개, 표 {tables}개, 문단 {normals}개")

    title = args.title or input_path.stem
    org_content = convert_to_org(paragraphs, title)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(org_content)

    logger.info(f"저장 완료: {output_path}")


if __name__ == '__main__':
    main()

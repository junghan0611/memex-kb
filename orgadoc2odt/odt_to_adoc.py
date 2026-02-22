#!/usr/bin/env python3
"""
ODT 테이블 → AsciiDoc 역변환기

ODT 파일의 테이블을 분석하여 AsciiDoc 병합 셀 문법으로 출력한다.
제안서 표지처럼 복잡한 병합 테이블의 역설계에 사용.

사용법:
    python odt_to_adoc.py input.odt [-t TABLE_NUM] [-o output.adoc]
"""

import argparse
import sys
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

NS = {
    'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
    'fo': 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
    'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
}

TBL = f'{{{NS["table"]}}}'
TXT = f'{{{NS["text"]}}}'


@dataclass
class Cell:
    text: str = ''
    colspan: int = 1
    rowspan: int = 1
    is_covered: bool = False


def extract_text(element) -> str:
    """요소에서 텍스트 추출 (중첩 span 포함)"""
    parts = []
    for para in element.findall(f'.//{TXT}p'):
        line_parts = []
        if para.text:
            line_parts.append(para.text)
        for child in para:
            if child.text:
                line_parts.append(child.text)
            if child.tail:
                line_parts.append(child.tail)
        parts.append(''.join(line_parts))
    return '\n'.join(parts).strip()


def parse_table(table_elem) -> list[list[Cell]]:
    """테이블 요소를 Cell 그리드로 파싱"""
    rows = []

    # header-rows + body rows
    all_rows = []
    for header in table_elem.findall(f'{TBL}table-header-rows'):
        all_rows.extend(header.findall(f'{TBL}table-row'))
    all_rows.extend(table_elem.findall(f'{TBL}table-row'))

    for row_elem in all_rows:
        row = []
        for child in row_elem:
            tag = child.tag.split('}')[1] if '}' in child.tag else child.tag

            if tag == 'table-cell':
                cs = int(child.get(f'{TBL}number-columns-spanned', '1'))
                rs = int(child.get(f'{TBL}number-rows-spanned', '1'))
                text = extract_text(child)
                row.append(Cell(text=text, colspan=cs, rowspan=rs))

            elif tag == 'covered-table-cell':
                row.append(Cell(is_covered=True))

        rows.append(row)

    return rows


def grid_to_adoc(rows: list[list[Cell]], total_cols: int = None) -> str:
    """Cell 그리드를 AsciiDoc 테이블 문법으로 변환"""
    if not rows:
        return '|===\n|===\n'

    # 실제 열 수 계산
    if total_cols is None:
        total_cols = 0
        for row in rows:
            col_count = sum(c.colspan if not c.is_covered else 1 for c in row)
            total_cols = max(total_cols, col_count)

    lines = []
    lines.append(f'[cols="{",".join(["1"] * total_cols)}"]')
    lines.append('|===')

    for row in rows:
        cell_parts = []
        for cell in row:
            if cell.is_covered:
                continue

            prefix = ''
            if cell.colspan > 1 and cell.rowspan > 1:
                prefix = f'{cell.colspan}.{cell.rowspan}+'
            elif cell.colspan > 1:
                prefix = f'{cell.colspan}+'
            elif cell.rowspan > 1:
                prefix = f'.{cell.rowspan}+'

            # 텍스트 내 개행 → AsciiDoc 셀 내 개행
            text = cell.text.replace('\n', ' +\n')
            cell_parts.append(f'{prefix}| {text}')

        lines.append('\n'.join(cell_parts))
        lines.append('')  # 행 구분 빈 줄

    lines.append('|===')
    return '\n'.join(lines)


def odt_to_adoc(odt_path: str, table_num: int = None) -> str:
    """ODT 파일에서 테이블을 AsciiDoc으로 변환"""
    with zipfile.ZipFile(odt_path) as z:
        content = z.read('content.xml')

    root = ET.fromstring(content)
    tables = root.findall(f'.//{TBL}table')

    if not tables:
        print("테이블 없음", file=sys.stderr)
        return ''

    results = []

    for i, table in enumerate(tables):
        if table_num is not None and i != table_num - 1:
            continue

        # 열 수 확인
        col_elems = table.findall(f'{TBL}table-column')
        total_cols = 0
        for col in col_elems:
            repeat = int(col.get(f'{TBL}number-columns-repeated', '1'))
            total_cols += repeat

        rows = parse_table(table)

        results.append(f'// === 테이블 {i+1} ({len(rows)}행 × {total_cols}열) ===')
        results.append(grid_to_adoc(rows, total_cols))

    return '\n\n'.join(results)


def main():
    parser = argparse.ArgumentParser(description='ODT 테이블 → AsciiDoc 역변환')
    parser.add_argument('input', help='입력 ODT 파일')
    parser.add_argument('-t', '--table', type=int, help='특정 테이블 번호만 (1부터)')
    parser.add_argument('-o', '--output', help='출력 AsciiDoc 파일')
    args = parser.parse_args()

    result = odt_to_adoc(args.input, args.table)

    if args.output:
        from pathlib import Path
        Path(args.output).write_text(result, encoding='utf-8')
        print(f"출력: {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
AsciiDoc 테이블 파서

AsciiDoc 테이블 문법을 파싱하여 구조화된 데이터로 변환합니다.
셀 병합 문법 (colspan/rowspan)을 해석합니다.

AsciiDoc 테이블 병합 문법:
- colspan: 2+| (2열 병합)
- rowspan: .2+| (2행 병합)
- 둘 다: 2.2+| (2열 x 2행 병합)
"""

import re
from dataclasses import dataclass, field


@dataclass
class AsciiDocCell:
    """AsciiDoc 테이블 셀"""
    text: str = ""
    col_span: int = 1
    row_span: int = 1


@dataclass
class AsciiDocTable:
    """AsciiDoc 테이블"""
    rows: list[list[AsciiDocCell]] = field(default_factory=list)
    col_count: int = 0
    col_widths: list[int] = field(default_factory=list)


# 셀 패턴: [colspan][.rowspan]+|text
# 예: 2+|text, .3+|text, 2.3+|text, |text
CELL_PATTERN = re.compile(
    r'^(?:(\d+))?(?:\.(\d+))?\+\|(.*)$'  # 병합 셀 (+ 필수)
)
SIMPLE_CELL_PATTERN = re.compile(r'^\|(.*)$')  # 일반 셀


def parse_asciidoc_cell(cell_str: str) -> AsciiDocCell:
    """AsciiDoc 셀 문자열을 파싱"""
    cell = AsciiDocCell()
    cell_str = cell_str.strip()

    match = CELL_PATTERN.match(cell_str)
    if match:
        col_span_str, row_span_str, text = match.groups()
        cell.col_span = int(col_span_str) if col_span_str else 1
        cell.row_span = int(row_span_str) if row_span_str else 1
        cell.text = unescape_asciidoc(text.strip())
        return cell

    simple_match = SIMPLE_CELL_PATTERN.match(cell_str)
    if simple_match:
        cell.text = unescape_asciidoc(simple_match.group(1).strip())
        return cell

    cell.text = unescape_asciidoc(cell_str.strip())
    return cell


def parse_asciidoc_table(table_text: str) -> AsciiDocTable:
    """AsciiDoc 테이블 전체를 파싱"""
    table = AsciiDocTable()
    lines = table_text.strip().split("\n")

    in_table = False
    current_row: list[AsciiDocCell] = []

    for line in lines:
        line = line.strip()

        if line == "|===":
            if in_table:
                if current_row:
                    table.rows.append(current_row)
                break
            else:
                in_table = True
                continue

        if line.startswith("[cols="):
            match = re.search(r'\[cols="([^"]+)"\]', line)
            if match:
                cols_str = match.group(1)
                table.col_widths = [int(c) if c.isdigit() else 1 for c in cols_str.split(",")]
                table.col_count = len(table.col_widths)
            continue

        if not in_table:
            continue

        if not line:
            if current_row:
                table.rows.append(current_row)
                current_row = []
            continue

        if line.startswith("|") or re.match(r'^\d', line):
            cells = split_cells(line)
            for cell_str in cells:
                if cell_str:
                    cell = parse_asciidoc_cell(cell_str)
                    current_row.append(cell)

    if not table.col_count and table.rows:
        table.col_count = sum(cell.col_span for cell in table.rows[0])

    return table


def split_cells(line: str) -> list[str]:
    """한 줄에서 셀들을 분리 (한 줄 = 한 셀)"""
    line = line.strip()
    if line:
        return [line]
    return []


def unescape_asciidoc(text: str) -> str:
    """AsciiDoc 이스케이프 해제"""
    replacements = [
        ("\\|", "|"),
        ("\\*", "*"),
        ("\\_", "_"),
        ("\\`", "`"),
        ("\\#", "#"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text

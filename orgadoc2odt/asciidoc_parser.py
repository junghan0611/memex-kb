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
    """
    AsciiDoc 셀 문자열을 파싱

    Args:
        cell_str: "2.3+|text" 또는 "|text" 형식의 문자열

    Returns:
        AsciiDocCell 객체
    """
    cell = AsciiDocCell()
    cell_str = cell_str.strip()

    # 병합 셀 파싱: 2+|, .3+|, 2.3+|
    match = CELL_PATTERN.match(cell_str)
    if match:
        col_span_str, row_span_str, text = match.groups()
        cell.col_span = int(col_span_str) if col_span_str else 1
        cell.row_span = int(row_span_str) if row_span_str else 1
        # AsciiDoc 이스케이프 해제
        cell.text = unescape_asciidoc(text.strip())
        return cell

    # 일반 셀: |text
    simple_match = SIMPLE_CELL_PATTERN.match(cell_str)
    if simple_match:
        # AsciiDoc 이스케이프 해제
        cell.text = unescape_asciidoc(simple_match.group(1).strip())
        return cell

    # 패턴 매칭 실패시 전체를 텍스트로 (이스케이프 해제 포함)
    cell.text = unescape_asciidoc(cell_str.strip())
    return cell


def parse_asciidoc_table(table_text: str) -> AsciiDocTable:
    """
    AsciiDoc 테이블 전체를 파싱

    Args:
        table_text: |=== 로 시작하고 끝나는 테이블 문자열

    Returns:
        AsciiDocTable 객체
    """
    table = AsciiDocTable()
    lines = table_text.strip().split("\n")

    in_table = False
    current_row: list[AsciiDocCell] = []

    for line in lines:
        line = line.strip()

        # 테이블 시작/끝
        if line == "|===":
            if in_table:
                # 테이블 끝: 마지막 행 저장
                if current_row:
                    table.rows.append(current_row)
                break
            else:
                in_table = True
                continue

        # 테이블 속성 (예: [cols="1,1,1"])
        if line.startswith("[cols="):
            # 열 너비 파싱
            match = re.search(r'\[cols="([^"]+)"\]', line)
            if match:
                cols_str = match.group(1)
                table.col_widths = [int(c) if c.isdigit() else 1 for c in cols_str.split(",")]
                table.col_count = len(table.col_widths)
            continue

        if not in_table:
            continue

        # 빈 줄 = 행 구분
        if not line:
            if current_row:
                table.rows.append(current_row)
                current_row = []
            continue

        # 셀 파싱
        # 한 줄에 여러 셀이 있을 수 있음: |cell1|cell2
        # 또는 한 줄에 하나의 셀: |cell
        if line.startswith("|") or re.match(r'^\d', line):
            # 셀 분리 (단순히 | 로 분리하면 안됨, 병합 문법 고려)
            cells = split_cells(line)
            for cell_str in cells:
                if cell_str:
                    cell = parse_asciidoc_cell(cell_str)
                    current_row.append(cell)

    # 열 개수 계산 (첫 번째 행 기준)
    if not table.col_count and table.rows:
        table.col_count = sum(cell.col_span for cell in table.rows[0])

    return table


def split_cells(line: str) -> list[str]:
    """
    한 줄에서 셀들을 분리

    AsciiDoc 셀 형식:
    - |cell1 (한 줄에 한 셀)
    - 2+|merged (병합 셀)
    - .2+|rowspan (행 병합)

    Returns:
        셀 문자열 리스트
    """
    # 단순화: 한 줄 = 한 셀로 처리 (AsciiDoc 기본 형식)
    # HWPX에서 내보낸 형식은 한 줄에 한 셀씩
    line = line.strip()
    if line:
        return [line]
    return []


def escape_hwpx_text(text: str) -> str:
    """HWPX XML용 텍스트 이스케이프"""
    replacements = [
        ("&", "&amp;"),
        ("<", "&lt;"),
        (">", "&gt;"),
        ('"', "&quot;"),
        ("'", "&apos;"),
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    return text


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


if __name__ == "__main__":
    # 테스트
    test_table = """
[cols="1,1,1"]
|===
|헤더1
|헤더2
|헤더3

2+|병합된 셀
|일반 셀

.2+|행 병합
|셀1
|셀2

|셀3
|셀4

|===
"""

    table = parse_asciidoc_table(test_table)
    print(f"행 수: {len(table.rows)}")
    print(f"열 수: {table.col_count}")

    for i, row in enumerate(table.rows):
        print(f"\n행 {i}:")
        for cell in row:
            print(f"  - {cell.text!r} (col:{cell.col_span}, row:{cell.row_span})")

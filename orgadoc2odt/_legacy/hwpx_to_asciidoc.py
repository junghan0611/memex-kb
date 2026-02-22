#!/usr/bin/env python3
"""
HWPX → AsciiDoc 변환기

HWPX 파일을 파싱하여 AsciiDoc 형식으로 변환합니다.
테이블 셀 병합(colspan/rowspan)을 보존합니다.

Usage:
    python hwpx_to_asciidoc.py input.hwpx -o output.adoc
"""

import argparse
import logging
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# HWPX XML 네임스페이스
NAMESPACES = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hc": "http://www.hancom.co.kr/hwpml/2011/head",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
}


@dataclass
class TableCell:
    """테이블 셀 데이터"""
    text: str = ""
    col_span: int = 1
    row_span: int = 1
    col_addr: int = 0  # HWPX 열 주소
    row_addr: int = 0  # HWPX 행 주소


@dataclass
class Table:
    """테이블 데이터"""
    cells: list[TableCell] = field(default_factory=list)  # 플랫 셀 목록
    col_count: int = 0
    row_count: int = 0


@dataclass
class Paragraph:
    """문단 데이터"""
    text: str = ""
    style: str = ""  # heading1, heading2, normal 등
    para_pr_id: int = 0  # paraPrIDRef (스타일 참조)
    char_pr_id: int = 0  # charPrIDRef (문자 스타일 참조)


class HwpxParser:
    """HWPX 파일 파서"""

    def __init__(self, hwpx_path: str):
        self.hwpx_path = Path(hwpx_path)
        self.paragraphs: list[Paragraph] = []
        self.tables: list[Table] = []
        self.elements: list[Paragraph | Table] = []  # 순서 유지

    def parse(self) -> None:
        """HWPX 파일 파싱"""
        if not self.hwpx_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {self.hwpx_path}")

        with zipfile.ZipFile(self.hwpx_path, "r") as zf:
            # section 파일들 찾기
            section_files = sorted([
                f for f in zf.namelist()
                if f.startswith("Contents/section") and f.endswith(".xml")
            ])

            if not section_files:
                raise ValueError("HWPX 파일에서 section을 찾을 수 없습니다")

            for section_file in section_files:
                logger.info(f"섹션 파싱: {section_file}")
                content = zf.read(section_file)
                self._parse_section(content)

    def _parse_section(self, content: bytes) -> None:
        """섹션 XML 파싱"""
        root = ET.fromstring(content)

        # 모든 문단과 테이블을 순서대로 처리
        for elem in root.iter():
            if elem.tag == f"{{{NAMESPACES['hp']}}}p":
                para = self._parse_paragraph(elem)
                if para.text.strip():
                    self.paragraphs.append(para)
                    self.elements.append(para)
            elif elem.tag == f"{{{NAMESPACES['hp']}}}tbl":
                table = self._parse_table(elem)
                if table.cells:
                    self.tables.append(table)
                    self.elements.append(table)

    def _parse_paragraph(self, p_elem: ET.Element) -> Paragraph:
        """문단 파싱"""
        para = Paragraph()

        # 텍스트 추출
        texts = []
        for t_elem in p_elem.iter(f"{{{NAMESPACES['hp']}}}t"):
            if t_elem.text:
                texts.append(t_elem.text)

        para.text = "".join(texts)

        # 스타일 추출 (TODO: 헤딩 레벨 파싱)
        # para_pr = p_elem.find(f".//{{{NAMESPACES['hp']}}}paraPr")

        return para

    def _parse_table(self, tbl_elem: ET.Element) -> Table:
        """테이블 파싱 (셀 병합 계산)"""
        table = Table()

        # 테이블 메타데이터에서 행/열 개수 추출
        table.row_count = int(tbl_elem.get("rowCnt", 0))
        table.col_count = int(tbl_elem.get("colCnt", 0))

        # 모든 셀 수집
        for tc_elem in tbl_elem.findall(f".//{{{NAMESPACES['hp']}}}tc"):
            cell = TableCell()

            # 셀 주소 추출
            cell_addr = tc_elem.find(f"{{{NAMESPACES['hp']}}}cellAddr")
            if cell_addr is not None:
                cell.col_addr = int(cell_addr.get("colAddr", 0))
                cell.row_addr = int(cell_addr.get("rowAddr", 0))

            # 셀 텍스트 추출
            texts = []
            for t_elem in tc_elem.iter(f"{{{NAMESPACES['hp']}}}t"):
                if t_elem.text:
                    texts.append(t_elem.text)
            cell.text = " ".join(texts)

            table.cells.append(cell)

        # 병합 정보 계산
        self._calculate_spans(table)

        return table

    def _calculate_spans(self, table: Table) -> None:
        """셀 주소 기반으로 colspan/rowspan 계산"""
        if not table.cells:
            return

        # 행/열 개수: 메타데이터 우선, 없으면 셀 주소에서 계산
        if table.col_count == 0 or table.row_count == 0:
            max_col = max(c.col_addr for c in table.cells)
            max_row = max(c.row_addr for c in table.cells)
            if table.col_count == 0:
                table.col_count = max_col + 1
            if table.row_count == 0:
                table.row_count = max_row + 1

        # 셀을 (row, col) 기준으로 정렬
        table.cells.sort(key=lambda c: (c.row_addr, c.col_addr))

        # 같은 행의 셀들로 그룹화
        rows_map: dict[int, list[TableCell]] = {}
        for cell in table.cells:
            if cell.row_addr not in rows_map:
                rows_map[cell.row_addr] = []
            rows_map[cell.row_addr].append(cell)

        # 각 행 내에서 colspan 계산
        for row_addr, row_cells in rows_map.items():
            row_cells.sort(key=lambda c: c.col_addr)
            for i, cell in enumerate(row_cells):
                if i + 1 < len(row_cells):
                    # 다음 셀까지의 거리 = colspan
                    next_col = row_cells[i + 1].col_addr
                    cell.col_span = next_col - cell.col_addr
                else:
                    # 마지막 셀: 테이블 끝까지
                    cell.col_span = table.col_count - cell.col_addr

        # 같은 열의 셀들로 그룹화
        cols_map: dict[int, list[TableCell]] = {}
        for cell in table.cells:
            if cell.col_addr not in cols_map:
                cols_map[cell.col_addr] = []
            cols_map[cell.col_addr].append(cell)

        # 각 열 내에서 rowspan 계산
        for col_addr, col_cells in cols_map.items():
            col_cells.sort(key=lambda c: c.row_addr)
            for i, cell in enumerate(col_cells):
                if i + 1 < len(col_cells):
                    # 다음 셀까지의 거리 = rowspan
                    next_row = col_cells[i + 1].row_addr
                    cell.row_span = next_row - cell.row_addr
                else:
                    # 마지막 셀: 테이블 끝까지
                    cell.row_span = table.row_count - cell.row_addr


class AsciiDocConverter:
    """AsciiDoc 변환기"""

    def __init__(self, parser: HwpxParser):
        self.parser = parser

    def convert(self) -> str:
        """AsciiDoc 문자열 생성"""
        lines: list[str] = []

        for elem in self.parser.elements:
            if isinstance(elem, Paragraph):
                lines.append(self._convert_paragraph(elem))
                lines.append("")
            elif isinstance(elem, Table):
                lines.append(self._convert_table(elem))
                lines.append("")

        return "\n".join(lines)

    def _convert_paragraph(self, para: Paragraph) -> str:
        """문단 → AsciiDoc"""
        text = self._escape_asciidoc(para.text)

        # TODO: 헤딩 스타일 처리
        # if para.style == "heading1":
        #     return f"= {text}"

        return text

    def _convert_table(self, table: Table) -> str:
        """테이블 → AsciiDoc (셀 병합 포함)"""
        lines: list[str] = []

        # 테이블 시작
        lines.append(f"[cols=\"{','.join(['1'] * table.col_count)}\"]")
        lines.append("|===")

        # 셀을 행별로 그룹화
        rows_map: dict[int, list[TableCell]] = {}
        for cell in table.cells:
            if cell.row_addr not in rows_map:
                rows_map[cell.row_addr] = []
            rows_map[cell.row_addr].append(cell)

        # 행 순서대로 출력
        for row_addr in sorted(rows_map.keys()):
            row_cells = sorted(rows_map[row_addr], key=lambda c: c.col_addr)
            row_parts: list[str] = []

            for cell in row_cells:
                prefix = self._format_merge_prefix(cell.col_span, cell.row_span)
                text = self._escape_asciidoc(cell.text)
                row_parts.append(f"{prefix}{text}")

            lines.append("\n".join(row_parts))
            lines.append("")  # 행 구분

        lines.append("|===")

        return "\n".join(lines)

    def _format_merge_prefix(self, col_span: int, row_span: int) -> str:
        """AsciiDoc 셀 병합 접두사 생성

        AsciiDoc 테이블 병합 문법:
        - colspan: 2+| (2열 병합)
        - rowspan: .2+| (2행 병합)
        - 둘 다: 2.2+| (2열 x 2행 병합)
        """
        if col_span > 1 and row_span > 1:
            return f"{col_span}.{row_span}+|"
        elif col_span > 1:
            return f"{col_span}+|"
        elif row_span > 1:
            return f".{row_span}+|"
        return "|"

    def _escape_asciidoc(self, text: str) -> str:
        """AsciiDoc 특수 문자 이스케이프"""
        if not text:
            return ""

        # AsciiDoc 특수 문자
        replacements = [
            ("|", "\\|"),  # 테이블 구분자
            ("*", "\\*"),  # 굵게
            ("_", "\\_"),  # 기울임
            ("`", "\\`"),  # 코드
            ("#", "\\#"),  # 헤딩 (일부 변환)
        ]

        for old, new in replacements:
            text = text.replace(old, new)

        return text


def main():
    parser = argparse.ArgumentParser(
        description="HWPX → AsciiDoc 변환기"
    )
    parser.add_argument("input", help="입력 HWPX 파일")
    parser.add_argument("-o", "--output", help="출력 AsciiDoc 파일 (기본: stdout)")
    parser.add_argument("-v", "--verbose", action="store_true", help="상세 로그")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # 파싱
        hwpx_parser = HwpxParser(args.input)
        hwpx_parser.parse()

        logger.info(f"파싱 완료: {len(hwpx_parser.paragraphs)}개 문단, {len(hwpx_parser.tables)}개 테이블")

        # 변환
        converter = AsciiDocConverter(hwpx_parser)
        result = converter.convert()

        # 출력
        if args.output:
            output_path = Path(args.output)
            output_path.write_text(result, encoding="utf-8")
            logger.info(f"저장 완료: {output_path}")
        else:
            print(result)

    except Exception as e:
        logger.error(f"변환 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

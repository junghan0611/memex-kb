#!/usr/bin/env python3
"""
AsciiDoc → HWPX 역변환기

AsciiDoc 파일을 파싱하여 HWPX 파일로 변환합니다.
테이블 셀 병합(colspan/rowspan)을 보존합니다.

Usage:
    python asciidoc_to_hwpx.py input.adoc -o output.hwpx
    python asciidoc_to_hwpx.py input.adoc --template blank.hwpx -o output.hwpx
"""

import argparse
import logging
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from asciidoc_parser import AsciiDocCell, AsciiDocTable, parse_asciidoc_table

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

# 네임스페이스 등록
for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix, uri)


class HwpxGenerator:
    """HWPX 파일 생성기"""

    def __init__(self, template_path: str | None = None):
        self.template_path = Path(template_path) if template_path else None
        self.tables: list[AsciiDocTable] = []
        self.paragraphs: list[str] = []

    def parse_asciidoc(self, adoc_path: str) -> None:
        """AsciiDoc 파일 파싱"""
        content = Path(adoc_path).read_text(encoding="utf-8")

        # 테이블 추출
        table_pattern = re.compile(r'\[cols=[^\]]*\]\s*\n\|===.*?\|===', re.DOTALL)

        for match in table_pattern.finditer(content):
            table_text = match.group()
            table = parse_asciidoc_table(table_text)
            self.tables.append(table)
            logger.info(f"테이블 파싱: {len(table.rows)}행 x {table.col_count}열")

        # 테이블 외 텍스트 추출
        last_end = 0
        for match in table_pattern.finditer(content):
            text = content[last_end:match.start()].strip()
            if text:
                for line in text.split("\n"):
                    line = line.strip()
                    if line:
                        self.paragraphs.append(line)
            last_end = match.end()

        # 마지막 테이블 이후 텍스트
        text = content[last_end:].strip()
        if text:
            for line in text.split("\n"):
                line = line.strip()
                if line:
                    self.paragraphs.append(line)

    def generate(self, output_path: str) -> None:
        """HWPX 파일 생성"""
        output = Path(output_path)

        if self.template_path and self.template_path.exists():
            # 템플릿 기반 생성
            self._generate_from_template(output)
        else:
            # 새로 생성
            self._generate_new(output)

    def _generate_from_template(self, output: Path) -> None:
        """템플릿 기반 HWPX 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # 템플릿 압축 해제
            with zipfile.ZipFile(self.template_path, "r") as zf:
                zf.extractall(tmpdir_path)

            # section0.xml 수정
            section_path = tmpdir_path / "Contents" / "section0.xml"
            if section_path.exists():
                self._modify_section(section_path)

            # 새 HWPX 생성
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in tmpdir_path.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(tmpdir_path)
                        zf.write(file_path, arcname)

        logger.info(f"HWPX 생성 완료: {output}")

    def _generate_new(self, output: Path) -> None:
        """새 HWPX 파일 생성 (템플릿 없이)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # 기본 디렉토리 구조 생성
            (tmpdir_path / "Contents").mkdir()
            (tmpdir_path / "META-INF").mkdir()

            # mimetype
            (tmpdir_path / "mimetype").write_text(
                "application/hwp+zip", encoding="utf-8"
            )

            # META-INF/container.xml
            container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>
  </rootfiles>
</container>"""
            (tmpdir_path / "META-INF" / "container.xml").write_text(
                container_xml, encoding="utf-8"
            )

            # Contents/content.hpf
            content_hpf = """<?xml version="1.0" encoding="UTF-8"?>
<hpf:hwpPackage xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf">
  <hpf:manifestItem id="header" href="header.xml"/>
  <hpf:manifestItem id="section0" href="section0.xml"/>
</hpf:hwpPackage>"""
            (tmpdir_path / "Contents" / "content.hpf").write_text(
                content_hpf, encoding="utf-8"
            )

            # Contents/header.xml (최소 헤더)
            header_xml = """<?xml version="1.0" encoding="UTF-8"?>
<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head">
</hh:head>"""
            (tmpdir_path / "Contents" / "header.xml").write_text(
                header_xml, encoding="utf-8"
            )

            # Contents/section0.xml 생성
            section_xml = self._create_section_xml()
            (tmpdir_path / "Contents" / "section0.xml").write_text(
                section_xml, encoding="utf-8"
            )

            # HWPX 압축
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in tmpdir_path.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(tmpdir_path)
                        zf.write(file_path, arcname)

        logger.info(f"HWPX 생성 완료: {output}")

    def _modify_section(self, section_path: Path) -> None:
        """기존 section XML 수정"""
        tree = ET.parse(section_path)
        root = tree.getroot()

        # 기존 내용 삭제 (선택적)
        # 새 내용 추가
        for para_text in self.paragraphs:
            para_elem = self._create_paragraph_element(para_text)
            root.append(para_elem)

        for table in self.tables:
            table_elem = self._create_table_element(table)
            root.append(table_elem)

        tree.write(section_path, encoding="utf-8", xml_declaration=True)

    def _create_section_xml(self) -> str:
        """section XML 생성"""
        # 네임스페이스를 직접 문자열로 생성 (ET의 중복 방지)
        root = ET.Element(f"{{{NAMESPACES['hs']}}}sec")

        # 문단 추가
        for para_text in self.paragraphs:
            para_elem = self._create_paragraph_element(para_text)
            root.append(para_elem)

        # 테이블 추가
        for table in self.tables:
            table_elem = self._create_table_element(table)
            root.append(table_elem)

        return ET.tostring(root, encoding="unicode")

    def _create_paragraph_element(self, text: str) -> ET.Element:
        """문단 XML 요소 생성"""
        p = ET.Element(f"{{{NAMESPACES['hp']}}}p")
        run = ET.SubElement(p, f"{{{NAMESPACES['hp']}}}run")
        t = ET.SubElement(run, f"{{{NAMESPACES['hp']}}}t")
        t.text = text
        return p

    def _create_table_element(self, table: AsciiDocTable) -> ET.Element:
        """테이블 XML 요소 생성"""
        tbl = ET.Element(
            f"{{{NAMESPACES['hp']}}}tbl",
            {
                "rowCnt": str(len(table.rows)),
                "colCnt": str(table.col_count),
            }
        )

        for row_idx, row in enumerate(table.rows):
            tr = ET.SubElement(tbl, f"{{{NAMESPACES['hp']}}}tr")

            col_idx = 0
            for cell in row:
                tc = ET.SubElement(tr, f"{{{NAMESPACES['hp']}}}tc")

                # 셀 주소
                cell_addr = ET.SubElement(
                    tc,
                    f"{{{NAMESPACES['hp']}}}cellAddr",
                    {
                        "colAddr": str(col_idx),
                        "rowAddr": str(row_idx),
                    }
                )

                # 셀 내용
                p = ET.SubElement(tc, f"{{{NAMESPACES['hp']}}}p")
                run = ET.SubElement(p, f"{{{NAMESPACES['hp']}}}run")
                t = ET.SubElement(run, f"{{{NAMESPACES['hp']}}}t")
                t.text = cell.text

                # 다음 열 위치 (colspan 고려)
                col_idx += cell.col_span

        return tbl


def main():
    parser = argparse.ArgumentParser(
        description="AsciiDoc → HWPX 역변환기"
    )
    parser.add_argument("input", help="입력 AsciiDoc 파일")
    parser.add_argument("-o", "--output", help="출력 HWPX 파일 (기본: input.hwpx)")
    parser.add_argument("-t", "--template", help="템플릿 HWPX 파일")
    parser.add_argument("-v", "--verbose", action="store_true", help="상세 로그")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 출력 파일 경로
    if args.output:
        output_path = args.output
    else:
        output_path = Path(args.input).with_suffix(".hwpx")

    try:
        # 생성기 초기화
        generator = HwpxGenerator(args.template)

        # AsciiDoc 파싱
        generator.parse_asciidoc(args.input)

        logger.info(
            f"파싱 완료: {len(generator.paragraphs)}개 문단, "
            f"{len(generator.tables)}개 테이블"
        )

        # HWPX 생성
        generator.generate(str(output_path))

    except Exception as e:
        logger.error(f"변환 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

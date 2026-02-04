#!/usr/bin/env python3
"""
HWPX → Org-mode 변환기 (텍스트/목차 중심)

테이블은 제외하고 목차와 텍스트만 추출합니다.

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
from typing import List, Optional
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
class Paragraph:
    """문단 데이터"""
    text: str
    style_id: int = 0
    is_heading: bool = False
    heading_level: int = 0


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


def detect_heading(text: str, style_id: int) -> tuple:
    """텍스트가 헤딩인지 감지"""
    # 숫자로 시작하는 패턴 감지
    patterns = [
        (r'^(\d+)\.\s+(.+)$', 1),           # "1. 제목" → level 1
        (r'^(\d+)-(\d+)\.\s+(.+)$', 2),     # "1-1. 제목" → level 2
        (r'^(\d+)-(\d+)-(\d+)\.\s+(.+)$', 3),  # "1-1-1. 제목" → level 3
        (r'^[가-힣]\.\s+(.+)$', 2),          # "가. 제목" → level 2
        (r'^\([가-힣]\)\s+(.+)$', 3),        # "(가) 제목" → level 3
        (r'^\(\d+\)\s+(.+)$', 3),           # "(1) 제목" → level 3
    ]

    for pattern, level in patterns:
        if re.match(pattern, text.strip()):
            return True, level

    return False, 0


def is_inside_table(elem, root) -> bool:
    """요소가 테이블 내부에 있는지 확인"""
    # 부모를 거슬러 올라가며 tbl 태그 확인
    for parent in root.iter():
        for child in parent:
            if child == elem:
                if parent.tag == '{http://www.hancom.co.kr/hwpml/2011/paragraph}tbl':
                    return True
                if parent.tag.endswith('}tc'):  # table cell
                    return True
    return False


def parse_hwpx_section(section_path: Path) -> Section:
    """HWPX 섹션 XML 파싱 (표 내부 텍스트 제외)"""
    section = Section(name=section_path.stem)

    tree = ET.parse(section_path)
    root = tree.getroot()

    # 테이블 내부 문단 ID 수집
    table_para_ids = set()
    for tbl in root.findall('.//hp:tbl', NS):
        for p_elem in tbl.findall('.//hp:p', NS):
            table_para_ids.add(id(p_elem))

    # 최상위 문단만 추출 (테이블 제외)
    for p_elem in root.findall('./hp:p', NS):  # 직접 자식만
        text = extract_text_from_paragraph(p_elem)
        if not text.strip():
            continue

        # 너무 긴 텍스트는 표 데이터일 가능성 (건너뛰기)
        if len(text) > 500:
            continue

        style_id = int(p_elem.get('styleIDRef', '0'))
        is_heading, level = detect_heading(text, style_id)

        para = Paragraph(
            text=text.strip(),
            style_id=style_id,
            is_heading=is_heading,
            heading_level=level
        )
        section.paragraphs.append(para)

    return section


def parse_hwpx(hwpx_path: Path) -> List[Section]:
    """HWPX 파일 파싱"""
    sections = []

    with zipfile.ZipFile(hwpx_path, 'r') as zf:
        # 섹션 파일 목록
        section_files = sorted([
            n for n in zf.namelist()
            if n.startswith('Contents/section') and n.endswith('.xml')
        ])

        for section_file in section_files:
            logger.info(f"섹션 파싱: {section_file}")

            # 임시 추출
            content = zf.read(section_file)
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)

            section = parse_hwpx_section(tmp_path)
            section.name = Path(section_file).stem
            sections.append(section)

            tmp_path.unlink()

    return sections


def convert_to_org(sections: List[Section], title: str = "") -> str:
    """섹션 리스트를 Org 형식으로 변환"""
    lines = []

    # 헤더
    lines.append(f"#+TITLE: {title or 'HWPX 변환 문서'}")
    lines.append(f"#+DATE: [{datetime.now().strftime('%Y-%m-%d %a %H:%M')}]")
    lines.append(f"#+HWPX_SECTIONS: {len(sections)}")
    lines.append("")

    for section in sections:
        lines.append(f"* {section.name}")
        lines.append(":PROPERTIES:")
        lines.append(f":HWPX_SECTION: {section.name}")
        lines.append(":END:")
        lines.append("")

        current_level = 1
        for para in section.paragraphs:
            if para.is_heading:
                # 헤딩 레벨에 따라 * 개수 조정 (섹션이 *1이므로 +1)
                org_level = para.heading_level + 1
                stars = '*' * org_level
                lines.append(f"{stars} {para.text}")
            else:
                # 일반 문단
                lines.append(para.text)
            lines.append("")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='HWPX → Org-mode 변환기 (텍스트/목차 중심)')
    parser.add_argument('input', help='입력 HWPX 파일')
    parser.add_argument('-o', '--output', help='출력 Org 파일')
    parser.add_argument('-t', '--title', default='', help='문서 제목')
    parser.add_argument('-v', '--verbose', action='store_true', help='상세 로그')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix('.org')

    # HWPX 파싱
    logger.info(f"HWPX 파싱: {input_path}")
    sections = parse_hwpx(input_path)

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

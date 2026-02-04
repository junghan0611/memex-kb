#!/usr/bin/env python3
"""
HWPX → Org-mode 변환기 (국가과제 제안서용)

본문(1-5장)만 추출, 글머리표를 헤딩으로, 표는 소스블록으로 변환합니다.

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
from typing import List, Optional, Tuple
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# HWPX XML 네임스페이스
NS = {
    'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hs': 'http://www.hancom.co.kr/hwpml/2011/section',
    'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
}

# 메모 패턴 (무시 - 역변환 시 불필요)
# 메모는 변환 시 일반 텍스트로 처리됨


@dataclass
class Paragraph:
    """문단 데이터"""
    text: str
    style_id: int = 0
    is_heading: bool = False
    heading_level: int = 0
    is_table: bool = False
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


def extract_table_text(tbl_elem) -> Tuple[str, bool]:
    """테이블에서 텍스트 추출, 작성요령 여부 반환"""
    texts = []
    is_guide = False

    for t in tbl_elem.findall('.//hp:t', NS):
        if t.text:
            texts.append(t.text)

    full_text = '\n'.join(texts)

    # 작성요령 감지
    if re.search(r'작성\s*요령|작성요령', full_text[:100]):
        is_guide = True

    return full_text, is_guide




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
                    tbl_text, is_guide = extract_table_text(tbl)
                    if tbl_text.strip():
                        tbl_para = Paragraph(
                            text=tbl_text.strip(),
                            is_table=True,
                            is_guide=is_guide
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
            if para.is_table:
                if para.is_guide:
                    # 작성요령 → EXAMPLE
                    lines.append("#+BEGIN_EXAMPLE")
                    lines.append(para.text)
                    lines.append("#+END_EXAMPLE")
                else:
                    # 일반 표 → SRC asciidoc
                    lines.append("#+BEGIN_SRC asciidoc")
                    lines.append(para.text)
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

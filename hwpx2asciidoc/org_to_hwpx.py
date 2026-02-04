#!/usr/bin/env python3
"""
Org-mode 메타 포맷 → HWPX 변환기

Org 파일에서 내용을 추출하여 HWPX 템플릿에 삽입합니다.

사용법:
    python org_to_hwpx.py input.org -t template.hwpx -o output.hwpx
"""

import argparse
import logging
import re
import zipfile
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# XML 네임스페이스
NAMESPACES = {
    'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hs': 'http://www.hancom.co.kr/hwpml/2011/section',
    'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
}

for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix, uri)


@dataclass
class OrgSection:
    """Org 섹션 데이터"""
    level: int
    title: str
    hwpx_section: Optional[str] = None
    content: str = ""
    asciidoc_blocks: List[Dict] = field(default_factory=list)
    mermaid_blocks: List[Dict] = field(default_factory=list)
    children: List['OrgSection'] = field(default_factory=list)


@dataclass
class OrgDocument:
    """Org 문서 데이터"""
    title: str = ""
    hwpx_template: str = ""
    author: str = ""
    date: str = ""
    sections: List[OrgSection] = field(default_factory=list)


def parse_org_file(org_path: Path) -> OrgDocument:
    """Org 파일 파싱"""
    doc = OrgDocument()
    current_section: Optional[OrgSection] = None
    in_src_block = False
    src_block_type = ""
    src_block_name = ""
    src_block_content = []
    properties = {}
    in_properties = False

    with open(org_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 메타데이터 파싱
        if stripped.startswith('#+TITLE:'):
            doc.title = stripped[8:].strip()
        elif stripped.startswith('#+HWPX_TEMPLATE:'):
            doc.hwpx_template = stripped[16:].strip()
        elif stripped.startswith('#+AUTHOR:'):
            doc.author = stripped[9:].strip()
        elif stripped.startswith('#+DATE:'):
            doc.date = stripped[7:].strip()

        # PROPERTIES 블록
        elif stripped == ':PROPERTIES:':
            in_properties = True
            properties = {}
        elif stripped == ':END:' and in_properties:
            in_properties = False
            if current_section and 'HWPX_SECTION' in properties:
                current_section.hwpx_section = properties['HWPX_SECTION']
        elif in_properties and stripped.startswith(':') and ':' in stripped[1:]:
            key, value = stripped[1:].split(':', 1)
            properties[key.strip()] = value.strip()

        # SRC 블록
        elif stripped.startswith('#+BEGIN_SRC'):
            in_src_block = True
            src_block_content = []
            # #+BEGIN_SRC asciidoc :name 테이블명
            parts = stripped[11:].strip().split()
            src_block_type = parts[0] if parts else ""
            src_block_name = ""
            for j, p in enumerate(parts):
                if p == ':name' and j + 1 < len(parts):
                    src_block_name = parts[j + 1]
                elif p == ':file' and j + 1 < len(parts):
                    src_block_name = parts[j + 1]

        elif stripped == '#+END_SRC' and in_src_block:
            in_src_block = False
            if current_section:
                block_data = {
                    'name': src_block_name,
                    'content': '\n'.join(src_block_content)
                }
                if src_block_type == 'asciidoc':
                    current_section.asciidoc_blocks.append(block_data)
                elif src_block_type == 'mermaid':
                    current_section.mermaid_blocks.append(block_data)

        elif in_src_block:
            src_block_content.append(line.rstrip())

        # 헤딩 파싱
        elif stripped.startswith('*') and ' ' in stripped:
            match = re.match(r'^(\*+)\s+(.+)$', stripped)
            if match:
                level = len(match.group(1))
                title = match.group(2)

                new_section = OrgSection(level=level, title=title)

                if level == 1:
                    doc.sections.append(new_section)
                    current_section = new_section
                elif current_section:
                    # 하위 섹션은 현재 섹션의 content에 포함
                    pass

                current_section = new_section

        # 일반 텍스트
        elif current_section and not in_properties:
            current_section.content += line

        i += 1

    return doc


def create_hwpx_paragraph(text: str, para_id: int = 0) -> ET.Element:
    """HWPX 문단 요소 생성"""
    p = ET.Element('{http://www.hancom.co.kr/hwpml/2011/paragraph}p')
    p.set('id', str(para_id))
    p.set('paraPrIDRef', '0')
    p.set('styleIDRef', '0')

    run = ET.SubElement(p, '{http://www.hancom.co.kr/hwpml/2011/paragraph}run')
    run.set('charPrIDRef', '0')

    t = ET.SubElement(run, '{http://www.hancom.co.kr/hwpml/2011/paragraph}t')
    t.text = text

    return p


def convert_org_to_hwpx(org_doc: OrgDocument, template_path: Path, output_path: Path):
    """Org 문서를 HWPX로 변환"""

    # 템플릿 압축 해제
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        with zipfile.ZipFile(template_path, 'r') as zf:
            zf.extractall(tmpdir)

        logger.info(f"템플릿 압축 해제: {template_path}")

        # 각 섹션 처리
        for section in org_doc.sections:
            if section.hwpx_section:
                section_file = tmpdir / 'Contents' / f'{section.hwpx_section}.xml'
                if section_file.exists():
                    logger.info(f"섹션 처리: {section.hwpx_section} - {section.title}")

                    # XML 파싱
                    tree = ET.parse(section_file)
                    root = tree.getroot()

                    # 기존 문단들 가져오기
                    paragraphs = root.findall('.//{http://www.hancom.co.kr/hwpml/2011/paragraph}p')

                    # 첫 번째 문단 찾기 (텍스트 삽입 위치)
                    if paragraphs:
                        # 섹션 제목과 내용을 첫 문단에 추가
                        first_p = paragraphs[0]
                        run = first_p.find('{http://www.hancom.co.kr/hwpml/2011/paragraph}run')
                        if run is not None:
                            t = run.find('{http://www.hancom.co.kr/hwpml/2011/paragraph}t')
                            if t is not None:
                                # 기존 텍스트에 Org 내용 추가
                                original = t.text or ""
                                org_content = f"\n\n[Org 삽입: {section.title}]\n{section.content.strip()}"
                                t.text = original + org_content

                    # XML 저장
                    tree.write(section_file, encoding='UTF-8', xml_declaration=True)
                    logger.info(f"섹션 저장: {section_file}")

        # HWPX 재압축
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in tmpdir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(tmpdir)
                    zf.write(file_path, arcname)

        logger.info(f"HWPX 생성 완료: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Org-mode → HWPX 변환기')
    parser.add_argument('input', help='입력 Org 파일')
    parser.add_argument('-t', '--template', required=True, help='HWPX 템플릿 파일')
    parser.add_argument('-o', '--output', help='출력 HWPX 파일')
    parser.add_argument('-v', '--verbose', action='store_true', help='상세 로그')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    input_path = Path(args.input)
    template_path = Path(args.template)
    output_path = Path(args.output) if args.output else input_path.with_suffix('.hwpx')

    # Org 파일 파싱
    logger.info(f"Org 파일 파싱: {input_path}")
    org_doc = parse_org_file(input_path)

    logger.info(f"  제목: {org_doc.title}")
    logger.info(f"  템플릿: {org_doc.hwpx_template}")
    logger.info(f"  섹션 수: {len(org_doc.sections)}")

    for section in org_doc.sections:
        logger.info(f"    - {section.title} → {section.hwpx_section or '(미지정)'}")
        logger.info(f"      AsciiDoc 블록: {len(section.asciidoc_blocks)}")
        logger.info(f"      Mermaid 블록: {len(section.mermaid_blocks)}")

    # HWPX 변환
    convert_org_to_hwpx(org_doc, template_path, output_path)


if __name__ == '__main__':
    main()

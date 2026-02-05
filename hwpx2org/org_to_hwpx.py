#!/usr/bin/env python3
"""
Org-mode → HWPX 역변환기 (장별 변환용)

v2-hybrid: python-hwpx + ET + patch_hwpx_binary (서식 100% 보존)
단일 장(chapter) HWPX 파일 단위로 라운드트립합니다.

사용법:
    python org_to_hwpx.py ch1.org -t samples/ch1.hwpx -o output/ch1.hwpx
    python org_to_hwpx.py ch2.org -t samples/ch2.hwpx -o output/ch2.hwpx
"""

import argparse
import logging
import re
import struct
import zipfile
import zlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from copy import deepcopy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from asciidoc_parser import parse_asciidoc_table, AsciiDocTable, AsciiDocCell
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from asciidoc_parser import parse_asciidoc_table, AsciiDocTable, AsciiDocCell


# ============================================================
# HWPX XML 네임스페이스 (전체)
# ============================================================
NAMESPACES = {
    'ha': 'http://www.hancom.co.kr/hwpml/2011/app',
    'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hp10': 'http://www.hancom.co.kr/hwpml/2016/paragraph',
    'hs': 'http://www.hancom.co.kr/hwpml/2011/section',
    'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
    'hh': 'http://www.hancom.co.kr/hwpml/2011/head',
    'hhs': 'http://www.hancom.co.kr/hwpml/2011/history',
    'hm': 'http://www.hancom.co.kr/hwpml/2011/master-page',
    'hpf': 'http://www.hancom.co.kr/schema/2011/hpf',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'opf': 'http://www.idpf.org/2007/opf/',
    'ooxmlchart': 'http://www.hancom.co.kr/hwpml/2016/ooxmlchart',
    'epub': 'http://www.idpf.org/2007/ops',
    'config': 'urn:oasis:names:tc:opendocument:xmlns:config:1.0',
}

ALL_NS_DECL = ' '.join(f'xmlns:{k}="{v}"' for k, v in NAMESPACES.items())

for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix, uri)

HP = NAMESPACES['hp']
HS = NAMESPACES['hs']


# ============================================================
# Org 파서
# ============================================================
@dataclass
class OrgElement:
    hwpx_idx: Optional[int] = None

@dataclass
class OrgHeading(OrgElement):
    level: int = 0
    title: str = ""

@dataclass
class OrgParagraph(OrgElement):
    text: str = ""

@dataclass
class OrgTable(OrgElement):
    table: Optional[AsciiDocTable] = None
    name: str = ""

@dataclass
class OrgDocument:
    title: str = ""
    date: str = ""
    elements: List[OrgElement] = field(default_factory=list)


HEADING_BULLETS = {
    1: '', 2: '',
    3: '□ ', 4: 'o ', 5: '- ', 6: '⋅', 7: '',
}


def parse_org_file(org_path: Path) -> OrgDocument:
    """Org 파일 파싱 (HWPX_IDX 태그 지원)"""
    doc = OrgDocument()
    with open(org_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    i = 0
    pending_hwpx_idx: Optional[int] = None

    while i < len(lines):
        line = lines[i]

        if line.startswith('#+TITLE:'):
            doc.title = line[8:].strip()
            i += 1; continue
        elif line.startswith('#+DATE:'):
            doc.date = line[7:].strip()
            i += 1; continue

        hwpx_match = re.match(r'^#\+HWPX:\s*(\d+)', line)
        if hwpx_match:
            pending_hwpx_idx = int(hwpx_match.group(1))
            i += 1; continue

        # AsciiDoc 표 블록
        if line.strip().startswith('#+BEGIN_SRC asciidoc'):
            name_match = re.search(r':name\s+(.+)$', line)
            table_name = name_match.group(1).strip() if name_match else ""
            block_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('#+END_SRC'):
                block_lines.append(lines[i])
                i += 1
            block_content = '\n'.join(block_lines)
            if '|===' in block_content:
                table = parse_asciidoc_table(block_content)
                if table.rows:
                    elem = OrgTable(table=table, name=table_name)
                    elem.hwpx_idx = pending_hwpx_idx
                    doc.elements.append(elem)
            pending_hwpx_idx = None
            i += 1; continue

        if line.strip().startswith('#+BEGIN_EXAMPLE'):
            pending_hwpx_idx = None
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('#+END_EXAMPLE'):
                i += 1
            i += 1; continue

        if line.startswith('#+'):
            i += 1; continue

        heading_match = re.match(r'^(\*+)\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2)
            elem = OrgHeading(level=level, title=title)

            if i + 1 < len(lines) and lines[i + 1].strip() == ':PROPERTIES:':
                j = i + 2
                while j < len(lines) and lines[j].strip() != ':END:':
                    idx_match = re.match(r'\s*:HWPX_IDX:\s*(\d+)', lines[j])
                    if idx_match:
                        elem.hwpx_idx = int(idx_match.group(1))
                    j += 1
                i = j + 1
            else:
                i += 1

            doc.elements.append(elem)
            pending_hwpx_idx = None
            continue

        if line.strip():
            elem = OrgParagraph(text=line.strip())
            elem.hwpx_idx = pending_hwpx_idx
            doc.elements.append(elem)
            pending_hwpx_idx = None
        i += 1

    return doc


# ============================================================
# HWPX XML 헬퍼
# ============================================================
def _fix_hwpx_xml(xml_str: str) -> str:
    """ET.tostring() 출력을 한컴 호환 XML로 후처리"""
    xml_str = re.sub(r'<hp:t\s*/>', '<hp:t/>', xml_str)
    xml_str = re.sub(r'\s+/>', '/>', xml_str)
    return xml_str


def hp_tag(name: str) -> str:
    return f'{{{HP}}}{name}'


def heading_to_hwpx_text(heading: OrgHeading) -> str:
    title = heading.title
    if re.match(r'^\d+[\.-]', title):
        return title
    clean_title = re.sub(r'^[□○o\-⋅·]\s*', '', title)
    bullet = HEADING_BULLETS.get(heading.level, '')
    return f"{bullet}{clean_title}"


# ============================================================
# 바이너리 ZIP 패처 (한컴 HWPX 호환)
# ============================================================
def _parse_zip_structure(data: bytes) -> Tuple[list, int, int, int]:
    """ZIP 파일의 Central Directory 구조를 파싱"""
    eocd_off = data.rfind(b'PK\x05\x06')
    if eocd_off < 0:
        raise ValueError("EOCD not found")

    cd_off = struct.unpack_from('<I', data, eocd_off + 16)[0]
    cd_size = struct.unpack_from('<I', data, eocd_off + 12)[0]
    num_entries = struct.unpack_from('<H', data, eocd_off + 10)[0]

    cd_entries = []
    off = cd_off
    for _ in range(num_entries):
        nlen = struct.unpack_from('<H', data, off + 28)[0]
        elen = struct.unpack_from('<H', data, off + 30)[0]
        clen = struct.unpack_from('<H', data, off + 32)[0]
        name = data[off + 46:off + 46 + nlen].decode('utf-8')
        cd_entries.append({
            'cd_off': off,
            'cd_size': 46 + nlen + elen + clen,
            'name': name,
            'crc32': struct.unpack_from('<I', data, off + 16)[0],
            'comp_size': struct.unpack_from('<I', data, off + 20)[0],
            'uncomp_size': struct.unpack_from('<I', data, off + 24)[0],
            'local_off': struct.unpack_from('<I', data, off + 42)[0],
        })
        off += 46 + nlen + elen + clen

    return cd_entries, cd_off, eocd_off, num_entries


def patch_hwpx_binary(template_path: Path, new_section_xml: bytes, output_path: Path):
    """템플릿 HWPX의 바이너리를 수술적으로 수정하여 section0.xml만 교체

    한컴의 독자적 ZIP 구현(flags=0x0004 + 실제값 in 로컬헤더 + DD 없음)을 그대로 유지.
    """
    with open(template_path, 'rb') as f:
        data = f.read()

    cd_entries, cd_off, eocd_off, num_entries = _parse_zip_structure(data)

    target = 'Contents/section0.xml'
    sec_entry = None
    for ce in cd_entries:
        if ce['name'] == target:
            sec_entry = ce
            break

    if sec_entry is None:
        raise ValueError(f'{target} not found in template')

    loc_off = sec_entry['local_off']
    nlen = struct.unpack_from('<H', data, loc_off + 26)[0]
    elen = struct.unpack_from('<H', data, loc_off + 28)[0]
    data_start = loc_off + 30 + nlen + elen
    old_comp_size = sec_entry['comp_size']
    data_end = data_start + old_comp_size

    new_crc = zlib.crc32(new_section_xml) & 0xFFFFFFFF
    new_uncomp_size = len(new_section_xml)

    compressor = zlib.compressobj(2, zlib.DEFLATED, -15)
    new_compressed = compressor.compress(new_section_xml) + compressor.flush()
    new_comp_size = len(new_compressed)
    delta = new_comp_size - old_comp_size

    logger.info(f"section0.xml 압축: {new_uncomp_size} → {new_comp_size} bytes (delta={delta:+d})")

    result = bytearray()
    result.extend(data[:data_start])
    result.extend(new_compressed)
    result.extend(data[data_end:cd_off])
    new_cd_off = len(result)
    result.extend(data[cd_off:eocd_off])
    new_eocd_off = len(result)
    result.extend(data[eocd_off:])

    struct.pack_into('<I', result, loc_off + 14, new_crc)
    struct.pack_into('<I', result, loc_off + 18, new_comp_size)
    struct.pack_into('<I', result, loc_off + 22, new_uncomp_size)

    for ce in cd_entries:
        ce_new_off = new_cd_off + (ce['cd_off'] - cd_off)
        if ce['name'] == target:
            struct.pack_into('<I', result, ce_new_off + 16, new_crc)
            struct.pack_into('<I', result, ce_new_off + 20, new_comp_size)
            struct.pack_into('<I', result, ce_new_off + 24, new_uncomp_size)
        elif ce['local_off'] >= data_end:
            new_local_off = ce['local_off'] + delta
            struct.pack_into('<I', result, ce_new_off + 42, new_local_off)

    struct.pack_into('<I', result, new_eocd_off + 16, new_cd_off)

    with open(output_path, 'wb') as f:
        f.write(result)

    logger.info(f"HWPX 바이너리 패치 완료: {output_path} ({len(result)} bytes)")


# ============================================================
# v2-hybrid: python-hwpx + ET + patch_hwpx_binary
# ============================================================
def _get_toplevel_p_text(p_el: ET.Element) -> str:
    """top-level <hp:p>에서 run의 <hp:t> 텍스트 추출 (테이블 내부 제외)"""
    texts = []
    for run in p_el:
        if run.tag != hp_tag('run'):
            continue
        for child in run:
            if child.tag == hp_tag('tbl'):
                break
            if child.tag == hp_tag('t') and child.text:
                texts.append(child.text)
    return ''.join(texts)


def convert_org_to_hwpx(org_doc: OrgDocument, template_path: Path, output_path: Path):
    """v2-hybrid: python-hwpx + ET + patch_hwpx_binary (서식 100% 보존)"""
    from hwpx.document import HwpxDocument

    if not template_path or not template_path.exists():
        logger.error(f"템플릿 필수: {template_path}")
        return

    doc = HwpxDocument.open(str(template_path))
    section_elem = doc.sections[0].element

    p_tag_name = hp_tag('p')
    toplevel_ps = [child for child in section_elem if child.tag == p_tag_name]
    logger.info(f"원본 top-level <hp:p>: {len(toplevel_ps)}개")

    matched = 0
    skipped = 0
    failed = 0

    for elem in org_doc.elements:
        idx = elem.hwpx_idx
        if idx is None or idx < 0 or idx >= len(toplevel_ps):
            continue

        if not isinstance(elem, (OrgHeading, OrgParagraph)):
            continue

        new_text = heading_to_hwpx_text(elem) if isinstance(elem, OrgHeading) else elem.text
        current_text = _get_toplevel_p_text(toplevel_ps[idx])

        if current_text.strip() == new_text.strip():
            skipped += 1
            continue

        if not current_text.strip():
            skipped += 1
            continue

        count = doc.replace_text_in_runs(current_text, new_text)
        if count > 0:
            matched += 1
            logger.debug(f"[{idx}] 교체({count}): '{current_text[:30]}' → '{new_text[:30]}'")
        else:
            failed += 1
            logger.warning(f"[{idx}] 매칭 실패 (skip): '{current_text[:60]}'")

    logger.info(f"매칭 결과: {matched}개 교체, {skipped}개 동일, {failed}개 실패(skip)")

    # ET 직렬화 + 전체 네임스페이스 선언
    xml_str = ET.tostring(section_elem, encoding='unicode')
    xml_str = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>' + xml_str
    xml_str = re.sub(r'<hs:sec[^>]*>', f'<hs:sec {ALL_NS_DECL}>', xml_str, count=1)
    xml_str = _fix_hwpx_xml(xml_str)
    new_section_xml = xml_str.encode('utf-8')

    logger.info(f"v2-hybrid section0.xml: {len(new_section_xml)} bytes")

    patch_hwpx_binary(template_path, new_section_xml, output_path)
    logger.info(f"v2-hybrid HWPX 저장: {output_path}")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description='Org-mode → HWPX 역변환기 (장별, v2-hybrid)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    python org_to_hwpx.py ch1.org -t samples/ch1.hwpx -o output/ch1.hwpx
    python org_to_hwpx.py ch2.org -t samples/ch2.hwpx -o output/ch2.hwpx
"""
    )
    parser.add_argument('input', help='입력 Org 파일')
    parser.add_argument('-t', '--template', required=True, help='HWPX 템플릿 파일 (원본 장 HWPX)')
    parser.add_argument('-o', '--output', help='출력 HWPX 파일')
    parser.add_argument('-v', '--verbose', action='store_true', help='상세 로그')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    input_path = Path(args.input)
    template_path = Path(args.template)
    output_path = Path(args.output) if args.output else input_path.with_suffix('.hwpx')

    logger.info(f"Org 파일 파싱: {input_path}")
    org_doc = parse_org_file(input_path)

    headings = sum(1 for e in org_doc.elements if isinstance(e, OrgHeading))
    tables = sum(1 for e in org_doc.elements if isinstance(e, OrgTable))
    paragraphs = sum(1 for e in org_doc.elements if isinstance(e, OrgParagraph))
    tagged = sum(1 for e in org_doc.elements if e.hwpx_idx is not None)

    logger.info(f"  제목: {org_doc.title}")
    logger.info(f"  헤딩: {headings}개, 표: {tables}개, 문단: {paragraphs}개")
    logger.info(f"  HWPX_IDX 태그: {tagged}개")

    if tagged == 0:
        logger.error("HWPX_IDX 태그가 없습니다. hwpx_to_org.py로 먼저 변환하세요.")
        return

    convert_org_to_hwpx(org_doc, template_path, output_path)


if __name__ == '__main__':
    main()

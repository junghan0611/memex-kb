#!/usr/bin/env python3
"""
Org-mode → HWPX 역변환기

Org 파일에서 헤딩과 AsciiDoc 표를 추출하여 HWPX 템플릿에 삽입합니다.
hwpx_to_org.py의 역변환입니다.

전략:
    1. template.hwpx의 모든 파일(header.xml, 스타일 등)을 보존
    2. section0.xml: 첫 문단(셋업)을 원본 그대로 보존 + 내용 교체
    3. 모든 문단에 linesegarray 포함 (필수)
    4. 템플릿에서 추출한 스타일 ID 매핑 사용

사용법:
    python org_to_hwpx.py input.org -t template.hwpx -o output.hwpx
"""

import argparse
import logging
import re
import struct
import tempfile
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from copy import deepcopy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# AsciiDoc 파서 임포트
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

import xml.etree.ElementTree as ET
for prefix, uri in NAMESPACES.items():
    ET.register_namespace(prefix, uri)

HP = NAMESPACES['hp']
HS = NAMESPACES['hs']


# ============================================================
# 스타일 ID 매핑 (template.hwpx 분석 결과)
# ============================================================
@dataclass
class StyleMapping:
    """HWPX 스타일 ID 조합"""
    style_id_ref: str
    para_pr_id_ref: str
    char_pr_id_ref: str


STYLE_MAP = {
    'H1':          StyleMapping('177', '65', '59'),
    'H2':          StyleMapping('177', '21', '59'),
    'H3':          StyleMapping('15',  '39', '29'),
    'H4':          StyleMapping('15',  '39', '29'),
    'H5':          StyleMapping('15',  '39', '29'),
    'H6':          StyleMapping('15',  '73', '29'),
    'BODY':        StyleMapping('15',  '75', '65'),
    'TABLE_TITLE': StyleMapping('15',  '12', '2'),
    'TABLE_BODY':  StyleMapping('15',  '12', '29'),
}

# paraPrIDRef별 lineseg 기본값 (template.hwpx에서 추출)
LINESEG_DEFAULTS: Dict[str, Dict[str, str]] = {
    '65':  {'vertsize': '1300', 'textheight': '1300', 'baseline': '1105', 'spacing': '780'},
    '21':  {'vertsize': '1300', 'textheight': '1300', 'baseline': '1105', 'spacing': '780'},
    '39':  {'vertsize': '1300', 'textheight': '1300', 'baseline': '1105', 'spacing': '780'},
    '73':  {'vertsize': '1200', 'textheight': '1200', 'baseline': '1020', 'spacing': '720'},
    '75':  {'vertsize': '1200', 'textheight': '1200', 'baseline': '1020', 'spacing': '720'},
    '12':  {'vertsize': '800',  'textheight': '800',  'baseline': '680',  'spacing': '480'},
    '24':  {'vertsize': '800',  'textheight': '800',  'baseline': '680',  'spacing': '480'},
}
LINESEG_FALLBACK = {'vertsize': '1200', 'textheight': '1200', 'baseline': '1020', 'spacing': '720'}

HEADING_BULLETS = {
    1: '', 2: '',
    3: '□ ', 4: 'o ', 5: '- ', 6: '⋅', 7: '',
}


# ============================================================
# Org 파서
# ============================================================
@dataclass
class OrgElement:
    hwpx_idx: Optional[int] = None  # v2: 원본 HWPX 문단 인덱스

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


def parse_org_file(org_path: Path) -> OrgDocument:
    """Org 파일 파싱 (v2: HWPX_IDX 태그 지원)"""
    doc = OrgDocument()
    with open(org_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    i = 0
    # v2: 다음 요소에 적용할 HWPX 인덱스 (#+HWPX: N으로 설정)
    pending_hwpx_idx: Optional[int] = None

    while i < len(lines):
        line = lines[i]

        if line.startswith('#+TITLE:'):
            doc.title = line[8:].strip()
            i += 1; continue
        elif line.startswith('#+DATE:'):
            doc.date = line[7:].strip()
            i += 1; continue

        # v2: #+HWPX: N 키워드 → 다음 요소에 인덱스 부여
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
                    logger.debug(f"테이블: {table_name} ({len(table.rows)}행)")
            pending_hwpx_idx = None
            i += 1; continue

        if line.strip().startswith('#+BEGIN_EXAMPLE'):
            # 작성요령 블록도 HWPX_IDX 보존
            example_hwpx_idx = pending_hwpx_idx
            pending_hwpx_idx = None
            block_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('#+END_EXAMPLE'):
                block_lines.append(lines[i])
                i += 1
            # EXAMPLE 블록은 현재 v1과 동일하게 skip
            i += 1; continue

        if line.startswith('#+'):
            i += 1; continue

        heading_match = re.match(r'^(\*+)\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2)
            elem = OrgHeading(level=level, title=title)

            # v2: :PROPERTIES: 드로어에서 :HWPX_IDX: 파싱
            if i + 1 < len(lines) and lines[i + 1].strip() == ':PROPERTIES:':
                j = i + 2
                while j < len(lines) and lines[j].strip() != ':END:':
                    idx_match = re.match(r'\s*:HWPX_IDX:\s*(\d+)', lines[j])
                    if idx_match:
                        elem.hwpx_idx = int(idx_match.group(1))
                    j += 1
                i = j + 1  # :END: 다음 줄로
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
# HWPX XML 생성 헬퍼
# ============================================================
def _fix_hwpx_xml(xml_str: str) -> str:
    """ET.tostring() 출력을 한컴 호환 XML로 후처리

    1. self-closing 태그 공백 제거: ' />' → '/>'
    2. 빈 <hp:t /> → <hp:t></hp:t> 복원 (한컴은 빈 self-closing <hp:t/>도 허용하지만
       ET가 원본 <hp:t>텍스트</hp:t>를 <hp:t /> 로 바꾸는 것이 문제)
    """
    # 빈 hp:t self-closing → 원본 형태 복원
    xml_str = re.sub(r'<hp:t\s*/>', '<hp:t/>', xml_str)
    # 나머지 모든 self-closing 태그의 공백 제거
    xml_str = re.sub(r'\s+/>', '/>', xml_str)
    return xml_str


def hp_tag(name: str) -> str:
    return f'{{{HP}}}{name}'

def hs_tag(name: str) -> str:
    return f'{{{HS}}}{name}'


def get_style(element_type: str) -> StyleMapping:
    return STYLE_MAP.get(element_type, STYLE_MAP['BODY'])


def heading_to_hwpx_text(heading: OrgHeading) -> str:
    title = heading.title
    if re.match(r'^\d+[\.-]', title):
        return title
    clean_title = re.sub(r'^[□○o\-⋅·]\s*', '', title)
    bullet = HEADING_BULLETS.get(heading.level, '')
    return f"{bullet}{clean_title}"


def get_heading_style_key(heading: OrgHeading) -> str:
    level = min(heading.level, 6)
    return f'H{level}'


def create_linesegarray(para_pr_id: str, page_width: str = '48188') -> ET.Element:
    """linesegarray 요소 생성 (모든 문단에 필수)"""
    lsa = ET.Element(hp_tag('linesegarray'))
    seg = ET.SubElement(lsa, hp_tag('lineseg'))

    defaults = LINESEG_DEFAULTS.get(para_pr_id, LINESEG_FALLBACK)
    seg.set('textpos', '0')
    seg.set('vertpos', '0')
    seg.set('vertsize', defaults['vertsize'])
    seg.set('textheight', defaults['textheight'])
    seg.set('baseline', defaults['baseline'])
    seg.set('spacing', defaults['spacing'])
    seg.set('horzpos', '0')
    seg.set('horzsize', page_width)
    seg.set('flags', '393216')

    return lsa


def create_p_element(text: str, style: StyleMapping, para_id: int = 0) -> ET.Element:
    """HWPX 문단 요소 생성 (linesegarray 포함)"""
    p = ET.Element(hp_tag('p'))
    p.set('id', str(para_id))
    p.set('paraPrIDRef', style.para_pr_id_ref)
    p.set('styleIDRef', style.style_id_ref)
    p.set('pageBreak', '0')
    p.set('columnBreak', '0')
    p.set('merged', '0')

    run = ET.SubElement(p, hp_tag('run'))
    run.set('charPrIDRef', style.char_pr_id_ref)

    t = ET.SubElement(run, hp_tag('t'))
    t.text = text

    # linesegarray 추가
    p.append(create_linesegarray(style.para_pr_id_ref))

    return p


def create_table_p_element(table: AsciiDocTable, table_name: str,
                           table_id: int, para_id: int,
                           page_width: int = 48188) -> ET.Element:
    """테이블 포함 문단 요소 생성

    구조: <hp:p> > <hp:run> > <hp:tbl> > <hp:tr> > <hp:tc>
    tc 내부: <subList> > <p> > <run> > <t> + cellAddr + cellSpan + cellSz + cellMargin
    """
    style = get_style('TABLE_BODY')

    p = ET.Element(hp_tag('p'))
    p.set('id', str(para_id))
    p.set('paraPrIDRef', style.para_pr_id_ref)
    p.set('styleIDRef', style.style_id_ref)
    p.set('pageBreak', '0')
    p.set('columnBreak', '0')
    p.set('merged', '0')

    run = ET.SubElement(p, hp_tag('run'))
    run.set('charPrIDRef', style.char_pr_id_ref)

    row_count = len(table.rows)
    col_count = table.col_count or (len(table.rows[0]) if table.rows else 1)

    tbl = ET.SubElement(run, hp_tag('tbl'))
    tbl.set('id', str(table_id))
    tbl.set('zOrder', '0')
    tbl.set('numberingType', 'TABLE')
    tbl.set('textWrap', 'TOP_AND_BOTTOM')
    tbl.set('textFlow', 'BOTH_SIDES')
    tbl.set('lock', '0')
    tbl.set('dropcapstyle', 'None')
    tbl.set('pageBreak', 'CELL')
    tbl.set('repeatHeader', '0')
    tbl.set('rowCnt', str(row_count))
    tbl.set('colCnt', str(col_count))
    tbl.set('cellSpacing', '0')
    tbl.set('borderFillIDRef', '3')
    tbl.set('noAdjust', '0')

    col_width = page_width // col_count

    def _create_tc(tr_el, text, col_idx, row_idx, col_span=1, row_span=1, is_header=False):
        """단일 테이블 셀(tc) 생성"""
        tc = ET.SubElement(tr_el, hp_tag('tc'))
        tc.set('name', '')
        tc.set('header', '1' if is_header else '0')
        tc.set('hasMargin', '0')
        tc.set('protect', '0')
        tc.set('editable', '0')
        tc.set('dirty', '0')
        tc.set('borderFillIDRef', '3')

        sub_list = ET.SubElement(tc, hp_tag('subList'))
        sub_list.set('id', '')
        sub_list.set('textDirection', 'HORIZONTAL')
        sub_list.set('lineWrap', 'BREAK')
        sub_list.set('vertAlign', 'CENTER')
        sub_list.set('linkListIDRef', '0')
        sub_list.set('linkListNextIDRef', '0')
        sub_list.set('textWidth', '0')
        sub_list.set('textHeight', '0')
        sub_list.set('hasTextRef', '0')
        sub_list.set('hasNumRef', '0')

        cell_p = ET.SubElement(sub_list, hp_tag('p'))
        cell_p.set('id', '0')
        cell_p.set('paraPrIDRef', '24')
        cell_p.set('styleIDRef', '0')
        cell_p.set('pageBreak', '0')
        cell_p.set('columnBreak', '0')
        cell_p.set('merged', '0')

        cell_run = ET.SubElement(cell_p, hp_tag('run'))
        cell_run.set('charPrIDRef', '80')

        cell_t = ET.SubElement(cell_run, hp_tag('t'))
        cell_t.text = text or ''

        cell_lsa = create_linesegarray('24', str(col_width * col_span - 1020))
        cell_p.append(cell_lsa)

        cell_addr = ET.SubElement(tc, hp_tag('cellAddr'))
        cell_addr.set('colAddr', str(col_idx))
        cell_addr.set('rowAddr', str(row_idx))

        cell_span_el = ET.SubElement(tc, hp_tag('cellSpan'))
        cell_span_el.set('colSpan', str(col_span))
        cell_span_el.set('rowSpan', str(row_span))

        cell_sz = ET.SubElement(tc, hp_tag('cellSz'))
        cell_sz.set('width', str(col_width * col_span))
        cell_sz.set('height', '282')

        cell_margin = ET.SubElement(tc, hp_tag('cellMargin'))
        cell_margin.set('left', '510')
        cell_margin.set('right', '510')
        cell_margin.set('top', '141')
        cell_margin.set('bottom', '141')

    for row_idx, row in enumerate(table.rows):
        tr = ET.SubElement(tbl, hp_tag('tr'))

        col_idx = 0
        for cell in row:
            _create_tc(tr, cell.text, col_idx, row_idx,
                        cell.col_span, cell.row_span, row_idx == 0)
            col_idx += cell.col_span

        # 행에 셀이 부족하면 빈 셀로 채움 (colCnt 불일치 → segfault 방지)
        while col_idx < col_count:
            _create_tc(tr, '', col_idx, row_idx)
            col_idx += 1

    # run 끝 빈 텍스트
    t = ET.SubElement(run, hp_tag('t'))
    t.text = ''

    # 문단 linesegarray
    p.append(create_linesegarray(style.para_pr_id_ref))

    return p


# ============================================================
# 섹션 빌드
# ============================================================
def extract_first_paragraph(section_xml: bytes) -> Optional[ET.Element]:
    """원본 section0.xml에서 첫 번째 문단(셋업) 그대로 추출

    이 문단은 secPr(페이지 설정), ctrl(colPr, pageNum), linesegarray를 포함합니다.
    """
    root = ET.fromstring(section_xml)
    for child in root:
        if child.tag.endswith('}p'):
            return child
    return None


def build_section_xml(org_doc: OrgDocument, setup_p: Optional[ET.Element]) -> ET.Element:
    """Org 문서로부터 새 section0.xml 루트 생성"""
    root = ET.Element(hs_tag('sec'))

    # 1. 원본 첫 문단(셋업) 그대로 삽입
    if setup_p is not None:
        root.append(deepcopy(setup_p))

    # 2. 내용 문단 추가
    para_id = 100
    table_id = 1000000000

    for elem in org_doc.elements:
        if isinstance(elem, OrgHeading):
            text = heading_to_hwpx_text(elem)
            style_key = get_heading_style_key(elem)
            style = get_style(style_key)
            p = create_p_element(text, style, para_id)
            root.append(p)
            para_id += 1

        elif isinstance(elem, OrgParagraph):
            style = get_style('BODY')
            p = create_p_element(elem.text, style, para_id)
            root.append(p)
            para_id += 1

        elif isinstance(elem, OrgTable):
            if elem.name:
                style = get_style('TABLE_TITLE')
                title_p = create_p_element(f"<{elem.name}>", style, para_id)
                root.append(title_p)
                para_id += 1

            table_p = create_table_p_element(
                elem.table, elem.name, table_id, para_id
            )
            root.append(table_p)
            para_id += 1
            table_id += 1

    return root


# ============================================================
# 바이너리 ZIP 패처 (한컴 HWPX 호환)
# ============================================================
def _parse_zip_structure(data: bytes) -> Tuple[list, int, int, int]:
    """ZIP 파일의 Central Directory 구조를 파싱

    Returns:
        (cd_entries, cd_offset, eocd_offset, num_entries)
    """
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

    ZIP 헤더(ver_made, flags, dates, ext_attr 등)를 바이트 단위로 완벽 보존.
    한컴의 독자적 ZIP 구현(flags=0x0004 + 실제값 in 로컬헤더 + DD 없음)을 그대로 유지.

    처리 흐름:
        1. 템플릿을 raw bytes로 읽기
        2. section0.xml의 압축 데이터 영역만 교체
        3. CRC/sizes 업데이트 (로컬 헤더 + Central Directory)
        4. 후속 엔트리들의 offset 보정
        5. EOCD의 CD offset 보정
    """
    with open(template_path, 'rb') as f:
        data = f.read()

    cd_entries, cd_off, eocd_off, num_entries = _parse_zip_structure(data)

    # section0.xml 엔트리 찾기
    target = 'Contents/section0.xml'
    sec_entry = None
    for ce in cd_entries:
        if ce['name'] == target:
            sec_entry = ce
            break

    if sec_entry is None:
        raise ValueError(f'{target} not found in template')

    # 로컬 헤더에서 데이터 시작 위치 계산
    loc_off = sec_entry['local_off']
    nlen = struct.unpack_from('<H', data, loc_off + 26)[0]
    elen = struct.unpack_from('<H', data, loc_off + 28)[0]
    data_start = loc_off + 30 + nlen + elen
    old_comp_size = sec_entry['comp_size']
    data_end = data_start + old_comp_size

    logger.debug(f"section0.xml: loc={loc_off}, data=[{data_start}:{data_end}], "
                 f"comp={old_comp_size}, uncomp={sec_entry['uncomp_size']}")

    # 새 데이터 압축 (raw deflate, ZIP 호환)
    new_crc = zlib.crc32(new_section_xml) & 0xFFFFFFFF
    new_uncomp_size = len(new_section_xml)

    # 한컴 HWPX는 zlib level 2로 압축 (원본과 동일한 deflate 스트림 생성)
    compressor = zlib.compressobj(2, zlib.DEFLATED, -15)
    new_compressed = compressor.compress(new_section_xml) + compressor.flush()
    new_comp_size = len(new_compressed)
    delta = new_comp_size - old_comp_size

    logger.info(f"section0.xml 압축: {new_uncomp_size} → {new_comp_size} bytes "
                f"(delta={delta:+d})")

    # 바이너리 조합: [before_data] + [new_compressed] + [after_data..CD] + [CD] + [EOCD]
    result = bytearray()
    result.extend(data[:data_start])          # 모든 헤더+데이터 (section0 데이터 직전까지)
    result.extend(new_compressed)              # 새 압축 데이터
    result.extend(data[data_end:cd_off])       # section0 이후 엔트리들
    new_cd_off = len(result)
    result.extend(data[cd_off:eocd_off])       # Central Directory
    new_eocd_off = len(result)
    result.extend(data[eocd_off:])             # EOCD

    # 로컬 헤더 업데이트: section0.xml의 CRC, comp_size, uncomp_size
    struct.pack_into('<I', result, loc_off + 14, new_crc)
    struct.pack_into('<I', result, loc_off + 18, new_comp_size)
    struct.pack_into('<I', result, loc_off + 22, new_uncomp_size)

    # Central Directory 업데이트
    for ce in cd_entries:
        ce_new_off = new_cd_off + (ce['cd_off'] - cd_off)

        if ce['name'] == target:
            # section0: CRC, comp_size, uncomp_size 업데이트
            struct.pack_into('<I', result, ce_new_off + 16, new_crc)
            struct.pack_into('<I', result, ce_new_off + 20, new_comp_size)
            struct.pack_into('<I', result, ce_new_off + 24, new_uncomp_size)
        elif ce['local_off'] >= data_end:
            # section0 이후 엔트리: local_header_offset 보정
            new_local_off = ce['local_off'] + delta
            struct.pack_into('<I', result, ce_new_off + 42, new_local_off)

    # EOCD 업데이트: CD offset
    struct.pack_into('<I', result, new_eocd_off + 16, new_cd_off)

    with open(output_path, 'wb') as f:
        f.write(result)

    logger.info(f"HWPX 바이너리 패치 완료: {output_path} ({len(result)} bytes)")


# ============================================================
# 변환 메인
# ============================================================
def convert_org_to_hwpx(org_doc: OrgDocument, template_path: Path, output_path: Path):
    """Org 문서를 HWPX로 변환 (바이너리 패치 방식)

    Python zipfile을 사용하지 않고 템플릿의 raw bytes를 수술적으로 수정.
    한컴 HWPX의 독자적 ZIP 헤더(ver_made, flags, dates, ext_attr)를 완벽 보존.
    """
    if not template_path or not template_path.exists():
        logger.error(f"템플릿 필수: {template_path}")
        return

    # 1. 원본 section0.xml에서 첫 문단(셋업) 추출
    with zipfile.ZipFile(template_path, 'r') as zf:
        section_data = zf.read('Contents/section0.xml')

    setup_p = extract_first_paragraph(section_data)
    if setup_p is not None:
        logger.info("셋업 문단 추출 (secPr + ctrl + linesegarray)")

    # 2. 새 section0.xml 생성
    new_root = build_section_xml(org_doc, setup_p)

    # 3. XML 직렬화 (원본과 동일하게 한 줄, 인덴트 없음)
    xml_bytes = ET.tostring(new_root, encoding='unicode')

    # 4. 후처리: XML 선언 + 전체 네임스페이스 + 한컴 호환
    xml_str = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>' + xml_bytes
    xml_str = re.sub(r'<hs:sec[^>]*>', f'<hs:sec {ALL_NS_DECL}>', xml_str, count=1)
    xml_str = _fix_hwpx_xml(xml_str)
    new_section_xml = xml_str.encode('utf-8')

    logger.info(f"section0.xml 생성: {len(org_doc.elements)}개 요소, "
                f"{len(new_section_xml)} bytes")

    # 5. 바이너리 패치로 HWPX 생성
    patch_hwpx_binary(template_path, new_section_xml, output_path)

    logger.info(f"HWPX 저장: {output_path}")


# ============================================================
# v2: 문단 매칭 + 텍스트 교체 (서식 100% 보존)
#
# 핵심: ET.tostring()을 사용하지 않음.
# 원본 XML 바이트를 그대로 유지하고 <hp:t> 태그 내용만 문자열 치환.
# 이렇게 하면 ET roundtrip(\r 정규화, 속성 순서, self-closing 등)을 완전 회피.
# ============================================================
def _find_toplevel_p_ranges(xml_str: str) -> List[Tuple[int, int]]:
    """원본 XML 문자열에서 top-level <hp:p>의 (start, end) 범위 리스트 반환

    중첩된 <hp:p> (테이블 셀 내부)를 구분하기 위해 depth 추적.
    """
    # <hs:sec ...> 뒤부터 탐색
    sec_close = xml_str.index('>', xml_str.index('<hs:sec')) + 1
    content = xml_str[sec_close:]

    ranges = []
    i = 0
    depth = 0
    block_start = -1

    while i < len(content):
        if content[i:i+6] == '<hp:p ' or content[i:i+6] == '<hp:p>':
            if depth == 0:
                block_start = sec_close + i
            depth += 1
            i += 6
        elif content[i:i+7] == '</hp:p>':
            depth -= 1
            if depth == 0 and block_start >= 0:
                block_end = sec_close + i + 7
                ranges.append((block_start, block_end))
                block_start = -1
            i += 7
        else:
            i += 1

    return ranges


def _extract_text_from_block(xml_str: str, start: int, end: int) -> str:
    """XML 블록 문자열에서 top-level run의 <hp:t> 텍스트를 추출

    테이블 셀 내부의 <hp:t>는 제외하고, 직접 자식 run의 텍스트만 추출.
    """
    block = xml_str[start:end]

    # <hp:tbl> 이전의 텍스트만 추출 (테이블 셀 텍스트 제외)
    tbl_pos = block.find('<hp:tbl ')
    if tbl_pos >= 0:
        search_area = block[:tbl_pos]
    else:
        search_area = block

    texts = []
    for m in re.finditer(r'<hp:t>(.*?)</hp:t>', search_area, re.DOTALL):
        texts.append(m.group(1))
    # self-closing <hp:t/> 는 빈 텍스트
    return ''.join(texts)


def _replace_t_in_block(xml_str: str, start: int, end: int,
                        new_text: str) -> str:
    """XML 블록 내 top-level run의 <hp:t> 텍스트를 교체

    <hp:tbl> 이전의 첫 번째 텍스트가 있는 <hp:t>의 순수 텍스트 부분만 교체.
    <hp:tab/>, <hp:lineBreak/> 등 자식 요소는 보존.
    나머지 <hp:t>의 순수 텍스트만 비움.
    <hp:t/> (self-closing)은 건드리지 않음.
    """
    block = xml_str[start:end]

    # 테이블 이전 영역만 처리
    tbl_pos = block.find('<hp:tbl ')
    if tbl_pos >= 0:
        before_tbl = block[:tbl_pos]
        after_tbl = block[tbl_pos:]
    else:
        before_tbl = block
        after_tbl = ''

    # <hp:t>...</hp:t> 패턴 찾기 (self-closing <hp:t/> 제외)
    # 내부에 자식 요소(<hp:tab/>, <hp:lineBreak/> 등)가 있을 수 있음
    t_pattern = re.compile(r'<hp:t>(.*?)</hp:t>', re.DOTALL)
    matches = list(t_pattern.finditer(before_tbl))

    if not matches:
        return xml_str  # 교체 대상 없음

    # 순수 텍스트만 추출하는 헬퍼 (자식 태그 제거)
    def _pure_text(inner: str) -> str:
        return re.sub(r'<[^>]+/?>', '', inner).strip()

    # 텍스트가 있는 첫 번째 <hp:t> 찾기
    target_idx = 0
    for i, m in enumerate(matches):
        if _pure_text(m.group(1)):
            target_idx = i
            break

    # 역순으로 치환 (offset 유지)
    new_before = before_tbl
    for i in range(len(matches) - 1, -1, -1):
        m = matches[i]
        inner = m.group(1)

        # 자식 요소 (<hp:tab/>, <hp:lineBreak/> 등) 추출
        child_elements = re.findall(r'<hp:\w+[^/]*/>', inner)
        children_str = ''.join(child_elements)

        if i == target_idx:
            # 자식 요소 보존 + 새 텍스트
            replacement = f'<hp:t>{children_str}{_escape_xml(new_text)}</hp:t>'
        else:
            # 자식 요소 보존 + 텍스트만 비움
            replacement = f'<hp:t>{children_str}</hp:t>'

        new_before = new_before[:m.start()] + replacement + new_before[m.end():]

    new_block = new_before + after_tbl
    return xml_str[:start] + new_block + xml_str[end:]


def _replace_table_in_block(xml_str: str, start: int, end: int,
                            org_table: 'OrgTable') -> str:
    """XML 블록 내 <hp:tbl>의 셀 텍스트를 교체

    셀별로 (rowAddr, colAddr)를 매칭하여 <hp:t> 텍스트만 교체.
    """
    if not org_table.table or not org_table.table.rows:
        return xml_str

    block = xml_str[start:end]

    # Org 테이블에서 (row, col) → text 매핑
    org_cell_map: Dict[Tuple[int, int], str] = {}
    for row_idx, row in enumerate(org_table.table.rows):
        col_idx = 0
        for cell in row:
            org_cell_map[(row_idx, col_idx)] = cell.text or ''
            col_idx += cell.col_span

    # 각 <hp:tc> 블록을 찾아서 셀 텍스트 교체
    # tc 블록: <hp:tc ...>...</hp:tc>
    result = block
    tc_pattern = re.compile(r'<hp:tc\s[^>]*>.*?</hp:tc>', re.DOTALL)

    # 역순 처리 (offset 변동 방지)
    tc_matches = list(tc_pattern.finditer(result))
    for tc_match in reversed(tc_matches):
        tc_block = tc_match.group()

        # cellAddr 추출
        addr_m = re.search(r'<hp:cellAddr\s+colAddr="(\d+)"\s+rowAddr="(\d+)"', tc_block)
        if not addr_m:
            continue
        col = int(addr_m.group(1))
        row = int(addr_m.group(2))

        new_text = org_cell_map.get((row, col))
        if new_text is None:
            continue

        # 현재 텍스트 확인
        t_matches = list(re.finditer(r'<hp:t>(.*?)</hp:t>', tc_block, re.DOTALL))
        if not t_matches:
            continue
        current = ''.join(m.group(1) for m in t_matches)
        if current.strip() == new_text.strip():
            continue  # 동일 → skip

        # 셀 내 <hp:t> 교체 (첫 번째에 텍스트, 나머지 비움)
        new_tc = tc_block
        for i in range(len(t_matches) - 1, -1, -1):
            m = t_matches[i]
            if i == 0:
                replacement = f'<hp:t>{_escape_xml(new_text)}</hp:t>'
            else:
                replacement = '<hp:t></hp:t>'
            new_tc = new_tc[:m.start()] + replacement + new_tc[m.end():]

        result = result[:tc_match.start()] + new_tc + result[tc_match.end():]

    return xml_str[:start] + result + xml_str[end:]


def _escape_xml(text: str) -> str:
    """XML 텍스트 이스케이프"""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    return text


def convert_org_to_hwpx_v2(org_doc: OrgDocument, template_path: Path, output_path: Path):
    """v2: 원본 HWPX 문단 매칭 + 텍스트만 교체 (서식 100% 보존)

    ET.tostring()을 사용하지 않고 원본 XML 바이트를 직접 조작.
    <hp:t> 태그 내용만 문자열 치환하므로 XML 구조가 1바이트도 변형되지 않음.
    """
    if not template_path or not template_path.exists():
        logger.error(f"템플릿 필수: {template_path}")
        return

    # 1. 원본 section0.xml을 문자열로 읽기
    with zipfile.ZipFile(template_path, 'r') as zf:
        section_data = zf.read('Contents/section0.xml')
    xml_str = section_data.decode('utf-8')

    # 2. top-level <hp:p> 범위 인덱싱 (문자열 탐색)
    p_ranges = _find_toplevel_p_ranges(xml_str)
    logger.info(f"원본 top-level <hp:p>: {len(p_ranges)}개")

    # 3. Org 요소를 hwpx_idx로 매핑하여 교체
    # 역순 처리 (문자열 offset 변동 방지)
    replacements = []  # [(idx, elem), ...]
    for elem in org_doc.elements:
        idx = elem.hwpx_idx
        if idx is None or idx < 0 or idx >= len(p_ranges):
            continue
        replacements.append((idx, elem))

    # idx 역순 정렬
    replacements.sort(key=lambda x: x[0], reverse=True)

    matched = 0
    skipped = 0
    for idx, elem in replacements:
        start, end = p_ranges[idx]
        current_text = _extract_text_from_block(xml_str, start, end)

        if isinstance(elem, OrgHeading):
            new_text = heading_to_hwpx_text(elem)
            if current_text.strip() == new_text.strip():
                skipped += 1
                continue
            xml_str = _replace_t_in_block(xml_str, start, end, new_text)
            matched += 1
            logger.debug(f"[{idx}] 헤딩 교체: {new_text[:40]}")

        elif isinstance(elem, OrgParagraph):
            if current_text.strip() == elem.text.strip():
                skipped += 1
                continue
            xml_str = _replace_t_in_block(xml_str, start, end, elem.text)
            matched += 1
            logger.debug(f"[{idx}] 본문 교체: {elem.text[:40]}")

        elif isinstance(elem, OrgTable):
            xml_str = _replace_table_in_block(xml_str, start, end, elem)
            matched += 1
            logger.debug(f"[{idx}] 테이블 교체: {elem.name}")

        # 범위 재계산 (이 교체로 길이가 바뀌었을 수 있음)
        # 역순이므로 이전 인덱스의 범위는 영향 없음

    logger.info(f"매칭 결과: {matched}개 교체, {skipped}개 동일(skip)")

    # 4. 수정된 원본 XML을 그대로 패치 (ET.tostring 없음!)
    new_section_xml = xml_str.encode('utf-8')
    logger.info(f"v2 section0.xml: {len(new_section_xml)} bytes")

    # 5. 바이너리 패치로 HWPX 생성
    patch_hwpx_binary(template_path, new_section_xml, output_path)

    logger.info(f"v2 HWPX 저장: {output_path}")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description='Org-mode → HWPX 역변환기',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
헤딩 레벨 매핑:
    * level 1  → "1. " (숫자 - 원본 유지)
    ** level 2 → "1-1. " (숫자 - 원본 유지)
    *** level 3 → "□ " (네모)
    **** level 4 → "o " (동그라미)
    ***** level 5 → "- " (줄표)
    ****** level 6 → "⋅" (점)

예시:
    python org_to_hwpx.py proposal.org -t template.hwpx -o output.hwpx
"""
    )
    parser.add_argument('input', help='입력 Org 파일')
    parser.add_argument('-t', '--template', required=True, help='HWPX 템플릿 파일 (필수)')
    parser.add_argument('-o', '--output', help='출력 HWPX 파일')
    parser.add_argument('-m', '--mode', choices=['v1', 'v2'], default='v2',
                        help='변환 모드: v1=XML 재생성, v2=문단 매칭+텍스트 교체 (기본: v2)')
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

    if args.mode == 'v2':
        if tagged == 0:
            logger.warning("HWPX_IDX 태그가 없습니다. v1 모드로 폴백합니다.")
            convert_org_to_hwpx(org_doc, template_path, output_path)
        else:
            logger.info("v2 모드: 문단 매칭 + 텍스트 교체")
            convert_org_to_hwpx_v2(org_doc, template_path, output_path)
    else:
        logger.info("v1 모드: XML 재생성")
        convert_org_to_hwpx(org_doc, template_path, output_path)


if __name__ == '__main__':
    main()

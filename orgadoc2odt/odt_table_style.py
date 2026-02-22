#!/usr/bin/env python3
"""
ODT 테이블 스타일 후처리기

pandoc이 생성한 ODT 테이블에 제안서 수준의 스타일을 적용한다.

적용 항목:
  - 모든 셀: 검정 1pt 테두리
  - 모든 셀: 세로 가운데 정렬, 패딩 0.1cm
  - 헤더 행: 회색 배경(#d9d9d9), 볼드, 가운데 정렬
  - 본문 셀: 폰트 크기 맞춤
  - 테이블: 100% 너비
  - 폰트: 돋움(Dotum) 8pt (proposal-pipeline reference.odt 기준)
"""

import argparse
import os
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

# ODT 네임스페이스
NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
}

# proposal-pipeline의 reference.odt에서 추출한 스타일 값
CELL_BORDER = "0.035cm solid #000000"
HEADER_BG = "#d9d9d9"
FONT_NAME = "Dotum"
FONT_SIZE = "8pt"
CELL_PADDING = "0.097cm"

# 추가 네임스페이스 (content.xml 직렬화에 필요)
EXTRA_NS = {
    "draw": "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0",
    "svg": "urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0",
    "xlink": "http://www.w3.org/1999/xlink",
    "dc": "http://purl.org/dc/elements/1.1/",
    "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0",
    "number": "urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0",
    "chart": "urn:oasis:names:tc:opendocument:xmlns:chart:1.0",
    "dr3d": "urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0",
    "math": "http://www.w3.org/1998/Math/MathML",
    "form": "urn:oasis:names:tc:opendocument:xmlns:form:1.0",
    "script": "urn:oasis:names:tc:opendocument:xmlns:script:1.0",
    "ooo": "http://openoffice.org/2004/office",
    "ooow": "http://openoffice.org/2004/writer",
    "oooc": "http://openoffice.org/2004/calc",
    "dom": "http://www.w3.org/2001/xml-events",
    "xforms": "http://www.w3.org/2002/xforms",
    "xsd": "http://www.w3.org/2001/XMLSchema",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "rpt": "http://openoffice.org/2005/report",
    "of": "urn:oasis:names:tc:opendocument:xmlns:of:1.2",
    "rdfa": "http://docs.oasis-open.org/opendocument/meta/rdfa#",
    "field": "urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0",
    "loext": "urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0",
}


def qn(ns, local):
    return f"{{{NS[ns]}}}{local}"


def register_namespaces():
    for prefix, uri in {**NS, **EXTRA_NS}.items():
        ET.register_namespace(prefix, uri)


def process_content(content_xml_path):
    """content.xml의 테이블 스타일을 제안서 수준으로 보정"""
    register_namespaces()
    tree = ET.parse(content_xml_path)
    root = tree.getroot()

    auto_styles = root.find(f".//{qn('office', 'automatic-styles')}")
    if auto_styles is None:
        print("WARNING: automatic-styles 없음")
        return {}

    stats = {
        'cell_border': 0,
        'header_bg': 0,
        'font_fixed': 0,
        'table_width': 0,
    }

    # --- 1. 셀 스타일 보정: 테두리 + 패딩 + 세로 가운데 ---
    for style in auto_styles.findall(f"{qn('style', 'style')}"):
        family = style.get(f"{qn('style', 'family')}", "")
        name = style.get(f"{qn('style', 'name')}", "")

        if family == "table-cell":
            props = style.find(f"{qn('style', 'table-cell-properties')}")
            if props is None:
                props = ET.SubElement(style, f"{qn('style', 'table-cell-properties')}")

            # 테두리
            props.set(f"{qn('fo', 'border')}", CELL_BORDER)
            # 개별 border 제거 (border가 우선)
            for side in ('border-top', 'border-bottom', 'border-left', 'border-right'):
                key = f"{qn('fo', side)}"
                if key in props.attrib:
                    del props.attrib[key]

            # 패딩
            props.set(f"{qn('fo', 'padding')}", CELL_PADDING)

            # 세로 가운데
            props.set(f"{qn('style', 'vertical-align')}", "middle")

            stats['cell_border'] += 1

        # --- 2. 테이블 너비 100% ---
        if family == "table":
            props = style.find(f"{qn('style', 'table-properties')}")
            if props is None:
                props = ET.SubElement(style, f"{qn('style', 'table-properties')}")
            props.set(f"{qn('style', 'rel-width')}", "100%")
            props.set(f"{qn('table', 'align')}", "center")
            stats['table_width'] += 1

    # --- 3. 헤더 행 감지 + 배경색 적용 ---
    # pandoc은 <table:table-header-rows>로 헤더를 구분함
    for header_rows in root.iter(f"{qn('table', 'table-header-rows')}"):
        for row in header_rows.findall(f"{qn('table', 'table-row')}"):
            for cell in row.findall(f"{qn('table', 'table-cell')}"):
                cell_style = cell.get(f"{qn('table', 'style-name')}", "")
                if cell_style:
                    # 해당 셀 스타일에 배경색 추가
                    _add_header_bg(auto_styles, cell_style)
                    stats['header_bg'] += 1
                # 헤더 셀의 텍스트 볼드 + 가운데 정렬
                for para in cell.findall(f".//{qn('text', 'p')}"):
                    _set_header_text_style(auto_styles, para)
                    stats['font_fixed'] += 1

    # --- 4. 모든 셀의 텍스트에 폰트 스타일 적용 ---
    for cell in root.iter(f"{qn('table', 'table-cell')}"):
        for para in cell.findall(f".//{qn('text', 'p')}"):
            para_style = para.get(f"{qn('text', 'style-name')}", "")
            if para_style:
                _ensure_font_style(auto_styles, para_style)

    tree.write(content_xml_path, xml_declaration=True, encoding="UTF-8")
    return stats


def _add_header_bg(auto_styles, cell_style_name):
    """셀 스타일에 헤더 배경색 추가"""
    for style in auto_styles.findall(f"{qn('style', 'style')}"):
        name = style.get(f"{qn('style', 'name')}", "")
        if name == cell_style_name:
            props = style.find(f"{qn('style', 'table-cell-properties')}")
            if props is not None:
                props.set(f"{qn('fo', 'background-color')}", HEADER_BG)
            return


def _set_header_text_style(auto_styles, para):
    """헤더 문단에 볼드 + 가운데 정렬 스타일 설정"""
    style_name = para.get(f"{qn('text', 'style-name')}", "")
    if not style_name:
        return

    for style in auto_styles.findall(f"{qn('style', 'style')}"):
        name = style.get(f"{qn('style', 'name')}", "")
        if name == style_name:
            # 문단 정렬
            p_props = style.find(f"{qn('style', 'paragraph-properties')}")
            if p_props is None:
                p_props = ET.SubElement(style, f"{qn('style', 'paragraph-properties')}")
            p_props.set(f"{qn('fo', 'text-align')}", "center")

            # 텍스트 볼드
            t_props = style.find(f"{qn('style', 'text-properties')}")
            if t_props is None:
                t_props = ET.SubElement(style, f"{qn('style', 'text-properties')}")
            t_props.set(f"{qn('fo', 'font-weight')}", "bold")
            t_props.set(f"{qn('style', 'font-weight-asian')}", "bold")
            t_props.set(f"{qn('style', 'font-weight-complex')}", "bold")
            return


def _ensure_font_style(auto_styles, style_name):
    """문단 스타일에 폰트/크기 보장"""
    for style in auto_styles.findall(f"{qn('style', 'style')}"):
        name = style.get(f"{qn('style', 'name')}", "")
        if name == style_name:
            t_props = style.find(f"{qn('style', 'text-properties')}")
            if t_props is None:
                t_props = ET.SubElement(style, f"{qn('style', 'text-properties')}")

            # 폰트 크기 (없으면 설정)
            if f"{qn('fo', 'font-size')}" not in t_props.attrib:
                t_props.set(f"{qn('fo', 'font-size')}", FONT_SIZE)
                t_props.set(f"{qn('style', 'font-size-asian')}", FONT_SIZE)
                t_props.set(f"{qn('style', 'font-size-complex')}", FONT_SIZE)

            # 폰트 이름 (없으면 설정)
            if f"{qn('style', 'font-name')}" not in t_props.attrib:
                t_props.set(f"{qn('style', 'font-name')}", FONT_NAME)
                t_props.set(f"{qn('style', 'font-name-asian')}", FONT_NAME)

            # 줄간격
            p_props = style.find(f"{qn('style', 'paragraph-properties')}")
            if p_props is None:
                p_props = ET.SubElement(style, f"{qn('style', 'paragraph-properties')}")
            if f"{qn('fo', 'margin-top')}" not in p_props.attrib:
                p_props.set(f"{qn('fo', 'margin-top')}", "0cm")
                p_props.set(f"{qn('fo', 'margin-bottom')}", "0cm")

            return


def postprocess_odt(input_odt, output_odt=None):
    """ODT 파일의 테이블 스타일 후처리"""
    if output_odt is None:
        output_odt = input_odt

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(input_odt, 'r') as zf:
            zf.extractall(tmpdir)

        content_path = os.path.join(tmpdir, 'content.xml')
        if not os.path.exists(content_path):
            print("ERROR: content.xml 없음")
            return False

        stats = process_content(content_path)

        tmp_odt = output_odt + '.tmp'
        with zipfile.ZipFile(tmp_odt, 'w') as zf:
            mimetype_path = os.path.join(tmpdir, 'mimetype')
            if os.path.exists(mimetype_path):
                zf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            for dirpath, _, filenames in os.walk(tmpdir):
                for fn in filenames:
                    if fn == 'mimetype':
                        continue
                    full = os.path.join(dirpath, fn)
                    arcname = os.path.relpath(full, tmpdir)
                    zf.write(full, arcname, compress_type=zipfile.ZIP_DEFLATED)
        os.replace(tmp_odt, output_odt)

    print(f"테이블 스타일 보정 완료: {output_odt}")
    print(f"  셀 테두리: {stats.get('cell_border', 0)}개")
    print(f"  헤더 배경: {stats.get('header_bg', 0)}개")
    print(f"  폰트 보정: {stats.get('font_fixed', 0)}개")
    print(f"  테이블 너비: {stats.get('table_width', 0)}개")
    return True


def main():
    parser = argparse.ArgumentParser(description='ODT 테이블 스타일 후처리')
    parser.add_argument('input', help='입력 ODT 파일')
    parser.add_argument('-o', '--output', help='출력 ODT (기본: 덮어쓰기)')
    args = parser.parse_args()

    postprocess_odt(args.input, args.output or args.input)


if __name__ == '__main__':
    main()

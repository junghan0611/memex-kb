#!/usr/bin/env python3
"""ODT 후처리: 테이블 헤더 셀에 회색 배경 추가.

사용법:
    python odt_postprocess.py input.odt [output.odt]

Org ODT 내보내기 후 실행. 헤더 행(OrgTableHeading* 문단 스타일)의
셀에 #d9d9d9 배경색을 추가한다.
"""

import sys
import os
import shutil
import tempfile
import zipfile
import xml.etree.ElementTree as ET

NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
}

HEADER_BG = "#d9d9d9"
CELL_BORDER = "0.035cm solid #000000"  # 1pt 검정 실선


def register_namespaces():
    """XML 직렬화 시 네임스페이스 접두사 보존."""
    for prefix, uri in NS.items():
        ET.register_namespace(prefix, uri)
    # 추가 네임스페이스 (content.xml에서 사용)
    extra = {
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
    }
    for prefix, uri in extra.items():
        ET.register_namespace(prefix, uri)


def qn(ns, local):
    """Qualified name: {uri}local."""
    return f"{{{NS[ns]}}}{local}"


def process_content(content_xml_path):
    """content.xml에서 헤더 셀에 배경색 추가."""
    register_namespaces()
    tree = ET.parse(content_xml_path)
    root = tree.getroot()

    # 1) 기존 셀 스타일 수집 (automatic-styles)
    auto_styles = root.find(f".//{qn('office', 'automatic-styles')}")
    if auto_styles is None:
        print("WARNING: content.xml에 automatic-styles가 없습니다 — 스타일 수정 건너뜀")
        return 0, 0, 0
    cell_styles = {}
    for style in auto_styles.findall(f"{qn('style', 'style')}"):
        name = style.get(f"{qn('style', 'name')}")
        family = style.get(f"{qn('style', 'family')}")
        if family == "table-cell" and name and name.startswith("OrgTblCell"):
            cell_styles[name] = style

    # 2) 모든 셀 스타일에 검정 border 설정 (HWP 호환)
    border_count = 0
    border_attrs = [
        f"{qn('fo', 'border-top')}",
        f"{qn('fo', 'border-bottom')}",
        f"{qn('fo', 'border-left')}",
        f"{qn('fo', 'border-right')}",
    ]
    for name, style in cell_styles.items():
        props = style.find(f"{qn('style', 'table-cell-properties')}")
        if props is not None:
            for attr in border_attrs:
                props.set(attr, CELL_BORDER)
            border_count += 1

    # 3) 헤더 셀용 배경 스타일 생성 (기존 스타일 복제 + 배경색)
    shaded_map = {}  # original_name -> shaded_name

    def get_shaded_style(orig_name):
        if orig_name in shaded_map:
            return shaded_map[orig_name]
        shaded_name = orig_name + "Shaded"
        if orig_name in cell_styles:
            orig = cell_styles[orig_name]
            new_style = ET.SubElement(auto_styles, f"{qn('style', 'style')}")
            new_style.set(f"{qn('style', 'name')}", shaded_name)
            new_style.set(f"{qn('style', 'family')}", "table-cell")
            props = orig.find(f"{qn('style', 'table-cell-properties')}")
            new_props = ET.SubElement(new_style, f"{qn('style', 'table-cell-properties')}")
            if props is not None:
                for k, v in props.attrib.items():
                    new_props.set(k, v)
            new_props.set(f"{qn('fo', 'background-color')}", HEADER_BG)
        shaded_map[orig_name] = shaded_name
        return shaded_name

    # 3) 헤더 행의 셀 스타일을 shaded 버전으로 교체
    count = 0
    for cell in root.iter(f"{qn('table', 'table-cell')}"):
        para = cell.find(f"{qn('text', 'p')}")
        if para is None:
            continue
        para_style = para.get(f"{qn('text', 'style-name')}", "")
        if "OrgTableHeading" in para_style:
            orig_cell_style = cell.get(f"{qn('table', 'style-name')}", "")
            if orig_cell_style and orig_cell_style.startswith("OrgTblCell"):
                shaded = get_shaded_style(orig_cell_style)
                cell.set(f"{qn('table', 'style-name')}", shaded)
                count += 1

    tree.write(content_xml_path, xml_declaration=True, encoding="UTF-8")
    return count, len(shaded_map), border_count


def main():
    if len(sys.argv) < 2:
        print(f"사용법: {sys.argv[0]} input.odt [output.odt]")
        sys.exit(1)

    input_odt = sys.argv[1]
    output_odt = sys.argv[2] if len(sys.argv) > 2 else input_odt

    with tempfile.TemporaryDirectory() as tmpdir:
        # 압축 해제
        with zipfile.ZipFile(input_odt, "r") as zf:
            zf.extractall(tmpdir)

        content_path = os.path.join(tmpdir, "content.xml")
        if not os.path.exists(content_path):
            print("ERROR: content.xml not found")
            sys.exit(1)

        cells_modified, styles_created, borders_fixed = process_content(content_path)
        print(f"셀 border {borders_fixed}개 수정, 헤더 셀 {cells_modified}개 배경 추가, 스타일 {styles_created}개 생성")

        # 재압축 (임시파일 → 원본 교체로 안전하게)
        tmp_odt = output_odt + ".tmp"
        with zipfile.ZipFile(tmp_odt, "w") as zf:
            mimetype_path = os.path.join(tmpdir, "mimetype")
            if os.path.exists(mimetype_path):
                zf.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
            for dirpath, dirnames, filenames in os.walk(tmpdir):
                for fn in filenames:
                    if fn == "mimetype":
                        continue
                    full = os.path.join(dirpath, fn)
                    arcname = os.path.relpath(full, tmpdir)
                    zf.write(full, arcname, compress_type=zipfile.ZIP_DEFLATED)
        os.replace(tmp_odt, output_odt)

    print(f"완료: {output_odt}")


if __name__ == "__main__":
    main()

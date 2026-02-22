#!/usr/bin/env python3
"""
Org + AsciiDoc 하이브리드 → ODT 변환기

Org 파일 내 #+begin_src adoc 블록의 AsciiDoc 테이블을 
HTML로 변환하여, 병합 셀(colspan/rowspan)이 보존된 ODT를 생성한다.

파이프라인:
  1. Org에서 AsciiDoc 블록 추출
  2. asciidoctor -b html5 → <table> HTML 추출
  3. Org 블록을 #+begin_export html 로 교체
  4. pandoc: org → html → odt (2단계, 병합 셀 보존)

검증 결과:
  - DocBook 경유: rowspan 소실 ❌
  - pandoc org→odt 직접: RawBlock(html) 무시 ❌  
  - org → html → odt 2단계: colspan/rowspan 모두 보존 ✅
"""

import argparse
import logging
import re
import subprocess
import sys
import tempfile
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
log = logging.getLogger(__name__)


def extract_adoc_blocks(org_content: str) -> list[dict]:
    """Org 파일에서 #+begin_src adoc(iidoc) 블록들을 추출"""
    pattern = re.compile(
        r'(#\+begin_src\s+adoc(?:iidoc)?\s*\n)(.*?)(#\+end_src)',
        re.DOTALL | re.IGNORECASE
    )
    blocks = []
    for m in pattern.finditer(org_content):
        blocks.append({
            'full_match': m.group(0),
            'content': m.group(2),
            'start': m.start(),
            'end': m.end(),
        })
    return blocks


def adoc_to_html_table(adoc_content: str) -> str:
    """AsciiDoc 테이블 → HTML <table> (asciidoctor 경유)"""
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.adoc', delete=False, encoding='utf-8'
    ) as f:
        f.write(adoc_content)
        f.flush()

        result = subprocess.run(
            ['asciidoctor', '-b', 'html5', '-s', '-o', '-', f.name],
            capture_output=True, text=True
        )

    if result.returncode != 0:
        log.error(f"asciidoctor 실패: {result.stderr}")
        return f"<!-- asciidoctor 변환 실패 -->\n<pre>{adoc_content}</pre>"

    # <table> 태그만 추출
    table_match = re.search(r'<table.*?</table>', result.stdout, re.DOTALL)
    if table_match:
        return table_match.group(0)

    log.warning("HTML에서 <table> 태그를 찾지 못함")
    return f"<!-- 테이블 없음 -->\n{result.stdout}"


def preprocess_org(org_content: str) -> str:
    """Org 파일의 AsciiDoc 블록 → HTML export 블록으로 교체"""
    blocks = extract_adoc_blocks(org_content)

    if not blocks:
        log.info("AsciiDoc 블록 없음 — 원본 그대로 사용")
        return org_content

    log.info(f"AsciiDoc 블록 {len(blocks)}개 발견")

    result = org_content
    for block in reversed(blocks):
        html_table = adoc_to_html_table(block['content'])
        replacement = f"#+begin_export html\n{html_table}\n#+end_export"
        result = result[:block['start']] + replacement + result[block['end']:]
        log.info(f"  블록 변환 완료 (위치: {block['start']})")

    return result


def org_to_odt(org_path: str, odt_path: str, reference_odt: str = None) -> bool:
    """Org + AsciiDoc → ODT 변환 (2단계: org→html→odt)"""
    org_content = Path(org_path).read_text(encoding='utf-8')

    # Step 1: AsciiDoc 블록 전처리
    processed = preprocess_org(org_content)

    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.org', delete=False, encoding='utf-8'
    ) as f:
        f.write(processed)
        processed_org = f.name

    # Step 2: Org → HTML (pandoc)
    html_path = tempfile.mktemp(suffix='.html')
    cmd_html = ['pandoc', '-f', 'org', '-t', 'html', '-o', html_path, processed_org]
    r1 = subprocess.run(cmd_html, capture_output=True, text=True)
    if r1.returncode != 0:
        log.error(f"pandoc org→html 실패: {r1.stderr}")
        return False

    # Step 3: HTML → ODT (pandoc)
    cmd_odt = ['pandoc', '-f', 'html', '-t', 'odt', '-o', odt_path, html_path]
    if reference_odt and Path(reference_odt).exists():
        cmd_odt.extend(['--reference-doc', reference_odt])
        log.info(f"스타일 시트: {reference_odt}")
    r2 = subprocess.run(cmd_odt, capture_output=True, text=True)
    if r2.returncode != 0:
        log.error(f"pandoc html→odt 실패: {r2.stderr}")
        return False

    log.info(f"ODT 생성 완료: {odt_path}")
    return True


def verify_odt_merges(odt_path: str) -> dict:
    """ODT 파일의 병합 셀 현황 검사"""
    import zipfile
    import xml.etree.ElementTree as ET

    NS = {
        'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
        'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    }

    with zipfile.ZipFile(odt_path) as z:
        content = z.read('content.xml')

    root = ET.fromstring(content)
    tables = root.findall('.//table:table', NS)

    result = {
        'tables': len(tables),
        'total_colspan': 0,
        'total_rowspan': 0,
        'details': [],
    }

    for i, table in enumerate(tables):
        rows = table.findall('.//table:table-row', NS)
        table_info = {'table': i + 1, 'rows': len(rows), 'merges': []}

        for j, row in enumerate(rows):
            cells = row.findall('table:table-cell', NS)
            for cell in cells:
                cs = cell.get(f'{{{NS["table"]}}}number-columns-spanned', '1')
                rs = cell.get(f'{{{NS["table"]}}}number-rows-spanned', '1')
                if cs != '1' or rs != '1':
                    texts = cell.findall('.//text:p', NS)
                    txt = texts[0].text if texts and texts[0].text else ''
                    merge = {}
                    if cs != '1':
                        merge['colspan'] = int(cs)
                        result['total_colspan'] += 1
                    if rs != '1':
                        merge['rowspan'] = int(rs)
                        result['total_rowspan'] += 1
                    merge['text'] = txt
                    merge['row'] = j
                    table_info['merges'].append(merge)

        result['details'].append(table_info)

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Org + AsciiDoc 하이브리드 → ODT 변환기'
    )
    sub = parser.add_subparsers(dest='command')

    # convert
    p_conv = sub.add_parser('convert', help='Org → ODT 변환')
    p_conv.add_argument('input', help='입력 Org 파일')
    p_conv.add_argument('-o', '--output', help='출력 ODT 파일')
    p_conv.add_argument('-r', '--reference', help='스타일 참조 ODT')

    # preprocess (디버깅용)
    p_pre = sub.add_parser('preprocess', help='AsciiDoc 블록만 HTML로 변환')
    p_pre.add_argument('input', help='입력 Org 파일')
    p_pre.add_argument('-o', '--output', help='출력 Org 파일')

    # verify
    p_ver = sub.add_parser('verify', help='ODT 병합 셀 검사')
    p_ver.add_argument('input', help='ODT 파일')

    args = parser.parse_args()

    if args.command == 'convert':
        output = args.output or args.input.replace('.org', '.odt')
        success = org_to_odt(args.input, output, args.reference)
        if not success:
            sys.exit(1)
        # 자동 검증
        result = verify_odt_merges(output)
        print(f"\n검증: 테이블 {result['tables']}개, "
              f"colspan {result['total_colspan']}개, "
              f"rowspan {result['total_rowspan']}개")
        for t in result['details']:
            if t['merges']:
                print(f"  테이블 {t['table']} ({t['rows']}행): "
                      f"{len(t['merges'])}개 병합 셀")
                for m in t['merges']:
                    parts = []
                    if 'colspan' in m:
                        parts.append(f"cs={m['colspan']}")
                    if 'rowspan' in m:
                        parts.append(f"rs={m['rowspan']}")
                    print(f"    행{m['row']}: [{m['text']}] {' '.join(parts)}")

    elif args.command == 'preprocess':
        org_content = Path(args.input).read_text(encoding='utf-8')
        result = preprocess_org(org_content)
        if args.output:
            Path(args.output).write_text(result, encoding='utf-8')
        else:
            print(result)

    elif args.command == 'verify':
        result = verify_odt_merges(args.input)
        print(f"테이블 {result['tables']}개, "
              f"colspan {result['total_colspan']}개, "
              f"rowspan {result['total_rowspan']}개")
        for t in result['details']:
            print(f"\n테이블 {t['table']} ({t['rows']}행):")
            if t['merges']:
                for m in t['merges']:
                    parts = []
                    if 'colspan' in m:
                        parts.append(f"cs={m['colspan']}")
                    if 'rowspan' in m:
                        parts.append(f"rs={m['rowspan']}")
                    print(f"  행{m['row']}: [{m['text']}] {' '.join(parts)}")
            else:
                print("  병합 셀 없음")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()

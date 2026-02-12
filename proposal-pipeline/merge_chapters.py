#!/usr/bin/env python3
"""
장별 Org 파일을 하나의 통합 Org 파일로 합치기

각 장의 content Org 파일을 제안서 목차 순서로 통합합니다.
Emacs에서 전체 제안서를 검토할 수 있도록 합니다.

사용법:
    python merge_chapters.py -o 제안서-전체.org
    python merge_chapters.py --strip-hwpx-idx -o 제안서-전체.org
    python merge_chapters.py --strip-hwpx-idx --org-tables -o 제안서-검토.org
"""

import argparse
import re
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
MEMEX_KB_DIR = SCRIPT_DIR.parent
ORG_OUTPUT = MEMEX_KB_DIR / 'output' / 'proposal-org'

# 제안서 목차 순서: (파일명, 제안서 장 번호, 제목)
CHAPTER_ORDER = [
    ('ch1-content.org', '1', '연구개발과제의 필요성'),
    ('ch2-content.org', '2', '연구개발과제의 목표 및 내용'),
    ('ch3-content.org', '3', '추진전략·방법 및 추진체계'),
    ('ch4-content.org', '4', '연구개발 추진체계 및 위험관리'),
    ('ch5-content.org', '5', '활용방안 및 사업화 전략'),
]


def strip_org_header(content: str) -> str:
    """Org 파일에서 #+TITLE, #+DATE, #+STARTUP 헤더 제거"""
    lines = content.split('\n')
    result = []
    for line in lines:
        if line.startswith('#+TITLE:'):
            continue
        if line.startswith('#+DATE:'):
            continue
        if line.startswith('#+STARTUP:'):
            continue
        result.append(line)
    # 앞쪽 빈 줄 제거
    while result and not result[0].strip():
        result.pop(0)
    return '\n'.join(result)


def add_chapter_prefix_to_hwpx_idx(content: str, chapter: str) -> str:
    """HWPX_IDX에 장 접두어 추가 (예: 0 → ch1:0)"""
    content = re.sub(
        r':HWPX_IDX:\s*(\d+)',
        rf':HWPX_IDX: {chapter}:\1',
        content
    )
    content = re.sub(
        r'#\+HWPX:\s*(\d+)',
        rf'#+HWPX: {chapter}:\1',
        content
    )
    return content


def convert_asciidoc_to_org_tables(content: str) -> str:
    """#+BEGIN_SRC asciidoc 블록 내 테이블을 Org 네이티브 테이블로 변환

    변환 전:
        #+BEGIN_SRC asciidoc
        [cols="1,1,1"]
        |===
        |헤더1
        |헤더2
        |헤더3

        |셀1
        |셀2
        |셀3
        |===
        #+END_SRC

    변환 후:
        | 헤더1 | 헤더2 | 헤더3 |
        |-------+-------+-------|
        | 셀1   | 셀2   | 셀3   |
    """
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # asciidoc SRC 블록 감지
        if line.strip().startswith('#+BEGIN_SRC asciidoc'):
            # 블록 내용 수집
            block_lines = []
            table_name = ""
            name_match = re.search(r':name\s+(.+)$', line)
            if name_match:
                table_name = name_match.group(1).strip()
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('#+END_SRC'):
                block_lines.append(lines[i])
                i += 1
            i += 1  # #+END_SRC 스킵

            # AsciiDoc 테이블 파싱 → Org 테이블
            org_table = _asciidoc_block_to_org_table(block_lines)
            if org_table:
                if table_name:
                    result.append(f"#+CAPTION: {table_name}")
                result.extend(org_table)
            else:
                # 변환 실패 시 원본 유지
                result.append(f"#+BEGIN_SRC asciidoc")
                result.extend(block_lines)
                result.append("#+END_SRC")
            continue

        # EXAMPLE 블록 (작성요령)은 그대로
        result.append(line)
        i += 1

    return '\n'.join(result)


def _asciidoc_block_to_org_table(block_lines: list) -> list:
    """AsciiDoc 블록 라인을 Org 테이블 라인으로 변환

    Returns: Org 테이블 라인 리스트 또는 None (변환 실패)
    """
    # cols 정보와 테이블 데이터 분리
    col_count = 0
    in_table = False
    rows = []
    current_row = []

    for line in block_lines:
        line = line.strip()

        # cols 정보
        if line.startswith('[cols='):
            match = re.search(r'\[cols="([^"]+)"\]', line)
            if match:
                col_count = len(match.group(1).split(','))
            continue

        # 테이블 시작/종료
        if line == '|===':
            if in_table:
                # 테이블 종료
                if current_row:
                    rows.append(current_row)
                break
            else:
                in_table = True
                continue

        if not in_table:
            continue

        # 빈 줄 = 행 구분
        if not line:
            if current_row:
                rows.append(current_row)
                current_row = []
            continue

        # 셀 읽기
        if line.startswith('|'):
            cell_text = _unescape_asciidoc(line[1:].strip())
            current_row.append(cell_text)

    if not rows:
        return None

    # col_count 결정
    if not col_count:
        col_count = max(len(r) for r in rows)

    # 각 행이 col_count에 맞는지 확인, 부족하면 빈 셀 추가
    for row in rows:
        while len(row) < col_count:
            row.append('')

    # Org 테이블 생성
    org_lines = []
    for idx, row in enumerate(rows):
        cells_str = ' | '.join(row)
        org_lines.append(f"| {cells_str} |")
        # 첫 번째 행 뒤에 구분선 (헤더)
        if idx == 0:
            org_lines.append('|' + '+'.join(['-' * (len(c) + 2) for c in row]) + '|')

    return org_lines


def _unescape_asciidoc(text: str) -> str:
    """AsciiDoc 이스케이프 해제"""
    for old, new in [("\\|", "|"), ("\\*", "*"), ("\\_", "_"), ("\\`", "`")]:
        text = text.replace(old, new)
    return text


def strip_hwpx_idx(content: str) -> str:
    """HWPX_IDX와 #+HWPX 태그 완전 제거 (깔끔한 검토용)"""
    lines = content.split('\n')
    result = []
    skip_properties = False
    for line in lines:
        if line.strip() == ':PROPERTIES:':
            skip_properties = True
            continue
        if skip_properties:
            if line.strip() == ':END:':
                skip_properties = False
            continue
        if re.match(r'^#\+HWPX:', line):
            continue
        result.append(line)
    return '\n'.join(result)


def main():
    parser = argparse.ArgumentParser(
        description='장별 Org 파일 → 통합 Org 파일',
    )
    parser.add_argument('-o', '--output', default=str(ORG_OUTPUT / '제안서-전체.org'),
                        help='출력 Org 파일')
    parser.add_argument('--strip-hwpx-idx', action='store_true',
                        help='HWPX_IDX 태그 제거 (검토용)')
    parser.add_argument('--org-tables', action='store_true',
                        help='AsciiDoc 테이블을 Org 네이티브 테이블로 변환')
    parser.add_argument('--org-dir', default=str(ORG_OUTPUT),
                        help='Org 입력 디렉토리')

    args = parser.parse_args()
    org_dir = Path(args.org_dir)
    output_path = Path(args.output)

    lines = []
    lines.append('#+TITLE: AI 소프트센서 기반 스마트홈 플랫폼 - 기술연구개발계획서')
    lines.append(f'#+DATE: [{datetime.now().strftime("%Y-%m-%d %a %H:%M")}]')
    lines.append('#+STARTUP: overview')
    lines.append('#+OPTIONS: toc:3 num:t H:5')
    lines.append('')

    found_count = 0
    for filename, ch_num, ch_title in CHAPTER_ORDER:
        org_file = org_dir / filename
        if not org_file.exists():
            print(f"WARNING: {org_file} 없음 — 건너뜀")
            continue

        found_count += 1
        print(f"  추가: {filename} ({ch_num}. {ch_title})")

        with open(org_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 헤더 제거
        content = strip_org_header(content)

        # HWPX_IDX 처리
        if args.strip_hwpx_idx:
            content = strip_hwpx_idx(content)
        else:
            # 장 접두어 추가 (장 간 구분)
            ch_key = filename.split('-')[0]  # ch1, ch2, ...
            content = add_chapter_prefix_to_hwpx_idx(content, ch_key)

        # AsciiDoc → Org 테이블 변환
        if args.org_tables:
            content = convert_asciidoc_to_org_tables(content)

        lines.append(content)
        lines.append('')  # 장 사이 빈 줄

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"\n통합 Org 파일 생성: {output_path}")
    print(f"  포함된 장: {found_count}개")


if __name__ == '__main__':
    main()

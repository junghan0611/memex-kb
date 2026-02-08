#!/usr/bin/env python3
"""
Google Docs MD 후처리기 (v3)

MCP get_doc_content 출력 또는 Google Docs 네이티브 MD 내보내기를 처리:
  1. 탭별 MD 파일 분할
  2. base64 인라인 이미지 → 별도 PNG 파일 추출
  3. 탭별 이미지 매핑

Usage:
  # 탭 분할 (MCP get_doc_content 결과)
  python gdocs_md_processor.py split-tabs --input mcp_output.json --output-dir ./output

  # 이미지 추출 (Google Docs 네이티브 MD 내보내기)
  python gdocs_md_processor.py extract-images --input exported.md --output-dir ./output

  # 전체 처리 (탭 분할 + 이미지 추출)
  python gdocs_md_processor.py full --mcp-input mcp_output.json --md-input exported.md --output-dir ./output
"""

import argparse
import base64
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class Tab:
    """Google Docs 탭 정보"""
    name: str
    tab_id: Optional[str]
    depth: int  # 들여쓰기 깊이 (0=최상위)
    content: str
    line_start: int
    line_end: int

    @property
    def safe_filename(self) -> str:
        """파일명으로 사용 가능한 이름 생성"""
        name = self.name.strip()
        # 숫자 접두사가 있으면 유지 (예: "1. 연구개발과제의 배경")
        name = re.sub(r'[^\w가-힣\s\-\.]', '', name)
        name = re.sub(r'\s+', '-', name.strip())
        return name or "untitled"


@dataclass
class ExtractedImage:
    """추출된 이미지 정보"""
    ref_name: str       # image1, image2, ...
    format: str         # png, jpeg
    data: bytes
    filename: str       # output filename


# ──────────────────────────────────────────────
# Tab Splitter: MCP get_doc_content 결과 분할
# ──────────────────────────────────────────────

TAB_MARKER_PATTERN = re.compile(
    r'^--- TAB:\s*(?P<indent>\s*)(?P<name>.+?)'
    r'(?:\s*\(\s*ID:\s*(?P<tab_id>[^)]+)\s*\))?'
    r'\s*---$'
)


def parse_mcp_content(input_path: str) -> str:
    """MCP 출력 파일에서 텍스트 추출 (JSON 또는 plain text)"""
    with open(input_path, 'r', encoding='utf-8') as f:
        raw = f.read()

    # JSON 형식인 경우
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and 'result' in data:
            return data['result']
        return str(data)
    except (json.JSONDecodeError, ValueError):
        return raw


def split_tabs(content: str) -> List[Tab]:
    """MCP get_doc_content 결과를 탭 단위로 분할"""
    lines = content.split('\n')
    tabs: List[Tab] = []
    current_tab: Optional[dict] = None

    for i, line in enumerate(lines, 1):
        match = TAB_MARKER_PATTERN.match(line)
        if match:
            # 이전 탭 마무리
            if current_tab:
                current_tab['line_end'] = i - 1
                tab_lines = lines[current_tab['line_start'] - 1:current_tab['line_end']]
                current_tab['content'] = '\n'.join(tab_lines)
                tabs.append(Tab(**current_tab))

            indent = match.group('indent') or ''
            depth = len(indent) // 4  # 4칸 들여쓰기 = 1 depth
            current_tab = {
                'name': match.group('name').strip(),
                'tab_id': match.group('tab_id'),
                'depth': depth,
                'line_start': i + 1,  # 마커 다음 줄부터
                'line_end': len(lines),
                'content': '',
            }

    # 마지막 탭
    if current_tab:
        current_tab['line_end'] = len(lines)
        tab_lines = lines[current_tab['line_start'] - 1:current_tab['line_end']]
        current_tab['content'] = '\n'.join(tab_lines)
        tabs.append(Tab(**current_tab))

    return tabs


def save_tabs(tabs: List[Tab], output_dir: str) -> List[str]:
    """탭별 MD 파일 저장"""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    saved_files = []
    for idx, tab in enumerate(tabs):
        # 탭 이름으로 파일명 생성 (번호 접두사로 정렬 보장)
        filename = f"{idx:02d}--{tab.safe_filename}.md"
        filepath = out / filename

        # MD 헤더 추가
        header = f"# {tab.name}\n\n"
        if tab.tab_id:
            header += f"<!-- tab-id: {tab.tab_id} -->\n\n"

        content = header + tab.content.strip() + '\n'

        filepath.write_text(content, encoding='utf-8')
        saved_files.append(str(filepath))
        logger.info(
            f"  [{idx:02d}] {tab.name} "
            f"(depth={tab.depth}, lines={tab.line_end - tab.line_start + 1})"
        )

    return saved_files


# ──────────────────────────────────────────────
# Image Extractor: base64 이미지 → PNG 파일
# ──────────────────────────────────────────────

# base64 이미지 정의: [imageN]: <data:image/png;base64,...>
IMAGE_DEF_PATTERN = re.compile(
    r'^\[(?P<ref>image\d+)\]:\s*<data:image/(?P<fmt>png|jpeg|jpg);base64,'
    r'(?P<data>[A-Za-z0-9+/=\s]+)>$',
    re.MULTILINE,
)

# 이미지 참조: ![][imageN]
IMAGE_REF_PATTERN = re.compile(r'!\[\]\[(?P<ref>image\d+)\]')


def extract_images(md_path: str, output_dir: str) -> str:
    """Google Docs 네이티브 MD에서 base64 이미지 추출 및 참조 변환

    Returns:
        변환된 MD 내용 (base64 → 파일 경로)
    """
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    images_dir = Path(output_dir) / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    original_size = len(content)
    extracted: List[ExtractedImage] = []

    # base64 이미지 정의 찾기 및 추출
    for match in IMAGE_DEF_PATTERN.finditer(content):
        ref_name = match.group('ref')
        fmt = match.group('fmt')
        raw_data = match.group('data').replace('\n', '').replace(' ', '')

        try:
            img_bytes = base64.b64decode(raw_data)
        except Exception as e:
            logger.warning(f"  {ref_name} base64 디코딩 실패: {e}")
            continue

        filename = f"{ref_name}.{fmt}"
        img_path = images_dir / filename
        img_path.write_bytes(img_bytes)

        extracted.append(ExtractedImage(
            ref_name=ref_name,
            format=fmt,
            data=img_bytes,
            filename=filename,
        ))
        logger.info(
            f"  {ref_name}.{fmt}: {len(img_bytes) / 1024:.1f} KB"
        )

    # base64 정의 제거
    cleaned = IMAGE_DEF_PATTERN.sub('', content)

    # 참조를 파일 경로로 변환: ![][imageN] → ![imageN](images/imageN.png)
    def replace_ref(m):
        ref = m.group('ref')
        img = next((e for e in extracted if e.ref_name == ref), None)
        if img:
            return f"![{ref}](images/{img.filename})"
        return m.group(0)

    cleaned = IMAGE_REF_PATTERN.sub(replace_ref, cleaned)

    # 후행 빈 줄 정리
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip() + '\n'

    cleaned_size = len(cleaned)
    logger.info(
        f"  크기: {original_size / 1024:.0f}KB → {cleaned_size / 1024:.0f}KB "
        f"({(1 - cleaned_size / original_size) * 100:.0f}% 감소)"
    )

    return cleaned


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def cmd_split_tabs(args):
    """탭 분할 명령"""
    logger.info(f"MCP 출력 파싱: {args.input}")
    content = parse_mcp_content(args.input)
    tabs = split_tabs(content)
    logger.info(f"발견된 탭: {len(tabs)}개")

    saved = save_tabs(tabs, args.output_dir)
    logger.info(f"저장 완료: {len(saved)}개 파일 → {args.output_dir}")

    # 요약 출력
    print(f"\n📂 탭 분할 결과 ({len(tabs)}개 탭):")
    for idx, tab in enumerate(tabs):
        indent = "  " * tab.depth
        tid = f" ({tab.tab_id})" if tab.tab_id else ""
        print(f"  {indent}{idx:02d}. {tab.name}{tid}")


def cmd_extract_images(args):
    """이미지 추출 명령"""
    logger.info(f"MD 파일 처리: {args.input}")
    cleaned_md = extract_images(args.input, args.output_dir)

    # 변환된 MD 저장
    out_path = Path(args.output_dir) / Path(args.input).name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(cleaned_md, encoding='utf-8')

    images_dir = Path(args.output_dir) / "images"
    image_count = len(list(images_dir.glob("*"))) if images_dir.exists() else 0

    print(f"\n📂 이미지 추출 결과:")
    print(f"  MD: {out_path}")
    print(f"  이미지: {image_count}개 → {images_dir}/")


def cmd_full(args):
    """전체 처리 (탭 분할 + 이미지 추출)"""
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Step 1: 탭 분할
    if args.mcp_input:
        logger.info("=== Step 1: 탭 분할 ===")
        content = parse_mcp_content(args.mcp_input)
        tabs = split_tabs(content)
        logger.info(f"발견된 탭: {len(tabs)}개")
        saved = save_tabs(tabs, str(out / "tabs"))
        logger.info(f"탭 파일 저장: {len(saved)}개")
    else:
        logger.info("MCP 입력 없음 → 탭 분할 건너뜀")
        tabs = []

    # Step 2: 이미지 추출
    if args.md_input:
        logger.info("=== Step 2: 이미지 추출 ===")
        cleaned_md = extract_images(args.md_input, str(out))
        md_out = out / Path(args.md_input).name
        md_out.write_text(cleaned_md, encoding='utf-8')
        logger.info(f"변환된 MD: {md_out}")
    else:
        logger.info("MD 입력 없음 → 이미지 추출 건너뜀")

    # 요약
    print(f"\n📂 처리 결과:")
    if tabs:
        print(f"  탭: {len(tabs)}개 → {out / 'tabs'}/")
    images_dir = out / "images"
    if images_dir.exists():
        count = len(list(images_dir.glob("*")))
        print(f"  이미지: {count}개 → {images_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="Google Docs MD 후처리기 (MCP + 이미지 추출)"
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # split-tabs
    p_split = subparsers.add_parser(
        'split-tabs', help='MCP get_doc_content 결과를 탭별로 분할'
    )
    p_split.add_argument('--input', '-i', required=True, help='MCP 출력 파일 (JSON)')
    p_split.add_argument('--output-dir', '-o', default='./output', help='출력 디렉토리')
    p_split.set_defaults(func=cmd_split_tabs)

    # extract-images
    p_img = subparsers.add_parser(
        'extract-images', help='Google MD 내보내기에서 base64 이미지 추출'
    )
    p_img.add_argument('--input', '-i', required=True, help='Google MD 파일')
    p_img.add_argument('--output-dir', '-o', default='./output', help='출력 디렉토리')
    p_img.set_defaults(func=cmd_extract_images)

    # full
    p_full = subparsers.add_parser(
        'full', help='탭 분할 + 이미지 추출 전체 처리'
    )
    p_full.add_argument('--mcp-input', help='MCP 출력 파일 (JSON)')
    p_full.add_argument('--md-input', help='Google MD 파일')
    p_full.add_argument('--output-dir', '-o', default='./output', help='출력 디렉토리')
    p_full.set_defaults(func=cmd_full)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()

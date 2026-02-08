#!/usr/bin/env python3
"""
Google Docs MD 후처리기 (v4)

Google Docs를 탭별 MD 파일로 자동 변환:
  1. export: Google API 직접 호출 → 탭별 MD 다운로드 + 이미지 추출 (완전 자동)
  2. split-tabs: MCP get_doc_content 결과 분할 (수동)
  3. extract-images: base64 인라인 이미지 → 별도 PNG 파일 추출 (수동)

Usage:
  # 완전 자동화: 문서 ID만 넣으면 탭별 MD + 이미지 추출
  python gdocs_md_processor.py export DOC_ID --output-dir ./output

  # 특정 이메일 계정 사용
  python gdocs_md_processor.py export DOC_ID --account jhkim2@goqual.com

  # 탭 분할 (MCP get_doc_content 결과)
  python gdocs_md_processor.py split-tabs --input mcp_output.json --output-dir ./output

  # 이미지 추출 (Google Docs 네이티브 MD 내보내기)
  python gdocs_md_processor.py extract-images --input exported.md --output-dir ./output
"""

import argparse
import base64
import json
import logging
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

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
# Google API Client: 직접 API 호출
# ──────────────────────────────────────────────

MCP_CREDS_DIR = Path.home() / ".google_workspace_mcp_work" / "credentials"
DOCS_API_BASE = "https://docs.google.com/document/d"
DOCS_REST_API = "https://docs.googleapis.com/v1/documents"


class GoogleDocsClient:
    """MCP credentials를 재활용하여 Google Docs API 직접 호출"""

    def __init__(self, account: Optional[str] = None):
        self.creds = self._load_credentials(account)
        self.access_token = self._refresh_token()

    def _load_credentials(self, account: Optional[str]) -> Dict[str, Any]:
        if account:
            creds_path = MCP_CREDS_DIR / f"{account}.json"
        else:
            # 첫 번째 credentials 파일 사용
            creds_files = list(MCP_CREDS_DIR.glob("*.json"))
            if not creds_files:
                logger.error(f"MCP credentials 없음: {MCP_CREDS_DIR}")
                sys.exit(1)
            creds_path = creds_files[0]
            logger.info(f"계정: {creds_path.stem}")

        with open(creds_path, 'r') as f:
            return json.load(f)

    def _refresh_token(self) -> str:
        data = urllib.parse.urlencode({
            "client_id": self.creds["client_id"],
            "client_secret": self.creds["client_secret"],
            "refresh_token": self.creds["refresh_token"],
            "grant_type": "refresh_token",
        }).encode()
        req = urllib.request.Request(self.creds["token_uri"], data=data)
        with urllib.request.urlopen(req) as resp:
            token = json.loads(resp.read())["access_token"]
        logger.info("Google OAuth 토큰 갱신 완료")
        return token

    def _api_request(self, url: str) -> bytes:
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {self.access_token}"}
        )
        with urllib.request.urlopen(req) as resp:
            return resp.read()

    def get_tabs(self, doc_id: str) -> List[Dict[str, Any]]:
        """Docs API로 탭 목록 조회 (ID, 제목)"""
        url = f"{DOCS_REST_API}/{doc_id}?fields=tabs"
        data = json.loads(self._api_request(url))
        tabs = []
        self._collect_tabs(data.get("tabs", []), tabs, depth=0)
        return tabs

    def _collect_tabs(
        self, tab_list: List[Dict], result: List[Dict], depth: int
    ):
        for tab in tab_list:
            props = tab.get("tabProperties", {})
            result.append({
                "tab_id": props.get("tabId", ""),
                "title": props.get("title", "Untitled"),
                "depth": depth,
            })
            children = tab.get("childTabs", [])
            if children:
                self._collect_tabs(children, result, depth + 1)

    def export_tab_as_md(self, doc_id: str, tab_id: str) -> str:
        """개별 탭을 Markdown으로 내보내기"""
        url = f"{DOCS_API_BASE}/{doc_id}/export?format=markdown&tab={tab_id}"
        return self._api_request(url).decode("utf-8")


def extract_images_from_content(
    content: str, images_dir: Path, prefix: str = ""
) -> str:
    """MD 문자열에서 base64 이미지 추출 및 참조 변환 (파일 경로 불필요)"""
    images_dir.mkdir(parents=True, exist_ok=True)
    original_size = len(content)
    extracted: List[ExtractedImage] = []

    for match in IMAGE_DEF_PATTERN.finditer(content):
        ref_name = match.group('ref')
        fmt = match.group('fmt')
        raw_data = match.group('data').replace('\n', '').replace(' ', '')
        try:
            img_bytes = base64.b64decode(raw_data)
        except Exception as e:
            logger.warning(f"  {prefix}{ref_name} base64 디코딩 실패: {e}")
            continue

        filename = f"{prefix}{ref_name}.{fmt}" if prefix else f"{ref_name}.{fmt}"
        (images_dir / filename).write_bytes(img_bytes)
        extracted.append(ExtractedImage(
            ref_name=ref_name, format=fmt, data=img_bytes, filename=filename,
        ))
        logger.info(f"  {filename}: {len(img_bytes) / 1024:.1f} KB")

    cleaned = IMAGE_DEF_PATTERN.sub('', content)

    def replace_ref(m):
        alt = m.group('alt') or ''
        ref = m.group('ref')
        img = next((e for e in extracted if e.ref_name == ref), None)
        if img:
            label = alt if alt else ref
            return f"![{label}](images/{img.filename})"
        return m.group(0)

    cleaned = IMAGE_REF_PATTERN.sub(replace_ref, cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip() + '\n'

    cleaned_size = len(cleaned)
    if original_size > 0 and original_size != cleaned_size:
        logger.info(
            f"  크기: {original_size / 1024:.0f}KB → {cleaned_size / 1024:.0f}KB "
            f"({(1 - cleaned_size / original_size) * 100:.0f}% 감소)"
        )
    return cleaned


# ──────────────────────────────────────────────
# MD Escape Cleaner: Google Docs 불필요 이스케이프 정리
# ──────────────────────────────────────────────

# Google Docs MD export가 불필요하게 이스케이프하는 문자들
# 예: \~ \< \> \+ \- \. \) \= \& \_ \* \[ \]
_GDOCS_UNESCAPE = re.compile(
    r'\\([~<>+\-.)=&_*\[\]])'
)


def clean_md_escapes(content: str) -> str:
    r"""Google Docs MD export의 불필요한 이스케이프 문자 정리

    Google Docs는 MD 내보내기 시 특수문자를 과도하게 이스케이프합니다:
      \~ → ~  (물결표, 날짜 범위)
      \< → <  (비교 부호)
      \> → >  (비교 부호)
      \+ → +  (더하기)
      \- → -  (하이픈)
      \. → .  (마침표, 헤딩 번호)
      \) → )  (닫는 괄호)
      \= → =  (등호)
      \& → &  (앰퍼샌드)
      \_ → _  (밑줄)
      \* → *  (별표)
      \[ → [  (대괄호)
      \] → ]  (대괄호)
    """
    return _GDOCS_UNESCAPE.sub(r'\1', content)


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

# 이미지 참조: ![][imageN] 또는 ![alt text][imageN] (이스케이프된 \] 포함)
IMAGE_REF_PATTERN = re.compile(
    r'!\[(?P<alt>(?:[^\]\\]|\\.)*)\]\[(?P<ref>image\d+)\]'
)


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

    # 참조를 파일 경로로 변환: ![alt][imageN] → ![alt](images/imageN.png)
    def replace_ref(m):
        alt = m.group('alt') or ''
        ref = m.group('ref')
        img = next((e for e in extracted if e.ref_name == ref), None)
        if img:
            label = alt if alt else ref
            return f"![{label}](images/{img.filename})"
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


def cmd_export(args):
    """완전 자동화: 문서 ID → 탭별 MD + 이미지 추출"""
    doc_id = args.doc_id
    max_depth = args.depth  # 0=상위만, 1=1단계 하위, 2=2단계까지, -1=전체
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    images_dir = out / "images"

    # Step 1: Google API 인증
    logger.info("=== Step 1: Google API 인증 ===")
    client = GoogleDocsClient(account=args.account)

    # Step 2: 탭 목록 조회 (하위 탭 포함)
    logger.info("=== Step 2: 탭 목록 조회 ===")
    all_tabs = client.get_tabs(doc_id)

    # depth 필터링 (-1은 전체)
    if max_depth >= 0:
        tabs = [t for t in all_tabs if t["depth"] <= max_depth]
    else:
        tabs = all_tabs

    logger.info(f"전체 탭: {len(all_tabs)}개, 내보내기 대상: {len(tabs)}개 (depth≤{max_depth})")
    for t in all_tabs:
        indent = "  " * t["depth"]
        marker = "→" if t in tabs else "  (skip)"
        logger.info(f"  {indent}{t['title']} (depth={t['depth']}){marker}")

    # Step 3: 탭별 MD 다운로드 + 이미지 추출
    logger.info("=== Step 3: 탭별 MD 다운로드 ===")
    total_images = 0
    for idx, tab in enumerate(tabs):
        tab_title = tab["title"]
        tab_id = tab["tab_id"]
        depth = tab["depth"]
        safe_name = re.sub(r'[^\w가-힣\s\-\.]', '', tab_title)
        safe_name = re.sub(r'\s+', '-', safe_name.strip()) or "untitled"
        filename = f"{idx:02d}--{safe_name}.md"

        logger.info(f"  [{idx:02d}] {tab_title} (depth={depth}) 다운로드...")

        # Rate limit 대응: 429 시 최대 3회 재시도 (2초, 5초, 10초 대기)
        md_content = None
        for attempt, wait in enumerate([0, 2, 5, 10]):
            if wait > 0:
                logger.info(f"  [{idx:02d}] {wait}초 대기 후 재시도 ({attempt}/3)...")
                time.sleep(wait)
            try:
                md_content = client.export_tab_as_md(doc_id, tab_id)
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 3:
                    continue
                logger.error(f"  [{idx:02d}] HTTP {e.code}: {e.reason}")
                break

        if md_content is None:
            continue

        # 탭 간 요청 간격 (rate limit 방지)
        if idx < len(tabs) - 1:
            time.sleep(1)

        # 이미지 추출 (탭별 prefix로 충돌 방지)
        img_prefix = f"tab{idx:02d}-"
        cleaned = extract_images_from_content(md_content, images_dir, img_prefix)

        # 불필요한 이스케이프 정리 (\~, \<, \., \- 등)
        cleaned = clean_md_escapes(cleaned)

        # 탭 메타 주석 추가 (depth 정보 포함)
        header = f"<!-- tab-id: {tab_id} depth: {depth} -->\n\n"
        filepath = out / filename
        filepath.write_text(header + cleaned, encoding='utf-8')

        img_count = len(list(images_dir.glob(f"{img_prefix}*"))) if images_dir.exists() else 0
        total_images += img_count
        size_kb = len(cleaned) / 1024
        logger.info(f"  [{idx:02d}] {filename} ({size_kb:.1f}KB, 이미지 {img_count}개)")

    # 요약
    print(f"\n결과: {len(tabs)}개 탭 → {out}/")
    print(f"  MD 파일: {len(tabs)}개")
    if total_images > 0:
        print(f"  이미지: {total_images}개 → {images_dir}/")


def cmd_full(args):
    """전체 처리 (탭 분할 + 이미지 추출) - 레거시"""
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
    print(f"\n처리 결과:")
    if tabs:
        print(f"  탭: {len(tabs)}개 → {out / 'tabs'}/")
    images_dir = out / "images"
    if images_dir.exists():
        count = len(list(images_dir.glob("*")))
        print(f"  이미지: {count}개 → {images_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="Google Docs MD 변환기 (탭별 자동 내보내기 + 이미지 추출)"
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # export (주요 명령)
    p_export = subparsers.add_parser(
        'export', help='Google Docs → 탭별 MD 자동 내보내기 (완전 자동화)'
    )
    p_export.add_argument('doc_id', help='Google Docs 문서 ID')
    p_export.add_argument('--output-dir', '-o', default='./output', help='출력 디렉토리')
    p_export.add_argument('--account', '-a', help='Google 계정 (예: user@gmail.com)')
    p_export.add_argument(
        '--depth', '-d', type=int, default=-1,
        help='탭 깊이 제한 (0=상위만, 1=1단계 하위, -1=전체, 기본: -1)',
    )
    p_export.set_defaults(func=cmd_export)

    # split-tabs (레거시)
    p_split = subparsers.add_parser(
        'split-tabs', help='MCP get_doc_content 결과를 탭별로 분할'
    )
    p_split.add_argument('--input', '-i', required=True, help='MCP 출력 파일 (JSON)')
    p_split.add_argument('--output-dir', '-o', default='./output', help='출력 디렉토리')
    p_split.set_defaults(func=cmd_split_tabs)

    # extract-images (레거시)
    p_img = subparsers.add_parser(
        'extract-images', help='Google MD 내보내기에서 base64 이미지 추출'
    )
    p_img.add_argument('--input', '-i', required=True, help='Google MD 파일')
    p_img.add_argument('--output-dir', '-o', default='./output', help='출력 디렉토리')
    p_img.set_defaults(func=cmd_extract_images)

    # full (레거시)
    p_full = subparsers.add_parser(
        'full', help='탭 분할 + 이미지 추출 (레거시)'
    )
    p_full.add_argument('--mcp-input', help='MCP 출력 파일 (JSON)')
    p_full.add_argument('--md-input', help='Google MD 파일')
    p_full.add_argument('--output-dir', '-o', default='./output', help='출력 디렉토리')
    p_full.set_defaults(func=cmd_full)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()

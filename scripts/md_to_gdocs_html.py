#!/usr/bin/env python3
"""
md_to_gdocs_html.py — Markdown → Google Docs 붙여넣기용 HTML 변환기

최적 경로: MD → Org (md_to_gdocs.py) → HTML (pandoc org→html5) → inline style 주입

Google Docs는 <style> 블록과 CSS class를 무시한다.
모든 서식을 inline style로 넣어야 붙여넣기 시 유지된다.

사용법:
    python scripts/md_to_gdocs_html.py INPUT.md [-o OUTPUT.html] [--open]
    python scripts/md_to_gdocs_html.py INPUT.org [-o OUTPUT.html] [--open]

파이프라인:
    1. MD인 경우 → md_to_gdocs.py의 md_to_org()로 Org 변환 (코드블록/테이블 정확 변환)
    2. Org → pandoc -f org -t html5 (깔끔한 <pre> 생성)
    3. inline style 주입 (모노스페이스, 테이블 테두리, 줄별 <div>)
    4. Google Docs 붙여넣기 최적화
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


# ── 스타일 정의 ──────────────────────────────────────────────────────

MONO_FONT = "'Courier New', Courier, monospace"
BODY_FONT = "'Arial', sans-serif"

STYLES = {
    "body": f"font-family: {BODY_FONT}; font-size: 11pt; line-height: 1.5; color: #1a1a1a; max-width: 800px; margin: 20px auto; padding: 0 20px;",
    "h1": f"font-family: {BODY_FONT}; font-size: 20pt; font-weight: bold; margin: 24px 0 12px 0; color: #1a1a1a; border-bottom: 1px solid #e0e0e0; padding-bottom: 6px;",
    "h2": f"font-family: {BODY_FONT}; font-size: 16pt; font-weight: bold; margin: 20px 0 10px 0; color: #1a1a1a;",
    "h3": f"font-family: {BODY_FONT}; font-size: 13pt; font-weight: bold; margin: 16px 0 8px 0; color: #1a1a1a;",
    "h4": f"font-family: {BODY_FONT}; font-size: 11pt; font-weight: bold; margin: 12px 0 6px 0; color: #1a1a1a;",
    "h5": f"font-family: {BODY_FONT}; font-size: 11pt; font-weight: bold; font-style: italic; margin: 10px 0 6px 0; color: #333;",
    "h6": f"font-family: {BODY_FONT}; font-size: 10pt; font-weight: bold; margin: 10px 0 6px 0; color: #555;",
    "p": f"font-family: {BODY_FONT}; font-size: 11pt; margin: 6px 0;",
    "li": f"font-family: {BODY_FONT}; font-size: 11pt; margin: 3px 0;",
    "ul": "margin: 6px 0; padding-left: 24px;",
    "ol": "margin: 6px 0; padding-left: 24px;",
    # 코드블록 — 핵심! 줄별 div로 쪼개므로 pre 자체는 컨테이너 역할
    "pre": f"font-family: {MONO_FONT}; font-size: 9pt; background-color: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px; padding: 12px; margin: 8px 0; line-height: 1.4; white-space: pre; overflow-x: auto;",
    # 인라인 코드
    "code_inline": f"font-family: {MONO_FONT}; font-size: 9.5pt; background-color: #f0f0f0; padding: 1px 4px; border-radius: 3px;",
    # 코드블록 내부 code 태그 (pre > code)
    "code_block": f"font-family: {MONO_FONT}; font-size: 9pt; background-color: transparent; padding: 0; border: none;",
    # 코드블록 내부 각 줄 (div로 감쌈)
    "code_line": f"font-family: {MONO_FONT}; font-size: 9pt; white-space: pre; min-height: 1em;",
    # 테이블
    "table": "border-collapse: collapse; margin: 10px 0; width: auto;",
    "th": f"font-family: {BODY_FONT}; font-size: 10pt; font-weight: bold; border: 1px solid #d0d7de; padding: 6px 12px; background-color: #f6f8fa; text-align: left;",
    "td": f"font-family: {BODY_FONT}; font-size: 10pt; border: 1px solid #d0d7de; padding: 6px 12px; text-align: left;",
    # 인용
    "blockquote": f"font-family: {BODY_FONT}; font-size: 11pt; border-left: 3px solid #d0d7de; padding: 4px 12px; margin: 8px 0; color: #57606a;",
    # 구분선
    "hr": "border: none; border-top: 1px solid #d0d7de; margin: 16px 0;",
    # 강조
    "strong": "font-weight: bold;",
    "em": "font-style: italic;",
    # 링크
    "a": "color: #0969da; text-decoration: underline;",
}


# ── HTML 인라인 스타일 주입기 ────────────────────────────────────────

class GDocsStyleInjector:
    """pandoc 출력 HTML에 Google Docs 호환 inline style을 주입한다."""

    def __init__(self, html: str):
        self.html = html

    def process(self) -> str:
        """전체 처리 파이프라인."""
        html = self.html

        # 1단계: 태그별 inline style 주입
        html = self._inject_tag_styles(html)

        # 2단계: <pre><code>...</code></pre> 내부를 줄별 div로 분할
        html = self._split_code_lines(html)

        # 3단계: inline code (pre 밖의 code) 스타일 적용
        html = self._style_inline_code(html)

        # 4단계: <li> 앞에 \n 삽입 (Google Docs 줄바꿈 트릭)
        html = html.replace("<li", "\n<li")

        # 5단계: <style> 블록 제거 (Google Docs에서 무시되므로 불필요)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)

        return html

    def _inject_tag_styles(self, html: str) -> str:
        """각 태그에 inline style을 주입한다."""
        simple_tags = [
            "body", "h1", "h2", "h3", "h4", "h5", "h6",
            "p", "li", "ul", "ol", "table", "th", "td",
            "blockquote", "hr", "strong", "em", "a",
        ]
        for tag in simple_tags:
            if tag in STYLES:
                style = STYLES[tag]
                # 기존 style이 있는 경우 병합
                html = re.sub(
                    rf'<{tag}(\s+style="[^"]*")',
                    lambda m: f'<{tag} style="{style}; ' + m.group(1).split('"')[1] + '"',
                    html
                )
                # style이 없는 경우 추가
                html = re.sub(
                    rf'<{tag}([\s>])',
                    lambda m, t=tag, s=style: f'<{t} style="{s}"{m.group(1)}',
                    html
                )

        # pre 태그 (특별 처리 — 이미 class가 있을 수 있음)
        html = re.sub(
            r'<pre[^>]*>',
            f'<pre style="{STYLES["pre"]}">',
            html
        )

        return html

    def _split_code_lines(self, html: str) -> str:
        """<pre><code>...</code></pre> 내부를 줄별 <div>로 감싼다.

        Google Docs는 <pre> 안의 줄바꿈을 무시하는 경향이 있다.
        각 줄을 <div style="...">로 감싸면 강제 줄바꿈 + 모노스페이스가 유지된다.
        """
        def replace_code_block(match):
            full = match.group(0)
            # <pre ...><code ...> 와 </code></pre> 사이의 내용 추출
            inner_match = re.search(r'<code[^>]*>(.*?)</code>', full, re.DOTALL)
            if not inner_match:
                return full

            content = inner_match.group(1)
            lines = content.split('\n')

            # 마지막 빈 줄 제거 (pandoc이 넣는 trailing newline)
            if lines and lines[-1].strip() == '':
                lines = lines[:-1]

            styled_lines = []
            line_style = STYLES["code_line"]
            for line in lines:
                # 빈 줄은 non-breaking space로 최소 높이 보장
                display_line = line if line.strip() else '&nbsp;'
                styled_lines.append(
                    f'<div style="{line_style}">{display_line}</div>'
                )

            return (
                f'<pre style="{STYLES["pre"]}">'
                f'<code style="{STYLES["code_block"]}">'
                + ''.join(styled_lines)
                + '</code></pre>'
            )

        html = re.sub(
            r'<pre[^>]*>\s*<code[^>]*>.*?</code>\s*</pre>',
            replace_code_block,
            html,
            flags=re.DOTALL
        )
        return html

    def _style_inline_code(self, html: str) -> str:
        """<pre> 밖의 <code> 태그에 인라인 코드 스타일을 적용한다."""
        # 이미 code_block 스타일이 적용된 것은 건드리지 않음
        block_style = STYLES["code_block"]
        inline_style = STYLES["code_inline"]

        def replace_inline_code(match):
            if block_style in match.group(0):
                return match.group(0)  # 블록 코드는 스킵
            attrs = match.group(1) or ''
            return f'<code style="{inline_style}"{attrs}>'

        html = re.sub(r'<code(?:\s+([^>]*))?\s*>', replace_inline_code, html)
        return html


# ── MD → Org 변환 (md_to_gdocs.py 재사용) ───────────────────────────

def _md_to_org(input_path: Path) -> Path:
    """MD 파일을 Org로 변환한다. md_to_gdocs.py의 md_to_org()를 import."""
    sys.path.insert(0, str(SCRIPT_DIR))
    from md_to_gdocs import md_to_org

    org_content = md_to_org(input_path)

    # Org 헤더
    title = input_path.stem.replace('-', ' ').replace('_', ' ').title()
    header = f"#+TITLE: {title}\n#+OPTIONS: toc:nil author:nil num:t\n\n"

    org_path = Path(f"/tmp/{input_path.stem}-gdocs.org")
    org_path.write_text(header + org_content, encoding='utf-8')
    return org_path


# ── Org → HTML (pandoc) ─────────────────────────────────────────────

def _org_to_html(org_path: Path) -> str:
    """pandoc으로 Org → HTML5 변환."""
    cmd = [
        "pandoc", str(org_path),
        "-f", "org", "-t", "html5",
        "-s", "--wrap=preserve", "--no-highlight",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ pandoc 실행 실패: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("❌ pandoc이 설치되어 있지 않습니다.", file=sys.stderr)
        sys.exit(1)
    return result.stdout


# ── 메인 ─────────────────────────────────────────────────────────────

def convert_to_gdocs_html(input_path: str, output_path: str | None = None) -> str:
    """입력 파일(MD/Org)을 Google Docs 붙여넣기용 HTML로 변환한다.

    MD → Org → HTML → inline style 주입
    """
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {input_path}", file=sys.stderr)
        sys.exit(1)

    suffix = input_path.suffix.lower()

    # Step 1: MD → Org (이미 Org면 스킵)
    if suffix in ('.md', '.markdown', '.mkd'):
        print(f"📝 MD → Org: {input_path.name}")
        org_path = _md_to_org(input_path)
        print(f"   → {org_path}")
    elif suffix == '.org':
        org_path = input_path
    else:
        org_path = input_path  # 기본값: org로 시도

    # Step 2: Org → HTML (pandoc)
    print(f"📄 Org → HTML: {org_path.name}")
    raw_html = _org_to_html(org_path)

    # Step 3: inline style 주입
    injector = GDocsStyleInjector(raw_html)
    styled_html = injector.process()

    # 출력 경로
    if output_path is None:
        output_path = f"/tmp/{input_path.stem}-gdocs.html"
    Path(output_path).write_text(styled_html, encoding='utf-8')

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="Markdown/Org → Google Docs 붙여넣기용 HTML (MD→Org→HTML→inline style)",
        epilog="예시: python scripts/md_to_gdocs_html.py README.md --open",
    )
    parser.add_argument("input", help="입력 파일 (MD 또는 Org)")
    parser.add_argument("-o", "--output", help="출력 HTML 경로 (기본: /tmp/<이름>-gdocs.html)")
    parser.add_argument("--open", action="store_true", help="변환 후 브라우저에서 열기")

    args = parser.parse_args()

    output = convert_to_gdocs_html(args.input, args.output)
    print(f"✅ 변환 완료: {output}")
    print(f"   브라우저에서 열고 → Ctrl+A → Ctrl+C → Google Docs에 Ctrl+V")

    if args.open:
        subprocess.Popen(["xdg-open", output], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"   🌐 브라우저에서 열었습니다.")


if __name__ == "__main__":
    main()

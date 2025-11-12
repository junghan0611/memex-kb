#!/usr/bin/env python3
"""
Confluence to Markdown Converter for Memex-KB
==============================================

Confluence에서 export한 .doc 파일(실제로는 MIME HTML)을
Denote 규칙을 따르는 깨끗한 Markdown으로 변환합니다.

Author: junghanacs (with Claude Code)
Date: 2025-11-12
Version: 1.0.0

Usage:
    python3 confluence_to_markdown.py input.doc [output.md]
    python3 confluence_to_markdown.py --batch input_dir/ output_dir/

Features:
    - MIME 메시지 파싱으로 깨끗한 HTML 추출
    - UTF-8 인코딩 완벽 보존 (한글 문제 해결)
    - Pandoc을 통한 Markdown 변환
    - Fenced div (:::) 제거 및 코드 블록 정리
    - 헤딩 ID 속성 정리
    - Unicode NFD → NFC 정규화

Requirements:
    - Python 3.8+
    - pandoc
    - email (built-in)
"""

import argparse
import email
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from email import policy
from pathlib import Path
from typing import Optional, Tuple


class ConfluenceConverter:
    """Confluence .doc 파일을 Markdown으로 변환하는 클래스"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def log(self, message: str):
        """로그 출력"""
        if self.verbose:
            print(f"[INFO] {message}", file=sys.stderr)

    def extract_html_from_mime(self, doc_file: Path) -> str:
        """
        Confluence export .doc 파일에서 HTML 추출

        Args:
            doc_file: .doc 파일 경로

        Returns:
            UTF-8로 인코딩된 HTML 문자열
        """
        self.log(f"MIME 메시지 파싱: {doc_file}")

        with open(doc_file, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)

        # HTML 파트 찾기
        html_content = None
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                html_content = part.get_content()
                break

        if not html_content:
            raise ValueError("HTML 파트를 찾을 수 없습니다. Confluence export 파일이 아닐 수 있습니다.")

        self.log(f"HTML 추출 완료: {len(html_content)} bytes")
        return html_content

    def convert_html_to_markdown(self, html_content: str) -> str:
        """
        Pandoc으로 HTML을 Markdown으로 변환

        Args:
            html_content: HTML 문자열

        Returns:
            Markdown 문자열
        """
        self.log("Pandoc 변환 시작 (HTML → Markdown)")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.html',
                                         encoding='utf-8', delete=False) as tmp_html:
            tmp_html.write(html_content)
            tmp_html_path = tmp_html.name

        try:
            result = subprocess.run(
                ['pandoc', tmp_html_path, '-f', 'html', '-t', 'markdown', '--wrap=none'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=60
            )

            if result.returncode != 0:
                raise RuntimeError(f"Pandoc 변환 실패: {result.stderr}")

            markdown = result.stdout
            self.log(f"Pandoc 변환 완료: {len(markdown)} bytes")
            return markdown

        finally:
            os.unlink(tmp_html_path)

    def clean_markdown(self, markdown: str) -> str:
        """
        Markdown 후처리: fenced div 제거, 코드 블록 정리, 헤딩 정리

        Args:
            markdown: 원본 Markdown

        Returns:
            정리된 Markdown
        """
        self.log("Markdown 후처리 시작")

        # 1. 긴 Section1 구분자 제거
        markdown = re.sub(r'^:{3,}.*Section\d+.*$', '', markdown, flags=re.MULTILINE)

        # 2. 빈 fenced div 제거
        markdown = re.sub(r'^:{3,}\s*{[^}]*}\s*$', '', markdown, flags=re.MULTILINE)
        markdown = re.sub(r'^:{3,}\s*$', '', markdown, flags=re.MULTILINE)

        # 3. 불필요한 클래스 속성이 있는 fenced div 제거
        markdown = re.sub(r'^:{3,}\s+\{\.[\w\s\-\.]+\}$', '', markdown, flags=re.MULTILINE)
        markdown = re.sub(r'^:{3,}\s+[\w\-]+$', '', markdown, flags=re.MULTILINE)

        # 4. 코드 블록의 복잡한 속성을 json으로 정리
        markdown = re.sub(
            r'```\s*\{\.syntaxhighlighter-pre[^}]+\}',
            '```json',
            markdown
        )

        # 5. 헤딩 ID 간소화 (한글 ID 제거)
        markdown = re.sub(r'\s+{#[^}]+}', '', markdown)

        # 6. 연속된 빈 줄 정리 (3개 이상 → 2개로)
        markdown = re.sub(r'\n{4,}', '\n\n\n', markdown)

        # 7. 파일 시작 부분 정리
        markdown = markdown.lstrip()

        # 8. Unicode NFD → NFC 정규화 (한글 조합형 → 완성형)
        markdown = unicodedata.normalize('NFC', markdown)

        self.log("Markdown 후처리 완료")
        return markdown

    def extract_title_from_markdown(self, markdown: str) -> Optional[str]:
        """
        Markdown에서 제목 추출 (첫 번째 # 헤딩)

        Args:
            markdown: Markdown 문자열

        Returns:
            제목 또는 None
        """
        match = re.search(r'^# (.+)$', markdown, re.MULTILINE)
        return match.group(1).strip() if match else None

    def convert_file(self, input_file: Path, output_file: Optional[Path] = None) -> Tuple[Path, str]:
        """
        단일 파일 변환

        Args:
            input_file: 입력 .doc 파일
            output_file: 출력 .md 파일 (None이면 자동 생성)

        Returns:
            (출력 파일 경로, 제목) 튜플
        """
        if not input_file.exists():
            raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")

        # HTML 추출
        html_content = self.extract_html_from_mime(input_file)

        # Markdown 변환
        markdown = self.convert_html_to_markdown(html_content)

        # 후처리
        markdown = self.clean_markdown(markdown)

        # 제목 추출
        title = self.extract_title_from_markdown(markdown)

        # 출력 파일명 결정
        if output_file is None:
            output_file = input_file.with_suffix('.md')

        # 저장
        output_file.write_text(markdown, encoding='utf-8')
        self.log(f"변환 완료: {output_file}")

        return output_file, title or "Untitled"

    def convert_batch(self, input_dir: Path, output_dir: Path):
        """
        디렉토리 일괄 변환

        Args:
            input_dir: 입력 디렉토리
            output_dir: 출력 디렉토리
        """
        if not input_dir.is_dir():
            raise NotADirectoryError(f"입력 디렉토리가 아닙니다: {input_dir}")

        output_dir.mkdir(parents=True, exist_ok=True)

        doc_files = list(input_dir.glob('*.doc'))
        if not doc_files:
            print(f"⚠️  {input_dir}에 .doc 파일이 없습니다.")
            return

        print(f"📁 {len(doc_files)}개 파일 발견")
        print(f"   입력: {input_dir}")
        print(f"   출력: {output_dir}\n")

        success_count = 0
        fail_count = 0

        for i, doc_file in enumerate(doc_files, 1):
            try:
                output_file = output_dir / doc_file.with_suffix('.md').name
                result_file, title = self.convert_file(doc_file, output_file)
                print(f"✅ [{i}/{len(doc_files)}] {doc_file.name}")
                print(f"   → {result_file.name}")
                print(f"   📄 {title}\n")
                success_count += 1
            except Exception as e:
                print(f"❌ [{i}/{len(doc_files)}] {doc_file.name}")
                print(f"   오류: {e}\n")
                fail_count += 1

        print(f"\n📊 변환 결과:")
        print(f"   성공: {success_count}")
        print(f"   실패: {fail_count}")


def main():
    parser = argparse.ArgumentParser(
        description="Confluence export .doc → Markdown 변환기 (Memex-KB)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 단일 파일 변환
  %(prog)s document.doc

  # 출력 파일명 지정
  %(prog)s document.doc output.md

  # 일괄 변환
  %(prog)s --batch input_dir/ output_dir/

  # 자세한 로그 출력
  %(prog)s -v document.doc
        """
    )

    parser.add_argument('input', type=Path, help='입력 파일 또는 디렉토리')
    parser.add_argument('output', type=Path, nargs='?', help='출력 파일 또는 디렉토리')
    parser.add_argument('--batch', '-b', action='store_true', help='일괄 변환 모드')
    parser.add_argument('--verbose', '-v', action='store_true', help='자세한 로그 출력')

    args = parser.parse_args()

    converter = ConfluenceConverter(verbose=args.verbose)

    try:
        if args.batch:
            if not args.output:
                parser.error("일괄 변환 모드에서는 출력 디렉토리가 필요합니다.")
            converter.convert_batch(args.input, args.output)
        else:
            result_file, title = converter.convert_file(args.input, args.output)
            print(f"✅ 변환 완료!")
            print(f"   📄 {title}")
            print(f"   💾 {result_file}")

    except KeyboardInterrupt:
        print("\n❌ 사용자가 중단했습니다.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"❌ 오류 발생: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

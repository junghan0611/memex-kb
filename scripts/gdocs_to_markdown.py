#!/usr/bin/env python3
"""
Google Docs to Markdown 변환기
Google Docs API를 사용하여 문서를 Markdown으로 변환
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from dotenv import load_dotenv

# 로컬 모듈
from denote_namer import DenoteNamer
from categorizer import DocumentCategorizer

# 환경변수 로드
load_dotenv('config/.env')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Google API 스코프
SCOPES = [
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]


class GoogleDocsToMarkdown:
    """Google Docs를 Markdown으로 변환하는 클래스"""

    def __init__(self, credentials_path: Optional[str] = None):
        """
        초기화

        Args:
            credentials_path: Google API 인증 파일 경로
        """
        self.creds = self._authenticate(credentials_path)
        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.namer = DenoteNamer()
        self.categorizer = DocumentCategorizer()

    def _authenticate(self, credentials_path: Optional[str] = None) -> Credentials:
        """
        Google API 인증

        Args:
            credentials_path: 인증 파일 경로

        Returns:
            Credentials: 인증 객체
        """
        creds = None

        # 환경변수에서 경로 가져오기
        if not credentials_path:
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'config/credentials.json')

        token_path = os.getenv('GOOGLE_OAUTH_TOKEN_FILE', 'config/token.json')

        # 기존 토큰이 있으면 로드
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # 토큰이 없거나 유효하지 않으면 새로 생성
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Service Account 또는 OAuth 2.0 사용
                if credentials_path.endswith('.json'):
                    # Service Account 시도
                    try:
                        creds = service_account.Credentials.from_service_account_file(
                            credentials_path, scopes=SCOPES
                        )
                    except:
                        # OAuth 2.0 플로우
                        flow = InstalledAppFlow.from_client_secrets_file(
                            credentials_path, SCOPES
                        )
                        creds = flow.run_local_server(port=0)

                # 토큰 저장
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())

        return creds

    def get_document(self, document_id: str) -> Dict:
        """
        Google Docs 문서 가져오기

        Args:
            document_id: 문서 ID

        Returns:
            Dict: 문서 객체
        """
        try:
            document = self.docs_service.documents().get(
                documentId=document_id
            ).execute()
            return document
        except HttpError as error:
            logger.error(f"문서를 가져올 수 없습니다: {error}")
            return None

    def get_document_metadata(self, document_id: str) -> Dict:
        """
        문서 메타데이터 가져오기

        Args:
            document_id: 문서 ID

        Returns:
            Dict: 메타데이터
        """
        try:
            file_metadata = self.drive_service.files().get(
                fileId=document_id,
                fields='name,modifiedTime,lastModifyingUser'
            ).execute()

            return {
                'title': file_metadata.get('name', 'Untitled'),
                'modified': file_metadata.get('modifiedTime'),
                'author': file_metadata.get('lastModifyingUser', {}).get('emailAddress', 'Unknown')
            }
        except HttpError as error:
            logger.error(f"메타데이터를 가져올 수 없습니다: {error}")
            return {}

    def convert_to_markdown(self, document: Dict) -> str:
        """
        Google Docs 문서를 Markdown으로 변환

        Args:
            document: Google Docs 문서 객체

        Returns:
            str: Markdown 텍스트
        """
        if not document:
            return ""

        content = document.get('body', {}).get('content', [])
        markdown_lines = []
        list_level = 0

        for element in content:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                text = self._extract_paragraph_text(paragraph)

                # 스타일 확인
                style = paragraph.get('paragraphStyle', {})
                named_style = style.get('namedStyleType', '')

                # 제목 처리
                if named_style.startswith('HEADING'):
                    level = int(named_style.replace('HEADING_', '')) if 'HEADING_' in named_style else 1
                    markdown_lines.append(f"{'#' * level} {text}")
                    markdown_lines.append("")

                # 리스트 처리
                elif paragraph.get('bullet'):
                    bullet = paragraph['bullet']
                    nesting_level = bullet.get('nestingLevel', 0)

                    # 순서 있는 리스트
                    if bullet.get('listId'):
                        list_properties = document.get('lists', {}).get(bullet['listId'], {})
                        if self._is_ordered_list(list_properties, nesting_level):
                            markdown_lines.append(f"{'   ' * nesting_level}1. {text}")
                        else:
                            markdown_lines.append(f"{'   ' * nesting_level}- {text}")
                    else:
                        markdown_lines.append(f"{'   ' * nesting_level}- {text}")

                # 일반 단락
                elif text.strip():
                    markdown_lines.append(text)
                    markdown_lines.append("")

            # 테이블 처리 (간단한 버전)
            elif 'table' in element:
                markdown_lines.append(self._convert_table(element['table']))
                markdown_lines.append("")

        return '\n'.join(markdown_lines)

    def _extract_paragraph_text(self, paragraph: Dict) -> str:
        """
        단락에서 텍스트 추출

        Args:
            paragraph: 단락 객체

        Returns:
            str: 추출된 텍스트
        """
        text_elements = []

        for element in paragraph.get('elements', []):
            text_run = element.get('textRun', {})
            if text_run:
                content = text_run.get('content', '')

                # 텍스트 스타일 처리
                text_style = text_run.get('textStyle', {})

                # 볼드
                if text_style.get('bold'):
                    content = f"**{content.strip()}**"

                # 이탤릭
                if text_style.get('italic'):
                    content = f"*{content.strip()}*"

                # 코드
                if text_style.get('weightedFontFamily', {}).get('fontFamily') == 'Courier New':
                    content = f"`{content.strip()}`"

                # 링크
                if text_style.get('link'):
                    url = text_style['link'].get('url', '')
                    content = f"[{content.strip()}]({url})"

                text_elements.append(content)

        return ''.join(text_elements).strip()

    def _is_ordered_list(self, list_properties: Dict, nesting_level: int) -> bool:
        """
        순서 있는 리스트인지 확인

        Args:
            list_properties: 리스트 속성
            nesting_level: 중첩 레벨

        Returns:
            bool: 순서 있는 리스트 여부
        """
        nesting_levels = list_properties.get('nestingLevels', [])
        if nesting_level < len(nesting_levels):
            glyph_type = nesting_levels[nesting_level].get('glyphType', '')
            return glyph_type in ['DECIMAL', 'ALPHA', 'ROMAN']
        return False

    def _convert_table(self, table: Dict) -> str:
        """
        테이블을 Markdown으로 변환

        Args:
            table: 테이블 객체

        Returns:
            str: Markdown 테이블
        """
        rows = table.get('tableRows', [])
        if not rows:
            return ""

        markdown_table = []

        for i, row in enumerate(rows):
            cells = []
            for cell in row.get('tableCells', []):
                cell_text = self._extract_cell_text(cell)
                cells.append(cell_text)

            markdown_table.append('| ' + ' | '.join(cells) + ' |')

            # 헤더 구분선 추가
            if i == 0:
                markdown_table.append('|' + '---|' * len(cells))

        return '\n'.join(markdown_table)

    def _extract_cell_text(self, cell: Dict) -> str:
        """
        테이블 셀에서 텍스트 추출

        Args:
            cell: 셀 객체

        Returns:
            str: 추출된 텍스트
        """
        text_parts = []
        for element in cell.get('content', []):
            if 'paragraph' in element:
                text = self._extract_paragraph_text(element['paragraph'])
                text_parts.append(text)
        return ' '.join(text_parts)

    def process_document(
        self,
        document_id: str,
        output_dir: str = "docs"
    ) -> Dict[str, Any]:
        """
        문서 처리 (변환, 분류, 저장)

        Args:
            document_id: Google Docs 문서 ID
            output_dir: 출력 디렉토리

        Returns:
            Dict: 처리 결과
        """
        # 문서 가져오기
        document = self.get_document(document_id)
        if not document:
            return {'success': False, 'error': 'Document not found'}

        # 메타데이터 가져오기
        metadata = self.get_document_metadata(document_id)

        # Markdown 변환
        markdown_content = self.convert_to_markdown(document)

        # 문서 분석 (분류 및 태그)
        analysis = self.categorizer.analyze_document(
            title=metadata.get('title', 'Untitled'),
            content=markdown_content,
            filename=metadata.get('title', '')
        )

        # Denote 파일명 생성
        filename = self.namer.generate_filename(
            title=metadata.get('title', 'Untitled'),
            tags=analysis['tags'],
            date=datetime.fromisoformat(metadata.get('modified', datetime.now().isoformat()).replace('Z', '+00:00'))
        )

        # 카테고리별 디렉토리에 저장
        category_dir = Path(output_dir) / analysis['category']
        category_dir.mkdir(parents=True, exist_ok=True)

        output_path = category_dir / filename

        # 메타데이터를 포함한 Markdown 생성
        full_markdown = self._add_metadata_to_markdown(
            markdown_content,
            metadata,
            analysis,
            document_id
        )

        # 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_markdown)

        logger.info(f"문서 저장 완료: {output_path}")

        return {
            'success': True,
            'document_id': document_id,
            'title': metadata.get('title'),
            'filename': filename,
            'category': analysis['category'],
            'tags': analysis['tags'],
            'output_path': str(output_path),
            'needs_review': analysis['needs_review']
        }

    def _add_metadata_to_markdown(
        self,
        markdown: str,
        metadata: Dict,
        analysis: Dict,
        document_id: str
    ) -> str:
        """
        Markdown에 메타데이터 추가

        Args:
            markdown: Markdown 내용
            metadata: 문서 메타데이터
            analysis: 분석 결과
            document_id: 문서 ID

        Returns:
            str: 메타데이터가 포함된 Markdown
        """
        header = f"""---
title: {metadata.get('title', 'Untitled')}
author: {metadata.get('author', 'Unknown')}
modified: {metadata.get('modified', datetime.now().isoformat())}
category: {analysis['category']}
tags: {', '.join(analysis['tags'])}
source: https://docs.google.com/document/d/{document_id}
auto_generated: {datetime.now().isoformat()}
needs_review: {analysis['needs_review']}
---

# {metadata.get('title', 'Untitled')}

"""
        return header + markdown


def main():
    """테스트 실행"""
    import sys

    if len(sys.argv) < 2:
        print("사용법: python gdocs_to_markdown.py <DOCUMENT_ID>")
        sys.exit(1)

    document_id = sys.argv[1]

    # 변환기 초기화
    converter = GoogleDocsToMarkdown()

    # 문서 처리
    result = converter.process_document(document_id)

    if result['success']:
        print(f"✅ 변환 성공!")
        print(f"   제목: {result['title']}")
        print(f"   카테고리: {result['category']}")
        print(f"   태그: {', '.join(result['tags'])}")
        print(f"   파일: {result['output_path']}")
        if result['needs_review']:
            print(f"   ⚠️  검토 필요: 분류 정확도가 낮습니다.")
    else:
        print(f"❌ 변환 실패: {result.get('error')}")


if __name__ == "__main__":
    main()
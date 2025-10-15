#!/usr/bin/env python3
"""
Google Docs to Markdown 변환기 V2
외부 도구(Pandoc)를 활용한 더 안정적인 변환
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# 로컬 모듈
from denote_namer import DenoteNamer
from categorizer import DocumentCategorizer

# 환경변수 로드
load_dotenv('config/.env')

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google API 스코프
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly'
]


class ImprovedGoogleDocsConverter:
    """개선된 Google Docs 변환기 - 외부 도구 활용"""

    def __init__(self, method: str = "pandoc"):
        """
        초기화

        Args:
            method: 변환 방법 ("pandoc", "rclone", "api")
        """
        self.method = method
        self.creds = self._authenticate()
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.namer = DenoteNamer()
        self.categorizer = DocumentCategorizer()

    def _authenticate(self) -> Any:
        """Google API 인증"""
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'config/credentials.json')

        try:
            creds = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=SCOPES
            )
            return creds
        except Exception as e:
            logger.error(f"인증 실패: {e}")
            raise

    def check_dependencies(self) -> bool:
        """필요한 외부 도구 확인"""
        tools_needed = {
            "pandoc": ["pandoc"],
            "rclone": ["rclone", "pandoc"],
            "api": []
        }

        missing = []
        for tool in tools_needed.get(self.method, []):
            if subprocess.run(["which", tool], capture_output=True).returncode != 0:
                missing.append(tool)

        if missing:
            logger.error(f"필요한 도구가 없습니다: {', '.join(missing)}")
            logger.info(f"설치: sudo apt install {' '.join(missing)}")
            return False

        return True

    def export_as_docx(self, document_id: str, output_path: str) -> bool:
        """
        Google Docs를 DOCX로 다운로드

        Args:
            document_id: 문서 ID
            output_path: 저장 경로

        Returns:
            bool: 성공 여부
        """
        try:
            request = self.drive_service.files().export_media(
                fileId=document_id,
                mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )

            with open(output_path, 'wb') as f:
                downloader = request.execute()
                f.write(downloader)

            logger.info(f"DOCX 다운로드 완료: {output_path}")
            return True

        except HttpError as error:
            logger.error(f"다운로드 실패: {error}")
            return False

    def convert_with_pandoc(self, docx_path: str, markdown_path: str) -> bool:
        """
        Pandoc으로 DOCX를 Markdown으로 변환

        Args:
            docx_path: DOCX 파일 경로
            markdown_path: Markdown 출력 경로

        Returns:
            bool: 성공 여부
        """
        try:
            # Pandoc 명령어 구성
            cmd = [
                "pandoc",
                docx_path,
                "-o", markdown_path,
                "--wrap=none",  # 줄바꿈 안함
                "--markdown-headings=atx",  # # 스타일 헤딩
                "--extract-media=images",  # 이미지 추출
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Pandoc 변환 성공: {markdown_path}")
                return True
            else:
                logger.error(f"Pandoc 변환 실패: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Pandoc 실행 오류: {e}")
            return False

    def convert_with_rclone(self, document_id: str, output_path: str) -> bool:
        """
        Rclone을 사용한 변환 (설정 필요)

        Args:
            document_id: 문서 ID
            output_path: 출력 경로

        Returns:
            bool: 성공 여부
        """
        try:
            # Rclone으로 직접 Markdown 내보내기
            cmd = [
                "rclone",
                "copyto",
                f"gdrive:{{fileid={document_id}}}",
                output_path,
                "--drive-export-formats", "md"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Rclone 실행 오류: {e}")
            return False

    def post_process_markdown(self, markdown_path: str) -> str:
        """
        Markdown 후처리 (정리 및 개선)

        Args:
            markdown_path: Markdown 파일 경로

        Returns:
            str: 처리된 Markdown 내용
        """
        with open(markdown_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 일반적인 정리 작업
        import re

        # 연속된 빈 줄 제거
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Pandoc이 생성한 불필요한 이스케이프 제거
        content = content.replace('\\[', '[').replace('\\]', ']')
        content = content.replace('\\<', '<').replace('\\>', '>')
        content = content.replace('\\#', '#').replace('\\$', '$')
        content = content.replace('\\~', '~')
        content = content.replace('\\"', '"')

        # {.underline} 등 불필요한 스타일 태그 제거
        content = re.sub(r'\{\.underline\}', '', content)
        content = re.sub(r'\{\.bold\}', '', content)
        content = re.sub(r'\{\.italic\}', '', content)

        # 링크 내 줄바꿈 수정 (링크 텍스트와 URL이 분리된 경우)
        # [[text
text]] 형식 처리
        content = re.sub(r'\[\[([^\]]+)\n([^\]]+)\]\]', r'[[\1 \2]]', content)
        # [text](url) 형식에서 링크 텍스트 내 줄바꿈 처리
        content = re.sub(r'\[([^\]]*?)\n([^\]]*?)\]\(([^\)]+)\)', r'[\1 \2](\3)', content)

        # 이상한 문자 제거 (예: ## 8. 앞의 특수문자)
        content = re.sub(r'([^\n])## (\d+\.)', r'\1\n\n## \2', content)
        content = re.sub(r'^([^\#\n]+)## ', r'\n## ', content, flags=re.MULTILINE)

        # 이미지 경로 조정 (필요시)
        content = re.sub(r'!\[(.*?)\]\(images/(.*?)\)', r'![\1](./images/\2)', content)

        return content

    def process_document(
        self,
        document_id: str,
        output_dir: str = "docs"
    ) -> Dict[str, Any]:
        """
        문서 처리 전체 파이프라인

        Args:
            document_id: Google Docs 문서 ID
            output_dir: 출력 디렉토리

        Returns:
            Dict: 처리 결과
        """
        # 의존성 확인
        if not self.check_dependencies():
            return {'success': False, 'error': 'Missing dependencies'}

        # 메타데이터 가져오기
        try:
            file_metadata = self.drive_service.files().get(
                fileId=document_id,
                fields='name,modifiedTime,lastModifyingUser'
            ).execute()

            metadata = {
                'title': file_metadata.get('name', 'Untitled'),
                'modified': file_metadata.get('modifiedTime'),
                'author': file_metadata.get('lastModifyingUser', {}).get('emailAddress', 'Unknown')
            }
        except Exception as e:
            return {'success': False, 'error': f'Metadata fetch failed: {e}'}

        # 임시 디렉토리에서 작업
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            docx_path = temp_path / f"{document_id}.docx"
            temp_md_path = temp_path / f"{document_id}.md"

            # 방법별 변환
            if self.method == "pandoc":
                # DOCX 다운로드
                if not self.export_as_docx(document_id, str(docx_path)):
                    return {'success': False, 'error': 'DOCX download failed'}

                # Pandoc 변환
                if not self.convert_with_pandoc(str(docx_path), str(temp_md_path)):
                    return {'success': False, 'error': 'Pandoc conversion failed'}

            elif self.method == "rclone":
                # Rclone 직접 변환
                if not self.convert_with_rclone(document_id, str(temp_md_path)):
                    return {'success': False, 'error': 'Rclone conversion failed'}

            else:  # API 방법 (기존 코드 사용)
                # 기존 gdocs_to_markdown.py의 로직 재사용
                from gdocs_to_markdown import GoogleDocsToMarkdown
                converter = GoogleDocsToMarkdown()
                return converter.process_document(document_id, output_dir)

            # Markdown 후처리
            markdown_content = self.post_process_markdown(str(temp_md_path))

            # 문서 분석 (분류 및 태그)
            analysis = self.categorizer.analyze_document(
                title=metadata['title'],
                content=markdown_content,
                filename=metadata['title']
            )

            # Denote 파일명 생성
            filename = self.namer.generate_filename(
                title=metadata['title'],
                tags=analysis['tags'],
                date=datetime.fromisoformat(metadata['modified'].replace('Z', '+00:00'))
            )

            # 카테고리별 디렉토리에 저장
            category_dir = Path(output_dir) / analysis['category']
            category_dir.mkdir(parents=True, exist_ok=True)

            output_path = category_dir / filename

            # 메타데이터 추가
            header = f"""---
title: {metadata['title']}
author: {metadata['author']}
modified: {metadata['modified']}
category: {analysis['category']}
tags: {', '.join(analysis['tags'])}
source: https://docs.google.com/document/d/{document_id}
converter: {self.method}
---

# {metadata['title']}

"""
            full_content = header + markdown_content

            # 파일 저장
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_content)

            # 이미지 디렉토리 이동 (있으면)
            images_dir = temp_path / "images"
            if images_dir.exists():
                import shutil
                target_images = category_dir / "images"
                shutil.copytree(images_dir, target_images, dirs_exist_ok=True)

        logger.info(f"문서 처리 완료: {output_path}")

        return {
            'success': True,
            'document_id': document_id,
            'title': metadata['title'],
            'filename': filename,
            'category': analysis['category'],
            'tags': analysis['tags'],
            'output_path': str(output_path),
            'needs_review': analysis['needs_review'],
            'method': self.method
        }


def main():
    """테스트 실행"""
    import sys

    if len(sys.argv) < 2:
        print("사용법: python gdocs_to_markdown_v2.py <DOCUMENT_ID> [method]")
        print("method: pandoc (기본), rclone, api")
        sys.exit(1)

    document_id = sys.argv[1]
    method = sys.argv[2] if len(sys.argv) > 2 else "pandoc"

    # 변환기 초기화
    converter = ImprovedGoogleDocsConverter(method=method)

    # 문서 처리
    result = converter.process_document(document_id)

    if result['success']:
        print(f"✅ 변환 성공! (방법: {result['method']})")
        print(f"   제목: {result['title']}")
        print(f"   카테고리: {result['category']}")
        print(f"   태그: {', '.join(result['tags'])}")
        print(f"   파일: {result['output_path']}")
    else:
        print(f"❌ 변환 실패: {result.get('error')}")


if __name__ == "__main__":
    main()
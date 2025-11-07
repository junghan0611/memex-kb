"""
Threads API Adapter for memex-kb

Threads SNS 포스트를 가져와 Org-mode 형식으로 변환
"""

import os
import re
import requests
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from .base import BaseAdapter


logger = logging.getLogger(__name__)


class ThreadsAdapter(BaseAdapter):
    """Threads API Adapter"""

    def __init__(self, access_token: str, user_id: Optional[str] = None):
        """
        초기화

        Args:
            access_token: Threads API Access Token
            user_id: Threads User ID (없으면 자동 조회)
        """
        self.access_token = access_token
        self.base_url = "https://graph.threads.net/v1.0"
        self.user_id = user_id
        self._username = None
        
        logger.info("ThreadsAdapter 초기화 완료")

    def authenticate(self) -> str:
        """
        인증 및 사용자 ID 조회

        Returns:
            Threads User ID
        """
        if self.user_id:
            logger.info(f"기존 User ID 사용: {self.user_id}")
            return self.user_id

        try:
            logger.info("사용자 정보 조회 중...")
            data = self._make_request("/me", params={'fields': 'id,username'})
            self.user_id = data.get('id')
            self._username = data.get('username')
            
            logger.info(f"✅ 인증 성공: @{self._username} (ID: {self.user_id})")
            return self.user_id

        except Exception as e:
            logger.error(f"❌ 인증 실패: {e}")
            raise

    def list_documents(
        self, 
        limit: int = 100, 
        max_posts: Optional[int] = None,
        fields: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        전체 포스트 목록 조회 (페이지네이션 자동 처리)

        Args:
            limit: 한 번에 가져올 포스트 수 (최대 100)
            max_posts: 가져올 최대 포스트 수 (None이면 전체)
            fields: 조회할 필드 리스트

        Returns:
            포스트 목록
        """
        if not self.user_id:
            self.authenticate()

        if fields is None:
            fields = [
                'id', 'text', 'timestamp', 'media_type',
                'media_url', 'permalink',
                'children{id,media_type,media_url}'
            ]

        all_posts = []
        next_url = None
        page = 0

        try:
            while True:
                page += 1
                logger.info(f"📄 페이지 {page} 조회 중... (현재까지 {len(all_posts)}개)")

                if next_url:
                    # 페이지네이션 URL 사용
                    response = requests.get(next_url)
                    response.raise_for_status()
                    data = response.json()
                else:
                    # 첫 페이지
                    data = self._make_request(
                        f"/{self.user_id}/threads",
                        params={
                            'fields': ','.join(fields),
                            'limit': limit
                        }
                    )

                posts = data.get('data', [])
                if not posts:
                    logger.info("더 이상 포스트가 없습니다.")
                    break

                all_posts.extend(posts)
                logger.info(f"   ✅ {len(posts)}개 포스트 추가됨")

                # 최대 개수 체크
                if max_posts and len(all_posts) >= max_posts:
                    all_posts = all_posts[:max_posts]
                    logger.info(f"최대 포스트 수({max_posts})에 도달했습니다.")
                    break

                # 다음 페이지 확인
                paging = data.get('paging', {})
                next_url = paging.get('next')
                
                if not next_url:
                    logger.info("마지막 페이지입니다.")
                    break

            logger.info(f"🎉 전체 {len(all_posts)}개 포스트 조회 완료!")
            return all_posts

        except Exception as e:
            logger.error(f"❌ 포스트 목록 조회 실패: {e}")
            raise

    def fetch_document(
        self, 
        media_id: str, 
        include_replies: bool = True
    ) -> Dict:
        """
        개별 포스트 상세 정보 + 댓글 조회

        Args:
            media_id: 포스트 ID
            include_replies: 댓글 포함 여부

        Returns:
            포스트 데이터 (댓글 포함)
        """
        try:
            # 포스트 상세 정보
            post = self._make_request(
                f"/{media_id}",
                params={
                    'fields': 'id,text,timestamp,media_type,media_url,permalink,username'
                }
            )

            # 댓글 조회
            if include_replies:
                try:
                    replies_data = self._make_request(
                        f"/{media_id}/replies",
                        params={'fields': 'id,text,username,timestamp'}
                    )
                    post['replies'] = replies_data.get('data', [])
                except Exception as e:
                    logger.warning(f"댓글 조회 실패 (media_id: {media_id}): {e}")
                    post['replies'] = []
            else:
                post['replies'] = []

            return post

        except Exception as e:
            logger.error(f"❌ 포스트 조회 실패 (media_id: {media_id}): {e}")
            raise

    def convert_to_format(
        self, 
        content: Dict, 
        output_format: str = 'org'
    ) -> str:
        """
        포스트를 Org-mode 형식으로 변환

        Args:
            content: 포스트 데이터
            output_format: 출력 형식 (현재 'org'만 지원)

        Returns:
            Org-mode 형식 문자열
        """
        if output_format == 'org':
            return self._convert_to_org(content)
        elif output_format == 'markdown':
            return self._convert_to_markdown(content)
        else:
            raise ValueError(f"지원하지 않는 형식: {output_format}")

    def _convert_to_org(self, post: Dict, level: int = 2) -> str:
        """
        포스트를 Org-mode 항목으로 변환

        Args:
            post: 포스트 데이터
            level: 헤딩 레벨 (기본: 2)

        Returns:
            Org-mode 형식 문자열
        """
        # 타임스탬프 변환
        timestamp_iso = post.get('timestamp', '')
        try:
            dt = datetime.fromisoformat(timestamp_iso.replace('Z', '+00:00'))
            org_timestamp = dt.strftime('[%Y-%m-%d %a %H:%M]')
            heading_date = dt.strftime('%Y-%m-%d %a')
        except:
            org_timestamp = timestamp_iso
            heading_date = timestamp_iso

        # 텍스트 처리
        text = post.get('text', '(내용 없음)')

        # 첫 줄을 헤딩 제목으로 사용 (50자 제한)
        lines = text.strip().split('\n')
        title = lines[0][:50] + '...' if len(lines[0]) > 50 else lines[0]

        # 본문
        body = text.strip()

        # Permalink
        permalink = post.get('permalink', '')

        # 메타데이터
        metadata = f"""
- 작성일: {org_timestamp}
- 링크: [[{permalink}][Threads에서 보기]]
"""

        # 헤딩 문자열
        heading = '*' * level

        # Org 항목 기본 구조
        org_entry = f"""{heading} {title}
:PROPERTIES:
:POST_ID: {post.get('id', '')}
:TIMESTAMP: {timestamp_iso}
:PERMALINK: {permalink}
:MEDIA_TYPE: {post.get('media_type', 'TEXT')}
:END:

{body}
{metadata}
"""

        return org_entry

    def _convert_to_markdown(self, post: Dict) -> str:
        """
        포스트를 Markdown 형식으로 변환 (미구현)

        Args:
            post: 포스트 데이터

        Returns:
            Markdown 형식 문자열
        """
        # TODO: Markdown 변환 구현
        raise NotImplementedError("Markdown 변환은 아직 구현되지 않았습니다.")

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """
        API 요청 헬퍼

        Args:
            endpoint: API 엔드포인트
            params: 쿼리 파라미터

        Returns:
            응답 JSON 데이터
        """
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params['access_token'] = self.access_token

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error: {e}")
            raise

    def download_attachment(self, attachment_url: str, output_path: str) -> bool:
        """
        이미지 다운로드

        Args:
            attachment_url: 이미지 URL
            output_path: 저장 경로

        Returns:
            성공 여부
        """
        try:
            logger.info(f"이미지 다운로드 중: {attachment_url}")

            # 디렉토리 생성
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)

            response = requests.get(attachment_url, timeout=30)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"✅ 저장 완료: {output_path}")
            return True

        except Exception as e:
            logger.error(f"❌ 이미지 다운로드 실패: {e}")
            return False

    def download_all_images(self, post: Dict, output_dir: str) -> List[str]:
        """
        포스트의 모든 이미지 다운로드

        Args:
            post: 포스트 데이터
            output_dir: 저장 디렉토리

        Returns:
            다운로드된 이미지 경로 리스트
        """
        downloaded = []
        post_id = post.get('id', 'unknown')
        media_type = post.get('media_type')

        if media_type == 'CAROUSEL_ALBUM':
            # 캐러셀: children 배열의 모든 이미지 다운로드
            children = post.get('children', {}).get('data', [])
            for i, child in enumerate(children, 1):
                url = child.get('media_url')
                if url:
                    filename = f"{post_id}_{i:02d}.jpg"
                    path = os.path.join(output_dir, filename)
                    if self.download_attachment(url, path):
                        downloaded.append(path)

        elif media_type == 'IMAGE':
            # 단일 이미지
            url = post.get('media_url')
            if url:
                filename = f"{post_id}.jpg"
                path = os.path.join(output_dir, filename)
                if self.download_attachment(url, path):
                    downloaded.append(path)

        # TEXT_POST, VIDEO는 이미지 없음
        return downloaded

"""
Base Adapter for memex-kb Backend Integration

모든 Backend Adapter는 이 추상 클래스를 상속해야 합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class BaseAdapter(ABC):
    """Backend Adapter 추상 클래스"""

    @abstractmethod
    def authenticate(self) -> Any:
        """
        인증 수행

        Returns:
            인증 정보 (예: user_id, credentials 등)
        """
        pass

    @abstractmethod
    def list_documents(self, **kwargs) -> List[Dict]:
        """
        문서 목록 조회

        Args:
            **kwargs: Backend별 파라미터

        Returns:
            문서 목록 (각 문서는 딕셔너리)
        """
        pass

    @abstractmethod
    def fetch_document(self, doc_id: str, **kwargs) -> Dict:
        """
        개별 문서 내용 가져오기

        Args:
            doc_id: 문서 ID
            **kwargs: Backend별 추가 파라미터

        Returns:
            문서 데이터 (딕셔너리)
        """
        pass

    @abstractmethod
    def convert_to_format(self, content: Dict, output_format: str = 'markdown') -> str:
        """
        문서를 지정된 형식으로 변환

        Args:
            content: 원본 문서 데이터
            output_format: 출력 형식 ('markdown', 'org', 등)

        Returns:
            변환된 문서 내용 (문자열)
        """
        pass

    def get_metadata(self, doc_id: str) -> Dict:
        """
        문서 메타데이터 조회 (선택)

        Args:
            doc_id: 문서 ID

        Returns:
            메타데이터 딕셔너리
        """
        return {}

    def download_attachment(self, attachment_url: str, output_path: str) -> bool:
        """
        첨부파일 다운로드 (선택)

        Args:
            attachment_url: 첨부파일 URL
            output_path: 저장 경로

        Returns:
            성공 여부
        """
        return False

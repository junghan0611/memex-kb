#!/usr/bin/env python3
"""
Denote 스타일 파일명 생성기
형식: timestamp--한글-제목__태그1_태그2.md
예시: 20250913t150000--api-설계-가이드__backend_api_guide.md
"""

import re
from datetime import datetime
from typing import List, Optional
from slugify import slugify


class DenoteNamer:
    """Denote 스타일 파일명 생성 클래스"""

    def __init__(self):
        """초기화"""
        self.korean_pattern = re.compile(r'[가-힣]+')
        self.english_pattern = re.compile(r'[a-zA-Z]+')

    def generate_timestamp(self, date: Optional[datetime] = None) -> str:
        """
        Denote 스타일 타임스탬프 생성

        Args:
            date: 날짜 객체 (없으면 현재 시간)

        Returns:
            str: YYYYMMDDTHHMMSS 형식의 타임스탬프
        """
        if date is None:
            date = datetime.now()
        return date.strftime("%Y%m%dt%H%M%S")

    def slugify_korean(self, text: str) -> str:
        """
        한글 제목을 슬러그화

        Args:
            text: 원본 제목

        Returns:
            str: 슬러그화된 제목
        """
        # 특수문자 제거, 공백을 하이픈으로
        text = re.sub(r'[^\w\s가-힣-]', '', text)
        text = re.sub(r'\s+', '-', text.strip())

        # 연속된 하이픈 제거
        text = re.sub(r'-+', '-', text)

        # 소문자 변환 (영문만)
        result = []
        for word in text.split('-'):
            if self.english_pattern.match(word):
                result.append(word.lower())
            else:
                result.append(word)

        return '-'.join(result)

    def normalize_tags(self, tags: List[str]) -> List[str]:
        """
        태그 정규화

        Args:
            tags: 원본 태그 리스트

        Returns:
            List[str]: 정규화된 태그 리스트
        """
        normalized = []

        for tag in tags:
            # 소문자 변환
            tag = tag.lower()

            # 특수문자 제거
            tag = re.sub(r'[^\w가-힣]', '', tag)

            # 한글 태그는 영문으로 변환 시도
            if self.korean_pattern.match(tag):
                # 간단한 매핑 (확장 가능)
                mapping = {
                    '백엔드': 'backend',
                    '프론트엔드': 'frontend',
                    '데이터베이스': 'database',
                    '개발': 'dev',
                    '운영': 'ops',
                    '설계': 'design',
                    'API': 'api',
                    '가이드': 'guide',
                    '문서': 'doc',
                }
                tag = mapping.get(tag, slugify(tag))

            if tag:  # 빈 문자열이 아니면 추가
                normalized.append(tag)

        # 중복 제거하고 정렬
        return sorted(list(set(normalized)))

    def generate_filename(
        self,
        title: str,
        tags: Optional[List[str]] = None,
        date: Optional[datetime] = None,
        extension: str = 'md'
    ) -> str:
        """
        Denote 스타일 파일명 생성

        Args:
            title: 문서 제목
            tags: 태그 리스트
            date: 날짜 객체
            extension: 파일 확장자

        Returns:
            str: Denote 스타일 파일명
        """
        # 타임스탬프 생성
        timestamp = self.generate_timestamp(date)

        # 제목 슬러그화
        slug_title = self.slugify_korean(title)

        # 태그 처리
        if tags:
            normalized_tags = self.normalize_tags(tags)
            tag_string = '_'.join(normalized_tags)
            filename = f"{timestamp}--{slug_title}__{tag_string}.{extension}"
        else:
            filename = f"{timestamp}--{slug_title}.{extension}"

        return filename

    def parse_filename(self, filename: str) -> dict:
        """
        Denote 파일명 파싱

        Args:
            filename: Denote 스타일 파일명

        Returns:
            dict: 파싱된 정보 (timestamp, title, tags)
        """
        # 파일명 패턴: timestamp--title__tags.extension
        pattern = r'^(\d{8}t\d{6})--(.+?)(?:__(.+?))?\.(\w+)$'
        match = re.match(pattern, filename)

        if not match:
            return None

        timestamp_str, title, tags_str, extension = match.groups()

        # 타임스탬프 파싱
        timestamp = datetime.strptime(timestamp_str, "%Y%m%dt%H%M%S")

        # 태그 파싱
        tags = tags_str.split('_') if tags_str else []

        return {
            'timestamp': timestamp,
            'title': title,
            'tags': tags,
            'extension': extension
        }


def main():
    """테스트 및 예시"""
    namer = DenoteNamer()

    # 테스트 케이스
    test_cases = [
        {
            'title': 'API 설계 가이드',
            'tags': ['백엔드', 'api', '가이드'],
        },
        {
            'title': '시스템 아키텍처 설계 문서',
            'tags': ['architecture', 'design', 'system'],
        },
        {
            'title': '투야 IoT 플랫폼 연동 가이드',
            'tags': ['tuya', 'iot', 'integration'],
        },
        {
            'title': '장애 대응 매뉴얼',
            'tags': ['운영', 'troubleshooting'],
        },
    ]

    print("Denote 파일명 생성 예시:\n")
    for test in test_cases:
        filename = namer.generate_filename(
            title=test['title'],
            tags=test['tags']
        )
        print(f"제목: {test['title']}")
        print(f"태그: {test['tags']}")
        print(f"결과: {filename}")
        print()

        # 파싱 테스트
        parsed = namer.parse_filename(filename)
        if parsed:
            print(f"파싱 결과: {parsed}")
            print("-" * 50)


if __name__ == "__main__":
    main()
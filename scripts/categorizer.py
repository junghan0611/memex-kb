#!/usr/bin/env python3
"""
문서 자동 분류기
규칙 기반 분류로 토큰 절약, LLM 사용 최소화
"""

import re
import yaml
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentCategorizer:
    """문서 자동 분류 클래스"""

    def __init__(self, config_path: str = "config/categories.yaml"):
        """
        초기화

        Args:
            config_path: 분류 규칙 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.categories = self.config.get('categories', {})
        self.classification = self.config.get('classification', {})
        self.weights = self.classification.get('weights', {})

    def _load_config(self, config_path: str) -> dict:
        """
        설정 파일 로드

        Args:
            config_path: 설정 파일 경로

        Returns:
            dict: 설정 내용
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"설정 파일을 찾을 수 없습니다: {config_path}")
            return {}

    def calculate_score(
        self,
        category_config: dict,
        title: str,
        content: str,
        filename: str = ""
    ) -> int:
        """
        카테고리 매칭 점수 계산

        Args:
            category_config: 카테고리 설정
            title: 문서 제목
            content: 문서 내용
            filename: 파일명

        Returns:
            int: 매칭 점수 (0-100)
        """
        score = 0

        # 제목 키워드 매칭
        keywords = category_config.get('keywords', [])
        for keyword in keywords:
            if keyword.lower() in title.lower():
                score += self.weights.get('title_keyword', 10)

        # 제목 패턴 매칭
        patterns = category_config.get('patterns', [])
        for pattern in patterns:
            try:
                if re.search(pattern, title, re.IGNORECASE):
                    score += self.weights.get('title_pattern', 15)
                    break  # 첫 번째 매칭만 점수 부여
            except re.error:
                logger.warning(f"잘못된 정규식 패턴: {pattern}")

        # 본문 키워드 매칭 (첫 500자만 검사하여 성능 최적화)
        content_preview = content[:500] if content else ""
        for keyword in keywords:
            if keyword.lower() in content_preview.lower():
                score += self.weights.get('content_keyword', 5)

        # 파일명 힌트 매칭
        file_hints = category_config.get('file_hints', [])
        filename_lower = filename.lower()
        for hint in file_hints:
            if hint.lower() in filename_lower:
                score += self.weights.get('file_hint', 20)
                break

        return min(score, 100)  # 최대 100점

    def categorize(
        self,
        title: str,
        content: str = "",
        filename: str = ""
    ) -> Tuple[str, int, Dict[str, int]]:
        """
        문서 분류

        Args:
            title: 문서 제목
            content: 문서 내용
            filename: 파일명

        Returns:
            Tuple[str, int, Dict[str, int]]:
                - 선택된 카테고리
                - 최고 점수
                - 모든 카테고리별 점수
        """
        scores = {}

        # 각 카테고리별 점수 계산
        for category_key, category_config in self.categories.items():
            score = self.calculate_score(
                category_config,
                title,
                content,
                filename
            )
            scores[category_key] = score

        # 최고 점수 카테고리 선택
        if scores:
            best_category = max(scores, key=scores.get)
            best_score = scores[best_category]

            # 최소 점수 체크
            min_score = self.classification.get('min_score', 30)
            if best_score < min_score:
                uncategorized = self.classification.get('uncategorized', {})
                return uncategorized.get('folder', '_uncategorized'), best_score, scores

            return best_category, best_score, scores
        else:
            uncategorized = self.classification.get('uncategorized', {})
            return uncategorized.get('folder', '_uncategorized'), 0, scores

    def extract_tags(self, title: str, content: str = "") -> List[str]:
        """
        문서에서 태그 자동 추출

        Args:
            title: 문서 제목
            content: 문서 내용

        Returns:
            List[str]: 추출된 태그 리스트
        """
        tags = []
        tag_config = self.config.get('tags', {})
        auto_extract = tag_config.get('auto_extract', [])
        normalize_map = tag_config.get('normalize', {})

        # 제목과 내용에서 태그 추출
        text = f"{title} {content[:1000]}".lower()  # 첫 1000자만 검사

        for tag in auto_extract:
            if tag.lower() in text:
                # 정규화 적용
                normalized = normalize_map.get(tag.lower(), tag.lower())
                tags.append(normalized)

        # 중복 제거
        return list(set(tags))

    def get_category_info(self, category_key: str) -> dict:
        """
        카테고리 정보 조회

        Args:
            category_key: 카테고리 키

        Returns:
            dict: 카테고리 정보
        """
        return self.categories.get(category_key, {})

    def analyze_document(
        self,
        title: str,
        content: str = "",
        filename: str = ""
    ) -> dict:
        """
        문서 종합 분석

        Args:
            title: 문서 제목
            content: 문서 내용
            filename: 파일명

        Returns:
            dict: 분석 결과
        """
        # 카테고리 분류
        category, score, all_scores = self.categorize(title, content, filename)

        # 태그 추출
        tags = self.extract_tags(title, content)

        # 카테고리 정보
        category_info = self.get_category_info(category)

        return {
            'category': category,
            'category_name': category_info.get('name', category),
            'score': score,
            'all_scores': all_scores,
            'tags': tags,
            'needs_review': score < self.classification.get('min_score', 30)
        }


def main():
    """테스트 및 예시"""
    # 분류기 초기화
    categorizer = DocumentCategorizer()

    # 테스트 문서들
    test_documents = [
        {
            'title': 'API 설계 가이드',
            'content': '이 문서는 RESTful API 설계에 대한 가이드입니다. 백엔드 개발자를 위한...',
            'filename': 'api_design_guide.md'
        },
        {
            'title': '시스템 아키텍처 설계서',
            'content': '마이크로서비스 아키텍처 기반의 시스템 설계 문서입니다.',
            'filename': 'system_architecture.md'
        },
        {
            'title': '서버 장애 대응 매뉴얼',
            'content': '서버 장애 발생 시 대응 절차와 트러블슈팅 가이드',
            'filename': 'troubleshooting.md'
        },
        {
            'title': '[투야] IoT 플랫폼 연동 가이드',
            'content': '투야 클라우드 API를 사용한 IoT 디바이스 연동 방법',
            'filename': 'tuya_integration.md'
        },
        {
            'title': '회의록 2025-09-13',
            'content': '오늘 회의에서 논의된 내용은...',
            'filename': 'meeting_notes.md'
        }
    ]

    print("문서 분류 테스트\n")
    print("=" * 60)

    for doc in test_documents:
        print(f"\n제목: {doc['title']}")
        print(f"파일명: {doc['filename']}")

        # 문서 분석
        result = categorizer.analyze_document(
            title=doc['title'],
            content=doc['content'],
            filename=doc['filename']
        )

        print(f"분류: {result['category']} ({result['category_name']})")
        print(f"점수: {result['score']}")
        print(f"태그: {', '.join(result['tags']) if result['tags'] else '없음'}")
        print(f"검토 필요: {'예' if result['needs_review'] else '아니오'}")

        # 상세 점수
        print(f"카테고리별 점수:")
        for cat, score in result['all_scores'].items():
            print(f"  - {cat}: {score}")

        print("-" * 60)


if __name__ == "__main__":
    main()
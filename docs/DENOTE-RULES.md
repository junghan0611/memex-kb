# Denote 규칙 가이드

Memex-KB의 핵심: **일관된 파일명 규칙**과 **규칙 기반 자동 분류**

이 문서는 한글 중심의 지식 관리를 위한 Denote 규칙을 설명합니다.

---

## Denote 파일명 규칙

### 형식

```
timestamp--한글-제목__태그1_태그2.md
```

- **timestamp**: `YYYYMMDDTHHMMSS` (대문자 T 필수!)
- **한글-제목**: 한글로 의미 명확하게 (하이픈으로 구분)
- **태그들**: 영어 소문자 (언더스코어로 구분)

### 예시

```bash
# 입력
title: "API 설계 가이드"
tags: ["백엔드", "api", "가이드"]

# 출력
20250913T150000--api-설계-가이드__backend_api_guide.md
```

### 장점

| 특성 | 설명 |
|------|------|
| **시간 기반 정렬** | 파일 탐색기에서 자동 정렬 |
| **인간 친화적** | 한글 제목 유지 (검색 쉬움) |
| **명확한 태그** | 언더스코어로 구분, 프로그래밍으로 파싱 가능 |
| **파싱 가능** | 메타데이터 자동 추출 |

### 구현

파일: `scripts/denote_namer.py`

```python
from denote_namer import DenoteNamer

namer = DenoteNamer()
filename = namer.generate_filename(
    title="문서 제목",
    tags=["tag1", "tag2"]
)
# → 20250913T150000--문서-제목__tag1_tag2.md
```

---

## 분류 규칙 (categories.yaml)

LLM 없이 토큰 비용 0원으로 자동 분류

### 설정 예시

파일: `config/categories.yaml`

```yaml
categories:
  architecture:
    name: "시스템 설계"
    keywords: ["설계", "아키텍처", "구조"]
    patterns: ["^시스템.*설계"]
    file_hints: ["architecture", "design"]

  development:
    name: "개발 가이드"
    keywords: ["개발", "API", "코드"]
    patterns: [".*가이드$"]
    file_hints: ["dev", "api"]

  operations:
    name: "운영 문서"
    keywords: ["운영", "배포", "모니터링"]
    patterns: [".*운영.*"]
    file_hints: ["ops", "deploy"]

  products:
    name: "제품별 문서"
    keywords: ["제품", "서비스", "기능"]
    file_hints: ["product", "service"]

classification:
  min_score: 30  # 최소 매칭 점수
  weights:
    title_keyword: 10    # 제목에 키워드 있을 때
    title_pattern: 15    # 제목이 패턴에 매칭될 때
    content_keyword: 5   # 본문에 키워드 있을 때
    file_hint: 20        # 파일명에 힌트 있을 때
```

### 분류 로직

1. **키워드 매칭**: 제목/본문에서 키워드 검색
2. **패턴 매칭**: 정규식으로 제목 패턴 확인
3. **파일 힌트**: 파일명에서 힌트 추출
4. **점수 계산**: 가중치 합산
5. **최고 점수 선택**: 가장 높은 점수의 카테고리로 분류

### 구현

파일: `scripts/categorizer.py`

```python
from categorizer import DocumentCategorizer

categorizer = DocumentCategorizer()
category, score, all_scores = categorizer.categorize(
    title="API 설계 가이드",
    content="이 문서는 REST API 설계 원칙을 설명합니다..."
)
# → category: "development", score: 45
```

### 왜 LLM을 쓰지 않는가?

| LLM 기반 분류 | 규칙 기반 분류 |
|--------------|---------------|
| 토큰 비용 발생 | **비용 0원** |
| 결과 비결정적 | **재현 가능** |
| API 의존성 | **오프라인 동작** |
| 블랙박스 | **투명한 YAML 설정** |

---

## 출력 디렉토리 구조

```
docs/
├── architecture/      # 시스템 설계
├── development/       # 개발 가이드
├── operations/        # 운영 문서
├── products/          # 제품별 문서
└── _uncategorized/    # 미분류 (수동 검토 필요)
```

### 미분류 처리

`min_score` (기본 30) 이하면 `_uncategorized/`에 저장

→ 수동 검토 후 적절한 카테고리로 이동하거나, `categories.yaml`에 규칙 추가

---

## 한글 중심 설계 철학

### 왜 한글 제목인가?

1. **검색 용이성**: 파일 탐색기에서 바로 내용 파악
2. **문맥 보존**: 영어 번역 시 뉘앙스 손실 방지
3. **Org-mode 호환**: Emacs Denote와 완벽 호환

### 왜 영어 태그인가?

1. **파싱 안정성**: 한글 태그는 정규식 처리 복잡
2. **검색 통합**: 기존 도구들과 호환
3. **국제화 대비**: 영어 태그로 글로벌 검색 가능

### 예시

```
# 좋은 예
20250913T150000--api-설계-가이드__backend_api_guide.md

# 피해야 할 예
20250913T150000--api-design-guide__백엔드_api_가이드.md
```

---

## 팁: Emacs Denote 연동

Emacs Denote 패키지와 완벽 호환됩니다.

```elisp
;; Denote 설정 예시
(setq denote-directory "~/memex-kb/docs")
(setq denote-file-type 'markdown-yaml)
```

변환된 문서를 Emacs에서 바로 편집하고, Denote의 링크/백링크 기능 활용 가능

---

← [README.md](../README.md)로 돌아가기

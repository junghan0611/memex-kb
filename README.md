# 🧠 Memex-KB: Universal Knowledge Base Converter

> "당신의 지식을 당신의 방식으로" - Denote 기반 범용 지식베이스 변환 시스템

## 📖 철학 (Philosophy)

**Memex-KB는 지식 관리의 시작점이자, RAG 파이프라인의 입구입니다.**

입문자에게 "일정한 규칙"을 제공하여, 산재된 지식을 체계적으로 정리하고, **AI 협업 가능한 형태로 변환**합니다.

### 왜 memex-kb인가?

**기술 배경**:
```
✅ 검증된 기술 스택 (2025 Q3):
- n8n: 40+ 노드 워크플로우 (AI Agent Automation)
- Supabase pgvector: 벡터 DB (2,945개 Org 파일 임베딩 완료)
- Ollama: 로컬 임베딩 (multilingual-e5-large, GPU 클러스터)
- Airbyte: ETL 파이프라인 (Channel.io → PostgreSQL 등)
- Rerank API Server: 자체 구축

→ 기술 스택 자체는 "껍데기". 이미 다 해봤습니다.
```

**핵심 문제**:
```
그런데 Legacy 문서(Google Docs, Dooray, Confluence...)를
어떻게 RAG-ready 형태로 변환하는가?

변환만 하는 도구는 많습니다.
Pandoc, Notion Exporter, Confluence API...

하지만:
- 일관성 없는 파일명 → 검색 어려움
- 분류 기준 모호 → 찾기 어려움
- 메타데이터 손실 → 컨텍스트 부족
- Git 미연동 → 버전 관리 불가

→ 임베딩해도 품질이 낮습니다.
```

**memex-kb의 독창적 접근**:
```
1. Denote 파일명 규칙:
   timestamp--한글-제목__태그들.md
   → 파싱 가능, 시간 정렬, 의미 명확

2. 규칙 기반 자동 분류:
   YAML 설정으로 일관성 확보
   → LLM 비용 0원, 재현 가능

3. Git 버전 관리:
   모든 변환 과정 추적
   → 투명성, 롤백 가능

4. Backend 중립:
   Adapter 패턴으로 확장
   → 도구 바뀌어도 데이터는 유지

5. 임베딩 파이프라인 통합 (v2.0):
   변환 → Denote → Embedding → Vector DB → RAG
   → 검증된 파이프라인 재사용
```

**결과**:
```
단순 변환 도구 (감흥 없음)
    ↓
RAG 파이프라인의 입구 (가치 있음)
    ↓
Legacy 문서가 AI Second Brain이 됩니다.
```

### 핵심 원칙

1. **Denote 파일명 규칙**: `timestamp--한글-제목__태그1_태그2.md`
   - 시간 기반 정렬 (검색 불필요)
   - 인간 친화적 제목 (한글 지원)
   - 명확한 태그 (자동 추출)

2. **규칙 기반 자동 분류**: LLM 없이 토큰 절약
   - YAML 설정 파일로 간단 관리
   - 키워드 + 패턴 매칭
   - 확장 가능한 카테고리

3. **Git 버전 관리**: 모든 변경사항 추적
   - 로컬 우선 (보안)
   - 협업 가능 (GitHub/GitLab)
   - 영구 보존

4. **Backend 중립**: 여러 소스 지원
   - Google Docs (✅ 구현됨)
   - Threads SNS (✅ 구현됨) - **NEW!**
   - Dooray Wiki (🔧 개발 중)
   - Confluence (📋 계획 중)

---

## 🎯 누구를 위한 도구인가?

### 이런 분들에게 추천합니다

- ✅ **지식 관리 입문자**: "어디서부터 시작해야 할지 모르겠어요"
- ✅ **회사 Wiki 관리자**: "산재된 문서를 정리하고 싶어요"
- ✅ **보안 중시 사용자**: "회사 데이터를 로컬에 보관하고 싶어요"
- ✅ **Org-mode 사용자**: "회사 문서를 Emacs로 관리하고 싶어요"
- ✅ **자동화 선호자**: "수작업은 줄이고 규칙으로 관리하고 싶어요"

### 이런 니즈를 해결합니다

| 문제 | Memex-KB 해결책 |
|------|----------------|
| 문서가 여기저기 흩어져 있어요 | 한 곳에 Markdown으로 통합 |
| 파일명이 일관성 없어요 | Denote 규칙으로 자동 생성 |
| 분류 기준이 모호해요 | YAML로 명확한 규칙 정의 |
| 버전 관리가 안 돼요 | Git으로 모든 변경사항 추적 |
| 회사 도구가 계속 바뀌어요 | Backend만 교체, 데이터는 그대로 |

---

## 🏗️ 시스템 아키텍처

```
[Backend Sources]
    ├── Google Docs    (✅ 구현됨)
    ├── Threads SNS    (✅ 구현됨) ← NEW!
    ├── Dooray Wiki    (🔧 개발 중)
    └── Confluence     (📋 계획 중)
         ↓
[Backend Adapter] ← 확장 가능한 설계
         ↓
[Markdown/Org Conversion]
         ↓
[공통 파이프라인]
    ├── DenoteNamer      (파일명 생성)
    ├── Categorizer      (자동 분류)
    └── Tag Extractor    (태그 추출)
         ↓
[Local Git Repository]
    ├── docs/
    │   ├── architecture/
    │   ├── development/
    │   ├── operations/
    │   ├── products/
    │   └── _uncategorized/
    └── .git/
         ↓
[개인 지식베이스]
    ├── Org-mode
    ├── Obsidian
    └── 기타 Markdown 도구
```

---

## 📁 프로젝트 구조

```
memex-kb/
├── flake.nix                    # Nix Flake (의존성 관리) ✅
├── flake.lock                   # 잠금 파일 (재현성)
├── .envrc                       # direnv 설정
├── scripts/                     # 변환 및 동기화 스크립트
│   ├── adapters/                # Backend Adapters (확장 가능)
│   │   ├── base.py              # BaseAdapter (추상 클래스)
│   │   └── threads.py           # Threads API Adapter ✅
│   ├── gdocs_to_markdown.py     # Google Docs 변환 ✅
│   ├── threads_exporter.py      # Threads 포스트 내보내기 ✅
│   ├── refresh_threads_token.py # Threads OAuth 토큰 갱신 ✅
│   ├── denote_namer.py          # Denote 파일명 생성 (공통)
│   └── categorizer.py           # 문서 자동 분류 (공통)
├── docs/                        # 변환된 문서
│   ├── threads-aphorisms.org    # Threads 아포리즘 통합 파일 ✅
│   ├── images/threads/          # Threads 이미지 (gitignored)
│   └── 2025*.org                # 프로젝트 문서들
├── config/
│   ├── .env                     # 환경변수 (gitignore)
│   ├── .env.example             # 설정 예시
│   └── credentials.json         # API 인증 (gitignore)
├── logs/                        # 실행 로그
└── README.md                    # 이 파일
```

---

## 🚀 Quick Start

### 1. 환경 설정

**이 프로젝트는 Nix Flake (`flake.nix`)를 사용합니다 - 수동 설치 불필요!**

```bash
# ✅ Nix Flake 환경 진입 (권장)
nix develop

# ✅ 또는 direnv 사용 (자동 환경 로드)
direnv allow
# → cd 시 자동으로 환경 활성화

# 확인 메시지:
# 🚀 memex-kb 개발 환경 (flake)
# ================================
# Python: Python 3.12.x
# Pandoc: pandoc 3.x
# Gitleaks: 8.x
```

**포함된 패키지** (`flake.nix`):
- Python 3.12 + 모든 필요 패키지
- Pandoc (문서 변환)
- Git, jq, rclone
- gitleaks (비밀 탐지)

### 2A. Google Docs 연동

```bash
# 1. Google Cloud Console에서 프로젝트 생성
# 2. Google Drive API 활성화
# 3. Service Account 생성 및 키 다운로드
# 4. credentials.json을 config/ 디렉토리에 저장

# 환경변수 설정
cp config/.env.example config/.env
# config/.env 파일 편집

# 단일 문서 변환
nix develop --command python scripts/gdocs_to_markdown.py "DOCUMENT_ID"
```

### 2B. Threads SNS 연동 (NEW! 🎉)

**아포리즘을 디지털가든으로**: Threads 포스트를 단일 Org 파일로 통합

#### 환경 설정

```bash
# 환경변수 설정
cp config/.env.threads.example config/.env.threads
# config/.env.threads 파일 편집 (APP_ID, APP_SECRET, REDIRECT_URI)
```

#### 사용법

```bash
# Step 1: Access Token 획득 (Graph API Explorer 사용)
# https://developers.facebook.com/tools/explorer/
# → API를 "threads.net"으로 변경 (중요!)
# → Generate Access Token

# Step 2: 장기 토큰(60일)으로 교환
nix develop --command python scripts/refresh_threads_token.py --exchange "단기토큰"

# Step 3: 토큰 테스트
nix develop --command python scripts/refresh_threads_token.py --test

# Step 4: 전체 포스트 내보내기
nix develop --command python scripts/threads_exporter.py --download-images

# 결과: docs/threads-aphorisms.org 생성
# - 포스트 (시간순 정렬)
# - 댓글 포함
# - 이미지 다운로드 (docs/images/threads/)
# - Permalink 연결
# - "어쏠리즘(Assholism)": 추천 알고리즘을 넘어선 진정한 연결
```

#### Org 구조

```org
* 서론 :META:
  (프로필 정보 및 통계)

* 주제: (미분류)
  :PROPERTIES:
  :POST_COUNT: 160
  :END:

** [포스트 제목 (첫 줄 50자)]
   :PROPERTIES:
   :POST_ID: 18101712844662284
   :TIMESTAMP: 2025-11-06T22:34:08+0000
   :PERMALINK: https://www.threads.com/@junghanacs/post/...
   :MEDIA_TYPE: IMAGE
   :END:

   [포스트 본문]

*** 이미지
    - [[file:docs/attachments/threads/18101712844662284.jpg]]

*** 댓글
**** @username ([2025-11-06 Thu 22:34])
     [댓글 내용]
```

**옵션**:
```bash
# 테스트로 5개만 내보내기
nix develop --command python scripts/threads_exporter.py --max-posts 5 --download-images

# 오래된 순으로 정렬
nix develop --command python scripts/threads_exporter.py --reverse --download-images
```

**상세 문서**: [docs/20251107T123200--threads-aphorism-exporter-프로젝트__threads_aphorism_assholism.org](docs/20251107T123200--threads-aphorism-exporter-프로젝트__threads_aphorism_assholism.org)

### 2C. Confluence 연동 (NEW! 🎉)

**Legacy 문서를 RAG-ready 형태로**: Confluence Export를 완벽한 Markdown으로 변환

> **💡 왜 이것이 memex-kb의 핵심인가?**
>
> 변환 도구는 많습니다. Pandoc, Notion Exporter, Confluence API...
> 하지만 **문자 인코딩 하나**를 제대로 처리하지 못하면 모든 것이 무너집니다.
>
> - 한글이 깨지면? → 검색 불가능
> - NFD/NFC 혼재? → 파일 손상, 편집 불가능
> - Quoted-printable 오류? → 데이터 유실
>
> **memex-kb는 "변환"이 아닌 "완벽한 변환"을 추구합니다.**
> 이것이 단순 도구와 RAG 파이프라인 입구의 차이입니다.
>
> 🎯 **철학**:
> - 첫 번째 변환에서 완벽하게 처리
> - 인코딩 문제로 인한 데이터 손실 Zero
> - RAG 임베딩 품질을 첫 단계에서 확보

#### 문제 상황

Confluence에서 Export한 `.doc` 파일을 pandoc으로 변환 시:
- 한글이 유니코드 escape 형식(=EC=97=B0...)과 섞여서 표시
- Fenced div (`:::`) 및 불필요한 HTML 속성 남음
- 코드 블록이 복잡한 형식으로 변환됨

#### 해결책

**완벽한 MIME 파싱 + Pandoc + 후처리** 파이프라인:

1. Python `email` 모듈로 MIME 메시지 파싱
2. HTML 파트를 UTF-8로 추출
3. Pandoc으로 깨끗한 Markdown 변환
4. Fenced div 제거 및 코드 블록 정리
5. Unicode NFD → NFC 정규화 (한글 완벽 보존)

#### 사용법

```bash
# 단일 파일 변환
nix develop --command python scripts/confluence_to_markdown.py document.doc

# 출력 파일명 지정
nix develop --command python scripts/confluence_to_markdown.py document.doc output.md

# 일괄 변환 (디렉토리)
nix develop --command python scripts/confluence_to_markdown.py --batch input_dir/ output_dir/

# 자세한 로그
nix develop --command python scripts/confluence_to_markdown.py -v document.doc
```

#### 변환 결과

**Before (Raw Confluence Export)**:
```markdown
# IoT Core Device =EC=97=B0=EB=8F=99=EA=B7=9C=EA=B2=A9=EC=84=9C v1.13
::::::::::::::::::: Section1
::: table-wrap
```

**After (Clean Markdown)**:
```markdown
# IoT Core Device 연동규격서 v1.13

| **버전** | **작성일** | **변경 내용** |
|----------|------------|---------------|
| v1.0     | 2025. 1. 21. | - 초안 작성 |
```

#### 기술 세부사항

- **MIME 파싱**: `email.message_from_binary_file()` 사용
- **Quoted-Printable 디코딩**: Soft line break 자동 처리
- **UTF-8 정규화**: `unicodedata.normalize('NFC')` 적용
- **Pandoc 옵션**: `--wrap=none` (라인 래핑 방지)
- **성능**: 1.1MB 문서 → 178KB (2초 이내)

#### 🔥 왜 이것이 혁명적인가?

> **"Confluence는 쥐약이다"** - AI 에이전트 협업의 관점에서
>
> Confluence는 인간 협업엔 훌륭하지만, **AI 에이전트 협업엔 최악**입니다:
> - 비표준 Export 형식 (MIME HTML)
> - 인코딩 문제 (Quoted-printable)
> - 불필요한 마크업 (Fenced div, 복잡한 속성)
> - 한글 손상 (NFD/NFC 혼재)
>
> **결과**: RAG 파이프라인에 넣으면 품질 저하
> - 검색 안 됨 (깨진 한글)
> - 임베딩 품질 낮음 (노이즈 많음)
> - 컨텍스트 손실 (구조 붕괴)
>
> **memex-kb는 협업의 틀을 바꿉니다**:
> ```
> Confluence (인간 협업)
>     ↓
> memex-kb (완벽한 변환)
>     ↓
> Denote Markdown (AI 협업 가능)
>     ↓
> RAG Pipeline (Second Brain)
> ```
>
> 이것은 단순한 변환 도구가 아닙니다.
> **Legacy 시스템을 AI 시대로 전환하는 첫 단계**입니다.

**참고**: Emacs 실시간 한글 입력 문제 해결은 [docs/20251112T194526--utf8-정규화-완벽-가이드-confluence-emacs__unicode_nfc_nfd_confluence_emacs.org](docs/20251112T194526--utf8-정규화-완벽-가이드-confluence-emacs__unicode_nfc_nfd_confluence_emacs.org) 참조

---

## 🎨 Denote 파일명 규칙

### 형식

```
timestamp--한글-제목__태그1_태그2.md
```

### 예시

```bash
# 입력
title: "API 설계 가이드"
tags: ["백엔드", "api", "가이드"]

# 출력
20250913t150000--api-설계-가이드__backend_api_guide.md
```

### 장점

1. **시간 기반 정렬**: 파일 탐색기에서 자동 정렬
2. **인간 친화적**: 한글 제목 유지 (검색 쉬움)
3. **명확한 태그**: 언더스코어로 구분
4. **파싱 가능**: 프로그래밍으로 정보 추출

---

## 📊 분류 규칙 (categories.yaml)

### 설정 예시

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

classification:
  min_score: 30  # 최소 매칭 점수
  weights:
    title_keyword: 10
    title_pattern: 15
    content_keyword: 5
    file_hint: 20
```

### 분류 로직

1. **키워드 매칭**: 제목/본문에서 키워드 검색
2. **패턴 매칭**: 정규식으로 제목 패턴 확인
3. **파일 힌트**: 파일명에서 힌트 추출
4. **점수 계산**: 가중치 합산
5. **최고 점수 선택**: 가장 높은 점수의 카테고리로 분류

---

## 🔧 Backend Adapter 확장 가이드

### 1. Base Adapter 인터페이스

```python
from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    """Backend Adapter 추상 클래스"""

    @abstractmethod
    def authenticate(self):
        """인증"""
        pass

    @abstractmethod
    def list_documents(self):
        """문서 목록 조회"""
        pass

    @abstractmethod
    def fetch_document(self, doc_id: str):
        """문서 내용 가져오기"""
        pass

    @abstractmethod
    def convert_to_markdown(self, content):
        """Markdown 변환"""
        pass
```

### 2. 새 Adapter 구현 예시

```python
# scripts/adapters/dooray.py

from .base import BaseAdapter

class DoorayAdapter(BaseAdapter):
    """Dooray Wiki Adapter"""

    def __init__(self, token: str):
        self.token = token

    def authenticate(self):
        # Dooray API 인증
        pass

    def list_documents(self):
        # Wiki 목록 조회
        pass

    def fetch_document(self, doc_id: str):
        # Wiki 내용 가져오기
        pass

    def convert_to_markdown(self, content):
        # Markdown 변환
        pass
```

### 3. 사용

```python
# 공통 파이프라인 사용
from adapters.dooray import DoorayAdapter
from denote_namer import DenoteNamer
from categorizer import DocumentCategorizer

# Adapter 초기화
adapter = DoorayAdapter(token="YOUR_TOKEN")

# 문서 가져오기
content = adapter.fetch_document("DOC_ID")
markdown = adapter.convert_to_markdown(content)

# Denote 파일명 생성 (공통)
namer = DenoteNamer()
filename = namer.generate_filename(
    title="문서 제목",
    tags=["tag1", "tag2"]
)

# 자동 분류 (공통)
categorizer = DocumentCategorizer()
category, score, all_scores = categorizer.categorize(
    title="문서 제목",
    content=markdown
)
```

---

## 🌟 활용 사례

### 1. 회사 기술문서 백업

```bash
# Google Docs → Markdown → Git
python scripts/batch_processor.py --backend gdocs
git add docs/
git commit -m "Backup: 기술문서 $(date +%Y%m%d)"
git push
```

### 2. 개인 지식베이스 구축

```bash
# Dooray Wiki → Markdown → Org-mode
python scripts/batch_processor.py --backend dooray
# ~/org/ 디렉토리에 복사
cp -r docs/ ~/org/work/
```

### 3. 팀 지식 공유

```bash
# Markdown → GitHub Pages
git push origin main
# GitHub Actions로 자동 배포
```

---

## 🔒 보안 고려사항

### 구현된 보안 조치

1. **로컬 우선**: 모든 데이터 로컬 저장
2. **Git 버전관리**: 변경사항 추적 가능
3. **.gitignore**: credentials 파일 제외
4. **gitleaks**: 민감 정보 자동 탐지 (네이티브)

### 보안 스캔

```bash
# Git 리포지토리 스캔
gitleaks detect

# 파일 스캔 (디지털 가든 배포 전)
gitleaks detect --no-git

# 특정 경로 스캔
gitleaks detect --source ./docs
```

### 권장사항

- API 키는 환경변수 사용
- credentials 파일은 절대 커밋 금지
- Private 저장소 사용 권장
- 정기적 보안 스캔 (커밋 전 gitleaks 실행)

---

## 📈 로드맵

### v1.0 (2025-09-13, 완료)
- ✅ Google Docs Adapter (Pandoc 기반, 95% 정확도)
- ✅ Denote 파일명 생성 (한글 제목 + 영어 태그)
- ✅ 규칙 기반 자동 분류 (LLM 비용 0원)
- ✅ Git 버전 관리

### v1.1 (2025-10-15, 완료)
- ✅ Threads SNS Adapter (아포리즘 내보내기)
- ✅ Confluence Adapter (MIME 파싱, UTF-8 정규화)
- ✅ Adapter 패턴 리팩토링
- ✅ 문서화 강화

### v1.2 (2026-01-21, 완료)
- ✅ Nix Flake 마이그레이션 (`shell.nix` → `flake.nix`)
- ✅ gitleaks 통합 (secretlint 대체)
- ✅ Threads 토큰 갱신 스크립트 (`refresh_threads_token.py`)
- ✅ direnv 통합 (`.envrc`)

### v1.3 (계획 중)
- 📋 Dooray Wiki Adapter
- 📋 Notion Adapter (Airbyte 경험 활용)
- 📋 CLI 개선

### v2.0 (RAG Pipeline Integration)

**배경**: n8n, Supabase pgvector, Ollama Embedding, Rerank API 서버 등 기술 스택 검증 완료 (2,945개 Org 파일 임베딩 성공)

**목표**: Legacy → Denote → **RAG-ready** 변환 시스템

```
memex-kb v1.x (Conversion)
    ↓ Denote Markdown
memex-kb v2.0 (Embedding Pipeline) ← NEW!
    ↓ Vector DB
n8n RAG Orchestration (검증됨)
    ↓ AI Second Brain
```

**주요 기능**:
- 💡 Denote Markdown → Vector Embedding
  - Ollama (mxbai-embed-large, 로컬)
  - 폴더별 차별화 청킹 (meta 1500, bib 1200, journal 800, notes 1000)
- 💡 Supabase pgvector 통합 (검증된 파이프라인 재사용)
- 💡 n8n RAG Workflow (Hybrid Search: 키워드 + 벡터 + 그래프)
- 💡 지식 계층 구조 반영 (meta → bib → journal → notes)

**차별화**:
- 단순 변환 도구와 다름
- **Legacy → RAG 파이프라인의 입구**
- 검증된 기술 스택 통합 (실전 경험 기반)
- 독창적 접근: Denote + 계층적 지식 구조 + RAG

---

## 🤝 기여하기

### 기여 방법

1. 이 저장소를 Fork
2. Feature 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 Push (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

### Backend Adapter 기여

새로운 Backend를 지원하고 싶으신가요?

1. `scripts/adapters/base.py` 참고
2. 새 Adapter 클래스 구현
3. 테스트 추가
4. PR 제출

**환영하는 기여**:
- Confluence Adapter
- Notion Adapter
- Obsidian Sync
- 기타 Wiki/문서 도구

---

## 📄 라이선스

MIT License

개인/상업적 용도 모두 자유롭게 사용 가능합니다.

---

## 🙏 감사의 말

### 영감을 받은 프로젝트

- [Denote](https://protesilaos.com/emacs/denote) by Protesilaos Stavrou
- [Org-mode](https://orgmode.org/) by Carsten Dominik
- [Obsidian](https://obsidian.md/) - 개인 지식베이스 트렌드

### 철학적 기반

> "The memex is a device in which an individual stores all his books, records, and communications, and which is mechanized so that it may be consulted with exceeding speed and flexibility."
>
> — Vannevar Bush, "As We May Think" (1945)

**Memex-KB는 Vannevar Bush의 Memex 개념을 현대적으로 구현합니다.**

---

## 📞 연락처

- **개발자**: Junghan Kim
- **Email**: junghanacs@gmail.com 
- **GitHub**: [junghan0611](https://github.com/junghan0611)
- **블로그**: [힣's 디지털가든](https://notes.junghanacs.com)

---

## 📚 추가 문서

- [AGENTS.md](AGENTS.md) - Claude Code 에이전트 가이드
- [CHANGELOG.md](CHANGELOG.md) - 변경 이력
- [README_SECURITY.md](README_SECURITY.md) - 보안 가이드

---

**버전**: 1.2.0
**최종 업데이트**: 2026-01-29
**상태**: 🟢 활발히 개발 중

---

**"당신의 지식을 당신의 방식으로 관리하세요."**

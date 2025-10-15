# 🧠 Memex-KB: Universal Knowledge Base Converter

> "당신의 지식을 당신의 방식으로" - Denote 기반 범용 지식베이스 변환 시스템

## 📖 철학 (Philosophy)

**Memex-KB는 지식 관리의 시작점입니다.**

입문자에게 "일정한 규칙"을 제공하여, 산재된 지식을 체계적으로 정리할 수 있도록 돕습니다.

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
    ├── Dooray Wiki    (🔧 개발 중)
    └── Confluence     (📋 계획 중)
         ↓
[Backend Adapter] ← 확장 가능한 설계
         ↓
[Markdown Conversion]
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
├── scripts/                     # 변환 및 동기화 스크립트
│   ├── adapters/                # Backend Adapters (확장 가능)
│   │   ├── base.py              # BaseAdapter (추상 클래스)
│   │   ├── gdocs.py             # Google Docs Adapter
│   │   └── dooray.py            # Dooray Adapter (개발 중)
│   ├── denote_namer.py          # Denote 파일명 생성 (공통)
│   ├── categorizer.py           # 문서 자동 분류 (공통)
│   └── batch_processor.py       # 일괄 처리
├── docs/                        # 변환된 Markdown 문서
│   ├── architecture/            # 시스템 설계
│   ├── development/             # 개발 가이드
│   ├── operations/              # 운영 문서
│   ├── products/                # 제품별 문서
│   └── _uncategorized/          # 미분류 문서
├── config/
│   ├── categories.yaml          # 분류 규칙 (사용자 정의)
│   ├── credentials.json         # API 인증 (gitignore)
│   └── .env                     # 환경변수
├── logs/                        # 실행 로그
└── README.md                    # 이 파일
```

---

## 🚀 Quick Start

### 1. 환경 설정

```bash
# Python 패키지 설치
pip install -r requirements.txt

# Pandoc 설치 (문서 변환용)
# Ubuntu/Debian
sudo apt-get install pandoc

# macOS
brew install pandoc

# NixOS
nix-shell -p pandoc
```

### 2. Google Docs 연동 (예시)

```bash
# 1. Google Cloud Console에서 프로젝트 생성
# 2. Google Drive API 활성화
# 3. Service Account 생성 및 키 다운로드
# 4. credentials.json을 config/ 디렉토리에 저장

# 환경변수 설정
cp config/.env.example config/.env
# config/.env 파일 편집
```

### 3. 문서 변환

```bash
# 단일 문서 변환
python scripts/adapters/gdocs.py "DOCUMENT_ID"

# 전체 폴더 변환
python scripts/batch_processor.py

# Git 커밋 (옵션)
git add docs/
git commit -m "Add: 새 문서 변환"
```

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
4. **Secretlint**: 민감 정보 자동 탐지

### 권장사항

- API 키는 환경변수 사용
- credentials 파일은 절대 커밋 금지
- Private 저장소 사용 권장
- 정기적 보안 스캔 (secretlint)

---

## 📈 로드맵

### v1.0 (현재)
- ✅ Google Docs Adapter
- ✅ Denote 파일명 생성
- ✅ 규칙 기반 자동 분류
- ✅ Git 버전 관리

### v1.1 (개발 중)
- 🔧 Dooray Adapter
- 🔧 Adapter 패턴 리팩토링
- 🔧 CLI 개선

### v1.2 (계획 중)
- 📋 Confluence Adapter
- 📋 Notion Adapter
- 📋 웹 UI

### v2.0 (미래)
- 💡 AI 요약 기능
- 💡 벡터 검색 (RAG)
- 💡 자동 태깅 고도화

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

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - 상세 설치 가이드
- [POC_RESULTS.md](POC_RESULTS.md) - POC 결과 보고서
- [README_SECURITY.md](README_SECURITY.md) - 보안 가이드

---

**버전**: 1.1.0
**최종 업데이트**: 2025-10-15
**상태**: 🟢 활발히 개발 중

---

**"당신의 지식을 당신의 방식으로 관리하세요."**

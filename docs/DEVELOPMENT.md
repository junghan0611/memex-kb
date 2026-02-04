# 개발 가이드

Memex-KB에 새로운 Backend를 추가하거나 기능을 확장하는 방법을 안내합니다.

---

## Backend Adapter 확장 가이드

### 1. Base Adapter 인터페이스

파일: `scripts/adapters/base.py`

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseAdapter(ABC):
    """Backend Adapter 추상 클래스"""

    @abstractmethod
    def authenticate(self) -> Any:
        """인증 수행"""
        pass

    @abstractmethod
    def list_documents(self, **kwargs) -> List[Dict]:
        """문서 목록 조회"""
        pass

    @abstractmethod
    def fetch_document(self, doc_id: str, **kwargs) -> Dict:
        """개별 문서 내용 가져오기"""
        pass

    @abstractmethod
    def convert_to_format(self, content: Dict, output_format: str) -> str:
        """문서를 Markdown/Org로 변환"""
        pass
```

### 2. 새 Adapter 구현 예시

파일: `scripts/adapters/dooray.py`

```python
from .base import BaseAdapter
from typing import List, Dict, Any

class DoorayAdapter(BaseAdapter):
    """Dooray Wiki Adapter"""

    def __init__(self, token: str, org_id: str):
        self.token = token
        self.org_id = org_id
        self.session = None

    def authenticate(self) -> Any:
        """Dooray API 인증"""
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.token}'
        })
        return self.session

    def list_documents(self, project_id: str = None) -> List[Dict]:
        """Wiki 목록 조회"""
        url = f"https://api.dooray.com/wiki/v1/..."
        response = self.session.get(url)
        return response.json()['result']

    def fetch_document(self, doc_id: str) -> Dict:
        """Wiki 내용 가져오기"""
        url = f"https://api.dooray.com/wiki/v1/.../pages/{doc_id}"
        response = self.session.get(url)
        return response.json()['result']

    def convert_to_format(self, content: Dict, output_format: str = 'markdown') -> str:
        """Markdown 변환"""
        # Dooray 특화 변환 로직
        body = content.get('body', '')
        title = content.get('title', '')

        if output_format == 'markdown':
            return f"# {title}\n\n{body}"
        elif output_format == 'org':
            return f"* {title}\n\n{body}"
        else:
            raise ValueError(f"Unsupported format: {output_format}")
```

### 3. 공통 파이프라인과 통합

```python
# 사용 예시
from adapters.dooray import DoorayAdapter
from denote_namer import DenoteNamer
from categorizer import DocumentCategorizer

# 1. Adapter 초기화
adapter = DoorayAdapter(
    token="YOUR_DOORAY_TOKEN",
    org_id="YOUR_ORG_ID"
)
adapter.authenticate()

# 2. 문서 가져오기
documents = adapter.list_documents(project_id="PROJECT_ID")

for doc in documents:
    content = adapter.fetch_document(doc['id'])
    markdown = adapter.convert_to_format(content, 'markdown')

    # 3. Denote 파일명 생성 (공통)
    namer = DenoteNamer()
    filename = namer.generate_filename(
        title=doc['title'],
        tags=doc.get('tags', [])
    )

    # 4. 자동 분류 (공통)
    categorizer = DocumentCategorizer()
    category, score, _ = categorizer.categorize(
        title=doc['title'],
        content=markdown
    )

    # 5. 파일 저장
    output_path = f"docs/{category}/{filename}"
    with open(output_path, 'w') as f:
        f.write(markdown)
```

---

## 프로젝트 구조

```
memex-kb/
├── scripts/
│   ├── adapters/              # Backend Adapters
│   │   ├── __init__.py
│   │   ├── base.py            # 추상 클래스 (필수 구현)
│   │   └── threads.py         # 구현 예시
│   ├── denote_namer.py        # Denote 파일명 생성 (공통)
│   ├── categorizer.py         # 자동 분류 (공통)
│   └── [backend]_exporter.py  # Backend별 CLI 스크립트
├── hwpx2asciidoc/             # HWPX 변환 모듈
├── epub2org/                  # EPUB 변환 모듈
├── htmltoepub/                # HTML→EPUB 변환 모듈
├── config/
│   ├── categories.yaml        # 분류 규칙
│   └── .env.example           # 환경변수 템플릿
└── docs/                      # 변환된 문서
```

---

## 환경 설정

### Nix Flake

이 프로젝트는 `flake.nix`로 모든 의존성을 관리합니다.

```bash
# 개발 환경 진입
nix develop

# 또는 direnv 사용 (권장)
direnv allow
```

### 환경변수

**공통** (`.env`):
```bash
GOOGLE_APPLICATION_CREDENTIALS=config/credentials.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
```

**Threads** (`.env.threads`):
```bash
APP_ID=your_app_id
APP_SECRET=your_app_secret
REDIRECT_URI=https://localhost/callback
ACCESS_TOKEN=your_access_token
USER_ID=your_user_id
```

---

## 코드 스타일

### Python

- 타입 힌트 사용 (`from typing import List, Dict`)
- 한글 docstring + 영어 주석 (혼합 허용)
- `logging` 모듈 사용 (`print` 지양)

```python
import logging

logger = logging.getLogger(__name__)

def fetch_document(doc_id: str) -> Dict:
    """문서 내용 가져오기

    Args:
        doc_id: 문서 ID

    Returns:
        문서 내용 딕셔너리
    """
    logger.info(f"Fetching document: {doc_id}")
    # implementation...
```

### Bash

- 색상 출력 (RED, GREEN, YELLOW, BLUE)
- `set -e`로 에러 핸들링
- 로그 파일은 `logs/`에 저장

```bash
#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Starting conversion...${NC}"
```

---

## 테스트

### 수동 테스트 워크플로우

```bash
# Threads API 토큰 테스트
nix develop --command python scripts/refresh_threads_token.py --test

# Denote 파일명 생성 테스트
nix develop --command python scripts/denote_namer.py

# 분류기 테스트
nix develop --command python scripts/categorizer.py

# 커밋 전 보안 스캔
nix develop --command gitleaks detect
```

### 새 Adapter 테스트 체크리스트

- [ ] `authenticate()` 성공적으로 인증되는가?
- [ ] `list_documents()` 문서 목록 반환하는가?
- [ ] `fetch_document()` 개별 문서 내용 가져오는가?
- [ ] `convert_to_format()` Markdown/Org 변환되는가?
- [ ] Denote 파일명 규칙 준수하는가?
- [ ] 분류기와 통합되는가?

---

## 기여하기

### 기여 방법

1. 이 저장소를 Fork
2. Feature 브랜치 생성 (`git checkout -b feature/NewBackend`)
3. 변경사항 커밋 (`git commit -m 'Add NewBackend adapter'`)
4. 브랜치에 Push (`git push origin feature/NewBackend`)
5. Pull Request 생성

### 환영하는 기여

- 새로운 Backend Adapter
  - Notion
  - Obsidian Sync
  - Jira
  - 기타 Wiki/문서 도구
- 분류 규칙 개선
- 문서화

---

## 보안 고려사항

### 구현된 보안 조치

1. **로컬 우선**: 모든 데이터 로컬 저장
2. **Git 버전관리**: 변경사항 추적 가능
3. **.gitignore**: credentials 파일 제외
4. **gitleaks**: 민감 정보 자동 탐지

### 보안 스캔

```bash
# Git 리포지토리 스캔
gitleaks detect

# 파일 스캔 (디지털 가든 배포 전)
gitleaks detect --no-git
```

### 권장사항

- API 키는 환경변수 사용
- credentials 파일은 절대 커밋 금지
- Private 저장소 사용 권장

---

← [README.md](../README.md)로 돌아가기

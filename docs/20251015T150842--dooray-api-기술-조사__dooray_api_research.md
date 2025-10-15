---
title:      "Dooray API 기술 조사"
date:       2025-10-15T15:08:42+09:00
tags:       ["dooray", "api", "research", "memex-kb"]
identifier: "20251015T150842"
---

# 🔍 Dooray API 기술 조사

**목적**: memex-kb Dooray Adapter 개발을 위한 기술 조사
**조사일**: 2025-10-15
**상태**: 🟡 진행 중 - 추가 조사 필요

---

## 📊 조사 결과 요약

### ✅ 확인된 것

**1. dooray-go 조직 리포지토리 (3개)**:

| 리포지토리 | 목적 | 언어 | 핵심 기능 |
|-----------|------|------|-----------|
| **dooray** | Go Client Library | Go | Webhook 메시징, OpenAPI 프로젝트 조회 |
| **dooray_mcp** | MCP Server (Claude 통합) | Go | Messenger, Calendar, Project 연동 |
| **doorayctl** | CLI Tool | Go | 사용자 정보, 메시징, 캘린더 조회 |

**2. 확인된 Dooray API**:
- ✅ **Messenger API**: 메시지 전송, 사용자 조회
- ✅ **Calendar API**: 일정 조회, 일정 등록
- ✅ **Project API**: 프로젝트 조회, 태스크 관리
- ✅ **Webhook API**: 메시지 발송

**3. PyDooray Python 라이브러리**:
- messenger, project, calendar, **drive**, **wiki** 지원 명시
- drive, wiki는 `Relation` 타입으로 존재
- 구체적인 메서드 미문서화

---

### ❓ 확인 필요한 것

**Wiki API**:
- [ ] Wiki 목록 조회 API
- [ ] Wiki 페이지 내용 조회 API
- [ ] Wiki Markdown export 기능
- [ ] Wiki HTML export 기능
- [ ] Notion처럼 내보내기 UI 존재 여부

**Drive API**:
- [ ] 파일 목록 조회 API
- [ ] 파일 다운로드 API
- [ ] 폴더 구조 조회 API
- [ ] Google Drive처럼 export 기능

---

## 🏗️ dooray-go 리포지토리 상세 분석

### 1. dooray (Go Client Library)

**설치**:
```bash
$ go get -u github.com/dooray-go/dooray
```

**주요 기능**:

**A. Webhook 메시징**:
```go
doorayErr := dooray.PostWebhookContext(
    subCtx1,
    "[Your WebHook URL]",
    &dooray.WebhookMessage{
        BotName: "dooray-go",
        Text: "Hello",
    }
)
```

**B. OpenAPI 프로젝트 조회**:
```go
response, err := NewDefaultProject().GetProjects(
    "{dooray-api-key}",
    projectType,
    scope,
    state
)
```

**패키지 구조**:
- `hook/`: Webhook 관련
- `openapi/`: OpenAPI 구현
- `utils/`: 유틸리티

---

### 2. dooray_mcp (MCP Server)

**목적**: Claude.ai 데스크톱 앱과 Dooray 통합

**설정**:
```json
// claude_desktop_config.json
{
  "dooray-mcp": {
    "command": "/path/to/dooray_mcp",
    "args": [],
    "env": {
      "DOORAY_TOKEN": "your-token-here"
    }
  }
}
```

**주요 파일**:
- `main.go`: 앱 진입점
- `messenger.go`: 메시징 기능
- `calendar.go`: 캘린더 관리
- `project.go`: 프로젝트/태스크
- `account.go`: 인증

**사용 예시**:
```
"오늘 내 일정을 중요한 순으로 정렬해서 김XX에게 메신저로 보내줘"
"내일 일정 중에 중요한 일정은 뭐야?"
"Dooray-잘쓰자 프로젝트에서 가장 급한일을 알려줘"
```

**언어 비율**:
- Go: 97.9%
- Shell: 2.1%

---

### 3. doorayctl (CLI Tool)

**목적**: Dooray Open API CLI 도구

**설정**:
```bash
# ~/.dooray/config
YOUR_DOORAY_API_TOKEN
```

**설치**:
```bash
$ sudo mv doorayctl.darwin.arm64 /usr/local/bin/doorayctl
```

**명령어**:

**사용자 정보 조회**:
```bash
$ doorayctl account 정지범
ID: 1234567890123456789
이름: 정지범
외부 이메일: jibum@example.com
```

**메시지 전송**:
```bash
$ doorayctl messenger [UserID] "안녕하세요"
메시지가 정상적으로 보내졌습니다.
```

**캘린더 조회**:
```bash
$ doorayctl calendar list
ID: calendar-123...
이름: 내 캘린더
타입: personal
생성일: 2025-01-01
소유자: user@example.com
```

---

## 🔧 PyDooray Python 라이브러리 분석

**설치**:
```bash
pip install PyDooray
```

**지원 서비스** (문서 명시):
- messenger
- project
- calendar
- **drive** ⭐
- **wiki** ⭐

**Project 객체**:
```python
# drive와 wiki는 Relation 타입
class Project:
    wiki: dooray.DoorayObjects.Relation
    drive: dooray.DoorayObjects.Relation
```

**문제점**:
- drive, wiki의 구체적 메서드 미문서화
- export/download 기능 불명확
- API 레퍼런스에 상세 내용 없음

---

## 🚨 조사 결과: Wiki/Drive Export 불명확

### 문제 상황

**1. 공식 문서 접근 제한**:
- Dooray helpdesk 문서가 WebFetch로 내용 확인 불가
- API 전체 목록 파악 어려움

**2. Wiki API 미확인**:
- PyDooray에 wiki가 존재하지만 메서드 없음
- Wiki export API 존재 여부 불명
- Markdown export 기능 미확인

**3. Drive API 미확인**:
- PyDooray에 drive가 존재하지만 메서드 없음
- 파일 다운로드 API 존재 여부 불명
- Google Drive처럼 export 기능 미확인

---

## 🎯 다음 단계

### 즉시 실행 필요

**1. Dooray 계정 생성 & 직접 확인**:
```
- [ ] Dooray 30일 무료 계정 생성
- [ ] Wiki 기능 테스트
- [ ] Wiki 내보내기 UI 확인 (Notion처럼?)
- [ ] Drive 기능 테스트
- [ ] API Token 발급
```

**2. Dooray Helpdesk 문서 수동 확인**:
```
- [ ] https://helpdesk.dooray.com/share/pages/9wWo-xwiR66BO5LGshgVTg
      브라우저로 직접 접속
- [ ] Wiki API 섹션 찾기
- [ ] Drive API 섹션 찾기
- [ ] Export/Download API 찾기
```

**3. dooray-go 소스코드 직접 확인**:
```bash
# dooray_mcp 리포 클론
git clone https://github.com/dooray-go/dooray_mcp.git
cd dooray_mcp

# messenger.go, calendar.go, project.go 패턴 확인
# 비슷한 패턴으로 wiki.go, drive.go 구현 가능한지 파악
```

**4. PyDooray 소스코드 확인**:
```bash
# PyDooray 소스코드 확인
git clone https://github.com/dooray/PyDooray.git

# wiki, drive Relation 객체 실제 구현 확인
# API 엔드포인트 파악
```

---

## 💡 대안 전략 (Wiki Export 불가능 시)

### Plan A: HTML Scraping (최후의 수단)
```python
# Dooray Wiki가 웹 UI만 제공하는 경우
import requests
from bs4 import BeautifulSoup

def scrape_dooray_wiki(wiki_url, auth_token):
    # 로그인 후 HTML 크롤링
    # BeautifulSoup로 파싱
    # Pandoc으로 HTML → Markdown 변환
    pass
```

**단점**:
- 불안정 (UI 변경 시 깨짐)
- Rate Limiting 이슈
- 비공식 방법

---

### Plan B: Dooray Drive API 활용 (⭐ 권장!)

**전략**: Google Drive와 유사한 패턴 가정

**Google Drive 패턴**:
```python
# memex-kb에서 검증된 방식
from google.oauth2 import service_account
from googleapiclient.discovery import build

# 1. 인증
service = build('drive', 'v3', credentials=creds)

# 2. 파일 목록 조회
results = service.files().list(
    q="mimeType='application/vnd.google-apps.document'",
    fields="files(id, name, mimeType)"
).execute()

# 3. DOCX로 Export
request = service.files().export_media(
    fileId=file_id,
    mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
)

# 4. Pandoc 변환
# DOCX → Markdown (이미 검증됨!)
```

**Dooray Drive 예상 패턴**:
```python
# 유사하게 구현 가능할 것으로 예상
import requests

class DoorayDriveAdapter(BaseAdapter):
    BASE_URL = "https://api.dooray.com"

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"dooray-api {token}"
        }

    def list_files(self, project_id: str):
        """Drive 파일 목록 조회"""
        # 추정 엔드포인트: /drive/v1/files?projectId=XXX
        response = requests.get(
            f"{self.BASE_URL}/drive/v1/files",
            headers=self.headers,
            params={"projectId": project_id}
        )
        return response.json()

    def download_file(self, file_id: str):
        """파일 다운로드"""
        # 추정 엔드포인트: /drive/v1/files/{file_id}/download
        response = requests.get(
            f"{self.BASE_URL}/drive/v1/files/{file_id}/download",
            headers=self.headers,
            stream=True
        )
        return response.content

    def convert_to_markdown(self, file_content, file_type):
        """파일 → Markdown 변환"""
        if file_type == 'docx':
            # Google Docs 패턴 재사용!
            # DOCX → Pandoc → Markdown (검증됨)
            import pypandoc
            return pypandoc.convert_text(
                file_content,
                'markdown',
                format='docx'
            )
        elif file_type == 'html':
            # HTML → Markdown
            return pypandoc.convert_text(
                file_content,
                'markdown',
                format='html'
            )
        elif file_type == 'md':
            # 이미 Markdown
            return file_content.decode('utf-8')
```

**장점**:
- ✅ Google Docs 패턴과 동일 (검증된 방식)
- ✅ Pandoc 재사용 (DOCX → Markdown 이미 검증)
- ✅ 파일 기반이라 더 안정적
- ✅ Wiki보다 범용적 (모든 문서 타입 지원)

**확인 필요**:
- [ ] Dooray Drive API 엔드포인트
- [ ] 파일 목록 조회 API
- [ ] 파일 다운로드 API
- [ ] 지원하는 파일 타입 (DOCX? MD? HTML?)

---

### Plan C: Project API 활용
```python
# Wiki가 Project에 포함되어 있다면
# Project API로 접근
def get_wiki_from_project(project_id, auth_token):
    # PyDooray Project.wiki 사용
    # Relation 객체 탐색
    pass
```

---

## 📋 memex-kb Dooray Adapter 설계 (잠정)

### 가정: Wiki API가 존재한다면

```python
# scripts/adapters/dooray.py

from .base import BaseAdapter
import requests

class DoorayAdapter(BaseAdapter):
    """Dooray Wiki Adapter"""

    BASE_URL = "https://api.dooray.com"

    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"dooray-api {token}",
            "Content-Type": "application/json"
        }

    def authenticate(self):
        """토큰 유효성 확인"""
        response = requests.get(
            f"{self.BASE_URL}/common/v1/members/me",
            headers=self.headers
        )
        return response.status_code == 200

    def list_documents(self):
        """Wiki 목록 조회 (API 엔드포인트 확인 필요!)"""
        # 추정: /wiki/v1/wikis?projectId=XXX
        response = requests.get(
            f"{self.BASE_URL}/wiki/v1/wikis",
            headers=self.headers
        )
        return response.json()

    def fetch_document(self, doc_id: str):
        """Wiki 내용 가져오기 (API 엔드포인트 확인 필요!)"""
        # 추정: /wiki/v1/wikis/{doc_id}
        response = requests.get(
            f"{self.BASE_URL}/wiki/v1/wikis/{doc_id}",
            headers=self.headers
        )
        return response.json()

    def convert_to_markdown(self, content):
        """Markdown 변환"""
        # Dooray가 Markdown 제공하면 그대로 사용
        # HTML 제공하면 Pandoc 변환
        if content.get('format') == 'markdown':
            return content.get('body')
        else:
            # Pandoc HTML → Markdown
            import pypandoc
            return pypandoc.convert_text(
                content.get('body'),
                'markdown',
                format='html'
            )
```

---

## 🔗 참고 링크

**GitHub 리포지토리**:
- https://github.com/dooray-go/dooray
- https://github.com/dooray-go/dooray_mcp
- https://github.com/dooray-go/doorayctl

**dooray-go 개발자**:
- **정지범** (zbum): https://github.com/zbum
  - dooray-go 조직 리포지토리 메인테이너
  - Go로 Dooray 클라이언트 라이브러리 개발

**공식 문서**:
- Dooray API: https://helpdesk.dooray.com/share/pages/9wWo-xwiR66BO5LGshgVTg
- PyDooray: https://pydooray.readthedocs.io/

**관련 프로젝트**:
- memex-kb: https://github.com/junghan0611/memex-kb
- memex-kb Dooray Adapter 개발: ~/claude-memory/projects/20251015T143530--memex-kb-dooray-adapter-개발__active_dooray_opensource.md

---

## 📝 결론 및 권장사항

### 현재 상황
- Messenger, Calendar, Project API는 명확히 확인됨
- **Wiki, Drive API는 존재 여부 불명확**
- 공식 문서 접근 제한으로 상세 확인 불가

### 권장사항

**우선순위 1: 직접 확인**
1. Dooray 30일 계정 생성
2. Wiki 기능 테스트
3. UI에서 내보내기 확인
4. API Token으로 직접 테스트

**우선순위 2: 소스코드 확인**
1. dooray-go 리포 클론
2. PyDooray 소스 확인
3. API 엔드포인트 패턴 파악

**우선순위 3: 대안 준비**
- Wiki API 없으면: HTML Scraping
- Drive API 활용 가능성 탐색
- Project API 경유 가능성 확인

### 다음 체크포인트
- **2025-10-17**: Dooray 계정 생성 & Wiki 테스트 완료
- **2025-10-18**: API 엔드포인트 확인 & Adapter 설계 확정

---

## 📧 후배 연락용 질문 리스트

**컨텍스트**:
```
안녕하세요! 정한 형입니다.

Dooray 추천해주신다고 하셨죠. 감사합니다!
이직 포트폴리오용으로 Dooray 관련 도구를 만들어보려고 하는데,
몇 가지 기술적인 질문이 있어서 연락드립니다.
```

**질문 1: Wiki API**
```
Q: Dooray Wiki를 API로 조회하거나 export할 수 있나요?
   - Wiki 목록 조회 API
   - Wiki 내용 조회 API
   - Markdown/HTML export API
   - 혹시 UI에서 "내보내기" 기능이 있나요? (Notion처럼)
```

**질문 2: Drive API**
```
Q: Dooray Drive API는 어떤 기능을 제공하나요?
   - 파일 목록 조회 API
   - 파일 다운로드 API
   - Google Drive처럼 export 기능이 있나요?
   - 지원하는 파일 타입은? (DOCX, MD, HTML 등)
```

**질문 3: API 문서**
```
Q: Dooray API 공식 문서가 있나요?
   - https://helpdesk.dooray.com/share/pages/9wWo-xwiR66BO5LGshgVTg
     여기 말고 더 상세한 개발자 문서가 있는지 궁금합니다
   - OpenAPI Spec이나 Swagger 문서가 있을까요?
```

**질문 4: 사용 사례**
```
Q: 현재 Dooray 사용 회사들이 주로 어떤 기능을 많이 쓰나요?
   - Wiki를 많이 쓰나요? 아니면 Messenger 중심인가요?
   - 기술문서를 어디에 저장하나요? (Wiki? Drive?)
   - 개인 지식베이스로 활용하는 사람들이 있나요?
```

**배경 설명**:
```
제가 만들려는 도구:
- Dooray Wiki/Drive 문서를 개인 지식베이스(Org-mode)로 자동 백업
- Denote 파일명 규칙으로 체계적 관리
- Git 버전 관리로 모든 변경사항 추적
- Google Docs도 지원하는 범용 KB 변환 도구

목적:
- 입사 후 바로 사용할 수 있는 실용적 도구
- 이직 포트폴리오 (검증된 아키텍처 재사용 능력 입증)
- 오픈소스 공개 (MIT License)
```

**마무리**:
```
혹시 내부 API 문서나 사용 가이드가 있으면
공유 가능한 범위 내에서 알려주시면 감사하겠습니다!

시간 되실 때 편하게 답변 주세요 :)
```

---

**최종 업데이트**: 2025-10-15T15:20:00+09:00
**작성자**: Claude AI + junghanacs

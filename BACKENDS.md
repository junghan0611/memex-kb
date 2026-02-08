# Backend 연동 가이드

Memex-KB는 다양한 Backend 소스를 지원합니다. 각 Backend별 설정, 접근법 비교, 한계 및 권장 워크플로우를 안내합니다.

## History

- **2026-02-08**: Google Docs - 3가지 접근법(MCP/네이티브MD/Pandoc DOCX) 실측 비교, `gdocs_md_processor.py` 추가 (탭 분할 + 이미지 추출)
- **2026-02-04**: BACKENDS.md 초안 작성 (Google Docs, Threads, Confluence, HWPX)
- **2026-01-29**: Confluence MIME 파싱 + UTF-8 정규화 파이프라인 완성

---

## 지원 Backend 현황

| Backend | 상태 | 스크립트 | 권장 접근법 |
|---------|------|----------|-------------|
| Google Docs | ✅ 구현됨 | `gdocs_md_processor.py` | 브라우저 탭별 MD + 이미지 추출 |
| Threads SNS | ✅ 구현됨 | `threads_exporter.py` | API 직접 호출 |
| Confluence | ✅ 구현됨 | `confluence_to_markdown.py` | MIME 파싱 + Pandoc |
| HWPX | ✅ 구현됨 | `hwpx2asciidoc/` | XML 직접 파싱 |
| Dooray Wiki | 🔧 개발 중 | - | - |

---

## Google Docs 연동

Google Docs는 팀 협업에서 가장 빈번하게 사용되는 소스입니다. 문서를 가져올 때 **이미지, 표, 탭(Tab) 구조**를 보존하는 것이 핵심 과제입니다.

### 접근법 비교 (2026-02-08 실측)

3가지 접근법을 동일 문서(연구개발계획서, 26MB, 15탭, 이미지 5장)에 적용한 결과:

| 항목 | 브라우저 MD 내보내기 | MCP get_doc_content | Pandoc DOCX 변환 |
|------|---------------------|---------------------|-------------------|
| **헤딩** | `## 1.1 제목` (보존) | `1.1 제목` (plain text) | `## 1.1 제목` (보존) |
| **표** | MD 표로 변환 | 셀별 줄 분리 (구조 손실) | 복잡한 표 깨짐 |
| **볼드/이탤릭** | `**굵게**` (보존) | 포맷팅 없음 | `**굵게**` (보존) |
| **이미지** | base64 인라인 (5개) | 없음 | BMP 추출 (4개, 1개 누락) |
| **탭 분리** | 브라우저에서 탭별 개별 내보내기 | `--- TAB: xxx ---` 마커 (유일한 소스) | 탭 구분 없음 (전체 병합) |
| **크기 제한** | 없음 (수동) | 없음 | 26MB 초과 시 API 거부 |
| **출력 용량** | 1,463KB (base64 포함) | 196KB (text only) | 781KB + 7.4MB (BMP) |
| **인증** | 브라우저 세션 | MCP OAuth (자동) | Google API 키 필요 |

### 한계 정리

| 접근법 | 핵심 한계 | 대안 |
|--------|-----------|------|
| MCP `get_doc_content` | 이미지/포맷팅 없음 | 탭 발견 전용으로 사용 |
| MCP `get_drive_file_download_url` | 26MB 초과 시 DOCX 내보내기 불가 | 수동 다운로드 |
| Pandoc DOCX | 이미지 BMP 출력, 복잡한 표 깨짐, 이미지 누락 가능 | 네이티브 MD 사용 |
| 네이티브 MD 내보내기 | base64 인라인 (파일 비대), 이스케이프 문자 | `extract-images`로 후처리 |
| Google Docs API (v1/v2) | 인증 복잡, 이미지 미지원 | MCP 또는 네이티브 활용 |

### 권장 워크플로우

```
[에이전트]                          [사용자]
    │                                  │
    ├─ MCP get_doc_content ───────────►│
    │  "16개 탭 발견, 핵심 탭 안내"     │
    │                                  │
    │◄────── 브라우저에서 탭별 MD ──────┤
    │        내보내기 (File → Download  │
    │        → Markdown)               │
    │                                  │
    ├─ gdocs_md_processor.py ─────────►│
    │  extract-images                  │
    │  "28KB MD + 5개 PNG 생성"        │
    │                                  │
    ├─ 후속 변환 (MD → Org 등) ───────►│
    │  "HWPX 검증/합병 준비 완료"      │
```

**Step 1: 탭 구조 파악** (에이전트가 수행)

```bash
# MCP get_doc_content 호출 후 탭 분할
python scripts/gdocs_md_processor.py split-tabs \
  --input mcp_output.json \
  --output-dir ./output/tabs
```

**Step 2: 탭별 MD 내보내기** (사용자가 브라우저에서 수행)

Google Docs 브라우저에서:
1. 원하는 탭 선택
2. File → Download → Markdown (.md)
3. 탭마다 반복 (또는 핵심 탭만 선택)

**Step 3: 이미지 추출** (에이전트가 수행)

```bash
# base64 인라인 이미지 → 별도 PNG 파일
python scripts/gdocs_md_processor.py extract-images \
  --input "1-연구개발과제의필요성.md" \
  --output-dir ./output

# 결과: 1,463KB → 28KB MD + 1.1MB images/ (98% 텍스트 감소)
```

**Step 4: 전체 처리** (탭 분할 + 이미지 추출 통합)

```bash
python scripts/gdocs_md_processor.py full \
  --mcp-input mcp_output.json \
  --md-input exported.md \
  --output-dir ./output
```

### 에이전트 가이드

Google Docs 협업 시 에이전트가 알아야 할 사항:

1. **탭 발견은 MCP만 가능**: `get_doc_content`의 `--- TAB: xxx (ID: t.xxx) ---` 마커가 유일한 탭 정보 소스
2. **이미지 품질은 네이티브 MD가 최고**: PNG 원본 품질, Pandoc DOCX는 BMP로 열화
3. **26MB 이상 문서는 API 내보내기 불가**: `exportSizeLimitExceeded` 에러 → 수동 다운로드 안내
4. **이스케이프 문자 주의**: 네이티브 MD 내보내기 시 `\*\*`, `\<`, `\~` 등 불필요한 이스케이프 발생
5. **표 품질**: 네이티브 MD > Pandoc DOCX >> MCP text (복잡한 병합 셀은 모든 접근법에서 한계)

### 레거시 스크립트

v1/v2는 Google API를 직접 호출하는 방식 (이미지 미지원, 참고용):

```bash
# v1: Google Docs API 직접 파싱
nix develop --command python scripts/gdocs_to_markdown.py "DOCUMENT_ID"

# v2: Pandoc 활용 변환
nix develop --command python scripts/gdocs_to_markdown_v2.py "DOCUMENT_ID"
```

---

## Threads SNS 연동

**아포리즘을 디지털가든으로**: Threads 포스트를 단일 Org 파일로 통합

### 환경 설정

```bash
# 환경변수 설정
cp config/.env.threads.example config/.env.threads
# config/.env.threads 파일 편집 (APP_ID, APP_SECRET, REDIRECT_URI)
```

### 사용법

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
```

### 결과

- `docs/threads-aphorisms.org` 생성
- 포스트 (시간순 정렬)
- 댓글 포함
- 이미지 다운로드 (`docs/images/threads/`)
- Permalink 연결
- "어쏠리즘(Assholism)": 추천 알고리즘을 넘어선 진정한 연결

### Org 구조

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

### 옵션

```bash
# 테스트로 5개만 내보내기
nix develop --command python scripts/threads_exporter.py --max-posts 5 --download-images

# 오래된 순으로 정렬
nix develop --command python scripts/threads_exporter.py --reverse --download-images
```

**상세 문서**: [20251107T123200--threads-aphorism-exporter-프로젝트__threads_aphorism_assholism.org](20251107T123200--threads-aphorism-exporter-프로젝트__threads_aphorism_assholism.org)

---

## Confluence 연동

**Legacy 문서를 RAG-ready 형태로**: Confluence Export를 완벽한 Markdown으로 변환

### 왜 이것이 memex-kb의 핵심인가?

변환 도구는 많습니다. Pandoc, Notion Exporter, Confluence API...
하지만 **문자 인코딩 하나**를 제대로 처리하지 못하면 모든 것이 무너집니다.

- 한글이 깨지면? → 검색 불가능
- NFD/NFC 혼재? → 파일 손상, 편집 불가능
- Quoted-printable 오류? → 데이터 유실

**memex-kb는 "변환"이 아닌 "완벽한 변환"을 추구합니다.**

### 문제 상황

Confluence에서 Export한 `.doc` 파일을 pandoc으로 변환 시:
- 한글이 유니코드 escape 형식(`=EC=97=B0...`)과 섞여서 표시
- Fenced div (`:::`) 및 불필요한 HTML 속성 남음
- 코드 블록이 복잡한 형식으로 변환됨

### 해결책

**완벽한 MIME 파싱 + Pandoc + 후처리** 파이프라인:

1. Python `email` 모듈로 MIME 메시지 파싱
2. HTML 파트를 UTF-8로 추출
3. Pandoc으로 깨끗한 Markdown 변환
4. Fenced div 제거 및 코드 블록 정리
5. Unicode NFD → NFC 정규화 (한글 완벽 보존)

### 사용법

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

### 변환 결과

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

### 기술 세부사항

- **MIME 파싱**: `email.message_from_binary_file()` 사용
- **Quoted-Printable 디코딩**: Soft line break 자동 처리
- **UTF-8 정규화**: `unicodedata.normalize('NFC')` 적용
- **Pandoc 옵션**: `--wrap=none` (라인 래핑 방지)
- **성능**: 1.1MB 문서 → 178KB (2초 이내)

### 왜 이것이 혁명적인가?

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

**참고**: Emacs 실시간 한글 입력 문제 해결은 [20251112T194526--utf8-정규화-완벽-가이드-confluence-emacs__unicode_nfc_nfd_confluence_emacs.org](20251112T194526--utf8-정규화-완벽-가이드-confluence-emacs__unicode_nfc_nfd_confluence_emacs.org) 참조

---

## HWPX 연동

**한글 문서를 AI 에이전트와 함께**: HWPX ↔ AsciiDoc 양방향 변환

### 개요

- HWPX/OWPML → AsciiDoc 변환 (테이블 병합 보존)
- AsciiDoc → HWPX 역변환 (왕복 변환 테스트 통과)
- KS X 6101 표준 준수

### 사용법

```bash
# HWPX → AsciiDoc
nix develop --command python hwpx2asciidoc/hwpx_to_asciidoc.py input.hwpx output.adoc

# AsciiDoc → HWPX
nix develop --command python hwpx2asciidoc/asciidoc_to_hwpx.py input.adoc output.hwpx

# 통합 CLI
nix develop --command ./hwpx2asciidoc/run.sh
```

### v1.4 방향: Org-mode 메타 포맷

> **"Org-mode를 국가과제 제안서의 메타 포맷으로"**

여러 세부과제를 취합하고, 용어/양식을 통일하여, 한 사람이 작성한 것처럼 일관된 문서를 AI 에이전트와 함께 생성합니다.

자세한 내용은 [README.md 로드맵](README.md#-로드맵) 참조

---

## 새 Backend 추가하기

새로운 Backend를 지원하려면 [DEVELOPMENT.md](DEVELOPMENT.md)의 Adapter 확장 가이드를 참조하세요.

---

← [README.md](README.md)로 돌아가기

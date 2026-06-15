# Backend 연동 가이드

Memex-KB는 다양한 Backend 소스를 지원합니다. 각 Backend별 설정, 접근법 비교, 한계 및 권장 워크플로우를 안내합니다.

## History

- **2026-02-08**: Google Docs - v4 완성: Python 직접 API 호출로 탭별 MD + 이미지 추출 완전 자동화 (`export` 명령). Apps Script 방식 폐기
- **2026-02-15**: GitHub Stars → BibTeX 백엔드 추가 (doomemacs-config에서 이관)
- **2026-02-04**: BACKENDS.md 초안 작성 (Google Docs, Threads, Confluence, HWPX)
- **2026-01-29**: Confluence MIME 파싱 + UTF-8 정규화 파이프라인 완성

---

## 지원 Backend 현황

| Backend | 상태 | 스크립트 | 권장 접근법 |
|---------|------|----------|-------------|
| Google Docs | ✅ 구현됨 | `gdocs_md_processor.py` | `export` 명령 (완전 자동) |
| Threads SNS | ✅ 구현됨 | `threads_exporter.py` | API 직접 호출 |
| Confluence | ✅ 구현됨 | `confluence_to_markdown.py` | MIME 파싱 + Pandoc |
| HWPX | ✅ 구현됨 | `hwpx2asciidoc/` | XML 직접 파싱 |
| GitHub Stars | ✅ 구현됨 | `gh_starred_to_bib.sh` | gh CLI + jq → BibTeX |
| Dooray Wiki | 🔧 개발 중 | - | - |
| Scan PDF / EPUB | ✅ 활성 | `.claude/skills/scanbook/`, `mineru-client/`, `scripts/mineru2org.py`, `./run.sh mineru-*`, `./run.sh diff-review`, `./run.sh org2epub-build` | MinerU VLM → Org → EPUB. 새 세션은 scanbook 스킬부터 읽기 |
| ROSSE 배포 (syndicate) | ✅ 활성 | `.claude/skills/syndicate/`, `scripts/syndicate.py`, `./run.sh syndicate`, `./run.sh syndicate-specs` | 가든 canonical 노트 → 매체별 복붙 묶음 1파일(원문형/전문형/요약형). 복붙·브라우저 1차, API 발행 후속. 새 세션은 syndicate 스킬부터 읽기. 이슈 #4 |

---

## 스캔 책 → Org/EPUB 변환 툴체인

현재 기준선(2026-06)은 **MinerU VLM → `scripts/mineru2org.py` → Org → ox-epub**이다.
새 세션에서 `물리학강의`, `mineru`, `스캔책`, `epub 만들` 같은 작업을 시작하면 먼저
repo-local skill **`.claude/skills/scanbook/SKILL.md`** 를 읽는다. run.sh는 로컬 명령만 담고,
스킬은 원격 GPU 서버, 책별 config 작성법, 교정 판단, EPUB 함정을 담는다.

### 경계와 진입점

| 구성요소 | 역할 | 메모 |
|----------|------|------|
| `.claude/skills/scanbook/SKILL.md` | 운영 절차 SSOT | gpu2i 서버 확인, 5단계 파이프라인, 교정 전략, 새 책 체크리스트 |
| `mineru-client/` | 로컬 얇은 클라이언트 | 추론은 원격 gpu2i vLLM; 로컬은 HTTP client |
| `./run.sh mineru-setup` | MinerU client 설치 | `uv sync`; opencv-headless override |
| `./run.sh mineru-parse <PDF> [OUT]` | PDF → Markdown + `content_list.json` + images | SSH tunnel 자동 생성. 서버 자체는 nixos 담당 영역 |
| `scripts/mineru2org.py` | MinerU Markdown → clean Org | headings/footnotes/equations/images/HTML residue/EPUB header 처리 |
| `scripts/corrections/<book>.json` | 책별 구조·교정 SSOT | `meta`, `structure`, `safe_regex`, `literal`, `candidate_regex` |
| `./run.sh diff-review <a> <b>` | 전사본 충돌점 추출 | 엔진 무관 QA. marker 전용 명령이 아님 |
| `./run.sh org2epub-build <book.org>` | Org → EPUB3 + epubcheck | `~/repos/gh/ox-epub` fork를 직접 로드 |
| `scanpdf/` | nested private repo | PDF, MinerU outputs, EPUB 등 책 데이터는 여기서 추적 |
| `scanpdf2org/` | 이전 vision 전사 표면 | 이미 있는 vision본은 oracle로 쓸 수 있지만 새 책 primary는 아님 |

### 원격 MinerU 서버

- 서버: `gpu2i` tmux session `mineru-vllm`, vLLM `MinerU2.5-Pro`, port `30000`.
- 새 parse 전 먼저 확인:

```bash
ssh gpu2i 'tmux ls | grep mineru-vllm'
```

- 없으면 GLG / nixos 담당에게 요청한다. memex-kb 세션에서 직접 서버를 띄우지 않는다.
- `./run.sh mineru-parse`는 `localhost:30000 → gpu2i:30000` SSH tunnel만 자동 보장한다.

### 교정 전략

MinerU가 본문·수식·그림을 빠르게 깔아주지만, 책의 핵심어 OCR 오독은 남을 수 있다.
자동 치환은 안전한 규칙만 적용한다.

- `safe_regex`: 문맥 없이도 안전한 정규식만 자동 적용.
- `literal`: 검증된 정확 문자열 치환.
- `candidate_regex`: 로그만 남기고 본문은 건드리지 않음.
- 애매한 후보는 사람/LLM이 문맥을 읽어 경량 교정한다.
- 이미 vision 전사본이 있는 책은 `diff-review`로 oracle처럼 비교할 수 있다.

### 은퇴한 경로

- **vision/Opus 전체 전사**: 새 책 primary가 아니다. 기존 전사본은 gold/oracle로만 사용.
- **marker/surya OCR**: memex-kb에서 제거됨. `marker-pdf`, `marker-diff`, `marker/STRATEGY.md`를 문서나 새 작업 지시의 primary로 쓰지 않는다.
- **tesseract / ocrmypdf**: 한글 스캔 품질 문제로 flake/run.sh에서 제거됨.

### flake.nix에 포함한 경량/중간급 도구

| 도구 | 역할 | 메모 |
|------|------|------|
| `mupdf` / `mutool` | PDF 조작·추출·점검 | `pdfinfo`/page sanity, 이미지/페이지 확인 보조 |
| `poppler_utils` | `pdfinfo`, `pdftotext`, `pdfimages` | born-digital PDF 구조 점검/추출 보조 |
| `epubcheck` | EPUB 검증 | `./run.sh org2epub-build` 검증에도 사용 |
| `uv` | PyPI client 도구 잠금/venv 관리 | `mineru-client/` 설치 |

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

### 권장 워크플로우 (완전 자동)

```
[에이전트] ── export DOC_ID ──►  Google API 직접 호출
    │                              │
    ├─ 1. OAuth 토큰 갱신           │ (~/.google_workspace_mcp_work/credentials/)
    ├─ 2. Docs API → 탭 목록 조회   │ (documents/{id}?fields=tabs)
    ├─ 3. 탭별 MD 다운로드           │ (/export?format=markdown&tab={tabId})
    └─ 4. base64 이미지 → PNG 추출  │
                                    ▼
                              output/
                              ├── 00--탭이름.md
                              ├── 01--탭이름.md
                              └── images/
                                  ├── tab00-image1.png
                                  └── tab01-image1.png
```

**한 줄 실행** (사용자 개입 불필요):

```bash
# 문서 ID만 넣으면 탭별 MD + 이미지 자동 추출
nix develop --command python scripts/gdocs_md_processor.py export \
  "DOC_ID" --output-dir ./output

# 특정 Google 계정 지정
nix develop --command python scripts/gdocs_md_processor.py export \
  "DOC_ID" --account jhkim2@goqual.com --output-dir ./output
```

**레거시 (수동 워크플로우)**:

```bash
# MCP 출력에서 탭 분할
python scripts/gdocs_md_processor.py split-tabs -i mcp_output.json -o ./output

# 브라우저 다운로드 MD에서 이미지 추출
python scripts/gdocs_md_processor.py extract-images -i exported.md -o ./output
```

### 에이전트 가이드

Google Docs 변환 시 에이전트가 알아야 할 사항:

1. **`export` 명령 우선 사용**: `gdocs_md_processor.py export DOC_ID`로 완전 자동화. MCP 불필요
2. **인증**: MCP credentials (`~/.google_workspace_mcp_work/credentials/`)의 refresh_token 재활용
3. **이미지 처리**: base64 인라인 → PNG 파일 자동 추출 (탭별 prefix로 충돌 방지)
4. **이스케이프 문자 주의**: Google MD export 시 `\*\*`, `\<`, `\~` 등 불필요한 이스케이프 발생 (bd-207)
5. **표 품질**: 네이티브 MD가 최고 (복잡한 병합 셀은 모든 접근법에서 한계)

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

## GitHub Stars 연동

**개발자의 관심사를 지식으로**: GitHub Starred repos를 BibTeX로 변환하여 Citar/Denote 생태계와 연결

### 왜 BibTeX인가?

GitHub Stars는 개발자의 **관심사 타임라인**입니다. 하지만 웹 UI에서는:
- 검색/필터링이 빈약
- starred_at(별 찍은 시점) 메타데이터 활용 불가
- Emacs/Org-mode 워크플로우와 단절

BibTeX `@software{}` 엔트리로 변환하면:
- **Citar**에서 즉시 검색/인용 가능
- **3가지 시간축** 보존: starred_at, pushed_at, updated_at
- **topics → keywords** 매핑으로 주제별 탐색

### 사용법

```bash
# 기본 출력 (~/org/resources/github-starred.bib)
./run.sh github-starred-export

# 출력 경로 지정
./run.sh github-starred-export ~/custom/path.bib
```

### 의존성

- `gh` CLI (시스템 설치, NixOS 전역)
- `jq` (flake.nix에 포함)
- `gh auth login` 사전 인증 필요

### BibTeX 필드 매핑

| BibTeX 필드 | GitHub API 소스 | Citar 템플릿 |
|-------------|-----------------|--------------|
| `title` | `full_name` (owner/repo) | `${title:49}` |
| `author` | `owner.login` | `${author editor:19}` |
| `date` | `updated_at` | `${date year issued:4}` |
| `origdate` | `created_at` | - |
| `url` | `html_url` | `${url:19}` |
| `urldate` | `starred_at` (날짜만) | - |
| `abstract` | `description` | `${abstract}` |
| `keywords` | `topics` (콤마 구분) | `${keywords:*}` |
| `note` | stars, language, license | - |
| `datemodified` | `pushed_at` | `${datemodified:10}` |
| `dateadded` | `starred_at` | `${dateadded:10}` |

### 에이전트 가이드

1. **gh 인증 확인**: `gh auth status`로 사전 체크
2. **API Rate Limit**: paginate 사용 → star 수천 개도 자동 처리
3. **출력 위치**: `~/org/resources/github-starred.bib` (Citar 자동 감지 경로)
4. **갱신 주기**: 수동 실행 (star 추가 시 재실행)

---

## 새 Backend 추가하기

새로운 Backend를 지원하려면 [DEVELOPMENT.md](DEVELOPMENT.md)의 Adapter 확장 가이드를 참조하세요.

---

← [README.md](README.md)로 돌아가기

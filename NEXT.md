# NEXT — memex-kb

휘발성 후속 작업 메모. 영속 사실은 AGENTS.md / docs / commit으로 옮긴다.

## 지금 작업 중: scanpdf2org (스캔 한글 책 → org)

전자책 없는 한글 책 5권을 스캔. vision 전사로 org화 → EPUB(듣기).
**전통 OCR 안 씀** — 에이전트가 페이지 이미지를 직접 읽어 옮긴다.

- 파이프라인 문서: `scanpdf2org/README.org`
- 전사 규칙(SSOT): `scanpdf2org/prompts/page-to-org.md`
- 렌더: `./run.sh scanpdf2org-render <PDF> <OUT> [PAGES] [DPI]`

### 리포 분리 (2026-05-31)

- **데이터/작업 = 별도 private 리포 `scanpdf/`** (memex-kb 안에 nested, memex-kb는 전체 무시).
  - PDF 5권 = **Git LFS** (~1GB), 전사 org/골격/PROGRESS = 일반 추적, 렌더 PNG = ignore(재생성).
  - 로컬 init 커밋 완료. **remote 호스팅 미정** (oracle forge / work forge / 기타 — 힣이 결정).
  - push 시 전역 pre-push 안전훅이 LFS 업로드를 위임하는지 검증 필요.
- forgebot 자동화 루프: **보류** (구조는 이슈화 가능하나 지금은 안 함). git 버전관리만 유지.
- 도구(scanpdf2org 등)는 공개 memex-kb 유지. 두 리포 나란히 클론해 사용.

### 진행

- ✅ `scanpdf/` 별도 리포화 + LFS (저작권 보호, memex-kb는 scanpdf/ 전체 무시)
- ✅ flake.nix에 pymupdf/pillow 추가
- ✅ 렌더 스크립트 + 전사 프롬프트 + run.sh 명령
- ✅ **파일럿**: 물질,생명,인간 1장 1절 전사 완료 (`scanpdf/work/물질생명인간/org/01장-01절.org`)

### 책별 진행 (목표: 책마다 1장)

| 책 | 1장 범위 (물리쪽) | 인쇄쪽 | offset | hi-res | 상태 |
|----|------------------|--------|--------|--------|------|
| 물질,생명,인간 | 11–16 (1절) | 13–18 | +2 | ✅ | 1절 전사 ✅ / 2~5절 ⬜ |
| 물리학강의 (최무영) | 24–55 (1강) | 26–57 | +2 | ✅ 32쪽 | SEED ✅ / 물리 26–55 grind ⬜ |
| 자연철학강의 (장회익) | 34–77 (제1장) | 34–77 | 0 | ✅ 44쪽 | SEED ✅ / 물리 38–77 grind ⬜ |
| 물리의정석 (서스킨드) | 12–31 (1강) | 15–36 | 인쇄=물리+4 | ✅ 20쪽 | SEED ✅ / 물리 14–31 grind ⬜ |
| 인공지능시대 (이기상?) | 15–48 (1장) | 17–50 | 인쇄=물리+2 | ✅ 34쪽 | SEED ✅ / 물리 18–48 grind ⬜ |

5권 모두 1장 범위 확정 + hi-res 렌더 + 도입부 SEED + PROGRESS 완료.
각 책 `scanpdf/work/<책>/{PROGRESS.md, org/*-seed.org}` 에 페이지맵·grind 지침·CHECK 정리.
→ **분신(GPT-5.4)에게 PROGRESS + seed 주면 책별로 쭉 grind 가능.**

**★ 마스터 골격 완료** — 5권 모두 전체 목차를 `scanpdf/work/<책>/org/<책>.org`에
헤딩(`*` 책 / `**` 장·부 / `***` 절·소절 / `****` 항목) + **인쇄 페이지번호**로 박아둠.
내용 없이 골격만 — 분신은 "이 소절 = 인쇄 NN쪽" 보고 해당 페이지를 채우기만 하면 됨.
- 페이지번호 완비: 물질생명인간(전 절), 물리의정석(전 강), 자연철학(전 장), 인공지능시대(전 장)
- 물리학강의: 강-level 일부만 확인됨(1·2·4·5·6·13·14·21~27강), 나머지는 부 범위 내 탐색
- 책 제목 확정: 인공지능시대 → 《인공지능시대와 철학의 쓸모》(이기상 추정)
- offset: 물질생명인간 −2 / 물리학강의 −2 / 자연철학 0 / 물리의정석 −4 / 인공지능시대 −2 (물리=인쇄+offset)

### 다음 한 걸음

1. **org→epub 명세 확정** (아래 ★ 섹션 — 이게 핵심 선행작업)
2. **분신 grind** (책별, SEED 패턴대로 이어 전사):
   - 물리학강의 물리 26–55 / 자연철학 물리 38–77 / 물리의정석 물리 14–31 / 인공지능시대 물리 18–48
   - 물질,생명,인간 1장 2~5절 물리 17–74
3. 인공지능시대 책 제목/저자 정확화 (표지 물리 1~6)
4. 미해소 `[[CHECK]]` 마커 사람 검수

## ★ org → EPUB : 이 리포 플로우의 엑기스 (핵심 선행작업)

이 리포에는 `epub2org/`(epub→org, PATTERNS.org에 정착된 규칙)는 있는데
**역방향 `org2epub`이 없다.** 잘돼서가 아니라 그동안 할 일이 없었을 뿐.
scanpdf2org가 org를 쏟아내므로, 이제 **org→epub을 우리가 원하는 형식으로
정확히** 만들어야 한다. 이걸 잘 명세해두면 GPT-5.4·Sonnet 누가 돌려도 같은
형식이 나온다. → 이 리포의 전체 플로우 엑기스.

### 확정할 명세 (SSOT가 될 것 — `org2epub/SPEC.org`에 박을 예정)

**1) org 헤딩 레벨 (책 구조 = epub 챕터 분할 기준)**
- `*` = 장/강 (epub 챕터 분할 단위) / `**` = 절 / `***` = 소절
- ※ `epub2org/PATTERNS.org`는 `**`=챕터였음(상위 제목 있던 구조). 우리는 `*`=챕터로 통일.
  현 scanpdf2org 시드/프롬프트는 이미 `*`=장 규칙 → 일치. 그대로 간다.
- 책 1권 = 장별 org 합본 + 상단 메타데이터 블록.

**2) 수식 LaTeX syntax (★ 정확히 고정해야 일관 출력)**
- 인라인: `\( ... \)`  / 별행: `\[ ... \]`  (epub2org S1/S2와 동일, 시드도 이걸 씀)
- epub에서 수식 렌더: ox-epub→MathML 또는 MathJax. 듣기(TTS)엔 무의미하므로
  "데이터/읽기용 보존"이 1차 목적. epub 렌더 방식은 도구 선정 후 결정.

**3) 메타데이터 블록 (ox-epub 필수)**
- `#+title:` `#+author:` `#+language: ko` `#+date:` 그리고 ox-epub용
  `#+epub_*` 옵션(표지, UUID 등). 책별 yaml/org 헤더 템플릿화.

**4) 그림 처리**
- 현재 스캔본은 그림 이미지 미추출 → `[[그림 N: 설명]]` 텍스트 placeholder.
- 결정 필요: PDF에서 그림 이미지 추출해 삽입할지(보존판) vs placeholder 유지(듣기판).
  듣기 목적이면 placeholder로 충분.

### 도구 선택 (프로토타입으로 결정)

- **ox-epub** (Emacs org→epub3 네이티브) — org 구조·메타데이터 그대로, MathML 가능.
  Emacs/org 중심 환경에 자연스러움. emacs skill로 batch export 가능. ← 1순위 후보
- **pandoc** org→epub — 형님 "pandoc 거의 안 씀"이지만 fallback 후보.
- 둘 중 하나로 시드 org 1장을 실제 epub으로 뽑아 비교 → 도구 확정.

### 만들 것

- `org2epub/` 디렉토리 (epub2org 대칭): `SPEC.org`(위 명세), 변환 스크립트/elisp,
  `README.org`, `run.sh org2epub-build <ORG>` 명령.
- 완성 시 scanpdf2org → org2epub 풀 파이프라인: 스캔 PDF → org → EPUB(듣기).

### ⚠️ 주의

- **각 책 1장에 독자 연필 낙서 있음** (1장만 정독). 손글씨 무시, 인쇄 활자만 전사.
- 물리 페이지 ≠ 인쇄 쪽번호. 책마다 오프셋 다름 (물질생명인간 = +2).

## 별건 (이번 세션에서 발견)

- **repo 전체 정리 예정** — 구성이 지저분함. scanpdf2org 작업 끝난 뒤 진행.
  구체적인 정리 범위/방향은 그때 힣이 알려준다. (지금은 skip)
- `epub2org/AGENTS.md` 삭제함 (stale beads 워크플로 강제 — 불필요 문서).
  beads는 이제 안 씀(이번 세션에 `.beads/`도 삭제).

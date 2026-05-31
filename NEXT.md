# NEXT — memex-kb

휘발성 후속 작업 메모. 영속 사실은 AGENTS.md / docs / commit으로 옮긴다.

## 지금 작업 중: scanpdf2org (스캔 한글 책 → org)

전자책 없는 한글 책 5권을 스캔(`scanpdf/`, gitignore). vision 전사로 org화 →
EPUB(듣기). **전통 OCR 안 씀** — 에이전트가 페이지 이미지를 직접 읽어 옮긴다.

- 파이프라인 문서: `scanpdf2org/README.org`
- 전사 규칙(SSOT): `scanpdf2org/prompts/page-to-org.md`
- 렌더: `./run.sh scanpdf2org-render <PDF> <OUT> [PAGES] [DPI]`

### 진행

- ✅ `scanpdf/` gitignore 설정 (저작권 보호 — PDF/이미지/org 본문 커밋 금지)
- ✅ flake.nix에 pymupdf/pillow 추가
- ✅ 렌더 스크립트 + 전사 프롬프트 + run.sh 명령
- ✅ **파일럿**: 물질,생명,인간 1장 1절 전사 완료 (`scanpdf/work/물질생명인간/org/01장-01절.org`)

### 다음 한 걸음

1. 물질,생명,인간 **1장 나머지 절(2~5절, 인쇄 19~76)** 이어서 전사
   - `./run.sh scanpdf2org-render scanpdf/물질생명인간001.pdf scanpdf/work/물질생명인간/pages_hi 17-74 250`
   - 진행 상태: `scanpdf/work/물질생명인간/PROGRESS.md`
2. 나머지 4권도 각각 목차 렌더 → 1장 범위 확정 → 전사 (목표: 책마다 1장)
3. 미해소 `[[CHECK]]` 마커 사람 검수
4. org → EPUB 변환 경로 결정 (기존 epub2org/html2epub 역방향 활용 검토)

### ⚠️ 주의

- **각 책 1장에 독자 연필 낙서 있음** (1장만 정독). 손글씨 무시, 인쇄 활자만 전사.
- 물리 페이지 ≠ 인쇄 쪽번호. 책마다 오프셋 다름 (물질생명인간 = +2).

## 별건 (이번 세션에서 발견)

- **repo 전체 정리 예정** — 구성이 지저분함. scanpdf2org 작업 끝난 뒤 진행.
  구체적인 정리 범위/방향은 그때 힣이 알려준다. (지금은 skip)
- `epub2org/AGENTS.md`가 stale — beads(`br`) 워크플로 강제하는데 beads는 이제
  안 씀(이번 세션에 `.beads/` 삭제). 위 repo 정리 때 함께 처리.

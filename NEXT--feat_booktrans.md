# NEXT — booktrans upstream-first 레인 (`feat/booktrans`)

> disposable branch handoff. 브랜치 머지 전 삭제한다.
> 번역 실험의 현재 SSOT는 upstream ignored artifact와 아래 receipt다. 완성품을 미리 만들지 않는다.

# RAIL — 현재 좌표

- [x] **1. 원점 복귀 + Vendor-0** — memex 구현/vendor 전부 제거, upstream `5d07e73` 그대로 작은 실물 왕복
- [x] **2. Vendor-1 실제 책 1-chunk** — *Why Machines Learn* 변환 + fresh Opus `chunk0008` 번역 + 혼합 EPUB
- [ ] **3. fresh Sonnet으로 Chapter 1 번역** ← **CURRENT: 1-chunk pilot → 2 → 4**
- [ ] **4. Chapter 1 EPUB/TTS 실청취** — 완벽한 수식보다 실제로 들리는 번역을 먼저 판정
- [ ] **5. 그 뒤에만 경계 결정** — upstream 직접 사용 / 출력만 Org·ox-epub / 전체 fork

현재 좌표: 1–2 완료 → 3 진행 대기 → 4–5 보류

# NOW

- **Stem**: upstream 번역도구를 고치지 않고 Chapter 1을 한국어로 끝까지 옮겨 실제로 듣는다.
- **Current**: memex-kb에는 booktrans 코드가 없고, upstream repo도 코드 변경 0. 이 branch는 handoff만 추적한다.
- **Next**:
  1. fresh Claude Code **`sonnet`** 한 명이 `chunk0009.md`만 번역한다.
  2. Opus가 만든 `output_chunk0008.md`와 문체·용어·수식 연속성을 PM이 검수한다.
  3. PASS면 fresh Sonnet wave **2 chunks → barrier/merge**, 이어서 **4 chunks → barrier/merge**.
     남은 Chapter 1은 `chunk0007`, `chunk0009`–`chunk0014` 총 7개라 `1 → 2 → 4`로 닫힌다.
- **Blocker**: 없음. 다음 세션에서 pilot을 시작하면 된다.
- **Read**:
  - upstream 계약: `~/repos/3rd/translate-book/AGENTS.md`, `SKILL.md`
  - 작은 baseline receipt: `~/repos/3rd/translate-book/tests/.artifacts/vendor0-ko/VENDOR0.md`
  - 실제 책 receipt: `~/repos/3rd/translate-book/tests/.artifacts/why-machines-vendor1/VENDOR1.md`
  - workspace: `~/repos/3rd/translate-book/tests/.artifacts/why-machines-vendor1/Why_Machines_Learn_temp/`
  - Opus 기준 번역: 위 workspace의 `chunk0008.md`, `output_chunk0008.md`, `output_chunk0008.meta.json`, `glossary.json`
- **Verify (Sonnet pilot)**:
  - upstream `SKILL.md` 그대로, 1 chunk = 1 fresh context, 코드·문서 수정 0
  - heading/image/blockquote/수식/아래첨자 보존; 실제 빈 링크 `[]`는 삭제하되 이미지 빈 alt `![](...)`는 보존
  - glossary table과 neighbor context를 upstream CLI로 주입; meta v1 validator PASS
  - output을 record한 뒤 `prepare-merge → PM decision → apply-merge`; batch barrier 전에 다음 wave 금지
- **Do not touch**:
  - memex 안에 vendor/capture/inventory/enrichment 프레임워크를 다시 만들지 않는다
  - Chapter 1 실청취 전 fork·Org SSOT·수식 OCR·EPUB 오류 수정으로 우회하지 않는다
  - passthrough output 206개를 실제 번역으로 보고하지 않는다
  - nested fan-out, commit, push 금지(별도 명시 요청 전)

# RECENT

- [2026-08-10] 과도한 `a2edcbc`를 버리고 branch를 `099ae35`로 reset. `booktrans/`와 `out/booktrans/` 삭제.
- [2026-08-10] upstream CI-equivalent **226 PASS**. Vendor-0에서 실제 한글 chunk·glossary/meta·EPUB 경로 확인.
- [2026-08-10] 실제 EPUB SHA-256 `2c3bddb70d918a349bcb7f544f98dc85fb4a4e5aa51dd794855868bcf1169d2e` 불변.
- [2026-08-10] upstream 변환: 207 chunks, 이미지 asset 478. Chapter 1=`0007`–`0014`, 8 chunks/31,405B/이미지 12.
- [2026-08-10] fresh Opus `20260810T172541-68f57e`의 `chunk0008` 번역 품질 승인. 용어표 14/14, meta PASS.
- [2026-08-10] 혼합 EPUB은 한국어 본문+표 이미지를 담고 열리지만 EPUBCheck 52 errors/1 warning, image 477/478.
  **고치지 않았다.** 먼저 Chapter 1을 듣고 출력단 교체 필요성을 판정한다.

# NEXT — memex-kb

휘발성 후속 작업 메모. 영속 사실은 AGENTS.md / docs / 커밋 / `.claude/skills/scanbook/SKILL.md` /
per-book `mineru/README.md` 로 옮긴다. 이 파일은 "지금 다음 한 걸음"만 가볍게 유지한다.

> scanbook 작업은 항상 **scanbook 스킬 먼저 읽기**. 원격 gpu2i 서버·교정전략·봉합판단·함정이 거기 있다.

---

## scanbook 진행 현황 — 5권

파이프라인: PDF → ①MinerU(gpu2i 원격) → ②`mineru2org.py`(구조복원+교정+감독형 봉합) → ③ox-epub. 전부 결정론적(org 바이트 동일 재현).

| 책 | 구조 타입 | 봉합 | EPUB | 텍스트 교정 |
|---|---|---|---|---|
| 물질생명인간 | chapters 2단(장/절) | page+samepage 167 | 0/0/0 240KB | ✅ 앎 safe_regex 등 |
| 물리학강의 | 3level(부/강/소절) | page+samepage 430(skip규칙) | 0/0/0 9.9MB | ✅ literal 282 |
| 자연철학강의 | chapsec(장/고정마커절/소절) | **page만**(운문/한문 오염→samepage 제외) 187 | 0/0/0 6.4MB | ✅ literal 159 |
| 물리의정석 | **강+막간(부 없음)** | page+samepage 136(skip규칙) | 0/0/0 4.1MB | ⚠️ **0건(v1 RAW)** |
| 인공지능시대 | 미착수 | — | — | — |

엔진 핵심(SSOT = `mineru2org.py`):
- 구조 핸들러 3종(chapters 2단 / 3level / chapsec) + chapters 일반규칙(seen_chap 중복장→소절, 강번호줄 드롭)으로 4종 구조 커버. **새 책은 핸들러 안 만들고 config+소규모 일반규칙으로** (GLG 방침: 완전자동화 안 노림, TOC 정본 알므로 정렬은 쉬움).
- 감독형 봉합 `_seam_for`: digit-head/caption-head/pageref-tail/enum-circled skip + josa/fusion/mid-어절 seam. **samepage_break는 책별 판단** — 자유형 오염(운문/한문)=카테고리 드롭, 규칙형 오염(캡션/교차참조/박스제목)=skip 규칙 추가. 항상 dry-run `.merges.log` 통독 후 결정.
- 새 skip/구조 규칙은 공통 SSOT라 **추가 후 커밋된 책 전부 회귀 0 확인 의무**.

---

## 다음 한 걸음

### 물리의정석 2차 (content-first 후속 — v1은 EPUB 0/0/0이나 텍스트 RAW)
- [ ] **텍스트 교정 패스**: candidates 547건은 대부분 의도표기 오탐(H/T 동전상태·σ·n 물리변수). 진짜 깨짐만 골라 literal — `Most지→많지`, `쏸→썼을`, `써으니까→썼으니까`, `옵긴이→옮긴이`, `끊여→끓여`, `쇛조각`, `꺼어`. candidate_regex가 너무 넓어 오탐多 → 좁히기.
- [ ] **서문/입문자는 도움이 필요해** 추가(v1 컷): body_start→`최소한의 이론`, 서문 2항 chapters 추가, `차례` TOC 테이블 드롭.
- [ ] back matter 봉합 노이즈(찾아보기 색인 `가++각속도`, 판권 `지은이++옵긴이`) — detector body_bounds에서 색인 제외.
- [ ] (저우선) 인라인 수식의 별행화(eq_interrupt) — 현 렌더 정상, 시각적 들여쓰기만.

### 다음 책
- [ ] **인공지능시대와 철학의 쓸모** — scanbook New book checklist. PDF: `scanpdf/인공지능시대001.pdf`.

### 백로그
- [ ] (선택) 봉합 워크플로 스킬화 — 리스트→봉합→로그검수→환류 루프.
- [ ] (선택) `scanbook/eval/` — 6종 샘플셋 + 총교정비용 점수표(MinerU vs DeepSeek-OCR 공정비교).
- [ ] DeepSeek-OCR 클라 개선(필요시): `## ##` strip, bbox 캘리브레이션, 띄어쓰기 붕괴 탐지.

---

## 인프라 메모

- **flake.nix nix-ld 자립**(2026-06-04): MinerU 클라(numpy/opencv manylinux wheel)가 `nix-ld.libraries=[libcap]`만인 호스트에서 `libstdc++/libz` 부재로 실패 → flake shellHook이 `MINERU_LD_LIBRARY_PATH = makeLibraryPath [stdenv.cc.cc.lib zlib] + nix-ld path` export, run.sh mineru 명령을 nix develop 안에서 그 변수로 실행. 호스트 nix-ld 설정 무관 자립.
- **원격 서버**(nixos 담당): MinerU = gpu2i tmux `mineru-vllm` :30000. DeepSeek-OCR = gpu1i tmux `deepseek-ocr` :8000. `run.sh mineru-parse`/`deepseek-parse` 가 터널 자동.
- **빌드**: `nix develop --command ./run.sh org2epub-build` (zip/unzip 필요, flake에 포함). ltximg는 빌드캐시(gitignore) — RSC-007 시 `rm -rf ltximg *.epub` 후 재빌드.

---

## 은퇴/기록

- vision/Opus 전체전사 은퇴(oracle로만 비교). tesseract/ocrmypdf, marker/surya 제거. 살아남은 QA = `diff_review.py`(`./run.sh diff-review`, 엔진무관).
- ox-epub는 `~/repos/gh/ox-epub` 포크(EPUB3 네이티브+headless). memex-kb 내부 후처리(`epub_upgrade.py`/`org2epub.el`) 재도입 금지. SVG 수식 대문짝 버그 = ox-epub CSS `max-width:90%;height:auto`로 해결됨.
- scanpdf = nested private repo, remote `work` Forgejo `glg-bot/scanpdf`.

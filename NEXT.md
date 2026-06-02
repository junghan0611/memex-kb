# NEXT — memex-kb

휘발성 후속 작업 메모. 영속 사실은 AGENTS.md / docs / commit으로 옮긴다.

---

## ★ 다음 작업 — 품질 가드 전략 확보됨, 적용 단계 (2026-06-02 갱신)

**smoke 1 완료 + 전략 도구화 완료.** 전략: `marker/STRATEGY.md`, 근거: `marker/SMOKE-RESULTS.md`.

전략 한 줄: **marker(충실 OCR) ↔ vision(유창 구조)를 자동 diff로 충돌점만 추출,
LLM은 페이지 재독 없이 충돌점만 이미지로 판정**(`diff_review`). 양쪽 약점
(vision 환각/정규화 + marker 글자오독)을 동시에 잡는다 = "덜 수고 + 품질 가드".

검증된 근거(2장 2절 6쪽, 30 충돌점 자동추출):

- marker 정답/vision 오류: 93쪽(89 오기), 라세(라셰 정규화), 초래할(결정짓는), 필연적으로(구절환각), 대해(누락), 되냐고(추가) …
- vision 정답/marker 오류(반증): 버금가는(marker 가→기 오독).
- → **어느 엔진도 절대 권위 아님. 양방향 판정 필수.**

구축물(이번 세션):

- `./run.sh marker-pdf <pdf>` — 충실 OCR 전사. NixOS env 우회(PYTHONPATH 제거 + nix-ld libstdc++) 내장.
- `./run.sh marker-diff <md> <org>` — 충돌점 추출(`marker/scripts/diff_review.py`, stdlib).
- `marker/` uv 프로젝트(pyproject+`uv.lock`). 설치 `nix develop --command uv sync --directory marker`.

다음 (적용):

1. **Mode B 즉시** — 1~4장 vision org를 `marker-pdf`+`marker-diff`로 QA, 충돌점 이미지 판정해 환각/탈자 정정. 가장 빠른 이득.
2. **수식/표 smoke** — 산문만 검증됨. 4장/`물리의정석`으로 marker LaTeX·표 평가(Mode A 관문).
3. **marker 본격 전사는 GPU/서버 오버나잇** — CPU ~4분/쪽(261쪽 ~17h). flake portable → NUC/Oracle tmux.
4. marker 신뢰도 점수 활용한 자동 플래그 + heading/각주 구조 후처리 스크립트.

기준선/준비(유지):

- vision-only Opus 5병렬 1~4장 전사 완료. 단 환각/정규화 주의 — Mode B QA 대상.
- flake dev shell: `tesseract(eng+kor+osd)`, `ocrmypdf`, `mupdf`, `poppler-utils`, `epubcheck`, `uv`.
- `marker/`: `.venv`/`out`/`smoke` gitignore, 추적은 pyproject+lock+scripts+문서만. venv 5.1G.
- `scanpdf` private Forgejo `glg-bot/scanpdf`. work server rsync 완료.

---

## 완료/기준선 — OCR-less Opus 5병렬 전사 (2026-06-01)

### 1. 오늘 핵심 성과: OCR-less Opus 5병렬 전사 성공

《물질, 생명, 인간》 본문 **1~4장 전사 완료**.

- 작업 위치: `scanpdf/work/물질생명인간/`
- 최종 전사 파일:
  - 1장: `org/01장-01절.org` ~ `org/01장-05절.org`
  - 2장: `org/02장-01절.org` ~ `org/02장-05절.org`, `org/02장-부록1.org`, `org/02장-부록2.org`
  - 3장: `org/03장-01절.org` ~ `org/03장-05절.org`
  - 4장: `org/04장-01절.org` ~ `org/04장-05절.org`
- chunk 원본: `org/chunks/*.opus.org`
- 진행/비용/offset 기록: `scanpdf/work/물질생명인간/PROGRESS.md`
- lean 지침: `scanpdf/work/물질생명인간/AGENTS.md`

운용 패턴:

- `pi-shell-acp` + `claude-opus-4-8` 5개 분신을 `async`로 띄움.
- 같은 5개 분신을 `entwurf_resume(mode="async")`로 장별 재사용.
- 각 분신은 자기 chunk 파일만 작성. parent가 회수·경계 확인·최종 병합.
- OCR 금지. 이미지 직접 읽기 + crop/zoom만 허용.
- 결과: 1~4장 본문을 한 세션에 끝냄. 이 패턴은 재사용 가치 큼.

관련 이슈:

- pi-shell-acp 성공 사례/문서화 요청: <https://github.com/junghan0611/pi-shell-acp/issues/31>

### 2. 페이지 offset 확정

장 표지/간지 때문에 offset이 계속 바뀐다. **항상 하단 쪽번호 직접 확인**.

| 구간 | 확인된 offset |
|------|---------------|
| 1장 본문 | 인쇄 = 물리 + 2 |
| 2장 본문/부록 | 인쇄 = 물리 + 4 |
| 3장 본문 | 인쇄 = 물리 + 5 |
| 4장 본문 | 인쇄 = 물리 + 6 |

다음 지점:

- 물리 239 = 인쇄 245, `참고문헌` 시작.
- 본문 듣기용 EPUB라면 참고문헌/찾아보기는 생략 가능.

### 3. 남은 CHECK

사람 검수 후보:

- `org/01장-01절.org`: p15 어절 판독 1개
- `org/01장-03절.org`: `[[CHECK]]` 3개 + `[?]` 1개
- `org/01장-05절.org`: p57 인용/판본 대조 1개
- `org/03장-03절.org`: 슈뢰딩거 인용 경계 1개

2~4장 대부분은 최종 본문 기준 마커 0.

### 4. 다음 한 걸음

1. 참고문헌/찾아보기 전사 여부 결정.
   - 듣기용 EPUB 목적이면 생략해도 됨.
2. `org/물질생명인간.org` 마스터에 1~4장 본문을 병합할지, 개별 파일 include/link 방식으로 둘지 결정.
3. `[[CHECK]]` 사람 검수.
4. 실제 EPUB 빌드:
   - `./run.sh org2epub-build <book.org>`로 검증한다. 이 명령은 memex-kb 내부 후처리 없이 `~/repos/gh/ox-epub/ox-epub.el`을 직접 load한다.
5. scanpdf nested repo는 `7c2297a feat(transcription): add material life human chapters 1-4`로 커밋 완료. 푸시는 아직 하지 않음.

### 5. 현재 git / 서버 상태

- `memex-kb` GitHub main: `f0f248c feat(ocr): add reproducible PDF toolchain` push 완료.
- `scanpdf` Forgejo work main: `9d293df feat(epub): add material life human draft` push 완료.
- `scanpdf/`는 nested private repo이며 remote는 `work` Forgejo `glg-bot/scanpdf`.
- work server의 같은 repo 경로에 `scanpdf` 포함 rsync 완료.

---

## org → EPUB 후속

`~/repos/gh/ox-epub` 포크가 EPUB3 네이티브 export와 headless 표지 처리를 흡수했다. 따라서 memex-kb에는 별도 `org2epub/` 구현을 두지 않는다.

현재 정책:

- `./run.sh org2epub-build <book.org>`는 thin wrapper다.
- wrapper는 `OX_EPUB_REPO`(기본 `~/repos/gh/ox-epub`)의 `ox-epub.el`을 직접 load한다.
- `epub_upgrade.py`, `org2epub.el` 같은 memex-kb 내부 후처리 레이어는 재도입하지 않는다.
- 《물질, 생명, 인간》 1~4장 마스터 org → EPUB 빌드 완료. `epubcheck` 0 errors / 0 warnings.

남은 책 단위 결정:

- 그림 처리: PDF 그림 추출 삽입 vs placeholder.
- CSS 조판 톤.
- 대용량 책 장별 xhtml 분할 필요성.

---

## OCR / marker 툴체인 — 정리됨 (2026-06-02)

해결된 결정(상단 ★ 섹션이 현재 상태):

- **tesseract/ocrmypdf 제거.** 한글 스캔 OCR 품질 사용 불가 → flake/`run.sh ocr-pdf`에서 삭제.
  OCR 경로는 marker(surya)로 일원화. (nixos-config 전역 설치분은 별개로 남아있음 — memex-kb는 더이상 선언 안 함)
- **marker는 `uv` venv/lock으로 pin** (`marker/` 디렉토리, 별도 flake input 아님). 결정 완료.
- `nougat`은 당장 안 씀. marker 우선.
- marker CPU smoke 완료(thinkpad ~4분/쪽). run.sh `marker-pdf`/`marker-diff` 추가됨.
- 배치/책 단위는 `tmux` + 서버 오버나잇.

남은 것은 상단 ★ "다음(적용)" 참조 — 수식 smoke, Org 구조 후처리, GPU 재측정.

---

## 다른 책 scanpdf2org

이번 실험으로 “Opus 병렬팀” 패턴이 검증됨. 다른 책도 같은 방식으로 갈 수 있다.

대상 후보:

- `물리학강의`
- `자연철학강의`
- `물리의정석`
- `인공지능시대와 철학의 쓸모`

각 책은 기존 `scanpdf/work/<책>/PROGRESS.md`와 seed/org 골격을 보고 시작.

---

## 별건

- repo 전체 정리 예정 — scanpdf2org 큰 흐름이 끝난 뒤 진행.
- `epub2org/AGENTS.md`와 `.beads/` 삭제 이력 있음. beads는 이제 안 씀.

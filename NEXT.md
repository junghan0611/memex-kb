# NEXT — memex-kb

휘발성 후속 작업 메모. 영속 사실은 AGENTS.md / docs / commit으로 옮긴다.

---

## ★ 다음 작업 — OCR + marker + 에이전트 파이프라인 검증 (2026-06-02)

목표: 《물질, 생명, 인간》을 기준으로 **OCR / marker / 에이전트 vision**을 엮어
동일한 EPUB급 결과물을 더 낮은 비용·시간으로 만들 수 있는지 검증한다.

현재 기준선:

- Opus vision-only 5병렬로 1~4장 전사 성공.
- `scanpdf/work/물질생명인간/org/물질생명인간-epub.epub`는 폰에서 확인한 결과 퀄리티 높음.
- 이 결과가 품질 baseline이다. marker/OCR 경로는 이 baseline 대비 비용·시간·수정량을 비교한다.

검증 가설:

- OCR/marker가 초안을 제공하면 에이전트가 직접 읽어야 할 분량이 줄어든다.
- 최종 품질이 vision-only baseline에 근접하면서 wall time/API cost가 줄면 성공.
- 성공하면 다른 책(`물리학강의`, `자연철학강의`, `물리의정석`, `인공지능시대와 철학의 쓸모`)로 확장한다.

준비 완료:

- `memex-kb` flake는 `nixos-config`와 nixpkgs lock을 맞춤(`0c88e1f...`) — store path 중복 최소화.
- dev shell 도구: `tesseract(eng+kor+osd)`, `ocrmypdf`, `mupdf/mutool`, `poppler-utils`, `epubcheck`, `uv`.
- `./run.sh ocr-pdf <INPUT.pdf> [OUTPUT.pdf] [LANGS]` 추가.
- `nougat`은 당장 넣지 않음. marker 우선.
- `scanpdf` private Forgejo repo: work Forgejo `glg-bot/scanpdf`.
- work server의 같은 repo 경로에 `scanpdf` 포함 rsync 완료. 서버에서 바로 이어갈 수 있음.

다음 순서:

1. marker 설치 방식 결정: 우선 `uv` lock/venv 방식으로 작은 smoke를 시도한다.
2. 《물질, 생명, 인간》의 짧은 범위(예: 2장 2절 또는 4장 일부)를 marker로 Markdown+LaTeX 변환.
3. 같은 범위에 `ocr-pdf`/tesseract searchable text를 생성해 marker 결과와 비교.
4. 에이전트가 marker/OCR 출력 + page image를 대조해 Org 정규화.
5. 기존 vision-only 전사와 비교:
   - 누락/오독/수식·표 처리
   - 사람/에이전트 수정량
   - wall time
   - API cost
6. 통과하면 `marker → Org 정규화 → ox-epub build` 명령을 `run.sh`에 추가한다.

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

## OCR / marker 툴체인 후속

nixos-config에는 편의상 PDF/EPUB/OCR 도구가 전역 설치되어 있지만, memex-kb도
자기 flake에서 재현 가능해야 한다. 현재 반영한 방향:

- flake에 `mupdf`, `poppler-utils`, `tesseract(eng+kor+osd)`, `ocrmypdf`, `epubcheck`, `uv` 추가.
- `ocrmypdf`는 override된 `tesseractKor`를 공유해 전체 언어팩 중복을 피한다.
- `./run.sh ocr-pdf <INPUT.pdf> [OUTPUT.pdf] [LANGS]` 유지: OCR은 전사 대체가 아니라 searchable PDF·검증·에이전트 부담 절감용.
- `tesseract equ`는 품질 낮아 제외. 수식/표 책은 우선 marker 계열로 보낸다.

다음 결정:

1. `marker-pdf`를 uv-managed venv/lockfile로 pin할지, 별도 flake input으로 감쌀지 결정.
   - `uv`는 시스템에도 있지만 marker lock runner로 flake에 둘 수 있다. nixos-config와 lock을 맞추면 store path 중복은 없다.
2. `nougat`은 당장 넣지 않는다. marker 우선.
3. marker CPU 추론 성능을 thinkpad에서 작은 PDF로 smoke test.
4. marker output → Org 정규화 → ox-epub 빌드까지 연결하는 명령을 run.sh에 추가할지 결정.
5. 배치 변환은 `tmux` 장시간 작업으로 운용.

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

# NEXT — memex-kb

휘발성 후속 작업 메모. 영속 사실은 AGENTS.md / docs / commit으로 옮긴다.

---

## ★ 퇴근 HANDOFF — 2026-06-01

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

### 5. 현재 git 상태 주의

루트 `memex-kb`에는 전부터 이어진 별도 변경이 staged 상태로 남아 있다:

- `AGENTS.md`, `README.md`, `run.sh`, `NEXT.md`
- `samples/org-to-odt/` → `org2odtdoc/` rename
- `org2epub/` 내부 구현은 제거함. EPUB 빌드는 `~/repos/gh/ox-epub` 포크를 직접 사용.

`scanpdf/`는 nested private repo이며 현재 clean. 전사 결과는 로컬 커밋 `7c2297a`에 들어갔고 푸시는 아직 하지 않음.

커밋/푸시는 GLG 판단 후 별도 진행.

---

## org → EPUB 후속

`~/repos/gh/ox-epub` 포크가 EPUB3 네이티브 export와 headless 표지 처리를 흡수했다. 따라서 memex-kb에는 별도 `org2epub/` 구현을 두지 않는다.

현재 정책:

- `./run.sh org2epub-build <book.org>`는 thin wrapper다.
- wrapper는 `OX_EPUB_REPO`(기본 `~/repos/gh/ox-epub`)의 `ox-epub.el`을 직접 load한다.
- `epub_upgrade.py`, `org2epub.el` 같은 memex-kb 내부 후처리 레이어는 재도입하지 않는다.
- 다음 검증 대상: 《물질, 생명, 인간》 1~4장 마스터 org를 만든 뒤 첫 EPUB 빌드.

남은 책 단위 결정:

- 그림 처리: PDF 그림 추출 삽입 vs placeholder.
- CSS 조판 톤.
- 대용량 책 장별 xhtml 분할 필요성.

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

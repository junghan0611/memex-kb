# NEXT — memex-kb

휘발성 후속 작업 메모. 영속 사실은 AGENTS.md / docs / commit으로 옮긴다.

---

## ★★★ 물리학강의 — 3단 계층(부/강/소절) EPUB 성공 (2026-06-02 16:20)

**두 번째 책. MinerU→org→EPUB 풀사이클 동작 + 엔진 3단 확장.**
《최무영 교수의 물리학 강의》(718쪽) → **부7/강27/소절129** → EPUB **epubcheck 0/0/0**(10MB).

### 엔진 개선 (mineru2org.py — 물질생명인간 2단 경로는 보존)

| 추가 | 내용 |
|------|------|
| `reconstruct_3level()` | 부`*`/강`**`/소절`***`. 부 제목이 본문서 비유일(소절·강 제목과 충돌) → config part↔lecture 소속 SSOT로 **첫 강 직전 부 헤딩 합성**, 부 표지(다음이 N강) 드롭. 강 표지 2형태(`# N강`+제목 / 평문 `N강`+제목, 4·6·13·18강 누락분 흡수). 강 제목은 config 권위(퀴크→쿼크 보정). 한글 없는 헤딩(영문 포스터) 강등 |
| `footnote_superscript:false` | 수식책 위첨자=지수(cm²/10²³), 각주 아님 → 변환 끔. 스퓨리어스 각주 87건→0 |
| 각주 조건부 | 정의 0개면 `* 각주` 섹션 생략 |

### 산출/설정

- 변환기: `scripts/mineru2org.py` (v3, 3단 지원). config: `scripts/corrections/물리학강의.json`.
- 산출: `scanpdf/work/물리학강의/mineru/{물리학강의-mineru.org, .epub, README.md, *.log}`.
- 재현 3-command + 구조 특이점 = `mineru/README.md`.

### 남은 단계 (text-accuracy만, 구조/EPUB는 끝)

1. **candidates.log 858건 LLM 경량 패스**: Latin 혼입(`나/ns지요`, `손 pop히는`, `바(pr)`, `von리학`) + 깨진 어절. **보오손은 책 의도 표기**(찾아보기 `보오손(boson)`) — 고치지 말 것.
2. LLM 패스 후 안전 분류는 config literal 승격 → 재변환 → EPUB 재빌드.
3. 어제 vision seed(`org/01강-seed.org`, `org/물리학강의.org` 골격)는 **은퇴**. 골격은 config 작성 재료로 소진됨. MinerU 산출이 primary.
4. 다음 책: 자연철학강의 / 물리의정석 / 인공지능시대.

---

## (이전) MinerU→후처리→org→EPUB 파이프라인 완성 (2026-06-02 15:10)

**vision/Opus 전사 완전 은퇴. 풀 사이클 동작.** `MinerU → mineru2org.py(후처리) → org(이미지/수식/각주) → ox-epub`.
물질생명인간 EPUB 생성 성공(**epubcheck 0 errors/warnings**). 다음은 물리학강의(수식 많음).

### 파이프라인 구성요소

- **변환기**: `scripts/mineru2org.py` (v2 = 구조 복원기). 책 config + content_list 구동.
- **책 config**: `scripts/corrections/물질생명인간.json` — meta(epub 헤더) + structure(장 목록) + 교정사전 + candidate.
- **QA**: `scripts/diff_review.py` (`./run.sh diff-review <a> <b>`, 엔진무관).
- **산출**: `scanpdf/work/물질생명인간/mineru/` 아래 org + epub + .changes.log + .candidates.log.

### v2 후처리가 하는 일 (GPT 리뷰 REVIEW-gpt.md 반영)

| 패스 | 내용 |
|------|------|
| 표면변환 | 이미지 `![]()`→`[[file:]]`, 블록수식 `$$`→`\[\]`, 인라인 `$$`→`\(\)`, 각주 `$^{n}$`+유니코드위첨자(⁵⁸²³)→`[fn:n]` |
| HTML정리 | `<details>`(7) 제거, mermaid 제거, `<table>`(4)→org 표 |
| **구조복원** | 장 `*`(4) / 절 `**`(번호+제목 병합) / 소절 `***` / **가짜헤딩 강등**(①②, 〈도식〉, A B C, 10건). front-matter/TOC 컷, 책머리에 보존 |
| **각주정의** | content_list `page_footnote`(20) → `* 각주` 섹션에 `[fn:n]` 정의 연결. 본문 떠도는 각주(1/2/19) 흡수. ref↔def 21 해소 |
| 교정 | 안전 regex/literal 자동, 애매는 후보 로그 |
| epub헤더 | config meta → `#+title/author/date/language/publisher/uid` + `#+options: ^:{} tex:dvisvgm` |

### 검증 (diff-review vs vision본)

- **앎 오독 163 → 37건**(교정 마무리 후). 후보 97건 로그.
- 수식 12개 LaTeX→SVG 렌더, 이미지 8개 임베드, 헤딩 계층 정연(장4/절/소절).

### 교정 전략 — 핵심 설계 결정 (영속 가치)

- **단순 정규식 전수 치환 위험**: `앉은/않은/읽은`=정상어, `앞의`=정상어, `암`=暗/癌.
  안전 규칙 = "오독 글자 + 그 글자가 동사어미로 못 받는 조사". 애매는 후보 로그 → LLM/사람.
- **범용 해법 = LLM 경량 교정 패스**(MinerU 95% 위 5% 문맥교정). vision Opus 전체전사의 경량화.
- 이 책 한정 검증: `암+조사`는 전수 검증 후 자동(暗/癌 부재). 다른 책은 그대로 쓰면 안 됨 → candidate부터.

### ✅ EPUB 검증 완료

`물질생명인간-mineru.epub` (241KB) — **epubcheck 0 fatals / 0 errors / 0 warnings**.
수식 12개 SVG 임베드, 이미지 8개, toc.ncx 정상. 구조: 장4 / 절26 / 소절62 / 가짜헤딩강등10 / 찾아보기구분자드롭.
(빌드 중 발견·수정: `\leqq`→`\leq` 비표준LaTeX, 찾아보기 자모구분자(7/□/人/⇒)가 수식-헤딩 돼 패키징 실패 → 색인 내부 헤딩 드롭.)

### 남은 단계

1. **잔여 교정 37 + 후보 97**: LLM 경량 패스(나/분신1) 또는 사람. 특히 `앉은/앞` 문맥 애매건. 각주 ref 7/11 미포착(정의는 있음).
3. **용어집**: `mineru/split/찾아보기.md`(560항목) → org 용어집. 참고문헌도 citar 재료.
4. **다음 책 물리학강의**: → **`.claude/skills/scanbook/SKILL.md` "New book checklist" 따라가면 됨.**
   같은 파이프라인. config 새로 작성(structure/meta). 수식 많음 → `text_image` 억제(GPT P4) 필요.
   새 세션은 run.sh가 아니라 **scanbook 스킬**부터 읽어라 — 원격 gpu2i 서버·교정전략·함정이 거기 있다.
5. **mineru2org.py 추가 개선**(GPT 우선순위): footnote stable id(page 기반), `text_image` 수식 격리, TOC 완전 분리.
6. **문서 기준선 유지**: 새 세션이 헷갈리지 않도록 README/BACKENDS/AGENTS/scanbook 스킬의 primary path를 항상 MinerU 기준으로 동기화한다.

> GPT 후처리 리뷰 전문: `scanpdf/work/물질생명인간/mineru/REVIEW-gpt.md` (충돌 유형표 + P0~P5 개선안 + epub blocker).

---

## (이전) 판정 완료 — MinerU 단번 vs Opus5 병렬 (2026-06-02 12:40)

**전체 261쪽 MinerU 파싱 1회 완료.** `mineru-client/out/물질생명인간001/vlm/물질생명인간001.md`
(3,612줄, 헤딩 140, **이미지 24개 추출**). 소요 **약 3분**(12:35→12:38).
분리본: `out/물질생명인간001/split/{본문1-4장,참고문헌,찾아보기}.md`.

### 효율 판정 — 역할 분담이 정답 (둘 다 단독은 아님)

| 축 | MinerU 단번 | Opus5 병렬(vision) |
|----|------------|---------------------|
| 속도 | **261쪽 3분, 전자동** | 한 세션 전체(병렬 분신 오케스트레이션) |
| 커버리지 | **본문+참고문헌+찾아보기+이미지24** | 1~4장 본문만 |
| 본문 문자 정확도 | △ — 핵심어 `앎` 광범위 오독 | **○ — `앎` 정확** |

→ **결론: Opus5 병렬은 비효율 → 은퇴.** 단, MinerU 단독도 `앎` 문제로 본문 그대로 못 씀.
**역할 분담**:
- **1~4장 본문 → vision본 그대로 사용** (이미 정확, 재작업 불필요). diff 유사도 0.953.
- **참고문헌·찾아보기·책머리에 → MinerU 채택** (vision이 안 한 영역. 단 `앎`류 후처리 필요).
- **그림 24개 → MinerU `images/*.jpg` 사용.**
- 향후 다른 책: **MinerU 1차 + 겹받침 후처리 사전 + diff QA**. Opus 병렬 안 씀.

### ⚠️ MinerU 치명 약점 — 겹받침 `앎` 오독 (이 책 핵심어!)

겹받침 ㄻ(`앎`)을 VLM이 못 읽어 **`암/앉/않/읽/앞`으로 ~160회 오독**. 목차·헤딩·찾아보기까지 전염:
- 목차 "4장 …삶과 **암**"(←앎), 헤딩 "(1) 과학과 **않**의 틀"(←앎), 찾아보기 "객관적인 **암**·236"(←앎).
- 다른 오독: `되↔뇌`, `펴↔피`, `렸↔렀`, `착상↔작성`, `버금기는`(←버금가는), `은생명`(←온생명), `바ächt다`(깨짐).
- **그림 `<details>` 데이터표는 VLM 추정치** — 비검증, 본문 채택 금지. 그림은 `images/*.jpg` 파일만 신뢰.

### 남은 한 걸음 (힣 복귀 후)

1. **용어집 만들기** — `찾아보기.md`(560항목, 용어·쪽번호) 기반. `앎`류 받침 오독만 교정하면 골격 완성.
   참고문헌(`참고문헌.md`, 1~4장별 분류 깔끔)도 용어집/citar 재료로 합류.
2. **`앎` 후처리 사전** 만들지 결정 — 가변 오독(암/앉/않/읽)이라 단순 치환 위험(`암`=癌/暗 정상어).
   1~4장은 vision본이 정확하니, `앎` 교정은 참고문헌/찾아보기/front-matter 소수 항목만 수동이면 충분.
3. **최종 org 병합** → vision 1~4장 본문 + MinerU 참고문헌/찾아보기/이미지 → `./run.sh org2epub-build`.
4. MinerU md → org 정규화 스크립트(heading 레벨/각주/인용괄호) 만들지.

### 인프라 (의존)

- **서버(외부 의존)**: gpu2i tmux `mineru-vllm`, vllm 0.11.2, `MinerU2.5-Pro-2605-1.2B`, port 30000, served `mineru`. nixos 담당 영역. 영구화(systemd) 여부 미정.
- 클라이언트(memex-kb): `./run.sh mineru-setup`/`mineru-parse` 완비. thinkpad는 SSH 터널(자동).
- 클러스터: gpu2i 기존 `default` 채팅모델 내리고 MinerU로 swap함(nixos담당). gpu3i는 임베딩 튜닝용(vllm off).

---

## 품질 가드 도구 — diff-review만 유지

핵심: **어느 엔진도 절대 권위 아님 → diff로 충돌점만 LLM/사람이 이미지 판정**.
MinerU 시대에도 `scripts/diff_review.py`가 QA 도구로 살아남았다.

- 현재 명령: `./run.sh diff-review <a.md|org> <b.md|org>`.
- marker/surya OCR 명령(`marker-pdf`, `marker-diff`)은 memex-kb에서 은퇴했다. 새 세션은 이 이름을 쓰지 말 것.
- 이미 존재하는 vision 전사본은 gold/oracle로 비교할 수 있지만, 새 책 primary는 MinerU다.

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

## 은퇴한 OCR / vision 경로 — 역사 기록

해결된 결정(상단 ★ 섹션이 현재 상태):

- **tesseract/ocrmypdf 제거.** 한글 스캔 OCR 품질 사용 불가 → flake/`run.sh ocr-pdf`에서 삭제.
- **marker/surya OCR 제거.** `marker-pdf`, `marker-diff` 명령은 더 이상 현재 작업 경로가 아니다. 살아남은 것은 엔진 무관 `scripts/diff_review.py` / `./run.sh diff-review`뿐.
- **Opus 병렬 vision 전체전사 은퇴.** 이미 만든 vision본은 oracle로 비교할 수 있지만, 새 책은 MinerU 1차 + config + LLM 경량 교정으로 간다.

---

## 다른 책 — scanbook 경로로 시작

대상 후보:

- `물리학강의` — 다음 1순위. 수식 많음 → `text_image` 억제/격리 필요.
- `자연철학강의`
- `물리의정석`
- `인공지능시대와 철학의 쓸모`

새 책은 기존 `scanpdf2org`/Opus 패턴이 아니라 **`.claude/skills/scanbook/SKILL.md` New book checklist**로 시작한다.

---

## 별건

- repo 전체 정리 예정 — MinerU/scanbook 큰 흐름이 안정된 뒤 진행.
- `epub2org/AGENTS.md`와 `.beads/` 삭제 이력 있음. beads는 이제 안 씀.

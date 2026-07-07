# NEXT — memex-kb

휘발성 후속 작업 메모. 영속 사실은 AGENTS.md / docs / 커밋 / `.claude/skills/scanbook/SKILL.md` /
per-book `mineru/README.md` 로 옮긴다. 이 파일은 "지금 다음 한 걸음"만 가볍게 유지한다.

> scanbook 작업은 항상 **scanbook 스킬 먼저 읽기**. 원격 gpu2i 서버·교정전략·봉합판단·함정이 거기 있다.

---

## 🆕 작업축 — Anthropic HTML 논문 → Org 변환 로직 + 스킬 (2026-07-07 착수)

**무엇**: Anthropic **Distill 스타일 HTML 공개논문**을 **org로 재현가능하게 담는** 변환 로직 + 에이전트용 스킬. 첫 표본 = **J-space 논문**(『Verbalizable Representations Form a Global Workspace in Language Models』, `transformer-circuits.pub/2026/workspace/index.html`, 2026-07-06). memex-kb 문서 변환 도구축의 신규 케이스.

**왜(GLG)**: 논문을 **PDF로 올리면 활용이 안 된다.** 이 논문은 **HTML**(PDF 아님) → 재활용 가능 = "논문은 이렇게 써야 한다"의 실증. 목표는 **왕복**: HTML 논문 → org(캡처) + **org → HTML 역변환**(GLG가 org로 논문 쓰면 그대로 웹으로 내보내기). **문서 변환이 본질, 논문 정독이 목적 아님.**

### 원칙 (범위·도구·재현성) — 다음 세션이 지킬 것
- **⚠️ 범위 고정 — Anthropic HTML 공개논문에만 집중.** 범용 HTML→org로 넓히면 지금 커버 못 하고 산으로 간다(GLG). transformer-circuits.pub Distill 계열 한 종만 제대로.
- **조합 도구.** pandoc은 **일부만**(LLM 이전 도구). 골격 추출에만 쓰고, 수식·구조 판단·위젯 대체 서술은 **LLM + 커스텀 로직 조합**. "pandoc HTML→org 한 방"이 아니다.
- **재현가능성이 산출물.** 논문 1개 제대로 가져오는 과정에서 **필요한 모든 것(도구 조합·규칙·수동 판단)을 재현가능하게 기록** → 그게 곧 스킬 재료.

### 소스 세트
- 논문 HTML: `https://transformer-circuits.pub/2026/workspace/index.html`
- 코드 repo: `anthropics/jacobian-lens` → GLG fork `junghan0611/jacobian-lens` 클론 `~/repos/gh/jacobian-lens` (`jlens/`, `data/`, `assets/`, `walkthrough.ipynb`, `README.md`). "jlens = Jacobian lens" 레퍼런스 구현.
- 해설본은 **별개 축** — 소넷이 저널 날것 `20260706` 해설 작업 중(memex-kb 소관 아님).

### 문서 특성 (변환 난이도 실측 2026-07-07)
~25,000단어, 8+ 섹션(Introduction/Methods/J-space as Global Workspace/구조/Alignment Auditing/Assistant's Perspective/Counterfactual Reflection Training/Discussion), Distill 스타일, **LaTeX 수식**(인라인+디스플레이), 그림 = **정적 PNG + 인터랙티브 JS 위젯**(Slice Stack viewer). → 텍스트·헤딩·정적PNG는 org로 잘 담김. **LaTeX 수식** = 최대 난관(pandoc이 KaTeX 렌더 스팬만 보면 깨짐 → 원본 소스 LaTeX 긁기). **인터랙티브 위젯** = org 불가 → 스크린샷+원문 링크 대체.

### 로드맵 (완료 정의)
1. [x] (2026-07-07) **변환 로직 완성** — `scripts/anthropic_paper_to_org.py` + `run.sh paper2org`. 조합 파이프(격리→sentinel 보호→pandoc 골격→복원→조립). J-space 실측 검수: 헤딩 76·수식 230/7·인용 155·각주 9·임베드 10·인터랙티브 84·**잔여 sentinel 0**. 결정론적(재현가능).
2. [x] (2026-07-07) **org → HTML 왕복 확인** — pandoc `-t html5 --mathjax`로 구조·수식(232)·이미지·앵커 전부 생존 = "논문 쓰기 포맷=org" 성립. (단 pandoc org리더는 `[cite:]` 못 읽음 → 프로덕션은 ox-html+org-cite. 스킬에 명시.)
3. [x] (2026-07-07) **스킬화** — `.claude/skills/anthropic-paper2org/SKILL.md`(그림 2분기·저작권·담당자 워크플로·함정). AGENTS/README 동기화, `out/anthropic-paper/` gitignore(원문 저작권=Anthropic).
4. [ ] **jacobian-lens 담당자 세팅** (GLG 몫) — 담당자가 스킬 보고 `run.sh paper2org` → org 산출물 repo에 담기. ⚠️ public `junghan0611/*` identity 훅 주의(스킬에 절차 있음).
5. **완료 상태** = memex-kb가 **변환 로직 + 에이전트 스킬 + 실제 검수(QA)** 다 소유 → **1~3 달성, 4만 GLG 대기.**

### ⭐ 후속 — org → 다중 export (web HTML + arxiv급 PDF + docx) (GLG 요청 2026-07-07)

2번(왕복)을 pandoc **증명** → 실제 **출판 파이프**로 격상. 목표: paper2org 산출 org(SSOT) 하나에서
**{web HTML, arxiv급 PDF, docx}** 가 다 나온다 = "논문 쓰기 포맷=org"의 완성.

**이미 있는 것(재사용)** — 바퀴 다시 안 만든다:
- `templates/arxiv-acm/` = org→acmart LaTeX→PDF (`build.el`, `./run.sh arxiv-build`). **`build.el`이 GLG 논문 공개
  셋업 `~/repos/gh/geworfen/docs/build.el`과 바이트 동일** = 그 트윈. texlive scheme-full+emacs는 `arxiv-acm/flake.nix`.
- pandoc(메인 flake), ox-html(emacs, org-cite citeproc).

**만들 것 = 브리지 (paper2org org → export-ready org)**:
1. [x] (2026-07-07) **arxiv급 PDF 완성** — `paper2org --acmart` 가 `<name>.acmart.org` 생성(저자 N명→acmart 프리앰블
   자동, `[cite:@k]`→natbib `\cite{}`, `\bibliography{bibliography}`, 이미지 폭맞춤, 단일컬럼 manuscript) + `scripts/paper_build.el`
   (broken-links 허용 + backtrace 억제) + `./run.sh paper2org-pdf`. **J-space 실빌드 검증: 93쪽, 인용 155개 bibtex 해석,
   수식·그림 정상**(p1 제목+저자16, p7 수식+그림 눈검수 완료).
2. [ ] **web HTML**: ox-html + org-cite citeproc(인용까지 렌더) → Distill 유사 웹. pandoc 왕복=증명 완료, ox-html=프로덕션 미착수.
3. [ ] (선택) **docx**: pandoc org→docx 또는 기존 md_to_gdocs 경로.
4. [ ] (최적화) **texlive 슬림화** — scheme-full 494MB 과잉 → scheme-basic+acmart+deps 큐레이션(의존성 누락 토끼굴 주의).

**설계 확정**: 캡처(`paper2org`)와 PDF export(`paper2org-pdf`) 명령 분리. acmart 초록 생략(J-space 초록 없음, acmart 경고만).
산출물(org/pdf/png) `out/anthropic-paper/` gitignore(Anthropic 원문). 원문의 깨진 `??` 참조 = 소스 문제(PDF에선 빈괄호).
참고: `geworfen/docs`(build.el=arxiv-acm 트윈), `run.sh arxiv-build`.

**⚠️ 함정**: `jacobian-lens`가 public `junghan0611/*` fork → 핸드오프/식별자 파일에 GLG 식별자 넣으면 **identity 훅이 커밋 차단**. 변환 산출물·담당자 메모는 memex-kb 쪽. jacobian-lens는 최종 org 산출물 담는 곳(4단계 담당자 몫).

---

## ⏸️ 작업축 — ROSSE 배포 파이프라인 (이슈 #4) — 손 배포 모드, 자동화 보류

> **현황 (2026-07-07): 손 배포 모드.** ROSSE는 지금 GLG가 각 면에 **손으로 직접** 원문을 남기고, **해설본(가든 canonical)은 org 담당자가 GLG 글을 받아 작성** 중. 완전 자동화는 번거롭고 잘될지도 불확실 → `syndicate` 도구/스킬은 **당장 안 돌린다**(v2026.6.15 구축분·스킬은 그대로 보존, 필요할 때 재개). 아래 실전 사이클·자동화 항목은 전부 **저우선 보류**.

POSSE 변형 **ROSSE**(Raw Outside, Syndicate via own Site, Everywhere). 링크드인/저널 등 바깥 면에 손가락으로 남긴 날것 원문 → org 에이전트가 가든(notes.junghanacs.com) **canonical 해설본(autholog, 원문 내장)** 으로 만듦 → memex-kb 도구+스킬로 여러 공개면에 syndicate, **모든 면이 가든 링크로 수렴**. 전략 SSOT = 가든 노트 `20250324T110312`(POSSE) / `20250328T090326`(링크드인 날것면). 완성되면 힣봇 군단 주입.

### 면별 출력 규칙 (3겹)
입력 = 가든 canonical org 1개(SSOT). 거기서 3종 포맷으로 분기 → 면별 퍼블리셔.

| 포맷 | 면 | 내용 |
|---|---|---|
| **원문형** | 링크드인·페이스북 (블로그 아님) | 원문 + 가든 링크. 딱 이대로 |
| **전문형** | 네이버블로그·티스토리 | 가든본 전체 포스팅(원문이 가든본에 내장). **인터넷 짜집기 글 절대 금지** |
| **요약형** | 스레드·트위터·블루스카이·인스타 | 한/영 요약 + 가든링크, **매체별 글자수 기준 준수** |

### 쓰기(syndicate) 경로 — 두 종족
- **API-clean (직접 발행)**:
  - **Threads** ⭐ — `threads_exporter.py` 읽기 연동 有 + 토큰 스코프에 **`threads_content_publish` 이미 보유**(`refresh_threads_token.py:210`). publish 2단계(미디어컨테이너→발행)만 추가하면 끝. **MVP 첫 수직슬라이스**.
  - **Bluesky** — AT Protocol 공개 API, 앱 패스워드. 깔끔.
  - **Facebook** — Graph API **Page** 발행(개인 프로필 발행은 Meta 차단). 토큰 작업 필요.
  - **Instagram** — Graph API, 비즈니스계정 + 이미지 필수.
  - **Twitter/X** — API 유료·제한(후순위).
- **브라우저 자동화 강제 (공식 쓰기 API 없음 → 우회가 유일경로)**:
  - **네이버 블로그** — `naver_blog_crawler.py` 읽기는 잘됨(`naver-saiculture` = 이기상 선생 블로그 org 산출물). 쓰기 공식 API 無 → `browser-tools` 스킬(CDP) / 클로드 크롬 확장.
  - **티스토리** — Open API 2024 폐쇄 → 브라우저 자동화뿐.

### 전략 전환 (2026-06-15)
완전 자동화(API 발행) 트랙 1차 보류. **개인 프로필 발행이라 페북/티스토리/네이버 모두 공식 쓰기 API가 막혔거나 없음.** → 1차 = **복붙용 면별 포맷 묶음 1파일** 생성. 사람 복붙 or 브라우저 클로드가 소비. 면별 퍼블리셔가 복붙/브라우저로 수렴 = **스킬도 면별 N개 아니라 `syndicate` 하나**.

> 구축 완료분(syndicate 스킬·생성기·포맷 3종·노트 실행 헤딩)은 v2026.6.15 CHANGELOG로 이관. 운영 SSOT = `.claude/skills/syndicate/`.

### 1차 사이클 실측 기록 (2026-06-15 완료 — 이후 손 배포로 전환)

**1차 사이클 대상 = 노트 `20251121T132839` (갷발자 — 발자와 취향의 자기표현).** 링크드인 휘갈김→가든 정리의 표본. autholog 노트가 다수라 한두 사이클 돌려 포맷 실측.
- 입력 매핑: `해설`=본문(발자/취향/pi-shell-acp/케빈켈리/세션 섹션), `원문`=`* 출근길 원문 보존` 블록, `garden_url`=https://notes.junghanacs.com/notes/20251121T132839
- ⚠️ **요약형(스레드·트위터·블루스카이)은 AI가 과하게 다듬지 말 것** — 이 노트 자체의 교훈("손구락으로 터치터치", 취향=완성도 필터 아님). 취향 보존이 본질.
- ⚠️ **전문형(네이버·티스토리)**: 원문에 `lnkd.in` 숏링크 이미 박힘 + 본문에 denote 내부링크 다수 → 가든 밖에선 안 풀림. 붙일 때 외부 URL로 풀거나 가든 링크로 수렴 처리.
- [x] (2026-06-15) 위 노트로 묶음 생성 완료. 입력 `out/syndicate/20251121T132839.input.md` → 출력 `out/syndicate/20251121T132839.input.bundle.md`, 8면 전부 통과.
  - 해설 = denote 내부링크 평문화(가든 밖 가독), 원문 = `* 출근길 원문 보존` 그대로(lnkd.in 숏링크 유지), 요약 ko/en.
  - 실측: 블루스카이 en이 가든 URL(49자) 포함 347자로 47자 초과 → en만 최소 절삭(282자)으로 해결. ko 면들은 여유 충분. 요약형은 노트 어투 보존(기계절단 X).
  - 링크드인 본문 링크 0 + 가든 링크 "↳ 첫 댓글" 분리 정상 반영. 전문형은 `─── 원문 ───` 평문 구분선.
  - **전환(2026-07-07)**: 이후 배포는 GLG **손으로 직접** + 해설본은 org 담당자 작성으로 감. 이 묶음 생성기는 필요 시 재사용(당장 정례 배포엔 안 씀).

**링크 질문 해결(2026-06-15) + 구현**: 링크드인 `lnkd.in` 숏링크는 **문제없음**(리다이렉트 래퍼, 목적지 그대로 가든, canonical 수렴 유지). 단 **본문 외부링크 = 도달 -18~60%(2026.3 후 가팔라짐)** — 90만 포스트 연구 확인. → **링크드인 `link=comment`로 구현**: 본문은 순수 날것(링크 0), 가든 링크는 묶음의 "↳ 첫 댓글" 블록을 따로 등록(도달 -5~10%로 급감). article 참조도 가든이 들고 있으니 본문에서 뺀다. cf. 블루스카이/트위터는 가든 URL **전체**가 글자수 차지(자동단축 없음/ t.co 23자). 페북은 일단 본문 링크 유지(개인 프로필 페널티 덜 명확).

### 후속 (자동화)
- [ ] 요약형 글자수 초과 시 매체별 자연스럽게 줄이는 루프(현재 입력 요약 그대로) — 단 취향 보존 원칙 유지.
- [ ] 새 노트 금지·기존 확장 매칭 보조(denotecli/semantic-memory) 스킬 워크플로 연결.
- [ ] API-clean 자동발행 — Threads(`threads_content_publish` 보유) → Bluesky(AT Proto). 읽기/쓰기 스킬 흡수.
- [ ] 네이버/티스토리/개인 페북 브라우저 자동화(`browser-tools`/크롬확장) — 묶음 파일 소비.

> ⚠️ 검토 메모: 면들이 **API-clean(Threads·Bluesky·FB Page·IG) vs 브라우저-자동화-강제(네이버·티스토리·개인FB)** 두 종족. 후속 자동화 시 이 분기 유지. 포맷 규격 변경은 `PLATFORMS` 한 곳만. 문서세트(README/AGENTS/BACKENDS) 동기화 = v2026.6.15에서 완료.

---

## scanbook 진행 현황 — 6권

파이프라인: PDF → ①MinerU(gpu2i 원격) → ②`mineru2org.py`(구조복원+교정+감독형 봉합) → ③ox-epub. 전부 결정론적(org 바이트 동일 재현).

| 책 | 구조 타입 | 봉합 | EPUB | 텍스트 교정 |
|---|---|---|---|---|
| 물질생명인간 | chapters 2단(장/절) | page+samepage 167 | 0/0/0 240KB | ✅ 앎 safe_regex 등 |
| 물리학강의 | 3level(부/강/소절) | page+samepage 430(skip규칙) | 0/0/0 9.9MB | ✅ literal 282 |
| 자연철학강의 | chapsec(장/고정마커절/소절) | **page만**(운문/한문 오염→samepage 제외) 187 | 0/0/0 6.4MB | ✅ literal 159 |
| 물리의정석 | **강+막간(부 없음)** | page+samepage **129**(back_matter 제외 fix) | 0/0/0 4.1MB | ✅ **safe 3+literal 22=45곳** |
| 인공지능시대 | chapters 2단 (**heading 파편 극심**) | 미평가(봉합 off) | **0/0/0 385KB** | ✅ literal 20(가나10+한글7+latin3), candidate 4 보류 |

엔진 핵심(SSOT = `mineru2org.py` + `detect_para_splits.py`):
- 구조 핸들러 3종(chapters 2단 / 3level / chapsec) + chapters 일반규칙(seen_chap 중복장→소절, 강번호줄 드롭, **단일 한글음절 헤딩 강등**=색인 자모 divider)으로 4종 구조 커버. **새 책은 핸들러 안 만들고 config+소규모 일반규칙으로** (GLG 방침: 완전자동화 안 노림, TOC 정본 알므로 정렬은 쉬움).
- **heading 파편 극심한 책(인공지능시대)**: MinerU가 큰 제목 글자를 줄단위로 쪼개 `text_level=1`이 224개(소절 ~58개). mineru2org reconstruct로 복원 불가. **GLG 방침(2026-06-04): 목차 정렬은 정형 패턴 아님 → 범용 mineru2org 에 넣지 말고 책 전용 `scanpdf/work/<book>/assemble.py`**. vision 스켈레톤(`org/*.org` 마스터 TOC)을 정답으로 장 anchor 동기화 + 한글전용 norm(병기 무시) + fuzzy(OCR 1글자) + lookahead 매칭(61/66) + override 3(MinerU가 heading 인식 못한 일반텍스트 소절). **스켈레톤 외 heading은 전부 본문(평문) 아니면 block** — 시→`#+begin_verse`(행바꿈 보존; GLG: "시 heading 두면 org 이상해져"), 번호항목·도식·일화 소제목·맺음말 본문화, 장제목 파편 삭제. 파이프: mineru2org(글/문단/그림/수식/각주 자동) → assemble.py(heading만).
- 감독형 봉합 `_seam_for`: digit-head/caption-head/pageref-tail/enum-circled skip + josa/fusion/mid-어절 seam. **samepage_break는 책별 판단** — 자유형 오염(운문/한문)=카테고리 드롭, 규칙형 오염(캡션/교차참조/박스제목)=skip 규칙 추가. 항상 dry-run `.merges.log` 통독 후 결정.
- `body_bounds`(봉합/탐지 본문범위): back_matter 표제가 `text_level` 헤딩이면 거기서 컷, **아니면(MinerU가 러닝헤드 type=header로만 출력) 그 표제 첫 등장 페이지의 첫 블록 fallback** — 물리의정석 찾아보기 색인+판권이 봉합되던 버그 해소.
- 새 skip/구조/body_bounds 규칙은 공통 SSOT라 **추가 후 커밋된 책 전부 byte-identical 회귀 0 확인 의무** (물리의정석 2차에서 4권 전부 확인 완료).

---

## 다음 한 걸음

### 🎯 메인 작업축 — 한글 텍스트린트 + kime  (상세: 아래 섹션)
연결고리(textlint↔kime) 실증 완료(2026-06-04). 다음 = **양 채우기** → 아래 "한글 텍스트린트" 섹션의 '다음' 참조.
당장 후보: 룰 A(마침표 뒤 공백, `check.mjs` 로직 → 룰화), scanbook `run.sh kospell` 게이트(인공지능시대부터), ko-saisiot `PAIRS` 확장.

### scanbook — 안정화, 저우선 후속
- [ ] **인공지능시대 char 잔여 4건** (oracle 없어 보류, `.candidates.log`): `섬ピ`/`바WWW하게`(L476)/`'WWW'를 다했나`(L556)/`되Mrkm되어`. 교정어 미상 → DeepSeek-OCR 의심페이지 대조 or reading-pass.
- [ ] (선택) 인공지능시대 para-splits 평가 → 봉합 on 여부 (현재 봉합 off).
- [ ] **물리의정석 3차** (저우선): 서문 추가(body_start→`최소한의 이론`, 서문 2항 chapters, `차례` TOC 드롭; 서문에 `Most지→많지` 잔존), 전수 reading-pass(DeepSeek 대조), eq_interrupt 별행화(현 렌더 정상, 시각만).

### 백로그
- [ ] (선택) 봉합 워크플로 스킬화 — 리스트→봉합→로그검수→환류 루프.
- [ ] (선택) `scanbook/eval/` — 4엔진 총교정비용 점수표(MinerU vs DeepSeek-OCR vs **PaddleOCR-VL** vs **GLM-OCR**). 벤치는 항상 **물리학강의 5강(PDF p121–137)** 동일구간(= DeepSeek 비교 때 쓴 구간).
  - **⚠️ eval 설계 원칙(GLG 2026-06-05)**: 후처리(구조복원+교정+감독형 봉합)는 우리가 결정론적으로 **소유**한다 → 엔진은 **우리가 못 고치는 부분 = raw OCR 글자/레이아웃 충실도**로만 줄세운다. 엔진이 뱉는 markdown 구조 예쁨(heading/표/reading order)은 어차피 mineru2org/assemble에서 재구성하므로 **점수에서 제외**. 메트릭 = 글자 오독(literal/safe_regex 발생수) + 띄어쓰기 붕괴 + 도판 asset(픽셀·bbox) 품질. 목적은 "문서 보면서 custom하게 org 생성".
  - **⚙️ 모델 layer vs 도구 layer 구분 (2026-06-06 측정 결론 — GLG 핵심질문 "MinerU가 모델로서/도구로서 의미있나")**: 엔진은 **2겹**이다. 비교도 2층으로 나눠야 공정.
    - **모델**(페이지→텍스트): MinerU2.5-VLM / PaddleOCR-VL / DeepSeek-OCR / GLM-OCR. 글자정확도 경쟁.
    - **도구**(layout + **asset 픽셀크롭** + **수식 LaTeX 인식** + content_list 구조라벨): MinerU pipeline / PaddleOCR **PP-StructureV3**.
    - **작업별 최강(물리학강의 5강 실측)**: 이미지 픽셀크롭 = **MinerU 유일**(9개 `.jpg`/전체 376, caption 분리) · 수식 LaTeX = **MinerU 유일**(`$$2\mathrm{H}_2+\mathrm{O}_2\rightarrow$$` vs PaddleOCR-VL `2H2+O2` 평문화·아래첨자 손실) · 구조라벨(header17/page_number17/caption/footnote) = **MinerU content_list 유일** · 본문글자 = **PaddleOCR≳DeepSeek>MinerU**(MinerU `mosaic`/`焮` 환각) · 고유명사안정성 = **DeepSeek>MinerU(일관오독)≈Paddle(분산오독)**.
    - **결론**: MinerU는 **모델로선 약하나(글자·환각 열위) 도구로선 base 유지 가치 압도** — 그림·수식 책에서 모델직결은 픽셀/LaTeX/구조를 원천적으로 못 얻어 탈락. **조합 = MinerU(도구) 골격 + 더 정확한 모델을 targeted oracle 로 글자 오독만 덮어쓰기**(스킬 "best of both" 측정 재확인).
    - **✅ "도구 대 도구" 측정 완료(2026-06-06)** — gpu3i tmux:ppserve :8118 PaddleX `/layout-parsing`(nixos 담당, korean_PP-OCRv5_mobile_rec). 클라 `scripts/ppstructure_client.py` + `run.sh ppstructure-parse`(터널 8118). 산출 `ppstructure-out/`.
      - **PP-StructureV3 = MinerU 도구 동급**: 구조라벨 image 9=9·formula 1=1·figure_title 8·paragraph_title 3·number 17, asset크롭 10, 수식 **인라인까지** LaTeX(`$$2H_{2}+O_{2}\rightarrow$$`+`$(H_2)$`), 표 SLANet. **MinerU 도구 유일성 깨짐** — 대안 생김.
      - **단 텍스트모델(mobile rec) 약점**: **띄어쓰기 붕괴 공백비율 0.120**(vs PaddleOCR 0.228/DeepSeek 0.211, 정상~0.15+) = PP-OCR 고질. 환각은 없음(MinerU mosaic/焮 대비 우위). 고유명사: 돌턴 6/6✓·찐빵✓(DeepSeek 돌탄/Paddle 전빵 깨진 곳 맞힘), 톰슨 통슨2/톰슨2, 굽은→급은.
      - **🔗 구조적 연결**: 띄어쓰기 붕괴 복원 = **kime(형태소) 역할** → **scanbook ↔ textlint-ko 두 작업축이 만남**. PP-StructureV3 채택의 전제 = kime 띄어쓰기 복원. (nixos 담당도 "후처리가 복원"이라 명시)
      - **4엔진 톰슨 4변형**(톈슨/톰슨/톱슨·통순·통슨/통슨) → multi-engine voting 탐지기 더 강력(돌턴은 DeepSeek만 틀려 3:1).
- [x] **PaddleOCR-VL 연결 완료**(2026-06-06). gpu3i:8000 vLLM(served `paddleocr-vl`). 클라 `scripts/paddleocr_vl_client.py`(DeepSeek 클라 기반, 순수 OCR raw md, grounding/asset 없음, `--strip-page-num`) + `run.sh paddleocr-parse`(로컬 8001→gpu3i:8000 터널, 8000=DeepSeek 회피). 프롬프트 `OCR:`(="Convert to markdown" 동일출력). 17p/26.8s.
  - **1차 공정평가(물리학강의 5강 p121–137, vs MinerU base)**: ① **본문 글자정확도 PaddleOCR > MinerU**(MinerU `지焮지만`한자환각·`웹만큼`·`볼렸`·`쏘깔` vs Paddle `지녔지만`·`웬만큼`·`불렀습니다` ✅). ② **환각 차이가 결정적** — MinerU 톰슨→`mosaic`(영어환각)·한자`焮` **원문에 없는 토큰 생성**(OCR 치명) vs Paddle 환각 없이 음절치환만(`전빵`/`조갤`)→교정추적 쉬움. ③ **단 Paddle 약점=고유명사 분산+비결정성**: 톰슨 `톱슨/통순/통슨/톰슨` 4변형, **temp=0인데 `알갱이`/`알깡이` 호출마다 갈림**(vLLM greedy 불안정, seed/enforce_eager 서빙설정 의심—nixos 담당 확인필요). 슈뢰딩거는 MinerU 완벽 vs Paddle `슈퇴당거`. cf. "일관오독<분산오독" 교정비용 원칙.
  - 잠정순위(이 구간 raw): 본문 `Paddle≳DeepSeek>MinerU`, 고유명사안정성 `DeepSeek>MinerU(일관)≈Paddle(분산)`.
  - 산출: `paddleocr-out/물리학강의001/물리학강의001.md`. 평가 끝나면 `./scripts/vllm-serve.sh gpu3i paddleocr-vl stop`(hej-nixos-cluster).
  - **DeepSeek 5강 재측정 완료(2026-06-06, `deepseek-out/`)**: 톰슨 5/5·찐빵 정확(MinerU/Paddle 다 깨진 걸 맞힘), 수식 `\[2H_2+O_2\rightarrow2H_2O\]` LaTeX ✅, **단 돌턴→`돌탄`×4 약점**, 이미지 8블록 bbox만(픽셀 없음=MinerU 유일성 유지), 구조 grounding(text47/sub_title3/image_caption7/equation1).
  - **🔑 최대 발견 — 엔진별 오독 비중첩 → 3엔진 교차 = 고유명사 오독 자동탐지기**: 톰슨(MinerU·Paddle✗/DeepSeek✓)·돌턴(DeepSeek✗/MinerU·Paddle✓)·슈뢰딩거(Paddle✗/타✓). **3엔진 불일치 지점 = OCR 오독 의심점** → 사람 reading-pass로 찾던 고유명사 오독을 **multi-engine voting 으로 기계가 교정후보 자동생성**. 스킬 "consistency≠accuracy"의 역(逆)활용(한 엔진 반복오독은 못 잡지만 엔진간 불일치는 신호). **차기 도구 후보: `scripts/engine_vote.py`(3엔진 같은구간 정렬→불일치 토큰→candidate 교정 제안)**.
  - **다음**: ① ✅ PP-StructureV3 측정완료(위 모델/도구 블록). ② 비결정성 nixos 담당과(seed 고정 요청). ③ GLM-OCR(transformers≥5.0 풀리면, 프로파일 준비됨). ④ **engine_vote 탐지기 PoC**(4엔진 정렬→불일치 토큰→교정후보, 톰슨 4변형이 실증). ⑤ **kime 띄어쓰기 복원 PoC**(PP-StructureV3 0.120 붕괴 입력 → textlint-ko 복원, 두 작업축 연결점).
- [x] **GLM-OCR 측정완료**(2026-06-06). gpu3i:8101 vLLM(격리 venv: vllm 0.22 + transformers 5.10, nixos 담당). 별도 클라 안 만들고 **paddleocr 클라 재사용**(`--url …:8101 --model glm-ocr --prompt "Text Recognition:"`). 산출 `glm-out/`.
  - **⚠️ 결과: 한국어 스캔책 부적합** — OmniDocBench v1.5 **94.6%(5엔진 SOTA 1등)** 인데 5강 17p에서 **돌턴/톰슨/볼츠만 정상표기 0건**(전멸: 톰슨→통속, 데카르트→대칭르트, 볼츠만→불초만), **한자환각**(磊嚣螽), 띄어쓰기만 정상(0.218). **OmniDocBench ≠ 한국어 충실도의 결정적 반례** — "MEASURE first" 입증. 영문 문서엔 SOTA일 것. 전용 클라/run.sh 보류(한국어 탈락 → 인프라 불필요).
  - **5엔진 한국어 본문 최선 = DeepSeek-OCR / PaddleOCR-VL**(글자 우수+띄어쓰기 정상). GLM 제외, PP-StructureV3는 도구로만(kime 전제).
- [x] **🏆 PaddleOCR-VL 도구모드 = 단일 최강 발견**(2026-06-06, GLG "vl 우리도 해본거 아닌가" → 모델모드만 본 것). gpu3i:8119 PaddleX `/layout-parsing`(nixos 담당). **모델모드(:8000 vLLM `/v1/chat`)와 같은 모델·다른 서빙** → ppstructure 클라 재사용(`--url …:8119`). 산출 `vltool-out/`.
  - 결과: **띄어쓰기 0.202**(PP mobile 0.120 붕괴 해결) + **asset 12** + **구조 9종**(vision_footnote/display_formula/reference_content) + **돌턴6·볼츠만4·굽은✓**(GLM/DeepSeek/MinerU가 깨먹은 곳 맞힘). **MinerU 환각·PP 띄어쓰기붕괴·GLM 한국어전멸 3대 약점 동시 회피.** 약점: 느림 8.5s/p(MinerU 빠름), 톰슨→통슨(고유명사 oracle/voting 보완).
  - **decision(SKILL 반영): tool base = PaddleOCR-VL 도구모드(:8119), MinerU = 빠른 대안 base.** 같은 모델도 서빙(모델 vs 도구)으로 갈린다 — 오늘 최종 교훈.
- [ ] DeepSeek-OCR 클라 개선(필요시): `## ##` strip, bbox 캘리브레이션, 띄어쓰기 붕괴 탐지.

> 완료(상세는 커밋 history + 위 엔진핵심): 물리의정석 2차(2026-06-04, 봉합검증+body_bounds fix+교정45), 인공지능시대(2026-06-04, 책전용 assemble.py heading복원 + 각주 orphan fix[4권 회귀 0 확인] + char 1차 20곳 + EPUB 0/0/0).

---

## 한글 텍스트린트 + kime (신규 작업축 — 2026-06-04 착수, 연결고리 완성)

**무엇**: 한국어 글 린터를 memex-kb 안에서 self-contained 로 새로 짓는다. textlint(Node) + **kime(Kiwi 형태소)**.
형태소 분석이 해자 — regex만인 Vale 는 한국어 조사/어미 오탐에 익사한다(GLG 2023 `[[denote:20231108T061821]]`).
kime 가 품사를 줘서 "속도가"의 `가`(조사)·"거리이다"의 `이다`(계사)를 명사로 오인하지 않는다.

### ⚠️ 방향 고정 — 다음 세션이 또 헷갈리지 말 것 (2026-06-04 실제로 헷갈렸음)

> **함정**: `~/repos/gh/koprfrdr` 를 열어보면 **거의 완성된 textlint preset**(prh 5,817 + ko-morpheme 1,022 +
> kiwi 토큰매핑)이 나온다. "이게 베이스네, 이걸 쓰면 되겠네" 라고 착각하기 쉽다. **아니다.**
>
> - koprfrdr = **ychoi-kr 포크, LICENSE 없음, 규칙 JSON/prh = ychoi 데이터**. 공개 리포로 못 옮긴다.
> - GLG 결정(숙고 끝): koprfrdr **베이스로 안 씀 / 담당자 안 세움**. memex-kb `textlint-ko/` 에 **새로**.
> - koprfrdr 는 **레퍼런스 only** — 볼 가치: `scripts/kiwi_token_map_extended.json`(세종태그 매핑),
>   규칙 카테고리 분류, `kiwi-wrapper.ts`/`rule-matcher.ts`(이건 GLG 자작 글루라 ychoi 데이터 0 → 참고 깨끗).
> - 규칙 = 국립국어원 공개규범 + **GLG 실증(scanbook safe_regex/literal)** 으로 처음부터 세종태그로. ychoi 포팅 ❌.
>
> **kime ≠ dictcli 의 kiwi.** dictcli 는 kiwi-java(JNI)+JVM+clojure 라 무겁고 복잡. memex-kb 는 **kiwi-nlp
> (npm, C++→WASM, JVM 0)** 로 가볍게. 모델은 `~/repos/3rd/Kiwi/models/cong/base`(GLG가 lfs pull) 를 주입,
> 리포에 안 담음. 이게 GLG가 말한 "C++라 빠르게 가볍게 연결".

### ✅ 이번 세션 한 것 — 연결고리(textlint ↔ kime), 린하게

양(룰 개수)이 아니라 **연결**에 집중. `memex-kb/textlint-ko/` (검증 전이라 신규 리포 ❌, 여기 안에 lean):

```
textlint kernel ─┬ lint → report(file:line:col)   ✅ 실증
                 └ fix  → 자동교정 output           ✅ 실증
   ↓ 룰 객체 직접 주입
 rules/ko-saisiot.mjs  (TextlintRuleModule {linter,fixer}, async)
   ↓ await
 kime.mjs  (싱글톤: getKiwi/tokenize/isNoun)
   ↓
 kiwi-nlp WASM(C++) + cong 모델 → 세종 품사 토큰
```
- 파일: `kime.mjs`(공유 백엔드), `rules/ko-saisiot.mjs`(룰 1개), `run-textlint.mjs`(kernel 드라이버),
  `probe.mjs`/`check.mjs`(형태소 실증), `package.json`(kiwi-nlp+textlint), `.gitignore`(node_modules 제외).
- 실증: `초기 값→초깃값` 등 lint 3건 + fix 정확, **`속도가`/`거리이다` 오탐 0**(kime POS 검증).
- flake.nix 에 `pkgs.nodejs_24` 추가(textlint 15.x CI 매트릭스 [20,22,24] 검증). `nix develop` → node v24.15.0.

### 다음 (양 채우기 = 이후, 병렬 가능)

- [ ] **CLI 패키징(Phase 1.5)**: `npx textlint --rulesdir` 가 ESM `.mjs` 룰을 안 잡음("No rules found").
  진짜 `npx textlint` UX엔 `textlint-scripts build`로 CJS 빌드 or 패키지화 필요. (지금은 kernel 드라이버로 충분.)
- [ ] **룰 A 추가**: 마침표 뒤 공백(regex, kime 불요, 결정론). 물리의정석 org 실측 43곳. `check.mjs` 에 로직 있음 → 룰화.
- [ ] **양 채우기(병렬)**: ko-saisiot `PAIRS` 확장, morpheme-match 엔진(azu `textlint-rule-morpheme-match` 한국판),
  국립국어원 규범 규칙. **구조 스타일** = textlint 공식(`src/index.ts` TextlintRuleModule + `textlint-tester` valid/invalid
  + `textlint-scripts`), 조합은 preset(`{rules, rulesConfig}` + 룰키==설정키 불변식 테스트). 모노리포: 지금 **lean
  단일 패키지**, Phase 2 졸업 때 pnpm-workspace(catalog/lerna)로 쪼갬.
- [ ] **scanbook 연동**: `run.sh kospell <file>` = 한국어 산문 QA 게이트. OCR 비단어 깨짐(쏸/옵긴이)은 내 방법
  (merges.log+의심음절), 표준 띄어쓰기/사이시옷은 kospell — 상보적. 인공지능시대(6권)부터 게이트.
- [ ] **Phase 2 졸업(IF 검증됨)**: 공개 `hangul-textlint` 리포로 추출, README 에 ychoi-kr/wikidocs+국립국어원 출처 크레딧. 그때 신규 담당자.

**레퍼런스 경로**: `~/repos/3rd/textlint`(공식 모노리포 — packages/, textlint-scripts, textlint-tester, pnpm
catalog), `~/repos/3rd/textlint-rule-preset-ja-technical-writing`(preset 조합 스타일), `~/repos/3rd/Kiwi`(C++ 소스
+cong 모델, wasm 바인딩), `~/repos/gh/koprfrdr`(레퍼런스 only ⚠️위 함정), `~/repos/gh/dictcli`(kiwi-java 무거운 길 — 안 감).

**GLG 4년치 사고**: `[[denote:20240923T220612]]`(textlint/vale 한글), `[[denote:20240123T173354]]`(린터 메타),
`[[denote:20231108T061821]]`(Vale 형태소 한계), `[[denote:20230707T095700]]`(한글 textlint 플러그인).

---

## 인프라 메모

- **flake.nix nix-ld 자립**(2026-06-04): MinerU 클라(numpy/opencv manylinux wheel)가 `nix-ld.libraries=[libcap]`만인 호스트에서 `libstdc++/libz` 부재로 실패 → flake shellHook이 `MINERU_LD_LIBRARY_PATH = makeLibraryPath [stdenv.cc.cc.lib zlib] + nix-ld path` export, run.sh mineru 명령을 nix develop 안에서 그 변수로 실행. 호스트 nix-ld 설정 무관 자립.
  - **nodejs_24 추가 완료**(2026-06-04, 한글 텍스트린트 작업축): 같은 flake buildInputs 에 `pkgs.nodejs_24`. textlint/kiwi-nlp 는 npm 으로 `textlint-ko/` 안에서(nix 엔 런타임만 — 가볍게). kiwi 모델은 `~/repos/3rd/Kiwi/models/cong/base` 외부 주입(리포에 안 담음). 외부 의존 0 유지.
- **원격 서버**(nixos 담당): MinerU = gpu2i tmux `mineru-vllm` :30000. DeepSeek-OCR = gpu1i tmux `deepseek-ocr` :8000. `run.sh mineru-parse`/`deepseek-parse` 가 터널 자동.
- **빌드**: `nix develop --command ./run.sh org2epub-build` (zip/unzip 필요, flake에 포함). ltximg는 빌드캐시(gitignore) — RSC-007 시 `rm -rf ltximg *.epub` 후 재빌드.

---

## 은퇴/기록

- vision/Opus 전체전사 은퇴(oracle로만 비교). tesseract/ocrmypdf, marker/surya 제거. 살아남은 QA = `diff_review.py`(`./run.sh diff-review`, 엔진무관).
- ox-epub는 `~/repos/gh/ox-epub` 포크(EPUB3 네이티브+headless). memex-kb 내부 후처리(`epub_upgrade.py`/`org2epub.el`) 재도입 금지. SVG 수식 대문짝 버그 = ox-epub CSS `max-width:90%;height:auto`로 해결됨.
- scanpdf = nested private repo, remote `work` Forgejo `glg-bot/scanpdf`.

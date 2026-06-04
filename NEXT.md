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
| 물리의정석 | **강+막간(부 없음)** | page+samepage **129**(back_matter 제외 fix) | 0/0/0 4.1MB | ✅ **safe 3+literal 22=45곳** |
| 인공지능시대 | 미착수 | — | — | — |

엔진 핵심(SSOT = `mineru2org.py` + `detect_para_splits.py`):
- 구조 핸들러 3종(chapters 2단 / 3level / chapsec) + chapters 일반규칙(seen_chap 중복장→소절, 강번호줄 드롭, **단일 한글음절 헤딩 강등**=색인 자모 divider)으로 4종 구조 커버. **새 책은 핸들러 안 만들고 config+소규모 일반규칙으로** (GLG 방침: 완전자동화 안 노림, TOC 정본 알므로 정렬은 쉬움).
- 감독형 봉합 `_seam_for`: digit-head/caption-head/pageref-tail/enum-circled skip + josa/fusion/mid-어절 seam. **samepage_break는 책별 판단** — 자유형 오염(운문/한문)=카테고리 드롭, 규칙형 오염(캡션/교차참조/박스제목)=skip 규칙 추가. 항상 dry-run `.merges.log` 통독 후 결정.
- `body_bounds`(봉합/탐지 본문범위): back_matter 표제가 `text_level` 헤딩이면 거기서 컷, **아니면(MinerU가 러닝헤드 type=header로만 출력) 그 표제 첫 등장 페이지의 첫 블록 fallback** — 물리의정석 찾아보기 색인+판권이 봉합되던 버그 해소.
- 새 skip/구조/body_bounds 규칙은 공통 SSOT라 **추가 후 커밋된 책 전부 byte-identical 회귀 0 확인 의무** (물리의정석 2차에서 4권 전부 확인 완료).

---

## 다음 한 걸음

### 물리의정석 2차 — ✅ 완료 (2026-06-04, 후처리 로직 검증 + 텍스트 교정)
- [x] **봉합 로직 검증**: merges.log 전수 검수 → 본문 seam 전부 정확, 봉합 무오류. 4번째 구조 검증.
- [x] **back_matter 봉합 버그 수정**: `body_bounds` 러닝헤드 fallback (찾아보기 색인+판권 떡칠 해소). 4권 회귀 0.
- [x] **색인 자모 divider 헤딩 강등**: 단일 한글음절 헤딩 일반규칙 (절 89→77, nav TOC 청소).
- [x] **텍스트 교정 45곳**: safe 3종(쏸/멜타/덜타) + literal 22종. candidate_regex 좁혀 오탐 547→0.

### 물리의정석 3차 (더 깊은 콘텐츠 폴리시 — 저우선)
- [ ] **서문/입문자는 도움이 필요해** 추가(컷 상태): body_start→`최소한의 이론`, 서문 2항 chapters 추가, `차례` TOC 테이블 드롭. (서문에 `Most지→많지` 등 잔존.)
- [ ] **전수 reading-pass**: mid-page 깨짐을 남김없이 잡으려면 DeepSeek-OCR 의심페이지 대조 or 전문 reading-pass (이 책엔 vision oracle 없음).
- [ ] (저우선) 인라인 수식의 별행화(eq_interrupt) — 현 렌더 정상, 시각적 들여쓰기만.

### 다음 책 (여섯째)
- [ ] **인공지능시대와 철학의 쓸모** — scanbook New book checklist. PDF: `scanpdf/인공지능시대001.pdf`.

### 백로그
- [ ] (선택) 봉합 워크플로 스킬화 — 리스트→봉합→로그검수→환류 루프.
- [ ] (선택) `scanbook/eval/` — 6종 샘플셋 + 총교정비용 점수표(MinerU vs DeepSeek-OCR 공정비교).
- [ ] DeepSeek-OCR 클라 개선(필요시): `## ##` strip, bbox 캘리브레이션, 띄어쓰기 붕괴 탐지.

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

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

## 한글 텍스트린트 + kime (신규 작업축 — 2026-06-04 착수 결정)

**무엇**: 한국어 글 린터를 memex-kb 안에서 self-contained 로 만든다. textlint(Node) + **kime(Kiwi 형태소)** 를
flake.nix devShell 에 함께 담아 외부 의존 0. 형태소 분석이 해자 — regex만인 Vale 는 한국어 조사/어미 오탐에
익사한다(GLG 2023 결론 `[[denote:20231108T061821]]`). kime 가 토큰+품사를 줘서 "명사+조사" 를 정밀 매칭.

**결정/근거 (2026-06-04)**:
- **전부 여기서, 외부 의존 없이.** kime 도 memex-kb 로 다시 품는다. dictcli 는 미완이라 의존 안 함 — 되면
  dictcli 형태소 역할까지 memex-kb 가 흡수 가능. flake.nix(scanbook nix-ld 자립과 같은 노선)로 node+textlint+kiwi 일괄.
- **koprfrdr(ychoi-kr 포크)는 손 안 댐 / 담당자 안 세움.** 규칙은 국립국어원 표준(공개) + **GLG 실증(scanbook
  safe_regex/literal)** 중심으로 베이스부터 새로. koprfrdr 9,743 규칙 포팅 ❌ — 데이터셋은 참고만, README 에
  ychoi-kr/wikidocs+국립국어원 출처 크레딧. (라이선스 근거: 한글 맞춤법/표준어/외래어 표기법 = 공개 규범,
  ychoi 의 JSON 은 한 렌더링일 뿐. 단 그의 code 는 한 줄도 안 가져옴.)
- **구조 템플릿** = `textlint-rule-preset-ja-technical-writing`(kuromoji 자리에 kime). 검증 전엔 신규 리포/담당자 0.

**scanbook 연동 (즉시 가치)**: `run.sh kospell <org>` = 한국어 산문 QA 게이트. 내 OCR-깨짐 방법(merges.log+의심음절)이
구조적으로 못 잡는 **MinerU 띄어쓰기 붕괴 + 사이시옷**을 잡는다. 실측: 물리의정석 org 에 `마침표+한글` 붙음 42곳
(`거리이다.속도`→`거리이다. 속도`), `초기 값`→`초깃값`. 상보적 — OCR 비단어 깨짐(쏸/옵긴이)은 내 방법, 표준
띄어쓰기/맞춤법은 kospell.

**Phase (검증-후-추출, 리포 먼저 ❌)**:
- [ ] **Phase 0 (memex-kb 단독)**: flake 에 node+textlint+kiwi 잡기 → 룰 1개(`명사+값→사이시옷` 또는
  `마침표 뒤 공백`) + kiwi 바인딩으로 물리의정석 org 실측. "형태소 덕에 조사 오탐 없이 잡힌다" 눈으로 확인.
- [ ] **Phase 1 (kime 통합)**: kiwi 바인딩 → memex-kb 내장 kime 진입점으로 통일(`tokenize --pos`).
- [ ] **Phase 2 (졸업, IF 증명됨)**: 공개 `hangul-textlint` 리포로 추출. 그때 신규 담당자.

**참고 — GLG 4년치 사고**: `[[denote:20240923T220612]]`(textlint/vale 한글 만들고 싶지),
`[[denote:20240123T173354]]`(린터 메타), `[[denote:20231108T061821]]`(Vale 형태소 한계),
`[[denote:20230707T095700]]`(한글 textlint 플러그인). koprfrdr = 데이터 수집 단계였고 이제 본편.

---

## 인프라 메모

- **flake.nix nix-ld 자립**(2026-06-04): MinerU 클라(numpy/opencv manylinux wheel)가 `nix-ld.libraries=[libcap]`만인 호스트에서 `libstdc++/libz` 부재로 실패 → flake shellHook이 `MINERU_LD_LIBRARY_PATH = makeLibraryPath [stdenv.cc.cc.lib zlib] + nix-ld path` export, run.sh mineru 명령을 nix develop 안에서 그 변수로 실행. 호스트 nix-ld 설정 무관 자립.
  - **예정(한글 텍스트린트 작업축)**: 같은 flake 에 nodejs + textlint + kiwi(형태소) 추가해 `kospell` self-contained. 외부 의존 0 원칙 유지.
- **원격 서버**(nixos 담당): MinerU = gpu2i tmux `mineru-vllm` :30000. DeepSeek-OCR = gpu1i tmux `deepseek-ocr` :8000. `run.sh mineru-parse`/`deepseek-parse` 가 터널 자동.
- **빌드**: `nix develop --command ./run.sh org2epub-build` (zip/unzip 필요, flake에 포함). ltximg는 빌드캐시(gitignore) — RSC-007 시 `rm -rf ltximg *.epub` 후 재빌드.

---

## 은퇴/기록

- vision/Opus 전체전사 은퇴(oracle로만 비교). tesseract/ocrmypdf, marker/surya 제거. 살아남은 QA = `diff_review.py`(`./run.sh diff-review`, 엔진무관).
- ox-epub는 `~/repos/gh/ox-epub` 포크(EPUB3 네이티브+headless). memex-kb 내부 후처리(`epub_upgrade.py`/`org2epub.el`) 재도입 금지. SVG 수식 대문짝 버그 = ox-epub CSS `max-width:90%;height:auto`로 해결됨.
- scanpdf = nested private repo, remote `work` Forgejo `glg-bot/scanpdf`.

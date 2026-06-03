# NEXT — memex-kb

휘발성 후속 작업 메모. 영속 사실은 AGENTS.md / docs / commit으로 옮긴다.

---

## ★★★ 문단 잘림 봉합 — page-split paragraphs (진행중, 2026-06-04 시작)

OCR로 못 잡는 **구조 결함**: MinerU가 페이지를 독립적으로 읽어, 페이지 경계/그림·표·수식 끼임으로
한 문단이 별개 문단으로 쪼개진다(`물\n\n리과학`). 세 책 공통. 글자는 맞고 문단 경계만 틀어짐.

### 이번 세션 완료 ✅

- **`scripts/detect_para_splits.py` + `./run.sh para-splits <book>`** — 탐지·리스트 전용(본문 미변경).
  content_list.json + 한국어 종결부호 휴리스틱으로 5분류. front/back matter 제외.
- **본문 실측**: 물리학강의 701(page 392/image 130/eq 58/table 17/samepage 104),
  자연철학강의 473, 물질생명인간 202.
- **핵심 발견**: 봉합부 **공백 여부는 자동화 불가** — page_boundary 392건 측정상 ~65% 무공백(어절중간),
  ~30% 공백(어절경계), ~5% 모호. 일괄 치환 시 30% 단어 붙음/띄움. → **탐지는 신뢰, 봉합은 검수**.
- **scanbook SKILL.md 전면 재작성**(영어·토큰절약): 📐 Paragraph splits + 감독형 봉합 섹션 1급화.

### 감독형 봉합 패스 구현 완료 ✅ (2026-06-04)

- **`mineru2org.py` `--merge-paragraphs`** (기본 OFF, config `paragraph_merge.enabled`로도 ON).
  raw md 위에서 `tail\n\nhead` 봉합. seam = 조사/어미→공백, 어절중간→무공백, 융합(`이`+란/며/든/었/는/들/라)→무공백,
  콤마→공백, 비한글/`:`→skip. `.merges.log` 전수 기록(MERGE/SKIP/MISS + 이유).
- **헤딩 경계 가드**: 평문 `N강`/`제N장`(NUMHEAD regex) + 장/절 제목 **정확일치** + 길이게이트(≤40자)로
  봉합이 강 표지를 흡수하던 버그(4·13·18강 실종) 차단. `detect_para_splits`는 full tail/head 텍스트 저장하도록 변경.
- **3책 검증(/tmp, 커밋 org 미변경)**: 물리학강의 478봉합/18skip/0miss(h2 28 보존),
  자연철학강의 265/64/3miss(반복라벨 안전거부), 물질생명인간 170/21/0. 전부 h1/h2/h3 구조 보존.

### 물질생명인간 — 봉합 첫 적용 완료 ✅ (2026-06-04, 첫 책)

config `paragraph_merge.enabled:true` → **167봉합 / 24skip / 0miss**, **EPUB epubcheck 0/0/0**(240KB),
num:nil 반영, 장7/절26/소절62 보존, 각주 전부 정상. **org 바이트 동일 재현 검증 완료**(merges.log md5 동일).

검수 루프가 잡은 seam 규칙(전부 `mineru2org.py`에 영속, 모든 책 공통):
- **`digit-head` skip** — 병합이 각주정의 orphan(`19 …`)을 앞 문단에 흡수→`그19…`→footnote 정의 실종→빌드 실패. 숫자시작 head는 봉합 금지(각주·번호목록 보호).
- **융합 확장** `이`+러/루/른/렇/를(이러한/이루는), **`josa-head`**(head 맨조사→무공백, `사이에`),
  **`게` 어미·`adv-tail`(물론)·`conj-head`(및)·`jeok-tail`(개인적 차원)·`latin-head`(엔트로피 entropy)**.
- 관형형/의존명사 잔여(`된연유`/`세계안에는`)는 일반화 위험 → config `literal`로 외과 교정.

### 다음 한 걸음 — 나머지 책 봉합 적용(감독, 새 세션)

- [ ] **자연철학강의** → config `paragraph_merge` 켜고 같은 루프(검수→환류→빌드 0/0/0). 단 **3miss(반복라벨 `변화의 원리`+`나중 상태`)** 확인.
      section_markers(역사 지평/내용 정리/해설 및 성찰) 헤딩 보존되는지 점검.
- [ ] **물리학강의** → 동일. 그림 200+·수식 多라 image/table_interrupt 보류분 많음. 평문 강표지(4·13·18강) 가드 확인.
- [ ] 검수에서 새 seam 오탐 나오면 `mineru2org.py` 휴리스틱에 환류(특히 `이`-종결, 관형형 `된/한`, 의존명사 `안/속`).
- [ ] eq/image_interrupt는 여전히 보류(수동). image 뒤 블록이 캡션/변수설명인 경우 구분 필요.
- [ ] (선택) 봉합 워크플로 스킬화 — 리스트→봉합→로그검수→환류 루프.

---

## ★★★ 물리학강의 본문 마무리 — 깨짐 토큰 전수 교정 ✅완료·푸시됨 (2026-06-03 22:xx → bbf13d9)

A 블록 실행 완료. **MinerU 베이스 + DeepSeek 오라클 + vision 페이지 판독** 3단으로 잔존 깨짐 전수 해결.
config `literal` **216 → 282** (+66). **EPUB epubcheck 0/0/0** (10.3MB). 구조 불변(부7/강27/소절129).
**커밋·푸시 완료**: memex-kb `bbf13d9`, scanpdf `93baa1f`(Forgejo).

### 해결 경로 (노하우 — 영속 가치)

1. **latin-glued ~30 + 한자 garbage ~25** = 문맥/오라클로 확정. 예: `mosaic→톰슨`, `Guq은→굽은`,
   `propag이는→알갱이는`, `지焠고→지니고`, `바撂니다→바뀝니다`, `반仄붙이→반딧불이`, `애擘의→애벗의`.
2. **양 엔진 모두 깨진 hard spot = vision 페이지 직접 판독**(스킬 "spot-checking page images"):
   - **쩔쩔맴**(쩔쩔매다, 저자 반복용어) — OCR이 `쫔Explamm`/`쳨湊mamm`/`젊巴巴`/`웰켈맵`/`챌젤땀` **5가지로** 깨뜨림. p636/656/679 3곳.
   - `꺌岁月을→꿰뚫을`(데카르트 물질 불가입성), `제어 Charging 변수→제어맺음변수`(control parameter),
     `사骐점→사귐점`(교점), `뇌下了데→놔뒀는데`, `차모暍→차모늄`(charmonium).
3. **시간펼침(시간 전개) 14회** — 양 엔진이 **펼→필 계통 오독**(`시간필침`). vision p181로 확정.
   ⭐ **노하우: OCR 일관성 ≠ 정확성** — 빈출 용어가 같은 방향으로 계통 오독되면 비교만으론 못 잡음.
4. **하마터면 틀릴 뻔한 의도 표기(건드리면 안 됨)**:
   - `궤뚫기` = 책의 tunneling 용어 → **STM = 훑기궤뚫기현미경**(궤 유지). `궤擣기`(擣 변이)만 `궤뚫기`로.
   - `기氣차라` = 스타트렉 "Energize!"의 **한자병기 말장난**(기(氣) 차라). 창발創發·팔정도八正道 스타일.
   - `Cx는` = 수식 항 `t'=Cx+Dt`의 Cx. 문맥 안 보면 오교정.
5. **DeepSeek 오라클 "page" 필드 = page_idx(0-based)** = content_list와 동일. `--pages`는 1-based(page_idx+1).

### 잔존 (저우선, 다음 세션)

- **시간필침 외 의도병기 다수 유지** — 오류 아님(나노nano, F=ma, 짝even, 보오손boson, corpuscle, DNA/QCD, 八正道 등).
- **찾아보기 `一` = 반복기호(—) 대시** — `一력(inertial force)` 류 색인 하위항목. 자모/반복기호 OCR. 정리하려면 색인 `一`→`—` 클래스 규칙(저우선).
- back matter(부록/문헌/찾아보기) 다듬기 1차 수준.

---

## ★★★ 수식 "대문짝" 버그 수정 — ox-epub CSS (2026-06-03 20:59, 작업 서버) ✅검증

GLG 보고: 자연철학강의 어제 EPUB에서 수식이 화면 가득 거대하게 나옴. **원인 = OCR 아님.**

- **근본 원인**: `~/repos/gh/ox-epub/ox-epub.el:140` `.org-svg { width: 90%; }`. ox-epub는 수식·그림
  SVG에 같은 `org-svg` 클래스를 붙임 → **인라인 수식 기호(13pt SVG)까지 컨테이너 폭 90%(~540px)로 강제 확대.**
- **수정** (ox-epub 포크, **커밋은 GLG 몫**): `width: 90%` → **`max-width: 90%; height: auto;`**.
  인라인=자연크기(~18px, 본문과 동일), 디스플레이=자연크기(폭 초과 시만 90% 캡), 그림=기존대로 90% 캡.
- **검증**: 자연철학강의 재빌드 → epubcheck **0/0/0**(6.6MB). SVG 976/987 정상치수(인라인 8~55pt, 디스플레이 419~455pt). 0pt 11개는 기존 빈 fragment(무해).
- ✅ **작업 서버 환경 갭 해결**: `zip`/`unzip` 미설치로 `org2epub-build`(emacs 내부 zip 호출) 실패했음 →
  **flake.nix devShell에 `pkgs.zip`/`pkgs.unzip` 추가.** 이후 `nix develop --command ./run.sh org2epub-build …`로 실행.
- **후속**: 다른 책(물리학강의 등)도 같은 CSS라 재빌드 시 자동 개선. 인라인 수식 baseline 정렬은 미세개선 여지(저우선).

---

## ★★★ OCR 다엔진 탐색 — "OCR을 어디까지 해볼 수 있는가" (2026-06-03 20:50, 작업 서버)

이슈 #3의 실행 단계. **핵심 질문은 OCR 정확도 벤치마크가 아니라 "한국어 스캔책(수식 多) →
clean org/EPUB까지의 총 교정비용 최소화."** 작업 디바이스는 노트북→**작업 서버**로 이전(상시 가동).

### 인프라 현황 (검증 시점에 재확인할 것)

| 서버 | 모델 | 포트 | 상태 |
|------|------|------|------|
| **gpu2i** (gpu-02, RTX5080 16GB) | `MinerU2.5-Pro-2605-1.2B` | `:30000` vLLM | ✅ tmux `mineru-vllm` 가동(Jun02~). 우리 기본 엔진 |
| **gpu1i** (gpu-01, RTX5080 16GB) | `DeepSeek-OCR`(3B/BF16 6.7GB) | (세팅중) | 🔧 GLG가 `hf download`+vLLM 세팅 중. **검증 후 GLG가 알려줌**. 현재 VRAM은 기존 `default`(qwen2) vLLM `:8000`이 점유 → DeepSeek 서빙하려면 스왑 |

→ **두 서버 분리 = 모델 스왑 없이 MinerU vs DeepSeek-OCR 동시 비교 가능.** 16GB 한 장에 둘이 동시 상주는 불가했는데 이게 풀림.

### DeepSeek-OCR을 쓰는 두 갈래 + GLG 방침 결정 (2026-06-03)

**→ ①이 메인. ②는 별도 평가 트랙(순차 조율).** (GLG 결정)

1. **vLLM thin-client 패턴 ✅ 메인** — gpu1i가 DeepSeek-OCR을 OpenAI-compat로 서빙 → 우리가 얇은
   클라이언트로 호출 → 산출 md를 후처리에 투입. **우리 org-메타포맷 유지.** 방침 "GPU 노드엔 로직 X,
   vLLM 모델만"과 일치. **pdf-craft의 `lan="en"/"zh"` 제약을 우회** — 모델 순수 OCR 능력(한국어 포함)을 직접 씀.
   - ⚠️ **mineru-client의 config 스왑이 아님.** MinerU 클라(`-b vlm-http-client`)는 PDF렌더+호출+
     **`content_list.json` 구조 SSOT 조립**까지 해주지만, DeepSeek-OCR vLLM은 **순수 이미지→md 엔드포인트**.
     → 미러는 `PDF→페이지이미지 + 페이지별 /v1/chat/completions + md 조립`의 **작은 커스텀 클라이언트**.
   - ⚠️ **함의 = ①트랙의 실제 관문**: DeepSeek 경로엔 `content_list.json`이 없음 → `mineru2org.py`의
     content_list 의존 패스(각주정의 수집·page_number·list 기반 가짜헤딩 탐지)가 SSOT를 잃음.
     OCR 텍스트 품질이 좋아도 **구조 복원 비용**이 올라갈 수 있다 → 총 교정비용 메트릭으로 정확히 잡힌다.
   - ⭐ "어디까지" 레버 = DeepSeek-OCR **멀티해상도 모드**(Tiny/Small/Base/Large/Gundam). vLLM 서빙 시
     해상도/프롬프트가 노브. MinerU엔 없는 비교 차원.
2. **pdf-craft 통짜 ⚠️ 별도 트랙** — `git@github.com:oomol-lab/pdf-craft.git` (clone됨: `~/repos/3rd/pdf-craft`, v1.0.13).
   DeepSeek-OCR을 **in-process 로딩**(`doc-page-extractor==1.0.12`, 원격 vLLM 안 씀). PDF→MD/EPUB 자체 완결.
   - 제약①: GPU 머신(gpu1i)에 **로직 설치** 필요 → GLG 방침("GPU 노드엔 로직 X") 충돌 + NixOS FHS 두더지잡기 재현.
   - 제약②: gpu1i 16GB는 **vLLM 서빙과 배타** → ①(서빙)·②(in-process) 동시 불가, 순차. 하나 띄우면 다른 걸 내려야.
   - → **pdf-craft 파이프라인 자체를 평가할 때만** 별도 트랙으로, GPU 점유 순차 조율. 선택적 `toc_llm`은 OpenAI-compat라 우리 vLLM 연결 가능.

### pdf-craft 검토 결과 (1차, README 기준 — 미설치)

- v1.0.13(2026-04), 18 릴리스. v1.0.0부터 DeepSeek-OCR 전면 채택(MIT), LLM 교정 의존 제거 → 오프라인.
- API: `transform_markdown(pdf_path, markdown_path, markdown_assets_path)` / `transform_epub(pdf_path, epub_path, book_meta=BookMeta(...))`.
- 수식 MathML/SVG/image-clip, 표 HTML/image-clip, 각주·이미지 보존, 헤더/푸터 자동 필터, 메타→EPUB, auto-TOC. 선택적 `toc_llm`(OpenAI-compat)로 챕터 제목 분석.
- 의존성: Poppler + PyTorch/torchvision, CUDA 권장. 모델 HF 자동 다운로드.
- ⚠️ **한국어 미명시**(`lan="en"/"zh"`만 문서화). DeepSeek-OCR 자체는 될 가능성 높으나 **검증 필수 — 1순위 평가 질문.**

### 평가 레이어 설계 (이슈 #3 미구현 태스크 → 실행)

- [ ] `scanbook/eval/` 신설 — 평가 docs + 점수표 템플릿. **메트릭 = org/EPUB까지 총 교정비용**, OCR 정확도 단독 아님.
- [ ] **고정 샘플 페이지셋 컨벤션** — 6종(TOC / 본문 / 수식헤비 / 그림표 / 각주헤비 / 머리말꼬리말)을 기존 5권에서 발췌. 공정 비교 SSOT.
- [ ] 측정 도구 = `diff_review.py`(`./run.sh diff-review`, 엔진무관) 재사용.
- [ ] **1차 대결: MinerU(gpu2i) vs DeepSeek-OCR(gpu1i, vLLM thin-client)** — 같은 샘플셋, 한국어 본문 정확도부터.
- [ ] **2차: pdf-craft 통짜** — gpu1i에 설치(Poppler+torch), 기존 책 1권 PDF→EPUB 직접 뽑아 우리 산출과 비교. 한국어 실측.
- [ ] DeepSeek-OCR thin-client = `mineru-client/` 미러로 신설할지 판단(서빙 확정 후).

### Docling — 알고만 있으면 됨 (이번 스코프 아님)

IBM, Granite-Docling-258M VLM, DoclingDocument(lossless JSON), MCP 서버. EPUB 대체 후보 아님.
중장기 memex-kb 공통 중간표현/에이전트 문서변환 표면 후보로만 기억. **이번 OCR 탐색에선 다루지 않음.**

### ✅ DeepSeek-OCR 서빙 + 한국어 실측 완료 (2026-06-03 20:43)

- **서빙**: gpu1i `:8000` OpenAI-compat, served-name `deepseek-ocr`, max_len 8192, tmux `deepseek-ocr`.
  외부 접속 = `ssh -fN -L 8000:localhost:8000 gpu1i`(ProxyJump). gpu2i:30000(MinerU)와 **동시 가동 → 동시 비교 가능.**
- **한국어 품질**: 실제 책 페이지(물질생명인간 p60 칸트 인용) 본문·한자병기(`지표指標`)·인용마커(`B 197-198`) 정확. **밀집 한글 완벽.** 0.9~2.0s/page.
- **pdf-craft `lan` 제약은 파이프라인 설정일 뿐 — 모델 OCR 능력은 한국어 완전 지원**(①트랙으로 우회 확정).

#### 수식 페이지 A/B — DeepSeek vs MinerU (물리학강의 p490, 2026-06-03 20:51)

- DeepSeek grounding이 **`equation[[bbox]]` 블록을 별도 라벨**로 주고 `\[...\]` 디스플레이로 정확 출력.
  인라인 `\(N_+\)`도 본문에 인라인 유지. **수식을 이미지로 안 박음** — 전부 LaTeX.
- 품질: MinerU `(2N_+ - N)a`(물리 정합) vs DeepSeek `(2N_+ - N_-)a`(N→N_- 1토큰 오독). **둘 다 클린 LaTeX, 미세차.**
- **"수식 대문짝" 문제(GLG, 자연철학강의 EPUB) = OCR 아님, EPUB CSS 버그로 확정·수정 완료.**

#### 엔진 강점 (추려서 org SSOT에 응용 — 다 만들 필요 없음)

| | MinerU | DeepSeek-OCR |
|---|---|---|
| 구조 | `content_list.json`(각주/페이지번호/헤더분류) | grounding **시맨틱 라벨**(text/equation/sub_title/title/image) |
| 수식 | LaTeX(content_list 교차참조) | **인라인/디스플레이 자체 구분**, 클린 LaTeX |
| 그림 asset | ✅ crop 저장 | ❌ 순수 OCR(asset 없음) — **그림책은 MinerU 강점 유지** |
| 운영 | 성숙·서빙(gpu2i) | 단순 엔드포인트(gpu1i) |

→ **우리가 만드는 것 = org SSOT 생산기. 이미 `mineru2org.py`가 그것.** DeepSeek 클라는 grounding 블록을
**MinerU 호환 md로 정규화** → 기존 `mineru2org.py`가 org로 받음. **OCR 프론트만 스왑, SSOT 생산기 재사용.**

#### API 계약 — 프롬프트 두 모드 (클라 설계 분기점)

| 모드 | 출력 | 우리 파이프라인 적합성 |
|------|------|------------------------|
| `<image>\n<\|grounding\|>Convert the document to markdown.` ⭐ | `<label>[[x1,y1,x2,y2]]\n<text>` 블록. **`sub_title`/`text`/`title` 시맨틱 라벨 직접 부여** | **권장.** content_list.json 잃은 자리를 라벨+bbox가 부분 대체(헤딩힌트·읽기순서·false-heading). 좌표 prefix 파싱 필요 |
| `<image>\nConvert the document to markdown.` | bbox 없는 깨끗한 md, 빈줄 문단 | 라벨 상실 + 헤더/푸터 분리 약함(러닝푸터 본문 혼입). 단순본문엔 OK |

→ thin-client는 **grounding 모드** 채택, 블록 파서가 `sub_title→**`/`title→*` 힌트 담은 md로 조립.
프로브 스크립트: `/tmp/dsocr/probe.py` (urllib만, 무의존). 향후 `scripts/`로 정식화.

### ✅ 측정: 5강 전면 재파싱 DeepSeek vs MinerU (2026-06-03, PDF p121–137)

GLG 가설 "DeepSeek로 다시 뽑으면 후처리 범위가 줄까?" → **본문 축에선 YES, 전체로는 분포가 바뀜.**

| 축 | DeepSeek | MinerU raw |
|---|---|---|
| 본문 char 깨짐 | **0**(corpuscle=병기) | **10**(=그 구간 config literal 10개) |
| 띄어쓰기 | 15/17쪽 정상, p121 붕괴 | 정상 |
| 소절 헤딩 | 부분(누락+`## ##`중복=클라버그) | config로 10소절 완벽 |
| 이미지 | 캡션+bbox만, asset 없음(인명 OCR오류) | asset crop O |

**판정**: DeepSeek 본문 글자정확도 압도(깨짐 0 vs 10) → char교정 거의 0. 단 비용이
**띄어쓰기·헤딩·이미지crop·캡션**으로 이동. **무비용 drop-in 아님.** scanbook SKILL.md「OCR engine choice」에 박음.
**결정규칙**: 본문헤비책=DeepSeek 유리 / 그림헤비책(물리학강의 200+)=MinerU 베이스 + DeepSeek 오라클로 깨진 자리만 / **항상 1개 강 측정 먼저**.

#### 후속 — DeepSeek 클라 개선 (필요시)
- `## ##` 중복: sub_title/title 텍스트에 이미 `#` 있으면 strip 후 마커.
- 이미지 bbox 좌표계 보정: DeepSeek bbox(x≤940,y≤873) ≠ 150dpi 렌더(849×1324) → 스케일 캘리브레이션해야 crop.
- 띄어쓰기 붕괴 페이지(p121류) 탐지/재처리.

#### 미커밋 변경 (이번 세션)
- `scripts/mineru2org.py`: `num:t→num:nil`(헤딩 자동번호 끔, GLG 요청). 물리학강의/자연철학강의 재빌드 시 반영.
- `scripts/deepseek_ocr_client.py`: `--pages` 옵션 추가(오라클용).
- (자연철학강의 org는 GLG가 직접 손봄 — 에이전트 미변경)

### 다음 한 걸음

- [완료] gpu1i DeepSeek-OCR 서빙·한국어 실측·API 계약 파악.
- [완료] pdf-craft clone `~/repos/3rd/pdf-craft`(v1.0.13) + 코드 정독(in-process 확인).
- [✅완료] **DeepSeek-OCR thin-client 신설** — `scripts/deepseek_ocr_client.py`(PyMuPDF 페이지렌더 +
  페이지별 grounding chat + 블록 파서 → MinerU 호환 md + `_blocks.json` 근거) + `./run.sh deepseek-parse`
  (터널 자동 gpu1i:8000, mineru-parse 미러). 검증: 물리학강의 p490(수식 11블록 `\[\]`+인라인 `\(\)`) /
  p120(sub_title→`##`). 1.0~2.5s/page. 산출 `<OUT>/<doc>/{<doc>.md, <doc>_blocks.json}`.
  - ⚠️ OCR 변이 관찰: 렌더 경로(PyMuPDF vs pdftoppm)에 따라 `N_+`→`N_4`/`N₄` 미세차. 렌더 충실도가 OCR에 영향(저우선 튜닝).
### ✅ A 블록 (물리학강의 본문 마무리) — 완료. 위 ★★★ 최신 섹션 참조.

측정으로 길 확정: 물리학강의(그림 200+)는 **MinerU 베이스 유지**, DeepSeek는 깨진 자리 **오라클**로만. (아래는 실행 당시 메모, 보존)

1. **깨진 토큰 대조표 완성** — 이미 오라클 배치 떠 있음: `/tmp/dsoracle2/물리학강의001/물리학강의001_blocks.json`
   (30페이지). org의 깨짐 후보 ~40개(latin-glued + 한자 garbage; 의도병기 DNA/QCD/ma/八正道/半整數 등은 제외).
   각 깨진 토큰 → content_list로 page_idx → DeepSeek 판독으로 올바른 토큰 확정 → 대조표.
   - 반복 토큰은 **token 규칙 하나로**(예 `mosaic→톰슨` 본문+인덱스 3곳). NEXT 교훈: 반복깨짐=규칙 1개가 literal 수십 대체.
   - ⚠️ `/tmp/`는 휘발 — 새 세션에선 `deepseek-parse --pages ...` 다시 떠야 할 수 있음(빠름, ~1분).
2. **GLG 승인** 후 config `literal`/`token`에 일괄 적용.
3. **재빌드**: `mineru2org.py`(num:nil 반영됨) → `nix develop --command ./run.sh org2epub-build …` → epubcheck 0/0/0.
   (zip은 flake에 들어갔으니 nix develop 안에서 돌릴 것.)
4. 의도병기(나노nano, F=ma, 짝even, 보오손boson, corpuscle)는 **건드리지 말 것**.

### 그 외 백로그
- image 블록 — DeepSeek asset 없음. 그림책은 MinerU crop 유지(DeepSeek bbox crop은 좌표보정 후 검토).
- DeepSeek 클라 개선(위 "후속" 참조): `## ##` strip, bbox 캘리브레이션, 띄어쓰기 붕괴 탐지.
- [가능·GPU 무관] `scanbook/eval/` 스캐폴딩 + 6종 샘플 페이지셋 + 총교정비용 점수표.

---

## ★★★ 자연철학강의 — 장/고정마커절/소절 EPUB 성공 (2026-06-02 17:25)

**세 번째 책. 십우십도 구조 충실 복원 + 엔진 4번째 핸들러.**
《장회익의 자연철학 강의》(612쪽) → **장10/절30/소절122** → EPUB **epubcheck 0/0/0**(6.6MB).

### 엔진 개선 (mineru2org.py)

| 추가 | 내용 |
|------|------|
| `reconstruct_chapsec()` | 장(章)`*`/절(고정마커)`**`/소절`***`. 절 = `역사 지평`/`내용 정리`/`해설 및 성찰` 고정 3종(공백 무시 매칭). 장은 config `chapters.match`(OCR형 십우도 구절)로 잡고 `title` 권위 출력(김들이다→길들이다, 저 Coconut에→저잣거리에). config `section_markers` 로 디스패치 |
| `demath_headings()` | **헤딩 내 인라인 수식 평문화** — `*** \(g_{\alpha\beta}\) 읽어내기`→`g_α β`. 헤딩 수식이 nav/TOC SVG 참조 만들어 ox-epub 패키징 누락(RSC-007) → 그리스문자·기호 유니코드로 차단. **세 책 공통 영속 개선** |

이제 mineru2org.py가 **3가지 책 형태**를 다룸: ① `chapters`(번호절) 2단=물질생명인간 ② `parts`+`lectures` 3단 부/강/소절=물리학강의 ③ `section_markers` 장/고정마커절/소절=자연철학강의.

### 산출/설정

- config: `scripts/corrections/자연철학강의.json`. 산출: `scanpdf/work/자연철학강의/mineru/`.
- 재현 3-command + 구조 특이점 = `mineru/README.md`.

### 본문 교열 — 완료 (2026-06-02 18:10, Opus 토큰 우선)

1. **앎 safe_regex 140건** — `얇/앉/않/읽+조사→앎`(장회익 핵심어, 이 책은 얇 변이 우세).
   `은/을/음` 제외로 `얇은 책`(정상) 보호. 《물질생명인간》 검증 규칙 재사용.
2. **토큰 literal 19건** — `지녔던`,`돌멩이`,`보냈는데`,`되짚어`,`탈바꿈할`,`다녔다`,`힉스` 등.
3. **잔존 ~0** — 남은 영문혼입은 전부 **의도 병기**(텐서metric, 흑체black, 멘토mentor…) = 오류 아님.
4. EPUB 재빌드 **0/0/0**. **물리학강의보다 깔끔** — 토큰 우선을 처음부터 적용(GPT 문장 패스 불필요).
5. back matter(부록 A.1~A.13, 문헌, 찾아보기) 구조는 1차 수준 — 필요시 다듬기(저우선).

**→ 자연철학강의는 구조+EPUB+본문교열 모두 완료. 커밋 대기.**

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

### 본문 교열 — 1차 완료 (2026-06-02 17:50)

**GPT-5.4 문장 패스 191건 + 토큰 정리 25건 = config literal 216개 적용.** EPUB 재빌드 0/0/0.

- **GPT-5.4 async 2턴**(de1743b4→bdf1c2d9, $6.4): 강 순서로 B류 깨진 span 191건을 문맥 복원,
  전부 `{from,to}` config literal로(재현성 유지). 전수 클린 매칭 검증.
- **토큰 consolidation**(힣 지시): 문장 패스가 놓친 **반복 토큰** ~80건을 토큰 규칙 17개로 일괄 청소.
  - `되REST기/되.sql기→되돌리기`(REST·sql=돌리 OCR 변이, ~65건!), `알-growing→알갱`, `나velop니다→나뉩니다` 등.
  - 교훈: **반복 깨짐은 토큰 규칙 하나가 문장 literal 수십 개를 대체**. OCR이 같은 단어(되돌리기)를
    `되REST기`/`되.sql기`/`되cest기` 여러 형태로 깨뜨려서 문장 단위로는 못 잡음.
- **잔존**: 진짜 깨짐 ~10개 하드 1-off(`vite요`,`round습니다`,`corpuscle`,`Guq`,`mosaic`; 일부 페이지 이미지 필요).
  나머지 "잔존"은 **의도 병기**(`나노nano`,`ma`=F=ma,`mg`무게,`짝even`/`홀odd`,SI접두어) — 오류 아님, 건드리지 말 것.
- ⚠️ **보오손 보존**(찾아보기 `보오손(boson)` = 책 의도 표기).

#### ★ 다음 — 물리학강의는 Opus가 쭉 밀고 간다 (힣 지시 2026-06-02)

GPT 문장 패스가 반복 깨짐을 너무 많이 남겼다(토큰 정리로 ~80건 수습). 하드 1-off와
최종 품질은 **Opus가 직접 통독하며 밀고 가는 게 맞다**. 자연철학강의는 토큰 우선으로
Opus가 처음부터 깔끔하게 끝냈으니, 물리학강의도 같은 손길로 마저.

- **하드 1-off ~10개**: `vite요`,`round습니다`,`corpuscle들로`,`Guq은`,`mosaic은` 등.
  `pages_hi` 현재 0024~0055만 → 필요 구간 추가 렌더(`./run.sh scanpdf2org-render`) 후 판정.
- **config 슬림화**: 토큰 규칙이 되돌리기 문장 literal 다수를 redundant화. 216→축소 가능
  (redundant 문장 literal 제거 후 토큰 규칙만 — 위험 낮을 때 별건).
- `candidate_regex` 노이즈(A류 false alarm 844) 좁히기 — config만.
- 의도 병기(나노nano, F=ma, 짝even, 보오손boson)는 **건드리지 말 것**.

#### 기타

- 어제 vision seed(`org/01강-seed.org`, `org/물리학강의.org` 골격) **은퇴** — 골격은 config 재료로 소진. MinerU 산출이 primary.
- 무거운 `mineru-client/out/물리학강의001/` (origin/layout PDF ~750MB) 정리 가능.
- 다음 책: 자연철학강의 / 물리의정석 / 인공지능시대.

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

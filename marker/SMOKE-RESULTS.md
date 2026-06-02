# marker smoke test — 물질생명인간 p86–91 (2026-06-02)

scanpdf2org 보조 OCR/레이아웃 경로로 marker-pdf를 검증한 첫 smoke. thinkpad CPU.

## 대상

- 입력: `marker/smoke/물질생명인간-p86-91.pdf` (물리 p86–91 = 인쇄 p90–95, 6쪽, 2장 2절)
- 기준선: vision-only Opus 5병렬 전사 `scanpdf/work/물질생명인간/org/02장-02절.org`
- 산문 위주 구간 (수식·표 없음). LaTeX 처리력은 이번에 평가 못 함 — 별도 수식 구간 필요.

## 환경 / 재현

NixOS + PyPI wheel 충돌을 두 가지로 우회:

1. `nix develop` 안에서 `uv run` → 셸 PYTHONPATH가 nix python3.13 Pillow를 주입해 `_imaging` ImportError.
2. `nix develop` 밖에서 venv 직접 실행 → PyPI numpy/torch가 `libstdc++.so.6` 못 찾음.

해결: **venv 바이너리 직접 실행 + PYTHONPATH 제거 + nix-ld libstdc++ 공급**.

```bash
GCC=/nix/store/<gcc-14.3.0-lib>/lib
env -u PYTHONPATH \
    LD_LIBRARY_PATH="$GCC:/run/current-system/sw/share/nix-ld/lib" \
    TORCH_DEVICE=cpu \
    marker/.venv/bin/marker_single <INPUT.pdf> --output_dir marker/out --output_format markdown
```

설치: `nix develop --command uv sync --directory marker` (venv 5.1G — torch 2.12 + surya-ocr 0.17 + transformers 4.57).

## 시간 / 비용 (thinkpad CPU)

| 항목 | 값 |
|------|-----|
| marker 내부 처리 시간 | **1448.7s (~24분)** / 6쪽 |
| wall (모델 258M 다운로드 포함) | ~29.5분 |
| 페이지당 | **~4분/쪽** |
| 병목 | "Recognizing Text" 단계 23분 (52블록, 최대 140s/block) |
| 261쪽 책 환산 | **~17시간 CPU** |

→ CPU 단독으로는 책 단위 비현실적. GPU/서버 필요.

tesseract(`ocr-pdf`) 비교: 초 단위로 빠르지만 한글 품질 사용 불가
("무 엇 인 가", "온 쟁 명"=온생명 오독, "라 세 프스키" 분절).

## 품질 — 핵심 발견 (기준선 가정 반전)

marker(surya OCR) 출력은 tesseract와 차원이 다르며, 대체로 **vision-only baseline보다
원문에 더 충실**했다. `diff_review.py`로 두 전사본을 정렬하니 **30개 충돌점**이 나왔고
(세/셰 같은 반복은 규칙 1개로 수렴), 페이지 이미지로 판정한 결과:

**marker 정답 / vision 오류 (다수):**

| 원문(이미지 확인) | marker | vision baseline | vision 오류 유형 |
|------|--------|------|------|
| `93쪽의 각주 4` | 93쪽 ✓ | **89쪽** ✗ | 숫자 오기 |
| `라세프스키` (반복 9회) | 라세 ✓ | **라셰** ✗ | 표준표기 무단 정규화 |
| `그 기능을 초래할` | 초래할 ✓ | **결정짓는** ✗ | 단어 치환 |
| `서술함에 있어서는 필연적으로` | ✓ | **있어서나 정의함에 있어서나** ✗ | 구절 환각 |
| `현상에 대해 관심을` | 대해 ✓ | (누락) ✗ | 어절 누락 |
| `말이 되냐고` | 되냐고 ✓ | **되느냐고** ✗ | 어절 추가 |
| `연유이기도 하다` | (이미지 `이기도`) | 일부 어절 누락 | 탈자 |

**vision 정답 / marker 오류 (반증 — 중요):**

| 원문(이미지 확인) | marker | vision | marker 오류 유형 |
|------|--------|------|------|
| `버금가는` | **버금기는** ✗ | 버금가는 ✓ | OCR 오독(가→기) |

**핵심 결론 — 양방향 판정 필수:**

- vision-only 전사는 유창하지만 **"확신에 찬 환각/정규화/누락"** 실패 모드가 있다. 원문 대조 없이는 안 보인다.
- marker(OCR)는 충실하지만 **가끔 글자 오독**(가→기)을 한다. 구조(heading level, 각주 위치)도 약하다.
- **어느 엔진도 절대 권위가 아니다.** 둘을 diff 떠서 갈린 곳만 이미지로 판정하면 양쪽 약점을 동시에 잡는다.

## 도구 — diff_review (품질 가드 핵심)

`marker/scripts/diff_review.py` (순수 stdlib, NixOS flake python 그대로 실행):

- 두 전사본을 **공백·괄호류 제거 후** 정렬(`difflib`) → 띄어쓰기/괄호 스타일 노이즈 제거, **실제 내용 차이만** 추출.
- 각 충돌점에 ±문맥과 `marker ↔ vision` 치환/삽입/누락 라벨.
- LLM/사람은 **페이지 전체 재독 대신 충돌점 N개만 이미지로 판정**.

```bash
./run.sh marker-pdf  <INPUT.pdf> [OUTPUT_DIR]      # 충실 OCR 전사 (CPU)
./run.sh marker-diff <marker.md> <vision.org>      # 충돌점 추출 → 판정 대상
```

수고 정량(2장 2절 6쪽): 6쪽 이미지 전부 재독 대신 → 충돌점 ~30개(반복 수렴 시 ~12 판정).

### marker 약점 (여전히 정규화 필요)

- 인용 괄호 정규화: 원문 `[Rosen 1991, …]` → marker `(Rosen 1991, …)`.
- 쪽 경계에서 문장 중간에 빈 줄 삽입(문단 분리 깨짐) → 재결합 필요.
- 문장 사이 공백 누락(`본다.여기서`), 음절 띄어쓰기 흔들림.
- 헤더 레벨 미부여(`heading_level: null`) — 절 제목은 잡지만 위계는 후처리 필요.
- Markdown 산출 → Org 정규화는 여전히 에이전트 작업.

## 가설 검증 결과

- "OCR/marker 초안이 에이전트 읽을 분량을 줄인다" — **부분 참**. 깨끗한 초안은 맞지만,
  vision의 환각을 잡으려면 에이전트가 결국 페이지 이미지와 라인 대조를 해야 한다.
  단, **방향이 바뀜**: marker가 vision을 검수하는 게 아니라 marker가 더 신뢰 가능한 1차본이고
  vision/에이전트가 레이아웃·애매문자·구조를 보강하는 역할이 맞다.
- "최종 품질 baseline 근접 + wall/cost 감소면 성공" — thinkpad CPU에선 **wall time 악화**(17h/책).
  GPU 서버라면 재평가 가치 큼.

## 권고 (GLG 결정 대기)

1. **단기**: marker는 **검수/대조 레이어**로 채택 가치 높음. 완성된 vision org를 marker 출력과
   diff 떠서 숫자·이름·구절 오류를 잡는 QA 패스. CPU로도 장별로는 감당 가능.
2. **수식/표 구간** 별도 smoke 필요(이번은 산문만). 4장·물리의정석 등으로 LaTeX 처리력 평가.
3. **책 단위 1차 전사**를 marker로 돌리려면 GPU(서버) 필요. thinkpad CPU 단독은 비추.
4. `run.sh`에 `marker-pdf` 래퍼 추가 여부는 위 결정 후. 환경 우회(PYTHONPATH/libstdc++)는 래퍼에 박아야 함.

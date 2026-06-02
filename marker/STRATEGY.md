# 스캔책 전사 품질 가드 전략 — diff-guided adjudication

목표: **LLM이 적은 수고로 높은 품질을 내는** 재현 가능한(NixOS) 스캔책 → Org/EPUB 전사 전략.

근거 데이터: `marker/SMOKE-RESULTS.md` (물질생명인간 2장 2절 6쪽 smoke, 2026-06-02).

---

## 1. 문제 — 단일 엔진은 모두 실패 모드가 있다

| 경로 | 강점 | 실패 모드 |
|------|------|-----------|
| tesseract OCR | 빠름 | 한글 깨짐("온 쟁 명"). **사용 불가** |
| vision-only LLM (Opus 5병렬) | 유창, 레이아웃·구조·애매글자 강함 | **확신에 찬 환각/정규화/누락** — 숫자(89↔93), 고유명사 무단 표준화(라세→라셰), 구절 환각, 어절 탈락. 원문 대조 없이는 안 보임 |
| marker (surya OCR) | 원문 충실(숫자·고유명사 신뢰) | 가끔 글자 오독(가→기), 구조 약함(heading level null, 각주 위치, [..]→(..) 정규화, 쪽경계 문장 분리) |

→ **vision은 안 본다고 안심할 수 없고, marker는 충실하지만 완벽하지 않다.** 어느 쪽도 단독으로 신뢰 불가.

## 2. 전략 — 두 충실/유창 전사본을 교차검증, LLM은 충돌점만 판정

```
        marker(충실 OCR)  ┐
                          ├─→ diff_review ─→ 충돌점 N개 ─→ LLM이 이미지로 판정 ─→ 정정
        vision(유창 구조)  ┘                  (페이지 전체 재독 X)
```

핵심: **LLM이 페이지 전체를 다시 읽지 않는다.** 자동 diff가 갈린 곳만 띄우고, LLM은
그 N개만 페이지 이미지와 대조해 원문에 맞는 쪽을 채택한다. 양쪽 약점(vision 환각 +
marker 오독)을 동시에 잡는다. — 이것이 "덜 수고 + 품질 가드".

도구: `marker/scripts/diff_review.py` — 공백·괄호 노이즈 제거 후 `difflib` 정렬.
`./run.sh marker-diff <marker.md> <vision.org>`.

## 3. 두 운용 모드

### Mode A — 신규 책: marker-primary (LLM 수고 최소)

1. `./run.sh marker-pdf <book.pdf>` → 충실 Markdown 1차본. (CPU 비싸므로 **서버 오버나잇**, §5)
2. LLM **1회 구조 패스**: marker md → Org. heading level 부여, 각주 위치 복원, 외래어 인라인,
   인용 괄호 `[..]` 복원, 쪽경계 분리 문장 재결합.
3. 충돌/애매: marker 자체를 신뢰하되, **marker가 불확실 플래그한 블록**(향후 신뢰도 점수 활용)만 이미지 대조.
4. 장당 몇 페이지 스팟체크.

→ vision 5병렬 전면 전사를 **생략**. LLM은 전사가 아니라 구조화 + 소수 판정만. API 비용·시간 대폭 절감.

### Mode B — 기존 vision 전사 QA (이미 만든 1~4장 검수)

1. 해당 구간 `./run.sh marker-pdf` 로 marker 충실본 생성.
2. `./run.sh marker-diff <marker.md> <vision.org>` → 충돌점.
3. LLM이 충돌점만 이미지 판정 → vision org의 환각/정규화/탈자 정정.

→ 이미 완성된 vision 자산을 버리지 않고 품질만 끌어올린다. 1~4장 사람 검수 시 바로 적용.

## 4. 채택 우선순위 (권고)

1. **Mode B 즉시 적용** — 1~4장 vision org를 marker diff로 QA. 가장 빠른 품질 이득.
2. **수식/표 smoke** — 이번 smoke는 산문만. 4장 또는 `물리의정석`으로 marker LaTeX·표 처리력 평가. Mode A 가능 여부의 관문.
3. 위 통과 시 **Mode A를 신규 책 기본**으로.

## 5. NixOS 재현 — 환경 우회를 도구에 내장

PyPI wheel(torch/numpy/surya) ↔ NixOS 충돌 2종을 명령에 박았다:

- `nix develop` 셸의 `PYTHONPATH`가 nix python Pillow를 주입 → `_imaging` 충돌 → **PYTHONPATH 제거**.
- venv를 셸 밖에서 돌리면 PyPI wheel이 `libstdc++.so.6` 못 찾음 → **`LD_LIBRARY_PATH=/run/current-system/sw/share/nix-ld/lib`**.
  nix-ld 경로는 store hash 하드코딩 없이 머신 간 재현 가능(검증됨).

```bash
# 설치 (lock 고정)
nix develop --command uv sync --directory marker   # venv ~5G, torch 2.12 + surya 0.17

# 실행 (env 우회는 run.sh가 내장)
./run.sh marker-pdf  <INPUT.pdf>
./run.sh marker-diff <marker.md> <vision.org>
```

- `marker/pyproject.toml` + `marker/uv.lock` 로 의존성 고정. flake와 별개 uv 레이어(nixos-config와 nixpkgs lock 정렬로 store 중복 최소).
- **CPU 비용**: ~4분/쪽 → 261쪽 ≈ 17h. thinkpad 단독 비현실적.
  flake가 portable하므로 **NUC/Oracle 서버에서 tmux 오버나잇** 권장(같은 `marker/` 그대로).

## 6. 다음 (미해결)

- marker **신뢰도/품질 점수**를 읽어 불확실 블록 자동 플래그 → Mode A의 이미지 판정 대상 자동화.
- heading level·각주 위치 후처리 스크립트(marker md → Org 구조 정규화).
- 수식/표 구간 marker 평가 후 LaTeX → Org 수식 변환 경로 결정.
- GPU 가용 시 marker wall time 재측정.

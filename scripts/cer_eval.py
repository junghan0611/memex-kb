#!/usr/bin/env python3
"""cer_eval — 전사본의 **정량 CER/WER**. `diff_review` 와 역할이 다르다.

- `diff_review` = 사람이 판정할 **충돌점 탐색**. 거기 `ratio` 는 difflib 정렬
  유사도이지 편집거리가 아니다. 그걸 CER 이라 부르면 안 된다.
- `cer_eval`(이 파일) = **정규화 편집거리 / 기준길이**. 엔진 줄세우기용 숫자.

정규화는 `diff_review.normalize()` 를 그대로 재사용한다 — 축이 갈리면 두 도구
숫자를 나란히 못 놓는다. 그 모듈의 "대칭 원칙" 주석이 이 숫자의 전제다.

## projection (GPT 교차검토 2026-07-30)

각주를 잘 잡는 엔진이 손해 보는지 보려면 한 숫자로는 안 된다. 3종을 따로 낸다.

- `body`        : 본문 + 각주본문 (기본)
- `body-no-fn`  : 각주 제외한 본문만
- `fn-only`     : 각주 본문만

## 편집거리 계산

전권(10만 자)에 순수 DP 를 돌리면 10^10 연산이라 못 쓴다. `SequenceMatcher` 로
일치 블록을 먼저 잡고 **불일치 구간에만** two-row Levenshtein 을 돌려 합산한다.
일치 블록을 지나는 정렬이 최적이라는 보장은 없으므로 결과는 엄밀히는 **상계**지만,
일치 블록이 길어 실질적으로 최적과 같다. 이 성질을 숨기지 말고 출력에 명시한다.

## gold 의 자격

기준본이 vision 전사본이면 그건 **vision silver** 이지 absolute gold 가 아니다.
gold 가 틀린 자리에서는 맞은 엔진이 벌점을 받는다. 그래서 이 도구의 출력은
"vision-gold 기준 CER" 이고, 사람이 페이지 이미지로 판정한 구간에 대해서만
"adjudicated CER" 이라 부를 수 있다. 라벨을 섞지 말 것.

순수 stdlib.
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import re
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "diff_review", Path(__file__).resolve().parent / "diff_review.py"
)
_dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dr)

PROJECTIONS = {"body": "keep", "body-no-fn": "drop", "fn-only": "only"}


def levenshtein(a: str, b: str) -> int:
    """two-row DP. 짧은 구간에만 쓴다."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(a) + 1))
    for j, cb in enumerate(b, 1):
        cur = [j]
        for i, ca in enumerate(a, 1):
            cur.append(min(prev[i] + 1, cur[i - 1] + 1, prev[i - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def edit_distance(hyp: str, ref: str) -> tuple[int, int]:
    """(편집거리, 불일치 구간 수). 일치 블록 밖에서만 DP."""
    sm = difflib.SequenceMatcher(None, hyp, ref, autojunk=False)
    dist = blocks = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        blocks += 1
        dist += levenshtein(hyp[i1:i2], ref[j1:j2])
    return dist, blocks


def _anchor_head(hay: str, needle: str) -> int | None:
    for n in (60, 40, 30, 24, 18):
        i = hay.find(needle[:n])
        if i >= 0:
            return i
    return None


def _anchor_tail(hay: str, needle: str, after: int = 0) -> int | None:
    """needle 끝에서 물러나며 hay 안의 대응 끝점을 찾는다."""
    back_limit = max(len(needle) // 4, 80)
    for back in range(0, back_limit, 20):
        hi = len(needle) - back
        tail = needle[max(hi - 40, 0):hi]
        if len(tail) < 18:
            break
        i = hay.rfind(tail)
        if i > after:
            return i + len(tail)
    return None


def trim_to(hyp: str, ref: str, min_block: int = 24) -> str:
    """hyp 을 ref 범위에 대응하는 구간으로 자른다.

    정확일치 앵커(40자 창)는 OCR 차이가 흩어져 있으면 실패한다 — 실제로 Upstage
    꼬리에서 그랬고, 그러면 범위를 넘는 278자가 통째로 오류로 잡혀 CER 이 부풀었다.
    그래서 정합 블록으로 잡는다: ref 와 실제로 일치한 첫/마지막 덩어리 바깥은
    이 구간의 내용이 아니다.

    앵커를 못 찾으면 자르지 않는다 — 조용히 어긋난 범위를 비교하면 숫자가 뒤집힌다.
    """
    sm = difflib.SequenceMatcher(None, hyp, ref, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size >= min_block]
    if not blocks:
        return hyp
    return hyp[blocks[0].a: blocks[-1].a + blocks[-1].size]


def locate_span(ref_full: str, probe: str) -> tuple[int, int] | None:
    """전권 ref 안에서 probe(구간 산출물)에 대응하는 범위를 찾는다.

    꼬리 앵커를 probe 끝에서 바로 잡으면 안 된다 — probe 가 ref 구간을 넘어
    끝나면(엔진이 다음 쪽까지 물고 온 경우) 앵커가 없어 통째로 실패한다.
    그래서 시작 앵커를 먼저 박고, 뒤에서부터 조금씩 물러나며 찾는다.
    """
    start = _anchor_head(ref_full, probe)
    if start is None:
        return None
    end = _anchor_tail(ref_full, probe, after=start)
    if end is None:
        return None
    return start, end


def main() -> int:
    ap = argparse.ArgumentParser(
        description="전사본 정량 CER (정규화 편집거리 / 기준길이)"
    )
    ap.add_argument("hyp", nargs="+", help="엔진 산출물 경로(여러 개면 나란히 비교)")
    ap.add_argument("--ref", required=True, help="기준본(gold/vision silver) 경로")
    ap.add_argument(
        "--projection", default="body", choices=sorted(PROJECTIONS),
        help="body(본문+각주) | body-no-fn(각주 제외) | fn-only(각주만)",
    )
    ap.add_argument(
        "--span", action="store_true",
        help="ref 가 전권이고 hyp 이 일부 구간일 때 대응 범위만 잘라 비교",
    )
    ap.add_argument("--label", default="vision-gold",
                    help="기준본 성격 라벨(예: vision-gold / adjudicated)")
    ap.add_argument(
        "--noise", action="append", default=[], metavar="REGEX",
        help="본문이 아닌 반복 요소를 정규화 후 제거(반복 지정 가능). "
             "쪽번호+러닝헤드는 책마다 달라 하드코딩하지 않는다. "
             r"예: --noise '\d{1,3}물질,생명,인간'",
    )
    args = ap.parse_args()

    fn = PROJECTIONS[args.projection]

    def prep(raw: str) -> str:
        s = _dr.normalize(raw, footnotes=fn)
        for pat in args.noise:
            s = re.sub(pat, "", s)
        return s

    ref_full = prep(Path(args.ref).read_text(encoding="utf-8"))

    print(f"# cer_eval  projection={args.projection}  기준={args.label}")
    print(f"ref: {args.ref}  (정규화 {len(ref_full):,}자)")
    if args.label == "vision-gold":
        print("⚠️ 기준본이 vision 전사본이면 absolute gold 가 아니다 — gold 가 틀린 "
              "자리에서는 맞은 엔진이 벌점을 받는다.")
    print("⚠️ 편집거리는 일치블록 밖에서만 DP 한 **상계**다(실질 최적).")
    print("=" * 76)

    hyps = {}
    for path in args.hyp:
        h = prep(Path(path).read_text(encoding="utf-8"))
        if not h:
            # fn-only 는 org `[fn:...]` 정의줄에 의존한다. md/txt 산출물은 각주를
            # 본문 인라인으로 담으므로 추출 자체가 불가능하다 — 0자를 CER 100%
            # 로 보고하면 "엔진이 각주를 다 틀렸다"는 거짓 결론이 된다.
            print(f"⚠️ {path}: projection={args.projection} 에서 추출된 내용 0자 "
                  f"— 이 포맷에 해당 구조가 없다. 비교 불가로 건너뛴다.")
            continue
        hyps[path] = h

    ref = ref_full
    if args.span and hyps:
        # ⚠️ 엔진마다 제 구간을 잡게 두면 기준 길이가 달라져 사과 대 사과가 아니다.
        # 모든 산출물의 교집합을 **공통 기준 구간**으로 고정한다.
        spans = {}
        for path, h in list(hyps.items()):
            loc = locate_span(ref_full, h)
            if loc is None:
                print(f"⚠️ {path}: ref 안에서 구간 앵커 실패 — 건너뛴다")
                hyps.pop(path)
                continue
            spans[path] = loc
        if not spans:
            return 1
        lo = max(s for s, _ in spans.values())
        hi = min(e for _, e in spans.values())
        if hi <= lo:
            print("⚠️ 산출물들의 구간이 겹치지 않는다 — 공통 기준을 만들 수 없다")
            return 1
        ref = ref_full[lo:hi]
        print(f"공통 기준 구간: ref[{lo}:{hi}] = {len(ref):,}자 "
              f"(개별 구간 {', '.join(f'{Path(p).name}:{e-s:,}' for p,(s,e) in spans.items())})")
        print("-" * 76)

    rows = []
    for path, h in hyps.items():
        hh = trim_to(h, ref) if args.span else h
        dist, blocks = edit_distance(hh, ref)
        cer = dist / max(len(ref), 1)
        rows.append((Path(path).name, len(hh), len(ref), dist, blocks, cer))

    if not rows:
        return 1
    w = max(len(r[0]) for r in rows)
    print(f"{'산출물':<{w}}  {'hyp자':>8} {'ref자':>8} {'편집거리':>8} {'구간':>6} {'CER':>8}")
    for name, lh, lr, d, b, c in rows:
        print(f"{name:<{w}}  {lh:8,} {lr:8,} {d:8,} {b:6,} {c*100:7.3f}%")
    if len(rows) > 1:
        best = min(rows, key=lambda r: r[5])
        print(f"\n최소 CER: {best[0]} ({best[5]*100:.3f}%)")
        print("※ 순위는 이 projection·이 구간 한정. 다른 projection 도 함께 볼 것.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

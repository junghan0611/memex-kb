#!/usr/bin/env python3
"""diff_review — marker(OCR 충실본) ↔ vision(구조본) 충돌점 추출기.

목적: 두 전사본을 정렬해 **내용이 갈리는 지점만** 뽑는다. LLM/사람은 페이지
전체를 다시 읽지 않고 이 충돌점들만 페이지 이미지로 판정(adjudicate)한다.
"덜 수고 + 품질 가드" 전략의 핵심 도구.

설계 메모:
- 한글 OCR은 띄어쓰기가 엔진마다 크게 다르다("어 떤" vs "어떤"). 띄어쓰기 차이를
  전부 충돌로 잡으면 노이즈 폭발 → **공백을 모두 제거한 문자열**로 diff 해서
  실제 내용 차이만 남긴다.
- 괄호/따옴표 스타일도 엔진마다 다르다([Rosen]/(Rosen), ""/'' 등) → 정규화로 제거.
  단 systematic bracket 차이는 따로 카운트해 보고만 한다.
- 각주 마커(<sup>N</sup>, [fn:...])는 위치가 달라 노이즈 → 제거.

순수 stdlib. NixOS flake python으로 그대로 실행 가능(컴파일 의존성 없음).
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys

# 정규화에서 제거할 괄호/따옴표류 (양쪽 엔진 스타일 차이 흡수)
BRACKETS = "[](){}「」『』〈〉《》""''\"'…"


def strip_markup(text: str) -> str:
    """org/md 구조 마크업 제거 — 내용 문자만 남긴다."""
    out = []
    for line in text.splitlines():
        s = line
        # org 주석/속성 라인 통째 제거
        if re.match(r"^\s*#\+?", s):
            continue
        if re.match(r"^\s*:[A-Z_]+:\s*$", s):
            continue
        # 각주 정의 라인(org): "[fn:foo] 내용" → 제거 (위치가 달라 노이즈)
        if re.match(r"^\s*\[fn:[^\]]+\]", s):
            continue
        out.append(s)
    s = "\n".join(out)
    # 인라인 각주 마커
    s = re.sub(r"<sup>\d+</sup>", "", s)
    s = re.sub(r"\[fn:[^\]]+\]", "", s)
    # md/org heading 기호, 강조 기호
    s = re.sub(r"^[#*]+\s*", "", s, flags=re.MULTILINE)
    s = s.replace("**", "").replace("*", "")
    return s


def normalize(text: str) -> str:
    """공백·괄호류 제거한 순수 내용 문자열."""
    s = strip_markup(text)
    s = re.sub(r"\s+", "", s)
    for ch in BRACKETS:
        s = s.replace(ch, "")
    return s


def context(s: str, i: int, j: int, pad: int = 22) -> str:
    a = max(0, i - pad)
    b = min(len(s), j + pad)
    pre, post = s[a:i], s[j:b]
    mid = s[i:j]
    return f"…{pre}【{mid}】{post}…"


def main() -> int:
    ap = argparse.ArgumentParser(description="marker ↔ vision 충돌점 추출")
    ap.add_argument("marker", help="marker Markdown 경로 (OCR 충실본)")
    ap.add_argument("vision", help="vision Org/텍스트 경로 (구조본)")
    ap.add_argument("--max-block", type=int, default=80,
                    help="이 길이 초과 replace/indel 블록은 잘림/구조차로 보고 생략 (기본 80자)")
    args = ap.parse_args()

    with open(args.marker, encoding="utf-8") as f:
        m_raw = f.read()
    with open(args.vision, encoding="utf-8") as f:
        v_raw = f.read()

    M = normalize(m_raw)
    V = normalize(v_raw)

    sm = difflib.SequenceMatcher(None, M, V, autojunk=False)
    ratio = sm.ratio()

    divs = []
    truncated = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        mlen, vlen = i2 - i1, j2 - j1
        if max(mlen, vlen) > args.max_block:
            truncated += 1
            continue
        divs.append((tag, i1, i2, j1, j2))

    print(f"# diff_review")
    print(f"marker: {args.marker}")
    print(f"vision: {args.vision}")
    print(f"정렬 유사도(공백/괄호 무시): {ratio:.4f}")
    print(f"충돌점(판정 대상): {len(divs)}개")
    print(f"생략된 대형 블록(잘림/구조차 추정): {truncated}개")
    print("=" * 72)

    for n, (tag, i1, i2, j1, j2) in enumerate(divs, 1):
        m_seg, v_seg = M[i1:i2], V[j1:j2]
        print(f"\n[{n}] {tag}")
        print(f"  marker: {context(M, i1, i2)}")
        print(f"  vision: {context(V, j1, j2)}")
        # 힌트: 한쪽만 비었으면 삽입/누락
        if not m_seg:
            print(f"  ※ marker엔 없음 → vision 추가/환각 의심")
        elif not v_seg:
            print(f"  ※ vision엔 없음 → vision 누락 의심")
        else:
            print(f"  ※ 치환: '{m_seg}' ↔ '{v_seg}' → 이미지 대조 필요")

    print("\n" + "=" * 72)
    print("판정법: 각 충돌점을 페이지 이미지에서 찾아 원문과 일치하는 쪽을 채택.")
    print("smoke 1 경험상 숫자/고유명사/구절은 marker가, 애매문자/레이아웃은 vision이 강함.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

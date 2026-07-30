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
- 각주 **마커**(<sup>N</sup>, $^N$, [fn:...])는 위치가 달라 노이즈 → 제거.
  각주 **본문**은 남긴다(아래 대칭 원칙).

⚠️ 대칭 원칙 (2026-07-30) — 이 규칙을 깨면 엔진 비교 숫자가 통째로 무효가 된다.
gold 는 org, 엔진 산출물은 md/txt 다. **한쪽 포맷에서만 사라지는 내용이 있으면
그 차이가 엔진 오류로 계상된다.** 실측으로 잡힌 비대칭 4종을 여기서 없앤다:
  1. org 각주 정의줄 통째 삭제 → 각주를 잘 잡는 엔진이 벌점. (물질생명인간 gold
     기준 23줄 2,790자 = 전체의 2.55% 가 한쪽에서만 증발했다.)
  2. BRACKETS 에 곡선 따옴표(U+2018/2019/201C/201D)가 없어 인용부호가 diff 에 남음.
     (전권 delete 1,786건 중 1,691건 = 95% 가 이 노이즈였다.)
  3. md heading(`# 제목`)은 줄째로 삭제되는데 org heading(`* 제목`)은 마커만 제거 →
     제목 텍스트가 한쪽에만 남음.
  4. md 이미지 참조(`![](images/<hash>.jpg)`)와 HTML 표 태그가 본문 문자로 계상됨.

CER 은 이 모듈이 내지 않는다. 여기 `ratio` 는 difflib 정렬 유사도일 뿐
편집거리가 아니다 — 정량 CER 은 `scripts/cer_eval.py` 를 쓴다.

순수 stdlib. NixOS flake python으로 그대로 실행 가능(컴파일 의존성 없음).
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys

# 정규화에서 제거할 괄호/따옴표류 (양쪽 엔진 스타일 차이 흡수).
# ⚠️ 곡선 따옴표는 반드시 \u 이스케이프로 적는다 — 리터럴로 두면 편집기/인코딩이
# ASCII 로 눌러버려 조용히 빠진다(실제로 그렇게 U+0027 이 3번 중복돼 있었다).
BRACKETS = (
    "[](){}"
    "「」『』"      # 「」『』
    "〈〉《》"      # 〈〉《》
    "‘’“”"      # ‘’“”  ← 이게 빠져 있어 delete 노이즈 95% 를 만들었다
    "'\""                           # ASCII
    "…"                        # …
)

# 각주 마커 — 본문은 건드리지 않고 마커만 뗀다.
FOOTNOTE_MARKERS = (
    r"<sup>\s*\d+\s*</sup>",   # md/HTML
    r"\$\s*\^\{?\d+\}?\s*\$",  # MinerU LaTeX 위첨자: $^1$ / $^{12}$
    r"\[fn:[^\]]*\]",          # org 인라인 참조 + 정의줄 라벨
)


def strip_markup(text: str, footnotes: str = "keep") -> str:
    """org/md 구조 마크업 제거 — 내용 문자만 남긴다.

    footnotes: keep(본문 유지) | drop(각주 정의줄 제거) | only(각주 정의줄만)
    """
    out = []
    for line in text.splitlines():
        s = line
        # org 키워드 줄(#+TITLE, #+begin_quote …)만 통째 제거.
        # md heading(`# 제목`)은 여기서 걸리면 안 된다 — 아래에서 마커만 뗀다.
        if re.match(r"^\s*#\+", s):
            continue
        if re.match(r"^\s*:[A-Z_]+:\s*$", s):
            continue
        # org 각주 정의줄: 라벨만 떼고 본문은 **제자리에** 남긴다(대칭 원칙 1).
        # ⚠️ 문서 끝으로 모으지 말 것 — 구간(span) 비교에서 각주가 범위 밖으로
        # 밀려나 projection 이 무력해진다(2026-07-30 실제로 그랬다).
        is_fn = bool(re.match(r"^\s*\[fn:[^\]]*\]", s))
        if is_fn:
            s = re.sub(r"^\s*\[fn:[^\]]*\]\s*", "", s)
        if footnotes == "only" and not is_fn:
            continue
        if footnotes == "drop" and is_fn:
            continue
        out.append(s)

    s = "\n".join(out)

    # 각주 마커(본문 아님)
    for pat in FOOTNOTE_MARKERS:
        s = re.sub(pat, "", s)
    # md 이미지 참조는 내용이 아니다 — 통째 제거(대칭 원칙 4).
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    # md 링크는 표시 텍스트만 남긴다.
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    # HTML 태그(주로 MinerU 표) 제거
    s = re.sub(r"</?[a-zA-Z][^>]*>", "", s)
    # heading 마커만 제거 — md `#`+공백, org `*`+공백 (대칭 원칙 3)
    s = re.sub(r"^\s*#{1,6}\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s*\*+\s+", "", s, flags=re.MULTILINE)
    # 강조 기호
    s = s.replace("**", "").replace("*", "")
    return s


def normalize(text: str, footnotes: str = "keep") -> str:
    """공백·괄호류 제거한 순수 내용 문자열."""
    s = strip_markup(text, footnotes=footnotes)
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

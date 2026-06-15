#!/usr/bin/env python3
"""ROSSE syndication bundler (이슈 #4).

가든 canonical 노트 1개 → 매체별 복붙용 포맷 묶음 파일 1개.

완전 자동화(API 발행)는 1차 목표가 아니다. 개인 프로필 발행이라 Meta/네이버/티스토리
모두 공식 쓰기 API가 없거나 막혀 있다. 대신 이 스크립트는 각 매체의 **복붙 규격**에 맞춘
출력 블록을 한 파일에 모은다. 사람이 직접 복붙하거나, 브라우저 클로드가 그 파일을 읽고
각 면에 꽂는다.

memex-kb가 보관할 진짜 자산은 아래 PLATFORMS 명세(매체별 글자수·포맷클래스·링크규칙·함정)다.
이 dict가 SSOT. 문서 표는 `python syndicate.py specs` 로 생성한다.

------------------------------------------------------------------------------
입력 규약 (단순 마크다운 + YAML-lite front matter)
------------------------------------------------------------------------------

    ---
    title: 제목
    garden_url: https://notes.junghanacs.com/notes/20250324T110312
    ---

    ## 해설
    가든 canonical 해설 본문 (에이전트가 정리한 글).

    ## 원문
    링크드인/저널에 손가락으로 남긴 날것 원문. 편집 없음.

    ## 요약
    ### ko
    한국어 요약 (짧은 면용 — 매체 글자수에 맞춰 잘림).
    ### en
    English summary (optional).

포맷 클래스 3종:
  - 원문형(raw)     : 원문 + 가든링크            → 페이스북, 링크드인
  - 전문형(full)    : 해설+원문 전체 + 가든링크   → 네이버블로그, 티스토리
  - 요약형(summary) : 매체별 글자수 요약 + 가든링크 → 스레드, 트위터, 블루스카이, 인스타
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# SSOT — 매체별 포맷 지식. (글자수는 2026-06 기준; Meta/네이버 정책 변동 시 여기만 고친다.)
# ─────────────────────────────────────────────────────────────────────────────
RAW = "raw"          # 원문형: 원문 + 가든링크
FULL = "full"        # 전문형: 가든본 전체 + 가든링크
SUMMARY = "summary"  # 요약형: 매체별 글자수 요약 + 가든링크

PLATFORMS = [
    # key,        표시명,            클래스,    글자수상한,  요약언어, 비고/복붙 함정
    {
        "key": "facebook", "name": "페이스북", "cls": RAW, "limit": 63206,
        "lang": None, "link": "post",
        "note": "개인 프로필 = API 발행 불가, 복붙 전용. 첫 링크만 미리보기 언펄. 줄바꿈 보존됨. 사실상 길이무제한.",
    },
    {
        "key": "linkedin", "name": "링크드인", "cls": RAW, "limit": 3000,
        "lang": None, "link": "post",
        "note": "원문 캡처면(여기가 출발점). 모바일 ~210자/'…더보기' 1300자에서 접힘. 링크는 본문에 직접.",
    },
    {
        "key": "naver", "name": "네이버블로그", "cls": FULL, "limit": None,
        "lang": None, "link": "top+bottom",
        "note": "스마트에디터. 제목 별도. 가든본 전체 박기. 짜집기 글 금지(원문이 가든본에 내장). 마크다운 직접 안 먹음→붙이고 서식 보정.",
    },
    {
        "key": "tistory", "name": "티스토리", "cls": FULL, "limit": None,
        "lang": None, "link": "top+bottom",
        "note": "Open API 2024 폐쇄→복붙/브라우저. 마크다운 모드 지원. 가든본 전체.",
    },
    {
        "key": "threads", "name": "스레드", "cls": SUMMARY, "limit": 500,
        "lang": "ko", "link": "post",
        "note": "토큰에 발행권한 있음(후속 자동화 후보). 1차는 복붙. 500자.",
    },
    {
        "key": "twitter", "name": "트위터/X", "cls": SUMMARY, "limit": 280,
        "lang": "ko", "link": "post",
        "note": "무료 280자(프리미엄 25000). 링크는 t.co로 23자 고정 차지.",
    },
    {
        "key": "bluesky", "name": "블루스카이", "cls": SUMMARY, "limit": 300,
        "lang": "en", "link": "post",
        "note": "300 graphemes. AT Protocol(후속 자동화 쉬움). 링크 자동 단축 없음→URL 전체가 글자수.",
    },
    {
        "key": "instagram", "name": "인스타그램", "cls": SUMMARY, "limit": 2200,
        "lang": "ko", "link": "bio",
        "note": "캡션 2200자. 본문 링크 클릭 불가→'링크는 프로필' 명시. 이미지 필수.",
    },
]
PLATFORM_BY_KEY = {p["key"]: p for p in PLATFORMS}


# ─────────────────────────────────────────────────────────────────────────────
# 입력 파싱
# ─────────────────────────────────────────────────────────────────────────────
def parse_input(text: str) -> dict:
    """front matter + 해설/원문/요약 블록 파싱."""
    meta: dict = {}
    body = text

    fm = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if fm:
        for line in fm.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
        body = fm.group(2)

    sections = _split_sections(body)
    summary = sections.get("요약", "")
    return {
        "title": meta.get("title", "").strip() or "(제목 없음)",
        "garden_url": meta.get("garden_url", "").strip(),
        "해설": sections.get("해설", "").strip(),
        "원문": sections.get("원문", "").strip(),
        "ko": _subsection(summary, "ko").strip(),
        "en": _subsection(summary, "en").strip(),
    }


def _split_sections(body: str) -> dict:
    """`## 이름` 헤딩 단위로 본문을 쪼갠다."""
    out: dict = {}
    cur = None
    buf: list[str] = []
    for line in body.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            if cur is not None:
                out[cur] = "\n".join(buf).strip()
            cur = m.group(1).strip()
            buf = []
        else:
            buf.append(line)
    if cur is not None:
        out[cur] = "\n".join(buf).strip()
    return out


def _subsection(text: str, name: str) -> str:
    """`### ko` 같은 하위 헤딩 추출."""
    m = re.search(rf"^###\s+{re.escape(name)}\s*$\n(.*?)(?=^###\s|\Z)",
                  text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ""


# ─────────────────────────────────────────────────────────────────────────────
# 면별 포맷터
# ─────────────────────────────────────────────────────────────────────────────
def _link_line(url: str) -> str:
    return f"→ 자세히(가든): {url}" if url else "→ 자세히(가든): (가든 링크 미입력)"


def format_for(p: dict, data: dict) -> tuple[str, str | None]:
    """(본문, 경고) 반환."""
    url = data["garden_url"]
    cls = p["cls"]

    if cls == RAW:
        body = f'{data["원문"]}\n\n{_link_line(url)}'
    elif cls == FULL:
        parts = []
        if data["해설"]:
            parts.append(data["해설"])
        if data["원문"]:
            parts.append("─── 원문 ───\n\n" + data["원문"])
        parts.append(_link_line(url))
        body = "\n\n".join(parts)
    else:  # SUMMARY
        summary = data.get(p["lang"]) or data.get("ko") or ""
        if not summary:
            summary = "(요약 미작성 — 에이전트가 채울 것)"
        if p["link"] == "bio":
            tail = f"\n\n{_link_line(url)}\n(링크는 프로필 참조)"
        else:
            tail = f"\n\n{_link_line(url)}"
        body = summary + tail

    warn = None
    if p["limit"] is not None and len(body) > p["limit"]:
        warn = f"⚠️ {len(body)}자 / 상한 {p['limit']}자 — {len(body) - p['limit']}자 초과. 줄여야 함."
    return body, warn


# ─────────────────────────────────────────────────────────────────────────────
# 묶음 생성
# ─────────────────────────────────────────────────────────────────────────────
def build_bundle(data: dict, only: list[str] | None = None) -> str:
    targets = [p for p in PLATFORMS if (not only or p["key"] in only)]
    out = [
        f"# 배포 묶음 — {data['title']}",
        "",
        "> 각 매체 블록을 그대로 복붙. 브라우저 클로드는 매체명 헤딩을 보고 해당 면에 넣는다.",
        f"> 가든 canonical: {data['garden_url'] or '(미입력)'}",
        "",
    ]
    cls_label = {RAW: "원문형", FULL: "전문형", SUMMARY: "요약형"}
    for p in targets:
        body, warn = format_for(p, data)
        limit = f"{p['limit']}자" if p["limit"] else "길이무제한"
        out.append(f"## {p['name']}  ·  {cls_label[p['cls']]}  ·  {limit}")
        if warn:
            out.append(f"\n{warn}")
        out.append(f"\n`{p['note']}`\n")
        out.append("```")
        out.append(body)
        out.append("```\n")
    return "\n".join(out)


def cmd_bundle(args) -> int:
    src = Path(args.input)
    if not src.exists():
        print(f"❌ 입력 없음: {src}", file=sys.stderr)
        return 1
    data = parse_input(src.read_text(encoding="utf-8"))
    only = args.only.split(",") if args.only else None
    bundle = build_bundle(data, only)

    if args.output:
        out = Path(args.output)
    else:
        out = Path("out/syndicate") / (src.stem + ".bundle.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(bundle, encoding="utf-8")
    print(f"✅ {out}")
    # 경고 요약
    for p in (PLATFORMS if not only else [PLATFORM_BY_KEY[k] for k in only]):
        _, warn = format_for(p, data)
        if warn:
            print(f"   {p['name']}: {warn}")
    return 0


def cmd_specs(_args) -> int:
    """SSOT 명세를 마크다운 표로 출력 (문서 생성용)."""
    cls_label = {RAW: "원문형", FULL: "전문형", SUMMARY: "요약형"}
    print("| 매체 | 클래스 | 글자수 | 요약언어 | 링크 | 비고 |")
    print("|---|---|---|---|---|---|")
    for p in PLATFORMS:
        limit = f"{p['limit']:,}" if p["limit"] else "—"
        print(f"| {p['name']} | {cls_label[p['cls']]} | {limit} | "
              f"{p['lang'] or '—'} | {p['link']} | {p['note']} |")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="ROSSE syndication bundler (이슈 #4)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("bundle", help="canonical 노트 → 면별 복붙 묶음")
    b.add_argument("input", help="입력 마크다운 경로")
    b.add_argument("-o", "--output", help="출력 경로 (기본 out/syndicate/<name>.bundle.md)")
    b.add_argument("--only", help="특정 매체만 (쉼표구분 key: facebook,threads,...)")
    b.set_defaults(func=cmd_bundle)

    s = sub.add_parser("specs", help="매체 포맷 명세 표 출력")
    s.set_defaults(func=cmd_specs)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

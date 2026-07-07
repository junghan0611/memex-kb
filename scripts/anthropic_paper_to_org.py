#!/usr/bin/env python3
r"""anthropic_paper_to_org.py — Anthropic Distill(transformer-circuits.pub) HTML 논문 → Org.

범위 고정: Anthropic Distill 템플릿(`<d-article>`/`<d-math>`/`<d-cite>`/`<d-footnote>`)
**전용**. 범용 HTML→org 변환기가 아니다 (memex-kb NEXT: "Anthropic HTML 논문에만 집중,
범용화하면 산으로 간다"). 다른 사이트 HTML은 대상 아님.

조합 파이프라인 (pandoc 은 골격 추출에만 = "일부만", 나머지는 커스텀 로직):

    fetch → isolate <d-article> → protect(Distill 태그를 sentinel 로) → pandoc HTML→org
          → restore(math/cite/footnote) → assemble(org 헤더 + 경로/레벨 보정)

핵심 설계
- **수식 무손실**: Distill 은 `<d-math>LaTeX</d-math>` 안에 LaTeX **소스**를 그대로 담는다
  (KaTeX 렌더 스팬이 아님). 그래서 sentinel 로 빼돌렸다가 org `\( \)` / `\[ \]` 로 그대로 복원.
- **그림 2종 분기**: 정적 PNG(본문 10개) → 다운로드 후 임베드. JS 렌더 인터랙티브 그림
  (~74개, 정적 이미지 없음) → 캡션 + `원문#앵커` 라이브 링크로 대체 (org 에 못 담는 것 규칙).
- **결정론적/재현가능**: 매 실행 동일 org 바이트. LLM 호출 없음 — LLM(에이전트)의 몫은
  이 로직을 만들고 검수하는 것과, 스킬이 명시하는 인터랙티브 그림 서술 판단.

사용:
    python scripts/anthropic_paper_to_org.py \
        --url https://transformer-circuits.pub/2026/workspace/index.html \
        --name jspace --outdir out/anthropic-paper --fetch
    # --fetch 없이 재실행하면 이미 받아둔 workdir 로 org 만 재생성(결정론 확인).
"""

from __future__ import annotations

import argparse
import html as _htmllib
import logging
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("paper2org")

# sentinel 토큰: 순수 대문자+숫자라 pandoc 이 건드리지 않는다(--wrap=none 과 함께).
S = lambda kind, i: f"ZZ{kind}{i}ZZ"


def _text(s: str) -> str:
    """HTML 조각 → 평문(태그 제거 + 엔티티 해제 + 공백 정리)."""
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", _htmllib.unescape(s)).strip()


# --------------------------------------------------------------------------- fetch
def fetch(url: str, workdir: Path) -> Path:
    """논문 HTML + bibliography.bib + 본문 정적 PNG 를 workdir 로 내려받는다."""
    workdir.mkdir(parents=True, exist_ok=True)
    base = url.rsplit("/", 1)[0] + "/"
    html_path = workdir / "paper.html"

    log.info("fetch HTML %s", url)
    html = _get(url).decode("utf-8", "replace")
    html_path.write_text(html, encoding="utf-8")

    # bibliography.bib (있으면)
    try:
        bib = _get(base + "bibliography.bib")
        (workdir / "bibliography.bib").write_bytes(bib)
        log.info("fetch bibliography.bib (%d bytes)", len(bib))
    except Exception as e:  # noqa: BLE001
        log.warning("no bibliography.bib: %s", e)

    # 본문(=visual-toc nav 바깥) 정적 이미지만 내려받는다
    art = _isolate(html)
    body = _strip_visual_toc(art)
    imgs = sorted(set(re.findall(r'<img[^>]*src="([^"]+)"', body)))
    png_dir = workdir / "png"
    png_dir.mkdir(exist_ok=True)
    for src in imgs:
        fname = src.rsplit("/", 1)[-1]
        try:
            data = _get(urllib.parse.urljoin(base, src))
            (png_dir / fname).write_bytes(data)
            log.info("fetch img %s (%d bytes)", fname, len(data))
        except Exception as e:  # noqa: BLE001
            log.warning("img fail %s: %s", src, e)
    return html_path


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "memex-kb/paper2org"})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
        return r.read()


# ----------------------------------------------------------------------- isolate
def _isolate(html: str) -> str:
    start = html.find("<d-article>")
    end = html.find("</d-article>")
    if start == -1 or end == -1:
        sys.exit("not an Anthropic Distill paper: <d-article> not found")
    return html[start : end + len("</d-article>")]


def _strip_visual_toc(art: str) -> str:
    return re.sub(r'<nav class="visual-toc">.*?</nav>', "", art, flags=re.S)


def _lift_heading_ids(html: str) -> str:
    """`<h2><a id='intro' href='#intro'>제목</a></h2>` → `<h2 id="intro">제목</h2>`.

    앵커 id 를 헤딩 자체로 올려 pandoc 이 :CUSTOM_ID: 로 쓰게 한다 → 본문 `[[#intro]]`
    상호참조가 실제로 해석된다(안 그러면 pandoc 이 제목 텍스트로 슬러그를 새로 만듦).
    """

    def repl(m: re.Match) -> str:
        lvl, hid, inner = m.group(1), m.group(2), m.group(3)
        return f'<h{lvl} id="{hid}">{inner}</h{lvl}>'

    return re.sub(r"<h([2-4])><a id='([^']+)'[^>]*>(.*?)</a>\s*</h\1>", repl, html, flags=re.S)


# -------------------------------------------------------------------- frontmatter
def extract_frontmatter(html: str) -> dict:
    title = "Untitled"
    m = re.search(r"<d-title>.*?<h1[^>]*>(.*?)</h1>", html, re.S)
    if m:
        title = _text(m.group(1))
    authors = [
        _text(a).rstrip(",").strip()
        for a in re.findall(r"<span class='author'>(.*?)</span>", html, re.S)
    ]
    # 각주 마커(*, †) 제거
    authors = [re.sub(r"[*†‡]+$", "", a).strip() for a in authors if a]
    date = ""
    m = re.search(r"id='published'[^>]*>.*?</h3><div>(.*?)</div>", html, re.S)
    if m:
        date = _text(m.group(1))
    return {"title": title, "authors": authors, "date": date}


# ------------------------------------------------------------------------ protect
def protect(body: str, source_url: str) -> tuple[str, dict]:
    """Distill 전용 태그를 sentinel 로 치환하고 복원 테이블을 만든다."""
    store: dict[str, str] = {}
    footnotes: list[str] = []

    # 1) 디스플레이 수식 → \[ ... \]  (인라인 수식보다 먼저)
    def _mb(m: re.Match) -> str:
        tok = S("MB", len(store))
        store[tok] = "\\[" + m.group(1).strip() + "\\]"
        return tok

    body = re.sub(r"<d-math block>(.*?)</d-math>", _mb, body, flags=re.S)

    # 2) 인라인 수식 → \( ... \)
    def _mi(m: re.Match) -> str:
        tok = S("MI", len(store))
        store[tok] = "\\(" + m.group(1).strip() + "\\)"
        return tok

    body = re.sub(r"<d-math>(.*?)</d-math>", _mi, body, flags=re.S)

    # 3) 인용 <d-cite key="a,b"> → [cite:@a;@b]   (각주보다 먼저 = 각주 안 인용도 처리)
    def _ci(m: re.Match) -> str:
        keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
        tok = S("CI", len(store))
        store[tok] = "[cite:" + ";".join("@" + k for k in keys) + "]"
        return tok

    body = re.sub(r'<d-cite\b[^>]*key="([^"]*)"[^>]*>.*?</d-cite>', _ci, body, flags=re.S)

    # 4) 각주 <d-footnote>INNER</d-footnote> → sentinel (INNER 는 뒤에서 따로 pandoc)
    def _fn(m: re.Match) -> str:
        tok = S("FN", len(footnotes))
        footnotes.append(m.group(1))
        return tok

    body = re.sub(r"<d-footnote>(.*?)</d-footnote>", _fn, body, flags=re.S)

    # 5) 그림 분기: 정적 img 있으면 유지, 없으면(JS 렌더) 캡션+라이브링크로 대체
    def _fig(m: re.Match) -> str:
        fig = m.group(0)
        if "<img" in fig:
            return fig  # pandoc 이 #+caption + 이미지로 변환
        fid = re.search(r'id="([^"]+)"', fig)
        num = re.search(r'fig-num">([^<]*)', fig)
        cap = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", fig, re.S)
        label = (num.group(1).strip() if num else "Figure").rstrip(":")
        anchor = f"{source_url}#{fid.group(1)}" if fid else source_url
        caption = ""
        if cap:
            caption = re.sub(r'<span class="fig-num">.*?</span>', "", cap.group(1), flags=re.S)
        # <strong> + 링크 + 캡션(내부 sentinel 유지) → pandoc 이 org 로 변환
        return (
            f'<p><strong>[{label} · 인터랙티브 그림 — 원문: '
            f'<a href="{anchor}">{anchor}</a>]</strong> {caption}</p>'
        )

    body = re.sub(r"<figure\b[^>]*>.*?</figure>", _fig, body, flags=re.S)

    store["__footnotes__"] = footnotes  # type: ignore[assignment]
    return body, store


# ------------------------------------------------------------------------- pandoc
def pandoc_html_to_org(html: str) -> str:
    p = subprocess.run(
        ["pandoc", "-f", "html", "-t", "org", "--wrap=none"],
        input=html.encode("utf-8"),
        capture_output=True,
    )
    if p.returncode != 0:
        sys.exit("pandoc failed: " + p.stderr.decode("utf-8", "replace"))
    return p.stdout.decode("utf-8")


# ------------------------------------------------------------------------ restore
def restore(org: str, store: dict) -> str:
    footnotes = store.get("__footnotes__", [])
    # 각주: INNER 를 각각 pandoc → 인라인 org 각주 [fn:N: ...]
    for i, inner in enumerate(footnotes):
        frag = pandoc_html_to_org(f"<div>{inner}</div>").strip()
        frag = re.sub(r"\s*\n\s*", " ", frag).strip()  # 각주는 한 줄
        org = org.replace(S("FN", i), f"[fn:{i + 1}: {frag}]")
    # 수식/인용 sentinel 복원 (뒤에 붙은 각주 텍스트 안의 것까지 전역 복원)
    for tok, val in store.items():
        if tok == "__footnotes__":
            continue
        org = org.replace(tok, val)
    return org


# -------------------------------------------------------------------------- fixup
def fixup(org: str) -> str:
    # 이미지 경로: pandoc 의 ./png/ , png/ → file:png/
    org = re.sub(r"\[\[(?:\./)?png/", "[[file:png/", org)
    # 헤딩 승급: 본문 최상위가 h2(=**) 이므로 한 단계씩 올린다(** → *, *** → **, ...)
    org = re.sub(r"^\*(\*+ )", r"\1", org, flags=re.M)
    # 빈 줄 3개+ → 2개
    org = re.sub(r"\n{3,}", "\n\n", org)
    return org.strip() + "\n"


def assemble(fm: dict, body: str, source_url: str, has_bib: bool) -> str:
    authors = "; ".join(fm["authors"]) if fm["authors"] else "Anthropic"
    head = [
        f"#+title:      {fm['title']}",
        f"#+author:     {authors}",
        f"#+date:       {fm['date']}" if fm["date"] else "",
        f"#+source:     {source_url}",
        "#+options:     toc:2 num:nil",
        "#+cite_export: basic",
        "#+bibliography: bibliography.bib" if has_bib else "",
        "",
        "# 변환: memex-kb scripts/anthropic_paper_to_org.py (Anthropic Distill HTML → Org).",
        "# 원문 저작권 = Anthropic. 이 org 는 개인 아카이브/연구용 캡처.",
        "",
    ]
    head = [h for h in head if h != ""] + [""]
    return "\n".join(head) + body


# --------------------------------------------------------------------------- main
def convert(html: str, source_url: str, workdir: Path, name: str) -> Path:
    fm = extract_frontmatter(html)
    log.info("title=%r authors=%d date=%r", fm["title"], len(fm["authors"]), fm["date"])
    art = _isolate(html)
    body_html = _strip_visual_toc(art)
    body_html = body_html[body_html.find("<h2") :]  # 제목/byline 버리고 첫 섹션부터
    body_html = _lift_heading_ids(body_html)  # 앵커 id → 헤딩 CUSTOM_ID (상호참조 복원)
    protected, store = protect(body_html, source_url)
    org_body = pandoc_html_to_org(protected)
    org_body = restore(org_body, store)
    org_body = fixup(org_body)
    has_bib = (workdir / "bibliography.bib").exists()
    org = assemble(fm, org_body, source_url, has_bib)
    out = workdir / f"{name}.org"
    out.write_text(org, encoding="utf-8")
    log.info("wrote %s (%d bytes)", out, len(org))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Anthropic Distill HTML 논문 → Org")
    ap.add_argument("--url", required=True, help="논문 index.html URL")
    ap.add_argument("--name", default="paper", help="산출물 이름(<name>.org)")
    ap.add_argument("--outdir", default="out/anthropic-paper", help="작업 루트")
    ap.add_argument("--fetch", action="store_true", help="HTML/이미지/bib 새로 내려받기")
    args = ap.parse_args()

    workdir = Path(args.outdir) / args.name
    html_path = workdir / "paper.html"
    if args.fetch or not html_path.exists():
        fetch(args.url, workdir)
    html = html_path.read_text(encoding="utf-8")
    out = convert(html, args.url, workdir, args.name)

    # 간단 검수 리포트
    org = out.read_text(encoding="utf-8")
    print("\n=== 검수 ===")
    print(f"  헤딩:        {len(re.findall(r'^\*+ ', org, re.M))}")
    print(f"  인라인수식:  {org.count(chr(92) + '(')}")
    print(f"  디스플레이:  {org.count(chr(92) + '[')}")
    print(f"  인용:        {org.count('[cite:')}")
    print(f"  각주:        {len(re.findall(r'\[fn:\d+:', org))}")
    print(f"  임베드이미지: {org.count('[[file:png/')}")
    print(f"  인터랙티브:  {org.count('인터랙티브 그림')}")
    leftover = re.findall(r"ZZ(?:MB|MI|CI|FN)\d+ZZ|<d-\w+", org)
    print(f"  잔여 sentinel/태그: {len(leftover)} {leftover[:5]}")


if __name__ == "__main__":
    main()

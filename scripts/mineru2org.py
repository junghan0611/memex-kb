#!/usr/bin/env python3
"""MinerU Markdown → Org 변환기 v2 (스캔책 파이프라인).

MinerU VLM이 뽑은 .md(95% 충실)를 org 메타포맷으로 변환한다.
설계 철학은 epub2org/PATTERNS.org 와 동일: 단계별 변환 + 전수 로그 + 재현.

v1(표면 치환) → v2(구조 복원기). GPT 리뷰(REVIEW-gpt.md) 반영:
  - 헤딩 계층 복원(H5): 장 `*` / 절 `**` / 소절 `***`. book config의 chapters로 구동.
  - 번호+제목 분리 병합, 가짜 헤딩(①②, <도식>, A B C) 강등.
  - 각주(F4/F5): unicode 위첨자(⁵⁸²³) ref 변환 + content_list page_footnote 정의 연결.
  - HTML 잔재(G6/I6/T4): <details>/mermaid 제거, <table> → org 표.
  - front-matter/TOC 컷(P5).

표면 변환(v1 유지):
  이미지 ![](images/x)→[[file:images/x]], 블록수식 $$→\\[\\], 인라인 $..$→\\(..\\),
  각주참조 $^{n}$→[fn:n], 깨진 마커/빈 $$ 제거.

교정(OCR 오독): 증명 가능 안전만 자동(corrections.json safe_regex/literal),
애매 후보는 .candidates.log 로만(본문 미변경). 범용 교정은 LLM 경량 패스가 정답.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
         "VII": 7, "VIII": 8, "IX": 9, "X": 10}
SUP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
       "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}


def load_json(path):
    if path and Path(path).exists():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return {}


# ─────────────────────────── 표면 변환 ───────────────────────────
def surface(t: str, corr: dict, log: list, cand: list) -> str:
    # 깨진 이미지 마커 '![' (괄호 없음)
    n = len(re.findall(r"!\[(?!\]\()", t))
    if n:
        t = re.sub(r"!\[(?!\]\()", "", t)
        log.append(f"[G-garbage] 깨진 '![' 제거: {n}")
    # 빈 블록수식
    n = len(re.findall(r"\$\$\s*\n\s*\$\$", t))
    if n:
        t = re.sub(r"\$\$\s*\n\s*\$\$\n?", "", t)
        log.append(f"[G-garbage] 빈 $$ 블록 제거: {n}")
    # 이미지
    n = len(re.findall(r"!\[[^\]]*\]\((images/[^)]+)\)", t))
    t = re.sub(r"!\[[^\]]*\]\((images/[^)]+)\)", r"[[file:\1]]", t)
    if n:
        log.append(f"[I-image] ![](images/..) → [[file:..]]: {n}")
    # 블록 수식
    n = len(re.findall(r"\$\$(.+?)\$\$", t, flags=re.DOTALL))
    t = re.sub(r"\$\$(.+?)\$\$", lambda m: "\\[" + m.group(1) + "\\]", t, flags=re.DOTALL)
    if n:
        log.append(f"[S-eq] 블록 $$..$$ → \\[..\\]: {n}")
    # 각주참조 $^{n}$
    n = len(re.findall(r"\$\^\{?(\d+)\}?\$", t))
    t = re.sub(r"\$\^\{?(\d+)\}?\$", r"[fn:\1]", t)
    if n:
        log.append(f"[F-fnref] $^{{n}}$ → [fn:n]: {n}")
    # unicode 위첨자 각주 (⁵ ²³ ...)
    def sup_repl(m):
        return "[fn:" + "".join(SUP[c] for c in m.group(0)) + "]"
    n = len(re.findall(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+", t))
    t = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+", sup_repl, t)
    if n:
        log.append(f"[F-fnref] unicode 위첨자 → [fn:n]: {n}")
    # 인라인 수식
    n = len(re.findall(r"\$([^$\n]+?)\$", t))
    t = re.sub(r"\$([^$\n]+?)\$", lambda m: "\\(" + m.group(1) + "\\)", t)
    if n:
        log.append(f"[S-eq] 인라인 $..$ → \\(..\\): {n}")

    # 교정 — safe regex
    for r in corr.get("safe_regex", []):
        c = len(re.findall(r["pattern"], t))
        if c:
            t = re.sub(r["pattern"], r["replace"], t)
            log.append(f"[fix-safe] {r.get('desc','')}: {c}")
    # 교정 — literal
    for r in corr.get("literal", []):
        c = t.count(r["from"])
        if c:
            t = t.replace(r["from"], r["to"])
            log.append(f"[fix-lit] {r.get('desc','')}: {c}")
    # 후보 수집
    for r in corr.get("candidate_regex", []):
        for m in re.finditer(r["pattern"], t):
            s, e = max(0, m.start() - 12), min(len(t), m.end() + 12)
            cand.append(f"[{r.get('desc','')}] …{t[s:e]}…".replace("\n", " "))
    return t


# ─────────────────────── HTML/mermaid 정리 ───────────────────────
def clean_html(t: str, log: list) -> str:
    # <details>...</details> (보조 OCR 블록) 제거
    n = len(re.findall(r"<details>.*?</details>", t, flags=re.DOTALL))
    t = re.sub(r"<details>.*?</details>\n?", "", t, flags=re.DOTALL)
    if n:
        log.append(f"[G6-details] <details> 보조블록 제거: {n}")
    # mermaid fence 제거 (도식은 이미지로 대체)
    n = len(re.findall(r"```mermaid.*?```", t, flags=re.DOTALL))
    t = re.sub(r"```mermaid.*?```\n?", "", t, flags=re.DOTALL)
    if n:
        log.append(f"[I2-mermaid] mermaid fence 제거: {n}")

    # <table>...</table> → org 표
    def table_repl(m):
        html = m.group(0)
        rows = re.findall(r"<tr>(.*?)</tr>", html, flags=re.DOTALL)
        org = []
        for r in rows:
            cells = re.findall(r"<td>(.*?)</td>", r, flags=re.DOTALL)
            cells = [c.replace("&gt;", ">").replace("&lt;", "<").strip() for c in cells]
            org.append("| " + " | ".join(cells) + " |")
        return "\n".join(org)
    n = len(re.findall(r"<table>.*?</table>", t, flags=re.DOTALL))
    t = re.sub(r"<table>.*?</table>", table_repl, t, flags=re.DOTALL)
    if n:
        log.append(f"[T4-table] <table> → org 표: {n}")
    return t


# ───────────────────── 구조 복원 (헤딩 계층) ─────────────────────
def reconstruct(t: str, struct: dict, log: list):
    if not struct:
        # 구조 정보 없으면 단순 #→** (v1 동작)
        t = re.sub(r"^#\s+", "** ", t, flags=re.MULTILINE)
        return t, {}

    chap_by_title = {}
    for ch in struct.get("chapters", []):
        chap_by_title[ch["title"]] = (ch["num"], ch["title"])
    for variant, canon in struct.get("chapter_title_variants", {}).items():
        for ch in struct.get("chapters", []):
            if ch["title"] == canon:
                chap_by_title[variant] = (ch["num"], canon)
    back = set(struct.get("back_matter", []))
    body_start = struct.get("body_start")

    lines = t.split("\n")
    # front-matter/TOC 컷: body_start 헤딩 전까지 제거 (책머리에는 보존 시도)
    cut = 0
    if body_start:
        for i, ln in enumerate(lines):
            if re.match(r"^#\s+" + re.escape(body_start) + r"\s*$", ln):
                cut = i
                break
    front = lines[:cut]
    lines = lines[cut:]
    # 책머리에(preface) 보존: front에서 '# 책머리에' 헤딩~다음 헤딩 전까지
    preface = []
    for i, ln in enumerate(front):
        if re.match(r"^#\s+책머리에", ln):
            preface.append("* 책머리에")
            j = i + 1
            while j < len(front) and not re.match(r"^#\s+", front[j]):
                preface.append(front[j])
                j += 1
            break

    def next_nonempty(idx):
        j = idx + 1
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        return j

    out = list(preface)
    stats = {"chapter": 0, "section": 0, "subsection": 0, "false_demote": 0, "index_drop": 0}
    in_index = False  # 찾아보기 내부: 자모 구분자 헤딩은 노이즈 → 드롭
    i = 0
    while i < len(lines):
        ln = lines[i]
        # 찾아보기 내부에서는 모든 '#' 헤딩(자모 구분자: 7/L/□/人/⇒ 등)을 드롭
        if in_index:
            mh_idx = re.match(r"^#\s+", ln)
            if mh_idx:
                stats["index_drop"] += 1
                i += 1
                continue
        # plain 'N장' (헤딩 아님) + 다음 줄 제목
        mpc = re.match(r"^(\d+장)\s*$", ln.strip())
        if mpc:
            j = next_nonempty(i)
            if j < len(lines):
                title = re.sub(r"^#\s+", "", lines[j]).strip()
                out.append(f"* {mpc.group(1)} {title}")
                stats["chapter"] += 1
                i = j + 1
                continue
        mh = re.match(r"^#\s+(.*\S)\s*$", ln)
        if not mh:
            out.append(ln)
            i += 1
            continue
        text = mh.group(1).strip()
        # 장 제목
        if text in chap_by_title:
            num, ctitle = chap_by_title[text]
            out.append(f"* {num} {ctitle}")
            stats["chapter"] += 1
            i += 1
            continue
        # 후미 (참고문헌/찾아보기)
        if text in back:
            out.append(f"* {text}")
            in_index = (text == "찾아보기")
            i += 1
            continue
        # 절 번호만 (I, 2, 3 ...) → 다음 줄 제목과 병합
        mnum = re.match(r"^(I|II|III|IV|V|VI|VII|VIII|IX|X|\d+)\.?$", text)
        if mnum:
            secnum = ROMAN.get(mnum.group(1), mnum.group(1))
            j = next_nonempty(i)
            if j < len(lines):
                title = re.sub(r"^#\s+", "", lines[j]).strip()
                out.append(f"** {secnum}. {title}")
                stats["section"] += 1
                i = j + 1
                continue
        # 소절 (N)
        if re.match(r"^\(\d+\)", text):
            out.append(f"*** {text}")
            stats["subsection"] += 1
            i += 1
            continue
        # 가짜 헤딩: ①②.., <..>/〈..〉, A B C 류 → 본문으로 강등
        if (re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫]", text)
                or re.match(r"^[<〈].*[>〉]$", text)
                or re.match(r"^[A-Z]( [A-Z])+$", text)):
            out.append(text)
            stats["false_demote"] += 1
            i += 1
            continue
        # 잔여 헤딩 → 절 제목(번호 없는)으로
        out.append(f"** {text}")
        stats["section"] += 1
        i += 1
    log.append(f"[H5-struct] 장 {stats['chapter']} / 절 {stats['section']} / "
               f"소절 {stats['subsection']} / 가짜헤딩강등 {stats['false_demote']}")
    return "\n".join(out), stats


# ───────────────── 각주 정의 (content_list) ─────────────────
def footnote_defs(t: str, content_list: list, log: list, cand: list) -> str:
    if not content_list:
        return t
    refs = set(int(n) for n in re.findall(r"\[fn:(\d+)\]", t))
    defs = {}
    for x in content_list:
        if x.get("type") == "page_footnote":
            m = re.match(r"^\s*(\d+)\s+(.*)", x.get("text", "").strip(), flags=re.DOTALL)
            if m:
                defs[int(m.group(1))] = re.sub(r"\s+", " ", m.group(2)).strip()
    # body에 떠다니는 numeric footnote 단락 흡수 (ref 번호이고 def 없을 때)
    lines = t.split("\n")
    kept = []
    absorbed = 0
    for ln in lines:
        m = re.match(r"^(\d+)\s+(\S.{15,})$", ln)
        if m and int(m.group(1)) in refs and int(m.group(1)) not in defs:
            defs[int(m.group(1))] = re.sub(r"\s+", " ", m.group(2)).strip()
            absorbed += 1
            continue
        kept.append(ln)
    t = "\n".join(kept)
    if absorbed:
        log.append(f"[F3-orphan] 본문 떠도는 각주정의 흡수: {absorbed}")

    resolved = sorted(refs & set(defs))
    unresolved_ref = sorted(refs - set(defs))
    unused_def = sorted(set(defs) - refs)
    block = ["", "* 각주", ""]
    for n in sorted(defs):
        block.append(f"[fn:{n}] {defs[n]}")
    t = t.rstrip() + "\n" + "\n".join(block) + "\n"
    log.append(f"[F5-fndef] 각주 정의 {len(defs)}개 연결 (ref↔def 해소 {len(resolved)})")
    if unresolved_ref:
        cand.append(f"[각주 미해소: ref 있으나 정의 없음] {unresolved_ref}")
    if unused_def:
        cand.append(f"[각주 미사용: 정의 있으나 ref 없음] {unused_def}")
    return t


def main() -> int:
    ap = argparse.ArgumentParser(description="MinerU md → org 변환기 v2")
    ap.add_argument("md")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--author", default="")
    ap.add_argument("--corrections", help="corrections.json (structure 포함)")
    ap.add_argument("--content-list", help="..._content_list.json (각주/구조)")
    ap.add_argument("--log")
    ap.add_argument("--candidates")
    args = ap.parse_args()

    md = Path(args.md).read_text(encoding="utf-8")
    corr = load_json(args.corrections)
    content_list = load_json(args.content_list) or []
    struct = corr.get("structure", {})
    log: list = []
    cand: list = []

    t = surface(md, corr, log, cand)
    t = clean_html(t, log)
    t, _ = reconstruct(t, struct, log)
    t = footnote_defs(t, content_list, log, cand)
    t = re.sub(r"\n{3,}", "\n\n", t)

    meta = corr.get("meta", {})
    title = args.title or meta.get("title", "")
    author = args.author or meta.get("author", "")
    hdr = []
    if title:
        hdr.append(f"#+title:      {title}")
    if author:
        hdr.append(f"#+author:     {author}")
    if meta.get("date"):
        hdr.append(f"#+date:       {meta['date']}")
    hdr.append(f"#+language:   {meta.get('language', 'ko')}")
    if meta.get("publisher"):
        hdr.append(f"#+publisher:  {meta['publisher']}")
    if meta.get("subject"):
        hdr.append(f"#+subject:    {meta['subject']}")
    if meta.get("uid"):
        hdr.append(f"#+uid:        {meta['uid']}")
    # ^:{} — stray '^' 가 위첨자로 깨지지 않도록(수식/각주 안전). tex:dvisvgm — LaTeX→SVG.
    hdr.append("#+options:    toc:t num:t H:4 tex:dvisvgm ^:{}")
    hdr.append("#+startup:    content")
    out_text = "\n".join(hdr) + "\n\n" + t
    Path(args.out).write_text(out_text, encoding="utf-8")
    Path(args.log or args.out + ".changes.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    Path(args.candidates or args.out + ".candidates.log").write_text("\n".join(cand) + "\n", encoding="utf-8")

    print(f"✓ org: {args.out}  ({len(out_text.splitlines())} 줄)")
    print(f"✓ 후보: {len(cand)}건 (본문 미변경)")
    print("\n--- 변환 요약 ---")
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())

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

# 같은 scripts/ 디렉토리 — 문단 잘림 탐지기를 봉합 패스가 재사용한다.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import detect_para_splits as psplit  # noqa: E402

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
    # 각주참조 위첨자 변환. 물리/수학책은 위첨자가 대개 '지수'(cm², 10²³, x²)이지
    # 각주가 아니므로 config 의 footnote_superscript:false 로 끈다(기본 true).
    # 끄면 $^{n}$ 는 아래 인라인 $..$ 패스가 \(^{n}\) 로, 유니코드 위첨자는 그대로 둔다.
    if corr.get("footnote_superscript", True):
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


def _nospace(s: str) -> str:
    return re.sub(r"\s+", "", s)


# 헤딩 안 인라인 수식은 nav/TOC 에서 SVG 리소스를 참조하는데 ox-epub 패키징이
# 누락해 epubcheck RSC-007 을 낸다(물질생명인간 가시). 헤딩의 \(..\)/\[..\] 는
# 평문(그리스문자·기호 유니코드)으로 바꿔 SVG 참조 자체를 없앤다.
_GREEK = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "zeta": "ζ", "eta": "η", "theta": "θ", "iota": "ι", "kappa": "κ",
    "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π", "rho": "ρ",
    "sigma": "σ", "tau": "τ", "upsilon": "υ", "phi": "φ", "chi": "χ",
    "psi": "ψ", "omega": "ω", "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ",
    "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Phi": "Φ",
    "Psi": "Ψ", "Omega": "Ω", "nabla": "∇", "partial": "∂", "infty": "∞",
    "times": "×", "cdot": "·", "Rightarrow": "⇒", "rightarrow": "→",
    "leq": "≤", "geq": "≥", "equiv": "≡", "approx": "≈", "sqrt": "√",
}


def _demath_inline(expr: str) -> str:
    s = expr
    for k, v in sorted(_GREEK.items(), key=lambda kv: -len(kv[0])):
        s = s.replace("\\" + k, v)
    s = re.sub(r"([_^])\{([^{}]*)\}", r"\1\2", s)  # _{x}->_x
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\\[a-zA-Z]+", " ", s)             # 남은 명령 제거
    s = re.sub(r"\s+", " ", s).strip()
    return s


def demath_headings(t: str, log: list) -> str:
    n = 0
    out = []
    for ln in t.split("\n"):
        if re.match(r"^\*+ ", ln) and re.search(r"\\[(\[]", ln):
            ln = re.sub(r"\\\((.+?)\\\)", lambda m: _demath_inline(m.group(1)), ln)
            ln = re.sub(r"\\\[(.+?)\\\]", lambda m: _demath_inline(m.group(1)), ln)
            n += 1
        out.append(ln)
    if n:
        log.append(f"[H-demath] 헤딩 내 수식 평문화: {n}")
    return "\n".join(out)


# ──────── 구조 복원 — 장 / 고정마커 절 / 소절 (자연철학강의류) ────────
def reconstruct_chapsec(t: str, struct: dict, log: list):
    """장(章) `*` / 절(고정 마커) `**` / 소절 `***` 복원.

    절 레벨이 번호도 합성도 아닌 '고정 문자열 집합'인 책용
    (예: [역사 지평]/[내용 정리]/[해설 및 성찰]). config `section_markers` 로 구동.
    - 장: config chapters 의 `match`(MinerU 헤딩에 나타난 십우도 구절, OCR 형태)로 잡고
      제목은 config `title`(권위, OCR 보정). 표지의 평문/헤딩 `제N장` 토큰과 짧은 부제
      평문 라인은 드롭.
    - 절: section_markers(공백 무시 매칭) → `**` (정규형 출력).
    - 그 외 본문 헤딩 → `*** 소절`. back_matter → `*`. index_start 이후 헤딩 드롭.
    """
    chapters = struct.get("chapters", [])
    chap_by_match = {}
    for c in chapters:
        key = _nospace(c.get("match", c["title"]))
        chap_by_match[key] = (c["num"], c["title"])
    sec_norm = {_nospace(s): s for s in struct.get("section_markers", [])}
    back = set(struct.get("back_matter", []))
    body_start = struct.get("body_start")
    preface_keep = struct.get("preface_keep", [])
    index_start = struct.get("index_start")

    lines = t.split("\n")
    # front-matter/TOC 컷
    cut = 0
    if body_start:
        bs = _nospace(body_start)
        for i, ln in enumerate(lines):
            m = re.match(r"^#\s+(.*\S)\s*$", ln)
            if m and _nospace(m.group(1)) == bs:
                cut = i
                break
    front, lines = lines[:cut], lines[cut:]

    # preface 보존 (3level 과 동일 규약)
    preface_out = []
    if preface_keep:
        keep_norm = {_nospace(k) for k in preface_keep}
        start = None
        for i, ln in enumerate(front):
            m = re.match(r"^#\s+(.*\S)\s*$", ln)
            if m and _nospace(m.group(1)) in keep_norm:
                start = i
                break
        if start is not None:
            for ln in front[start:]:
                m = re.match(r"^#\s+(.*\S)\s*$", ln)
                if m:
                    txt = m.group(1).strip()
                    preface_out.append(f"* {txt}" if _nospace(txt) in keep_norm else f"** {txt}")
                else:
                    preface_out.append(ln)

    def next_nonempty(idx):
        j = idx + 1
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        return j

    out = list(preface_out)
    stats = {"chapter": 0, "section": 0, "subsection": 0,
             "false_demote": 0, "index_drop": 0, "drop": 0}
    in_index = False
    i = 0
    while i < len(lines):
        ln = lines[i]
        raw = ln.strip()
        if in_index and re.match(r"^#\s+", ln):
            stats["index_drop"] += 1
            i += 1
            continue
        # '제N장' 평문/헤딩 토큰 드롭(장은 십우도 제목으로 잡는다)
        if re.match(r"^(?:#\s+)?제\d+장$", raw):
            stats["drop"] += 1
            i += 1
            continue
        mh = re.match(r"^#\s+(.*\S)\s*$", ln)
        if not mh:
            out.append(ln)
            i += 1
            continue
        text = mh.group(1).strip()
        key = _nospace(text)
        # 장 제목(십우도 구절)
        if key in chap_by_match:
            num, ctitle = chap_by_match[key]
            out.append(f"* {num} {ctitle}")
            stats["chapter"] += 1
            # 다음 짧은 평문 부제 라인 드롭(예: '않의 바탕 구도')
            j = next_nonempty(i)
            if j < len(lines):
                nxt = lines[j].strip()
                if nxt and not re.match(r"^#|^!\[|^<", nxt) and len(nxt) <= 25:
                    i = j + 1
                    continue
            i += 1
            continue
        # 절 마커
        if key in sec_norm:
            out.append(f"** {sec_norm[key]}")
            stats["section"] += 1
            i += 1
            continue
        # index 시작
        if index_start and key == _nospace(index_start):
            out.append(f"* {text}")
            in_index = True
            i += 1
            continue
        # 후미
        if text in back:
            out.append(f"* {text}")
            i += 1
            continue
        # 가짜 헤딩 강등
        if (re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫]", text)
                or re.match(r"^[<〈].*[>〉]$", text)
                or not re.search(r"[가-힣]", text)):
            out.append(text)
            stats["false_demote"] += 1
            i += 1
            continue
        # 소절
        out.append(f"*** {text}")
        stats["subsection"] += 1
        i += 1
    log.append(f"[H5-chapsec] 장 {stats['chapter']} / 절 {stats['section']} / "
               f"소절 {stats['subsection']} / 가짜강등 {stats['false_demote']} / "
               f"제N장드롭 {stats['drop']} / 색인드롭 {stats['index_drop']}")
    return "\n".join(out), stats


# ──────────────── 구조 복원 — 3단 계층 (부/강/소절) ────────────────
def reconstruct_3level(t: str, struct: dict, log: list):
    """부(部) `*` / 강(講) `**` / 소절 `***` 3단 책 구조 복원.

    MinerU는 헤딩을 전부 플랫 '#'로 뱉고, 강 표지를 두 방식으로 낸다:
      (a) '# N강' + '# 제목'  (헤딩 2개)        — 다수
      (b) 평문 'N강' + 평문 '제목'              — 일부(번호 헤딩 누락분)
    부 제목은 본문에서 유일하지 않다(소절/강 제목과 충돌). 따라서 부 표지는
    제목 매칭으로 잡지 않고, config 의 part↔lecture 소속을 SSOT 로 삼아
    '각 부의 첫 강 직전'에 부 헤딩을 합성한다. 본문의 부 표지 헤딩(다음 헤딩이
    N강인 경우)은 드롭한다. 강 제목은 config 값으로 권위 보정(OCR 오독 무시).
    """
    parts = struct.get("parts", [])
    lectures = struct.get("lectures", [])
    part_titles = {p["title"] for p in parts}
    part_by_num = {p["num"]: p["title"] for p in parts}
    lec_title = {l["num"]: l["title"] for l in lectures}
    # 각 부의 첫 강 → 부 헤딩 합성 트리거
    first_lec = {}
    seen = set()
    for l in lectures:
        pn = l.get("part")
        if pn and pn not in seen:
            first_lec[l["num"]] = (pn, part_by_num.get(pn, ""))
            seen.add(pn)
    back = set(struct.get("back_matter", []))
    body_start = struct.get("body_start")
    preface_keep = struct.get("preface_keep", [])

    lines = t.split("\n")
    # front-matter/TOC 컷
    cut = 0
    if body_start:
        for i, ln in enumerate(lines):
            if re.match(r"^#\s+" + re.escape(body_start) + r"\s*$", ln):
                cut = i
                break
    front, lines = lines[:cut], lines[cut:]

    # preface 보존: 가장 이른 preface_keep 헤딩~front 끝.
    # preface_keep 이름은 '*', 그 외 '#' 헤딩은 '**', 본문은 그대로.
    preface_out = []
    if preface_keep:
        keep_set = set(preface_keep)
        start = None
        for i, ln in enumerate(front):
            m = re.match(r"^#\s+(.*\S)\s*$", ln)
            if m and m.group(1).strip() in keep_set:
                start = i
                break
        if start is not None:
            for ln in front[start:]:
                m = re.match(r"^#\s+(.*\S)\s*$", ln)
                if m:
                    txt = m.group(1).strip()
                    preface_out.append(f"* {txt}" if txt in keep_set else f"** {txt}")
                else:
                    preface_out.append(ln)

    def next_nonempty(idx):
        j = idx + 1
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        return j

    def next_heading(idx):
        j = idx + 1
        while j < len(lines):
            s = lines[j].strip()
            if re.match(r"^#\s+", lines[j]) or re.match(r"^\d+강$", s):
                return j
            j += 1
        return -1

    out = list(preface_out)
    stats = {"part": 0, "lecture": 0, "subsection": 0,
             "false_demote": 0, "index_drop": 0, "part_drop": 0}
    in_index = False
    i = 0
    while i < len(lines):
        ln = lines[i]
        raw = ln.strip()
        # 찾아보기 내부: 모든 '#' 헤딩(자모 구분자 노이즈) 드롭
        if in_index and re.match(r"^#\s+", ln):
            stats["index_drop"] += 1
            i += 1
            continue
        # 강 토큰: '# N강' 또는 평문 'N강'
        m_lec = re.match(r"^(?:#\s+)?(\d+강)$", raw)
        if m_lec:
            num = m_lec.group(1)
            if num in first_lec:
                pn, pt = first_lec[num]
                out.append(f"* {pn} {pt}")
                stats["part"] += 1
            j = next_nonempty(i)
            title = lec_title.get(num)
            if title is None and j < len(lines):
                title = re.sub(r"^#\s+", "", lines[j]).strip()
            out.append(f"** {num} {title}")
            stats["lecture"] += 1
            i = (j + 1) if j < len(lines) else (i + 1)
            continue
        mh = re.match(r"^#\s+(.*\S)\s*$", ln)
        if not mh:
            out.append(ln)
            i += 1
            continue
        text = mh.group(1).strip()
        # 부 표지: 다음 헤딩이 N강이면 드롭(부는 첫 강에서 합성)
        if text in part_titles:
            nh = next_heading(i)
            if nh != -1 and re.match(r"^(?:#\s+)?\d+강$", lines[nh].strip()):
                stats["part_drop"] += 1
                i += 1
                continue
        # 후미(읽을거리/찾아보기)
        if text in back:
            out.append(f"* {text}")
            in_index = (text == "찾아보기")
            i += 1
            continue
        # 가짜 헤딩 강등: ①②, <도식>, 한국어 없는 헤딩(영문 그림 포스터/기호/숫자)
        if (re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫]", text)
                or re.match(r"^[<〈].*[>〉]$", text)
                or not re.search(r"[가-힣]", text)):
            out.append(text)
            stats["false_demote"] += 1
            i += 1
            continue
        # 소절
        out.append(f"*** {text}")
        stats["subsection"] += 1
        i += 1
    log.append(f"[H5-3lvl] 부 {stats['part']} / 강 {stats['lecture']} / "
               f"소절 {stats['subsection']} / 가짜강등 {stats['false_demote']} / "
               f"부표지드롭 {stats['part_drop']} / 색인드롭 {stats['index_drop']}")
    return "\n".join(out), stats


# ───────────────────── 구조 복원 (헤딩 계층) ─────────────────────
def reconstruct(t: str, struct: dict, log: list):
    if not struct:
        # 구조 정보 없으면 단순 #→** (v1 동작)
        t = re.sub(r"^#\s+", "** ", t, flags=re.MULTILINE)
        return t, {}
    # 3단 계층(부/강/소절) 모드: config에 parts 가 있으면.
    if struct.get("parts"):
        return reconstruct_3level(t, struct, log)
    # 장/고정마커 절/소절 모드: config에 section_markers 가 있으면.
    if struct.get("section_markers"):
        return reconstruct_chapsec(t, struct, log)

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
    seen_chap = set()  # 같은 장 제목 두 번째 등장 = 내부 소절(막간 표지 뒤 동명 소절) → 절로 강등
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
        # 강/막간 번호만 있는 표지 헤딩(# 2강, # 막간 2) → 드롭. config chapter 가 num 보유,
        # 바로 다음 제목줄이 '* N강 제목' 을 만든다(강 표지 2형태 중 분리형). 본문 참조 '9강에서'는
        # 헤딩이 아니라 영향 없음.
        if re.match(r"^(제?\s*\d+강|막간\s*\d+)$", text):
            stats["false_demote"] += 1
            i += 1
            continue
        # 장 제목 (단, 같은 ctitle 두 번째 등장은 내부 소절 → 아래 절 처리로 흘려보냄)
        if text in chap_by_title and chap_by_title[text][1] not in seen_chap:
            num, ctitle = chap_by_title[text]
            out.append(f"* {num} {ctitle}")
            seen_chap.add(ctitle)
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
    if not defs:
        # 각주 정의 없음(content_list page_footnote 부재 + 흡수 0) → 섹션 생략
        if refs:
            cand.append(f"[각주 ref 있으나 정의 전무] {sorted(refs)}")
        log.append("[F5-fndef] 각주 정의 0개 → '* 각주' 섹션 생략")
        return t
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


# ───────────────── 문단 봉합 (감독형 page-split merge) ─────────────────
# MinerU가 페이지를 독립적으로 읽어 쪼갠 문단을 다시 잇는다. 탐지는 detect_para_splits
# (content_list 인접성), seam(공백 여부)은 휴리스틱 + config override + 전수 로그(.merges.log).
# 원칙: 탐지는 신뢰, 봉합은 검수. eq/image/table은 기본 제외(캡션·디스플레이수식 오접합 위험).

# tail이 이 접미사(조사/어미)로 끝나면 어절 경계 → 공백. 그 외 한글이면 어절 중간 → 무공백.
_SEAM_SPACE_SUFFIX = sorted([
    "을", "를", "은", "는", "이", "가", "도", "만", "의", "와", "과", "로", "으로", "서",
    "에", "에서", "부터", "까지", "보다", "처럼", "마다", "조차", "마저", "나", "이나",
    "든", "든지", "라도", "밖에", "뿐", "께", "한테", "에게", "으로서", "로서", "으로써", "로써",
    "다", "요", "죠", "지요", "네요", "습니다", "했다", "된다", "한다", "진다", "이다",
    "거나", "면서", "면", "지만", "는데", "은데", "으며", "며", "고", "어서", "아서", "자",
    "라", "겠다", "였다", "게",   # 게 = 부사형 어미(심각하게/분명하게)
], key=len, reverse=True)

# tail의 마지막 어절이 완결 부사/접속사면(조사 없이 끝나 휴리스틱이 못 잡음) → 공백.
_SPACE_TAIL_WORDS = {
    "물론", "특히", "또한", "다만", "만일", "비록", "즉", "또", "곧", "결국", "과연",
    "대체로", "오히려", "이른바", "이를테면", "그러나", "그리고", "그런데", "따라서",
    "하지만", "그러므로", "왜냐하면", "예컨대", "가령",
}
# head가 접속사/나열어로 시작하면 → 공백.
_SPACE_HEAD_RE = re.compile(r"^(및|또는|혹은|그리고|그러나|그런데|즉|또|및는)(?=\s)")


# 융합 보정(보수적): tail이 '이'로 끝나는데 head 첫 글자가 '단어 첫음절로는 거의 안 오는'
# 음절이면 한 어절(이란/이며/이든/이었/이는/이들/이라)이 쪼개진 것 → 무공백.
#   '아름다움이'+'란'=이란(무공백), '표면을 이'+'루는'=이루는. 단 '고/다/나/지/면'은
#   단어 시작 가능(나오다/다음/지금)이라 제외 → 조사 규칙으로 공백(붙여 깨는 것보다 띄움이 읽기 안전).
#   러/루(이러/이루)는 ~95% 안전, 른/렇/를(이른/이렇/이를)은 단어 첫음절로 거의 안 와 안전.
_FUSION = {"이": set("란며든었는들라러루른렇를")}

# head가 '맨조사 토큰'(뒤에 공백)으로 시작 = 단어가 조사 직전에서 쪼개짐 → 조사가 앞에 붙음 → 무공백.
#   '…사이'+'에 전이'→'사이에'. 공백 lookahead로 '에너지'(에+너) 같은 단어시작은 제외.
#   이/와/로/나는 관형사·동사·명사 시작과 모호해 제외('이 가운데', '와 보니', '로마').
_JOSA_HEAD_RE = re.compile(
    r"^(에서|에게|한테|부터|까지|보다|처럼|마다|조차|마저|밖에|을|를|은|는|의|가|도|만|과|께|에)(?=\s)")

# 본문 연속이 아닌 '구조 라벨'은 봉합 금지(특히 textbook/도해 책). 셋 다 자연철학강의/물리학강의에서 관측.
_CAPTION_HEAD_RE = re.compile(r"^(그림|사진|표)\s*\d[\d.\-]*\s*[:：]")  # '그림 1-1: …' 도판 캡션
_PAGEREF_TAIL_RE = re.compile(r"\d\s*쪽$")                            # '더 알아보기 … 202쪽' 교차참조(왼쪽/양쪽 제외: 숫자+쪽만)
_CIRCLED = set("①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳")                       # '① 로렌츠 변환식' 박스 소제목/나열
# 박스 소제목(①-시작, 짧음)만 봉합 금지. ①로 시작하는 '긴' 인용 문단(칸트 ④/⑦…, ≥27자)은 평문이라 제외.
# 물리학강의 박스제목 ≤21자 / 물질생명인간 ①-인용 ≥27자 → 24자가 둘을 가른다.
_ENUM_TITLE_MAXLEN = 24


def _seam_for(tail: str, head: str, overrides: list):
    """봉합부 공백 결정 → ('space'|'nospace'|'skip', reason). head도 본다."""
    t = tail.rstrip()
    h = head.lstrip()
    for ov in overrides:                       # config override(접미사 매칭) 우선
        if ov.get("tail") and t.endswith(ov["tail"]):
            return ov.get("seam", "skip"), "override"
    if not t:
        return "skip", "empty"
    if h[:1].isdigit():                         # head가 숫자 시작 = 각주정의/번호목록 orphan → 봉합 금지
        return "skip", "digit-head"             #   (footnote_defs가 standalone 줄로 흡수해야 함)
    if _CAPTION_HEAD_RE.match(h):               # head가 '그림/표/사진 N:' 캡션 → 본문 아님
        return "skip", "caption-head"
    if _PAGEREF_TAIL_RE.search(t):              # tail이 'NNN쪽' 교차참조 라벨('더 알아보기 … 202쪽')
        return "skip", "pageref-tail"
    if t.lstrip()[:1] in _CIRCLED and len(t.strip()) <= _ENUM_TITLE_MAXLEN:  # 짧은 박스 소제목 '① 로렌츠 변환식'
        return "skip", "enum-circled"                                        #   (긴 ①-시작 인용 문단은 평문 연속 → 제외)
    last = t[-1]
    if last == ",":                            # 나열/절 연속 → 공백 (`A, B`)
        return "space", "comma"
    if not ("가" <= last <= "힣"):             # 그 외 digit/latin/symbol/`:` → 모호, 보류
        return "skip", "non-hangul"
    if _JOSA_HEAD_RE.match(h):                  # head가 맨조사로 시작 → 앞 단어에 붙음 → 무공백
        return "nospace", "josa-head"
    if h[:1].isascii() and h[:1].isalpha():     # head가 라틴(병기 entropy 등) → 공백
        return "space", "latin-head"
    if _SPACE_HEAD_RE.match(h):                 # head가 접속사/나열어 → 공백 (`위치 및`)
        return "space", "conj-head"
    if (t.split() or [""])[-1] in _SPACE_TAIL_WORDS:  # tail이 완결 부사/접속사 → 공백 (`물론 칸트`)
        return "space", "adv-tail"
    if t.endswith("적"):                        # X적(的) 형용사 + 명사 → 공백 (`개인적 차원`)
        return "space", "jeok-tail"
    if last in _FUSION and h[:1] in _FUSION[last]:  # 융합형이 쪼개짐 → 무공백
        return "nospace", "fusion"
    for suf in _SEAM_SPACE_SUFFIX:
        if t.endswith(suf):
            return "space", "josa/ending"
    return "nospace", "mid-eojeol"


# reconstruct()가 헤딩으로 승격할 '구조 마커 줄'(평문 N강/제N장/section_marker/장제목)을
# 봉합이 문단에 흡수하면 헤딩이 사라진다(4·13·18강 실종 버그). 그런 줄은 봉합 경계로 본다.
_NUMHEAD_RE = re.compile(r"^제?\s*\d+\s*[부강장절편](?:\s|$)")


def _build_struct_markers(struct: dict) -> set:
    # num('4강')은 제외 — 본문 '9강에서' 같은 참조와 충돌. 번호 헤딩은 _NUMHEAD_RE 로만.
    titles = set()
    for key in ("parts", "lectures", "chapters"):
        for x in struct.get(key, []):
            for f in ("title", "match"):
                v = (x.get(f) or "").strip()
                if v:
                    titles.add(v)
    for m in struct.get("section_markers", []):
        titles.add(m.strip())
    return {t for t in titles if t}


# 헤딩 블록은 짧다(제목뿐). 긴 본문 문단은 '양자역학은…'처럼 제목으로 시작해도 헤딩이 아님.
_STRUCT_MAXLEN = 40


def _is_structural(text: str, markers: set) -> bool:
    body = text.strip()
    if not body or len(body) > _STRUCT_MAXLEN:   # 길면 본문 문단 — 헤딩 아님
        return False
    line = body.split("\n", 1)[0].strip()
    if _NUMHEAD_RE.match(line):                   # '4강', '제2장 …', '15강 비선형동역학'
        return True
    # 제목-only 헤딩 블록은 마커와 '정확히' 일치. 본문 '고전역학에서…'는 시작만 같을 뿐 → 제외.
    return line in markers


def merge_paragraphs(md: str, content_list: list, struct: dict,
                     pm_cfg: dict, log: list, merges: list) -> str:
    """page-split 문단 봉합. raw md 위에서 (surface 변환 전) 동작 — content_list
    텍스트가 md의 정확한 substring이므로 `tail\\n\\nhead` 를 찾아 seam으로 잇는다."""
    if not pm_cfg.get("enabled") or not content_list:
        return md
    cats = pm_cfg.get("categories", ["page_boundary", "samepage_break"])
    overrides = pm_cfg.get("overrides", [])
    markers = _build_struct_markers(struct)
    si, ei = psplit.body_bounds(content_list, {"structure": struct})
    classified = psplit.classify(content_list, si, ei)
    seam_char = {"space": " ", "nospace": ""}
    applied = skipped = miss = 0
    for cat in cats:
        for r in classified.get(cat, []):
            tail, head = r["tail"], r["head"]
            if _is_structural(head, markers) or _is_structural(tail, markers):
                seam, why = "skip", "heading-boundary"
            else:
                seam, why = _seam_for(tail, head, overrides)
            tag = f"p{r['page_a']}" + (f"->p{r['page_b']}" if r["page_a"] != r["page_b"] else "")
            label = f"[{cat} {tag}] …{tail[-24:]} ++ {head[:24]}…"
            if seam == "skip":
                merges.append(f"SKIP({why})    {label}")
                skipped += 1
                continue
            joint = tail + "\n\n" + head
            n = md.count(joint)
            if n != 1:                          # 0=텍스트 불일치, 2+=모호 → 봉합 안 함
                merges.append(f"MISS(n={n})     {label}")
                miss += 1
                continue
            md = md.replace(joint, tail + seam_char[seam] + head, 1)
            merges.append(f"MERGE({seam},{why}) {label}")
            applied += 1
    log.append(f"[P6-merge] 봉합 {applied} / skip {skipped} / miss {miss} "
               f"(cats={','.join(cats)}, overrides={len(overrides)})")
    return md


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
    ap.add_argument("--merge-paragraphs", action="store_true",
                    help="page-split 문단 봉합 강제 ON (config paragraph_merge.enabled 무시)")
    args = ap.parse_args()

    md = Path(args.md).read_text(encoding="utf-8")
    corr = load_json(args.corrections)
    content_list = load_json(args.content_list) or []
    struct = corr.get("structure", {})
    log: list = []
    cand: list = []
    merges: list = []

    # 봉합은 raw md 위에서 먼저 (content_list 텍스트가 md의 정확한 substring일 때).
    pm_cfg = dict(corr.get("paragraph_merge", {}))
    if args.merge_paragraphs:
        pm_cfg["enabled"] = True
    md = merge_paragraphs(md, content_list, struct, pm_cfg, log, merges)

    t = surface(md, corr, log, cand)
    t = clean_html(t, log)
    t, _ = reconstruct(t, struct, log)
    t = demath_headings(t, log)
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
    # num:nil — 헤딩에 자동 번호(1, 1.1 …) 부착 안 함. 책 제목 헤딩(N장/N강)이 이미 번호를
    #           품고 있어 중복/오염되므로 끈다(EPUB 헤딩 번호 이슈, 2026-06-03 GLG).
    hdr.append("#+options:    toc:t num:nil H:4 tex:dvisvgm ^:{}")
    hdr.append("#+startup:    content")
    out_text = "\n".join(hdr) + "\n\n" + t
    Path(args.out).write_text(out_text, encoding="utf-8")
    Path(args.log or args.out + ".changes.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    Path(args.candidates or args.out + ".candidates.log").write_text("\n".join(cand) + "\n", encoding="utf-8")
    if merges:
        Path(args.out + ".merges.log").write_text("\n".join(merges) + "\n", encoding="utf-8")

    print(f"✓ org: {args.out}  ({len(out_text.splitlines())} 줄)")
    print(f"✓ 후보: {len(cand)}건 (본문 미변경)")
    if merges:
        print(f"✓ 봉합 로그: {args.out}.merges.log ({len(merges)}건)")
    print("\n--- 변환 요약 ---")
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())

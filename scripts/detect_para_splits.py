#!/usr/bin/env python3
"""문단 잘림 탐지기 (scanbook 파이프라인 보조 도구).

MinerU는 페이지 단위로 OCR 하므로, 한 문단이
  ① 페이지 경계를 넘어가거나      (page_boundary)
  ② 그림/표/수식이 문단 중간에 끼거나  (image/table/eq_interrupt)
  ③ 같은 페이지 안에서 까닭 없이 끊기면  (samepage_break)
.org/.epub 에서 별개 문단으로 쪼개진다. OCR 단계로는 못 잡는 영역이다.

이 도구는 **탐지·리스트 전용**이다. 본문을 고치지 않는다.
content_list.json 의 page_idx + block type + 한국어 종결부호 휴리스틱으로
잘림 후보를 분류해 리포트를 찍는다. 사람/LLM 이 이 리스트를 들고
mineru2org.py 의 병합 로직을 개선하거나 직접 봉합한다.

휴리스틱(보수적):
  - 앞 블록이 종결부호(.?!…。, 닫는 따옴표/괄호) 없이 끝나고
  - 뒤 블록이 새 문단 마커(*, -, #) 로 시작하지 않으면 → 잇는 문단 후보
  - front matter(body_start 이전) / back matter(찾아보기 등) 는 제외
    (목차·색인 줄은 페이지숫자로 끝나 대량 오탐을 낸다)

신뢰도 등급(병합 자동화 난이도):
  eq_interrupt   : 高 — 텍스트+디스플레이수식+텍스트 = 한 문단. 거의 안전.
  page_boundary  : 高(탐지) / 中(봉합) — 대부분 어절 중간 줄바꿈→공백 없이 접합.
  table_interrupt: 中
  image_interrupt: 中 — 뒤 블록이 '그림 설명/캡션'일 수 있어 진짜 연속과 구분 필요.
  samepage_break : 低 — 본문에선 드묾. 목차/색인 잔재가 섞이면 오탐.

사용:
  python3 scripts/detect_para_splits.py \\
    --content-list scanpdf/work/<book>/mineru/<book>001_content_list.json \\
    --corrections  scripts/corrections/<book>.json \\
    [--category eq_interrupt] [--limit 0] [--json]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

TERM = set(".!?…。") | set("」』）)]") | {'"', "'", "”", "’"}
PARA_OPENERS = set("*-#")
SKIP_INTER = {"page_number", "header", "footer", "image", "equation",
              "table", "chart"}


def ends_open(text: str) -> bool:
    t = text.rstrip()
    return bool(t) and t[-1] not in TERM


def starts_continuation(text: str) -> bool:
    t = text.lstrip()
    return bool(t) and t[0] not in PARA_OPENERS


def body_bounds(blocks, cfg):
    """body_start ~ back_matter 사이의 블록 인덱스 범위."""
    struct = cfg.get("structure", {})
    bstart = struct.get("body_start")
    bmat = struct.get("back_matter", [])
    si = 0
    if bstart:
        for i, b in enumerate(blocks):
            if b.get("text", "").strip().startswith(bstart):
                si = i
                break
    ei = len(blocks)
    found = False
    for i in range(si + 1, len(blocks)):
        b = blocks[i]
        if b.get("text_level") and any(
            b.get("text", "").strip().startswith(x) for x in bmat
        ):
            ei = i
            found = True
            break
    # Fallback: MinerU가 back_matter 표제를 헤딩(text_level)이 아니라 러닝헤드
    # (type='header', text_level=None)로만 출력하는 책(예: 물리의정석 찾아보기)에서는
    # 위 검색이 실패한다. 그 표제가 처음 등장하는 페이지의 첫 블록에서 컷 — 색인은
    # 그 페이지 첫 블록부터 시작하므로 색인+판권이 통째로 본문 밖으로 빠진다.
    if not found and bmat:
        back_pages = sorted({
            b.get("page_idx") for b in blocks[si + 1:]
            if b.get("text", "").strip() in bmat
            and b.get("page_idx") is not None
        })
        if back_pages:
            bp = back_pages[0]
            for i in range(si + 1, len(blocks)):
                if blocks[i].get("page_idx") == bp:
                    ei = i
                    break
    return si, ei


def classify(blocks, si, ei):
    """본문 범위에서 잘림 후보를 분류해 리스트로 반환."""
    out = {k: [] for k in
           ("page_boundary", "image_interrupt", "eq_interrupt",
            "table_interrupt", "samepage_break")}
    for i in range(si, min(ei, len(blocks)) - 1):
        a = blocks[i]
        if a.get("type") != "text" or a.get("text_level"):
            continue
        if not ends_open(a.get("text", "")):
            continue
        j = i + 1
        inter = []
        while j < ei and blocks[j].get("type") in SKIP_INTER:
            inter.append(blocks[j].get("type"))
            j += 1
        if j >= ei:
            break
        b = blocks[j]
        if b.get("type") != "text" or b.get("text_level"):
            continue
        if not starts_continuation(b.get("text", "")):
            continue
        s = set(inter)
        rec = {
            "page_a": a["page_idx"], "page_b": b["page_idx"],
            "inter": inter,
            "tail": a["text"].rstrip(),     # FULL tail text (merge needs it)
            "head": b["text"].lstrip(),     # FULL head text
        }
        if "image" in s:
            out["image_interrupt"].append(rec)
        elif "equation" in s:
            out["eq_interrupt"].append(rec)
        elif s & {"table", "chart"}:
            out["table_interrupt"].append(rec)
        elif a["page_idx"] != b["page_idx"]:
            out["page_boundary"].append(rec)
        else:
            out["samepage_break"].append(rec)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content-list", required=True)
    ap.add_argument("--corrections", required=True)
    ap.add_argument("--category", help="한 분류만 상세 출력")
    ap.add_argument("--limit", type=int, default=12,
                    help="분류별 샘플 개수 (0=전부)")
    ap.add_argument("--json", action="store_true", help="JSON 출력")
    args = ap.parse_args()

    blocks = json.loads(Path(args.content_list).read_text(encoding="utf-8"))
    cfg = json.loads(Path(args.corrections).read_text(encoding="utf-8"))
    si, ei = body_bounds(blocks, cfg)
    cats = classify(blocks, si, ei)

    if args.json:
        json.dump(cats, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    p0, p1 = blocks[si]["page_idx"], blocks[min(ei, len(blocks)) - 1]["page_idx"]
    print(f"# 문단 잘림 리포트  (본문 page {p0}..{p1}, blocks {si}..{ei})")
    total = sum(len(v) for v in cats.values())
    print(f"# 총 {total} 후보\n")
    order = ["eq_interrupt", "page_boundary", "table_interrupt",
             "image_interrupt", "samepage_break"]
    for k in order:
        print(f"  {k:18} {len(cats[k])}")
    cats_iter = [args.category] if args.category else order
    for k in cats_iter:
        recs = cats[k]
        print(f"\n=== {k} ({len(recs)}) ===")
        show = recs if args.limit == 0 else recs[:args.limit]
        for r in show:
            arrow = f"p{r['page_a']}->p{r['page_b']}" if r['page_a'] != r['page_b'] else f"p{r['page_a']}"
            inter = ("+[" + ",".join(r["inter"]) + "]") if r["inter"] else ""
            print(f"{arrow} {inter}\n    …{r['tail'][-30:]}\n  ++ {r['head'][:30]}…")


if __name__ == "__main__":
    main()

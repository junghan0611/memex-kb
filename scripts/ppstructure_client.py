#!/usr/bin/env python3
"""PP-StructureV3 thin-client — 스캔 PDF → markdown + asset 크롭 + 구조 (원격 PaddleX).

추론은 gpu3i RTX 5080의 PaddleX(PP-StructureV3 파이프라인, port 8118)가 한다.
OpenAI 호환이 아니라 PaddleX `/layout-parsing` 엔드포인트 — base64 이미지 POST →
markdown(text+images) + prunedResult(parsing_res_list 구조) + outputImages(시각화).

다른 3엔진(MinerU2.5-VLM / DeepSeek-OCR / PaddleOCR-VL)과 달리 PP-StructureV3는
*도구*다(MinerU pipeline 대응). 레이아웃 블록 라벨, 이미지 픽셀 크롭, 수식 LaTeX
(인라인 포함), 표, `##` 헤딩 구조를 준다. 약점은 텍스트 모델(korean_PP-OCRv5_mobile_rec)
— **띄어쓰기 붕괴가 고질**이라 memex-kb 후처리(kime/textlint)가 복원해야 한다.

사용:  ./run.sh ppstructure-parse <PDF> [OUT] [-- --first N --last M --dpi 200]
직접:  python3 scripts/ppstructure_client.py <PDF> -o out --first 121 --last 137
"""
from __future__ import annotations
import argparse
import base64
import json
import logging
import sys
import time
from collections import Counter
from pathlib import Path
from urllib import request as urlrequest

import fitz  # PyMuPDF

LOG = logging.getLogger("ppstructure")

DEFAULT_URL = "http://localhost:8118/layout-parsing"
# PP-StructureV3 도구는 markdown_ignore_labels(number/footnote/header/footer)로
# 본문/비본문을 이미 분리해 준다 → markdown.text 는 본문 위주.


def render_page_png(page: "fitz.Page", dpi: int) -> bytes:
    mtx = fitz.Matrix(dpi / 72, dpi / 72)
    return page.get_pixmap(matrix=mtx).tobytes("png")


def parse_page(png: bytes, url: str, timeout: int) -> dict:
    """이미지 1장 → PaddleX layoutParsingResults[0]."""
    b64 = base64.b64encode(png).decode()
    payload = {"file": b64, "fileType": 1}  # fileType 1 = image
    req = urlrequest.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urlrequest.urlopen(req, timeout=timeout) as r:
        resp = json.load(r)
    return resp["result"]["layoutParsingResults"][0]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="PP-StructureV3 thin-client (도구: md+asset+구조)")
    ap.add_argument("pdf", help="입력 PDF")
    ap.add_argument("-o", "--out", default="ppstructure-out", help="출력 디렉토리")
    ap.add_argument("--first", type=int, default=1)
    ap.add_argument("--last", type=int, default=0, help="0=끝까지")
    ap.add_argument("--pages", default="", help="특정 페이지만(1-based, 콤마)")
    ap.add_argument("--dpi", type=int, default=200, help="렌더 DPI(기본 200 — PP-OCR은 고DPI 유리)")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        LOG.error("PDF 없음: %s", pdf_path)
        return 1

    doc = fitz.open(pdf_path)
    n = doc.page_count
    if args.pages:
        pages = [int(x) for x in args.pages.split(",") if x.strip()]
        pages = [p for p in pages if 1 <= p <= n]
    else:
        last = args.last if args.last else n
        first, last = max(1, args.first), min(args.last or n, n)
        pages = list(range(first, last + 1)) if first <= last else []
    if not pages:
        LOG.error("파싱할 페이지 없음")
        return 1

    stem = pdf_path.stem
    outdir = Path(args.out) / stem
    imgdir = outdir / "images"
    outdir.mkdir(parents=True, exist_ok=True)

    LOG.info("PP-StructureV3: %s  %d쪽 중 %d페이지  dpi=%d", stem, n, len(pages), args.dpi)
    md_pages: list[str] = []
    structure: list[dict] = []
    label_tally: Counter = Counter()
    asset_count = 0
    t0 = time.time()
    for pno in pages:
        png = render_page_png(doc[pno - 1], args.dpi)
        try:
            it = parse_page(png, args.url, args.timeout)
        except Exception as e:                       # noqa: BLE001
            LOG.warning("  p%d 실패: %s", pno, e)
            md_pages.append(f"<!-- p{pno} 실패: {e} -->")
            continue
        md = (it.get("markdown") or {})
        text = md.get("text", "")
        images = md.get("images") or {}             # {상대경로: base64}
        # asset 크롭 저장
        for relpath, b64 in images.items():
            imgdir.mkdir(parents=True, exist_ok=True)
            name = f"p{pno:03d}_{Path(relpath).name}"
            try:
                (imgdir / name).write_bytes(base64.b64decode(b64))
                asset_count += 1
            except Exception as e:                   # noqa: BLE001
                LOG.warning("  p%d asset 저장 실패 %s: %s", pno, relpath, e)
        # 구조 라벨 집계
        plist = (it.get("prunedResult") or {}).get("parsing_res_list", [])
        labels = [b.get("block_label") for b in plist]
        label_tally.update(labels)
        structure.append({"page": pno, "labels": labels})
        md_pages.append(f"<!-- p{pno} -->\n{text.strip()}")
        LOG.info("  p%d: %d자 · %d블록 [%s] · 크롭 %d",
                 pno, len(text), len(plist),
                 ",".join(sorted(set(filter(None, labels)))), len(images))

    md_path = outdir / f"{stem}.md"
    md_path.write_text("\n\n".join(md_pages) + "\n", encoding="utf-8")
    (outdir / f"{stem}_structure.json").write_text(
        json.dumps(structure, ensure_ascii=False, indent=1), encoding="utf-8")

    dt = time.time() - t0
    LOG.info("완료 %.1fs · 라벨분포 %s · asset크롭 %d개",
             dt, dict(label_tally), asset_count)
    LOG.info("  md     : %s", md_path)
    LOG.info("  images : %s (%d)", imgdir, asset_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())

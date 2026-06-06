#!/usr/bin/env python3
"""PaddleOCR-VL thin-client — 스캔 PDF → raw Markdown (원격 vLLM).

추론은 gpu3i RTX 5080의 vLLM(served-name: paddleocr-vl, OpenAI 호환)이 한다.
이쪽은 PDF→페이지 이미지 렌더 + OCR 호출 + 페이지 조립만.
로컬엔 torch/CUDA 불필요(PyMuPDF + urllib 만).

DeepSeek-OCR 클라와 대칭이되, PaddleOCR-VL vLLM 엔드포인트는 grounding 라벨도
content_list.json 도 주지 않는다 — **순수 이미지→텍스트** 다. 출력 특성(p121 실측):
  - 본문 글자 정확도 높음(한국어/라틴 혼용 깨끗)
  - **물리적 줄바꿈을 그대로 보존**(MinerU 처럼 문단 1줄로 합치지 않음)
  - running-foot 페이지번호가 본문 끝줄에 섞임
  - 헤딩/이미지/수식 라벨 없음(평문)

평가 원칙(GLG): 후처리(구조복원/교정/봉합)는 우리가 결정론적으로 소유하므로,
엔진은 **raw 글자/레이아웃 충실도**로만 줄세운다. 그래서 이 클라는 엔진 출력에
가공을 최소화한 raw md 를 낸다(--strip-page-num 만 옵션). mineru2org 투입용
문단 재조립은 평가가 끝난 뒤 별도 단계로 둔다.

사용:  ./run.sh paddleocr-parse <PDF> [OUT_DIR] [-- --first N --last M]  (터널 자동 + nix env)
직접:  python3 scripts/paddleocr_vl_client.py <PDF> -o out --first 121 --last 137
"""
from __future__ import annotations
import argparse
import base64
import json
import logging
import re
import sys
import time
from pathlib import Path
from urllib import request as urlrequest

import fitz  # PyMuPDF

LOG = logging.getLogger("paddleocr_vl")

DEFAULT_URL = "http://localhost:8001/v1/chat/completions"
DEFAULT_MODEL = "paddleocr-vl"
# "OCR:" 와 "Convert the document to markdown." 출력 동일(p121 실측) → 간결한 쪽.
DEFAULT_PROMPT = "OCR:"

# running-head/foot 페이지번호: 순수 숫자(최대 4자리) 한 줄.
PAGENUM_RE = re.compile(r"^\s*\d{1,4}\s*$")


def render_page_png(page: "fitz.Page", dpi: int) -> bytes:
    """PDF 페이지 → PNG bytes."""
    mtx = fitz.Matrix(dpi / 72, dpi / 72)
    return page.get_pixmap(matrix=mtx).tobytes("png")


def ocr_page(png: bytes, url: str, model: str, prompt: str,
             max_tokens: int, timeout: int) -> tuple[str, dict]:
    """이미지 1장 → OCR 텍스트 + usage. OpenAI 호환 chat/completions."""
    b64 = base64.b64encode(png).decode()
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
                {"type": "text", "text": prompt},
            ],
        }],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }
    req = urlrequest.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urlrequest.urlopen(req, timeout=timeout) as r:
        resp = json.load(r)
    return resp["choices"][0]["message"]["content"], resp.get("usage", {})


def strip_page_numbers(text: str) -> str:
    """맨 앞/맨 끝의 순수 숫자 줄(running head/foot)만 제거. 본문 중간 숫자는 보존."""
    lines = text.splitlines()
    while lines and PAGENUM_RE.match(lines[0]):
        lines.pop(0)
    while lines and PAGENUM_RE.match(lines[-1]):
        lines.pop()
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="PaddleOCR-VL thin-client (PDF → raw md)")
    ap.add_argument("pdf", help="입력 PDF")
    ap.add_argument("-o", "--out", default="paddleocr-out", help="출력 디렉토리(기본 paddleocr-out)")
    ap.add_argument("--first", type=int, default=1, help="시작 페이지(1-based, 포함)")
    ap.add_argument("--last", type=int, default=0, help="끝 페이지(포함, 0=끝까지)")
    ap.add_argument("--pages", default="", help="특정 페이지만(1-based, 콤마): 오라클용. 예 121,129,137")
    ap.add_argument("--dpi", type=int, default=150, help="렌더 DPI(기본 150)")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--prompt", default=DEFAULT_PROMPT)
    ap.add_argument("--max-tokens", type=int, default=6000)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--strip-page-num", action="store_true",
                    help="페이지 맨앞/맨끝 순수 숫자 줄(running head/foot) 제거")
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
        first = max(1, args.first)
        last = min(last, n)
        if first > last:
            LOG.error("페이지 범위 오류: %d..%d (문서 %d쪽)", first, last, n)
            return 1
        pages = list(range(first, last + 1))

    stem = pdf_path.stem
    outdir = Path(args.out) / stem
    outdir.mkdir(parents=True, exist_ok=True)

    if not pages:
        LOG.error("파싱할 페이지 없음")
        return 1
    LOG.info("PaddleOCR-VL: %s  %d쪽 중 %d페이지  dpi=%d  prompt=%r",
             stem, n, len(pages), args.dpi, args.prompt)

    md_pages: list[str] = []
    tot_prompt = tot_completion = 0
    t0 = time.time()
    for pno in pages:
        page = doc[pno - 1]
        png = render_page_png(page, args.dpi)
        try:
            raw, usage = ocr_page(png, args.url, args.model, args.prompt,
                                  args.max_tokens, args.timeout)
        except Exception as e:                     # noqa: BLE001 — 페이지 단위 격리
            LOG.warning("  p%d OCR 실패: %s", pno, e)
            md_pages.append(f"<!-- p{pno} OCR 실패: {e} -->")
            continue
        if args.strip_page_num:
            raw = strip_page_numbers(raw)
        # 페이지 경계를 주석으로 남겨 비교 시 페이지 정렬 가능(가공 아님).
        md_pages.append(f"<!-- p{pno} -->\n{raw.strip()}")
        ct = usage.get("completion_tokens", 0)
        tot_prompt += usage.get("prompt_tokens", 0)
        tot_completion += ct
        LOG.info("  p%d: %d자 / %d tok", pno, len(raw), ct)

    md_path = outdir / f"{stem}.md"
    md_path.write_text("\n\n".join(md_pages) + "\n", encoding="utf-8")

    dt = time.time() - t0
    LOG.info("완료 %.1fs · %d페이지 · tokens(prompt=%d completion=%d)",
             dt, len(pages), tot_prompt, tot_completion)
    LOG.info("  md : %s", md_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

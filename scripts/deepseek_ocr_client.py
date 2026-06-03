#!/usr/bin/env python3
"""DeepSeek-OCR thin-client — 스캔 PDF → MinerU 호환 Markdown (원격 vLLM).

추론은 gpu1i RTX 5080의 vLLM(served-name: deepseek-ocr, OpenAI 호환)이 한다.
이쪽은 PDF→페이지 이미지 렌더 + grounding OCR 호출 + 블록 파서로 md 조립만.
로컬엔 torch/CUDA 불필요(PyMuPDF + urllib 만).

MinerU 클라(`-b vlm-http-client`)와 대칭이되, DeepSeek-OCR vLLM은 content_list.json을
주지 않는다(순수 이미지→md 엔드포인트). 대신 grounding 모드가 `label[[bbox]]` 블록을 줘서
시맨틱 라벨(text/equation/sub_title/title/image)로 구조를 부분 복원한다.

산출은 기존 scripts/mineru2org.py 가 받을 수 있도록 MinerU md 관례에 맞춘다:
  title     → '# '
  sub_title → '## '
  text      → 문단(인라인 \\(..\\) 유지)
  equation  → \\[..\\] 그대로(DeepSeek가 이미 디스플레이로 줌)
  image     → 자산 없음(순수 OCR) → '<!-- image bbox=.. -->' 주석으로만 표시
근거(grounding 블록: page/label/bbox/text)는 <doc>_blocks.json 으로 남긴다.

사용:  ./run.sh deepseek-parse <PDF> [OUT_DIR]   (터널 자동 + nix env)
직접:  python3 scripts/deepseek_ocr_client.py <PDF> -o out [--first N --last M]
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

LOG = logging.getLogger("deepseek_ocr")

DEFAULT_URL = "http://localhost:8000/v1/chat/completions"
DEFAULT_MODEL = "deepseek-ocr"
# grounding 모드: label[[bbox]] 시맨틱 블록을 준다(구조 복원에 유리).
GROUNDING_PROMPT = "<image>\n<|grounding|>Convert the document to markdown."
PLAIN_PROMPT = "<image>\nConvert the document to markdown."

# label[[x1, y1, x2, y2]] 블록 구분자 (한 줄)
BLOCK_RE = re.compile(r"^([a-z_]+)\[\[\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\s*\]\]\s*$")

# 헤딩 라벨 → md 레벨
HEADING = {"title": "#", "sub_title": "##"}


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


def parse_blocks(raw: str, page_idx: int) -> list[dict]:
    """grounding 출력 → 블록 리스트. `label[[bbox]]` 다음 줄들이 content."""
    blocks: list[dict] = []
    cur: dict | None = None
    for line in raw.splitlines():
        m = BLOCK_RE.match(line.strip())
        if m:
            if cur:
                blocks.append(cur)
            label, x1, y1, x2, y2 = m.groups()
            cur = {"page": page_idx, "label": label,
                   "bbox": [int(x1), int(y1), int(x2), int(y2)], "lines": []}
        else:
            if cur is None:
                # 라벨 없이 시작(plain 모드 폴백) → text 블록
                cur = {"page": page_idx, "label": "text", "bbox": None, "lines": []}
            cur["lines"].append(line)
    if cur:
        blocks.append(cur)
    for b in blocks:
        b["text"] = "\n".join(b.pop("lines")).strip()
    return [b for b in blocks if b["text"] or b["label"] == "image"]


def blocks_to_md(blocks: list[dict]) -> str:
    """블록 → MinerU 호환 md."""
    out: list[str] = []
    for b in blocks:
        label, text = b["label"], b["text"]
        if label in HEADING:
            out.append(f"{HEADING[label]} {' '.join(text.split())}")
        elif label == "equation":
            out.append(text)                       # 이미 \[..\]
        elif label == "image":
            out.append(f"<!-- image bbox={b.get('bbox')} (DeepSeek-OCR: no asset) -->")
        else:                                      # text 등
            out.append(text)
    return "\n\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DeepSeek-OCR thin-client (PDF → MinerU 호환 md)")
    ap.add_argument("pdf", help="입력 PDF")
    ap.add_argument("-o", "--out", default="deepseek-out", help="출력 디렉토리(기본 deepseek-out)")
    ap.add_argument("--first", type=int, default=1, help="시작 페이지(1-based, 포함)")
    ap.add_argument("--last", type=int, default=0, help="끝 페이지(포함, 0=끝까지)")
    ap.add_argument("--dpi", type=int, default=150, help="렌더 DPI(기본 150)")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--max-tokens", type=int, default=6000)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--plain", action="store_true",
                    help="grounding 끄고 순수 md(라벨/bbox 없음)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        LOG.error("PDF 없음: %s", pdf_path)
        return 1

    prompt = PLAIN_PROMPT if args.plain else GROUNDING_PROMPT
    doc = fitz.open(pdf_path)
    n = doc.page_count
    last = args.last if args.last else n
    first = max(1, args.first)
    last = min(last, n)
    if first > last:
        LOG.error("페이지 범위 오류: %d..%d (문서 %d쪽)", first, last, n)
        return 1

    stem = pdf_path.stem
    outdir = Path(args.out) / stem
    outdir.mkdir(parents=True, exist_ok=True)

    LOG.info("DeepSeek-OCR: %s  p%d..%d / %d쪽  dpi=%d  %s",
             stem, first, last, n, args.dpi,
             "plain" if args.plain else "grounding")

    all_blocks: list[dict] = []
    md_pages: list[str] = []
    tot_prompt = tot_completion = 0
    t0 = time.time()
    for pno in range(first, last + 1):
        page = doc[pno - 1]
        png = render_page_png(page, args.dpi)
        try:
            raw, usage = ocr_page(png, args.url, args.model, prompt,
                                  args.max_tokens, args.timeout)
        except Exception as e:                     # noqa: BLE001 — 페이지 단위 격리
            LOG.warning("  p%d OCR 실패: %s", pno, e)
            md_pages.append(f"<!-- p{pno} OCR 실패: {e} -->")
            continue
        blocks = parse_blocks(raw, pno - 1)        # page_idx 0-based (MinerU 관례)
        all_blocks.extend(blocks)
        md_pages.append(blocks_to_md(blocks))
        tot_prompt += usage.get("prompt_tokens", 0)
        tot_completion += usage.get("completion_tokens", 0)
        labels = ",".join(sorted({b["label"] for b in blocks}))
        LOG.info("  p%d: %d블록 [%s]", pno, len(blocks), labels)

    md_path = outdir / f"{stem}.md"
    blocks_path = outdir / f"{stem}_blocks.json"
    md_path.write_text("\n\n".join(md_pages), encoding="utf-8")
    blocks_path.write_text(json.dumps(all_blocks, ensure_ascii=False, indent=1),
                           encoding="utf-8")

    dt = time.time() - t0
    LOG.info("완료 %.1fs · %d블록 · tokens(prompt=%d completion=%d)",
             dt, len(all_blocks), tot_prompt, tot_completion)
    LOG.info("  md     : %s", md_path)
    LOG.info("  blocks : %s", blocks_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

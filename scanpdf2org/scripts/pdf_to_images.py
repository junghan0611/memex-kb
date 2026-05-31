#!/usr/bin/env python3
"""PDF 페이지 → PNG 렌더 (vision 전사용).

전통 OCR가 아니다. 스캔 PDF의 각 페이지를 고해상도 PNG로 래스터화하여,
에이전트(Claude/Codex/Gemini)가 vision으로 직접 읽고 org로 전사하게 만드는
파이프라인의 1단계다.

사용:
    python scanpdf2org/scripts/pdf_to_images.py <PDF> --out <DIR> [--pages 1-20] [--dpi 200]

예시:
    # 목차 추정용 앞부분만
    python scanpdf2org/scripts/pdf_to_images.py scanpdf/물질생명인간001.pdf \
        --out scanpdf/work/물질생명인간/pages --pages 1-15

    # 1장 페이지 범위
    python scanpdf2org/scripts/pdf_to_images.py scanpdf/물질생명인간001.pdf \
        --out scanpdf/work/물질생명인간/pages --pages 21-48 --dpi 220

출력 파일명: 0001.png, 0002.png … (1-based, PDF 물리 페이지 번호)
이미 존재하는 PNG는 건너뛴다(idempotent). --force로 덮어쓰기.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("PyMuPDF(fitz) 없음. `nix develop` 환경에서 실행하세요.")


def parse_pages(spec: str, total: int) -> list[int]:
    """'1-20', '5', '1-5,30-35,80' → 정렬된 1-based 페이지 리스트."""
    if not spec:
        return list(range(1, total + 1))
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            for p in range(int(a), int(b) + 1):
                out.add(p)
        else:
            out.add(int(part))
    return sorted(p for p in out if 1 <= p <= total)


def main() -> int:
    ap = argparse.ArgumentParser(description="PDF 페이지를 PNG로 렌더")
    ap.add_argument("pdf", type=Path, help="입력 PDF")
    ap.add_argument("--out", type=Path, required=True, help="PNG 출력 디렉토리")
    ap.add_argument("--pages", default="", help="페이지 범위 (예: 1-20, 5, 1-5,30-35). 비우면 전체")
    ap.add_argument("--dpi", type=int, default=200, help="렌더 해상도 (기본 200)")
    ap.add_argument("--force", action="store_true", help="기존 PNG 덮어쓰기")
    args = ap.parse_args()

    if not args.pdf.exists():
        sys.exit(f"PDF 없음: {args.pdf}")

    doc = fitz.open(args.pdf)
    total = doc.page_count
    pages = parse_pages(args.pages, total)
    if not pages:
        sys.exit(f"렌더할 페이지 없음 (PDF 총 {total}p, --pages={args.pages!r})")

    args.out.mkdir(parents=True, exist_ok=True)
    zoom = args.dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)

    rendered = skipped = 0
    for p in pages:
        dst = args.out / f"{p:04d}.png"
        if dst.exists() and not args.force:
            skipped += 1
            continue
        pix = doc[p - 1].get_pixmap(matrix=mat)
        pix.save(dst)
        rendered += 1
        print(f"  → {dst}  ({pix.width}x{pix.height})")

    print(f"\n완료: 렌더 {rendered}, 건너뜀 {skipped} / 요청 {len(pages)}p "
          f"(PDF 총 {total}p, dpi={args.dpi})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

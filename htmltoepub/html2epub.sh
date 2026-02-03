#!/bin/bash
# HTML → EPUB 변환 스크립트
#
# 사용법:
#   ./html2epub.sh input.html output.epub [metadata.yaml]
#
# 예시:
#   ./html2epub.sh tioh-ko-clean.html tioh-ko.epub metadata-tioh.yaml

set -e

INPUT_HTML="${1:-tioh-ko-clean.html}"
OUTPUT_EPUB="${2:-${INPUT_HTML%.html}.epub}"
METADATA="${3:-}"

echo "=== HTML → EPUB 변환 ==="
echo "입력: $INPUT_HTML"
echo "출력: $OUTPUT_EPUB"

# pandoc 옵션
OPTS=(
    --from=html
    --to=epub3
    --toc
    --toc-depth=2
    --split-level=2
)

# 메타데이터 파일이 있으면 추가
if [[ -n "$METADATA" && -f "$METADATA" ]]; then
    echo "메타데이터: $METADATA"
    OPTS+=(--metadata-file="$METADATA")
fi

# 변환 실행
pandoc "${OPTS[@]}" -o "$OUTPUT_EPUB" "$INPUT_HTML"

# 결과 확인
if [[ -f "$OUTPUT_EPUB" ]]; then
    SIZE=$(du -h "$OUTPUT_EPUB" | cut -f1)
    echo ""
    echo "✓ EPUB 생성 완료!"
    echo "  파일: $OUTPUT_EPUB"
    echo "  크기: $SIZE"

    # EPUB 내용 확인 (목차)
    echo ""
    echo "=== EPUB 목차 (처음 20개) ==="
    unzip -p "$OUTPUT_EPUB" "EPUB/nav.xhtml" 2>/dev/null | grep -oP '(?<=<a[^>]*>)[^<]+' | head -20 || \
    unzip -p "$OUTPUT_EPUB" "nav.xhtml" 2>/dev/null | grep -oP '(?<=<a[^>]*>)[^<]+' | head -20 || \
    echo "(목차 확인 불가)"
else
    echo "✗ EPUB 생성 실패"
    exit 1
fi

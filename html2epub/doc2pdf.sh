#!/bin/bash
# Org/Markdown → PDF 변환 스크립트 (책 제본용)
#
# 사용법:
#   ./doc2pdf.sh input.{org|md} output.pdf [style.yaml]
#
# 예시:
#   ./doc2pdf.sh tioh-ko.md tioh-ko.pdf book-style.yaml
#   ./doc2pdf.sh tioh-ko.org tioh-ko.pdf book-style.yaml

set -e

INPUT_DOC="${1}"
OUTPUT_PDF="${2:-${INPUT_DOC%.*}.pdf}"
STYLE_YAML="${3:-book-style.yaml}"

if [[ -z "$INPUT_DOC" ]]; then
    echo "사용법: $0 input.{org|md} [output.pdf] [style.yaml]"
    exit 1
fi

# 입력 형식 자동 감지
EXT="${INPUT_DOC##*.}"
case "$EXT" in
    org) FROM_FORMAT="org" ;;
    md|markdown) FROM_FORMAT="markdown" ;;
    *)
        echo "지원하지 않는 형식: $EXT (org, md만 가능)"
        exit 1
        ;;
esac

echo "=== $FROM_FORMAT → PDF 변환 (책 제본용) ==="
echo "입력: $INPUT_DOC"
echo "출력: $OUTPUT_PDF"
echo "스타일: $STYLE_YAML"

# pandoc 옵션
OPTS=(
    --from="$FROM_FORMAT"
    --to=pdf
    --pdf-engine=xelatex
    --toc
    --toc-depth=2
    --top-level-division=chapter
)

# 스타일 메타데이터 추가
if [[ -f "$STYLE_YAML" ]]; then
    OPTS+=(--metadata-file="$STYLE_YAML")
fi

# 변환 실행
echo ""
echo "변환 중... (한글 폰트 로딩으로 시간이 걸릴 수 있습니다)"
pandoc "${OPTS[@]}" -o "$OUTPUT_PDF" "$INPUT_DOC"

# 결과 확인
if [[ -f "$OUTPUT_PDF" ]]; then
    SIZE=$(du -h "$OUTPUT_PDF" | cut -f1)
    PAGES=$(pdfinfo "$OUTPUT_PDF" 2>/dev/null | grep -oP 'Pages:\s+\K\d+' || echo "?")

    echo ""
    echo "✓ PDF 생성 완료!"
    echo "  파일: $OUTPUT_PDF"
    echo "  크기: $SIZE"
    echo "  페이지: $PAGES 페이지"
else
    echo "✗ PDF 생성 실패"
    exit 1
fi

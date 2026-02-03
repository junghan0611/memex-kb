#!/usr/bin/env bash
#
# epub2org.sh - epub을 깔끔한 org/md로 변환
#
# 사용법:
#   ./epub2org.sh book.epub [output_name]
#
# 예시:
#   ./epub2org.sh VibeCoding.epub VibeCoding
#   -> VibeCoding.org (원본), VibeCoding.md (파생) 생성
#
# 파이프라인:
#   epub -> raw.md -> clean.md -> clean.org (정리) -> final.md
#   org가 원본, md는 org에서 파생
#
# 의존성:
#   - pandoc
#   - python3
#   - cleanup_epub_md.py (같은 디렉토리에 있어야 함)
#

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <input.epub> [output_name]"
    echo "Example: $0 book.epub book"
    exit 1
fi

INPUT_EPUB="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLEANUP_SCRIPT="$SCRIPT_DIR/cleanup_epub_md.py"

# 출력 이름 결정
if [ -n "$2" ]; then
    OUTPUT_NAME="$2"
else
    OUTPUT_NAME=$(basename "$INPUT_EPUB" .epub)
fi

RAW_MD="${OUTPUT_NAME}_raw.md"
TMP_MD="${OUTPUT_NAME}_tmp.md"
TMP_ORG="${OUTPUT_NAME}_tmp.org"
FINAL_ORG="${OUTPUT_NAME}.org"
FINAL_MD="${OUTPUT_NAME}.md"

echo "==> [1/5] epub -> markdown 변환..."
pandoc "$INPUT_EPUB" -t markdown -o "$RAW_MD"
echo "    생성: $RAW_MD"

echo "==> [2/5] markdown 정리..."
python3 "$CLEANUP_SCRIPT" "$RAW_MD" "$TMP_MD"
echo "    생성: $TMP_MD"

echo "==> [3/5] markdown -> org 변환..."
pandoc "$TMP_MD" -f markdown -t org -o "$TMP_ORG"
echo "    생성: $TMP_ORG"

echo "==> [4/5] org 정리 (링크, 문단, 구조)..."
python3 "$CLEANUP_SCRIPT" --fix-org "$TMP_ORG"
mv "$TMP_ORG" "$FINAL_ORG"
echo "    생성: $FINAL_ORG"

echo "==> [5/5] org -> markdown 파생..."
pandoc "$FINAL_ORG" -f org -t markdown-smart --wrap=none -o "$FINAL_MD"
echo "    생성: $FINAL_MD"

# 임시 파일 정리
rm -f "$RAW_MD" "$TMP_MD"

echo ""
echo "==> 완료!"
echo "    Org (원본): $FINAL_ORG"
echo "    MD (파생):  $FINAL_MD"

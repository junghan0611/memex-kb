#!/usr/bin/env bash
# AsciiDoc → HWPX 역변환 스크립트
#
# Usage:
#   ./asciidoc2hwpx.sh input.adoc [template.hwpx] [output.hwpx]
#
# Example:
#   ./asciidoc2hwpx.sh report.adoc
#   ./asciidoc2hwpx.sh report.adoc template.hwpx output.hwpx

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 입력 검증
if [[ $# -lt 1 ]]; then
    echo -e "${RED}Usage: $0 input.adoc [template.hwpx] [output.hwpx]${NC}"
    exit 1
fi

INPUT="$1"
TEMPLATE="${2:-}"
OUTPUT="${3:-${INPUT%.adoc}.hwpx}"

if [[ ! -f "$INPUT" ]]; then
    echo -e "${RED}Error: 파일을 찾을 수 없습니다: $INPUT${NC}"
    exit 1
fi

echo -e "${YELLOW}AsciiDoc → HWPX 역변환 시작${NC}"
echo "  입력: $INPUT"
if [[ -n "$TEMPLATE" ]]; then
    echo "  템플릿: $TEMPLATE"
fi
echo "  출력: $OUTPUT"

# nix develop 환경에서 실행
cd "$PROJECT_DIR"

if [[ -n "$TEMPLATE" && -f "$TEMPLATE" ]]; then
    nix develop --command python hwpx2asciidoc/asciidoc_to_hwpx.py "$INPUT" -t "$TEMPLATE" -o "$OUTPUT"
else
    nix develop --command python hwpx2asciidoc/asciidoc_to_hwpx.py "$INPUT" -o "$OUTPUT"
fi

echo -e "${GREEN}✅ 역변환 완료: $OUTPUT${NC}"

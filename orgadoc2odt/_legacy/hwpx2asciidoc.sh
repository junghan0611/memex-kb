#!/usr/bin/env bash
# HWPX → AsciiDoc 변환 스크립트
#
# Usage:
#   ./hwpx2asciidoc.sh input.hwpx [output.adoc]
#
# Example:
#   ./hwpx2asciidoc.sh report.hwpx
#   ./hwpx2asciidoc.sh report.hwpx /tmp/report.adoc

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
    echo -e "${RED}Usage: $0 input.hwpx [output.adoc]${NC}"
    exit 1
fi

INPUT="$1"
OUTPUT="${2:-${INPUT%.hwpx}.adoc}"

if [[ ! -f "$INPUT" ]]; then
    echo -e "${RED}Error: 파일을 찾을 수 없습니다: $INPUT${NC}"
    exit 1
fi

echo -e "${YELLOW}HWPX → AsciiDoc 변환 시작${NC}"
echo "  입력: $INPUT"
echo "  출력: $OUTPUT"

# nix develop 환경에서 실행
cd "$PROJECT_DIR"
nix develop --command python hwpx2asciidoc/hwpx_to_asciidoc.py "$INPUT" -o "$OUTPUT"

echo -e "${GREEN}✅ 변환 완료: $OUTPUT${NC}"

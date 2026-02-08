#!/usr/bin/env bash
# KIAT 연구개발계획서 Google Docs → 탭별 MD 다운로드
#
# 용도: "AI 홈·가전용 다중 IoT 소프트센서" 연구개발계획서를
#       Google Docs에서 최신 버전으로 가져올 때 사용.
#       문서가 업데이트될 때마다 이 스크립트 한 줄이면 됨.
#
# 사용법:
#   ./scripts/export_kiat_proposal.sh           # depth=2 (기본)
#   ./scripts/export_kiat_proposal.sh --depth 1 # 1단계 하위까지
#   ./scripts/export_kiat_proposal.sh --depth 0 # 상위 탭만
#   ./scripts/export_kiat_proposal.sh --depth -1 # 전체 (무제한)
set -euo pipefail

DOC_ID="1SEJWIbO-kA6Kzriun_iQ5QZuxlAzJzTYg6TtJcI1EGM"
ACCOUNT="jhkim2@goqual.com"
DEPTH=2
OUTPUT_DIR="./output/kiat-proposal"

while [[ $# -gt 0 ]]; do
    case $1 in
        --depth|-d) DEPTH="$2"; shift 2 ;;
        --output|-o) OUTPUT_DIR="$2"; shift 2 ;;
        *) echo "알 수 없는 옵션: $1"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "KIAT 연구개발계획서 다운로드 (depth=${DEPTH})"
echo "  출력: ${OUTPUT_DIR}/"
echo ""

nix develop --command python "${SCRIPT_DIR}/gdocs_md_processor.py" export \
    "$DOC_ID" \
    --account "$ACCOUNT" \
    --output-dir "$OUTPUT_DIR" \
    --depth "$DEPTH"

#!/usr/bin/env bash
# Org + AsciiDoc 병합 셀 → ODT 파이프라인
#
# Usage: ./run.sh <command> [options]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

show_help() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  Org + AsciiDoc 병합 셀 → ODT 파이프라인${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}사용법:${NC} ./run.sh <command> [options]"
    echo ""
    echo -e "${YELLOW}명령어:${NC}"
    echo -e "  ${GREEN}convert${NC}     <input.org> [-o out.odt] [-r ref.odt]  Org → ODT (병합 셀 보존)"
    echo -e "  ${GREEN}preprocess${NC}  <input.org> [-o out.org]              AsciiDoc블록 → HTML 전처리만"
    echo -e "  ${GREEN}verify${NC}      <file.odt>                            ODT 병합 셀 검사"
    echo -e "  ${GREEN}test${NC}                                              전체 파이프라인 검증"
    echo ""
    echo -e "${YELLOW}파이프라인:${NC}"
    echo -e "  Org (#+begin_src adoc) → asciidoctor → HTML table"
    echo -e "  → pandoc org→html → pandoc html→odt (병합 셀 보존)"
    echo ""
    echo -e "${YELLOW}예시:${NC}"
    echo -e "  ./run.sh convert samples/test-merge-tables.org"
    echo -e "  ./run.sh convert 제안서.org -r reference.odt"
    echo -e "  ./run.sh verify output.odt"
    echo -e "  ./run.sh test"
    echo ""
}

run_python() {
    cd "$PROJECT_DIR"
    nix develop --command python "$@"
}

cmd_convert() {
    echo -e "${YELLOW}Org + AsciiDoc → ODT 변환${NC}"
    run_python "$SCRIPT_DIR/adoc_to_odt.py" convert "$@"
}

cmd_preprocess() {
    echo -e "${YELLOW}AsciiDoc 블록 전처리${NC}"
    run_python "$SCRIPT_DIR/adoc_to_odt.py" preprocess "$@"
}

cmd_verify() {
    echo -e "${YELLOW}ODT 병합 셀 검사${NC}"
    run_python "$SCRIPT_DIR/adoc_to_odt.py" verify "$@"
}

cmd_test() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  전체 파이프라인 검증${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    local input="$SCRIPT_DIR/samples/test-merge-tables.org"
    local output="$SCRIPT_DIR/samples/output/test-merge-tables.odt"
    mkdir -p "$SCRIPT_DIR/samples/output"

    echo ""
    echo -e "${YELLOW}[1/3] 변환: Org → ODT${NC}"
    run_python "$SCRIPT_DIR/adoc_to_odt.py" convert "$input" -o "$output"

    echo ""
    echo -e "${YELLOW}[2/3] 검증: 병합 셀 확인${NC}"
    run_python "$SCRIPT_DIR/adoc_to_odt.py" verify "$output"

    echo ""
    echo -e "${YELLOW}[3/3] 파일 정보${NC}"
    ls -lh "$output"

    echo ""
    echo -e "${GREEN}✅ 파이프라인 검증 완료${NC}"
    echo -e "  ODT 파일: $output"
    echo -e "  LibreOffice로 열어서 시각 확인: ${CYAN}libreoffice $output${NC}"
}

case "${1:-}" in
    convert)     shift; cmd_convert "$@" ;;
    preprocess)  shift; cmd_preprocess "$@" ;;
    verify)      shift; cmd_verify "$@" ;;
    test)        shift; cmd_test "$@" ;;
    -h|--help|"")  show_help ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac

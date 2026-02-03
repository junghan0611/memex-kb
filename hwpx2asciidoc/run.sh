#!/usr/bin/env bash
# HWPX ↔ AsciiDoc 변환 도구
#
# Usage: ./run.sh <command> [options]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

show_help() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  HWPX ↔ AsciiDoc 변환 도구${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}사용법:${NC} ./run.sh <command> [options]"
    echo ""
    echo -e "${YELLOW}변환 명령어:${NC}"
    echo -e "  ${GREEN}to-adoc${NC}    <input.hwpx> [output.adoc]     HWPX → AsciiDoc"
    echo -e "  ${GREEN}to-hwpx${NC}    <input.adoc> [template] [out]  AsciiDoc → HWPX"
    echo -e "  ${GREEN}to-html${NC}    <input.adoc> [output.html]     AsciiDoc → HTML"
    echo -e "  ${GREEN}to-pdf${NC}     <input.adoc> [output.pdf]      AsciiDoc → PDF"
    echo ""
    echo -e "${YELLOW}분석 명령어:${NC}"
    echo -e "  ${GREEN}styles${NC}     <input.hwpx> [output.json]     폰트/스타일 추출"
    echo -e "  ${GREEN}test${NC}       <input.hwpx>                   왕복 변환 테스트"
    echo ""
    echo -e "${YELLOW}예시:${NC}"
    echo -e "  ./run.sh to-adoc 제안서.hwpx"
    echo -e "  ./run.sh to-hwpx 제안서.adoc 제안서.hwpx 결과.hwpx  ${BLUE}# 템플릿으로 폰트 보존${NC}"
    echo -e "  ./run.sh to-pdf 제안서.adoc"
    echo -e "  ./run.sh styles 제안서.hwpx"
    echo -e "  ./run.sh test 제안서.hwpx"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

run_python() {
    cd "$PROJECT_DIR"
    nix develop --command python "$@"
}

cmd_to_adoc() {
    if [[ $# -lt 1 ]]; then
        echo -e "${RED}Error: HWPX 파일을 지정하세요${NC}"
        echo "Usage: ./run.sh to-adoc <input.hwpx> [output.adoc]"
        exit 1
    fi
    local input="$1"
    local output="${2:-${input%.hwpx}.adoc}"

    echo -e "${YELLOW}HWPX → AsciiDoc${NC}"
    echo "  입력: $input"
    echo "  출력: $output"
    run_python "$SCRIPT_DIR/hwpx_to_asciidoc.py" "$input" -o "$output"
    echo -e "${GREEN}✅ 완료: $output${NC}"
}

cmd_to_hwpx() {
    if [[ $# -lt 1 ]]; then
        echo -e "${RED}Error: AsciiDoc 파일을 지정하세요${NC}"
        echo "Usage: ./run.sh to-hwpx <input.adoc> [template.hwpx] [output.hwpx]"
        exit 1
    fi
    local input="$1"
    local template="${2:-}"
    local output="${3:-${input%.adoc}.hwpx}"

    echo -e "${YELLOW}AsciiDoc → HWPX${NC}"
    echo "  입력: $input"
    [[ -n "$template" ]] && echo "  템플릿: $template (폰트 보존)"
    echo "  출력: $output"

    if [[ -n "$template" && -f "$template" ]]; then
        run_python "$SCRIPT_DIR/asciidoc_to_hwpx.py" "$input" -t "$template" -o "$output"
    else
        run_python "$SCRIPT_DIR/asciidoc_to_hwpx.py" "$input" -o "$output"
    fi
    echo -e "${GREEN}✅ 완료: $output${NC}"
}

cmd_to_html() {
    if [[ $# -lt 1 ]]; then
        echo -e "${RED}Error: AsciiDoc 파일을 지정하세요${NC}"
        echo "Usage: ./run.sh to-html <input.adoc> [output.html]"
        exit 1
    fi
    local input="$1"
    local output="${2:-${input%.adoc}.html}"

    echo -e "${YELLOW}AsciiDoc → HTML${NC}"
    asciidoctor "$input" -o "$output"
    echo -e "${GREEN}✅ 완료: $output${NC}"
}

cmd_to_pdf() {
    if [[ $# -lt 1 ]]; then
        echo -e "${RED}Error: AsciiDoc 파일을 지정하세요${NC}"
        echo "Usage: ./run.sh to-pdf <input.adoc> [output.pdf]"
        exit 1
    fi
    local input="$1"
    local output="${2:-${input%.adoc}.pdf}"

    echo -e "${YELLOW}AsciiDoc → PDF${NC}"
    asciidoctor-pdf "$input" -o "$output"
    echo -e "${GREEN}✅ 완료: $output${NC}"
}

cmd_styles() {
    if [[ $# -lt 1 ]]; then
        echo -e "${RED}Error: HWPX 파일을 지정하세요${NC}"
        echo "Usage: ./run.sh styles <input.hwpx> [output.json]"
        exit 1
    fi
    local input="$1"
    local output="${2:-${input%.hwpx}.styles.json}"

    echo -e "${YELLOW}스타일 추출${NC}"
    run_python "$SCRIPT_DIR/style_extractor.py" "$input" -o "$output"
}

cmd_test() {
    if [[ $# -lt 1 ]]; then
        echo -e "${RED}Error: HWPX 파일을 지정하세요${NC}"
        echo "Usage: ./run.sh test <input.hwpx>"
        exit 1
    fi

    echo -e "${YELLOW}왕복 변환 테스트${NC}"
    run_python "$SCRIPT_DIR/test_roundtrip.py" "$1"
}

# 메인
case "${1:-}" in
    to-adoc)  shift; cmd_to_adoc "$@" ;;
    to-hwpx)  shift; cmd_to_hwpx "$@" ;;
    to-html)  shift; cmd_to_html "$@" ;;
    to-pdf)   shift; cmd_to_pdf "$@" ;;
    styles)   shift; cmd_styles "$@" ;;
    test)     shift; cmd_test "$@" ;;
    -h|--help|"")  show_help ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac

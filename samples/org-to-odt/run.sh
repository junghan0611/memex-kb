#!/usr/bin/env bash
# Org → ODT/DOC 변환 파이프라인
# proposal-pipeline의 Emacs org-odt-export를 활용한 고품질 변환
#
# pandoc 대비 장점:
#   - reference.odt 스타일 정확 적용
#   - 한글 캡션 (그림, 표)
#   - 테이블 헤더 배경색 + 테두리 자동 보정
#   - CSL bibliography (URL 포함 참고문헌)
#
# 사용법:
#   ./run.sh build           # org → odt → doc 전체 빌드
#   ./run.sh build FILE.org  # 특정 파일 빌드
#   ./run.sh odt             # org → odt만
#   ./run.sh doc             # odt → doc만
#   ./run.sh check           # 의존성 확인
#   ./run.sh clean           # 생성 파일 정리
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE_DIR="$REPO_ROOT/proposal-pipeline"
EXPORT_EL="$PIPELINE_DIR/proposal-export.el"

# 기본 org 파일 (인자 없으면 sample.org)
ORG_FILE="${2:-$SCRIPT_DIR/sample.org}"
BASENAME="$(basename "$ORG_FILE" .org)"
ODT_FILE="$SCRIPT_DIR/$BASENAME.odt"
DOC_FILE="$SCRIPT_DIR/$BASENAME.doc"

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

usage() {
    cat <<EOF
Org → ODT/DOC 변환 파이프라인

사용법: ./run.sh <명령> [파일.org]

명령:
  build [FILE]  org → odt → doc 전체 빌드 (기본: sample.org)
  odt   [FILE]  org → odt 변환만
  postprocess   odt 테이블 후처리만
  doc           odt → doc 변환만
  clean         생성 파일 정리
  check         의존성 확인

예시:
  ./run.sh build                    # sample.org 빌드
  ./run.sh build my-resume.org      # 다른 파일 빌드
  ./run.sh check                    # 환경 확인
EOF
}

cmd_check() {
    info "의존성 확인..."
    local all_ok=true

    if command -v emacs &>/dev/null; then
        ok "emacs: $(emacs --version | head -1)"
    else
        err "emacs 없음"; all_ok=false
    fi

    if command -v libreoffice &>/dev/null; then
        ok "libreoffice: $(libreoffice --version 2>/dev/null | head -1)"
    else
        warn "libreoffice 없음 (doc 변환 불가)"
    fi

    if command -v python3 &>/dev/null; then
        ok "python3: $(python3 --version)"
    else
        err "python3 없음"; all_ok=false
    fi

    if [[ -f "$EXPORT_EL" ]]; then
        ok "proposal-export.el: $(realpath "$EXPORT_EL")"
    else
        err "proposal-export.el 없음: $EXPORT_EL"; all_ok=false
    fi

    if [[ -f "$PIPELINE_DIR/templates/reference.odt" ]]; then
        ok "reference.odt: $(ls -lh "$PIPELINE_DIR/templates/reference.odt" | awk '{print $5}')"
    else
        err "reference.odt 없음"; all_ok=false
    fi

    local bib_file="$SCRIPT_DIR/references.bib"
    if [[ -f "$bib_file" ]]; then
        local count
        count=$(grep -c '^@' "$bib_file" || true)
        ok "references.bib: ${count}개 엔트리"
    else
        warn "references.bib 없음 (인용 비활성)"
    fi

    $all_ok && ok "모든 의존성 확인 완료" || err "일부 의존성 누락"
}

cmd_odt() {
    info "org → odt 변환: $ORG_FILE"

    if [[ ! -f "$ORG_FILE" ]]; then
        err "파일 없음: $ORG_FILE"
        exit 1
    fi

    emacs --batch \
        -l "$EXPORT_EL" \
        --eval "(proposal-export-to-odt (expand-file-name \"$ORG_FILE\"))" \
        2>&1 | grep -E "^\[Proposal\]|ERROR|WARNING"

    ODT_FILE="$SCRIPT_DIR/$BASENAME.odt"
    if [[ -f "$ODT_FILE" ]]; then
        ok "생성: $ODT_FILE ($(ls -lh "$ODT_FILE" | awk '{print $5}'))"
    else
        err "ODT 생성 실패"
        exit 1
    fi
}

cmd_postprocess() {
    info "odt 테이블 후처리..."
    if [[ ! -f "$ODT_FILE" ]]; then
        err "파일 없음: $ODT_FILE"
        exit 1
    fi
    python3 "$PIPELINE_DIR/odt_postprocess.py" "$ODT_FILE"
    ok "후처리 완료"
}

cmd_doc() {
    info "odt → doc 변환..."
    if [[ ! -f "$ODT_FILE" ]]; then
        err "파일 없음: $ODT_FILE"
        exit 1
    fi
    libreoffice --headless --convert-to doc "$ODT_FILE" --outdir "$SCRIPT_DIR" 2>&1 | grep -v "^$"
    ok "생성: $DOC_FILE ($(ls -lh "$DOC_FILE" | awk '{print $5}'))"
}

cmd_build() {
    info "=== 전체 빌드: $ORG_FILE ==="
    echo ""
    cmd_odt
    echo ""
    cmd_postprocess
    echo ""
    cmd_doc
    echo ""
    ok "=== 빌드 완료 ==="
    echo ""
    ls -lh "$SCRIPT_DIR/$BASENAME".{org,odt,doc} 2>/dev/null
}

cmd_clean() {
    info "생성 파일 정리..."
    rm -f "$SCRIPT_DIR"/*.odt "$SCRIPT_DIR"/*.doc "$SCRIPT_DIR"/*.docx
    ok "정리 완료 (org 원본 유지)"
}

# ─── 메인 ───

cd "$SCRIPT_DIR"

case "${1:-}" in
    build)       cmd_build ;;
    odt)         cmd_odt ;;
    postprocess) cmd_postprocess ;;
    doc)         cmd_doc ;;
    clean)       cmd_clean ;;
    check)       cmd_check ;;
    *)           usage ;;
esac

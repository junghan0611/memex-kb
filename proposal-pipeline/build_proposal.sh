#!/usr/bin/env bash
#
# 제안서 파이프라인: Google Docs → MD → Org → ODT 변환 자동화
#
# memex-kb/output/kiat-proposal/ 의 MD를 Org로 변환하고 통합합니다.
# --export-odt 플래그로 Emacs batch ODT 내보내기 + 후처리까지 수행합니다.
#
# 사용법:
#   ./build_proposal.sh              # 전체 빌드 (MD 동기화 + 변환 + 통합)
#   ./build_proposal.sh --no-sync    # 동기화 없이 기존 md-source로 변환만
#   ./build_proposal.sh --export-md  # GDocs 다운로드부터 시작
#   ./build_proposal.sh --export-odt # Org→ODT→DOC까지 (Emacs batch)
#   ./build_proposal.sh -o /tmp/out  # 출력 디렉토리 지정
#

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MEMEX_KB_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
KIAT_OUTPUT="$MEMEX_KB_DIR/output/kiat-proposal"

MD_SOURCE="$MEMEX_KB_DIR/output/kiat-proposal/md"
ORG_OUTPUT=""

DO_SYNC=1
DO_EXPORT=0
DO_ODT=0

# Python 환경 검증 (nix develop / direnv 필요)
PYTHON="${PYTHON:-python}"
if ! command -v "$PYTHON" &>/dev/null; then
    echo "ERROR: python not found."
    echo "  NixOS: 'nix develop' 또는 'direnv allow' 후 실행하세요."
    echo "  또는: PYTHON=/path/to/python $0 $*"
    exit 1
fi

EMACS="${EMACS:-emacs}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-sync)    DO_SYNC=0; shift ;;
        --export-md)  DO_EXPORT=1; shift ;;
        --export-odt) DO_ODT=1; shift ;;
        -o|--output-dir)
            ORG_OUTPUT="$(realpath -m "$2")"
            shift 2 ;;
        --help|-h)
            echo "사용법: $0 [--no-sync] [--export-md] [--export-odt] [-o DIR]"
            echo ""
            echo "  --no-sync       MD 동기화 없이 기존 소스로 변환만"
            echo "  --export-md     GDocs 다운로드부터 시작 (export_kiat_proposal.sh)"
            echo "  --export-odt    Org→ODT→DOC 내보내기 (Emacs batch + 후처리)"
            echo "  -o, --output-dir DIR  출력 디렉토리 지정 (기본: output/proposal-org/)"
            exit 0 ;;
        *) echo "알 수 없는 인자: $1"; exit 1 ;;
    esac
done

# 출력 디렉토리 기본값
if [[ -z "$ORG_OUTPUT" ]]; then
    ORG_OUTPUT="$MEMEX_KB_DIR/output/proposal-org"
fi

# --export-odt 사전 검증 (fail fast)
if [[ $DO_ODT -eq 1 ]]; then
    if ! command -v "$EMACS" &>/dev/null; then
        echo "ERROR: emacs not found (--export-odt에 필요)."
        echo "  또는: EMACS=/path/to/emacs $0 $*"
        exit 1
    fi
fi

# 매핑: MD 파일 스템 → 챕터명
declare -A MAPPINGS=(
    ["ch1"]="06--1.-연구개발과제의-배경-및-필요성"
    ["ch2"]="08--2.-연구개발과제의-목표-및-성과지표"
    ["ch3"]="09--3.-기술개발내용-및-로드맵"
    ["ch4"]="10--6장.-연구개발-추진체계-및-위험관리"
    ["ch5"]="11--7.-연구개발성과의-활용방안-및-사업화계획"
)

echo "========================================="
echo "  Google Docs → Org 변환 파이프라인"
echo "========================================="

# Step 0: GDocs → MD (선택사항)
if [[ $DO_EXPORT -eq 1 ]]; then
    echo ""
    echo "--- Step 0: Google Docs → MD 다운로드 ---"
    if [[ -f "$MEMEX_KB_DIR/scripts/export_kiat_proposal.sh" ]]; then
        (cd "$MEMEX_KB_DIR" && bash scripts/export_kiat_proposal.sh)
    else
        echo "ERROR: $MEMEX_KB_DIR/scripts/export_kiat_proposal.sh 없음"
        exit 1
    fi
fi

# Step 1: MD 소스 확인
if [[ $DO_SYNC -eq 1 ]]; then
    echo ""
    echo "--- Step 1: MD 소스 확인 ---"

    if [[ ! -d "$KIAT_OUTPUT" ]]; then
        echo "ERROR: $KIAT_OUTPUT 없음. --export-md로 먼저 다운로드하세요."
        exit 1
    fi

    # MD 파일이 output/kiat-proposal/ 에 직접 있는 경우와 md/ 서브디렉토리에 있는 경우 모두 지원
    if [[ -d "$KIAT_OUTPUT/md" ]]; then
        MD_SOURCE="$KIAT_OUTPUT/md"
    else
        MD_SOURCE="$KIAT_OUTPUT"
    fi

    for ch in ch1 ch2 ch3 ch4 ch5; do
        md_stem="${MAPPINGS[$ch]}"
        if [[ -f "$MD_SOURCE/${md_stem}.md" ]]; then
            echo "  확인: ${md_stem}.md"
        else
            echo "  WARNING: ${md_stem}.md 없음"
        fi
    done
fi

# Step 2: MD → Org (장별)
echo ""
echo "--- Step 2: MD → Org (장별 변환) ---"
mkdir -p "$ORG_OUTPUT"

for ch in ch1 ch2 ch3 ch4 ch5; do
    md_stem="${MAPPINGS[$ch]}"
    md_file="$MD_SOURCE/${md_stem}.md"
    org_file="$ORG_OUTPUT/${ch}-content.org"

    if [[ ! -f "$md_file" ]]; then
        echo "  SKIP: ${md_stem}.md 없음"
        continue
    fi

    "$PYTHON" "$SCRIPT_DIR/md_to_org.py" "$md_file" -o "$org_file" 2>&1 | { grep -E '제목|헤딩|저장' || true; }
done

# Step 3: 통합 Org 생성
echo ""
echo "--- Step 3: 통합 Org 생성 ---"

# 검토용 (깔끔)
"$PYTHON" "$SCRIPT_DIR/merge_chapters.py" \
    --org-dir "$ORG_OUTPUT" --strip-hwpx-idx --org-tables \
    -o "$ORG_OUTPUT/제안서-전체-검토용.org"

# HWPX_IDX 포함 (파이프라인용)
"$PYTHON" "$SCRIPT_DIR/merge_chapters.py" \
    --org-dir "$ORG_OUTPUT" --org-tables \
    -o "$ORG_OUTPUT/제안서-전체.org"

# Step 3.5: Level 6→5 통합 후처리
echo ""
echo "--- Step 3.5: Level 6→5 헤딩 통합 ---"
"$PYTHON" "$SCRIPT_DIR/org_merge_levels.py" "$ORG_OUTPUT/제안서-전체-검토용.org"
"$PYTHON" "$SCRIPT_DIR/org_merge_levels.py" "$ORG_OUTPUT/제안서-전체.org"

# Step 4: 이미지 심볼릭 링크 (Org에서 이미지 프리뷰용)
if [[ -d "$MD_SOURCE/images" ]] && [[ ! -e "$ORG_OUTPUT/images" ]]; then
    ln -s "$MD_SOURCE/images" "$ORG_OUTPUT/images"
    echo "  이미지 심볼릭 링크: org-output/images → md-source/images"
fi

# Step 5-7: Org → ODT → DOC (선택사항, --export-odt)
if [[ $DO_ODT -eq 1 ]]; then
    echo ""
    echo "--- Step 5: Org → ODT (Emacs batch) ---"

    ORG_INPUT="$ORG_OUTPUT/제안서-전체.org"
    if [[ ! -f "$ORG_INPUT" ]]; then
        echo "ERROR: $ORG_INPUT 없음. Step 3까지 완료 필요."
        exit 1
    fi

    "$EMACS" --batch \
        -l "$SCRIPT_DIR/proposal-export.el" \
        -- export "$ORG_INPUT" 2>&1

    ODT_OUTPUT="${ORG_INPUT%.org}.odt"
    if [[ ! -f "$ODT_OUTPUT" ]]; then
        echo "ERROR: ODT 생성 실패"
        exit 1
    fi
    echo "  ODT 생성: $ODT_OUTPUT"

    # Step 6: ODT 후처리
    echo ""
    echo "--- Step 6: ODT 후처리 ---"
    "$PYTHON" "$SCRIPT_DIR/odt_postprocess.py" "$ODT_OUTPUT"

    # Step 7: ODT → DOC (LibreOffice, 선택)
    if command -v libreoffice &>/dev/null; then
        echo ""
        echo "--- Step 7: ODT → DOC ---"
        libreoffice --headless --convert-to doc --outdir "$ORG_OUTPUT" "$ODT_OUTPUT"
        echo "  DOC: ${ODT_OUTPUT%.odt}.doc"
    else
        echo ""
        echo "  INFO: LibreOffice 없음 → DOC 변환 생략"
    fi
fi

# 검증
echo ""
echo "========================================="
echo "  빌드 완료"
echo "========================================="
echo ""
echo "  검토용:  $ORG_OUTPUT/제안서-전체-검토용.org"
echo "  전체:    $ORG_OUTPUT/제안서-전체.org"
if [[ $DO_ODT -eq 1 ]] && [[ -f "${ORG_OUTPUT}/제안서-전체.odt" ]]; then
    echo "  ODT:     $ORG_OUTPUT/제안서-전체.odt"
fi
echo ""
echo "  이미지:  $(grep -c '\[\[file:' "$ORG_OUTPUT/제안서-전체-검토용.org" || echo 0) 개"
echo "  테이블:  $(grep -c '^|[^-]' "$ORG_OUTPUT/제안서-전체-검토용.org" || echo 0) 행"
echo "  MD잔여:  $(grep -c '!\[' "$ORG_OUTPUT/제안서-전체-검토용.org" || echo 0) 개"
echo ""
echo "  Emacs: emacsclient $ORG_OUTPUT/제안서-전체-검토용.org"

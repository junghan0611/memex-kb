#!/usr/bin/env bash
set -euo pipefail

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# memex-kb run.sh — Self-documenting CLI for humans & agents
# Usage:
#   ./run.sh              → Interactive menu
#   ./run.sh <command>    → Direct execution (agent-friendly)
#   ./run.sh help         → Show all commands
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# Project root (where this script lives)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="${PROJECT_DIR}/scripts"
CONFIG_DIR="${PROJECT_DIR}/config"

# Helper functions
info()    { echo -e "${BLUE}ℹ ${NC}$1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn()    { echo -e "${YELLOW}⚠${NC} $1"; }
error()   { echo -e "${RED}✗${NC} $1"; }
header()  { echo -e "\n${BOLD}${CYAN}$1${NC}"; }

# Run a command with logging
run_cmd() {
    local cmd="$1"
    echo ""
    info "실행: ${DIM}${cmd}${NC}"
    echo ""
    eval "$cmd"
    local status=$?
    echo ""
    if [[ $status -eq 0 ]]; then
        success "완료!"
    else
        error "실패 (exit code: $status)"
    fi
    return $status
}

# Ensure we're in project root
ensure_project_dir() {
    cd "$PROJECT_DIR"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMMANDS — 각 함수가 하나의 명령어
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ── Google Docs ──────────────────────────────────────────────────────

cmd_gdocs_export() {
    # DESC: Google Docs → Markdown 내보내기
    # USAGE: gdocs-export <DOC_ID> [ACCOUNT] [--format FMT] [--parent-tab TAB] [--depth N]
    # EXAMPLE: gdocs-export 1abc...xyz jhkim2@goqual.com
    # EXAMPLE: gdocs-export 1abc...xyz --format docx --depth 0
    local doc_id="${1:?DOC_ID가 필요합니다}"
    shift
    ensure_project_dir
    run_cmd "nix develop --command python ${SCRIPTS_DIR}/gdocs_md_processor.py export ${doc_id} $*"
}

cmd_gdocs_export_kiat() {
    # DESC: KIAT 연구개발계획서 내보내기 (D-0 세션)
    # USAGE: gdocs-export-kiat [--all] [--format FMT] [--depth N]
    # EXAMPLE: gdocs-export-kiat
    # EXAMPLE: gdocs-export-kiat --all --format docx
    ensure_project_dir
    run_cmd "${SCRIPTS_DIR}/export_kiat_proposal.sh $*"
}

cmd_gdocs_wrapper() {
    # DESC: export_gdoc.sh 래퍼 (환경변수로 옵션 지정)
    # USAGE: gdocs-wrapper <DOC_ID> [ACCOUNT]
    # ENV: OUTPUT_DIR, FORMAT, DEPTH, PARENT_TAB
    # EXAMPLE: FORMAT=docx gdocs-wrapper 1abc...xyz
    local doc_id="${1:?DOC_ID가 필요합니다}"
    shift
    ensure_project_dir
    run_cmd "${SCRIPTS_DIR}/export_gdoc.sh ${doc_id} $*"
}

# ── Threads SNS ──────────────────────────────────────────────────────

cmd_threads_export() {
    # DESC: Threads 전체 포스트 → Org-mode 내보내기
    # USAGE: threads-export [--max-posts N] [--reverse] [--download-images]
    # EXAMPLE: threads-export --download-images
    # EXAMPLE: threads-export --max-posts 5 --download-images
    ensure_project_dir
    local args="${*:---download-images}"
    run_cmd "nix develop --command python ${SCRIPTS_DIR}/threads_exporter.py ${args}"
}

cmd_threads_token_exchange() {
    # DESC: 단기 토큰 → 장기 토큰(60일) 교환
    # USAGE: threads-token-exchange <SHORT_TOKEN>
    # NOTE: Graph API Explorer에서 threads.net API로 단기 토큰 발급 후 사용
    # LINK: https://developers.facebook.com/tools/explorer/1351795096326806/
    local token="${1:?단기 토큰이 필요합니다}"
    ensure_project_dir
    run_cmd "nix develop --command python ${SCRIPTS_DIR}/refresh_threads_token.py --exchange '${token}'"
}

cmd_threads_token_test() {
    # DESC: 현재 Threads API 토큰 유효성 검사
    # USAGE: threads-token-test
    ensure_project_dir
    run_cmd "nix develop --command python ${SCRIPTS_DIR}/refresh_threads_token.py --test"
}

cmd_threads_token_refresh() {
    # DESC: 기존 장기 토큰 갱신
    # USAGE: threads-token-refresh
    ensure_project_dir
    run_cmd "nix develop --command python ${SCRIPTS_DIR}/refresh_threads_token.py"
}

# ── GitHub Stars ────────────────────────────────────────────────────

cmd_github_starred_export() {
    # DESC: GitHub starred repos → BibTeX 내보내기 (Citar 호환)
    # USAGE: github-starred-export [output.bib]
    # EXAMPLE: github-starred-export
    # EXAMPLE: github-starred-export ~/org/resources/github-starred.bib
    # NOTE: gh CLI 인증 필요 (gh auth login)
    ensure_project_dir
    run_cmd "${SCRIPTS_DIR}/gh_starred_to_bib.sh ${*:-}"
}

# ── Confluence ───────────────────────────────────────────────────────

cmd_confluence_convert() {
    # DESC: Confluence .doc(MIME HTML) → Markdown 변환
    # USAGE: confluence-convert <INPUT> [OUTPUT]
    # EXAMPLE: confluence-convert document.doc output.md
    local input="${1:?입력 파일이 필요합니다}"
    shift
    ensure_project_dir
    run_cmd "nix develop --command python ${SCRIPTS_DIR}/confluence_to_markdown.py '${input}' $*"
}

cmd_confluence_batch() {
    # DESC: Confluence 일괄 변환 (디렉토리)
    # USAGE: confluence-batch <INPUT_DIR> [OUTPUT_DIR]
    # EXAMPLE: confluence-batch ./confluence-export/ ./docs/
    local input_dir="${1:?입력 디렉토리가 필요합니다}"
    local output_dir="${2:-./docs}"
    ensure_project_dir
    run_cmd "nix develop --command python ${SCRIPTS_DIR}/confluence_to_markdown.py --batch '${input_dir}' '${output_dir}'"
}

# ── Proposal Pipeline ────────────────────────────────────────────────

cmd_proposal_build() {
    # DESC: 제안서 전체 빌드 (GDocs→MD→Org→통합→ODT)
    # USAGE: proposal-build [--no-sync] [--export-md] [--export-odt] [-o DIR]
    # EXAMPLE: proposal-build
    # EXAMPLE: proposal-build --export-md --export-odt
    ensure_project_dir
    info "실행: build_proposal.sh $*"
    "${PROJECT_DIR}/proposal-pipeline/build_proposal.sh" "$@"
}

cmd_proposal_convert() {
    # DESC: 제안서 MD→Org 변환 (장별)
    # USAGE: proposal-convert <INPUT.md> [-o OUTPUT.org]
    # EXAMPLE: proposal-convert output/kiat-proposal/06--1.-연구개발과제의-배경-및-필요성.md
    local input="${1:?입력 MD 파일이 필요합니다}"
    shift
    ensure_project_dir
    info "실행: md_to_org.py ${input}"
    nix develop --command python "${PROJECT_DIR}/proposal-pipeline/md_to_org.py" "${input}" "$@"
}

cmd_proposal_merge() {
    # DESC: 제안서 Org 통합 + L6→L5 후처리
    # USAGE: proposal-merge [--strip-hwpx-idx] [--org-tables] [-o OUTPUT.org]
    # EXAMPLE: proposal-merge --strip-hwpx-idx --org-tables
    ensure_project_dir
    local org_dir="${PROJECT_DIR}/output/proposal-org"
    local output="${org_dir}/제안서-전체.org"
    info "실행: merge_chapters.py + org_merge_levels.py"
    nix develop --command python "${PROJECT_DIR}/proposal-pipeline/merge_chapters.py" \
        --org-dir "${org_dir}" --org-tables "$@" -o "${output}"
    nix develop --command python "${PROJECT_DIR}/proposal-pipeline/org_merge_levels.py" "${output}"
}

cmd_proposal_odt_fix() {
    # DESC: ODT 후처리 (테이블 헤더 배경색 + 테두리)
    # USAGE: proposal-odt-fix <INPUT.odt> [OUTPUT.odt]
    # EXAMPLE: proposal-odt-fix output/proposal-org/제안서.odt
    local input="${1:?ODT 파일이 필요합니다}"
    shift
    ensure_project_dir
    info "실행: odt_postprocess.py ${input}"
    nix develop --command python "${PROJECT_DIR}/proposal-pipeline/odt_postprocess.py" "${input}" "$@"
}

cmd_proposal_export_odt() {
    # DESC: Org→ODT 내보내기 (Emacs batch + 후처리)
    # USAGE: proposal-export-odt [ORG_FILE]
    # EXAMPLE: proposal-export-odt output/proposal-org/제안서-전체.org
    local input="${1:-${PROJECT_DIR}/output/proposal-org/제안서-전체.org}"
    ensure_project_dir
    if [[ ! -f "${input}" ]]; then
        error "파일 없음: ${input}"
        return 1
    fi
    info "실행: emacs --batch proposal-export.el -- export ${input}"
    emacs --batch -l "${PROJECT_DIR}/proposal-pipeline/proposal-export.el" -- export "${input}"
    local odt_output="${input%.org}.odt"
    if [[ -f "${odt_output}" ]]; then
        info "ODT 후처리: ${odt_output}"
        nix develop --command python "${PROJECT_DIR}/proposal-pipeline/odt_postprocess.py" "${odt_output}"
        success "완료: ${odt_output}"
    else
        error "ODT 생성 실패"
        return 1
    fi
}

# ── Naver Blog ───────────────────────────────────────────────────────

cmd_naver_list() {
    # DESC: 네이버 블로그 전체 글 목록 수집
    # USAGE: naver-list <BLOG_ID> [--output FILE]
    # EXAMPLE: naver-list saiculture --output ./naver-saiculture/posts.json
    local blog_id="${1:?BLOG_ID가 필요합니다}"
    shift
    ensure_project_dir
    run_cmd "python3 ${SCRIPTS_DIR}/naver_blog_crawler.py list ${blog_id} $*"
}

cmd_naver_get() {
    # DESC: 네이버 블로그 단일 글 추출 (Denote org 미리보기)
    # USAGE: naver-get <BLOG_ID> <LOG_NO>
    # EXAMPLE: naver-get saiculture 224202104252
    local blog_id="${1:?BLOG_ID가 필요합니다}"
    local log_no="${2:?LOG_NO가 필요합니다}"
    ensure_project_dir
    python3 "${SCRIPTS_DIR}/naver_blog_crawler.py" get "${blog_id}" "${log_no}"
}

cmd_naver_crawl() {
    # DESC: 네이버 블로그 전체 크롤링 → Denote org + 이미지 (카테고리 폴더)
    # USAGE: naver-crawl <BLOG_ID> [--output-dir DIR] [--delay SEC] [--limit N]
    # EXAMPLE: naver-crawl saiculture
    # EXAMPLE: naver-crawl saiculture --output-dir ./naver-saiculture --limit 100
    # NOTE: 이어받기 지원. 중간에 끊어도 다시 실행하면 이어서 받음.
    local blog_id="${1:?BLOG_ID가 필요합니다}"
    shift
    ensure_project_dir
    run_cmd "python3 ${SCRIPTS_DIR}/naver_blog_crawler.py crawl ${blog_id} $*"
}

cmd_naver_verify() {
    # DESC: 크롤링 결과 정합성 검사 (누락/고아/깨진 이미지)
    # USAGE: naver-verify [--output-dir DIR]
    # EXAMPLE: naver-verify --output-dir ./naver-saiculture
    ensure_project_dir
    run_cmd "python3 ${SCRIPTS_DIR}/naver_blog_crawler.py verify $*"
}

cmd_naver_retry() {
    # DESC: 누락 이미지 재다운로드 (한글URL 인코딩, timeout 재시도)
    # USAGE: naver-retry <BLOG_ID> [--output-dir DIR] [--delay SEC]
    # EXAMPLE: naver-retry saiculture --output-dir ./naver-saiculture
    local blog_id="${1:?BLOG_ID가 필요합니다}"
    shift
    ensure_project_dir
    run_cmd "python3 ${SCRIPTS_DIR}/naver_blog_crawler.py retry ${blog_id} $*"
}

cmd_naver_fix_titles() {
    # DESC: 기존 org 파일의 제목/파일명 HTML entity 수정 (재크롤링 불필요)
    # USAGE: naver-fix-titles [--output-dir DIR]
    # EXAMPLE: naver-fix-titles --output-dir ./naver-saiculture
    ensure_project_dir
    run_cmd "python3 ${SCRIPTS_DIR}/naver_blog_crawler.py fix-titles $*"
}

cmd_naver_wordmap() {
    # DESC: 해시태그 워드맵 생성 (빈도 + 공기어)
    # USAGE: naver-wordmap [--output-dir DIR]
    # EXAMPLE: naver-wordmap --output-dir ./naver-saiculture
    ensure_project_dir
    run_cmd "python3 ${SCRIPTS_DIR}/naver_blog_crawler.py wordmap $*"
}

# ── Utility ──────────────────────────────────────────────────────────

cmd_env_check() {
    # DESC: 개발 환경 및 설정 상태 점검
    # USAGE: env-check
    ensure_project_dir
    header "환경 점검"

    echo -e "\n${BOLD}[Nix Flake]${NC}"
    if command -v nix &>/dev/null; then
        success "nix: $(nix --version 2>/dev/null | head -1)"
    else
        error "nix: 설치되지 않음"
    fi

    if [[ -f "${PROJECT_DIR}/flake.nix" ]]; then
        success "flake.nix: 존재"
    else
        error "flake.nix: 없음"
    fi

    if [[ -f "${PROJECT_DIR}/.envrc" ]]; then
        success ".envrc: 존재"
    else
        warn ".envrc: 없음 (direnv 미설정)"
    fi

    echo -e "\n${BOLD}[환경변수 (.env)]${NC}"
    if [[ -f "${CONFIG_DIR}/.env" ]]; then
        success ".env: 존재"
        # 민감 정보 제외하고 설정된 키만 표시
        local keys
        keys=$(grep -E '^[A-Z_]+=' "${CONFIG_DIR}/.env" 2>/dev/null | cut -d= -f1 | sort)
        if [[ -n "$keys" ]]; then
            echo -e "  ${DIM}설정된 키: $(echo "$keys" | tr '\n' ', ' | sed 's/,$//')${NC}"
        fi
    else
        warn ".env: 없음 (config/.env.example 참고)"
    fi

    echo -e "\n${BOLD}[Google Workspace MCP 인증]${NC}"
    local cred_dir="$HOME/.google_workspace_mcp_work/credentials"
    if [[ -d "$cred_dir" ]]; then
        local cred_files
        cred_files=$(ls "$cred_dir"/*.json 2>/dev/null | wc -l)
        if [[ "$cred_files" -gt 0 ]]; then
            success "MCP credentials: ${cred_files}개 계정"
            ls "$cred_dir"/*.json 2>/dev/null | while read -r f; do
                echo -e "  ${DIM}$(basename "$f" .json)${NC}"
            done
        else
            warn "MCP credentials: JSON 파일 없음"
        fi
    else
        warn "MCP credentials 디렉토리 없음: ${cred_dir}"
    fi

    echo -e "\n${BOLD}[GitHub CLI]${NC}"
    if command -v gh &>/dev/null; then
        success "gh: $(gh --version | head -1)"
        if gh auth status &>/dev/null 2>&1; then
            success "gh auth: 인증됨"
        else
            warn "gh auth: 미인증 (gh auth login 필요)"
        fi
    else
        error "gh: 설치되지 않음"
    fi

    echo -e "\n${BOLD}[Threads API]${NC}"
    if [[ -f "${CONFIG_DIR}/.env" ]] && grep -q "THREADS_ACCESS_TOKEN=." "${CONFIG_DIR}/.env" 2>/dev/null; then
        success "THREADS_ACCESS_TOKEN: 설정됨"
    else
        warn "THREADS_ACCESS_TOKEN: 미설정"
    fi

    echo ""
}

cmd_secret_scan() {
    # DESC: gitleaks로 시크릿 스캔 (커밋 전 필수!)
    # USAGE: secret-scan [--no-git]
    # EXAMPLE: secret-scan
    # EXAMPLE: secret-scan --no-git
    ensure_project_dir
    if [[ "${1:-}" == "--no-git" ]]; then
        run_cmd "nix develop --command gitleaks detect --no-git --source ."
    else
        run_cmd "nix develop --command gitleaks detect --source ."
    fi
}

cmd_categorize_test() {
    # DESC: 문서 자동 분류기 테스트
    # USAGE: categorize-test
    ensure_project_dir
    run_cmd "nix develop --command python ${SCRIPTS_DIR}/categorizer.py"
}

cmd_denote_test() {
    # DESC: Denote 파일명 생성기 테스트
    # USAGE: denote-test
    ensure_project_dir
    run_cmd "nix develop --command python ${SCRIPTS_DIR}/denote_namer.py"
}

cmd_md_to_gdocs_html() {
    # DESC: Markdown/Org → Google Docs 붙여넣기용 HTML 변환 (MD→Org→HTML, 최적 경로 ★추천)
    # USAGE: md-to-gdocs-html <INPUT.md> [-o OUTPUT.html] [--open]
    # EXAMPLE: md-to-gdocs-html README.md --open
    # EXAMPLE: md-to-gdocs-html ~/docs/guide.org --open
    local input="${1:?입력 파일이 필요합니다 (MD 또는 Org)}"
    shift
    ensure_project_dir
    run_cmd "python ${SCRIPTS_DIR}/md_to_gdocs_html.py ${input} $*"
}

cmd_md_to_gdocs() {
    # DESC: Markdown/Org → Google Docs 붙여넣기용 DOCX 변환 (MD→Org→ODT→DOCX, 모노스페이스 코드블록, 테이블 유지)
    # USAGE: md-to-gdocs <INPUT.md> [-o OUTPUT.docx] [--open] [--keep] [--step org|odt|docx]
    # EXAMPLE: md-to-gdocs README.md --open
    # EXAMPLE: md-to-gdocs ~/docs/guide.org --step org --keep
    local input="${1:?입력 파일이 필요합니다 (MD 또는 Org)}"
    shift
    ensure_project_dir
    run_cmd "python ${SCRIPTS_DIR}/md_to_gdocs.py ${input} $*"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMMAND REGISTRY — 명령어 이름 ↔ 함수 매핑
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 순서대로 메뉴에 표시됨. "---"는 구분선.
COMMANDS=(
    "--- Google Docs"
    "gdocs-export:cmd_gdocs_export"
    "gdocs-export-kiat:cmd_gdocs_export_kiat"
    "gdocs-wrapper:cmd_gdocs_wrapper"
    "--- Threads SNS"
    "threads-export:cmd_threads_export"
    "threads-token-exchange:cmd_threads_token_exchange"
    "threads-token-test:cmd_threads_token_test"
    "threads-token-refresh:cmd_threads_token_refresh"
    "--- GitHub Stars"
    "github-starred-export:cmd_github_starred_export"
    "--- Confluence"
    "confluence-convert:cmd_confluence_convert"
    "confluence-batch:cmd_confluence_batch"
    "--- Proposal Pipeline"
    "proposal-build:cmd_proposal_build"
    "proposal-convert:cmd_proposal_convert"
    "proposal-merge:cmd_proposal_merge"
    "proposal-odt-fix:cmd_proposal_odt_fix"
    "proposal-export-odt:cmd_proposal_export_odt"
    "--- Naver Blog"
    "naver-list:cmd_naver_list"
    "naver-get:cmd_naver_get"
    "naver-crawl:cmd_naver_crawl"
    "naver-verify:cmd_naver_verify"
    "naver-retry:cmd_naver_retry"
    "naver-wordmap:cmd_naver_wordmap"
    "--- 변환 도구"
    "md-to-gdocs:cmd_md_to_gdocs"
    "md-to-gdocs-html:cmd_md_to_gdocs_html"
    "--- Utility"
    "env-check:cmd_env_check"
    "secret-scan:cmd_secret_scan"
    "categorize-test:cmd_categorize_test"
    "denote-test:cmd_denote_test"
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTROSPECTION — 소스 파일에서 함수 주석 추출
# (declare -f는 주석을 제거하므로, 소스 파일을 직접 파싱)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCRIPT_SOURCE="${BASH_SOURCE[0]}"

# 함수의 소스 파일 주석에서 특정 태그의 첫 번째 값 추출
get_cmd_meta() {
    local func_name="$1"
    local tag="$2"
    # 함수 정의 이후의 주석 블록에서 태그 추출
    sed -n "/^${func_name}()/,/^}/p" "$SCRIPT_SOURCE" \
        | { grep -m1 "# ${tag}:" || true; } \
        | sed "s/.*# ${tag}: *//"
}

# 함수의 소스 파일 주석에서 특정 태그의 모든 값 추출
get_cmd_meta_all() {
    local func_name="$1"
    local tag="$2"
    sed -n "/^${func_name}()/,/^}/p" "$SCRIPT_SOURCE" \
        | { grep "# ${tag}:" || true; } \
        | sed "s/.*# ${tag}: *//"
}

# 함수의 모든 메타데이터 출력
show_cmd_detail() {
    local cmd_name="$1"
    local func_name="$2"

    local desc
    desc=$(get_cmd_meta "$func_name" "DESC")
    echo -e "  ${BOLD}${cmd_name}${NC}"
    echo -e "    ${desc:-설명 없음}"

    # USAGE 라인들
    while IFS= read -r line; do
        [[ -n "$line" ]] && echo -e "    ${DIM}사용: ${line}${NC}"
    done < <(get_cmd_meta_all "$func_name" "USAGE")

    # EXAMPLE 라인들
    while IFS= read -r line; do
        [[ -n "$line" ]] && echo -e "    ${GREEN}예시: ./run.sh ${line}${NC}"
    done < <(get_cmd_meta_all "$func_name" "EXAMPLE")

    # ENV / NOTE / LINK (optional tags)
    local env note link
    env=$(get_cmd_meta "$func_name" "ENV")
    note=$(get_cmd_meta "$func_name" "NOTE")
    link=$(get_cmd_meta "$func_name" "LINK")
    if [[ -n "$env" ]]; then echo -e "    ${YELLOW}환경변수: ${env}${NC}"; fi
    if [[ -n "$note" ]]; then echo -e "    ${CYAN}참고: ${note}${NC}"; fi
    if [[ -n "$link" ]]; then echo -e "    ${BLUE}링크: ${link}${NC}"; fi
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELP — 전체 명령어 목록 + 설명
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

show_help() {
    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${GREEN}  memex-kb${NC} — Universal Knowledge Base Converter"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${DIM}사용법:${NC}"
    echo -e "    ./run.sh                  ${DIM}# Interactive 메뉴${NC}"
    echo -e "    ./run.sh <command> [args] ${DIM}# 직접 실행 (에이전트용)${NC}"
    echo -e "    ./run.sh help             ${DIM}# 이 도움말${NC}"
    echo -e "    ./run.sh help <command>   ${DIM}# 명령어 상세 도움말${NC}"

    local idx=0
    for entry in "${COMMANDS[@]}"; do
        if [[ "$entry" == ---* ]]; then
            local section="${entry#--- }"
            echo ""
            echo -e "  ${YELLOW}${section}${NC}"
            continue
        fi

        idx=$((idx + 1))
        local cmd_name="${entry%%:*}"
        local func_name="${entry#*:}"
        local desc
        desc=$(get_cmd_meta "$func_name" "DESC")
        local usage
        usage=$(get_cmd_meta "$func_name" "USAGE")

        printf "    ${BOLD}%-3s${NC} %-28s %s\n" "${idx})" "${cmd_name}" "${desc:-}"
    done

    echo ""
    echo -e "  ${DIM}Nix 환경이 자동 적용됩니다 (flake.nix + direnv)${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

show_command_help() {
    local target="$1"
    for entry in "${COMMANDS[@]}"; do
        [[ "$entry" == ---* ]] && continue
        local cmd_name="${entry%%:*}"
        local func_name="${entry#*:}"
        if [[ "$cmd_name" == "$target" ]]; then
            echo ""
            show_cmd_detail "$cmd_name" "$func_name"
            echo ""
            return 0
        fi
    done
    error "알 수 없는 명령어: $target"
    echo "  ./run.sh help 로 전체 목록을 확인하세요."
    return 1
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTERACTIVE MENU — 사람용 (번호 선택)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interactive_menu() {
    while true; do
        show_help
        echo -e "    ${BOLD} 0)${NC} 종료"
        echo ""
        read -rp "  선택 (번호 또는 명령어): " choice

        # "0" or "q" → exit
        if [[ "$choice" == "0" || "$choice" == "q" ]]; then
            info "종료합니다."
            exit 0
        fi

        # 빈 입력 → 다시 메뉴
        [[ -z "$choice" ]] && continue

        # 번호 입력 → 명령어로 변환
        if [[ "$choice" =~ ^[0-9]+$ ]]; then
            local idx=0
            local found=""
            for entry in "${COMMANDS[@]}"; do
                [[ "$entry" == ---* ]] && continue
                idx=$((idx + 1))
                if [[ "$idx" -eq "$choice" ]]; then
                    found="$entry"
                    break
                fi
            done

            if [[ -z "$found" ]]; then
                error "잘못된 번호입니다: $choice"
                read -rp "  계속하려면 Enter..."
                continue
            fi

            local cmd_name="${found%%:*}"
            local func_name="${found#*:}"

            # 상세 설명 표시
            echo ""
            show_cmd_detail "$cmd_name" "$func_name"
            echo ""

            # 인자가 필요한 명령어인지 확인
            local usage
            usage=$(get_cmd_meta "$func_name" "USAGE")
            if echo "$usage" | grep -q '<'; then
                echo -e "  ${YELLOW}인자가 필요합니다.${NC}"
                read -rp "  인자 입력 (빈칸이면 취소): " args
                if [[ -z "$args" ]]; then
                    info "취소되었습니다."
                    read -rp "  계속하려면 Enter..."
                    continue
                fi
                eval "$func_name $args" || true
            else
                read -rp "  실행하시겠습니까? (Y/n): " confirm
                if [[ "${confirm:-y}" =~ ^[Nn]$ ]]; then
                    info "취소되었습니다."
                else
                    eval "$func_name" || true
                fi
            fi
        else
            # 명령어 이름 직접 입력
            dispatch_command "$choice"
        fi

        echo ""
        read -rp "  계속하려면 Enter..."
    done
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DISPATCH — 명령어 이름으로 함수 호출
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

dispatch_command() {
    local cmd="$1"
    shift 2>/dev/null || true

    for entry in "${COMMANDS[@]}"; do
        [[ "$entry" == ---* ]] && continue
        local cmd_name="${entry%%:*}"
        local func_name="${entry#*:}"
        if [[ "$cmd_name" == "$cmd" ]]; then
            "$func_name" "$@"
            return $?
        fi
    done

    error "알 수 없는 명령어: $cmd"
    echo ""
    echo "  ./run.sh help 로 전체 목록을 확인하세요."
    return 1
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENTRYPOINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

main() {
    # 인자 없음 → interactive 메뉴
    if [[ $# -eq 0 ]]; then
        interactive_menu
        return
    fi

    local cmd="$1"
    shift

    case "$cmd" in
        help|--help|-h)
            if [[ $# -gt 0 ]]; then
                show_command_help "$1"
            else
                show_help
            fi
            ;;
        *)
            dispatch_command "$cmd" "$@"
            ;;
    esac
}

main "$@"

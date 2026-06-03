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


# ── ArXiv Paper Template ─────────────────────────────────────────────

cmd_arxiv_build() {
    # DESC: Org → ACM acmart LaTeX → PDF 빌드 (ArXiv 논문 템플릿)
    # USAGE: arxiv-build [ORG_FILE]
    # EXAMPLE: arxiv-build
    # EXAMPLE: arxiv-build templates/arxiv-acm/sample.org
    # NOTE: NixOS texlive (scheme-full) 필요. templates/arxiv-acm/flake.nix 참조.
    local input="${1:-${PROJECT_DIR}/templates/arxiv-acm/sample.org}"
    ensure_project_dir
    if [[ ! -f "$input" ]]; then
        error "파일 없음: $input"
        return 1
    fi
    local build_el="${PROJECT_DIR}/templates/arxiv-acm/build.el"
    info "Org → ACM PDF: $input"
    run_cmd "nix-shell -p 'pkgs.emacs' '(pkgs.texlive.combine { inherit (pkgs.texlive) scheme-full latexmk; })' --run \"emacs -Q --batch --script ${build_el} ${input}\""
    local pdf="${input%.org}.pdf"
    if [[ -f "$pdf" ]]; then
        success "PDF 생성: $pdf ($(du -h "$pdf" | cut -f1))"
    fi
}

# ── ScanPDF→Org (스캔 PDF → org vision 전사) ────────────────────────────

cmd_scanpdf2org_render() {
    # DESC: 스캔 PDF 페이지 → PNG 렌더 (vision 전사용, OCR 아님)
    # USAGE: scanpdf2org-render <PDF> <OUT_DIR> [PAGES] [DPI]
    # EXAMPLE: scanpdf2org-render scanpdf/물질생명인간001.pdf scanpdf/work/물질생명인간/pages 1-15
    # EXAMPLE: scanpdf2org-render scanpdf/물질생명인간001.pdf scanpdf/work/물질생명인간/pages_hi 11-16 250
    # NOTE: 렌더 후 에이전트(Claude/Codex/Gemini)가 PNG를 직접 읽어 org로 옮긴다.
    #       전사 규칙은 scanpdf2org/prompts/page-to-org.md 참조.
    ensure_project_dir
    local pdf="${1:?PDF 경로 필요}"
    local out="${2:?출력 디렉토리 필요}"
    local pages="${3:-}"
    local dpi="${4:-200}"
    local args="\"${pdf}\" --out \"${out}\" --dpi ${dpi}"
    [[ -n "$pages" ]] && args="${args} --pages ${pages}"
    run_cmd "nix develop --command python ${PROJECT_DIR}/scanpdf2org/scripts/pdf_to_images.py ${args}"
}

# ── diff QA (엔진 무관) — 두 전사본 충돌점 추출 ──────────────────────
#
# marker(surya OCR) 엔진은 은퇴(2026-06-02): MinerU VLM이 속도/정확도 둘 다 우위.
# diff_review.py(stdlib)만 QA 도구로 보존 — MinerU md ↔ 기준본(vision/원본) 대조.

cmd_diff_review() {
    # DESC: 두 전사본(md/org) 충돌점만 추출. 페이지 전체 재독 없이 갈린 곳만 판정.
    # USAGE: diff-review <a.md|org> <b.md|org>
    # EXAMPLE: diff-review scanpdf/work/물질생명인간/mineru/split/본문1-4장.md scanpdf/work/물질생명인간/org/물질생명인간-epub.org
    # NOTE: 엔진 무관 stdlib. 충돌점은 페이지 이미지로 판정 → 원문 충실한 쪽 채택.
    ensure_project_dir
    local a="${1:?기준본 A 경로 필요}"
    local b="${2:?기준본 B 경로 필요}"
    run_cmd "python3 scripts/diff_review.py '${a}' '${b}'"
}

cmd_para_splits() {
    # DESC: MinerU 페이지 OCR로 쪼개진 문단(페이지경계/그림·표·수식 끼임/오분할) 후보 리스트.
    # USAGE: para-splits <book> [--category page_boundary] [--limit 0] [--json]
    # EXAMPLE: para-splits 물리학강의 --category page_boundary --limit 0
    # NOTE: 탐지·리스트 전용(본문 미변경). content_list.json + 종결부호 휴리스틱.
    #       봉합부 공백 여부는 자동화 불가(~30% 어절경계) → 사람/LLM 패스로 판정.
    ensure_project_dir
    local book="${1:?책 디렉토리명 필요 (예: 물리학강의)}"; shift || true
    local cl; cl=$(ls "scanpdf/work/${book}/mineru/"*content_list*.json 2>/dev/null | head -1)
    [ -n "${cl}" ] || { error "content_list 없음: scanpdf/work/${book}/mineru/"; return 1; }
    run_cmd "python3 scripts/detect_para_splits.py --content-list '${cl}' --corrections 'scripts/corrections/${book}.json' $*"
}

# ── MinerU (VLM, 원격 vLLM) — 충실 전사 + 수식/그림 추출 ──────────────
#
# 추론은 gpu2i RTX 5080의 vLLM이 한다(served-name: mineru). 로컬은 얇은 클라이언트.
# - 서버: nixos 담당이 gpu2i tmux로 vllm 0.11.2 서빙 (MinerU2.5-Pro-2605-1.2B).
# - thinkpad는 10G망 직접 못 닿아 SSH 터널로 붙는다(자동 보장).
# - 로컬 NixOS 우회: PYTHONPATH 제거(nix Pillow 충돌) + opencv-python-headless.
#   추론이 원격이라 로컬엔 torch/CUDA/triton 불필요(클라 venv ~480M).
# 설치: nix develop --command uv sync --directory mineru-client
#       그 뒤 opencv-python → headless 로 교체(uv pip).

MINERU_VENV="mineru-client/.venv"
MINERU_NIXLD="/run/current-system/sw/share/nix-ld/lib"
MINERU_TUNNEL_HOST="${MINERU_TUNNEL_HOST:-gpu2i}"   # ssh alias (ProxyJump 포함)
MINERU_PORT="${MINERU_PORT:-30000}"

cmd_mineru_setup() {
    # DESC: MinerU 클라이언트 설치(재현). uv sync 한 번 — opencv는 pyproject override로 headless 자동.
    # USAGE: mineru-setup
    # NOTE: 추론 원격이라 로컬 torch/CUDA/vLLM 불필요. venv ~480M.
    ensure_project_dir
    run_cmd "nix develop --command uv sync --directory mineru-client"
    info "임포트 검증..."
    if env -u PYTHONPATH LD_LIBRARY_PATH="${MINERU_NIXLD}" "${MINERU_VENV}/bin/python" -c "import cv2, magika" 2>/dev/null; then
        success "mineru 클라이언트 준비됨. 사용: ./run.sh mineru-parse <pdf>"
    else
        error "임포트 실패. LD_LIBRARY_PATH(nix-ld) 또는 opencv-headless 확인"
        return 1
    fi
}

cmd_mineru_parse() {
    # DESC: PDF/이미지 → Markdown+LaTeX+그림추출 (MinerU VLM, 원격 gpu2i 5080)
    # USAGE: mineru-parse <INPUT.pdf|DIR> [OUTPUT_DIR]
    # EXAMPLE: mineru-parse scanpdf/물질생명인간001.pdf mineru-client/out
    # ENV: MINERU_TUNNEL_HOST(기본 gpu2i) MINERU_PORT(기본 30000)
    # NOTE: 터널 자동 보장. 클러스터 내부(192.168.2.x)면 MINERU_TUNNEL_HOST 비우고 직접 URL도 가능.
    ensure_project_dir
    local input="${1:?입력 PDF/이미지/디렉토리 필요}"
    local outdir="${2:-mineru-client/out}"
    if [[ ! -x "${MINERU_VENV}/bin/mineru" ]]; then
        error "mineru 클라이언트 없음. 설치: nix develop --command uv sync --directory mineru-client (이후 opencv-headless 교체)"
        return 1
    fi
    # 터널 보장: localhost:PORT 헬스 안 되면 ssh -fN 으로 띄운다
    if ! curl -sf -m 3 "http://localhost:${MINERU_PORT}/health" >/dev/null 2>&1; then
        info "터널 띄움: localhost:${MINERU_PORT} → ${MINERU_TUNNEL_HOST}:${MINERU_PORT}"
        ssh -fN -o ExitOnForwardFailure=yes -L "${MINERU_PORT}:localhost:${MINERU_PORT}" "${MINERU_TUNNEL_HOST}" || {
            error "터널 실패. ssh ${MINERU_TUNNEL_HOST} 확인"; return 1; }
    fi
    run_cmd "env -u PYTHONPATH LD_LIBRARY_PATH='${MINERU_NIXLD}' ${MINERU_VENV}/bin/mineru -p '${input}' -o '${outdir}' -b vlm-http-client -u http://localhost:${MINERU_PORT}"
}

# ── DeepSeek-OCR (VLM, 원격 vLLM) — OCR 다엔진 비교 (이슈 #3) ──────────
#
# 추론은 gpu1i RTX 5080의 vLLM(served-name: deepseek-ocr, OpenAI 호환)이 한다.
# MinerU(gpu2i:30000)와 대칭이되, DeepSeek는 content_list.json을 안 준다 —
# grounding 모드의 label[[bbox]] 시맨틱 블록으로 구조를 부분 복원해 MinerU 호환 md를 만든다.
# 클라이언트는 scripts/deepseek_ocr_client.py (PyMuPDF + urllib, 로컬 torch 불필요).

DEEPSEEK_TUNNEL_HOST="${DEEPSEEK_TUNNEL_HOST:-gpu1i}"   # ssh alias (ProxyJump 포함)
DEEPSEEK_PORT="${DEEPSEEK_PORT:-8000}"

cmd_deepseek_parse() {
    # DESC: PDF → MinerU 호환 Markdown (DeepSeek-OCR grounding, 원격 gpu1i 5080)
    # USAGE: deepseek-parse <INPUT.pdf> [OUTPUT_DIR] [-- EXTRA_ARGS...]
    # EXAMPLE: deepseek-parse scanpdf/물리학강의001.pdf deepseek-out -- --first 489 --last 490
    # ENV: DEEPSEEK_TUNNEL_HOST(기본 gpu1i) DEEPSEEK_PORT(기본 8000)
    # NOTE: 터널 자동 보장. 산출 <OUT>/<doc>/{<doc>.md, <doc>_blocks.json}.
    ensure_project_dir
    local input="${1:?입력 PDF 필요}"; shift || true
    local outdir="deepseek-out"
    if [[ $# -gt 0 && "$1" != "--" && "$1" != --* ]]; then outdir="$1"; shift; fi
    [[ "${1:-}" == "--" ]] && shift
    # 터널 보장: localhost:PORT 모델 엔드포인트 안 되면 ssh -fN 으로 띄운다
    if ! curl -sf -m 3 "http://localhost:${DEEPSEEK_PORT}/v1/models" >/dev/null 2>&1; then
        info "터널 띄움: localhost:${DEEPSEEK_PORT} → ${DEEPSEEK_TUNNEL_HOST}:${DEEPSEEK_PORT}"
        ssh -fN -o ExitOnForwardFailure=yes -L "${DEEPSEEK_PORT}:localhost:${DEEPSEEK_PORT}" "${DEEPSEEK_TUNNEL_HOST}" || {
            error "터널 실패. ssh ${DEEPSEEK_TUNNEL_HOST} 확인"; return 1; }
    fi
    run_cmd "nix develop --command python3 scripts/deepseek_ocr_client.py '${input}' -o '${outdir}' --url 'http://localhost:${DEEPSEEK_PORT}/v1/chat/completions' $*"
}

# ── Org→EPUB (org-mode → clean EPUB 3.0) ─────────────────────────────

cmd_org2epub_build() {
    # DESC: org-mode → clean EPUB 3.0 (local ox-epub fork 직접 사용)
    # USAGE: org2epub-build <INPUT.org> [OUTPUT.epub]
    # EXAMPLE: org2epub-build scanpdf/work/물질생명인간/org/물질생명인간.org
    # ENV: OX_EPUB_REPO=~/repos/gh/ox-epub EPUBCHECK=1
    # NOTE: memex-kb 내부 후처리 스크립트 없이 ox-epub 포크가 EPUB3/headless export를 직접 처리.
    ensure_project_dir
    local org="${1:?org 파일 경로 필요}"
    local out="${2:-}"
    org="$(readlink -f "$org")"
    if [[ ! -f "$org" ]]; then
        error "파일 없음: $org"
        return 1
    fi

    local ox_repo="${OX_EPUB_REPO:-${HOME}/repos/gh/ox-epub}"
    local ox_el="${ox_repo}/ox-epub.el"
    if [[ ! -f "$ox_el" ]]; then
        error "ox-epub.el 없음: $ox_el"
        return 1
    fi

    local produced="${org%.org}.epub"
    local final="$produced"
    if [[ -n "$out" ]]; then
        final="$(readlink -m "$out")"
        mkdir -p "$(dirname "$final")"
    fi

    info "ox-epub export: $org"
    ORG_FILE="$org" emacs --batch -l "$ox_el" --eval \
        '(with-current-buffer (find-file-noselect (getenv "ORG_FILE"))
           (let ((default-directory (file-name-directory (getenv "ORG_FILE"))))
             (org-epub-export-to-epub)))'

    if [[ -n "$out" && "$produced" != "$final" ]]; then
        cp -f "$produced" "$final"
    fi

    if [[ "${EPUBCHECK:-1}" == "1" ]]; then
        info "epubcheck: $final"
        nix run nixpkgs#epubcheck -- "$final"
    else
        info "epubcheck skipped (EPUBCHECK=1 로 활성화)"
    fi

    success "EPUB 생성: $final"
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
    "--- ArXiv Paper"
    "arxiv-build:cmd_arxiv_build"
    "--- ScanPDF→Org"
    "scanpdf2org-render:cmd_scanpdf2org_render"
    "diff-review:cmd_diff_review"
    "para-splits:cmd_para_splits"
    "mineru-setup:cmd_mineru_setup"
    "mineru-parse:cmd_mineru_parse"
    "deepseek-parse:cmd_deepseek_parse"
    "--- Org→EPUB"
    "org2epub-build:cmd_org2epub_build"
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

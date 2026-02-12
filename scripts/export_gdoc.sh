#!/usr/bin/env bash
# ============================================================================
# export_gdoc.sh - Google Docs → 탭별 Markdown 완전 자동 변환
# ============================================================================
#
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 목적 (WHY)                                                        │
# │                                                                     │
# │ "연구개발계획서"를 Google Docs에서 공동 작성 중이다.                │
# │ 이 문서는 지속적으로 업데이트되며, 업데이트될 때마다                │
# │ 최신 내용을 로컬 Markdown으로 가져와야 한다.                       │
# │                                                                     │
# │ 가져온 MD는 다음 용도로 사용된다:                                  │
# │   1. HWPX 변환 결과물과 비교/검증 (원본 대조)                      │
# │   2. Org-mode/Denote 지식베이스에 통합                             │
# │   3. RAG 파이프라인 입력 (임베딩용)                                │
# │                                                                     │
# │ 핵심 요구사항:                                                     │
# │   - 사용자 개입 없는 완전 자동화 (브라우저 접근 불필요)            │
# │   - 탭별 독립 MD 파일 (탭 = 문서 섹션)                            │
# │   - 이미지는 별도 PNG 파일 (base64 인라인 제거)                    │
# │   - 불필요한 이스케이프 문자 자동 정리 (\~, \<, \. 등)            │
# └─────────────────────────────────────────────────────────────────────┘
#
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 작동 원리 (HOW)                                                    │
# │                                                                     │
# │ 1. MCP google-workspace의 credentials 파일에서 refresh_token 획득  │
# │    경로: ~/.google_workspace_mcp_work/credentials/{email}.json     │
# │                                                                     │
# │ 2. refresh_token → access_token 갱신 (OAuth2 token endpoint)       │
# │                                                                     │
# │ 3. Google Docs REST API로 탭 목록 조회                             │
# │    URL: https://docs.googleapis.com/v1/documents/{id}              │
# │         ?fields=tabs(tabProperties)                                 │
# │                                                                     │
# │ 4. 각 탭을 Markdown으로 내보내기                                   │
# │    URL: https://docs.google.com/document/d/{id}/export             │
# │         ?format=markdown&tab={tabId}                                │
# │    (공식 문서에 없지만 실제 동작하는 URL 패턴)                     │
# │                                                                     │
# │ 5. 각 탭 MD에서 base64 이미지 추출 → PNG 파일로 저장               │
# │    이미지 파일명: tab{NN}-image{N}.png (탭별 prefix로 충돌 방지)   │
# │                                                                     │
# │ 6. 불필요한 이스케이프 문자 정리 (13종)                            │
# │    \~ → ~, \< → <, \. → ., \- → -, \* → * 등                      │
# └─────────────────────────────────────────────────────────────────────┘
#
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 인증 전제조건                                                      │
# │                                                                     │
# │ MCP google-workspace 서버가 한 번이라도 인증된 상태여야 함.        │
# │ 즉, Claude Code에서 MCP google-workspace 도구를 사용한 적이 있고,  │
# │ ~/.google_workspace_mcp_work/credentials/ 에 JSON 파일이 존재해야. │
# │                                                                     │
# │ 이 스크립트는 MCP 서버 자체를 실행하지 않음.                       │
# │ MCP가 저장해둔 refresh_token만 재활용하여 직접 API를 호출함.       │
# │                                                                     │
# │ refresh_token은 revoke하지 않는 한 만료되지 않으므로               │
# │ 한 번 인증하면 이후로는 영구적으로 사용 가능.                      │
# └─────────────────────────────────────────────────────────────────────┘
#
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 삽질 기록 (폐기된 접근법들)                                        │
# │                                                                     │
# │ 1. MCP get_drive_file_download_url                                 │
# │    → PDF/DOCX만 지원. HTML/MD 불가. 26MB 초과 시 DOCX도 불가.     │
# │                                                                     │
# │ 2. MCP get_doc_content                                             │
# │    → plain text 전용. 이미지/서식/표 모두 없음.                    │
# │    → 탭 구조 발견에만 유용 (--- TAB: xxx --- 마커)                 │
# │                                                                     │
# │ 3. Pandoc DOCX 변환                                                │
# │    → 이미지가 BMP로 변환됨 (품질 열화)                             │
# │    → 26MB 이상 문서 DOCX 내보내기 API 거부                        │
# │    → 복잡한 표 깨짐                                                │
# │                                                                     │
# │ 4. Apps Script (UrlFetchApp.fetch)                                 │
# │    → MCP OAuth에 script.external_request 스코프 없음               │
# │    → MCP 서버가 uvx로 실행되므로 로컬 소스 수정 불가               │
# │    → DocumentApp.openById는 동작하나 HTML/MD export 불가           │
# │                                                                     │
# │ 5. 브라우저 수동 내보내기                                          │
# │    → 탭마다 File → Download → Markdown 반복 필요 (자동화 불가)     │
# │    → base64 이미지 인라인 (1.5MB/탭)                               │
# │                                                                     │
# │ ★ 최종 해결: Python에서 Google Docs export URL 직접 호출           │
# │   MCP credentials의 refresh_token만 재활용. 완전 자동화 달성.      │
# └─────────────────────────────────────────────────────────────────────┘
#
# ============================================================================
# 사용법
# ============================================================================
#
#   # 기본 사용 (첫 번째 Google 계정 자동 선택)
#   ./scripts/export_gdoc.sh DOC_ID
#
#   # 특정 계정 지정
#   ./scripts/export_gdoc.sh DOC_ID jhkim2@goqual.com
#
#   # 출력 디렉토리 지정
#   OUTPUT_DIR=/tmp/my-output ./scripts/export_gdoc.sh DOC_ID
#
# 예시:
#   # 연구개발계획서 (5탭, 5이미지)
#   ./scripts/export_gdoc.sh 1SEJWIbO-kA6Kzriun_iQ5QZuxlAzJzTYg6TtJcI1EGM
#
#   # 사본 (3탭, 이미지 없음)
#   ./scripts/export_gdoc.sh 11mCb1i_3urjJ1P7I75ECWV_sF4N5g1ayySgorUtQ3kQ
#
# 출력 구조:
#   output/
#   ├── 00--탭이름.md          # 탭 0번 (이스케이프 정리됨)
#   ├── 01--탭이름.md          # 탭 1번
#   ├── 02--탭이름.md          # ...
#   └── images/
#       ├── tab00-image1.png   # 탭 0번의 이미지 1
#       ├── tab00-image2.png   # 탭 0번의 이미지 2
#       └── tab01-image1.png   # 탭 1번의 이미지 1
#
# ============================================================================
# 관련 문서
# ============================================================================
#
# - BACKENDS.md          : 백엔드별 연동 가이드 (Google Docs 섹션)
# - AGENTS.md            : 에이전트 지침 (Nix 환경, br 이슈 트래커)
# - scripts/gdocs_md_processor.py : 핵심 Python 스크립트 (export 명령)
#
# beads 이슈:
# - bd-wnq: closed (export 명령으로 완전 자동화)
# - bd-222: closed (Apps Script 폐기, Python 직접 API로 해결)
# - bd-207: closed (13종 이스케이프 패턴 정리)
#
# ============================================================================

set -euo pipefail

# ── 색상 정의 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── 인수 처리 ──
DOC_ID="${1:-}"
ACCOUNT="${2:-}"
OUTPUT_DIR="${OUTPUT_DIR:-./output}"
DEPTH="${DEPTH:--1}"  # 기본값: -1 (전체 하위 탭 포함)
FORMAT="${FORMAT:-md}"  # 기본값: md (md, docx, pdf, html, txt)
PARENT_TAB="${PARENT_TAB:-}"  # 상위 탭 필터 (부분 매칭)

if [ -z "$DOC_ID" ]; then
    echo -e "${RED}사용법: $0 DOC_ID [ACCOUNT]${NC}"
    echo ""
    echo "  DOC_ID   : Google Docs 문서 ID (URL에서 /d/ 뒤의 문자열)"
    echo "  ACCOUNT  : Google 계정 (예: jhkim2@goqual.com) [선택]"
    echo ""
    echo "환경변수:"
    echo "  OUTPUT_DIR  : 출력 디렉토리 (기본: ./output)"
    echo "  DEPTH       : 탭 깊이 제한 (0=상위만, 1=1단계, -1=전체, 기본: -1)"
    echo "  FORMAT      : 출력 포맷 (md, docx, pdf, html, txt, 기본: md)"
    echo "  PARENT_TAB  : 상위 탭 필터 (부분 매칭, 해당 탭 + 하위 탭만)"
    echo ""
    echo "예시:"
    echo "  $0 1SEJWIbO-kA6Kzriun_iQ5QZuxlAzJzTYg6TtJcI1EGM"
    echo "  $0 1SEJWIbO-kA6Kzriun_iQ5QZuxlAzJzTYg6TtJcI1EGM jhkim2@goqual.com"
    echo "  DEPTH=0 $0 DOC_ID  # 상위 탭만"
    echo "  FORMAT=docx $0 DOC_ID  # DOCX 내보내기"
    echo "  PARENT_TAB='D-0 스프린트' $0 DOC_ID  # 특정 탭 하위만"
    exit 1
fi

# ── 실행 ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROCESSOR="${SCRIPT_DIR}/gdocs_md_processor.py"

if [ ! -f "$PROCESSOR" ]; then
    echo -e "${RED}오류: ${PROCESSOR} 를 찾을 수 없습니다.${NC}"
    exit 1
fi

echo -e "${GREEN}Google Docs → ${FORMAT^^} 변환 시작${NC}"
echo "  문서 ID: ${DOC_ID}"
echo "  포맷: ${FORMAT}"
echo "  출력: ${OUTPUT_DIR}/"
if [ -n "$PARENT_TAB" ]; then
    echo "  상위 탭: ${PARENT_TAB}"
fi
echo ""

# nix develop 환경에서 실행 (의존성 보장)
EXTRA_ARGS=""
if [ -n "$ACCOUNT" ]; then
    EXTRA_ARGS="${EXTRA_ARGS} --account ${ACCOUNT}"
fi
if [ -n "$PARENT_TAB" ]; then
    EXTRA_ARGS="${EXTRA_ARGS} --parent-tab ${PARENT_TAB}"
fi

nix develop --command python "$PROCESSOR" export \
    "$DOC_ID" \
    --output-dir "$OUTPUT_DIR" \
    --depth "$DEPTH" \
    --format "$FORMAT" \
    ${EXTRA_ARGS}

echo ""
echo -e "${GREEN}변환 완료!${NC}"
echo "  결과: ${OUTPUT_DIR}/"
ls -la "$OUTPUT_DIR/"
if [ -d "${OUTPUT_DIR}/images" ]; then
    echo ""
    echo "  이미지:"
    ls -la "${OUTPUT_DIR}/images/"
fi

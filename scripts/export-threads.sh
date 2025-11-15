#!/usr/bin/env bash
# Threads Aphorism Exporter - 간편 실행 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 헬프 메시지
show_help() {
    cat << EOF
${BLUE}Threads Aphorism Exporter${NC}

사용법:
  $0 [옵션]

옵션:
  -h, --help              이 도움말 표시
  -t, --test N            테스트 모드 (N개 포스트만 내보내기)
  -r, --reverse           오래된 순서로 정렬
  --no-images             이미지 다운로드 생략
  -f, --full              전체 내보내기 (기본값, 이미지 포함)
  --nix                   Nix shell 환경 사용 (기본: Python 직접 실행)

예제:
  $0                      # 전체 내보내기 (이미지 포함)
  $0 -t 10                # 테스트: 최근 10개만
  $0 -t 10 -r             # 테스트: 오래된 10개만
  $0 --no-images          # 이미지 없이 전체 내보내기

출력:
  - docs/threads-aphorisms.org (Org-mode datetree 구조)
  - docs/images/threads/       (첨부 이미지, --no-images 시 생략)

환경:
  - 기본: Python 직접 실행 (빠름)
  - --nix: Nix shell 환경 사용 (재현성)
  - config/.env 필요 (THREADS_ACCESS_TOKEN 등)
EOF
}

# 옵션 파싱
MAX_POSTS=""
REVERSE=""
DOWNLOAD_IMAGES="--download-images"
USE_NIX=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -t|--test)
            MAX_POSTS="--max-posts $2"
            shift 2
            ;;
        -r|--reverse)
            REVERSE="--reverse"
            shift
            ;;
        --no-images)
            DOWNLOAD_IMAGES=""
            shift
            ;;
        -f|--full)
            # 기본값이므로 아무것도 안함
            shift
            ;;
        --nix)
            USE_NIX=true
            shift
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# 환경 파일 체크
if [ ! -f "config/.env" ]; then
    echo -e "${RED}Error: config/.env not found!${NC}"
    echo -e "${YELLOW}Run 'nix-shell --run \"python scripts/get_threads_token.py\"' first${NC}"
    echo -e "${YELLOW}Or copy config/.env.example to config/.env and add your tokens${NC}"
    exit 1
fi

# 실행 명령어 구성
CMD="python scripts/threads_exporter.py $MAX_POSTS $REVERSE $DOWNLOAD_IMAGES"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}🧠 Threads Aphorism Exporter${NC}"
echo -e "${BLUE}============================================================${NC}"
if [ "$USE_NIX" = true ]; then
    echo -e "${GREEN}실행 방식:${NC} Nix shell"
else
    echo -e "${GREEN}실행 방식:${NC} Python 직접 실행"
fi
echo -e "${GREEN}실행 명령어:${NC} $CMD"
echo -e "${BLUE}============================================================${NC}"
echo

# 실행
if [ "$USE_NIX" = true ]; then
    nix-shell --run "$CMD"
else
    $CMD
fi

# 결과 확인
if [ $? -eq 0 ]; then
    echo
    echo -e "${GREEN}✅ 내보내기 완료!${NC}"
    echo -e "${BLUE}출력 파일:${NC}"
    echo -e "  - docs/threads-aphorisms.org"

    if [ -n "$DOWNLOAD_IMAGES" ]; then
        IMG_COUNT=$(find docs/images/threads -type f 2>/dev/null | wc -l)
        echo -e "  - docs/images/threads/ (${IMG_COUNT}개 이미지)"
    fi

    # 포스트 수 표시
    POST_COUNT=$(grep -c "^:POST_ID:" docs/threads-aphorisms.org 2>/dev/null || echo "0")
    echo -e "${BLUE}총 포스트:${NC} ${POST_COUNT}개"
else
    echo
    echo -e "${RED}❌ 내보내기 실패${NC}"
    exit 1
fi

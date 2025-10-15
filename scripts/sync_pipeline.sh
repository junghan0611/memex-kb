#!/bin/bash

# Google Drive 문서 동기화 파이프라인
# 이 스크립트는 Google Drive 폴더의 문서들을 Markdown으로 변환하고 Git에 푸시합니다.

set -e  # 에러 발생시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 스크립트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 설정 파일 로드
if [ -f "$PROJECT_ROOT/config/.env" ]; then
    export $(cat "$PROJECT_ROOT/config/.env" | grep -v '^#' | xargs)
fi

# 로그 파일
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/sync_$(date +%Y%m%d).log"
ERROR_LOG="$LOG_DIR/errors.log"

# 함수: 로그 출력
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$ERROR_LOG"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# 함수: Python 환경 확인
check_python_env() {
    log "Python 환경 확인 중..."

    # 가상환경 활성화
    if [ -d "$PROJECT_ROOT/venv" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
        log "가상환경 활성화 완료"
    else
        warning "가상환경이 없습니다. 시스템 Python을 사용합니다."
    fi

    # 필요한 모듈 확인
    python3 -c "import google.auth" 2>/dev/null || {
        error "Google API 라이브러리가 설치되지 않았습니다."
        error "pip install -r requirements.txt를 실행하세요."
        exit 1
    }
}

# 함수: Google Drive에서 문서 목록 가져오기
fetch_document_list() {
    log "Google Drive에서 문서 목록을 가져오는 중..."

    # Python 스크립트로 문서 목록 가져오기
    python3 << EOF
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# 인증
creds = service_account.Credentials.from_service_account_file(
    os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'config/credentials.json'),
    scopes=['https://www.googleapis.com/auth/drive.readonly']
)

service = build('drive', 'v3', credentials=creds)

# 폴더 ID
folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
if not folder_id:
    print("ERROR: GOOGLE_DRIVE_FOLDER_ID가 설정되지 않았습니다.")
    exit(1)

# 문서 목록 가져오기
results = service.files().list(
    q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document'",
    fields="files(id, name, modifiedTime)",
    pageSize=int(os.getenv('MAX_DOCS_PER_RUN', 50))
).execute()

documents = results.get('files', [])

# JSON으로 저장
with open('$PROJECT_ROOT/logs/documents_list.json', 'w') as f:
    json.dump(documents, f, indent=2)

print(f"Found {len(documents)} documents")
EOF

    if [ $? -eq 0 ]; then
        DOC_COUNT=$(python3 -c "import json; print(len(json.load(open('$PROJECT_ROOT/logs/documents_list.json'))))")
        success "$DOC_COUNT개의 문서를 찾았습니다."
    else
        error "문서 목록을 가져오는데 실패했습니다."
        exit 1
    fi
}

# 함수: 문서 변환
convert_documents() {
    log "문서 변환 시작..."

    # 문서 목록 읽기
    python3 << EOF
import json
import sys
import os
sys.path.insert(0, '$SCRIPT_DIR')

from gdocs_to_markdown import GoogleDocsToMarkdown

# 변환기 초기화
converter = GoogleDocsToMarkdown()

# 문서 목록 로드
with open('$PROJECT_ROOT/logs/documents_list.json', 'r') as f:
    documents = json.load(f)

# 통계
stats = {
    'total': len(documents),
    'success': 0,
    'failed': 0,
    'needs_review': 0
}

# 각 문서 변환
for doc in documents:
    doc_id = doc['id']
    doc_name = doc['name']

    print(f"변환 중: {doc_name}")

    try:
        result = converter.process_document(doc_id, output_dir='$PROJECT_ROOT/docs')

        if result['success']:
            stats['success'] += 1
            if result['needs_review']:
                stats['needs_review'] += 1
                print(f"  ⚠️  검토 필요: {doc_name}")
        else:
            stats['failed'] += 1
            print(f"  ❌ 실패: {doc_name}")
    except Exception as e:
        stats['failed'] += 1
        print(f"  ❌ 오류: {doc_name} - {str(e)}")

# 통계 저장
with open('$PROJECT_ROOT/logs/stats.json', 'w') as f:
    json.dump(stats, f, indent=2)

print(f"\n변환 완료: 성공 {stats['success']}/{stats['total']}, 실패 {stats['failed']}, 검토 필요 {stats['needs_review']}")
EOF

    if [ $? -eq 0 ]; then
        success "문서 변환 완료"
    else
        error "문서 변환 중 오류 발생"
    fi
}

# 함수: Git 커밋 및 푸시
git_sync() {
    log "Git 동기화 시작..."

    cd "$PROJECT_ROOT"

    # 변경사항 확인
    if [ -z "$(git status --porcelain docs/)" ]; then
        log "변경사항이 없습니다."
        return
    fi

    # 변경된 파일 추가
    git add docs/

    # 커밋 메시지 생성
    COMMIT_MSG="자동 동기화: $(date '+%Y-%m-%d %H:%M')"

    # 통계 정보 추가
    if [ -f "$PROJECT_ROOT/logs/stats.json" ]; then
        STATS=$(python3 -c "
import json
with open('$PROJECT_ROOT/logs/stats.json', 'r') as f:
    stats = json.load(f)
    print(f\"문서 {stats['success']}개 동기화, {stats['needs_review']}개 검토 필요\")
")
        COMMIT_MSG="$COMMIT_MSG - $STATS"
    fi

    # 커밋
    git commit -m "$COMMIT_MSG"

    # 푸시 (활성화된 경우)
    if [ "$ENABLE_AUTO_COMMIT" = "true" ]; then
        if [ -n "$GIT_REMOTE_URL" ]; then
            git remote set-url origin "$GIT_REMOTE_URL" 2>/dev/null || git remote add origin "$GIT_REMOTE_URL"
            git push origin "${GIT_BRANCH:-main}"
            success "Git 푸시 완료"
        else
            warning "Git remote URL이 설정되지 않았습니다. 로컬 커밋만 수행됩니다."
        fi
    else
        log "자동 커밋이 비활성화되어 있습니다."
    fi
}

# 함수: 검토 필요 문서 리포트
generate_review_report() {
    log "검토 필요 문서 리포트 생성 중..."

    python3 << EOF
import os
import json
from pathlib import Path

docs_dir = Path('$PROJECT_ROOT/docs/_uncategorized')
if not docs_dir.exists():
    print("미분류 문서가 없습니다.")
    exit(0)

uncategorized_files = list(docs_dir.glob('*.md'))

if uncategorized_files:
    print("\n=== 검토 필요 문서 ===")
    for file in uncategorized_files:
        print(f"  - {file.name}")

    print(f"\n총 {len(uncategorized_files)}개의 문서가 수동 분류를 기다리고 있습니다.")
    print("docs/_uncategorized/ 디렉토리를 확인하세요.")
EOF
}

# 함수: 정리 작업
cleanup() {
    log "정리 작업 수행 중..."

    # 오래된 로그 파일 삭제 (30일 이상)
    find "$LOG_DIR" -name "*.log" -mtime +30 -delete

    success "정리 작업 완료"
}

# 메인 실행
main() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Google Drive 문서 동기화 파이프라인${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    log "동기화 시작..."

    # 단계별 실행
    check_python_env
    fetch_document_list
    convert_documents
    git_sync
    generate_review_report
    cleanup

    echo ""
    success "✅ 모든 작업이 완료되었습니다!"

    # 통계 출력
    if [ -f "$PROJECT_ROOT/logs/stats.json" ]; then
        echo ""
        echo "📊 동기화 통계:"
        python3 -c "
import json
with open('$PROJECT_ROOT/logs/stats.json', 'r') as f:
    stats = json.load(f)
    print(f'  • 전체 문서: {stats[\"total\"]}개')
    print(f'  • 성공: {stats[\"success\"]}개')
    print(f'  • 실패: {stats[\"failed\"]}개')
    print(f'  • 검토 필요: {stats[\"needs_review\"]}개')
"
    fi

    echo ""
    log "다음 실행은 ${SYNC_INTERVAL_MINUTES:-15}분 후입니다."
}

# 트랩 설정 (에러 발생시)
trap 'error "스크립트가 예기치 않게 종료되었습니다."' ERR

# 실행
main "$@"
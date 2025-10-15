#!/usr/bin/env python3
"""
Google Drive shortcut을 따라가서 실제 문서 찾기
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv('config/.env')

def resolve_shortcuts():
    """Shortcut을 해결하여 실제 문서 정보 가져오기"""

    # 인증
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'config/credentials.json')
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

    print(f"📁 폴더 ID: {folder_id}")
    print("-" * 60)

    try:
        # Service Account 인증
        creds = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )

        # Drive 서비스 빌드
        service = build('drive', 'v3', credentials=creds)

        # Shortcut 파일들 가져오기
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.shortcut'",
            fields="files(id, name, shortcutDetails)",
            pageSize=100
        ).execute()

        shortcuts = results.get('files', [])

        if not shortcuts:
            print("❌ Shortcut을 찾을 수 없습니다.")
            return

        print(f"✅ {len(shortcuts)}개의 shortcut을 찾았습니다:\n")

        documents = []

        for shortcut in shortcuts:
            print(f"🔗 Shortcut: {shortcut['name']}")

            # Shortcut 상세 정보
            shortcut_details = shortcut.get('shortcutDetails', {})
            target_id = shortcut_details.get('targetId')
            target_mime = shortcut_details.get('targetMimeType', 'Unknown')

            print(f"   Target ID: {target_id}")
            print(f"   Target Type: {target_mime}")

            if target_id:
                try:
                    # 실제 문서 정보 가져오기
                    target_file = service.files().get(
                        fileId=target_id,
                        fields="id,name,mimeType,modifiedTime,lastModifyingUser,webViewLink"
                    ).execute()

                    print(f"   ✅ 실제 문서: {target_file['name']}")
                    print(f"   문서 ID: {target_file['id']}")
                    print(f"   URL: {target_file.get('webViewLink', 'N/A')}")
                    print(f"   수정일: {target_file.get('modifiedTime', 'Unknown')}")
                    print()

                    # Google Docs 문서인 경우 저장
                    if target_file['mimeType'] == 'application/vnd.google-apps.document':
                        documents.append(target_file)

                except HttpError as e:
                    print(f"   ❌ 대상 파일에 접근할 수 없습니다: {e}")
                    print()

        print("-" * 60)
        print(f"\n📄 변환 가능한 Google Docs 문서: {len(documents)}개")

        # 문서 ID 리스트 출력
        if documents:
            print("\n다음 명령어로 변환 테스트:")
            for doc in documents:
                print(f"python scripts/gdocs_to_markdown_v2.py {doc['id']}  # {doc['name']}")

        return documents

    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    resolve_shortcuts()
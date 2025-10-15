#!/usr/bin/env python3
"""
Google Drive 폴더의 문서 목록 확인
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

def list_documents():
    """Google Drive 폴더의 문서 목록 출력"""

    # 인증
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'config/credentials.json')
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

    print(f"📁 폴더 ID: {folder_id}")
    print(f"🔑 인증 파일: {credentials_path}")
    print("-" * 60)

    try:
        # Service Account 인증
        creds = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )

        # Drive 서비스 빌드
        service = build('drive', 'v3', credentials=creds)

        # 문서 목록 가져오기
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document'",
            fields="files(id, name, modifiedTime, lastModifyingUser)",
            pageSize=100
        ).execute()

        documents = results.get('files', [])

        if not documents:
            print("❌ 문서를 찾을 수 없습니다.")
            print("   폴더가 비어있거나 권한이 없을 수 있습니다.")
            return

        print(f"✅ {len(documents)}개의 문서를 찾았습니다:\n")

        for i, doc in enumerate(documents, 1):
            print(f"{i}. {doc['name']}")
            print(f"   ID: {doc['id']}")
            print(f"   수정일: {doc.get('modifiedTime', 'Unknown')}")
            print(f"   수정자: {doc.get('lastModifyingUser', {}).get('emailAddress', 'Unknown')}")
            print()

        return documents

    except FileNotFoundError as e:
        print(f"❌ 인증 파일을 찾을 수 없습니다: {credentials_path}")
        print("   Service Account JSON 파일을 config/ 디렉토리에 넣어주세요.")
    except HttpError as error:
        print(f"❌ API 오류: {error}")
        if '403' in str(error):
            print("   Service Account에 폴더 접근 권한이 없습니다.")
            print("   Google Drive 폴더를 Service Account 이메일과 공유하세요.")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_documents()
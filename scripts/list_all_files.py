#!/usr/bin/env python3
"""
Google Drive 폴더의 모든 파일 확인 (문서 타입 제한 없이)
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

def list_all_files():
    """Google Drive 폴더의 모든 파일 출력"""

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

        # 모든 파일 목록 가져오기 (타입 제한 없이)
        results = service.files().list(
            q=f"'{folder_id}' in parents",
            fields="files(id, name, mimeType, modifiedTime, lastModifyingUser)",
            pageSize=100
        ).execute()

        files = results.get('files', [])

        if not files:
            print("❌ 파일을 찾을 수 없습니다.")
            print("\n디버깅 정보:")
            print(f"API 응답: {results}")

            # 폴더 자체 정보 확인
            try:
                folder_info = service.files().get(fileId=folder_id, fields="name,id,mimeType,owners").execute()
                print(f"\n폴더 정보:")
                print(f"  이름: {folder_info.get('name')}")
                print(f"  타입: {folder_info.get('mimeType')}")
                print(f"  소유자: {folder_info.get('owners', [])}")
            except:
                print("폴더 정보를 가져올 수 없습니다.")

            return

        print(f"✅ {len(files)}개의 파일을 찾았습니다:\n")

        # MIME 타입별로 분류
        docs = []
        others = []

        for file in files:
            if file['mimeType'] == 'application/vnd.google-apps.document':
                docs.append(file)
            else:
                others.append(file)

        if docs:
            print("📄 Google Docs 문서:")
            for i, doc in enumerate(docs, 1):
                print(f"{i}. {doc['name']}")
                print(f"   ID: {doc['id']}")
                print(f"   수정일: {doc.get('modifiedTime', 'Unknown')}")
                print()

        if others:
            print("\n📁 기타 파일:")
            for file in others:
                print(f"- {file['name']}")
                print(f"  타입: {file['mimeType']}")
                print(f"  ID: {file['id']}")
                print()

        return files

    except HttpError as error:
        print(f"❌ API 오류: {error}")
        if '404' in str(error):
            print("   폴더를 찾을 수 없습니다. 폴더 ID를 확인하세요.")
        elif '403' in str(error):
            print("   권한이 없습니다. 폴더 공유 설정을 확인하세요.")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_all_files()
#!/usr/bin/env python3
"""
포스트 데이터 구조 확인용 디버그 스크립트
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from adapters.threads import ThreadsAdapter

# 환경변수 로드
env_path = Path(__file__).parent.parent / 'config' / '.env'
load_dotenv(env_path)

access_token = os.getenv('THREADS_ACCESS_TOKEN')
adapter = ThreadsAdapter(access_token)

# 인증
user_id = adapter.authenticate()
print(f"✅ 인증 성공: {user_id}\n")

# 포스트 1개 조회
print("📚 포스트 목록 조회 (최근 5개)...")
posts = adapter.list_documents(limit=5, max_posts=5)

print(f"\n총 {len(posts)}개 포스트\n")

for i, post in enumerate(posts, 1):
    print(f"{'='*60}")
    print(f"포스트 #{i}")
    print(f"{'='*60}")
    print(f"ID: {post.get('id')}")
    print(f"Media Type: {post.get('media_type')}")
    print(f"Media URL: {post.get('media_url')}")
    print(f"Children (list_documents): {post.get('children')}")
    print()

    # fetch_document로 다시 조회
    print(f"🔍 fetch_document로 재조회...")
    post_detail = adapter.fetch_document(post.get('id'), include_replies=True)
    print(f"Media Type: {post_detail.get('media_type')}")
    print(f"Media URL: {post_detail.get('media_url')}")
    print(f"Children (fetch_document): {post_detail.get('children')}")
    print(f"Replies: {len(post_detail.get('replies', []))}개")
    print()

    # 이미지 다운로드 시도
    if post_detail.get('media_type') in ['IMAGE', 'CAROUSEL_ALBUM']:
        print(f"🖼️  이미지 포스트 발견!")
        print(f"전체 데이터:")
        print(json.dumps(post_detail, indent=2, ensure_ascii=False))
        break
    print()

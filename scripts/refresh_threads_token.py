#!/usr/bin/env python3
"""
Threads API Token Refresh Script

Threads API 토큰 갱신 및 새 토큰 발급 스크립트
- 장기 토큰 갱신 (refresh)
- 단기 토큰 → 장기 토큰 교환 (exchange)
- 만료된 토큰 재발급 (full OAuth flow)

=== 토큰 발급 방법 (2026-01-21 검증됨) ===

1. Graph API Explorer에서 단기 토큰 발급:
   - https://developers.facebook.com/tools/explorer/1351795096326806/
   - 상단 드롭다운에서 API를 "threads.net"으로 변경 (중요!)
   - "Generate Access Token" 클릭
   - 단기 토큰 복사

2. 장기 토큰으로 교환:
   python refresh_threads_token.py --exchange "단기토큰"

3. 또는 기존 장기 토큰 갱신 (만료 전):
   python refresh_threads_token.py

※ User Token Generator는 테스터 계정 문제로 작동 안 함
※ Graph API Explorer + threads.net API 조합이 핵심!
"""

import os
import sys
import webbrowser
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import requests
from dotenv import load_dotenv, set_key

# 환경변수 로드
ENV_PATH = Path(__file__).parent.parent / 'config' / '.env'
load_dotenv(ENV_PATH)

# Threads API 설정
THREADS_API_BASE = "https://graph.threads.net"
THREADS_OAUTH_URL = "https://threads.net/oauth/authorize"

# 장기 토큰 기본 수명 (60일). API가 expires_in을 안 주면 이 값으로 만료일을 기록한다.
DEFAULT_TOKEN_TTL = 60 * 86400

# 환경변수
APP_ID = os.getenv('THREADS_APP_ID')
APP_SECRET = os.getenv('THREADS_APP_SECRET')
REDIRECT_URI = os.getenv('THREADS_REDIRECT_URI', 'http://localhost:8888/callback')
CURRENT_TOKEN = os.getenv('THREADS_ACCESS_TOKEN')


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """OAuth 콜백 핸들러"""

    authorization_code = None

    def do_GET(self):
        """GET 요청 처리"""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if 'code' in params:
            OAuthCallbackHandler.authorization_code = params['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(b"""
            <html>
            <head><title>Threads OAuth Success</title></head>
            <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                <h1>Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
            </body>
            </html>
            """)
        else:
            error = params.get('error', ['Unknown error'])[0]
            self.send_response(400)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"""
            <html>
            <head><title>Threads OAuth Error</title></head>
            <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                <h1>Authorization Failed</h1>
                <p>Error: {error}</p>
            </body>
            </html>
            """.encode())

    def log_message(self, format, *args):
        """로그 억제"""
        pass


def refresh_long_lived_token(token: str) -> dict:
    """
    장기 토큰 갱신

    Args:
        token: 현재 장기 토큰

    Returns:
        새 토큰 정보 {'access_token': ..., 'expires_in': ...}
    """
    print("🔄 장기 토큰 갱신 중...")

    response = requests.get(
        f"{THREADS_API_BASE}/refresh_access_token",
        params={
            'grant_type': 'th_refresh_token',
            'access_token': token
        },
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 토큰 갱신 성공! (만료: {data.get('expires_in', 0) // 86400}일 후)")
        return data
    else:
        error = response.json().get('error', {})
        raise Exception(f"토큰 갱신 실패: {error.get('message', response.text)}")


def exchange_code_for_token(code: str) -> dict:
    """
    Authorization code를 단기 토큰으로 교환

    Args:
        code: Authorization code

    Returns:
        단기 토큰 정보
    """
    print("🔄 Authorization code → 단기 토큰 교환 중...")

    response = requests.post(
        f"{THREADS_API_BASE}/oauth/access_token",
        data={
            'client_id': APP_ID,
            'client_secret': APP_SECRET,
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'code': code
        },
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 단기 토큰 획득! (User ID: {data.get('user_id')})")
        return data
    else:
        raise Exception(f"토큰 교환 실패: {response.text}")


def exchange_for_long_lived_token(short_token: str) -> dict:
    """
    단기 토큰을 장기 토큰으로 교환

    Args:
        short_token: 단기 토큰

    Returns:
        장기 토큰 정보
    """
    print("🔄 단기 토큰 → 장기 토큰 교환 중...")

    response = requests.get(
        f"{THREADS_API_BASE}/access_token",
        params={
            'grant_type': 'th_exchange_token',
            'client_secret': APP_SECRET,
            'access_token': short_token
        },
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()
        expires_days = data.get('expires_in', 0) // 86400
        print(f"✅ 장기 토큰 획득! (만료: {expires_days}일 후)")
        return data
    else:
        raise Exception(f"장기 토큰 교환 실패: {response.text}")


def run_oauth_flow() -> dict:
    """
    전체 OAuth 플로우 실행

    Returns:
        장기 토큰 정보 {'access_token': ..., 'expires_in': ...}
    """
    if not APP_ID or not APP_SECRET:
        print("❌ THREADS_APP_ID와 THREADS_APP_SECRET이 설정되지 않았습니다.")
        print("\nconfig/.env에 다음을 추가하세요:")
        print("  THREADS_APP_ID=your_app_id")
        print("  THREADS_APP_SECRET=your_app_secret")
        print("  THREADS_REDIRECT_URI=http://localhost:8888/callback")
        sys.exit(1)

    # Authorization URL 생성
    auth_params = {
        'client_id': APP_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': 'threads_basic,threads_content_publish',
        'response_type': 'code'
    }
    auth_url = f"{THREADS_OAUTH_URL}?{urllib.parse.urlencode(auth_params)}"

    print("\n" + "=" * 60)
    print("🔐 Threads OAuth 인증")
    print("=" * 60)
    print("\n브라우저에서 다음 URL을 열어 인증하세요:")
    print(f"\n{auth_url}\n")

    # 로컬 서버 시작 (콜백 수신용)
    parsed_uri = urllib.parse.urlparse(REDIRECT_URI)
    port = parsed_uri.port or 8888

    server = HTTPServer(('localhost', port), OAuthCallbackHandler)
    server.timeout = 300  # 5분 타임아웃

    # 브라우저 자동 열기
    print("🌐 브라우저를 여는 중...")
    webbrowser.open(auth_url)

    print(f"⏳ 인증 대기 중... (포트 {port}에서 콜백 대기)")
    print("   (Ctrl+C로 취소)\n")

    # 콜백 대기
    try:
        while OAuthCallbackHandler.authorization_code is None:
            server.handle_request()
    except KeyboardInterrupt:
        print("\n⚠️  사용자가 취소했습니다.")
        sys.exit(1)

    code = OAuthCallbackHandler.authorization_code
    print(f"\n✅ Authorization code 수신 완료!")

    # 토큰 교환
    short_token_data = exchange_code_for_token(code)
    short_token = short_token_data['access_token']

    # 장기 토큰으로 교환
    long_token_data = exchange_for_long_lived_token(short_token)

    return long_token_data


def save_token(token: str, expires_in: int = None):
    """
    토큰을 .env 파일에 저장

    Args:
        token: 저장할 토큰
        expires_in: 만료까지 남은 초. 주어지면 THREADS_TOKEN_EXPIRES(YYYY-MM-DD)를
                    함께 갱신한다. 없으면 장기 토큰 기본값(60일)으로 계산한다.
    """
    set_key(str(ENV_PATH), 'THREADS_ACCESS_TOKEN', token)

    seconds = expires_in if expires_in else DEFAULT_TOKEN_TTL
    expires_date = (datetime.now() + timedelta(seconds=seconds)).strftime('%Y-%m-%d')
    set_key(str(ENV_PATH), 'THREADS_TOKEN_EXPIRES', expires_date)
    set_key(str(ENV_PATH), 'THREADS_TOKEN_REFRESHED', datetime.now().strftime('%Y-%m-%d'))

    print(f"\n💾 토큰이 {ENV_PATH}에 저장되었습니다.")
    print(f"📅 만료 예정일: {expires_date} ({seconds // 86400}일 후)")
    print("   ※ 구글 캘린더 반복 알림을 이 날짜 기준으로 맞춰두면 된다.")


def days_until_expiry() -> int:
    """
    THREADS_TOKEN_EXPIRES 기준 남은 일수

    Returns:
        남은 일수. 기록이 없거나 형식이 깨졌으면 None
    """
    raw = os.getenv('THREADS_TOKEN_EXPIRES')
    if not raw:
        return None

    try:
        expires = datetime.strptime(raw.strip(), '%Y-%m-%d')
    except ValueError:
        return None

    return (expires.date() - datetime.now().date()).days


def print_expiry_status():
    """만료 기록이 있으면 남은 일수를 출력"""
    expires = os.getenv('THREADS_TOKEN_EXPIRES', '').strip()
    remaining = days_until_expiry()

    if remaining is None:
        if expires:
            print(f"⚠️  만료일 형식 오류: THREADS_TOKEN_EXPIRES='{expires}' (YYYY-MM-DD 필요)")
        else:
            print("ℹ️  만료일 기록 없음 (THREADS_TOKEN_EXPIRES) — 한 번 갱신하면 기록된다.")
        return

    if remaining < 0:
        print(f"❌ 만료일 경과: {expires} ({-remaining}일 지남)")
    elif remaining <= 7:
        print(f"🚨 만료 임박: {expires} ({remaining}일 남음) — 지금 갱신하라")
    elif remaining <= 14:
        print(f"⚠️  만료 임박: {expires} ({remaining}일 남음)")
    else:
        print(f"📅 만료 예정: {expires} ({remaining}일 남음)")


def test_token(token: str) -> bool:
    """
    토큰 유효성 테스트

    Args:
        token: 테스트할 토큰

    Returns:
        유효 여부
    """
    print("\n🔍 토큰 유효성 테스트 중...")

    response = requests.get(
        f"{THREADS_API_BASE}/v1.0/me",
        params={
            'fields': 'id,username',
            'access_token': token
        },
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 토큰 유효! (User: @{data.get('username')}, ID: {data.get('id')})")
        return True
    else:
        error = response.json().get('error', {})
        print(f"❌ 토큰 무효: {error.get('message', response.text)}")
        return False


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Threads API 토큰 갱신 스크립트',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
=== 토큰 발급 방법 (권장) ===

1. Graph API Explorer에서 단기 토큰 발급:
   https://developers.facebook.com/tools/explorer/1351795096326806/
   → 상단 드롭다운에서 API를 "threads.net"으로 변경 (중요!)
   → "Generate Access Token" 클릭
   → 단기 토큰 복사

2. 장기 토큰으로 교환:
   python refresh_threads_token.py --exchange "복사한_단기토큰"

3. 기존 장기 토큰 갱신 (만료 전, 자동):
   python refresh_threads_token.py

=== 예제 ===

  # 단기 토큰 → 장기 토큰 교환 (60일 유효) ★ 가장 많이 사용
  python refresh_threads_token.py --exchange "THAA..."

  # 현재 토큰 갱신 시도 (유효한 장기 토큰이 있을 때)
  python refresh_threads_token.py

  # 토큰 유효성 테스트만
  python refresh_threads_token.py --test

  # 강제로 새 토큰 발급 (OAuth 플로우, 잘 안됨)
  python refresh_threads_token.py --new

=== 환경변수 (config/.env) ===

  THREADS_APP_ID            필수 - Threads App ID
  THREADS_APP_SECRET        필수 - Threads App Secret
  THREADS_ACCESS_TOKEN      현재 토큰 (자동 업데이트)
  THREADS_TOKEN_EXPIRES     만료 예정일 YYYY-MM-DD (자동 기록, --test에서 남은 일수 출력)
  THREADS_TOKEN_REFRESHED   마지막 갱신일 YYYY-MM-DD (자동 기록)

※ User Token Generator는 테스터 계정 문제로 작동 안 함
※ Graph API Explorer + threads.net API 조합이 핵심!
"""
    )

    parser.add_argument(
        '--exchange', '-e',
        metavar='SHORT_TOKEN',
        help='단기 토큰을 장기 토큰(60일)으로 교환'
    )

    parser.add_argument(
        '--new', '-n',
        action='store_true',
        help='강제로 새 토큰 발급 (OAuth 플로우, 권장하지 않음)'
    )

    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='현재 토큰 유효성 + 만료까지 남은 일수만 확인'
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🧵 Threads API Token Manager")
    print("=" * 60)

    # 테스트 모드
    if args.test:
        if not CURRENT_TOKEN:
            print("❌ THREADS_ACCESS_TOKEN이 설정되지 않았습니다.")
            sys.exit(1)

        valid = test_token(CURRENT_TOKEN)
        print_expiry_status()
        sys.exit(0 if valid else 1)

    # 단기 토큰 → 장기 토큰 교환 모드 (★ 권장)
    if args.exchange:
        print("\n📋 단기 토큰 → 장기 토큰 교환 모드")
        print("=" * 60)

        if not APP_SECRET:
            print("❌ THREADS_APP_SECRET이 설정되지 않았습니다.")
            print("config/.env에 THREADS_APP_SECRET을 추가하세요.")
            sys.exit(1)

        try:
            result = exchange_for_long_lived_token(args.exchange)
            save_token(result['access_token'], result.get('expires_in'))
            test_token(result['access_token'])
            print("\n🎉 완료!")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ 교환 실패: {e}")
            print("\n💡 팁: Graph API Explorer에서 threads.net API로 변경 후 토큰 발급했는지 확인하세요.")
            print("   https://developers.facebook.com/tools/explorer/1351795096326806/")
            sys.exit(1)

    # 새 토큰 발급 모드
    if args.new:
        print("\n📋 새 토큰 발급 모드")
        result = run_oauth_flow()
        save_token(result['access_token'], result.get('expires_in'))
        test_token(result['access_token'])
        print("\n🎉 완료!")
        sys.exit(0)

    # 기본 모드: 갱신 시도 → 실패 시 새 발급
    if CURRENT_TOKEN:
        print("\n📋 기존 토큰 갱신 시도...")

        # 먼저 토큰 테스트
        if test_token(CURRENT_TOKEN):
            print_expiry_status()
            # 토큰 유효 → 갱신 시도
            try:
                result = refresh_long_lived_token(CURRENT_TOKEN)
                save_token(result['access_token'], result.get('expires_in'))
                print("\n🎉 토큰 갱신 완료!")
                sys.exit(0)
            except Exception as e:
                print(f"\n⚠️  토큰 갱신 실패: {e}")
                print("새 토큰을 발급합니다...")
        else:
            print("\n⚠️  토큰이 만료되었습니다. 새 토큰을 발급합니다...")
    else:
        print("\n📋 토큰이 없습니다. 새 토큰을 발급합니다...")

    # OAuth 플로우로 새 토큰 발급
    result = run_oauth_flow()
    save_token(result['access_token'], result.get('expires_in'))
    test_token(result['access_token'])
    print("\n🎉 완료!")


if __name__ == "__main__":
    main()

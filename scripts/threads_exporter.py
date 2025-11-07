#!/usr/bin/env python3
"""
Threads Aphorism Exporter

Threads SNS (@junghanacs)의 모든 아포리즘을 단일 Org 파일로 내보내기
"""

import os
import sys
import re
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from collections import defaultdict

from dotenv import load_dotenv

# 로컬 모듈
sys.path.insert(0, str(Path(__file__).parent))
from adapters.threads import ThreadsAdapter


# 환경변수 로드
env_path = Path(__file__).parent.parent / 'config' / '.env'
load_dotenv(env_path)


# 로깅 설정
def setup_logging(log_level: str = 'INFO'):
    """로깅 설정"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/threads_exporter.log')
        ]
    )


logger = logging.getLogger(__name__)


class ThreadsOrgExporter:
    """Threads 포스트를 단일 Org 파일로 내보내는 클래스"""

    def __init__(
        self,
        access_token: str,
        user_id: str = None,
        output_file: str = 'docs/threads-aphorisms.org',
        attachments_dir: str = 'docs/attachments/threads',
        download_images: bool = False
    ):
        """
        초기화

        Args:
            access_token: Threads API Access Token
            user_id: Threads User ID (선택)
            output_file: 출력 Org 파일 경로
            attachments_dir: 이미지 첨부파일 디렉토리
            download_images: 이미지 다운로드 여부
        """
        self.adapter = ThreadsAdapter(access_token, user_id)
        self.output_file = Path(output_file)
        self.attachments_dir = Path(attachments_dir)
        self.download_images = download_images

        # 디렉토리 생성
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        if self.download_images:
            self.attachments_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"ThreadsOrgExporter 초기화 완료")
        logger.info(f"  출력 파일: {self.output_file}")
        logger.info(f"  첨부파일 디렉토리: {self.attachments_dir}")
        logger.info(f"  이미지 다운로드: {self.download_images}")

    def export_all_posts(
        self,
        max_posts: int = None,
        reverse: bool = False
    ) -> int:
        """
        전체 포스트를 Org 파일로 내보내기

        Args:
            max_posts: 최대 포스트 수 (None이면 전체)
            reverse: True이면 오래된 순, False이면 최신순

        Returns:
            내보낸 포스트 수
        """
        try:
            logger.info("=" * 60)
            logger.info("🚀 Threads Aphorism Export 시작")
            logger.info("=" * 60)

            # 인증
            user_id = self.adapter.authenticate()

            # 전체 포스트 목록 조회
            logger.info("\n📚 포스트 목록 조회 중...")
            posts = self.adapter.list_documents(
                limit=100,
                max_posts=max_posts
            )

            if not posts:
                logger.warning("⚠️  포스트가 없습니다.")
                return 0

            logger.info(f"✅ 총 {len(posts)}개 포스트 조회 완료\n")

            # 시간순 정렬 (기본: 최신순)
            logger.info("📊 포스트 정렬 중...")
            posts_sorted = sorted(
                posts,
                key=lambda p: p.get('timestamp', ''),
                reverse=not reverse  # reverse=False면 최신순
            )

            # Org 파일 생성
            logger.info(f"📝 Org 파일 생성 중: {self.output_file}")
            self._write_org_file(posts_sorted)

            logger.info("\n" + "=" * 60)
            logger.info(f"🎉 내보내기 완료! {len(posts)}개 포스트")
            logger.info(f"📄 파일 위치: {self.output_file.absolute()}")
            logger.info("=" * 60)

            return len(posts)

        except Exception as e:
            logger.error(f"❌ 내보내기 실패: {e}", exc_info=True)
            raise

    def _extract_topic(self, text: str) -> str:
        """
        포스트에서 주제 추출

        Args:
            text: 포스트 본문

        Returns:
            주제 문자열
        """
        if not text:
            return "(미분류)"

        # 1. 해시태그 우선
        hashtags = re.findall(r'#(\w+)', text)
        if hashtags:
            return hashtags[0]

        # 2. 첫 줄 (20자 이내)
        first_line = text.split('\n')[0].strip()
        if first_line and len(first_line) <= 20:
            return first_line

        # 3. 미분류
        return "(미분류)"

    def _group_by_topic(self, posts: List[Dict]) -> Dict[str, List[Dict]]:
        """
        포스트를 주제별로 그룹화

        Args:
            posts: 포스트 목록

        Returns:
            주제별 포스트 딕셔너리
        """
        groups = defaultdict(list)
        for post in posts:
            topic = self._extract_topic(post.get('text', ''))
            groups[topic].append(post)
        return dict(groups)

    def _write_org_file(self, posts: List[Dict]):
        """
        Org 파일 작성 (주제별 그룹화)

        Args:
            posts: 정렬된 포스트 목록
        """
        # 현재 시각
        now = datetime.now().strftime('[%Y-%m-%d %a %H:%M]')

        # 프론트매터
        username = self.adapter._username or "junghanacs"
        frontmatter = f"""#+title:      Threads Aphorisms (@{username})
#+date:       {now}
#+filetags:   :threads:aphorism:assholism:sns:
#+identifier: {datetime.now().strftime('%Y%m%dT%H%M%S')}
#+threads_user: @{username}
#+threads_profile: https://www.threads.net/@{username}
#+last_sync: {now}
#+post_count: {len(posts)}

* 서론 :META:

이 문서는 Threads SNS에 작성한 아포리즘 모음입니다.

#+begin_quote
추천 알고리즘은 나를 작은 세상에 가둔다.
나는 떠오르는 키워드에 집중하여 직접 쓴다.
AI에게 요청하지 않고, 디지털가든과 연결한다.

외치는 글을 디지털가든에 "어쏠리즘"으로 담으면,
하나로 연결될 것이다.
#+end_quote

- 프로필: [[https://www.threads.net/@{username}][@{username}]]
- 총 포스트: {len(posts)}개
- 마지막 동기화: {now}

"""

        # 주제별 그룹화
        logger.info("📂 주제별 그룹화 중...")
        topic_groups = self._group_by_topic(posts)
        logger.info(f"✅ {len(topic_groups)}개 주제로 분류됨")

        # Org 파일 작성
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(frontmatter)

            # 주제별로 섹션 생성
            total_count = 0
            for topic in sorted(topic_groups.keys()):
                topic_posts = topic_groups[topic]
                f.write(f"\n* 주제: {topic}\n")
                f.write(f":PROPERTIES:\n")
                f.write(f":POST_COUNT: {len(topic_posts)}\n")
                f.write(f":END:\n\n")

                # 주제 내 포스트는 시간순 정렬 (최신순)
                sorted_posts = sorted(
                    topic_posts,
                    key=lambda p: p.get('timestamp', ''),
                    reverse=True
                )

                for post in sorted_posts:
                    total_count += 1
                    logger.info(f"  [{total_count}/{len(posts)}] 변환 중... (주제: {topic}, ID: {post.get('id')})")

                    # Org 형식 변환 (레벨 2)
                    org_entry = self.adapter.convert_to_format(post, output_format='org')
                    f.write(org_entry)

                    # 이미지 섹션 (레벨 3)
                    if self.download_images:
                        images = self.adapter.download_all_images(
                            post,
                            str(self.attachments_dir)
                        )
                        if images:
                            f.write("\n*** 이미지\n\n")
                            for img_path in images:
                                f.write(f"- [[file:{img_path}]]\n")

                    # 댓글 섹션 (레벨 3)
                    replies = post.get('replies', [])
                    if replies:
                        f.write("\n*** 댓글\n")
                        for reply in replies:
                            reply_timestamp = reply.get('timestamp', '')
                            try:
                                reply_dt = datetime.fromisoformat(reply_timestamp.replace('Z', '+00:00'))
                                reply_time = reply_dt.strftime('[%Y-%m-%d %a %H:%M]')
                            except:
                                reply_time = reply_timestamp

                            reply_username = reply.get('username', 'unknown')
                            reply_text = reply.get('text', '')

                            f.write(f"\n**** @{reply_username} ({reply_time})\n\n")
                            f.write(f"{reply_text}\n")

                    f.write('\n')

        logger.info(f"✅ Org 파일 작성 완료: {self.output_file}")

    def _download_post_images(self, post: Dict):
        """
        포스트 이미지 다운로드

        Args:
            post: 포스트 데이터
        """
        media_urls = post.get('media_url')
        if not media_urls:
            return

        post_id = post.get('id')
        timestamp = post.get('timestamp', '')

        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            date_prefix = dt.strftime('%Y%m%d_%H%M%S')
        except:
            date_prefix = post_id

        # 단일 URL 또는 리스트 처리
        urls = media_urls if isinstance(media_urls, list) else [media_urls]

        for i, url in enumerate(urls, 1):
            # 파일 확장자 추출
            ext = Path(url.split('?')[0]).suffix or '.jpg'
            filename = f"{date_prefix}_{i}{ext}"
            output_path = self.attachments_dir / filename

            # 다운로드
            self.adapter.download_attachment(url, str(output_path))


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='Threads Aphorism Exporter - Threads 포스트를 Org 파일로 내보내기',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 전체 포스트 내보내기
  python threads_exporter.py

  # 최대 50개만 내보내기
  python threads_exporter.py --max-posts 50

  # 이미지 포함 내보내기
  python threads_exporter.py --download-images

  # 오래된 순으로 정렬
  python threads_exporter.py --reverse

환경변수 (.env):
  THREADS_ACCESS_TOKEN       필수 - Threads API Access Token
  THREADS_USER_ID            선택 - Threads User ID
  THREADS_OUTPUT_FILE        선택 - 출력 파일 경로 (기본: docs/threads-aphorisms.org)
  THREADS_ATTACHMENTS_DIR    선택 - 첨부파일 디렉토리 (기본: docs/attachments/threads)
  LOG_LEVEL                  선택 - 로그 레벨 (기본: INFO)
"""
    )

    parser.add_argument(
        '--max-posts',
        type=int,
        default=None,
        help='최대 포스트 수 (기본: 전체)'
    )

    parser.add_argument(
        '--reverse',
        action='store_true',
        help='오래된 순으로 정렬 (기본: 최신순)'
    )

    parser.add_argument(
        '--download-images',
        action='store_true',
        help='이미지 다운로드'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='출력 파일 경로'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        default=None,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='로그 레벨'
    )

    args = parser.parse_args()

    # 로깅 설정
    log_level = args.log_level or os.getenv('LOG_LEVEL', 'INFO')
    
    # logs 디렉토리 생성
    Path('logs').mkdir(exist_ok=True)
    setup_logging(log_level)

    logger.info("=" * 60)
    logger.info("🧠 Threads Aphorism Exporter")
    logger.info("=" * 60)

    # 환경변수 확인
    access_token = os.getenv('THREADS_ACCESS_TOKEN')
    if not access_token:
        logger.error("❌ THREADS_ACCESS_TOKEN 환경변수가 설정되지 않았습니다.")
        logger.error("\n다음 단계를 수행하세요:")
        logger.error("1. config/.env 파일 생성")
        logger.error("2. THREADS_ACCESS_TOKEN=your_token 추가")
        logger.error("\n참고: config/.env.threads.example")
        sys.exit(1)

    # 설정 값
    user_id = os.getenv('THREADS_USER_ID')
    output_file = args.output or os.getenv('THREADS_OUTPUT_FILE', 'docs/threads-aphorisms.org')
    attachments_dir = os.getenv('THREADS_ATTACHMENTS_DIR', 'docs/attachments/threads')
    download_images = args.download_images or os.getenv('THREADS_DOWNLOAD_IMAGES', 'false').lower() == 'true'

    # Exporter 생성 및 실행
    try:
        exporter = ThreadsOrgExporter(
            access_token=access_token,
            user_id=user_id,
            output_file=output_file,
            attachments_dir=attachments_dir,
            download_images=download_images
        )

        post_count = exporter.export_all_posts(
            max_posts=args.max_posts,
            reverse=args.reverse
        )

        logger.info(f"\n✅ 성공: {post_count}개 포스트 내보내기 완료")
        sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("\n⚠️  사용자가 중단했습니다.")
        sys.exit(130)

    except Exception as e:
        logger.error(f"\n❌ 오류 발생: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

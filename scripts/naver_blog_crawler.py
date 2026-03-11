#!/usr/bin/env python3
"""
naver_blog_crawler.py — 네이버 블로그 전체 크롤러

네이버 블로그의 모든 글을 마크다운/org 형식으로 추출한다.
범용 도구: 블로그 ID만 바꾸면 어떤 네이버 블로그든 사용 가능.

Usage:
    # 글 목록 수집
    python3 naver_blog_crawler.py list saiculture

    # 글 목록 수집 + JSON 저장
    python3 naver_blog_crawler.py list saiculture --output posts.json

    # 전체 크롤링 (글 목록 → 본문 추출 → 마크다운 저장)
    python3 naver_blog_crawler.py crawl saiculture --output-dir ./output

    # 특정 글만 추출
    python3 naver_blog_crawler.py get saiculture 224202104252

    # 해시태그 워드맵 추출
    python3 naver_blog_crawler.py wordmap saiculture --output-dir ./output

Features:
    - PostTitleListAsync API로 전체 글 ID 수집 (30개/페이지)
    - 모바일 URL에서 se-text-paragraph 파싱 (JS 렌더링 불필요)
    - 해시태그(#태그) 자동 추출
    - rate limiting (예의 바르게)
    - 이어받기 지원 (이미 받은 파일 스킵)
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path


# ── API: 글 목록 ──────────────────────────────────────────────

def fetch_post_list(blog_id: str, page: int = 1, count: int = 30) -> list[dict]:
    """PostTitleListAsync API로 글 목록 한 페이지 가져오기."""
    url = (
        f"https://blog.naver.com/PostTitleListAsync.naver"
        f"?blogId={blog_id}&currentPage={page}"
        f"&categoryNo=0&countPerPage={count}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")

    # 네이버 JSON에 invalid escape가 있어서 regex로 파싱
    pairs = re.findall(r'"logNo":"(\d+)","title":"([^"]+)"', raw)
    category_pairs = re.findall(r'"logNo":"(\d+)"[^}]*"categoryNo":"(\d+)"', raw)
    cat_map = dict(category_pairs)

    total_m = re.search(r'"totalCount":"?(\d+)', raw)
    total = int(total_m.group(1)) if total_m else 0

    results = []
    for log_no, title_encoded in pairs:
        title = urllib.parse.unquote_plus(title_encoded)
        title = title.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
        results.append({
            "log_no": log_no,
            "title": title,
            "category_no": cat_map.get(log_no, "0"),
        })

    return results, total


def fetch_all_posts(blog_id: str, delay: float = 0.5) -> list[dict]:
    """전체 글 목록 수집."""
    all_posts = []
    page = 1

    first_page, total = fetch_post_list(blog_id, page=1)
    all_posts.extend(first_page)
    total_pages = (total + 29) // 30
    print(f"총 {total}편, {total_pages} 페이지", file=sys.stderr)

    for page in range(2, total_pages + 1):
        time.sleep(delay)
        posts, _ = fetch_post_list(blog_id, page=page)
        if not posts:
            break
        all_posts.append(posts)
        # flatten
        if isinstance(posts, list) and posts:
            all_posts = all_posts[:-1]
            all_posts.extend(posts)
        if page % 10 == 0:
            print(f"  {page}/{total_pages} ({len(all_posts)}편)", file=sys.stderr)

    print(f"수집 완료: {len(all_posts)}편", file=sys.stderr)
    return all_posts


# ── 본문 추출 ──────────────────────────────────────────────

def extract_post(blog_id: str, log_no: str) -> dict:
    """모바일 URL에서 본문 추출."""
    url = f"https://m.blog.naver.com/{blog_id}/{log_no}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")

    # 제목
    title_m = re.search(r"<title>([^:<]+)", html)
    title = title_m.group(1).strip() if title_m else ""

    # 날짜
    date_m = re.search(r'"publishDate":"(\d{4}-\d{2}-\d{2})', html)
    if not date_m:
        date_m = re.search(r'"addDate":"(\d{4}\.\s*\d+\.\s*\d+)', html)
    date = date_m.group(1).replace(".", "-").replace(" ", "") if date_m else ""

    # 본문 (se-text-paragraph — 스마트에디터 3)
    paragraphs = re.findall(
        r'class="se-text-paragraph[^"]*"[^>]*>(.*?)</p>', html, re.DOTALL
    )
    text_parts = []
    for p in paragraphs:
        text = re.sub(r"<[^>]+>", "", p).strip()
        text = text.replace("&lt;", "<").replace("&gt;", ">")
        text = text.replace("&amp;", "&").replace("&quot;", '"')
        text = text.replace("\u200b", "")  # zero-width space
        if text:
            text_parts.append(text)

    # 구버전 에디터 폴백 (se-text-paragraph 없는 경우)
    if not text_parts:
        old_body = re.findall(
            r'class="__se_component_area"[^>]*>(.*?)</div>', html, re.DOTALL
        )
        for block in old_body:
            text = re.sub(r"<[^>]+>", "", block).strip()
            text = text.replace("&nbsp;", " ").replace("\u200b", "")
            if text:
                text_parts.append(text)

    # 해시태그 추출
    hashtags = set()
    for part in text_parts:
        tags = re.findall(r"#(\S+)", part)
        hashtags.update(tags)

    body = "\n\n".join(text_parts)

    return {
        "log_no": log_no,
        "title": title,
        "date": date,
        "url": url,
        "body": body,
        "chars": len(body),
        "hashtags": sorted(hashtags),
    }


# ── 출력 포맷 ──────────────────────────────────────────────

def to_markdown(post: dict) -> str:
    """포스트를 마크다운으로 변환."""
    lines = [
        f"# {post['title']}",
        "",
        f"- 날짜: {post['date']}",
        f"- 출처: {post['url']}",
    ]
    if post["hashtags"]:
        lines.append(f"- 태그: {', '.join(post['hashtags'])}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(post["body"])
    return "\n".join(lines)


def to_org(post: dict, blog_id: str) -> str:
    """포스트를 org-mode 형식으로 변환."""
    date = post["date"] or "unknown"
    tags = ":".join(post["hashtags"][:5]) if post["hashtags"] else ""
    tag_str = f":{tags}:" if tags else ""

    lines = [
        f"#+title:      {post['title']}",
        f"#+date:       [{date}]",
        f"#+filetags:   :naverblog:{blog_id}:{tag_str}",
        f"#+source:     {post['url']}",
        "",
        post["body"],
    ]
    return "\n".join(lines)


# ── 워드맵 ──────────────────────────────────────────────

def build_wordmap(posts_dir: Path) -> dict:
    """크롤링된 마크다운 파일에서 해시태그 워드맵 생성."""
    tag_freq = {}
    tag_cooccur = {}  # 같은 글에 함께 나온 태그 쌍

    for f in sorted(posts_dir.glob("*.md")):
        text = f.read_text()
        tags_m = re.search(r"^- 태그: (.+)$", text, re.MULTILINE)
        if not tags_m:
            continue
        tags = [t.strip() for t in tags_m.group(1).split(",")]
        for t in tags:
            tag_freq[t] = tag_freq.get(t, 0) + 1
        # co-occurrence
        for i, t1 in enumerate(tags):
            for t2 in tags[i + 1 :]:
                pair = tuple(sorted([t1, t2]))
                tag_cooccur[pair] = tag_cooccur.get(pair, 0) + 1

    return {
        "total_tags": len(tag_freq),
        "frequency": dict(sorted(tag_freq.items(), key=lambda x: -x[1])),
        "cooccurrence_top50": {
            f"{k[0]} + {k[1]}": v
            for k, v in sorted(tag_cooccur.items(), key=lambda x: -x[1])[:50]
        },
    }


# ── CLI ──────────────────────────────────────────────

def cmd_list(blog_id: str, output: str = None):
    """글 목록 수집."""
    posts = fetch_all_posts(blog_id)
    if output:
        Path(output).write_text(json.dumps(posts, ensure_ascii=False, indent=2))
        print(f"저장: {output} ({len(posts)}편)", file=sys.stderr)
    else:
        for p in posts:
            print(f"{p['log_no']}\t{p['title']}")


def cmd_get(blog_id: str, log_no: str, fmt: str = "markdown"):
    """특정 글 추출."""
    post = extract_post(blog_id, log_no)
    if fmt == "org":
        print(to_org(post, blog_id))
    elif fmt == "json":
        print(json.dumps(post, ensure_ascii=False, indent=2))
    else:
        print(to_markdown(post))


def cmd_crawl(blog_id: str, output_dir: str, fmt: str = "markdown",
              delay: float = 1.0, limit: int = 0):
    """전체 크롤링."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 글 목록 수집 또는 기존 목록 사용
    list_file = out / "posts.json"
    if list_file.exists():
        posts = json.loads(list_file.read_text())
        print(f"기존 목록 사용: {len(posts)}편", file=sys.stderr)
    else:
        posts = fetch_all_posts(blog_id, delay=0.3)
        list_file.write_text(json.dumps(posts, ensure_ascii=False, indent=2))

    if limit > 0:
        posts = posts[:limit]

    ext = "org" if fmt == "org" else "md"
    done = 0
    skipped = 0

    for i, p in enumerate(posts):
        log_no = p["log_no"]
        fname = out / f"{log_no}.{ext}"
        if fname.exists():
            skipped += 1
            continue

        try:
            post = extract_post(blog_id, log_no)
            if fmt == "org":
                content = to_org(post, blog_id)
            else:
                content = to_markdown(post)
            fname.write_text(content)
            done += 1

            if done % 20 == 0:
                print(f"  {done}/{len(posts)} 완료 (스킵: {skipped})", file=sys.stderr)

        except Exception as e:
            print(f"  ❌ {log_no}: {e}", file=sys.stderr)

        time.sleep(delay)

    print(f"완료: {done}편 저장, {skipped}편 스킵", file=sys.stderr)


def cmd_wordmap(blog_id: str, output_dir: str):
    """해시태그 워드맵 생성."""
    out = Path(output_dir)
    if not out.exists():
        print(f"먼저 crawl을 실행하세요: {output_dir}", file=sys.stderr)
        sys.exit(1)

    wm = build_wordmap(out)
    result_file = out / "wordmap.json"
    result_file.write_text(json.dumps(wm, ensure_ascii=False, indent=2))
    print(f"워드맵 저장: {result_file}", file=sys.stderr)
    print(f"고유 태그: {wm['total_tags']}개", file=sys.stderr)
    print("\n상위 30개:")
    for tag, freq in list(wm["frequency"].items())[:30]:
        print(f"  {freq:4d}  {tag}")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    blog_id = sys.argv[2]

    if cmd == "list":
        output = None
        if "--output" in sys.argv:
            output = sys.argv[sys.argv.index("--output") + 1]
        cmd_list(blog_id, output)

    elif cmd == "get":
        if len(sys.argv) < 4:
            print("Usage: naver_blog_crawler.py get <blog_id> <log_no> [--format org|json|markdown]")
            sys.exit(1)
        log_no = sys.argv[3]
        fmt = "markdown"
        if "--format" in sys.argv:
            fmt = sys.argv[sys.argv.index("--format") + 1]
        cmd_get(blog_id, log_no, fmt)

    elif cmd == "crawl":
        output_dir = f"./naver-{blog_id}"
        fmt = "markdown"
        delay = 1.0
        limit = 0
        if "--output-dir" in sys.argv:
            output_dir = sys.argv[sys.argv.index("--output-dir") + 1]
        if "--format" in sys.argv:
            fmt = sys.argv[sys.argv.index("--format") + 1]
        if "--delay" in sys.argv:
            delay = float(sys.argv[sys.argv.index("--delay") + 1])
        if "--limit" in sys.argv:
            limit = int(sys.argv[sys.argv.index("--limit") + 1])
        cmd_crawl(blog_id, output_dir, fmt, delay, limit)

    elif cmd == "wordmap":
        output_dir = f"./naver-{blog_id}"
        if "--output-dir" in sys.argv:
            output_dir = sys.argv[sys.argv.index("--output-dir") + 1]
        cmd_wordmap(blog_id, output_dir)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

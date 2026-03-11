#!/usr/bin/env python3
"""
naver_blog_crawler.py — 네이버 블로그 → Denote org 변환 크롤러

네이버 블로그의 모든 글을 Denote 네이밍 규칙의 org 파일로 변환한다.
이미지는 별도 다운로드 후 문서 내 링크로 교체.
범용 도구: 블로그 ID만 바꾸면 어떤 네이버 블로그든 사용 가능.

Usage:
    # 글 목록 + 카테고리 수집
    python3 naver_blog_crawler.py list saiculture --output posts.json

    # 단일 글 확인
    python3 naver_blog_crawler.py get saiculture 224202104252

    # 전체 크롤링 → Denote org + 이미지
    python3 naver_blog_crawler.py crawl saiculture --output-dir ./output

    # 소규모 테스트
    python3 naver_blog_crawler.py crawl saiculture --output-dir ./output --limit 10

    # 해시태그 워드맵
    python3 naver_blog_crawler.py wordmap --output-dir ./output

Output structure:
    output/
    ├── posts.json                          # 글 목록 (캐시)
    ├── categories.json                     # 카테고리 매핑
    ├── 철학의-산책길/                       # 카테고리 폴더
    │   ├── 20260304T061200--현대의-언어론적-패러다임.org
    │   └── images/
    │       └── 224202104252_001.jpg
    ├── 하이데거-철학/
    │   └── ...
    └── wordmap.json
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

def fetch_post_list(blog_id: str, page: int = 1, count: int = 30) -> tuple[list, int]:
    """PostTitleListAsync API로 글 목록 한 페이지."""
    url = (
        f"https://blog.naver.com/PostTitleListAsync.naver"
        f"?blogId={blog_id}&currentPage={page}"
        f"&categoryNo=0&countPerPage={count}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    raw = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")

    pairs = re.findall(r'"logNo":"(\d+)","title":"([^"]+)"', raw)
    cat_pairs = re.findall(r'"logNo":"(\d+)"[^}]*"categoryNo":"(\d+)"', raw)
    add_dates = re.findall(r'"logNo":"(\d+)"[^}]*?"addDate":"([^"]+)"', raw)
    cat_map = dict(cat_pairs)
    date_map = dict(add_dates)

    total_m = re.search(r'"totalCount":"?(\d+)', raw)
    total = int(total_m.group(1)) if total_m else 0

    results = []
    for log_no, title_enc in pairs:
        title = _decode_entities(urllib.parse.unquote_plus(title_enc))
        results.append({
            "log_no": log_no,
            "title": title,
            "category_no": cat_map.get(log_no, "0"),
            "add_date": date_map.get(log_no, ""),
        })

    return results, total


def fetch_all_posts(blog_id: str, delay: float = 0.5) -> list[dict]:
    """전체 글 목록 수집."""
    all_posts = []
    first_page, total = fetch_post_list(blog_id, page=1)
    all_posts.extend(first_page)
    total_pages = (total + 29) // 30
    print(f"총 {total}편, {total_pages} 페이지", file=sys.stderr)

    for page in range(2, total_pages + 1):
        time.sleep(delay)
        posts, _ = fetch_post_list(blog_id, page=page)
        if not posts:
            break
        all_posts.extend(posts)
        if page % 10 == 0:
            print(f"  {page}/{total_pages} ({len(all_posts)}편)", file=sys.stderr)

    print(f"수집 완료: {len(all_posts)}편", file=sys.stderr)
    return all_posts


def fetch_category_name(blog_id: str, log_no: str) -> str:
    """개별 글 페이지에서 카테고리명 추출."""
    url = f"https://m.blog.naver.com/{blog_id}/{log_no}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8")
    m = re.search(r'CategoryName\s*=\s*"([^"]+)"', html)
    if m:
        return m.group(1).encode().decode("unicode_escape")
    return ""


def build_category_map(blog_id: str, posts: list[dict], delay: float = 0.3) -> dict:
    """카테고리 번호 → 이름 매핑 구축."""
    cat_samples = {}
    for p in posts:
        c = p.get("category_no", "0")
        if c not in cat_samples and c != "0":
            cat_samples[c] = p["log_no"]

    cat_map = {}
    print(f"카테고리 {len(cat_samples)}개 이름 수집 중...", file=sys.stderr)
    for cat_no, log_no in cat_samples.items():
        try:
            name = fetch_category_name(blog_id, log_no)
            cat_map[cat_no] = name
            print(f"  {cat_no}: {name}", file=sys.stderr)
        except Exception as e:
            cat_map[cat_no] = f"category-{cat_no}"
            print(f"  {cat_no}: error ({e})", file=sys.stderr)
        time.sleep(delay)

    return cat_map


# ── 본문 추출 (텍스트 + 이미지 순서 보존) ──────────────────────

def extract_post(blog_id: str, log_no: str) -> dict:
    """모바일 URL에서 본문 추출. 텍스트/이미지 순서 보존."""
    url = f"https://m.blog.naver.com/{blog_id}/{log_no}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")

    # 제목
    title_m = re.search(r"<title>([^:<]+)", html)
    title = _decode_entities(title_m.group(1).strip()) if title_m else ""

    # 날짜+시간
    # 초(seconds)는 블로그에 없으므로 logNo % 60으로 deterministic 생성
    # → 재현 가능하고 Denote ID 충돌 방지
    sec = int(log_no) % 60
    date_m = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?\s*(\d{1,2}):(\d{2})', html)
    if date_m:
        y, mo, d, h, mi = date_m.groups()
        date_str = f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
        time_str = f"{h.zfill(2)}:{mi}"
        denote_id = f"{y}{mo.zfill(2)}{d.zfill(2)}T{h.zfill(2)}{mi}{sec:02d}"
    else:
        date_m2 = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})', html)
        if date_m2:
            y, mo, d = date_m2.groups()
            date_str = f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
            time_str = "00:00"
            denote_id = f"{y}{mo.zfill(2)}{d.zfill(2)}T0000{sec:02d}"
        else:
            date_str = ""
            time_str = ""
            denote_id = ""

    # 카테고리
    cat_m = re.search(r'CategoryName\s*=\s*"([^"]+)"', html)
    category = cat_m.group(1).encode().decode("unicode_escape") if cat_m else ""

    cat_no_m = re.search(r'CategoryNo\s*=\s*(\d+)', html)
    category_no = cat_no_m.group(1) if cat_no_m else "0"

    # se-component 단위로 텍스트/이미지 순서 보존 파싱
    content_blocks = []  # (type, data)
    images = []

    for m in re.finditer(
        r'class="se-component\s+se-(text|image|sticker)[^"]*"(.*?)(?=class="se-component\s|</div>\s*</div>\s*</div>\s*$)',
        html, re.DOTALL
    ):
        ctype = m.group(1)
        block = m.group(2)

        if ctype == "text":
            paras = re.findall(
                r'class="se-text-paragraph[^"]*"[^>]*>(.*?)</p>', block, re.DOTALL
            )
            text = "\n\n".join(
                _clean_html(p) for p in paras if _clean_html(p)
            )
            if text:
                content_blocks.append(("text", text))

        elif ctype == "image":
            img_url = ""
            img_m = re.search(r'data-lazy-src="([^"]+)"', block)
            if not img_m:
                img_m = re.search(r'src="(https?://[^"]*pstatic[^"]+)"', block)
            if img_m:
                img_url = img_m.group(1)
                # type 파라미터 제거 후 원본 크기로
                img_url = re.sub(r'\?type=\w+', '?type=w966', img_url)

            caption = ""
            cap_m = re.search(r'class="se-caption[^"]*"[^>]*>(.*?)</figcaption>', block, re.DOTALL)
            if cap_m:
                caption = _clean_html(cap_m.group(1))

            if img_url:
                img_idx = len(images)
                images.append({"url": img_url, "caption": caption, "index": img_idx})
                content_blocks.append(("image", img_idx))

    # se-component가 없는 구버전
    if not content_blocks:
        old_paras = re.findall(
            r'class="se-text-paragraph[^"]*"[^>]*>(.*?)</p>', html, re.DOTALL
        )
        if not old_paras:
            old_paras = re.findall(
                r'class="__se_component_area"[^>]*>(.*?)</div>', html, re.DOTALL
            )
        for p in old_paras:
            text = _clean_html(p)
            if text:
                content_blocks.append(("text", text))

        # 구버전 이미지
        for img_m in re.finditer(r'src="(https?://postfiles[^"]+)"', html):
            img_idx = len(images)
            images.append({"url": img_m.group(1), "caption": "", "index": img_idx})
            content_blocks.append(("image", img_idx))

    # 해시태그 수집
    hashtags = set()
    for btype, bdata in content_blocks:
        if btype == "text":
            for tag in re.findall(r"#(\S+)", bdata):
                hashtags.add(tag)

    return {
        "log_no": log_no,
        "title": title,
        "date": date_str,
        "time": time_str,
        "denote_id": denote_id,
        "category": category,
        "category_no": category_no,
        "url": url,
        "content_blocks": content_blocks,
        "images": images,
        "hashtags": sorted(hashtags),
    }


def _decode_entities(s: str) -> str:
    """HTML 엔티티 변환. 제목/본문 공통."""
    s = s.replace("&lt;", "<").replace("&gt;", ">")
    s = s.replace("&amp;", "&").replace("&quot;", '"')
    s = s.replace("&apos;", "'").replace("&#39;", "'")
    s = s.replace("&nbsp;", " ").replace("&ndash;", "–").replace("&mdash;", "—")
    # &#xNN; / &#NNN; 숫자 엔티티
    s = re.sub(r'&#x([0-9A-Fa-f]+);', lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), s)
    s = s.replace("\u200b", "")
    # 연속 공백 정리
    s = re.sub(r'  +', ' ', s)
    return s


def _clean_html(s: str) -> str:
    """HTML 태그 제거 + 엔티티 변환."""
    text = re.sub(r"<[^>]+>", "", s).strip()
    return _decode_entities(text)


# ── 이미지 다운로드 ──────────────────────────────────────────

def _encode_url(url: str) -> str:
    """URL 내 한글 등 non-ASCII 문자를 percent-encoding."""
    # 이미 인코딩된 부분은 보존, 한글만 인코딩
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(parts.path, safe="/@!$&'()*+,;=-._~:")
    query = urllib.parse.quote(parts.query, safe="=&")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def download_image(img_url: str, dest_path: Path) -> bool:
    """이미지 다운로드. 이미 있으면 스킵."""
    if dest_path.exists():
        return True
    try:
        encoded_url = _encode_url(img_url)
        req = urllib.request.Request(encoded_url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://m.blog.naver.com/",
        })
        data = urllib.request.urlopen(req, timeout=15).read()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        return True
    except Exception as e:
        print(f"  ⚠️ 이미지 다운로드 실패: {img_url[:80]} → {e}", file=sys.stderr)
        return False


# ── Denote org 출력 ──────────────────────────────────────────

def slugify(title: str) -> str:
    """한글 제목을 Denote 파일명용으로 변환."""
    # 특수문자 제거, 공백→하이픈
    slug = re.sub(r"[^\w\s가-힣-]", "", title)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug)
    return slug[:80]  # 길이 제한


def category_dirname(name: str) -> str:
    """카테고리명을 디렉토리명으로. 공백→하이픈."""
    if not name:
        return "uncategorized"
    return re.sub(r"\s+", "-", name.strip())


def to_denote_org(post: dict, img_dir: str = "images") -> str:
    """포스트를 Denote org-mode 형식으로 변환."""
    lines = [
        f"#+title:      {post['title']}",
        f"#+date:       [{post['date']} {post['time']}]",
        f"#+identifier: {post['denote_id']}",
        f"#+source:     {post['url']}",
    ]
    if post["category"]:
        lines.append(f"#+category:   {post['category']}")
    if post["hashtags"]:
        tags_str = " ".join(f"#{t}" for t in post["hashtags"])
        lines.append(f"#+blog_tags:  {tags_str}")
    lines.append("")

    for btype, bdata in post["content_blocks"]:
        if btype == "text":
            lines.append(bdata)
            lines.append("")
        elif btype == "image":
            img = post["images"][bdata]
            ext = _img_ext(img["url"])
            fname = f"{post['log_no']}_{bdata:03d}{ext}"
            lines.append(f"[[file:{img_dir}/{fname}]]")
            if img["caption"]:
                lines.append(f"#+caption: {img['caption']}")
            lines.append("")

    return "\n".join(lines)


def _img_ext(url: str) -> str:
    """URL에서 이미지 확장자 추출."""
    m = re.search(r"\.(jpg|jpeg|png|gif|webp)", url, re.I)
    return f".{m.group(1).lower()}" if m else ".jpg"


# ── CLI Commands ──────────────────────────────────────────

def cmd_list(blog_id: str, output: str = None):
    """글 목록 + 카테고리 수집."""
    posts = fetch_all_posts(blog_id)
    cat_map = build_category_map(blog_id, posts)

    # 카테고리명 추가
    for p in posts:
        p["category"] = cat_map.get(p["category_no"], "")

    if output:
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(posts, ensure_ascii=False, indent=2))
        # 카테고리 매핑도 저장
        cat_file = out.parent / "categories.json"
        cat_file.write_text(json.dumps(cat_map, ensure_ascii=False, indent=2))
        print(f"저장: {output} ({len(posts)}편), {cat_file}", file=sys.stderr)
    else:
        for p in posts:
            cat = cat_map.get(p["category_no"], "?")
            print(f"{p['log_no']}\t{p['add_date']}\t[{cat}]\t{p['title']}")


def cmd_get(blog_id: str, log_no: str):
    """단일 글 추출 (미리보기)."""
    post = extract_post(blog_id, log_no)
    print(to_denote_org(post))
    print(f"\n# 이미지 {len(post['images'])}개, 해시태그 {len(post['hashtags'])}개",
          file=sys.stderr)


def cmd_crawl(blog_id: str, output_dir: str, delay: float = 1.0, limit: int = 0):
    """전체 크롤링 → Denote org + 이미지."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. 글 목록
    list_file = out / "posts.json"
    cat_file = out / "categories.json"
    if list_file.exists():
        posts = json.loads(list_file.read_text())
        print(f"기존 목록 사용: {len(posts)}편", file=sys.stderr)
    else:
        posts = fetch_all_posts(blog_id, delay=0.3)
        cat_map = build_category_map(blog_id, posts)
        for p in posts:
            p["category"] = cat_map.get(p["category_no"], "")
        list_file.write_text(json.dumps(posts, ensure_ascii=False, indent=2))
        cat_file.write_text(json.dumps(cat_map, ensure_ascii=False, indent=2))

    if limit > 0:
        posts = posts[:limit]

    # 2. 카테고리 매핑
    cat_map = {}
    if cat_file.exists():
        cat_map = json.loads(cat_file.read_text())

    done = 0
    skipped = 0
    img_count = 0

    for i, p in enumerate(posts):
        log_no = p["log_no"]

        # 카테고리 폴더
        cat_name = p.get("category") or cat_map.get(p["category_no"], "")
        cat_dir = out / category_dirname(cat_name)
        cat_dir.mkdir(parents=True, exist_ok=True)

        # 이미 있는지 체크 (denote_id 기반)
        existing = list(cat_dir.glob(f"*{log_no}*"))
        if existing:
            skipped += 1
            continue

        try:
            post = extract_post(blog_id, log_no)
            if not post["denote_id"]:
                print(f"  ⚠️ {log_no}: 날짜 없음, 스킵", file=sys.stderr)
                continue

            # Denote 파일명
            slug = slugify(post["title"])
            fname = f"{post['denote_id']}--{slug}.org"
            fpath = cat_dir / fname

            # 이미지 다운로드
            img_dir = cat_dir / "images"
            for img in post["images"]:
                ext = _img_ext(img["url"])
                img_fname = f"{log_no}_{img['index']:03d}{ext}"
                if download_image(img["url"], img_dir / img_fname):
                    img_count += 1

            # org 파일 저장
            content = to_denote_org(post)
            fpath.write_text(content)
            done += 1

            if done % 20 == 0:
                print(f"  {done}/{len(posts)} 완료 (이미지: {img_count}, 스킵: {skipped})",
                      file=sys.stderr)

        except Exception as e:
            print(f"  ❌ {log_no}: {e}", file=sys.stderr)

        time.sleep(delay)

    print(f"\n완료: {done}편 저장, 이미지 {img_count}개, 스킵 {skipped}편", file=sys.stderr)


def cmd_verify(output_dir: str) -> list[dict]:
    """크롤링 결과 정합성 검사. 누락/고아/깨진 이미지 검출."""
    out = Path(output_dir)

    # 1. org 파일에서 이미지 참조 수집
    referenced = {}  # full_path → org_file
    missing = []
    total_refs = 0
    org_files = sorted(out.rglob("*.org"))

    for org_file in org_files:
        dir_path = org_file.parent
        text = org_file.read_text()
        for m in re.finditer(r'\[\[file:(images/[^\]]+)\]\]', text):
            img_rel = m.group(1)
            total_refs += 1
            full = dir_path / img_rel
            referenced[str(full.resolve())] = str(org_file.relative_to(out))
            if not full.exists():
                missing.append({
                    "file": str(org_file.relative_to(out)),
                    "image": img_rel,
                })

    # 2. 디스크 이미지 파일 수집
    all_images = set()
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.gif", "*.webp"):
        for f in out.rglob(ext):
            all_images.add(str(f.resolve()))

    # 3. 고아 이미지 (파일O 참조X)
    orphans = sorted(all_images - set(referenced.keys()))

    # 4. 깨진 이미지 (1KB 미만 또는 HTML 응답)
    corrupted = []
    for img_path in sorted(all_images):
        p = Path(img_path)
        size = p.stat().st_size
        if size < 1024:
            corrupted.append({"path": str(p.relative_to(out.resolve())), "reason": f"too_small ({size}B)"})
        elif size < 5000:
            with open(p, "rb") as fh:
                header = fh.read(20).lower()
                if b"<html" in header or b"<!doctype" in header:
                    corrupted.append({"path": str(p.relative_to(out.resolve())), "reason": "html_response"})

    result = {
        "total_org_files": len(org_files),
        "total_image_refs": total_refs,
        "total_images_on_disk": len(all_images),
        "missing_count": len(missing),
        "orphan_count": len(orphans),
        "corrupted_count": len(corrupted),
        "status": "OK" if not missing and not orphans and not corrupted else "ISSUES",
        "missing": missing,
        "orphans": [str(Path(o).relative_to(out.resolve())) for o in orphans[:50]],
        "corrupted": corrupted[:50],
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return missing


def cmd_retry(blog_id: str, output_dir: str, delay: float = 1.0):
    """누락 이미지 재다운로드. verify 결과를 기반으로 글을 다시 파싱하여 이미지 URL 확보."""
    out = Path(output_dir)

    # 누락 이미지 수집
    missing_by_logno = {}  # logNo → [(img_rel, dir_path)]
    for org_file in sorted(out.rglob("*.org")):
        dir_path = org_file.parent
        text = org_file.read_text()
        for m in re.finditer(r'\[\[file:(images/[^\]]+)\]\]', text):
            img_rel = m.group(1)
            if not (dir_path / img_rel).exists():
                log_no_m = re.search(r'(\d{9,15})_\d{3}', img_rel)
                if log_no_m:
                    ln = log_no_m.group(1).split("_")[0].split("/")[-1]
                    missing_by_logno.setdefault(ln, []).append((img_rel, str(dir_path)))

    total_missing = sum(len(v) for v in missing_by_logno.values())
    print(f"누락 이미지: {total_missing}개 ({len(missing_by_logno)}편)", file=sys.stderr)
    if not missing_by_logno:
        print("모든 이미지 정상!", file=sys.stderr)
        return

    done = 0
    failed = 0
    for i, (log_no, items) in enumerate(missing_by_logno.items()):
        try:
            post = extract_post(blog_id, log_no)
            for img_rel, dir_str in items:
                idx_m = re.search(r'_(\d{3})', img_rel)
                if not idx_m:
                    failed += 1
                    continue
                idx = int(idx_m.group(1))
                if idx < len(post["images"]):
                    img = post["images"][idx]
                    dest = Path(dir_str) / img_rel
                    if download_image(img["url"], dest):
                        done += 1
                    else:
                        failed += 1
                else:
                    failed += 1
        except Exception as e:
            print(f"  ❌ {log_no}: {e}", file=sys.stderr)
            failed += len(items)

        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(missing_by_logno)} 글 처리 (성공: {done}, 실패: {failed})",
                  file=sys.stderr)
        time.sleep(delay)

    print(f"\n완료: 성공 {done}, 실패 {failed}", file=sys.stderr)


def _clean_hashtag(tag: str) -> str:
    """해시태그 정규화. HTML entity 잔여물 제거, 문장부호 strip."""
    # HTML entity 잔여물 (&#x27; → ', &#x3D; → = 등이 깨진 형태)
    if re.match(r'^x[0-9A-Fa-f]{2};', tag):
        return ""  # x27;..., x3D;... 패턴 통째 제거

    # HTML entity 중간에 남은 것 제거
    tag = re.sub(r'&#?x?[0-9A-Fa-f]{2,4};', '', tag)

    # 끝 문장부호 strip (반복): 콜론, 쉼표, 마침표, 세미콜론, 물음표, 느낌표, 따옴표, 꺾쇠, 괄호
    tag = re.sub(r'[,:;.!?\"\'>)\]]+$', '', tag)
    # 앞 문장부호 strip
    tag = re.sub(r'^[,:;.!?\"\'\[(<]+', '', tag)

    # 빈 문자열이나 순수 부호만 남은 경우
    tag = tag.strip()
    if not tag or re.match(r'^[^가-힣a-zA-Z0-9]+$', tag):
        return ""

    return tag


def cmd_fix_titles(output_dir: str):
    """기존 org 파일의 제목/파일명에서 HTML entity 잔여물 수정. 재크롤링 불필요."""
    out = Path(output_dir)
    fixed_titles = 0
    renamed = 0

    for org_file in sorted(out.rglob("*.org")):
        text = org_file.read_text()
        changed = False

        # #+title: 정리
        title_m = re.search(r'^(#\+title:\s+)(.+)$', text, re.MULTILINE)
        if title_m:
            old_title = title_m.group(2)
            new_title = _decode_entities(old_title)
            if old_title != new_title:
                text = text.replace(title_m.group(0), title_m.group(1) + new_title)
                changed = True
                fixed_titles += 1

        if changed:
            org_file.write_text(text)

        # 파일명 정리
        fname = org_file.name
        # Denote 패턴: YYYYMMDDTHHMMSS--제목.org
        fname_m = re.match(r'(\d{8}T\d{6}--)(.*)(\.org)$', fname)
        if not fname_m:
            continue

        # 수정된 제목에서 새 slug 생성
        title_m2 = re.search(r'^#\+title:\s+(.+)$', text, re.MULTILINE)
        if not title_m2:
            continue
        old_slug = fname_m.group(2)
        new_slug = slugify(title_m2.group(1))
        if old_slug != new_slug:
            new_fname = f"{fname_m.group(1)}{new_slug}{fname_m.group(3)}"
            new_path = org_file.parent / new_fname
            if not new_path.exists():
                org_file.rename(new_path)
                renamed += 1

    print(f"제목 수정: {fixed_titles}편, 파일명 변경: {renamed}편", file=sys.stderr)


def cmd_wordmap(output_dir: str):
    """해시태그 워드맵 생성. HTML entity 정리 + 정규화 포함."""
    out = Path(output_dir)
    tag_freq = {}
    tag_cooccur = {}
    file_count = 0
    raw_count = 0
    cleaned_count = 0

    for org_file in out.rglob("*.org"):
        text = org_file.read_text()
        tags_m = re.search(r"^\#\+blog_tags:\s+(.+)$", text, re.MULTILINE)
        if not tags_m:
            continue

        raw_tags = [t.lstrip("#") for t in tags_m.group(1).split()]
        raw_count += len(raw_tags)

        # 정규화
        tags = []
        for t in raw_tags:
            cleaned = _clean_hashtag(t)
            if cleaned:
                tags.append(cleaned)
        cleaned_count += len(tags)

        if not tags:
            continue

        file_count += 1
        for t in tags:
            tag_freq[t] = tag_freq.get(t, 0) + 1
        for i, t1 in enumerate(tags):
            for t2 in tags[i + 1:]:
                pair = tuple(sorted([t1, t2]))
                tag_cooccur[pair] = tag_cooccur.get(pair, 0) + 1

    wm = {
        "total_files": file_count,
        "total_unique_tags": len(tag_freq),
        "raw_tag_count": raw_count,
        "cleaned_tag_count": cleaned_count,
        "removed_noise": raw_count - cleaned_count,
        "frequency": dict(sorted(tag_freq.items(), key=lambda x: -x[1])),
        "cooccurrence_top100": {
            f"{k[0]} + {k[1]}": v
            for k, v in sorted(tag_cooccur.items(), key=lambda x: -x[1])[:100]
        },
    }

    result_file = out / "wordmap.json"
    result_file.write_text(json.dumps(wm, ensure_ascii=False, indent=2))
    print(f"워드맵: {result_file}", file=sys.stderr)
    print(f"파일: {file_count}, 고유 태그: {len(tag_freq)}개", file=sys.stderr)
    print(f"노이즈 제거: {raw_count} → {cleaned_count} ({raw_count - cleaned_count}개 제거)\n",
          file=sys.stderr)
    print("상위 50개:")
    for tag, freq in list(wm["frequency"].items())[:50]:
        print(f"  {freq:4d}  {tag}")


# ── main ──────────────────────────────────────────────

def _parse_flag(args: list, flag: str, default=None):
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            return args[idx + 1]
    return default


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        blog_id = sys.argv[2] if len(sys.argv) > 2 else "saiculture"
        output = _parse_flag(sys.argv, "--output")
        cmd_list(blog_id, output)

    elif cmd == "get":
        blog_id = sys.argv[2]
        log_no = sys.argv[3]
        cmd_get(blog_id, log_no)

    elif cmd == "crawl":
        blog_id = sys.argv[2] if len(sys.argv) > 2 else "saiculture"
        output_dir = _parse_flag(sys.argv, "--output-dir", f"./naver-{blog_id}")
        delay = float(_parse_flag(sys.argv, "--delay", "1.0"))
        limit = int(_parse_flag(sys.argv, "--limit", "0"))
        cmd_crawl(blog_id, output_dir, delay, limit)

    elif cmd == "verify":
        output_dir = _parse_flag(sys.argv, "--output-dir", "./output")
        cmd_verify(output_dir)

    elif cmd == "retry":
        blog_id = sys.argv[2] if len(sys.argv) > 2 else "saiculture"
        output_dir = _parse_flag(sys.argv, "--output-dir", f"./naver-{blog_id}")
        delay = float(_parse_flag(sys.argv, "--delay", "1.0"))
        cmd_retry(blog_id, output_dir, delay)

    elif cmd == "fix-titles":
        output_dir = _parse_flag(sys.argv, "--output-dir", "./output")
        cmd_fix_titles(output_dir)

    elif cmd == "wordmap":
        output_dir = _parse_flag(sys.argv, "--output-dir", "./output")
        cmd_wordmap(output_dir)

    else:
        print(f"Unknown: {cmd}\n")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""누락 이미지만 재다운로드. 크롤링 후 실패분 복구용."""

import re
import sys
import time
from pathlib import Path
from scripts.naver_blog_crawler import extract_post, download_image, _img_ext


def main():
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "./naver-saiculture"
    out = Path(output_dir)

    # 누락 이미지 찾기
    missing = []
    for org_file in sorted(out.rglob("*.org")):
        text = org_file.read_text()
        dir_path = org_file.parent
        for m in re.finditer(r'\[\[file:(images/[^\]]+)\]\]', text):
            img_rel = m.group(1)
            if not (dir_path / img_rel).exists():
                # logNo 추출
                log_no_m = re.search(r'(\d{9,15})_\d{3}', img_rel)
                if log_no_m:
                    missing.append({
                        "org_file": str(org_file),
                        "img_rel": img_rel,
                        "log_no": log_no_m.group(1).split("_")[0].split("/")[-1],
                        "dir": str(dir_path),
                    })

    print(f"누락 이미지: {len(missing)}개", file=sys.stderr)
    if not missing:
        return

    # logNo별로 그룹핑 (같은 글 반복 요청 방지)
    by_logno = {}
    for m in missing:
        ln = re.search(r'(\d{9,15})', m["img_rel"]).group(1)
        by_logno.setdefault(ln, []).append(m)

    print(f"글 {len(by_logno)}편에서 이미지 재다운로드", file=sys.stderr)

    done = 0
    failed = 0
    for i, (log_no, items) in enumerate(by_logno.items()):
        try:
            post = extract_post("saiculture", log_no)
            for item in items:
                # 해당 이미지 인덱스 찾기
                idx_m = re.search(r'_(\d{3})', item["img_rel"])
                if not idx_m:
                    continue
                idx = int(idx_m.group(1))
                if idx < len(post["images"]):
                    img = post["images"][idx]
                    dest = Path(item["dir"]) / item["img_rel"]
                    if download_image(img["url"], dest):
                        done += 1
                    else:
                        failed += 1
        except Exception as e:
            print(f"  ❌ {log_no}: {e}", file=sys.stderr)
            failed += len(items)

        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(by_logno)} 글 처리 (성공: {done}, 실패: {failed})",
                  file=sys.stderr)
        time.sleep(1.0)

    print(f"\n완료: 성공 {done}, 실패 {failed}", file=sys.stderr)


if __name__ == "__main__":
    main()

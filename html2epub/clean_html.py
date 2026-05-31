#!/usr/bin/env python3
"""
HTML -> EPUB 변환용 정리 스크립트

Immersive Translate로 번역된 PDF-to-HTML 파일을 정리합니다.
- Immersive Translate 태그에서 한글 번역만 추출
- 목차(TOC) 자동 생성
- EPUB 변환에 적합한 깔끔한 HTML 출력

사용법:
    python3 clean_html.py input.html output.html [--keep-images]
"""

from bs4 import BeautifulSoup, NavigableString
import re
import sys
import argparse


def extract_korean_text(element):
    """immersive-translate 태그에서 한글 번역 텍스트 추출"""
    # 번역된 텍스트 찾기
    inner = element.find('font', class_=lambda c: c and 'immersive-translate-target-inner' in c)
    if inner:
        return inner.get_text(strip=True)
    # 번역이 없으면 원본 텍스트
    return element.get_text(strip=True)


# 로마 숫자 -> 아라비아 숫자 변환
ROMAN_MAP = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
    'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
    'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15,
    'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19, 'XX': 20
}


# 목차에 포함할 헤딩의 id 패턴 (화이트리스트 방식)
# h1으로 승격할 패턴
H1_ID_PATTERNS = [
    r'^foreword-',       # 서문
    r'^preface-',        # 머리말
    r'^index$',          # 색인
]

# h2로 유지할 패턴 (챕터만)
CHAPTER_ID_PATTERNS = [
    r'^chapter[-]?[ivxlc]+$',  # chapter-i, chapteri, chapter-ii 등
]

# 필터링할 헤딩의 id 패턴 (블랙리스트)
SKIP_ID_PATTERNS = [
    r'^between-pages-',      # 이미지 페이지 구분
    r'^illustrations',       # 삽화
    r'^contents$',           # 목차 자체
    r'^thinking$',           # 소제목
    r'^humor$',
    r'^composition$',
    r'^demonstration$',
    r'^participation$',
    r'^animation$',
    r'^ii$', r'^iii$', r'^iv$', r'^v$',  # 로마 숫자 번호
    r'^\(a\)$', r'^\(b\)$', r'^\(c\)$',  # 알파벳 번호
    r'^whooping-cranes',     # 이상한 제목
    r'^national-park-service',  # 이미지 캡션
    # 챕터 subtitle들 (CHAPTER_TITLES에서 처리하므로 제외)
    r'^principles-of-interpretation$',
    r'^the-visitor',
    r'^raw-material',
    r'^the-story',
    r'^not-instruction',
    r'^the-chiefaim',  # CHAPTER V 한글 번역
    r'^toward-a-perfect',
    r'^for-the-younger',
    r'^the-written-word$',
    r'^past-',
    r'^nothing-in-excess$',
    r'^the-mystery',
    r'^the-priceless',
    r'^of-gadgetry$',
    r'^the-happy',
    r'^vistas-of-beauty$',
]


def should_be_h1(element_id):
    """h1으로 승격해야 할 헤딩인지 확인"""
    if not element_id:
        return False
    for pattern in H1_ID_PATTERNS:
        if re.match(pattern, element_id, re.IGNORECASE):
            return True
    return False


def is_valid_chapter(element_id):
    """유효한 챕터 헤딩인지 확인"""
    if not element_id:
        return False
    for pattern in CHAPTER_ID_PATTERNS:
        if re.match(pattern, element_id, re.IGNORECASE):
            return True
    return False


def should_skip_heading(element_id, text):
    """목차에서 제외할 헤딩인지 확인"""
    # id가 없으면 텍스트로 판단
    if element_id:
        for pattern in SKIP_ID_PATTERNS:
            if re.match(pattern, element_id, re.IGNORECASE):
                return True

    # 텍스트 기반 필터링
    if text:
        # "X쪽과 Y쪽 사이" 형식
        if re.match(r'^\d+쪽과 \d+쪽 사이$', text):
            return True
        # 너무 긴 텍스트는 이미지 캡션일 가능성
        if len(text) > 50:
            return True
        # 영문 소제목 (THINKING, HUMOR 등)
        if text.upper() in ['THINKING', 'HUMOR', 'DEMONSTRATION', 'PARTICIPATION', 'ANIMATION']:
            return True

    return False


def normalize_chapter_number(text):
    """챕터 번호를 '제X장' 형식으로 통일"""
    text = text.strip()

    # 이미 '제X장' 형식
    m = re.match(r'^제\s*(\d+|[IVXLC]+)\s*장$', text)
    if m:
        num = m.group(1)
        if num in ROMAN_MAP:
            return f"제{ROMAN_MAP[num]}장"
        return f"제{num}장"

    # 'CHAPTER X' 또는 'CHAPTERX' 형식
    m = re.match(r'^CHAPTER\s*([IVXLC]+|\d+)$', text, re.IGNORECASE)
    if m:
        num = m.group(1).upper()
        if num in ROMAN_MAP:
            return f"제{ROMAN_MAP[num]}장"
        return f"제{num}장"

    return None  # 챕터 번호가 아님


def is_chapter_number(text):
    """텍스트가 챕터 번호인지 확인"""
    return normalize_chapter_number(text) is not None


# 챕터 영어 제목 매핑 (PDF 원본 기준)
CHAPTER_TITLES = {
    'chapteri': 'I. Principles of Interpretation',
    'chapter-ii': 'II. The Visitor\'s First Interest',
    'chapter-iii': 'III. Raw Material and Its Product',
    'chapter-iv': 'IV. The Story\'s the Thing',
    'chapter-v': 'V. Not Instruction But Provocation',
    'chapter-vi': 'VI. Toward a Perfect Whole',
    'chapter-vii': 'VII. For the Younger Mind',
    'chapter-viii': 'VIII. The Written Word',
    'chapter-ix': 'IX. Past and Present',
    'chapter-x': 'X. Nothing in Excess',
    'chapter-xi': 'XI. The Mystery of Beauty',
    'chapter-xii': 'XII. The Priceless Ingredient',
    'chapter-xiii': 'XIII. Of Gadgetry',
    'chapter-xiv': 'XIV. The Happy Amateur',
    'chapter-xv': 'XV. Vistas of Beauty',
}


def clean_html_for_epub(input_file, output_file, keep_images=True):
    """HTML 파일을 EPUB 변환용으로 정리"""

    with open(input_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # 1. 불필요한 style, script, mathml 태그 제거
    for tag in soup.find_all(['style', 'script', 'mathml', 'mathmlword', 'asciimath', 'latex', 'mjx-container']):
        tag.decompose()

    # 2. 본문 컨텐츠 영역 찾기
    content = soup.find(id='pdf-pro-content') or soup.find(id='preview-content') or soup.find('body')

    # 2a. PART ONE/TWO 헤딩 삽입
    chapteri = content.find(id='chapteri')
    if chapteri:
        part_one = soup.new_tag('h1')
        part_one['id'] = 'part-one'
        part_one.string = 'PART ONE'
        chapteri.insert_before(part_one)

    chapterviii = content.find(id='chapter-viii')
    if chapterviii:
        part_two = soup.new_tag('h1')
        part_two['id'] = 'part-two'
        part_two.string = 'PART TWO'
        chapterviii.insert_before(part_two)

    # 3. 새 문서 구조 생성
    new_soup = BeautifulSoup('''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title></title>
    <style>
        body { font-family: 'Noto Serif KR', serif; line-height: 1.8; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { font-size: 2em; margin-top: 2em; border-bottom: 2px solid #333; }
        h2 { font-size: 1.5em; margin-top: 1.5em; }
        h3 { font-size: 1.2em; margin-top: 1em; }
        p { text-indent: 1em; margin: 0.8em 0; }
        figure { text-align: center; margin: 1.5em 0; }
        img { max-width: 100%; height: auto; }
        .toc { background: #f5f5f5; padding: 1em 2em; margin: 2em 0; }
        .toc h2 { margin-top: 0; }
        .toc ul { list-style: none; padding-left: 0; }
        .toc li { margin: 0.5em 0; }
        .toc a { text-decoration: none; color: #333; }
    </style>
</head>
<body>
</body>
</html>''', 'html.parser')

    body = new_soup.find('body')
    title_tag = new_soup.find('title')
    toc_entries = []
    heading_count = 0

    # 4. 헤딩 처리 - id 기반으로 구조화
    all_elements = list(content.find_all(['h1', 'h2', 'h3', 'div', 'p', 'figure']))

    for element in all_elements:
        # 4a. 헤딩 처리
        if element.name in ['h1', 'h2', 'h3']:
            elem_id = element.get('id', '').lower()
            text = extract_korean_text(element)

            # 건너뛸 헤딩 체크
            if should_skip_heading(elem_id, text):
                continue

            # 레벨과 텍스트 결정
            heading_level = element.name
            heading_text = text

            # PART ONE/TWO (h1으로 삽입됨)
            if elem_id in ['part-one', 'part-two']:
                heading_level = 'h1'
                heading_text = element.get_text(strip=True)

            # Foreword/Preface/Index → h1으로 승격
            elif should_be_h1(elem_id):
                heading_level = 'h1'
                heading_text = text

            # 챕터 → h2로 유지, 영어 제목 사용
            elif elem_id in CHAPTER_TITLES:
                heading_level = 'h2'
                heading_text = CHAPTER_TITLES[elem_id]

            # 일반 헤딩
            else:
                if not text or len(text) < 2:
                    continue
                heading_text = text

            # 새 헤딩 생성
            heading_count += 1
            heading_id = f"section-{heading_count}"

            new_heading = new_soup.new_tag(heading_level)
            new_heading.string = heading_text
            new_heading['id'] = heading_id
            body.append(new_heading)

            # 목차 항목 추가 (h1, h2만)
            if heading_level in ['h1', 'h2']:
                toc_entries.append({
                    'level': heading_level,
                    'text': heading_text,
                    'id': heading_id
                })

            # 첫 h1을 문서 제목으로
            if heading_level == 'h1' and not title_tag.string:
                title_tag.string = heading_text

        # 4b. 문단/div 처리
        elif element.name in ['div', 'p']:
            # 중첩 div 건너뛰기
            if element.find(['h1', 'h2', 'h3', 'figure']):
                continue

            text = extract_korean_text(element)
            if not text or len(text) < 10:
                continue

            # 영문만 있는 것 건너뛰기 (원문 잔여물)
            if not re.search(r'[가-힣]', text):
                continue

            new_p = new_soup.new_tag('p')
            new_p.string = text
            body.append(new_p)

        # 4c. 이미지 처리
        elif element.name == 'figure' and keep_images:
            img = element.find('img')
            if img and img.get('src'):
                new_figure = new_soup.new_tag('figure')
                new_img = new_soup.new_tag('img')
                new_img['src'] = img['src']
                new_img['alt'] = img.get('alt', '')
                new_figure.append(new_img)
                body.append(new_figure)

    # 5. 목차 생성 (헤딩 앞에 삽입)
    if toc_entries:
        toc_div = new_soup.new_tag('nav')
        toc_div['class'] = 'toc'
        toc_title = new_soup.new_tag('h2')
        toc_title.string = 'Table of Contents'
        toc_div.append(toc_title)

        toc_ul = new_soup.new_tag('ul')
        for entry in toc_entries:
            li = new_soup.new_tag('li')
            a = new_soup.new_tag('a')
            a['href'] = f"#{entry['id']}"
            a.string = entry['text']
            # h2는 들여쓰기
            if entry['level'] == 'h2':
                li['style'] = 'padding-left: 2em;'
            li.append(a)
            toc_ul.append(li)
        toc_div.append(toc_ul)

        # 첫 번째 요소 앞에 삽입
        if body.contents:
            body.contents[0].insert_before(toc_div)
        else:
            body.append(toc_div)

    # 6. 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(str(new_soup))

    # 통계 출력
    headings = new_soup.find_all(['h1', 'h2', 'h3'])
    paragraphs = new_soup.find_all('p')
    images = new_soup.find_all('img')

    print(f"✓ 정리 완료: {output_file}")
    print(f"  - 제목(h1-h3): {len(headings)}개")
    print(f"  - 문단: {len(paragraphs)}개")
    print(f"  - 이미지: {len(images)}개")
    print(f"  - 목차 항목: {len(toc_entries)}개")

    return len(paragraphs) > 0


def main():
    parser = argparse.ArgumentParser(description='Immersive Translate HTML 정리')
    parser.add_argument('input', help='입력 HTML 파일')
    parser.add_argument('output', nargs='?', default=None, help='출력 HTML 파일')
    parser.add_argument('--no-images', action='store_true', help='이미지 제외')

    args = parser.parse_args()

    if args.output is None:
        args.output = args.input.replace('.html', '-clean.html')

    clean_html_for_epub(args.input, args.output, keep_images=not args.no_images)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
epub -> markdown 변환 후 정리 스크립트
=====================================

개요:
    pandoc으로 epub을 markdown 변환 후 발생하는 잔여물을 정리하는 스크립트.
    LLM 대화용, Quarto 출판용 등 깔끔한 문서 활용을 목적으로 함.

사용법:
    # 1. epub -> raw markdown 변환
    pandoc book.epub -t markdown -o book_raw.md

    # 2. MD 정리 스크립트 실행
    python cleanup_epub_md.py book_raw.md book_clean.md

    # 3. org-mode 변환
    pandoc book_clean.md -f markdown -t org -o book_clean.org

    # 4. org 내부 링크 수정 (필수!)
    python cleanup_epub_md.py --fix-org book_clean.org

처리 항목:
    [범용 - 대부분 epub에 적용 가능]
    - OceanofPDF 등 해적판 워터마크 링크 제거
    - 빈 앵커/페이지 마커 제거: []{#...}
    - Pandoc fenced divs 제거: :::
    - HTML 속성 제거: aria-label, role 등
    - 연속 빈 줄 정리

    [패턴 기반 - 유사 구조에 적용 가능]
    - Footnote를 표준 MD 형식으로 변환: [^001]
    - HTML <figure> 태그를 MD 이미지 + 앵커로 변환
    - 헤딩 클래스 속성 제거: {.h1fm} 등

    [책 특화 - IT Revolution 출판사 스타일]
    - PART/CHAPTER [제목] -> PART/CHAPTER: 제목
    - xhtml prefix 제거: ch08.xhtml_fig8_1 -> fig8_1

자동화 수준:
    - 70% 자동 (범용 규칙)
    - 30% 책 특화 (새 epub은 패턴 분석 후 규칙 추가 필요)

테스트 완료:
    - VibeCoding_Gene_Kim_Steve_Yegge.epub (Gene Kim & Steve Yegge, 2025)
      - 원본: 750KB -> 정리 후: 672KB (약 10% 감소)
      - Figure/Table 16개 목차 링크 연결 완료
      - Footnote 150개 변환 완료

Changelog:
    2025-11-23  v1.5  org 기준 파이프라인으로 변경
                      - org가 원본, md는 org에서 파생
                      - epub2org.sh: 5단계 파이프라인
                      - 임시 파일 자동 정리
    2025-11-23  v1.4  :END: 뒤 빈 줄 추가 (문단 분리 안전성)
    2025-11-23  v1.3  문단 unfill 기능 추가
                      - 문단 내 줄바꿈 제거하여 한 줄로 만듦
                      - 구조적 요소(헤딩, 리스트, 블록 등) 보존
    2025-11-23  v1.2  줄바꿈 링크 한 줄로 합침 (fill-column 문제 해결)
                      - epub2org.sh 전체 파이프라인 스크립트 추가
    2025-11-23  v1.1  org 내부 링크 문법 수정
                      - [[#id]] -> [[id]] (# 제거, org 타겟 문법 준수)
                      - #+NAME: -> <<target>> 형식으로 변경
                      - --fix-org 옵션 추가
    2025-11-23  v1.0  초기 버전 (VibeCoding 책 기준)
                      - OceanofPDF 제거
                      - Pandoc div/속성 정리
                      - Footnote 변환 (로마자/숫자 혼합 패턴)
                      - HTML figure -> MD 이미지 + <a id> 앵커 변환
                      - 목차 링크 ID 정규화

작성: junghanacs (with AI assistant)
"""

import re
import sys
from pathlib import Path


def cleanup_epub_markdown(content: str) -> str:
    """epub에서 변환된 markdown 정리"""
    
    # 1. OceanofPDF 블록 제거 (div 포함)
    content = re.sub(
        r'::: \{style="float: none;[^}]*\}\n\[?\*?OceanofPDF\.com\*?\]?\([^)]*\)\n:::\n*',
        '', content
    )
    # 단독 링크도 제거
    content = re.sub(r'\[?\*?OceanofPDF\.com\*?\]?\(https://oceanofpdf\.com\)\n*', '', content)
    
    # 2. 빈 앵커/페이지마커 제거 []{#...}
    content = re.sub(r'\[\]\{#[^}]+\}\n?', '', content)
    
    # 3. Pandoc fenced divs 제거 (:::로 시작하는 라인)
    # 단, blockquote는 보존
    content = re.sub(r'^:{3,}.*$\n?', '', content, flags=re.MULTILINE)
    
    # 4. 헤딩의 클래스 속성 제거 {.h1fm}, {#id .class} 등
    content = re.sub(r'\s*\{[#.][^}]+\}\s*$', '', content, flags=re.MULTILINE)
    
    # 5. 이미지 속성 정리 - 복잡한 속성 제거하고 기본만 유지
    # ![alt](path){.class role="..."} -> ![alt](path)
    content = re.sub(r'(\!\[[^\]]*\]\([^)]+\))\{[^}]+\}', r'\1', content)
    
    # 6. Footnote 정리
    # 패턴1: ^[I](#intro.xhtml_footnote-074){#intro.xhtml_footnote-074-backlink}^
    # 패턴2: ^[7](#endnotes.xhtml_introen7){#intro.xhtml_introen_7}[III](#intro.xhtml_footnote-072){#intro.xhtml_footnote-072-backlink}^
    # -> [^074]
    
    # 복잡한 패턴 먼저 처리 (endnotes + footnote 혼합)
    def fix_complex_footnote(m):
        full = m.group(0)
        # footnote-XXX 패턴 우선
        num_match = re.search(r'footnote-(\d+)', full)
        if num_match:
            return f'[^{num_match.group(1)}]'
        # endnotes 패턴
        en_match = re.search(r'_(\w+)en(\d+)', full)
        if en_match:
            return f'[^{en_match.group(1)}-{en_match.group(2)}]'
        return ''
    
    # 복잡한 패턴: ^[숫자](#endnotes...){#...}[로마자](#footnote...){#...}^
    content = re.sub(
        r'\^\[\d+\]\([^)]+\)\{[^}]+\}\[([IVXLCDM]+)\]\([^)]+\)\{[^}]+\}\^',
        fix_complex_footnote,
        content
    )
    
    # 단순 패턴
    def fix_footnote_ref(m):
        full = m.group(0)
        num_match = re.search(r'footnote-(\d+)', full)
        if num_match:
            return f'[^{num_match.group(1)}]'
        return ''
    
    content = re.sub(
        r'\^\[([IVXLCDM]+|\d+)\]\([^)]+\)\{[^}]+\}\^',
        fix_footnote_ref,
        content
    )
    
    # 각주 정의 부분 정리
    # 1.  [I](#intro.xhtml_footnote-074-backlink){#intro.xhtml_footnote-074}. 내용
    # -> [^074]: 내용
    def fix_footnote_def(m):
        num_match = re.search(r'footnote-(\d+)', m.group(0))
        text = m.group(1).strip() if m.lastindex >= 1 else ''
        if num_match:
            return f'[^{num_match.group(1)}]: {text}'
        return m.group(0)
    
    content = re.sub(
        r'^\d+\.\s+\[[IVXLCDM]+\]\([^)]+\)\{[^}]+\}\.\s*(.*)$',
        fix_footnote_def,
        content,
        flags=re.MULTILINE
    )
    
    # 7. aria-label, role 등 HTML 속성 제거 (남은 것들)
    content = re.sub(r'\s*aria-label="[^"]*"', '', content)
    content = re.sub(r'\s*role="[^"]*"', '', content)
    
    # 8. 연속 빈 줄 정리 (3개 이상 -> 2개)
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # 9. 헤딩 뒤의 불필요한 텍스트 정리
    # # FOREWORD [DARIO AMODEI...]{.heading_breakf} -> # FOREWORD
    content = re.sub(r'^(#+\s+[A-Z][A-Z\s]+)\s+\[[^\]]+\]\{[^}]+\}', r'\1', content, flags=re.MULTILINE)
    
    # 헤딩의 [부제목] 패턴을 : 부제목 으로 변환
    # # PART 1 [WHY VIBE CODE] -> # PART 1: WHY VIBE CODE
    # ## CHAPTER 1 [THE FUTURE...] -> ## CHAPTER 1: THE FUTURE...
    content = re.sub(r'^(#+\s+(?:PART|CHAPTER)\s+\d+)\s+\[([^\]]+)\]', r'\1: \2', content, flags=re.MULTILINE)
    
    # 10. 남은 {.class} 패턴 제거
    content = re.sub(r'\{\.[\w-]+\}', '', content)
    
    # 11. 빈 div 마커 정리
    content = re.sub(r'^\s*$\n', '\n', content, flags=re.MULTILINE)
    
    # 12. 이미지 뒤에 헤딩이 바로 오면 빈 줄 추가
    content = re.sub(r'(\]\([^)]+\))\n(#)', r'\1\n\n\2', content)
    
    # 13. 목차 링크 정리: #ch08.xhtml_fig8_1 -> #fig8_1
    # 본문의 <figure id="fig8_1">과 매칭되도록
    content = re.sub(r'#(\w+)\.xhtml_', r'#', content)
    
    # 14. HTML figure 태그를 MD 형식으로 변환 (pandoc 확장 문법 사용)
    def convert_figure(m):
        full = m.group(0)
        # figure id 추출
        fig_match = re.search(r'<figure\s+id="([^"]+)"', full)
        fig_id = fig_match.group(1) if fig_match else ''
        # span id가 있으면 그것도 추출 (목차 링크와 매칭용)
        # 단, figcaption 밖에 있는 span만 사용 (page 마커 제외)
        # xhtml prefix 제거: ch08.xhtml_fig8_3 -> fig8_3
        # figure 태그와 figcaption 사이의 span만 찾기
        before_figcaption = re.split(r'<figcaption', full)[0] if '<figcaption' in full else full
        span_match = re.search(r'<span id="([^"]+)">', before_figcaption)
        if span_match:
            span_id = re.sub(r'^\w+\.xhtml_', '', span_match.group(1))
        else:
            span_id = None
        img_match = re.search(r'<img\s+src="([^"]+)"', full)
        # figcaption에서 Figure X.X: ... 형식 추출 (p 태그 포함 가능)
        cap_match = re.search(r'<figcaption>.*?((?:Figure|Table)\s+[\d.]+:[^<]+)', full, re.DOTALL)
        
        if img_match:
            src = img_match.group(1)
            caption = cap_match.group(1).strip() if cap_match else ''
            # span id가 있으면 그것을 앵커로 사용
            anchor_id = span_id if span_id else fig_id
            # 표준 HTML 앵커 사용 (MD 호환성)
            if caption:
                return f'<a id="{anchor_id}"></a>\n\n![{caption}]({src})\n\n**{caption}**'
            else:
                return f'<a id="{anchor_id}"></a>\n\n![]({src})'
        return full
    
    content = re.sub(
        r'<figure\s+id="[^"]+"[^>]*>.*?</figure>',
        convert_figure,
        content,
        flags=re.DOTALL
    )
    
    # 15. 연속 빈 줄 다시 정리
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip() + '\n'


def unfill_paragraphs(content: str) -> str:
    """문단 내 줄바꿈을 제거하여 한 줄로 만듦 (unwrap/unfill)
    
    문단 구분 기준:
    - 빈 줄
    - 헤딩 (* )
    - org 지시자 (#+, :PROPERTIES:, :END:)
    - 리스트 항목 (-, 1.)
    - 코드 블록
    - 타겟 (<<...>>)
    """
    lines = content.split('\n')
    result = []
    current_paragraph = []
    in_block = False  # #+begin_... #+end_... 블록 내부
    
    def is_structural(line):
        """구조적 요소인지 확인 (문단 구분자)"""
        stripped = line.strip()
        if not stripped:  # 빈 줄
            return True
        if stripped.startswith('* '):  # 헤딩 (* 뒤에 공백)
            return True
        if stripped.startswith('#+'):  # org 지시자
            return True
        if stripped.startswith(':') and stripped.endswith(':'):  # :PROPERTIES: 등
            return True
        if re.match(r'^[-*]\s', stripped):  # 리스트 항목
            return True
        if re.match(r'^\d+\.\s', stripped):  # 번호 리스트
            return True
        if stripped.startswith('<<') and stripped.endswith('>>'):  # 타겟
            return True
        if stripped.startswith('[[file:'):  # 이미지 링크
            return True
        return False
    
    def flush_paragraph():
        """현재 문단을 결과에 추가"""
        if current_paragraph:
            # 문단 내 줄들을 공백으로 연결
            joined = ' '.join(current_paragraph)
            result.append(joined)
            current_paragraph.clear()
    
    for line in lines:
        stripped = line.strip()
        
        # 블록 시작/끝 감지
        if stripped.lower().startswith('#+begin_'):
            in_block = True
            flush_paragraph()
            result.append(line)
            continue
        if stripped.lower().startswith('#+end_'):
            in_block = False
            result.append(line)
            continue
        
        # 블록 내부는 그대로 유지
        if in_block:
            result.append(line)
            continue
        
        # 구조적 요소면 문단 종료
        if is_structural(line):
            flush_paragraph()
            result.append(line)
        else:
            # 일반 텍스트는 문단에 추가
            current_paragraph.append(stripped)
    
    flush_paragraph()
    return '\n'.join(result)


def fix_org_anchors(content: str) -> str:
    """org 파일에서 내부 링크 수정 및 문단 정리
    
    1. 목차 링크에서 # 제거: [[#fig8_1]] -> [[fig8_1]]
    2. #+caption 앞에 <<target>> 앵커 추가
    3. 줄바꿈된 링크를 한 줄로 합침
    4. 문단 내 줄바꿈 제거 (unfill)
    """
    # 1. 목차/본문 링크에서 # 제거: [[#fig... -> [[fig...
    content = re.sub(r'\[\[#((?:fig|tab)[\d_]+)\]', r'[[\1]', content)
    
    # 2. #+caption: Figure X.X: ... 패턴 찾아서 앞에 <<target>> 추가
    def add_target(m):
        caption = m.group(1)
        id_match = re.search(r'(Figure|Table)\s+(\d+)\.(\d+)', caption)
        if id_match:
            prefix = 'fig' if id_match.group(1) == 'Figure' else 'tab'
            anchor_id = f"{prefix}{id_match.group(2)}_{id_match.group(3)}"
            return f'<<{anchor_id}>>\n#+caption: {caption}'
        return m.group(0)
    
    content = re.sub(r'#\+caption: ((?:Figure|Table)\s+[\d.]+:[^\n]+)', add_target, content)
    
    # 3. 줄바꿈된 링크를 한 줄로 합침
    def join_multiline_link(m):
        return m.group(0).replace('\n   ', ' ').replace('\n    ', ' ')
    
    content = re.sub(r'\[\[[^\]]+\]\[[^\]]*\n\s+[^\]]*\]\]', join_multiline_link, content)
    
    # 4. 문단 내 줄바꿈 제거
    content = unfill_paragraphs(content)
    
    # 5. :END: 뒤에 빈 줄 추가 (다음 문단과 분리)
    content = re.sub(r':END:\n(?!\n)', ':END:\n\n', content)
    
    return content


def main():
    if len(sys.argv) < 2:
        print("Usage: python cleanup_epub_md.py input.md [output.md]")
        print("       python cleanup_epub_md.py --fix-org input.org [output.org]")
        sys.exit(1)
    
    # org 후처리 모드
    if sys.argv[1] == '--fix-org':
        if len(sys.argv) < 3:
            print("Usage: python cleanup_epub_md.py --fix-org input.org [output.org]")
            sys.exit(1)
        input_path = Path(sys.argv[2])
        output_path = Path(sys.argv[3]) if len(sys.argv) > 3 else input_path
        content = input_path.read_text(encoding='utf-8')
        fixed = fix_org_anchors(content)
        output_path.write_text(fixed, encoding='utf-8')
        print(f"Fixed org anchors: {input_path} -> {output_path}")
        return
    
    # MD 정리 모드
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.with_stem(input_path.stem + '_clean')
    
    content = input_path.read_text(encoding='utf-8')
    cleaned = cleanup_epub_markdown(content)
    output_path.write_text(cleaned, encoding='utf-8')
    
    print(f"Cleaned: {input_path} -> {output_path}")
    print(f"Before: {len(content):,} chars, After: {len(cleaned):,} chars")


if __name__ == '__main__':
    main()

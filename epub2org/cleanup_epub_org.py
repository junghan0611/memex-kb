#!/usr/bin/env python3
"""
cleanup_epub_org.py - epub→org 변환 후 패턴별 정리 스크립트
==========================================================

epub2org 협업 워크플로우를 위한 패턴 기반 정리 도구.
각 패턴을 개별적으로 적용하여 단계별 검토 가능.

사용법:
    # 패턴 목록 보기
    python cleanup_epub_org.py --list-patterns

    # 단일 패턴 적용
    python cleanup_epub_org.py input.org --pattern G1-org -o output.org

    # 여러 패턴 순차 적용
    python cleanup_epub_org.py input.org --patterns G1-org,T2,H3

    # dry-run (변경 미리보기)
    python cleanup_epub_org.py input.org --pattern G1-org --dry-run

    # 통계만 보기
    python cleanup_epub_org.py input.org --pattern G1-org --stats

협업 방식:
    - PATTERNS.org 문서와 연동
    - 단계별 적용 → 검토 → 다음 단계
    - 에이전트가 이 스크립트와 문서를 보고 재현 가능

Changelog:
    2025-12-06  v1.0  초기 버전 (Susskind Classical Mechanics 기준)
"""

import re
import sys
import argparse
from pathlib import Path
from typing import Callable, Dict, Tuple


# =============================================================================
# 패턴 정의
# =============================================================================

def pattern_G1_org(content: str) -> Tuple[str, int]:
    """G1-org: OceanofPDF 링크 제거 (org 버전)

    입력: [[https://oceanofpdf.com][/OceanofPDF.com/]]
    출력: (제거)
    """
    pattern = r'\[\[https://oceanofpdf\.com\]\[/OceanofPDF\.com/\]\]\n?'
    matches = len(re.findall(pattern, content))
    result = re.sub(pattern, '', content)
    return result, matches


def pattern_T2(content: str) -> Tuple[str, int]:
    """T2: 페이지 목록 제거 (nav.xhtml hidden list)

    입력: 1. [[#chapter001.xhtml_pg1][1]]
          1. [[#title.xhtml_pgiii][iii]]  (로마 숫자)
          1. [[#nav.xhtml_toc001][Table of Contents]]
    출력: (제거)

    nav 블록 전체도 제거
    """
    total_matches = 0
    result = content

    # 1. 숫자 페이지: _pg123
    pattern1 = r'^\d+\. \[\[#[^\]]+_pg\d+\]\[\d+\]\]\n'
    matches1 = len(re.findall(pattern1, result, re.MULTILINE))
    result = re.sub(pattern1, '', result, flags=re.MULTILINE)
    total_matches += matches1

    # 2. 로마 숫자 페이지: _pgiii, _pgiv, _pgxi 등
    pattern2 = r'^\d+\. \[\[#[^\]]+_pg[ivxlcdm]+\]\[[ivxlcdm]+\]\]\n'
    matches2 = len(re.findall(pattern2, result, re.MULTILINE | re.IGNORECASE))
    result = re.sub(pattern2, '', result, flags=re.MULTILINE | re.IGNORECASE)
    total_matches += matches2

    # 3. TOC/네비게이션 목록: [[#nav.xhtml_toc001][...]], [[file:cover.xhtml][...]]
    pattern3 = r'^\d+\. \[\[(?:#[^\]]+_(?:toc|sec-)[^\]]*|file:[^\]]+)\]\[[^\]]+\]\]\n'
    matches3 = len(re.findall(pattern3, result, re.MULTILINE))
    result = re.sub(pattern3, '', result, flags=re.MULTILINE)
    total_matches += matches3

    # 4. brand_page 등 프론트매터 링크
    pattern4 = r'^\d+\. \[\[#[^\]]+_brand_page\]\[[^\]]+\]\]\n'
    matches4 = len(re.findall(pattern4, result, re.MULTILINE))
    result = re.sub(pattern4, '', result, flags=re.MULTILINE)
    total_matches += matches4

    # 5. nav.xhtml 관련 앵커
    pattern5 = r'<<nav\.xhtml>>\n?'
    matches5 = len(re.findall(pattern5, result))
    result = re.sub(pattern5, '', result)
    total_matches += matches5

    # 6. html nav 블록 (</nav> 포함)
    pattern6 = r'#\+begin_html\n\s*</?nav[^>]*>\n#\+end_html\n?'
    matches6 = len(re.findall(pattern6, result, re.IGNORECASE))
    result = re.sub(pattern6, '', result, flags=re.IGNORECASE)
    total_matches += matches6

    return result, total_matches


def pattern_H3(content: str) -> Tuple[str, int]:
    """H3: 헤딩 레벨 조정 (***** → ***)

    pandoc이 생성한 5레벨 헤딩을 3레벨로 조정
    ** = 챕터 (유지)
    ***** = 섹션 → ***
    """
    pattern = r'^(\*{5}) '
    matches = len(re.findall(pattern, content, re.MULTILINE))
    result = re.sub(pattern, r'*** ', content, flags=re.MULTILINE)
    return result, matches


def pattern_H4(content: str) -> Tuple[str, int]:
    """H4: :PROPERTIES: 블록 단순화

    CUSTOM_ID만 유지, CLASS 등 제거
    """
    # CLASS 속성 제거
    pattern = r'^:CLASS:.*\n'
    matches = len(re.findall(pattern, content, re.MULTILINE))
    result = re.sub(pattern, '', content, flags=re.MULTILINE)
    return result, matches


def pattern_I3(content: str) -> Tuple[str, int]:
    """I3: 이미지 경로 정규화

    ./output/media/images/ → ./images/
    ./output/media/xhtml/prh_core_assets/images/ → ./images/
    """
    patterns = [
        (r'\./output/media/images/', './images/'),
        (r'\./output/media/xhtml/prh_core_assets/images/', './images/'),
    ]

    total_matches = 0
    result = content
    for pattern, replacement in patterns:
        matches = len(re.findall(pattern, result))
        total_matches += matches
        result = re.sub(pattern, replacement, result)

    return result, total_matches


def pattern_G5(content: str) -> Tuple[str, int]:
    """G5: 연속 빈 줄 정리 (3개 이상 → 2개)"""
    pattern = r'\n{3,}'
    matches = len(re.findall(pattern, content))
    result = re.sub(pattern, '\n\n', content)
    return result, matches


def pattern_P1(content: str) -> Tuple[str, int]:
    """P1: 문단 unfill (줄바꿈 제거)

    문단 내 줄바꿈을 제거하여 한 줄로 만듦.
    구조적 요소(헤딩, 리스트, 블록 등)는 보존.
    """
    lines = content.split('\n')
    result = []
    current_paragraph = []
    in_block = False
    changes = 0

    def is_structural(line):
        stripped = line.strip()
        if not stripped:
            return True
        if stripped.startswith('* '):
            return True
        if stripped.startswith('#+'):
            return True
        if stripped.startswith(':') and stripped.endswith(':'):
            return True
        if re.match(r'^[-*]\s', stripped):
            return True
        if re.match(r'^\d+\.\s', stripped):
            return True
        if stripped.startswith('<<') and stripped.endswith('>>'):
            return True
        if stripped.startswith('[[file:') or stripped.startswith('[[./'):
            return True
        return False

    def flush_paragraph():
        nonlocal changes
        if current_paragraph:
            if len(current_paragraph) > 1:
                changes += len(current_paragraph) - 1
            joined = ' '.join(current_paragraph)
            result.append(joined)
            current_paragraph.clear()

    for line in lines:
        stripped = line.strip()

        if stripped.lower().startswith('#+begin_'):
            in_block = True
            flush_paragraph()
            result.append(line)
            continue
        if stripped.lower().startswith('#+end_'):
            in_block = False
            result.append(line)
            continue

        if in_block:
            result.append(line)
            continue

        if is_structural(line):
            flush_paragraph()
            result.append(line)
        else:
            current_paragraph.append(stripped)

    flush_paragraph()
    return '\n'.join(result), changes


def pattern_P2(content: str) -> Tuple[str, int]:
    """P2: :END: 뒤 빈 줄 추가 (문단 분리)"""
    pattern = r':END:\n(?!\n)'
    matches = len(re.findall(pattern, content))
    result = re.sub(pattern, ':END:\n\n', content)
    return result, matches


def pattern_L5(content: str) -> Tuple[str, int]:
    """L5: xhtml 앵커 제거

    pandoc 변환 시 생성되는 xhtml 앵커 제거.
    헤딩과 본문 모두에서 제거.

    입력: ** <<chapter001.xhtml_page_1>>Lecture 1
    출력: ** Lecture 1

    입력: between the state <<chapter001.xhtml_page_2>>of a system
    출력: between the state of a system
    """
    # <<*.xhtml*>> 패턴 제거 (chapter, prologue, preface, toc 등 모두)
    pattern = r'<<[a-z]+[0-9]*\.xhtml[^>]*>>'
    matches = len(re.findall(pattern, content))
    result = re.sub(pattern, '', content)
    return result, matches


def pattern_S1(content: str) -> Tuple[str, int]:
    r"""S1: 수식 이미지 → org LaTeX 치환

    인라인 수식 이미지를 org-mode LaTeX 형식으로 치환.
    org-mode 선호 형식: \( \pi \) (공백 허용)

    입력: [[./images/pi.png]]
    출력: \(\pi\)
    """
    # 그리스 문자 매핑
    greek_letters = {
        'alpha': r'\alpha',
        'beta': r'\beta',
        'gamma': r'\gamma',
        'delta': r'\delta',
        'epsilon': r'\epsilon',
        'zeta': r'\zeta',
        'eta': r'\eta',
        'theta': r'\theta',
        'iota': r'\iota',
        'kappa': r'\kappa',
        'lambda': r'\lambda',
        'mu': r'\mu',
        'nu': r'\nu',
        'xi': r'\xi',
        'pi': r'\pi',
        'rho': r'\rho',
        'sigma': r'\sigma',
        'tau': r'\tau',
        'upsilon': r'\upsilon',
        'phi': r'\phi',
        'chi': r'\chi',
        'psi': r'\psi',
        'omega': r'\omega',
        # 대문자
        'Gamma': r'\Gamma',
        'Delta': r'\Delta',
        'Theta': r'\Theta',
        'Lambda': r'\Lambda',
        'Xi': r'\Xi',
        'Pi': r'\Pi',
        'Sigma': r'\Sigma',
        'Phi': r'\Phi',
        'Psi': r'\Psi',
        'Omega': r'\Omega',
    }

    # 미분 표기 (dot notation)
    dot_symbols = {
        'xdot': r'\dot{x}',
        'ydot': r'\dot{y}',
        'pdot': r'\dot{p}',
        'qdot': r'\dot{q}',
        'rdot': r'\dot{r}',
        'thetadot': r'\dot{\theta}',
        'phidot': r'\dot{\phi}',
        'Ldot': r'\dot{L}',
        'upperxdot': r'\dot{X}',
    }

    # 특수 기호
    special_symbols = {
        'half': r'\frac{1}{2}',
        'unequal': r'\neq',
        'pi2': r'2\pi',
        'alphabeta': r'\alpha + \beta',
    }

    # 모든 매핑 합치기
    all_symbols = {}
    all_symbols.update(greek_letters)
    all_symbols.update(dot_symbols)
    all_symbols.update(special_symbols)

    total_matches = 0
    result = content

    for img_name, latex in all_symbols.items():
        # [[./images/sigma.png]] 또는 [[./images/sigma.jpg]] 패턴
        for ext in ['png', 'jpg']:
            pattern = rf'\[\[\.\/images\/{re.escape(img_name)}\.{ext}\]\]'
            matches = len(re.findall(pattern, result))
            if matches > 0:
                # org-mode 인라인 LaTeX: \( ... \)
                # lambda를 사용해 replacement 문자열 이스케이프 문제 회피
                org_latex = f'\\({latex}\\)'
                result = re.sub(pattern, lambda m: org_latex, result)
                total_matches += matches

    return result, total_matches


# =============================================================================
# 패턴 레지스트리
# =============================================================================

PATTERNS: Dict[str, Tuple[Callable, str]] = {
    'G1-org': (pattern_G1_org, 'OceanofPDF 링크 제거 (org)'),
    'T2': (pattern_T2, '페이지 목록 제거'),
    'H3': (pattern_H3, '헤딩 레벨 조정 (*****→***)'),
    'H4': (pattern_H4, ':PROPERTIES: 단순화'),
    'I3': (pattern_I3, '이미지 경로 정규화'),
    'G5': (pattern_G5, '연속 빈 줄 정리'),
    'P1': (pattern_P1, '문단 unfill'),
    'P2': (pattern_P2, ':END: 뒤 빈 줄'),
    'L5': (pattern_L5, 'xhtml 앵커 제거'),
    'S1': (pattern_S1, '수식 이미지 → LaTeX 치환'),
}


# =============================================================================
# CLI
# =============================================================================

def list_patterns():
    """사용 가능한 패턴 목록 출력"""
    print("사용 가능한 패턴:")
    print("-" * 50)
    for name, (func, desc) in PATTERNS.items():
        print(f"  {name:10} - {desc}")
    print("-" * 50)


def apply_pattern(content: str, pattern_name: str, dry_run: bool = False) -> Tuple[str, int]:
    """단일 패턴 적용"""
    if pattern_name not in PATTERNS:
        print(f"[ERROR] 알 수 없는 패턴: {pattern_name}")
        list_patterns()
        sys.exit(1)

    func, desc = PATTERNS[pattern_name]
    result, matches = func(content)

    print(f"[{pattern_name}] {desc}: {matches}개 처리")

    if dry_run:
        return content, matches
    return result, matches


def main():
    parser = argparse.ArgumentParser(
        description='epub→org 변환 후 패턴별 정리',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python cleanup_epub_org.py --list-patterns
  python cleanup_epub_org.py input.org --pattern G1-org -o output.org
  python cleanup_epub_org.py input.org --patterns G1-org,T2,H3
  python cleanup_epub_org.py input.org --pattern G1-org --dry-run
        """
    )

    parser.add_argument('input', nargs='?', help='입력 org 파일')
    parser.add_argument('-o', '--output', help='출력 파일 (없으면 덮어쓰기)')
    parser.add_argument('-p', '--pattern', help='적용할 패턴 (단일)')
    parser.add_argument('--patterns', help='적용할 패턴들 (콤마 구분)')
    parser.add_argument('--list-patterns', action='store_true', help='패턴 목록 보기')
    parser.add_argument('--dry-run', action='store_true', help='변경 미리보기 (실제 적용 안함)')
    parser.add_argument('--stats', action='store_true', help='통계만 보기')

    args = parser.parse_args()

    if args.list_patterns:
        list_patterns()
        return 0

    if not args.input:
        parser.print_help()
        return 1

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[ERROR] 파일 없음: {input_path}")
        return 1

    content = input_path.read_text(encoding='utf-8')
    original_len = len(content)

    # 패턴 목록 결정
    pattern_names = []
    if args.pattern:
        pattern_names = [args.pattern]
    elif args.patterns:
        pattern_names = [p.strip() for p in args.patterns.split(',')]
    else:
        print("[ERROR] --pattern 또는 --patterns 필요")
        return 1

    print(f"입력: {input_path} ({original_len:,} chars)")
    print(f"패턴: {', '.join(pattern_names)}")
    print("-" * 50)

    # 패턴 순차 적용
    total_matches = 0
    for pattern_name in pattern_names:
        content, matches = apply_pattern(content, pattern_name, args.dry_run or args.stats)
        total_matches += matches

    print("-" * 50)
    print(f"총 변경: {total_matches}개")
    print(f"크기: {original_len:,} → {len(content):,} chars ({len(content) - original_len:+,})")

    # 결과 저장
    if not args.dry_run and not args.stats:
        output_path = Path(args.output) if args.output else input_path
        output_path.write_text(content, encoding='utf-8')
        print(f"저장: {output_path}")

    return 0


if __name__ == '__main__':
    sys.exit(main())

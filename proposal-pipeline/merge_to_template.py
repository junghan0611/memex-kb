#!/usr/bin/env python3
"""
Template Org + Content Org → Merged Org 병합기

template.org (HWPX에서 추출, HWPX_IDX + 플레이스홀더)와
content.org (MD에서 변환, 실제 내용)를 병합합니다.

알고리즘:
  1. template Org 파싱 → 요소 리스트 (HWPX_IDX 보유)
  2. content Org 파싱 → 헤딩별 내용 트리
  3. 헤딩 매칭 (Level 1-2: 절 번호 정규화, Level 3+: 순서 기반)
  4. 매칭된 헤딩의 content 텍스트를 template 슬롯에 채움
  5. 매칭 리포트 출력

사용법:
    python merge_to_template.py template.org content.org -o merged.org
"""

import argparse
import logging
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# Org 파서 (경량: merge 전용)
# ============================================================
@dataclass
class OrgNode:
    """Org 요소 (헤딩 또는 문단)"""
    kind: str = ""          # "heading", "paragraph"
    level: int = 0          # 헤딩 레벨 (1-7)
    text: str = ""          # 헤딩 제목 또는 문단 텍스트
    hwpx_idx: Optional[int] = None
    children: List['OrgNode'] = field(default_factory=list)
    # 원본 라인 (template 출력용)
    raw_lines: List[str] = field(default_factory=list)


def parse_org_tree(org_path: Path) -> Tuple[List[OrgNode], str, str]:
    """Org 파일을 파싱하여 플랫 요소 리스트 + 메타데이터 반환"""
    with open(org_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    elements = []
    title = ""
    date = ""
    i = 0
    pending_hwpx_idx: Optional[int] = None

    while i < len(lines):
        line = lines[i]

        # 메타데이터
        if line.startswith('#+TITLE:'):
            title = line[8:].strip()
            i += 1; continue
        elif line.startswith('#+DATE:'):
            date = line[7:].strip()
            i += 1; continue
        elif line.startswith('#+STARTUP:'):
            i += 1; continue

        # HWPX index
        hwpx_match = re.match(r'^#\+HWPX:\s*(\d+)', line)
        if hwpx_match:
            pending_hwpx_idx = int(hwpx_match.group(1))
            i += 1; continue

        # BEGIN 블록 스킵 (테이블, 예제 등 — template에서는 그대로 유지)
        if line.strip().startswith('#+BEGIN_'):
            block_start = i
            block_type = line.strip().split()[0]  # #+BEGIN_SRC 등
            end_marker = block_type.replace('BEGIN', 'END')
            raw = [line]
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(end_marker):
                raw.append(lines[i])
                i += 1
            if i < len(lines):
                raw.append(lines[i])
                i += 1
            node = OrgNode(kind="block", text='\n'.join(raw), hwpx_idx=pending_hwpx_idx, raw_lines=raw)
            elements.append(node)
            pending_hwpx_idx = None
            continue

        # 기타 #+ 지시자 스킵
        if line.startswith('#+'):
            i += 1; continue

        # 헤딩
        heading_match = re.match(r'^(\*+)\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2)
            raw = [line]

            hwpx_idx_val = None
            # PROPERTIES 블록 읽기
            if i + 1 < len(lines) and lines[i + 1].strip() == ':PROPERTIES:':
                j = i + 1
                raw.append(lines[j])
                j += 1
                while j < len(lines) and lines[j].strip() != ':END:':
                    raw.append(lines[j])
                    idx_match = re.match(r'\s*:HWPX_IDX:\s*(\d+)', lines[j])
                    if idx_match:
                        hwpx_idx_val = int(idx_match.group(1))
                    j += 1
                if j < len(lines):
                    raw.append(lines[j])  # :END:
                    j += 1
                i = j
            else:
                i += 1

            node = OrgNode(kind="heading", level=level, text=heading_text,
                           hwpx_idx=hwpx_idx_val, raw_lines=raw)
            elements.append(node)
            pending_hwpx_idx = None
            continue

        # 빈 줄
        if not line.strip():
            i += 1; continue

        # 일반 문단 (# 주석 포함)
        node = OrgNode(kind="paragraph", text=line.strip(),
                       hwpx_idx=pending_hwpx_idx, raw_lines=[line])
        elements.append(node)
        pending_hwpx_idx = None
        i += 1

    return elements, title, date


# ============================================================
# 헤딩 정규화 (매칭용)
# ============================================================
def normalize_section_number(text: str) -> str:
    """절 번호 정규화: '4-1.' → '4.1', '7.1' → '7.1' 등"""
    # 선행 글머리표 제거
    text = re.sub(r'^[□○o\-⋅·]\s*', '', text.strip())

    # 절 번호 추출 (4-1., 7.1, 7.1.1 등)
    match = re.match(r'^(\d+)[-.](\d+)(?:[-.]\d+)*\.?\s', text)
    if match:
        # 하이픈을 점으로 통일
        num_part = re.match(r'^([\d\-\.]+)', text).group(1)
        normalized = num_part.replace('-', '.').rstrip('.')
        return normalized

    # 장 번호 (4., 7. 등)
    match = re.match(r'^(\d+)\.\s', text)
    if match:
        return match.group(1)

    return ""


def is_placeholder(text: str) -> bool:
    """템플릿 플레이스홀더 여부 판별"""
    # "템플릿1", "템플릿2" 등
    text = re.sub(r'^[□○o\-⋅·]\s*', '', text.strip())
    return bool(re.match(r'^템플릿\d+$', text.strip()))


def get_heading_key(text: str) -> str:
    """헤딩의 매칭 키 생성"""
    # 글머리표 제거
    clean = re.sub(r'^[□○o\-⋅·]\s*', '', text.strip())
    # 절 번호 정규화
    num = normalize_section_number(clean)
    if num:
        return num
    return clean


# ============================================================
# 콘텐츠 Org → 섹션 트리
# ============================================================
@dataclass
class ContentSection:
    """콘텐츠 Org의 섹션 (헤딩 + 하위 내용)"""
    heading: OrgNode
    key: str = ""
    paragraphs: List[OrgNode] = field(default_factory=list)
    subsections: List['ContentSection'] = field(default_factory=list)


def build_content_tree(elements: List[OrgNode]) -> List[ContentSection]:
    """플랫 요소 리스트를 헤딩 기반 트리로 구성"""
    sections = []
    stack: List[Tuple[int, ContentSection]] = []  # (level, section)

    for elem in elements:
        if elem.kind == "heading":
            section = ContentSection(
                heading=elem,
                key=get_heading_key(elem.text)
            )

            # 스택에서 현재 레벨보다 깊거나 같은 것 제거
            while stack and stack[-1][0] >= elem.level:
                stack.pop()

            if stack:
                stack[-1][1].subsections.append(section)
            else:
                sections.append(section)

            stack.append((elem.level, section))
        else:
            # 문단/블록은 현재 섹션에 추가
            if stack:
                stack[-1][1].paragraphs.append(elem)
            # 헤딩 전 문단은 무시 (전문 등)

    return sections


def flatten_content_sections(sections: List[ContentSection]) -> List[ContentSection]:
    """섹션 트리를 플랫 리스트로"""
    result = []
    for sec in sections:
        result.append(sec)
        result.extend(flatten_content_sections(sec.subsections))
    return result


# ============================================================
# 메인 병합 로직
# ============================================================
def merge_template_content(
    template_elements: List[OrgNode],
    content_elements: List[OrgNode],
    template_title: str,
    template_date: str,
) -> Tuple[str, Dict]:
    """template Org 구조 + content Org 텍스트 → merged Org

    Returns:
        (merged_org_text, report_dict)
    """
    # 콘텐츠를 섹션 트리로 구성
    content_tree = build_content_tree(content_elements)
    content_flat = flatten_content_sections(content_tree)

    # 콘텐츠 섹션을 key로 인덱싱
    content_by_key: Dict[str, ContentSection] = {}
    for sec in content_flat:
        if sec.key:
            content_by_key[sec.key] = sec

    logger.info(f"콘텐츠 섹션: {len(content_flat)}개 (key 있음: {len(content_by_key)}개)")
    for key in list(content_by_key.keys())[:10]:
        logger.debug(f"  key='{key}' → {content_by_key[key].heading.text[:40]}")

    # 매칭 리포트
    report = {
        'matched_headings': [],
        'unmatched_template': [],
        'unmatched_content': [],
        'placeholder_replaced': [],
        'paragraph_mapped': [],
    }

    # template 요소 순회하며 병합
    output_lines = []
    output_lines.append(f"#+TITLE: {template_title}")
    output_lines.append(f"#+DATE: {template_date}")
    output_lines.append("#+STARTUP: overview")
    output_lines.append("")

    # 현재 매칭된 콘텐츠 섹션 추적
    current_content_section: Optional[ContentSection] = None
    content_para_idx = 0  # 현재 섹션 내 문단 인덱스
    used_content_keys = set()

    for t_elem in template_elements:
        if t_elem.kind == "heading":
            t_key = get_heading_key(t_elem.text)

            if is_placeholder(t_elem.text):
                # 플레이스홀더 → 현재 섹션의 다음 문단 슬롯에서 가져옴
                if current_content_section and content_para_idx < len(current_content_section.paragraphs):
                    para = current_content_section.paragraphs[content_para_idx]
                    content_para_idx += 1

                    # 플레이스홀더 텍스트를 콘텐츠 텍스트로 교체
                    # 글머리표 접두어는 유지
                    bullet = _extract_bullet(t_elem.text)
                    new_text = f"{bullet}{para.text}" if bullet else para.text

                    stars = '*' * t_elem.level
                    output_lines.append(f"{stars} {new_text}")
                    if t_elem.hwpx_idx is not None:
                        output_lines.append(":PROPERTIES:")
                        output_lines.append(f":HWPX_IDX: {t_elem.hwpx_idx}")
                        output_lines.append(":END:")
                    output_lines.append("")

                    report['placeholder_replaced'].append({
                        'template': t_elem.text,
                        'content': new_text[:60],
                        'hwpx_idx': t_elem.hwpx_idx,
                    })
                else:
                    # 콘텐츠 부족 → 플레이스홀더 그대로 유지
                    for raw in t_elem.raw_lines:
                        output_lines.append(raw)
                    output_lines.append("")
                    report['unmatched_template'].append({
                        'text': t_elem.text,
                        'hwpx_idx': t_elem.hwpx_idx,
                        'reason': 'no content paragraph available',
                    })
                continue

            # 비-플레이스홀더 헤딩: 키 기반 매칭 시도
            matched_section = None

            if t_key:
                # 직접 키 매칭
                if t_key in content_by_key:
                    matched_section = content_by_key[t_key]
                else:
                    # 유사 키 검색 (4.1 ↔ 7.1 등 — 장 번호가 다를 수 있음)
                    t_sub = t_key.split('.', 1)[1] if '.' in t_key else None
                    for c_key, c_sec in content_by_key.items():
                        c_sub = c_key.split('.', 1)[1] if '.' in c_key else None
                        if t_sub and c_sub and t_sub == c_sub:
                            matched_section = c_sec
                            break

            if matched_section:
                used_content_keys.add(matched_section.key)
                current_content_section = matched_section
                content_para_idx = 0

                report['matched_headings'].append({
                    'template': t_elem.text[:50],
                    'content': matched_section.heading.text[:50],
                    'hwpx_idx': t_elem.hwpx_idx,
                })

                # 헤딩 텍스트는 template 것을 유지 (HWPX 서식 보존)
                for raw in t_elem.raw_lines:
                    output_lines.append(raw)
                output_lines.append("")
            else:
                # 매칭 실패 → template 그대로 출력
                current_content_section = None
                content_para_idx = 0

                for raw in t_elem.raw_lines:
                    output_lines.append(raw)
                output_lines.append("")

                if t_key:
                    report['unmatched_template'].append({
                        'text': t_elem.text[:50],
                        'hwpx_idx': t_elem.hwpx_idx,
                        'reason': f'no content match for key={t_key}',
                    })

        elif t_elem.kind == "paragraph":
            # 문단: 현재 콘텐츠 섹션에서 순서대로 문단 매핑
            if current_content_section and content_para_idx < len(current_content_section.paragraphs):
                para = current_content_section.paragraphs[content_para_idx]
                content_para_idx += 1

                if t_elem.hwpx_idx is not None:
                    output_lines.append(f"#+HWPX: {t_elem.hwpx_idx}")
                output_lines.append(para.text)
                output_lines.append("")

                report['paragraph_mapped'].append({
                    'template': t_elem.text[:40],
                    'content': para.text[:40],
                    'hwpx_idx': t_elem.hwpx_idx,
                })
            else:
                # 콘텐츠 부족 → template 그대로
                if t_elem.hwpx_idx is not None:
                    output_lines.append(f"#+HWPX: {t_elem.hwpx_idx}")
                output_lines.append(t_elem.text)
                output_lines.append("")

        elif t_elem.kind == "block":
            # 블록 (테이블 등)은 그대로
            if t_elem.hwpx_idx is not None:
                output_lines.append(f"#+HWPX: {t_elem.hwpx_idx}")
            for raw in t_elem.raw_lines:
                output_lines.append(raw)
            output_lines.append("")

    # 미사용 콘텐츠 섹션 리포트
    for sec in content_flat:
        if sec.key and sec.key not in used_content_keys:
            report['unmatched_content'].append({
                'key': sec.key,
                'text': sec.heading.text[:50],
            })

    return '\n'.join(output_lines), report


def _extract_bullet(text: str) -> str:
    """헤딩 텍스트에서 글머리표 접두어 추출"""
    match = re.match(r'^([□○o\-⋅·]\s*)', text)
    if match:
        return match.group(1)
    return ""


def print_report(report: Dict):
    """매칭 리포트 출력"""
    print("\n" + "=" * 60)
    print("MERGE REPORT")
    print("=" * 60)

    matched = len(report['matched_headings'])
    placeholders = len(report['placeholder_replaced'])
    paragraphs = len(report['paragraph_mapped'])
    unmatched_t = len(report['unmatched_template'])
    unmatched_c = len(report['unmatched_content'])

    print(f"\n  헤딩 매칭: {matched}개")
    print(f"  플레이스홀더 교체: {placeholders}개")
    print(f"  문단 매핑: {paragraphs}개")
    print(f"  미매칭 (template): {unmatched_t}개")
    print(f"  미매칭 (content): {unmatched_c}개")

    if report['matched_headings']:
        print(f"\n--- 매칭된 헤딩 ---")
        for m in report['matched_headings']:
            print(f"  [{m.get('hwpx_idx', '?')}] T: {m['template']}")
            print(f"        C: {m['content']}")

    if report['placeholder_replaced']:
        print(f"\n--- 교체된 플레이스홀더 ---")
        for p in report['placeholder_replaced']:
            print(f"  [{p.get('hwpx_idx', '?')}] {p['template']} → {p['content']}")

    if report['paragraph_mapped']:
        print(f"\n--- 매핑된 문단 ---")
        for p in report['paragraph_mapped']:
            print(f"  [{p.get('hwpx_idx', '?')}] T: {p['template']}")
            print(f"        C: {p['content']}")

    if report['unmatched_template']:
        print(f"\n--- 미매칭 (template 슬롯) ---")
        for u in report['unmatched_template']:
            print(f"  [{u.get('hwpx_idx', '?')}] {u['text']} — {u['reason']}")

    if report['unmatched_content']:
        print(f"\n--- 미매칭 (content 섹션) ---")
        for u in report['unmatched_content']:
            print(f"  key={u['key']} — {u['text']}")

    print("=" * 60)


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description='Template Org + Content Org → Merged Org 병합기',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
    python merge_to_template.py ch4-template.org ch4-content.org -o ch4-merged.org
"""
    )
    parser.add_argument('template', help='템플릿 Org 파일 (HWPX에서 추출)')
    parser.add_argument('content', help='콘텐츠 Org 파일 (MD에서 변환)')
    parser.add_argument('-o', '--output', help='출력 Org 파일')
    parser.add_argument('-v', '--verbose', action='store_true', help='상세 로그')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    template_path = Path(args.template)
    content_path = Path(args.content)
    output_path = Path(args.output) if args.output else template_path.with_name(
        template_path.stem.replace('-template', '-merged') + '.org'
    )

    logger.info(f"Template: {template_path}")
    logger.info(f"Content:  {content_path}")
    logger.info(f"Output:   {output_path}")

    # 파싱
    t_elements, t_title, t_date = parse_org_tree(template_path)
    c_elements, c_title, c_date = parse_org_tree(content_path)

    t_headings = sum(1 for e in t_elements if e.kind == "heading")
    t_paras = sum(1 for e in t_elements if e.kind == "paragraph")
    c_headings = sum(1 for e in c_elements if e.kind == "heading")
    c_paras = sum(1 for e in c_elements if e.kind == "paragraph")

    logger.info(f"Template: {t_headings} headings, {t_paras} paragraphs")
    logger.info(f"Content:  {c_headings} headings, {c_paras} paragraphs")

    # 병합
    merged_text, report = merge_template_content(t_elements, c_elements, t_title, t_date)

    # 저장
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(merged_text)
    logger.info(f"Merged 저장: {output_path}")

    # 리포트
    print_report(report)


if __name__ == '__main__':
    main()

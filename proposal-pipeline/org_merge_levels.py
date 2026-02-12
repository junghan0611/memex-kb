#!/usr/bin/env python3
"""Org Level 6→5 통합 후처리

Org 파일의 Level 6 헤딩을 Level 5로 변환합니다.
md_to_org.py → merge_chapters.py 이후 실행하는 파이프라인 단계.

변환 패턴:
  1a. L5 부모(이름에 ':' 없음, 본문 없음) → 이름 합치기, 부모 제거
      ***** - 소프트센서 + ****** ·문제 제기: XXX
      → ***** - 소프트센서: 문제 제기 — XXX

  1b. L5 부모(이름에 ':' 있음 또는 본문 있음) → 부모 유지, 자식 승격
      ***** - 에너지·생활: 설명 + ****** ·세부항목
      → ***** - 에너지·생활: 설명 / ***** - 세부항목

  2.  L5 부모 없음 (L4 바로 아래) → 단순 승격
      ****** ·항목 → ***** - 항목

사용법:
    python org_merge_levels.py input.org              # in-place
    python org_merge_levels.py input.org -o output.org # 별도 출력
"""
import argparse
import re
import sys


def parse_headings(lines):
    """모든 헤딩의 라인번호, 레벨, 텍스트를 파싱"""
    headings = []
    for i, line in enumerate(lines):
        m = re.match(r'^(\*+)\s+(.+)', line.rstrip('\n'))
        if m:
            headings.append({
                'idx': i,
                'level': len(m.group(1)),
                'text': m.group(2).strip()
            })
    return headings


def find_l5_parents(headings):
    """각 L6 헤딩의 L5 부모를 찾고, 부모 정보를 수집"""
    # L6 → L5 부모 연결
    for i, h in enumerate(headings):
        h['parent5'] = None
        if h['level'] == 6:
            for j in range(i - 1, -1, -1):
                if headings[j]['level'] <= 5:
                    if headings[j]['level'] == 5:
                        h['parent5'] = headings[j]
                    break
    return headings


def analyze_parents(headings, lines):
    """L5 부모의 패턴(1a/1b) 결정"""
    parent_info = {}
    for h in headings:
        if h['level'] == 6 and h['parent5']:
            p = h['parent5']
            if p['idx'] not in parent_info:
                p_name = re.sub(r'^-\s*', '', p['text'])
                first_child_idx = h['idx']

                # 부모와 첫 자식 사이 본문 존재 여부
                has_content = False
                in_props = False
                for li in range(p['idx'] + 1, first_child_idx):
                    s = lines[li].strip()
                    if s == ':PROPERTIES:':
                        in_props = True
                    elif s == ':END:':
                        in_props = False
                    elif in_props:
                        pass
                    elif s == '' or s.startswith('#'):
                        pass
                    else:
                        has_content = True
                        break

                has_colon = ':' in p_name
                pattern = '1a' if (not has_content and not has_colon) else '1b'

                parent_info[p['idx']] = {
                    'name': p_name,
                    'has_content': has_content,
                    'has_colon': has_colon,
                    'pattern': pattern
                }
    return parent_info


def build_skip_set(parent_info, lines):
    """Pattern 1a 부모의 헤딩+PROPERTIES+빈줄을 스킵 대상으로 수집"""
    skip = set()
    for p_idx, info in parent_info.items():
        if info['pattern'] == '1a':
            skip.add(p_idx)
            j = p_idx + 1
            while j < len(lines):
                s = lines[j].strip()
                if s.startswith(':') or s == '':
                    skip.add(j)
                    j += 1
                else:
                    break
    return skip


def merge_child_text(p_name, child_raw):
    """부모 이름과 자식 텍스트를 합쳐 새 헤딩 생성"""
    child_text = child_raw
    # 중복 접두사 제거 (크로스모달: 크로스모달 학습의... → 크로스모달: 학습의...)
    if child_text.startswith(p_name + ' '):
        child_text = child_text[len(p_name) + 1:]
    elif child_text == p_name:
        pass  # 동일하면 유지

    # 자식이 ': detail' 패턴인 경우 분리
    colon_m = re.match(r'^([^:]+):\s*(.+)', child_text)
    if colon_m:
        topic = colon_m.group(1).strip()
        detail = colon_m.group(2).strip()
        return f'{p_name}: {topic} — {detail}'
    else:
        return f'{p_name}: {child_text}'


def transform(lines):
    """메인 변환: Level 6 → Level 5 통합"""
    headings = parse_headings(lines)
    headings = find_l5_parents(headings)
    parent_info = analyze_parents(headings, lines)
    skip_lines = build_skip_set(parent_info, lines)

    result = []
    stats = {'1a': 0, '1b': 0, '2': 0, 'parents_removed': 0}

    for i, line in enumerate(lines):
        if i in skip_lines:
            if lines[i].rstrip('\n').startswith('*****'):
                stats['parents_removed'] += 1
            continue

        stripped = line.rstrip('\n')
        m6 = re.match(r'^(\*{6})\s+·(.+)', stripped)

        if m6:
            child_raw = m6.group(2).strip()
            h = next((hh for hh in headings if hh['idx'] == i and hh['level'] == 6), None)

            if h and h.get('parent5'):
                info = parent_info.get(h['parent5']['idx'])
                if info and info['pattern'] == '1a':
                    new_text = merge_child_text(info['name'], child_raw)
                    result.append(f'***** - {new_text}\n')
                    stats['1a'] += 1
                else:
                    result.append(f'***** - {child_raw}\n')
                    stats['1b'] += 1
            else:
                result.append(f'***** - {child_raw}\n')
                stats['2'] += 1
        else:
            result.append(line)

    # H:6 → H:5 (#+options 라인)
    final = []
    for line in result:
        if 'H:6' in line and re.match(r'^#\+options:', line, re.IGNORECASE):
            final.append(line.replace('H:6', 'H:5'))
        else:
            final.append(line)

    return final, stats


def main():
    parser = argparse.ArgumentParser(
        description='Org Level 6→5 통합 후처리',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('input', help='입력 Org 파일')
    parser.add_argument('-o', '--output', help='출력 Org 파일 (미지정 시 in-place)')
    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # L6 존재 여부 확인
    l6_count = sum(1 for l in lines if re.match(r'^\*{6}\s+', l))
    if l6_count == 0:
        print(f"  Level 6 헤딩 없음 — 변환 불필요 ({args.input})")
        return

    final, stats = transform(lines)
    output_path = args.output or args.input

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(final)

    total = stats['1a'] + stats['1b'] + stats['2']
    print(f"  Level 6→5 통합: {total}건 (합침:{stats['1a']}, 승격:{stats['1b']+stats['2']}, 부모제거:{stats['parents_removed']})")
    print(f"  {len(lines)}줄 → {len(final)}줄 ({len(final)-len(lines):+d})")


if __name__ == '__main__':
    main()

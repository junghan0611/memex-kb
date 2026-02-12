#!/usr/bin/env python3
"""Phase 1: 제안서 MD 뼈대 정비"""
import re, sys

def strip_heading_number(text):
    """H3+ 헤딩 텍스트에서 번호 제거. 1.1.1, 2.3.4-1, 2-1-1., A. 등"""
    return re.sub(r'^([A-Z\d]+[\.\-][\d\.\-]*\.?)\s+', '', text)

def is_caption(s):
    """<캡션> 패턴 판별 (HTML 태그/주석 제외)"""
    if len(s) < 3 or s[0] != '<' or s[-1] != '>':
        return False
    if s.startswith('<!--'):
        return False
    if re.match(r'^</?[a-z]', s):
        return False
    return True

def extract_caption(s):
    m = re.match(r'^<(.+)>$', s)
    return m.group(1).strip() if m else None

def main():
    if len(sys.argv) < 2:
        print(f"사용법: {sys.argv[0]} input.md [output.md]")
        sys.exit(1)
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path

    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    result = []
    i = 0
    prev_hr = False
    stats = {'bold_dot': 0, 'hr_removed': 0, 'heading_stripped': 0,
             'img_caption': 0, 'standalone_caption': 0, 'bullet': 0}

    while i < len(lines):
        line = lines[i]

        # === 1. **·** → · ===
        if '**·**' in line:
            line = line.replace('**·**', '·')
            stats['bold_dot'] += 1

        stripped = line.strip()

        # === 2. 수평선 중복 제거 ===
        if stripped == '---':
            if prev_hr:
                stats['hr_removed'] += 1
                i += 1
                continue
            prev_hr = True
        elif stripped:
            prev_hr = False

        # === 3. H3+ 번호 제거 ===
        h_match = re.match(r'^(#{3,})\s+(.+)$', line.rstrip())
        if h_match:
            hashes, text = h_match.group(1), h_match.group(2)
            new_text = text

            # *italic*
            it = re.match(r'^\*([^*]+)\*$', text)
            if it:
                inner = strip_heading_number(it.group(1))
                if inner != it.group(1):
                    new_text = f'*{inner}*'
            # **bold**
            elif text.startswith('**') and text.endswith('**'):
                inner = text[2:-2]
                s = strip_heading_number(inner)
                if s != inner:
                    new_text = f'**{s}**'
            # plain
            else:
                new_text = strip_heading_number(text)

            if new_text != text:
                line = f'{hashes} {new_text}\n'
                stats['heading_stripped'] += 1

        stripped = line.strip()

        # === 4. 이미지 + 캡션 병합 ===
        if re.match(r'^!\[', stripped):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and is_caption(lines[j].strip()):
                caption = extract_caption(lines[j].strip())
                img_m = re.match(r'!\[.*?\]\(([^)]+)\)', stripped)
                if caption and img_m:
                    result.append(f'![{caption}]({img_m.group(1)})\n')
                    stats['img_caption'] += 1
                    i = j + 1
                    continue
            result.append(line)
            i += 1
            continue

        # === 5. 독립 캡션 ===
        if is_caption(stripped):
            caption = extract_caption(stripped)
            if caption:
                result.append(f'*{caption}*\n')
                stats['standalone_caption'] += 1
                i += 1
                continue

        # === 6. 불릿 정리 (• → -) ===
        if '•' in line:
            stats['bullet'] += 1
            if stripped.startswith('|'):
                line = line.replace('<br>•', '<br>-')
                line = re.sub(r'\|\s*•\s*', '| - ', line)
                line = line.replace(' • ', '<br>- ')
                if '•' in line:
                    line = line.replace('•', '-')
            else:
                line = line.replace('• ', '- ')
                if '•' in line:
                    line = line.replace('•', '- ')

        result.append(line)
        i += 1

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(result)

    print(f"원본: {len(lines)}줄 → 결과: {len(result)}줄")
    for k, v in stats.items():
        if v > 0:
            print(f"  {k}: {v}건")

if __name__ == '__main__':
    main()

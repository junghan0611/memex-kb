#!/usr/bin/env python3
"""
build_master_md.py
5개 MD 소스 → 1개 통합 MD (제안서-통합-5장.md)
BUILD-INSTRUCTIONS.md 기반 자동 조립 스크립트

원칙:
- 모든 소스 텍스트 누락 없이 배치
- 미배치 텍스트는 DUMMY 섹션으로 뒤에 모음
- 헤딩 번호만 HWP 5장 양식에 맞게 변환
"""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MEMEX_KB_DIR = SCRIPT_DIR.parent
MD_SOURCE = MEMEX_KB_DIR / "output" / "kiat-proposal"
OUTPUT_DIR = MEMEX_KB_DIR / "output" / "proposal-org"
OUTPUT_FILE = OUTPUT_DIR / "제안서-통합-5장.md"

FILES = {
    "06": MD_SOURCE / "06--1.-연구개발과제의-배경-및-필요성.md",
    "08": MD_SOURCE / "08--2.-연구개발과제의-목표-및-성과지표.md",
    "09": MD_SOURCE / "09--3.-기술개발내용-및-로드맵.md",
    "10": MD_SOURCE / "10--6장.-연구개발-추진체계-및-위험관리.md",
    "11": MD_SOURCE / "11--7.-연구개발성과의-활용방안-및-사업화계획.md",
}

SEP = "\n---\n\n"


# ── 유틸리티 ──

def read_file(key):
    with open(FILES[key], "r", encoding="utf-8") as f:
        lines = f.readlines()
    return {i + 1: line for i, line in enumerate(lines)}


def get_text(src, key, start, end, used):
    """라인 범위 추출 + 사용 표시"""
    for i in range(start, end + 1):
        used[key].add(i)
    return "".join(src[key].get(i, "") for i in range(start, end + 1))


def xform(text, rules):
    """정규식 변환 (MULTILINE)"""
    for pattern, repl in rules:
        text = re.sub(pattern, repl, text, flags=re.MULTILINE)
    return text


# ── 10번 파일 전용 처리 ──

def process_ch10(text):
    """10번: 헤딩 하강 + 6.x→3-2-x 재번호
    6.2.3/6.2.4는 소스에서 ##이지만 6.2 하위이므로 2단계 하강"""
    lines = text.split("\n")

    # 6.2.3/6.2.4 구간 탐지
    extra_zone = set()
    in_extra = False
    for idx, line in enumerate(lines):
        if re.match(r"^## 6\.2\.[34]", line):
            in_extra = True
        elif in_extra and re.match(r"^## (6\.[34]|요약)", line):
            in_extra = False
        if in_extra:
            extra_zone.add(idx)

    result = []
    for idx, line in enumerate(lines):
        if re.match(r"^# ", line):
            continue  # 장 헤딩 제거

        if not line.startswith("#"):
            result.append(line)
            continue

        m = re.match(r"^(#+)(.*)", line)
        hashes, rest = m.group(1), m.group(2)

        demote = 2 if idx in extra_zone else 1
        new_hashes = "#" * (len(hashes) + demote)

        # 번호 재매핑 (긴 패턴부터)
        rest = re.sub(r" 6\.(\d+)\.(\d+)\.(\d+) ", r" 3-2-\1-\2-\3. ", rest)
        rest = re.sub(r" 6\.(\d+)\.(\d+) ", r" 3-2-\1-\2. ", rest)
        rest = re.sub(r" 6\.(\d+) ", r" 3-2-\1. ", rest)
        if rest.strip().startswith("요약"):
            rest = " 3-2-5. " + rest.strip()

        result.append(new_hashes + rest)

    return "\n".join(result)


# ── 장별 조립 ──

def build_ch1(src, used):
    """1장. 연구개발과제의 필요성 (06번 전체)"""
    text = get_text(src, "06", 2, 846, used)
    return xform(text, [
        (r"^(## )1\.1 ", r"\g<1>1-1. "),
        (r"^(## )1\.2 ", r"\g<1>1-2. "),
    ])


def build_ch2(src, used):
    """2장. 연구개발과제의 목표 및 내용 (08번 전체)"""
    parts = []

    # 원본 장 헤딩 소비
    get_text(src, "08", 2, 4, used)
    parts.append("# 2. 연구개발과제의 목표 및 내용\n\n")

    # 2-1: §2.1 + §2.2 (5~58행)
    s1 = get_text(src, "08", 5, 58, used)
    s1 = xform(s1, [
        (r"^## 2\.1 ", "## 2-1. "),
        (r"^## 2\.2 ", "### 2-1-1. "),
        (r"^### 2\.2\.(\d+)", r"#### 2-1-1-\1."),
    ])
    parts.append(s1)

    get_text(src, "08", 59, 59, used)
    parts.append(SEP)

    # 2-2: §2.3 (60~885행)
    s2 = get_text(src, "08", 60, 885, used)
    s2 = xform(s2, [
        (r"^## 2\.3 연차별 개발 목표 및 내용", "## 2-2. 개발목표 및 개발내용"),
    ])
    parts.append(s2)

    get_text(src, "08", 886, 886, used)
    parts.append(SEP)

    # 2-3: §2.4~2.6 (887~976행)
    s3 = get_text(src, "08", 887, 976, used)
    s3 = xform(s3, [
        (r"^## 2\.4 .*$", "## 2-3. 연구개발과제 수행일정 및 주요 결과물"),
        (r"^## 2\.5 ", "### 2-3-1. "),
        (r"^## 2\.6 ", "### 2-3-2. "),
        (r"^### 2\.5\.(\d+)", r"#### 2-3-1-\1."),
        (r"^### 2\.6\.(\d+)", r"#### 2-3-2-\1."),
    ])
    parts.append(s3)

    return "".join(parts)


def build_ch3(src, used):
    """3장. 추진전략·방법 및 추진체계 (09번+10번)"""
    parts = []

    get_text(src, "09", 2, 6, used)
    parts.append("# 3. 연구개발과제의 추진전략·방법 및 추진체계\n\n")

    # ── 3-1 ──
    parts.append("## 3-1. 기술개발 추진방법·전략\n\n")

    # Part1: Section 1 (09번 7~83)
    p1 = get_text(src, "09", 7, 83, used)
    p1 = xform(p1, [
        (r"^## Section 1:.*$", ""),
        (r"^### 3\.1\.(\d+)", r"### 3-1-\1."),
    ])
    parts.append(p1)

    get_text(src, "09", 84, 84, used)

    # Part2: Section 2 (09번 85~190) - 레벨 하강
    p2 = get_text(src, "09", 85, 190, used)
    p2 = xform(p2, [
        (r"^## Section 2:.*$", "### 3-1-4. 기술개발 상세 내용"),
        (r"^### 3\.2\.(\d+)", r"#### 3-1-4-\1."),
    ])
    parts.append(p2)

    get_text(src, "09", 191, 191, used)

    # Part3: Section 4 (09번 279~353) - 레벨 하강
    p3 = get_text(src, "09", 279, 353, used)
    p3 = xform(p3, [
        (r"^## Section 4:.*$", "### 3-1-5. 개발 방법론"),
        (r"^### 3\.4\.(\d+)", r"#### 3-1-5-\1."),
    ])
    p3 += "\n<!-- NOTE: §3.4.4~3.4.5 위험관리는 3-2절(10번)과 중복. PM 검토 후 간략 요약으로 대체 가능 -->\n\n"
    parts.append(p3)

    get_text(src, "09", 354, 354, used)

    # Part4: 로드맵 (09번 355~381) - 레벨 하강
    p4 = get_text(src, "09", 355, 381, used)
    p4 = xform(p4, [
        (r"^## 기술개발 로드맵.*$", "### 3-1-6. 기술개발 로드맵 (연차별)"),
    ])
    parts.append(p4)

    parts.append(SEP)

    # ── 3-2: 10번 전체 ──
    parts.append("## 3-2. 기술개발 추진체계\n\n")
    ch10 = get_text(src, "10", 2, 725, used)
    ch10 = process_ch10(ch10)
    parts.append(ch10)

    parts.append(SEP)

    # ── 3-3: 09번 Section 3 ──
    parts.append("## 3-3. 기술개발팀 편성도\n\n")
    s3 = get_text(src, "09", 192, 277, used)
    s3 = xform(s3, [
        (r"^## Section 3:.*$", ""),
        (r"^### 3\.3\.1", "### 3-3-1."),
        (r"^### 4\.3\.2", "### 3-3-2."),
        (r"^### 3\.3\.3", "### 3-3-3."),
    ])
    parts.append(s3)

    get_text(src, "09", 278, 278, used)
    parts.append(SEP)

    # ── 3-4: TODO ──
    parts.append("## 3-4. 과제 수행 중 일자리 창출 계획·방법\n\n")
    parts.append("<!-- TODO: 신규 작성 필요 -->\n")
    parts.append("<!--\n")
    parts.append("작성 가이드:\n")
    parts.append("- 과제 수행 기간 중 기관별 신규 고용 계획 (연구원, 보조연구원, 인턴)\n")
    parts.append("- 청년 인력 활용 방안 (석박사 참여, 산학연 연계)\n")
    parts.append("- 과제 종료 후 고용 유지/확대 계획\n")
    parts.append("- 참고: 11번 § 7.2.4-2 '일자리 창출 및 우수 인재 유치' 내용 발췌 가능\n")
    parts.append("- 참고: 09번 § 3.3.3 '전담 인력 구성'과 연계\n")
    parts.append("-->\n\n")

    return "".join(parts)


def build_ch4(src, used):
    """4장. 활용방안 및 기대효과 (11번 §7.1+§7.2)"""
    parts = []

    get_text(src, "11", 2, 4, used)
    parts.append("# 4. 연구개발성과의 활용방안 및 기대효과\n\n")

    # 4-1: §7.1 (5~177행)
    s1 = get_text(src, "11", 5, 177, used)
    s1 = xform(s1, [
        (r"^## 7\.1 ", "## 4-1. "),
        (r"^### 7\.1\.(\d+)", r"### 4-1-\1."),
    ])
    parts.append(s1)

    get_text(src, "11", 178, 178, used)
    parts.append(SEP)

    # 4-2: §7.2 (179~411행)
    s2 = get_text(src, "11", 179, 411, used)
    s2 = xform(s2, [
        (r"^## 7\.2 ", "## 4-2. "),
        (r"^### 7\.2\.(\d+)", r"### 4-2-\1."),
    ])
    parts.append(s2)

    get_text(src, "11", 412, 412, used)
    parts.append(SEP)

    # 4-3: TODO
    parts.append("## 4-3. 연구개발성과의 기술기여도\n\n")
    parts.append("<!-- TODO: 아래 골격에 내용 채우기 -->\n\n")
    parts.append("### 4-3-1. 해당 기술 분야 발전 기여도\n\n")
    parts.append("- AI 소프트센서: 국내 TRL 3→7 (본 과제가 4단계 상승에 기여)\n")
    parts.append("- 크로스모달 학습: 스마트홈 분야 국내 최초 실증\n\n")
    parts.append("### 4-3-2. 표준화 기여도\n\n")
    parts.append("<!-- 11번 § 7.5.3에서 발췌 -->\n")
    parts.append("- TTA 단체표준 1건 제정 (2년차)\n")
    parts.append("- CSA 기술 기고 5건 이상\n\n")
    parts.append("### 4-3-3. 타 산업 파급효과\n\n")
    parts.append("- 스마트 빌딩, 스마트 팩토리, 헬스케어 등으로 확산 가능\n")
    parts.append("<!-- 11번 § 7.2.1에서 관련 내용 발췌 -->\n\n")

    return "".join(parts)


def build_ch5(src, used):
    """5장. 사업화 전략 및 계획 (11번 §7.3+§7.4+§7.5)"""
    parts = []

    parts.append("# 5. 연구개발성과의 사업화 전략 및 계획\n\n")

    # 5-1: §7.3 (413~448행)
    s1 = get_text(src, "11", 413, 448, used)
    s1 = xform(s1, [
        (r"^## 7\.3 .*$", "## 5-1. 국내·외 기술과 시장 현황"),
        (r"^### 7\.3\.(\d+)", r"### 5-1-\1."),
    ])
    parts.append(s1)

    get_text(src, "11", 449, 449, used)
    parts.append(SEP)

    # 5-2: §7.5.1+7.5.2 (596~645행)
    s2 = get_text(src, "11", 596, 645, used)
    s2 = xform(s2, [
        (r"^## 7\.5 .*$", "## 5-2. 관련 지식재산권, 표준화 및 인증기준 현황 등"),
        (r"^### 7\.5\.1", "### 5-2-1."),
        (r"^### 7\.5\.2", "### 5-2-2."),
    ])
    parts.append(s2)

    get_text(src, "11", 646, 646, used)  # blank
    parts.append(SEP)

    # 5-3: §7.5.3 (647~671행) - 레벨 상승
    s3 = get_text(src, "11", 647, 671, used)
    s3 = xform(s3, [
        (r"^### 7\.5\.3 .*$", "## 5-3. 표준화 전략"),
    ])
    s3 = re.sub(r"^####", "###", s3, flags=re.MULTILINE)
    parts.append(s3)

    get_text(src, "11", 672, 672, used)  # blank
    parts.append(SEP)

    # 5-4: §7.4 (450~594행) + 요약 (709~739행)
    s4a = get_text(src, "11", 450, 594, used)
    s4a = xform(s4a, [
        (r"^## 7\.4 .*$", "## 5-4. 경제적 성과 창출계획"),
        (r"^### 7\.4\.(\d+)", r"### 5-4-\1."),
    ])
    parts.append(s4a)

    get_text(src, "11", 595, 595, used)  # separator

    s4b = get_text(src, "11", 709, 739, used)
    s4b = xform(s4b, [
        (r"^## 본 성과활용.*$", "### 5-4-3. 종합 요약"),
        (r"^### 핵심", "#### 핵심"),
        (r"^### 기대효과", "#### 기대효과"),
    ])
    parts.append("\n" + s4b)

    parts.append(SEP)

    # 5-5: TODO + 7.5.4 원본 포함
    parts.append("## 5-5. 사회적 가치 창출 계획\n\n")
    parts.append("<!-- TODO: 아래 골격에 내용 채우기 -->\n\n")
    parts.append("### 5-5-1. 취약계층 안전 기여\n\n")
    parts.append("<!-- 11번 § 7.2.3-1 '생명 보호' 에서 발췌 -->\n")
    parts.append("- 독거노인 응급 대응 시간 47분→5분 단축\n")
    parts.append("- 가정 내 사고 사망률 35% 감소\n\n")
    parts.append("### 5-5-2. 에너지 절감 및 환경 기여\n\n")
    parts.append("<!-- 기존 내용 중 에너지 관련 발췌 -->\n")
    parts.append("- AI 기반 에너지 최적화로 가구당 연간 15% 절감\n\n")
    parts.append("### 5-5-3. 개인정보 보호 및 데이터 주권\n\n")
    parts.append("- 온디바이스 AI로 데이터 외부 전송 없음\n")
    parts.append("- 차분 프라이버시(Differential Privacy) 적용\n\n")

    # 5-5-4: 11번 §7.5.4 원본 직접 포함 (673~707행)
    parts.append("### 5-5-4. 정부 정책 연계\n\n")
    parts.append("<!-- 아래는 11번 § 7.5.4 원본 (673~707행) -->\n\n")
    ref = get_text(src, "11", 673, 707, used)
    ref = xform(ref, [
        (r"^### 7\.5\.4 .*$", ""),  # 원본 헤딩 제거 (5-5-4로 대체)
    ])
    parts.append(ref)

    get_text(src, "11", 708, 708, used)  # separator

    return "".join(parts)


# ── DUMMY 수집 ──

def build_dummy(src, used):
    """미배치 라인 수집"""
    parts = []
    parts.append("\n---\n\n")
    parts.append("# DUMMY: 미배치 잉여 콘텐츠\n\n")
    parts.append("> 아래는 MD 원본에 있지만 위 본문에 배치되지 않은 콘텐츠입니다.\n")
    parts.append("> PM 검토 후 적절한 위치로 이동하거나 삭제해 주세요.\n\n")

    has_dummy = False
    for key in ["06", "08", "09", "10", "11"]:
        max_line = max(src[key].keys())
        unused = []
        for i in range(1, max_line + 1):
            if i not in used[key]:
                line = src[key].get(i, "")
                if line.strip().startswith("<!-- tab-id:"):
                    continue
                unused.append((i, line))

        substantive = [l for _, l in unused if l.strip() and l.strip() != "---"]
        if substantive:
            has_dummy = True
            fname = FILES[key].name
            parts.append(f"## DUMMY: {key}번 파일 미배치 ({len(substantive)}줄)\n\n")
            parts.append(f"<!-- 소스: {fname} -->\n\n")
            for lineno, line in unused:
                if line.strip():
                    parts.append(f"<!-- L{lineno} --> {line}")
            parts.append("\n")

    if not has_dummy:
        parts.append("> 미배치 콘텐츠 없음 - 모든 소스 텍스트가 본문에 포함됨\n\n")

    return "".join(parts)


# ── 메인 ──

def main():
    print("제안서 5장 통합 MD 조립 시작...")

    src = {key: read_file(key) for key in FILES}
    used = {key: {1} for key in FILES}  # line 1 (tab-id) 기본 제외

    output = []
    output.append("<!-- 제안서-통합-5장.md - 자동 생성 (build_master_md.py) -->\n")
    output.append("<!-- 소스: output/kiat-proposal/ 5개 파일 -->\n\n")

    output.append(build_ch1(src, used))
    output.append(SEP)
    output.append(build_ch2(src, used))
    output.append(SEP)
    output.append(build_ch3(src, used))
    output.append(SEP)
    output.append(build_ch4(src, used))
    output.append(SEP)
    output.append(build_ch5(src, used))
    output.append(build_dummy(src, used))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("".join(output))

    # 무결성 검증
    print("\n무결성 검증:")
    for key in ["06", "08", "09", "10", "11"]:
        max_line = max(src[key].keys())
        n_used = len(used[key])
        n_total = max_line
        unused_substantive = 0
        for i in range(1, max_line + 1):
            if i not in used[key]:
                line = src[key].get(i, "").strip()
                if line and line != "---" and not line.startswith("<!-- tab-id:"):
                    unused_substantive += 1
        status = "OK" if unused_substantive == 0 else f"DUMMY {unused_substantive}줄"
        print(f"  {key}번: {n_total}줄 -> {n_used}줄 사용  [{status}]")

    # 목차 출력
    result = "".join(output)
    print("\n목차:")
    for line in result.split("\n"):
        if line.startswith("#") and not line.startswith("<!--"):
            level = len(re.match(r"^(#+)", line).group(1))
            title = line.lstrip("#").strip()[:70]
            if level <= 3:
                indent = "  " * (level - 1)
                print(f"  {indent}{title}")

    print(f"\n출력: {OUTPUT_FILE}")
    out_lines = result.count("\n")
    print(f"총 {out_lines}줄 생성")


if __name__ == "__main__":
    main()

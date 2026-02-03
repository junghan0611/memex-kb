#!/usr/bin/env python3
"""
HWPX 스타일 추출기

원본 HWPX에서 폰트, 문자 속성, 문단 속성을 추출하여
JSON 메타데이터 파일로 저장합니다.

역변환 시 이 메타데이터를 사용하여 스타일을 복원합니다.

Usage:
    python style_extractor.py input.hwpx -o styles.json
"""

import argparse
import json
import logging
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

NAMESPACES = {
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
}


class StyleExtractor:
    """HWPX 스타일 추출기"""

    def __init__(self, hwpx_path: str):
        self.hwpx_path = Path(hwpx_path)
        self.styles = {
            "fonts": [],      # 폰트 목록
            "charPr": [],     # 문자 속성
            "paraPr": [],     # 문단 속성
            "borderFill": [], # 테두리/채우기
        }

    def extract(self) -> dict:
        """스타일 정보 추출"""
        with zipfile.ZipFile(self.hwpx_path, "r") as zf:
            # header.xml 파싱
            if "Contents/header.xml" in zf.namelist():
                content = zf.read("Contents/header.xml")
                self._parse_header(content)

        return self.styles

    def _parse_header(self, content: bytes) -> None:
        """header.xml에서 스타일 추출"""
        root = ET.fromstring(content)

        # 폰트 목록 추출
        for fontface in root.findall(f".//{{{NAMESPACES['hh']}}}fontface"):
            lang = fontface.get("lang", "")
            for font in fontface.findall(f"{{{NAMESPACES['hh']}}}font"):
                self.styles["fonts"].append({
                    "id": int(font.get("id", 0)),
                    "face": font.get("face", ""),
                    "type": font.get("type", ""),
                    "lang": lang,
                })

        # 문자 속성 추출
        for char_pr in root.findall(f".//{{{NAMESPACES['hh']}}}charPr"):
            pr = {
                "id": int(char_pr.get("id", 0)),
                "height": int(char_pr.get("height", 1000)),
                "textColor": char_pr.get("textColor", "#000000"),
            }

            # fontRef 추출 (폰트 참조)
            font_ref = char_pr.find(f"{{{NAMESPACES['hh']}}}fontRef")
            if font_ref is not None:
                pr["fontRef"] = {
                    "hangul": int(font_ref.get("hangul", 0)),
                    "latin": int(font_ref.get("latin", 0)),
                }

            self.styles["charPr"].append(pr)

        # 문단 속성 추출
        for para_pr in root.findall(f".//{{{NAMESPACES['hh']}}}paraPr"):
            self.styles["paraPr"].append({
                "id": int(para_pr.get("id", 0)),
                "lineSpacing": para_pr.get("lineSpacing", ""),
                "align": para_pr.get("align", ""),
            })

        logger.info(f"폰트: {len(self.styles['fonts'])}개")
        logger.info(f"문자 속성: {len(self.styles['charPr'])}개")
        logger.info(f"문단 속성: {len(self.styles['paraPr'])}개")

    def save(self, output_path: str) -> None:
        """JSON 파일로 저장"""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.styles, f, ensure_ascii=False, indent=2)
        logger.info(f"스타일 저장: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="HWPX 스타일 추출")
    parser.add_argument("input", help="HWPX 파일")
    parser.add_argument("-o", "--output", help="출력 JSON 파일")

    args = parser.parse_args()

    output = args.output or str(Path(args.input).with_suffix(".styles.json"))

    extractor = StyleExtractor(args.input)
    styles = extractor.extract()
    extractor.save(output)

    # 주요 폰트 출력
    print("\n사용된 폰트:")
    for font in styles["fonts"][:10]:
        print(f"  - {font['face']} ({font['lang']})")


if __name__ == "__main__":
    main()

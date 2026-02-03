#!/usr/bin/env python3
"""
HWPX ↔ AsciiDoc 왕복 변환 테스트

퀄리티 보장을 위한 테스트:
1. 텍스트 무손실 검증
2. 테이블 구조 보존 검증
3. 스타일 ID 보존 검증 (선택)

Usage:
    python test_roundtrip.py input.hwpx
"""

import argparse
import logging
import sys
import tempfile
from pathlib import Path

from hwpx_to_asciidoc import HwpxParser
from asciidoc_to_hwpx import HwpxGenerator
from asciidoc_parser import parse_asciidoc_table

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class RoundtripTester:
    """왕복 변환 테스트"""

    def __init__(self, hwpx_path: str):
        self.hwpx_path = Path(hwpx_path)
        self.original_parser = None
        self.converted_adoc = None
        self.roundtrip_parser = None

    def run_tests(self) -> dict:
        """모든 테스트 실행"""
        results = {
            "text_integrity": False,
            "table_count": False,
            "table_structure": False,
            "errors": [],
        }

        try:
            # Step 1: 원본 HWPX 파싱
            logger.info("1. 원본 HWPX 파싱...")
            self.original_parser = HwpxParser(str(self.hwpx_path))
            self.original_parser.parse()
            logger.info(f"   - {len(self.original_parser.paragraphs)}개 문단")
            logger.info(f"   - {len(self.original_parser.tables)}개 테이블")

            # Step 2: AsciiDoc 변환
            logger.info("2. AsciiDoc 변환...")
            from hwpx_to_asciidoc import AsciiDocConverter
            converter = AsciiDocConverter(self.original_parser)
            self.converted_adoc = converter.convert()

            # Step 3: AsciiDoc → HWPX 역변환
            logger.info("3. HWPX 역변환...")
            with tempfile.NamedTemporaryFile(suffix=".adoc", delete=False) as f:
                f.write(self.converted_adoc.encode())
                adoc_path = f.name

            with tempfile.NamedTemporaryFile(suffix=".hwpx", delete=False) as f:
                hwpx_path = f.name

            generator = HwpxGenerator()
            generator.parse_asciidoc(adoc_path)
            generator.generate(hwpx_path)

            # Step 4: 역변환된 HWPX 다시 파싱
            logger.info("4. 역변환 HWPX 파싱...")
            self.roundtrip_parser = HwpxParser(hwpx_path)
            self.roundtrip_parser.parse()

            # Step 5: 검증
            logger.info("5. 검증...")
            results["text_integrity"] = self._test_text_integrity()
            results["table_count"] = self._test_table_count()
            results["table_structure"] = self._test_table_structure()

        except Exception as e:
            results["errors"].append(str(e))
            logger.error(f"테스트 실패: {e}")

        return results

    def _test_text_integrity(self) -> bool:
        """텍스트 무손실 검증"""
        original_texts = set(p.text.strip() for p in self.original_parser.paragraphs if p.text.strip())
        roundtrip_texts = set(p.text.strip() for p in self.roundtrip_parser.paragraphs if p.text.strip())

        # 원본 텍스트가 역변환에 모두 존재하는지
        missing = original_texts - roundtrip_texts
        if missing:
            logger.warning(f"   누락된 텍스트: {len(missing)}개")
            for text in list(missing)[:3]:
                logger.warning(f"   - {text[:50]}...")
            return False

        logger.info(f"   ✅ 텍스트 무손실: {len(original_texts)}개")
        return True

    def _test_table_count(self) -> bool:
        """테이블 개수 검증"""
        original_count = len(self.original_parser.tables)
        roundtrip_count = len(self.roundtrip_parser.tables)

        if original_count != roundtrip_count:
            logger.warning(f"   테이블 개수 불일치: {original_count} → {roundtrip_count}")
            return False

        logger.info(f"   ✅ 테이블 개수 일치: {original_count}개")
        return True

    def _test_table_structure(self) -> bool:
        """테이블 구조(행/열) 검증"""
        all_match = True

        for i, (orig, rt) in enumerate(zip(self.original_parser.tables, self.roundtrip_parser.tables)):
            if orig.row_count != rt.row_count or orig.col_count != rt.col_count:
                logger.warning(
                    f"   테이블 {i}: 구조 불일치 "
                    f"({orig.row_count}x{orig.col_count} → {rt.row_count}x{rt.col_count})"
                )
                all_match = False
            else:
                logger.info(f"   ✅ 테이블 {i}: {orig.row_count}x{orig.col_count}")

        return all_match


def print_report(results: dict) -> None:
    """테스트 결과 리포트"""
    print("\n" + "=" * 50)
    print("왕복 변환 테스트 결과")
    print("=" * 50)

    tests = [
        ("텍스트 무손실", results["text_integrity"]),
        ("테이블 개수", results["table_count"]),
        ("테이블 구조", results["table_structure"]),
    ]

    passed = sum(1 for _, v in tests if v)
    total = len(tests)

    for name, passed_test in tests:
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"  {name}: {status}")

    if results["errors"]:
        print("\n오류:")
        for err in results["errors"]:
            print(f"  - {err}")

    print("=" * 50)
    print(f"결과: {passed}/{total} 통과")

    return passed == total


def main():
    parser = argparse.ArgumentParser(description="HWPX 왕복 변환 테스트")
    parser.add_argument("input", help="테스트할 HWPX 파일")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    tester = RoundtripTester(args.input)
    results = tester.run_tests()
    success = print_report(results)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

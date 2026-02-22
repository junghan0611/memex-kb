# Changelog

## [1.0.0] - 2026-02-22

### 초기 릴리즈 — Org + AsciiDoc 병합 셀 → ODT 파이프라인

`hwpx2asciidoc/`에서 `orgadoc2odt/`로 리네이밍 및 목적 전환.
HWPX 직접 변환 대신 **Org + AsciiDoc → ODT** 파이프라인에 집중.

#### 추가
- `adoc_to_odt.py`: Org 파일 내 `#+begin_src adoc` 블록을 전처리하여
  asciidoctor(HTML) → pandoc(org→html→odt)로 병합 셀 보존 ODT 생성
- `odt_to_adoc.py`: ODT 테이블 → AsciiDoc 역변환 (기존 제안서에서 구조 추출)
- `odt_table_style.py`: ODT 테이블 스타일 후처리
  - 셀 테두리 (1pt 검정), 헤더 배경 (#d9d9d9), 폰트 (돋움 8pt)
  - 셀 패딩, 세로 가운데, 테이블 100% 너비
- `run.sh`: CLI (convert, preprocess, verify, test)
- `samples/test-merge-tables.org`: 6유형 병합 셀 테스트
- `samples/complex-table.odt`: KIAT 제안서 표지 원본 (49행×30열)

#### 검증
- 6유형 병합 셀 테스트 전체 통과
- KIAT 제안서 표지 왕복: colspan 215개 + rowspan 39개 완벽 일치
- 변환 경로 비교: DocBook 경유(rowspan 소실), org→odt 직접(RawBlock 무시)
  → **org→html→odt 2단계만 안전** 확인

#### 변경
- `hwpx2asciidoc/` → `orgadoc2odt/` 리네이밍
- HWPX 관련 코드는 `_legacy/`로 이동 (삭제하지 않음)

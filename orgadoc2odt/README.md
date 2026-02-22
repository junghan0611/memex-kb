# orgadoc2odt — Org + AsciiDoc 병합 셀 → ODT 파이프라인

Org-mode 문서 안에 AsciiDoc 테이블을 삽입하여, **병합 셀(colspan/rowspan)이 보존된 ODT**를 생성한다.

## 왜 필요한가

| 포맷 | 셀 병합 | 비고 |
|------|---------|------|
| Markdown | ❌ 불가 | 표준에 셀 병합 자체가 없음 |
| Org-mode | ❌ 불가 | org-table은 병합 미지원 |
| **AsciiDoc** | ✅ 네이티브 | `.2+\|text` = 2행 병합 |
| HTML | ✅ 가능 | verbose, 편집 불편 |

제안서·공문서에 필수인 병합 셀 테이블을 Org 워크플로우에서 해결하기 위해,
AsciiDoc을 **구조 보존 중간 포맷**으로 활용한다.

## 파이프라인

```
[Org 파일]  (#+begin_src adoc 블록에 병합 테이블 작성)
    │
    ▼  adoc_to_odt.py — 전처리
    │  asciidoctor -b html5 → <table> 추출
    │  #+begin_export html 로 교체
    ▼
[pandoc org → html]
    │  Org 본문 + HTML 테이블이 하나의 HTML로 합성
    ▼
[pandoc html → odt]
    │  colspan/rowspan → ODT 병합 셀 완벽 변환
    ▼
[odt_table_style.py]  — 후처리
    │  테두리, 헤더 배경색, 폰트, 패딩 적용
    ▼
[ODT 파일]  →  LibreOffice  →  DOC/HWP
```

**검증된 변환 경로**: `org → html → odt` 2단계만 안전.
- DocBook 경유: rowspan 소실 ❌
- pandoc org→odt 직접: RawBlock(html) 무시 ❌

## 사용법

```bash
# 전체 파이프라인 검증 (6유형 테스트)
./orgadoc2odt/run.sh test

# Org → ODT 변환
./orgadoc2odt/run.sh convert input.org
./orgadoc2odt/run.sh convert input.org -o output.odt -r reference.odt

# ODT 병합 셀 검사
./orgadoc2odt/run.sh verify output.odt

# AsciiDoc 블록 전처리만 (디버깅용)
./orgadoc2odt/run.sh preprocess input.org

# ODT → AsciiDoc 역변환 (기존 제안서에서 테이블 구조 추출)
python orgadoc2odt/odt_to_adoc.py input.odt -o extracted.adoc
python orgadoc2odt/odt_to_adoc.py input.odt -t 1  # 특정 테이블만
```

## Org 파일 작성 예시

```org
#+title: 제안서

* 일반 본문

일반 텍스트와 Org 테이블은 그대로 작성.

** 예산 총괄표

#+begin_src adoc
[cols="2,3,1,1,1",options="header"]
|===
| 비목 | 산출근거 | 1차년도 | 2차년도 | 합계

.3+| 인건비
| 책임연구원 1명 × 12개월 | 36,000 | 38,000 | 74,000
| 선임연구원 2명 × 12개월 | 48,000 | 50,000 | 98,000
| 연구보조원 1명 × 6개월 | 9,000 | 9,500 | 18,500

| 합계 4+| 190,500
|===
#+end_src
```

## AsciiDoc 병합 셀 문법

| 문법 | 의미 | 예시 |
|------|------|------|
| `\|text` | 일반 셀 | `\| 내용` |
| `2+\|text` | 2열 병합 (colspan) | `2+\| 합계` |
| `.3+\|text` | 3행 병합 (rowspan) | `.3+\| 인건비` |
| `2.3+\|text` | 2열×3행 동시 병합 | `2.3+\| 총괄` |

## 스타일 후처리

`odt_table_style.py`가 proposal-pipeline의 `reference.odt` 기준으로 적용:

- 셀 테두리: 1pt 검정 실선 (`0.035cm solid #000000`)
- 헤더 행: 회색 배경 (`#d9d9d9`), 볼드, 가운데 정렬
- 셀 패딩: `0.097cm`, 세로 가운데 정렬
- 폰트: 돋움(Dotum) 8pt
- 테이블: 100% 너비, 가운데 정렬

## 파일 구조

```
orgadoc2odt/
├── adoc_to_odt.py        # Org+AsciiDoc → ODT 변환 (정방향)
├── odt_to_adoc.py        # ODT → AsciiDoc 역변환 (역방향)
├── odt_table_style.py    # ODT 테이블 스타일 후처리
├── asciidoc_parser.py    # AsciiDoc 테이블 파서
├── run.sh                # CLI 인터페이스
├── README.md
├── CHANGELOG.md
├── samples/
│   ├── test-merge-tables.org          # 6유형 병합 셀 테스트
│   ├── complex-table.odt             # KIAT 제안서 표지 (49행×30열)
│   └── complex-table-extracted.adoc  # 역추출된 AsciiDoc
└── _legacy/                          # HWPX 관련 코드 (보존)
```

## 검증 결과

### 기본 병합 (6유형)

| 유형 | 내용 | 결과 |
|------|------|------|
| 1 | colspan (열 병합) | ✅ |
| 2 | rowspan (행 병합) | ✅ |
| 3 | colspan + rowspan 복합 | ✅ |
| 4 | 다단 rowspan (3행 이상) | ✅ |
| 5 | 2차원 병합 (cs×rs 동시) | ✅ |
| 6 | 실전 예산표 | ✅ |

### KIAT 제안서 표지 왕복 테스트

- 원본: 49행 × 30열, colspan 215개, rowspan 39개
- 왕복: **colspan 215개, rowspan 39개 (완벽 일치)**

## proposal-pipeline과의 관계

```
proposal-pipeline (Emacs ox-odt)     orgadoc2odt (pandoc)
─────────────────────────────        ────────────────────
본문, 일반 테이블, 인용               병합 셀 테이블
reference.odt 스타일 시트             odt_table_style.py
citar + CSL 자동 인용                 —

         ↓                                  ↓
    본문 ODT                          병합 테이블 ODT
         └─────── ODT/DOC 레벨 합성 ───────┘
                        ↓
                  최종 제안서 ODT/DOC
```

각자 잘하는 영역을 분리하고, 최종 문서에서 합친다.
점진적 통합 예정.

## 의존성

- Python 3.12 (stdlib만 사용)
- asciidoctor 2.0+ (시스템 또는 Nix)
- pandoc 3.x

## 라이선스

MIT License

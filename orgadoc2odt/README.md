# HWPX ↔ AsciiDoc 양방향 변환기

HWPX(한글 XML 포맷)와 AsciiDoc 간 양방향 변환을 지원합니다.
테이블 셀 병합(colspan/rowspan)을 보존합니다.

## 설치

**Nix Flake 환경** (권장):
```bash
cd /home/junghan/sync/emacs/memex-kb
nix develop
```

## 사용법

### HWPX → AsciiDoc

```bash
# 쉘 스크립트
./hwpx2asciidoc/hwpx2asciidoc.sh input.hwpx output.adoc

# Python 직접 실행
nix develop --command python hwpx2asciidoc/hwpx_to_asciidoc.py input.hwpx -o output.adoc
```

### AsciiDoc → HWPX

```bash
# 쉘 스크립트 (새 HWPX 생성)
./hwpx2asciidoc/asciidoc2hwpx.sh input.adoc output.hwpx

# 템플릿 기반 생성
./hwpx2asciidoc/asciidoc2hwpx.sh input.adoc template.hwpx output.hwpx

# Python 직접 실행
nix develop --command python hwpx2asciidoc/asciidoc_to_hwpx.py input.adoc -o output.hwpx
```

## AsciiDoc 테이블 병합 문법

| 문법 | 설명 | 예시 |
|------|------|------|
| `\|text` | 일반 셀 | `\|내용` |
| `2+\|text` | 2열 병합 (colspan) | `2+\|병합된 내용` |
| `.3+\|text` | 3행 병합 (rowspan) | `.3+\|세로 병합` |
| `2.3+\|text` | 2열 x 3행 병합 | `2.3+\|큰 셀` |

## 파일 구조

```
hwpx2asciidoc/
├── hwpx_to_asciidoc.py   # HWPX → AsciiDoc 변환
├── asciidoc_to_hwpx.py   # AsciiDoc → HWPX 역변환
├── asciidoc_parser.py    # AsciiDoc 테이블 파서
├── hwpx2asciidoc.sh      # 변환 쉘 스크립트
├── asciidoc2hwpx.sh      # 역변환 쉘 스크립트
└── README.md             # 이 문서
```

## HWPX 파일 구조

HWPX는 ZIP 압축된 XML 파일입니다:

```
file.hwpx (ZIP)
├── mimetype
├── META-INF/
│   └── container.xml
└── Contents/
    ├── content.hpf       # 패키지 정보
    ├── header.xml        # 문서 헤더
    └── section0.xml      # 본문 (테이블, 문단)
```

### 테이블 XML 구조

```xml
<hp:tbl rowCnt="3" colCnt="4">
  <hp:tr>
    <hp:tc>
      <hp:cellAddr colAddr="0" rowAddr="0" />
      <hp:p><hp:run><hp:t>셀 내용</hp:t></hp:run></hp:p>
    </hp:tc>
  </hp:tr>
</hp:tbl>
```

**셀 병합 계산**: `cellAddr`의 `colAddr`/`rowAddr` 간격으로 colspan/rowspan 추론

## 폰트 보존 워크플로우

원본 HWPX를 템플릿으로 사용하면 **폰트 및 스타일 정보가 보존**됩니다.

```bash
# 1. 스타일 정보 추출 (선택, 참고용)
nix develop --command python hwpx2asciidoc/style_extractor.py 원본.hwpx

# 2. AsciiDoc 변환
./hwpx2asciidoc/hwpx2asciidoc.sh 원본.hwpx 편집용.adoc

# 3. AsciiDoc 편집 (에이전트 또는 수동)
# ... 텍스트 수정 ...

# 4. 역변환 (원본을 템플릿으로 사용!)
./hwpx2asciidoc/asciidoc2hwpx.sh 편집용.adoc 원본.hwpx 결과.hwpx
#                                            └────────┘
#                                            템플릿: header.xml(폰트) 보존
```

**보존되는 스타일**:
- 폰트 (굴림체, 바탕체, 맑은고딕 등)
- 문자 속성 (크기, 색상)
- 문단 속성 (정렬, 줄간격)
- 테두리/배경색

## 퀄리티 검증 테스트

```bash
# 왕복 변환 테스트 (텍스트 무손실, 테이블 구조 검증)
nix develop --command python hwpx2asciidoc/test_roundtrip.py input.hwpx
```

## 제한사항

- 이미지 변환 미지원 (텍스트/테이블만)
- 복잡한 서식(글꼴, 색상) 일부 손실
- 역변환 시 원본 레이아웃과 다를 수 있음

## 라이선스

MIT License

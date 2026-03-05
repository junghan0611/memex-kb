# Org → ODT/DOC 변환 샘플

Emacs `org-odt-export` 기반의 고품질 문서 변환 파이프라인.

## Why not Pandoc?

| | Pandoc | Emacs org-odt-export |
|---|---|---|
| 스타일 적용 | 제한적 | `reference.odt` 완벽 매핑 |
| 한글 캡션 | ❌ | ✅ (그림, 표, 수식) |
| 테이블 스타일 | 기본만 | 헤더 배경색 + 테두리 자동 보정 |
| Bibliography | 기본 | CSL (URL 포함, 한글 지원) |
| 이미지 임베딩 | ✅ | ✅ |

## 빠른 시작

```bash
# 의존성 확인
./run.sh check

# 샘플 빌드
./run.sh build

# 다른 파일 빌드
./run.sh build my-document.org
```

## 파일 구조

```
samples/org-to-odt/
├── run.sh              # 빌드 스크립트 (build/odt/doc/check/clean)
├── sample.org          # 샘플 원본
├── references.bib      # 참고문헌 (BibTeX, URL 포함)
├── .dir-locals.el      # Emacs 로컬 설정
├── images/             # 이미지 폴더
└── README.md           # 이 파일
```

## 파이프라인

```
[Org-mode 파일]
    │  Emacs org-odt-export (reference.odt 스타일)
    ▼
[ODT]
    │  odt_postprocess.py (테이블 헤더/테두리 보정)
    ▼
[ODT 보정 완료]
    │  LibreOffice CLI
    ▼
[DOC]
```

## 의존성

- **Emacs 30+** (org-odt-export)
- **Python 3** (odt_postprocess.py)
- **LibreOffice** (ODT → DOC, 선택)
- **proposal-pipeline/** (같은 리포, `reference.odt` + `proposal-export.el`)

## 커스터마이징

### 스타일 변경

`proposal-pipeline/templates/reference.odt`의 단락/문자 스타일을 LibreOffice에서 수정하면 모든 출력에 반영됩니다.

### 참고문헌 추가

`references.bib`에 BibTeX 엔트리를 추가하고, org 파일에서 `[cite:@key]` 형식으로 인용합니다.

### 이미지

`images/` 폴더에 PNG/JPG를 넣고 org에서 `[[file:images/파일명.png]]`로 참조합니다.

## 활용 예시

- 연구개발계획서
- 이력서 / CV
- 기술 문서
- 제안서

## 핵심 교훈

- **한글 볼드**: `*텍스트*` 앞뒤 공백 필요. ODT에서 NBSP 문제 시 `#+ATTR_ODT` 사용
- **테이블**: org 테이블은 자동 변환. 헤더 행 배경색은 `odt_postprocess.py`가 처리
- **캡션**: `#+caption:` 으로 그림/표 캡션. 한글 자동 지원

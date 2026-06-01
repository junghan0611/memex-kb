# Org → ODT/DOCX 변환 샘플 (품질 쇼케이스)

Emacs `org-odt-export` 기반의 고품질 문서 변환 파이프라인.
`sample.org` 하나에 **번호 인용·번호순 참고문헌·이미지·표·코드**가 모두 들어 있어,
빌드하면 정부 R&D 기획보고서급 품질이 그대로 나온다.

## Why not Pandoc?

| | Pandoc | Emacs org-odt-export |
|---|---|---|
| 스타일 적용 | 제한적 | `reference.odt` 완벽 매핑 |
| 한글 캡션 | ❌ | ✅ (그림, 표, 수식) |
| 테이블 스타일 | 기본만 | 헤더 배경색 + 테두리 자동 보정 |
| Bibliography | 기본 | CSL — IEEE 번호 인용 `[1]` + 번호순 참고문헌 |
| 이미지 임베딩 | ✅ | ✅ (`#+ATTR_ODT :width` 폭 지정) |

## 빠른 시작

```bash
./run.sh check              # 의존성 확인
./run.sh build              # sample.org → odt → 후처리 → docx
./run.sh build my-doc.org   # 다른 파일 빌드
```

산출물: `sample.odt`, `sample.docx`

## 파일 구조

```
samples/org-to-odt/
├── run.sh              # 빌드 스크립트 (build/odt/postprocess/docx/doc/check/clean)
├── sample.org          # 품질 쇼케이스 원본 (번호인용·이미지·표·코드)
├── references.bib      # 참고문헌 (BibTeX, URL 포함)
├── .dir-locals.el      # Emacs 로컬 설정
├── images/             # 이미지 폴더 (sample.png)
└── README.md           # 이 파일
```

## 파이프라인

```
[Org-mode 파일]
    │  Emacs org-odt-export (reference.odt 스타일 + ieee.csl 번호 인용)
    ▼
[ODT]
    │  odt_postprocess.py (테이블 헤더/테두리 보정)
    ▼
[ODT 보정 완료]
    │  LibreOffice CLI (별도 프로파일 — GUI 열려 있어도 변환 가능)
    ▼
[DOCX]
```

## 의존성

- **Emacs 30+** (org-odt-export, oc-csl)
- **Python 3** (odt_postprocess.py)
- **LibreOffice** (ODT → DOCX)
- **proposal-pipeline/** (같은 리포): `proposal-export.el` + `templates/reference.odt` + `templates/ieee.csl`

> 다른 리포에서 쓸 때는 `proposal-pipeline/`의 자산(`proposal-export.el`, `odt_postprocess.py`,
> `templates/reference.odt`, `templates/ieee.csl`)을 프로젝트 안으로 복사(vendoring)하고
> `PROPOSAL_PIPELINE` 환경변수 또는 로컬 경로로 가리키면 self-contained 하게 빌드된다.

## 커스터마이징

### 번호 인용 (IEEE)

헤더에 다음을 넣으면 본문 `[cite:@key]` 가 `[1]`, `[2]` 로 렌더되고
문서 끝 `#+print_bibliography:` 가 번호순 참고문헌을 만든다.

```org
#+bibliography: references.bib
#+cite_export: csl ieee.csl
```

`ieee.csl` 은 `proposal-pipeline/templates/` 에서 자동으로 찾는다(`org-cite-csl-styles-dir`).
저자-연도 스타일을 원하면 `csl` 만 쓰거나 다른 `.csl` 을 지정한다.

### 스타일 변경

`proposal-pipeline/templates/reference.odt` 의 단락/문자 스타일을 LibreOffice에서 수정하면
모든 출력에 반영된다.

### 참고문헌 추가

`references.bib` 에 BibTeX 엔트리를 추가하고, 본문에서 `[cite:@key]` 형식으로 인용한다.
IEEE 스타일에서는 **본문에서 인용한 항목만** 번호순으로 참고문헌에 나온다.

### 이미지

`images/` 폴더에 PNG/JPG 를 넣고 아래처럼 참조한다.

```org
#+CAPTION: 그림 1. 설명
#+ATTR_ODT: :width 14
[[file:images/sample.png]]
```

## 활용 예시

- 연구개발계획서 / 제안서
- 이력서 / CV
- 기술 문서

## 핵심 교훈

- **번호 인용**: `#+cite_export: csl ieee.csl` → 논문식 `[1]` 인용 + 번호순 서지
- **한글 볼드**: `*텍스트*` 앞뒤 공백 필요
- **테이블**: org 테이블은 자동 변환, 헤더 배경색은 `odt_postprocess.py` 처리
- **캡션**: `#+CAPTION:` 으로 그림/표 캡션 (한글 자동 지원)
- **이미지 폭**: `#+ATTR_ODT: :width N` (cm)
- **참고자료 중복 주의**: `#+print_bibliography:` 를 쓰면 수동 URL 리스트는 빼서 중복을 피한다
- **LibreOffice 충돌 회피**: 변환 시 `-env:UserInstallation` 별도 프로파일을 줘 GUI로 열어둔 상태에서도 빌드되게 한다

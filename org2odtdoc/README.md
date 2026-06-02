# Org → ODT/DOCX 변환 (self-contained SSOT 파이프라인)

Emacs `org-odt-export` 기반의 고품질 문서 변환 파이프라인.
`sample.org` 하나에 **번호 인용·번호순 참고문헌·이미지·표·코드**가 모두 들어 있어,
빌드하면 정부 R&D 기획보고서급 품질이 그대로 나온다.

**이 폴더 하나가 SSOT다.** 변환 로직(`pipeline/`)·스타일 마스터(`reference.odt`)·샘플이 모두
안에 들어 있어 외부 의존이 없다. 새 문서를 만들 때는 **이 폴더를 복사하고 `sample.org` 자리에
내 주제를 넣으면** 된다 — 주제가 달라져도 파이프라인은 동일하다.

빌드 산출물에 적용되는 스타일 규약(오늘 기준):
- 헤딩은 **수동 번호**(`1.` / `3-1.`)만 사용 — 자동 장번호 off (중복 `1. 1.` 방지)
- 캡션은 번호 없이 **`<표>` / `<그림>` 라벨 + 제목** (장번호 연동 off)
- 글머리표 **level1 `◦` / level2 `-`**, 표 헤더 배경·테두리 자동 보정
- 폰트는 범용 **Dotum(돋움)** — 특정 HWP 폰트 비의존, 어디서나 렌더

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
org2odtdoc/
├── run.sh                       # 빌드 스크립트 (build/odt/postprocess/docx/doc/check/clean)
├── sample.org                   # 품질 쇼케이스 원본 (번호인용·이미지·표·코드)
├── references.bib               # 참고문헌 (BibTeX, URL 포함)
├── .dir-locals.el               # Emacs 로컬 설정
├── images/                      # 이미지 폴더 (sample.png)
├── pipeline/                    # ← 변환 로직 (self-contained, 외부 의존 없음)
│   ├── proposal-export.el       #    org → odt (스타일·번호인용·헤딩/캡션 번호 제어)
│   ├── odt_postprocess.py       #    표 헤더/테두리 보정 + 캡션 번호 제거
│   └── templates/
│       ├── reference.odt        #    스타일 마스터 (Dotum·글머리표 ◦·번호 off)
│       └── ieee.csl             #    IEEE 번호 인용 스타일
└── README.md                    # 이 파일
```

## 파이프라인

```
[Org-mode 파일]
    │  Emacs org-odt-export — pipeline/proposal-export.el
    │    · reference.odt 스타일 + ieee.csl 번호 인용
    │    · 헤딩 자동 장번호 off / 캡션 장번호 연동 off
    ▼
[ODT]
    │  pipeline/odt_postprocess.py
    │    · 테이블 헤더 배경·테두리 보정
    │    · 캡션 번호 제거 (표 1 → <표>)
    ▼
[ODT 보정 완료]
    │  LibreOffice CLI (별도 프로파일 — GUI 열려 있어도 변환 가능)
    ▼
[DOCX]
```

## 의존성

- **Emacs 30+** (org-odt-export, oc-csl) + Doom 설정 로딩
- **Python 3** (odt_postprocess.py)
- **LibreOffice** (ODT → DOCX)
- 변환 로직은 모두 `pipeline/` 안에 vendoring — **외부 리포 의존 없음**

> 새 문서를 시작할 때는 이 폴더를 통째로 복사하고 `sample.org` 자리에 주제 org 를 넣어
> `./run.sh build my-doc.org` 하면 된다. `pipeline/`은 건드리지 않아도 동일 품질로 빌드된다.

## 커스터마이징

### 번호 인용 (IEEE)

헤더에 다음을 넣으면 본문 `[cite:@key]` 가 `[1]`, `[2]` 로 렌더되고
문서 끝 `#+print_bibliography:` 가 번호순 참고문헌을 만든다.

```org
#+bibliography: references.bib
#+cite_export: csl ieee.csl
```

`ieee.csl` 은 `pipeline/templates/` 에서 자동으로 찾는다(`org-cite-csl-styles-dir`).
저자-연도 스타일을 원하면 `csl` 만 쓰거나 다른 `.csl` 을 지정한다.

### 스타일 변경

`pipeline/templates/reference.odt` 의 단락/문자 스타일을 LibreOffice에서 수정하면
모든 출력에 반영된다.

### 참고문헌 추가

`references.bib` 에 BibTeX 엔트리를 추가하고, 본문에서 `[cite:@key]` 형식으로 인용한다.
IEEE 스타일에서는 **본문에서 인용한 항목만** 번호순으로 참고문헌에 나온다.

### 이미지

`images/` 폴더에 PNG/JPG 를 넣고 아래처럼 참조한다.

```org
#+CAPTION: 설명
#+ATTR_ODT: :width 14
[[file:images/sample.png]]
```

> 캡션 라벨(`<그림>` / `<표>`)은 후처리가 자동으로 붙인다. `#+CAPTION:` 에는 **제목만** 적는다
> (`그림 1.` 같은 수동 번호를 넣으면 `<그림> 그림 1.` 처럼 중복된다).

## 활용 예시

- 연구개발계획서 / 제안서
- 이력서 / CV
- 기술 문서

## 핵심 교훈

- **번호 인용**: `#+cite_export: csl ieee.csl` → 논문식 `[1]` 인용 + 번호순 서지
- **한글 볼드**: `*텍스트*` — 닫는 `*` 뒤에 공백/구두점 필요(뒤에 한글이 바로 붙으면 마크업이 깨져 `*`가 그대로 노출됨). `*증명하는*` 처럼 어미까지 감싸면 안전
- **헤딩 번호**: 헤딩 텍스트에 `1.` / `3-1.` 처럼 **직접** 적는다. 자동 장번호는 off라 중복되지 않는다
- **테이블**: org 테이블은 자동 변환, 헤더 배경색·테두리는 `odt_postprocess.py` 처리
- **캡션**: `#+CAPTION:` 에 제목만 적으면 `<표>` / `<그림>` 라벨이 자동으로 붙는다 (번호 없음)
- **이미지 폭**: `#+ATTR_ODT: :width N` (cm)
- **참고자료 중복 주의**: `#+print_bibliography:` 를 쓰면 수동 URL 리스트는 빼서 중복을 피한다
- **LibreOffice 충돌 회피**: 변환 시 `-env:UserInstallation` 별도 프로파일을 줘 GUI로 열어둔 상태에서도 빌드되게 한다

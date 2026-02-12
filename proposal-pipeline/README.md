# Proposal Pipeline

Google Docs → Markdown → Org-mode → ODT/HWP 제안서 변환 파이프라인.

KIAT 기술연구개발계획서 작성 과정에서 실전 검증된 도구 모음입니다.

## 파이프라인 흐름

```
[Google Docs]
    │  export_kiat_proposal.sh (memex-kb/scripts/)
    ▼
[Markdown 5개 장]  ← output/kiat-proposal/
    │
    ├─ cleanup_md.py        Phase 1: 불릿·캡션·번호 정규화
    ├─ build_master_md.py   5개 MD → 1개 통합 MD (5장 양식)
    │
    ├─ md_to_org.py         장별 MD → Org 변환 (HWPX 레벨 호환)
    │
    ├─ merge_chapters.py    장별 Org → 통합 Org
    ├─ merge_to_template.py 템플릿 Org + 콘텐츠 Org 병합
    ├─ org_merge_levels.py  Level 6→5 후처리
    │
    ▼
[통합 Org 파일]  ← output/proposal-org/
    │  Emacs org-odt-export (reference.odt 스타일 적용)
    ▼
[ODT]
    │  odt_postprocess.py   테이블 헤더 배경색 + 테두리 보정
    ▼
[ODT (보정 완료)]
    │  LibreOffice CLI
    ▼
[DOC] → [HWP/HWPX]
```

## 스크립트 역할

| 스크립트 | 역할 |
|---------|------|
| `build_proposal.sh` | 오케스트레이터 (전체 파이프라인 실행) |
| `md_to_org.py` | Markdown → Org-mode 변환 (HWPX 메타포맷 호환) |
| `merge_chapters.py` | 장별 Org 파일 → 통합 Org 파일 |
| `merge_to_template.py` | HWPX 템플릿 Org + 콘텐츠 Org → 병합 Org |
| `build_master_md.py` | 5개 MD 소스 → 1개 통합 MD (5장 양식 재번호) |
| `cleanup_md.py` | MD 뼈대 정비 (불릿 정리, 캡션 병합, 번호 제거) |
| `org_merge_levels.py` | Org Level 6→5 통합 후처리 |
| `odt_postprocess.py` | ODT 테이블 헤더 배경색 + 셀 테두리 보정 |

## 사용법

### run.sh 통합 명령

```bash
# 전체 빌드 (GDocs 다운로드 → MD → Org → 통합)
./run.sh proposal-build --export-md

# MD → Org 변환만
./run.sh proposal-build --no-sync

# 개별 MD → Org 변환
./run.sh proposal-convert output/kiat-proposal/06--*.md -o ch1.org

# Org 통합 + L6→L5
./run.sh proposal-merge --strip-hwpx-idx --org-tables

# ODT 후처리
./run.sh proposal-odt-fix output/proposal-org/제안서.odt
```

### 직접 실행

```bash
# 오케스트레이터
./proposal-pipeline/build_proposal.sh
./proposal-pipeline/build_proposal.sh --export-md
./proposal-pipeline/build_proposal.sh --no-sync -o /tmp/out

# 개별 스크립트
python proposal-pipeline/md_to_org.py input.md -o output.org
python proposal-pipeline/merge_chapters.py --org-dir output/proposal-org/ -o 제안서.org
python proposal-pipeline/org_merge_levels.py 제안서.org
python proposal-pipeline/odt_postprocess.py 제안서.odt
```

## 다른 제안서에 적용하기

1. **Google Docs 탭 구조 설정**: 장별 탭으로 문서 구성
2. **MD 내보내기**: `scripts/gdocs_md_processor.py` 로 장별 MD 다운로드
3. **매핑 수정**: `build_proposal.sh`의 `MAPPINGS` 배열을 실제 파일명에 맞게 수정
4. **변환 실행**: `./build_proposal.sh --no-sync`
5. **ODT 스타일**: `templates/reference.odt`를 제안서 양식에 맞게 커스터마이즈
6. **Emacs 내보내기**: `templates/.dir-locals.el` 설정 후 `org-odt-export-to-odt`

## 의존성

- **Python 3.12** (stdlib만 사용 — 추가 패키지 불필요)
- **Emacs** (Org → ODT 내보내기)
- **LibreOffice** (ODT → DOC 변환, 선택사항)
- **Pandoc** (MD 전처리, 선택사항)

## 템플릿/리소스

| 파일 | 용도 | 크기 |
|------|------|------|
| `templates/reference.odt` | ODT 스타일 마스터 (Org 내보내기 참조) | 7.9M |
| `templates/ieee.csl` | IEEE 인용 스타일 | 16K |
| `templates/references.bib` | 샘플 BibTeX (85건) | 36K |
| `templates/.dir-locals.el` | Emacs ODT 내보내기 설정 | 858B |

## 핵심 교훈

### 한글 볼드 + NBSP 문제
Org-mode에서 한글 볼드(`*텍스트*`)가 작동하려면 앞뒤에 공백이 필요.
그런데 ODT 내보내기 시 이 공백이 NBSP(Non-Breaking Space)로 변환되어
HWP에서 깨짐. 해결: 볼드 대신 `#+ATTR_ODT: :style "Bold"` 사용.

### ODT 스타일 주의
Org → ODT 내보내기는 `reference.odt`의 스타일을 상속. HWP 양식과
정확히 맞추려면 reference.odt의 단락/문자 스타일을 사전 조정 필수.

### Level 6→5 통합
HWP 양식은 최대 5단계 헤딩. MD H6이 존재하면 `org_merge_levels.py`로
L5로 통합. 부모-자식 이름을 합치는 패턴(1a)과 단순 승격(1b/2) 구분.

### 유니코드 글머리표
HWP와 ODT 간 글머리표 호환성 문제. `docs/unicode-bullet-guide.md` 참조.
`□`, `○`, `·`, `–` 등 안전한 문자만 사용.

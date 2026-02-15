# Changelog

All notable changes to this project will be documented in this file.

## [1.3.1] - 2026-02-15

### Added: GitHub Stars → BibTeX 백엔드 (`scripts/gh_starred_to_bib.sh`)
- GitHub starred repos → `@software{}` BibTeX 엔트리 변환 (Citar 호환)
- `gh api --paginate` + `jq`로 전체 star 자동 수집 (2,140개 테스트 완료)
- 3가지 시간축 보존: starred_at, pushed_at, updated_at
- `run.sh`: `github-starred-export` 명령 + `env-check`에 gh CLI 상태 추가
- doomemacs-config/bin/에서 이관

### Added: Backend 확장 시 문서 업데이트 체크리스트 (AGENTS.md)
- 새 Backend 추가 시 필수 업데이트 파일 4개 + 9개 체크항목
- 루트 MD 파일만 관리하는 전략 명문화

---

## [1.3.0] - 2026-02-03

### 🚀 문서 변환 도구 대폭 확장

#### Added: HWPX ↔ AsciiDoc 변환 (`hwpx2asciidoc/`)
- HWPX/OWPML → AsciiDoc 변환기 (테이블 병합 colspan/rowspan 보존)
- AsciiDoc → HWPX 역변환기 (정부 양식 호환)
- 왕복 변환 테스트 통과 (텍스트 무손실, 테이블 구조)
- `run.sh`: 통합 CLI (to-adoc, to-hwpx, to-html, to-pdf, test)
- OWPML 지원 (HWPX와 100% 동일 구조 확인)

#### Added: EPUB → Org 변환 (`epub2org/`)
- Calibre EPUB을 깔끔한 Org-mode로 변환
- 불필요한 마크업 자동 정리
- Gutenberg 프로젝트 책들 변환 (~/org/gutenberg)

#### Added: HTML → EPUB → Org 파이프라인 (`htmltoepub/`)
- Immersive Translate 번역 HTML → EPUB 변환
- PDF 원본 목차 구조 완벽 재현
- 책 제본용 PDF 출력 지원 (A4, 양면)
- Freeman Tilden "Interpreting Our Heritage" 변환 완료

### Fixed
- `unescape_asciidoc()` 호출 누락 수정 (텍스트 무손실 테스트 통과)

---

## [1.4.0] - 진행 중 🚀 **핵심 방향**

### 🎯 Org-mode 메타 포맷 → HWPX 변환 파이프라인

**비전**: Org-mode를 국가과제 제안서의 메타 포맷으로 활용

```
[여러 세부과제 Org 파일들]
        ↓ 취합/병합
[통합 Org 메타 포맷]
        ↓ AI 에이전트 편집 (용어/양식 통일)
[정리된 Org 파일]
        ↓ 변환
[HWPX] → 정부 시스템 업로드 (매크로 유지)
```

### Planned
- [ ] Org 메타 포맷 스펙 정의 (PROPERTIES, 키워드)
- [ ] Org → HWPX 템플릿 삽입 변환기
- [ ] AI 에이전트 편집 가이드라인
- [ ] 용어집 기반 자동 치환

**GitHub Issue**: [#2](https://github.com/junghan0611/memex-kb/issues/2)

---

## [1.2.0] - 2026-01-21

### Changed
- **Nix Flake 마이그레이션**: `shell.nix` → `flake.nix` (빌드 속도 개선)
- **보안 도구 교체**: secretlint (npm) → gitleaks (네이티브)
- **Threads 토큰 관리**: Graph API Explorer 기반 갱신 방식 도입

### Added
- `flake.nix`: Nix Flake 의존성 관리
- `flake.lock`: 재현 가능한 빌드
- `.envrc`: direnv 통합 (자동 환경 로드)
- `scripts/refresh_threads_token.py`: Threads OAuth 토큰 갱신
- gitleaks: Git 리포 및 파일 시스템 보안 스캔
- beads_rust (br) 워크플로우 통합

### Removed
- `shell.nix`: flake.nix로 대체
- `requirements.txt`: flake.nix로 대체
- `package.json`, `package-lock.json`: secretlint 제거

---

## [1.1.1] - 2025-11-07

### Added
- Threads SNS Adapter (아포리즘 내보내기)
- 댓글 자동 수집 기능
- 이미지 다운로드 (단일/캐러셀)
- Datetree 구조 (연도 → 월 → 일 → 포스트)
- Confluence Adapter (MIME 파싱, UTF-8 정규화)

### Fixed
- Org-mode 특수문자 이스케이프 처리
- 캐러셀 이미지 다운로드 (`children` 필드 추가)

---

## [1.1.0] - 2025-10-15

### Changed
- **범용 KB 시스템**: Google Docs 전용 → 다중 Backend 지원 아키텍처
- **Adapter 패턴 도입**: 확장 가능한 Backend 인터페이스 설계
- **철학 명확화**: "입문자를 위한 일정한 규칙" 제공

### Added
- 새로운 README.md (범용 지식베이스 비전)
- Backend Adapter 확장 가이드
- Dooray Wiki 지원 계획
- Confluence/Notion 지원 로드맵

---

## [1.0.0] - 2025-09-13

### 🎯 POC 완료 (Google Docs KB)

**목표**: Google Drive 기반 사내 기술문서 지식베이스 구축

### Added
- **Google Docs Adapter**: Pandoc 기반 Markdown 변환
- **Denote 파일명 규칙**: `timestamp--한글-제목__태그들.md`
- **규칙 기반 자동 분류**: YAML 설정으로 토큰 절약
- **Secretlint 통합**: 민감 정보 자동 탐지
- **Git 버전 관리**: 모든 변경사항 추적

### Technical Stack
- Python 3.8+
- Pandoc 2.x
- Google Drive API
- python-slugify
- PyYAML

### Features
- ✅ Shared Drive 권한 관리 해결
- ✅ 95% 변환 정확도
- ✅ 자동 문서 분류 (키워드 + 패턴 매칭)
- ✅ 보안 스캔 (Secretlint)
- ✅ 후처리 엔진 (스타일 태그 제거, 링크 복구)

### Performance
- 단일 문서 변환: 2-5초
- 10개 문서 배치: 30-50초
- 병목: Google API 호출 제한 (분당 60회)

---

## Development History (Before v1.0.0)

### 2025-09-13
- feat: POC 완료 - Pandoc 기반 Google Docs 변환 시스템
- feat: 보안 및 변환 품질 개선
- docs: POC 결과 문서화 및 체크포인트
- test: POC 성공 - Google Drive 공유 드라이브 연동
- feat: Google Drive 지식베이스 POC 초기 구현

---

## Migration Notes

**Reasons for Renaming**:
1. **범용성**: Google Docs 전용 → 다중 Backend 지원
2. **철학적 기반**: Vannevar Bush의 Memex 개념 구현
3. **확장성**: Adapter 패턴으로 새로운 Backend 추가 용이
4. **오픈소스**: 개인/상업적 용도 모두 사용 가능 (MIT License)

**What Changed**:
- Architecture: Monolithic → Adapter Pattern
- Backend: Google Docs only → Google Docs, Dooray, Confluence, etc.

**What Stayed the Same**:
- ✅ Denote 파일명 규칙
- ✅ 규칙 기반 자동 분류
- ✅ Git 버전 관리
- ✅ Secretlint 보안 스캔
- ✅ 모든 핵심 컴포넌트 (DenoteNamer, Categorizer)

---

## Roadmap

### v1.3 (Complete) ✅
- [x] HWPX ↔ AsciiDoc 변환기
- [x] EPUB → Org 변환기
- [x] HTML → EPUB → Org 파이프라인

### v1.4 (In Progress) 🚀 **핵심 방향**
- [ ] Org-mode 메타 포맷 → HWPX 파이프라인
- [ ] 국가과제 제안서 AI 협업 워크플로우
- [ ] 정부 양식 매크로 호환

### v2.0 (추후 검토)
- [ ] RAG 파이프라인 (경량화 방향 검토 중)
- [ ] 로컬 우선 임베딩

---

## Contributors

- **Junghan Kim** (junghanacs@gmail.com)
  - https://github.com/junghan0611/memex-kb
  - Initial POC (Google Docs KB)
  - Memex-KB Architecture & Design
  - Denote Integration

## License

MIT License - 개인/상업적 용도 모두 자유롭게 사용 가능

---

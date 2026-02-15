# Memex-KB: Universal Knowledge Base Converter

> "당신의 지식을 당신의 방식으로" - Denote 기반 범용 지식베이스 변환 시스템

**Memex-KB는 지식 관리의 시작점이자, RAG 파이프라인의 입구입니다.**

Legacy 문서(Google Docs, Threads, Confluence, HWPX...)를 **AI 협업 가능한 형태**로 변환합니다.

---

## 핵심 특징

| 특징 | 설명 |
|------|------|
| **Denote 파일명** | `timestamp--한글-제목__태그들.md` - 파싱 가능, 시간 정렬 |
| **규칙 기반 분류** | YAML 설정, LLM 비용 0원, 재현 가능 |
| **Git 버전 관리** | 모든 변환 과정 추적 |
| **Backend 중립** | Adapter 패턴으로 확장 |

→ 상세: [docs/PHILOSOPHY.md](docs/PHILOSOPHY.md)

---

## 지원 Backend

| Backend | 상태 | 설명 |
|---------|------|------|
| Google Docs | ✅ | Pandoc 기반 변환 |
| Threads SNS | ✅ | 아포리즘 → Org 통합 |
| Confluence | ✅ | MIME 파싱, UTF-8 정규화 |
| HWPX | ✅ | AsciiDoc 양방향 변환 |
| GitHub Stars | ✅ | Starred repos → BibTeX (Citar 호환) |
| Dooray Wiki | 🔧 | 개발 중 |

→ 상세: [docs/BACKENDS.md](docs/BACKENDS.md)

---

## Quick Start

**Nix Flake로 의존성 자동 관리** - 수동 설치 불필요!

```bash
# 환경 진입
nix develop
# 또는 direnv 사용
direnv allow

# 예시: Threads 내보내기
nix develop --command python scripts/threads_exporter.py --download-images

# 예시: Confluence 변환
nix develop --command python scripts/confluence_to_markdown.py document.doc

# 예시: GitHub Stars → BibTeX
./run.sh github-starred-export
```

→ Backend별 상세 가이드: [docs/BACKENDS.md](docs/BACKENDS.md)

---

## 로드맵

### v1.3 (2026-02-03, 완료)
- ✅ HWPX ↔ AsciiDoc 변환기
- ✅ EPUB → Org-mode 변환기
- ✅ HTML → EPUB 파이프라인

### v1.4 (진행 중) - **Org-mode 메타 포맷**

> "Org-mode를 국가과제 제안서의 메타 포맷으로"

```
[여러 세부과제 Org 파일들]
        ↓ 취합/병합
[통합 Org 메타 포맷]
        ↓ AI 에이전트 편집
[HWPX] → 정부 시스템 업로드
```

→ GitHub Issue: [#2](https://github.com/junghan0611/memex-kb/issues/2)

### v2.0 (추후 검토)
- 💭 Denote → Vector Embedding → RAG 파이프라인

---

## 문서

| 문서 | 내용 |
|------|------|
| [PHILOSOPHY.md](docs/PHILOSOPHY.md) | 철학, 왜 memex-kb, 대상 사용자 |
| [BACKENDS.md](docs/BACKENDS.md) | Backend별 연동 가이드 |
| [DENOTE-RULES.md](docs/DENOTE-RULES.md) | Denote 파일명/분류 규칙 |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | Adapter 확장 가이드 |
| [AGENTS.md](AGENTS.md) | Claude Code 에이전트 가이드 |
| [CHANGELOG.md](CHANGELOG.md) | 변경 이력 |

---

## 기여하기

새로운 Backend Adapter 기여를 환영합니다!

1. Fork → Feature 브랜치 → PR
2. [DEVELOPMENT.md](docs/DEVELOPMENT.md) 참조

---

## 연락처

- **개발자**: Junghan Kim (junghanacs)
- **GitHub**: [junghan0611](https://github.com/junghan0611)
- **블로그**: [힣's 디지털가든](https://notes.junghanacs.com)

---

**버전**: 1.3.1 | **라이선스**: MIT | **상태**: 🟢 활발히 개발 중

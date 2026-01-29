# 🔒 보안 설정 가이드

## gitleaks 설정

이 프로젝트는 **gitleaks**를 사용하여 민감한 정보가 실수로 커밋되는 것을 방지합니다.

### 사용법

```bash
# Git 리포지토리 스캔 (커밋 이력 포함)
gitleaks detect

# 파일 시스템만 스캔 (git 무시)
gitleaks detect --no-git

# 특정 경로만 스캔
gitleaks detect --source ./docs

# 자세한 출력
gitleaks detect -v

# 디지털 가든 배포 전 스캔
gitleaks detect --no-git --source ./docs
```

### Nix 환경에서 실행

```bash
# direnv 활성화 시 (자동)
gitleaks detect

# 수동 환경 진입
nix develop --command gitleaks detect
```

### 감지 패턴

gitleaks는 다음을 포함한 160+ 패턴을 자동 감지합니다:

- **API Keys**: Google, AWS, Azure, GitHub, etc.
- **Tokens**: OAuth, JWT, Session tokens
- **Secrets**: Private keys, Passwords
- **Credentials**: Database connection strings
- **Cloud**: Service account JSON files

### 설정 커스터마이징 (선택)

`.gitleaks.toml` 파일로 규칙 커스터마이징 가능:

```toml
[allowlist]
paths = [
    '''config/\.env\.example''',
    '''docs/.*\.org''',
]

[[rules]]
description = "Custom API Key Pattern"
regex = '''my-custom-api-key-[a-zA-Z0-9]{32}'''
```

---

## Git 보안

### 민감한 파일 관리

`.gitignore`에 다음 파일들이 포함되어 있는지 확인:

```gitignore
# 환경 변수
config/.env
config/.env.threads
.env
.env.*
!.env.example
!.env.*.example

# API 인증
config/credentials.json
config/*.json
!config/categories.yaml

# 로그
logs/

# 이미지 (용량 이슈)
docs/images/threads/
```

### 커밋 전 체크리스트

```bash
# 1. 변경 파일 확인
git status

# 2. 보안 스캔
gitleaks detect

# 3. 스테이징
git add <files>

# 4. 커밋
git commit -m "..."
```

---

## 환경 변수 보안

### .env 파일 구조

```bash
# config/.env (gitignored)

# Google Docs
GOOGLE_APPLICATION_CREDENTIALS=config/credentials.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id

# Threads API (60일마다 갱신 필요)
THREADS_ACCESS_TOKEN=your_access_token
USER_ID=your_user_id
APP_ID=your_app_id
APP_SECRET=your_app_secret
```

### 권장사항

1. **환경변수 사용**: 하드코딩 금지
2. **예시 파일 제공**: `.env.example` 템플릿 유지
3. **Private 저장소**: 민감한 프로젝트는 Private 권장
4. **정기 스캔**: 커밋 전 gitleaks 실행
5. **토큰 갱신**: Threads 토큰 60일마다 갱신

---

## secretlint에서 마이그레이션

> v1.2.0부터 secretlint (npm)를 gitleaks (네이티브)로 대체했습니다.

### 왜 gitleaks인가?

| 항목 | secretlint | gitleaks |
|------|------------|----------|
| 의존성 | npm (Node.js) | 네이티브 바이너리 |
| 속도 | 중간 | 빠름 |
| 설정 | 복잡 | 간단 |
| 패턴 | 플러그인 기반 | 내장 160+ |
| Nix 통합 | 어려움 | 쉬움 |

### 마이그레이션 완료 (v1.2.0)

- ✅ `package.json`, `package-lock.json` 삭제
- ✅ `.secretlintrc.json` 불필요
- ✅ `flake.nix`에 gitleaks 포함
- ✅ 동일 수준의 보안 감지

---

## 체크리스트

- [x] gitleaks 설치 (flake.nix)
- [x] .gitignore 업데이트
- [x] secretlint → gitleaks 마이그레이션
- [ ] Pre-commit hook 설정 (선택사항)
- [ ] CI/CD 통합 (선택사항)

---

**Last Updated**: 2026-01-29
**Version**: 1.2.0

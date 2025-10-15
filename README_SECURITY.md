# 🔒 보안 설정 가이드

## Secretlint 설정

이 프로젝트는 secretlint를 사용하여 민감한 정보가 실수로 커밋되는 것을 방지합니다.

### 설치

```bash
npm install -D @secretlint/secretlint-rule-preset-recommend @secretlint/secretlint-rule-pattern
```

### 사용법

```bash
# 스캔 실행
npx secretlint "**/*"

# 특정 파일 스캔
npx secretlint config/
```

### 감지 패턴

- Google API Keys
- HTTP Tokens
- Service Account JSON 파일
- 기타 민감한 패턴

## Git 보안

### Read-only 설정 (선택사항)

민감한 정보 보호를 위해 리포지토리를 읽기 전용으로 설정할 수 있습니다:

```bash
# 원격 저장소 URL을 HTTPS로 변경 (읽기 전용)
git remote set-url origin https://github.com/username/repo.git

# 또는 별도의 읽기 전용 remote 추가
git remote add readonly https://github.com/username/repo.git
```

### 민감한 파일 관리

`.gitignore`에 다음 파일들이 포함되어 있는지 확인:

- `config/*.json` - Service Account 키
- `config/.env` - 환경변수
- `logs/` - 로그 파일

## Markdown 변환 품질 개선사항

### 해결된 문제들

1. **불필요한 스타일 태그 제거**
   - `{.underline}`, `{.bold}` 등 제거

2. **이스케이프 문자 정리**
   - 불필요한 백슬래시 제거

3. **링크 줄바꿈 수정**
   - 링크 텍스트와 URL이 분리되지 않도록 수정

4. **특수문자 정리**
   - 헤딩 앞의 이상한 문자 제거

## 체크리스트

- [ ] Secretlint 설치 및 설정
- [x] .gitignore 업데이트
- [x] Pandoc 후처리 개선
- [ ] Pre-commit hook 설정 (선택사항)

---

**Last Updated**: 2025-10-15

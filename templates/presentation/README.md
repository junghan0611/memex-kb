# Quarto Presentation Template

Reveal.js 기반 프레젠테이션 템플릿입니다.

## 사용법

```bash
# 1. 템플릿 복사
cp -r templates/presentation/ my-presentation/
cd my-presentation/

# 2. template.qmd 수정
# - title, subtitle, author, date 수정
# - 슬라이드 내용 작성

# 3. 미리보기 (브라우저 자동 새로고침)
quarto preview template.qmd

# 4. HTML로 렌더링
quarto render template.qmd
# → _output/template.html 생성
```

## 파일 구조

```
presentation/
├── _quarto.yml    # 프로젝트 설정 (해상도, 테마 등)
├── template.qmd   # 메인 프레젠테이션 파일
├── custom.scss    # 커스텀 스타일 (색상, 폰트)
├── images/        # 이미지 폴더
│   └── .gitkeep
└── .gitignore     # Quarto 출력 제외
```

## 커스터마이징

### 색상 변경

`custom.scss`에서 색상 변수를 수정:

```scss
// 메인 색상
$link-color: #0984e3;        // 링크, 강조색
$body-color: #2d3436;        // 본문 텍스트

// 표 헤더
.reveal table th {
  background: #0984e3;       // 테이블 헤더 배경
}
```

### 로고 추가

1. `images/logo.png` 파일 추가
2. `_quarto.yml`과 `template.qmd`에서 logo 주석 해제:
   ```yaml
   logo: images/logo.png
   ```

### 푸터 변경

`_quarto.yml`에서 수정:
```yaml
footer: "Your Organization Name"
```

## 슬라이드 문법

### 섹션 제목
```markdown
# 섹션 제목 {.section}
```

### 2단 레이아웃
```markdown
:::: {.columns}
::: {.column width="50%"}
왼쪽 내용
:::
::: {.column width="50%"}
오른쪽 내용
:::
::::
```

### 강조 박스
```markdown
::: {.callout-note}
참고 사항
:::

::: {.callout-warning}
주의 사항
:::
```

### 진행률 바
```markdown
::: {.progress-bar}
::: {.progress-bar-fill style="width: 75%"}
:::
:::
```

## 출력 형식

- **기본**: HTML (Reveal.js)
- **PDF**: `quarto render template.qmd --to pdf` (추가 설정 필요)

## 요구사항

- Quarto 1.3+
- 웹 브라우저 (미리보기용)

---

**참고**: [Quarto Presentations Guide](https://quarto.org/docs/presentations/revealjs/)

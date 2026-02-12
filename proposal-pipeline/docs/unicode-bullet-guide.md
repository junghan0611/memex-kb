# 유니코드 불릿/기호 선택 가이드

## 현재 문서 상태 (제안서-통합-5장.org)

### 사용 중인 특수문자

| 문자 | 유니코드 | 이름 | 횟수 | 용도 | 호환성 |
|------|----------|------|------|------|--------|
| `·` | U+00B7 | MIDDLE DOT | 339 | 가운뎃점 "홈·가전", 표 내 구분자 | 최상 (Latin-1) |
| `→` | U+2192 | RIGHTWARDS ARROW | 196 | "TRL 4→5" | 최상 |
| `□` | U+25A1 | WHITE SQUARE | 71 | 헤딩 불릿 `*** □ 배경` | 양호 |
| `⋅` | U+22C5 | DOT OPERATOR | 61 | 소제목 불릿 `****** ⋅동작원리` | 양호 (수학기호) |
| `↑` | U+2191 | UPWARDS ARROW | 15 | "정확도 88%↑" | 최상 |
| `○` | U+25CB | WHITE CIRCLE | 10 | 인명 마스킹 "박○○" | 양호 |
| `↓` | U+2193 | DOWNWARDS ARROW | 1 | 감소 표시 | 최상 |

### ODT 불릿 리스트 스타일

- `List_20_1`, `OrgBulletedList`: 전 레벨 `•` (U+2022 BULLET)

---

## 불릿 문자 비교표

### 점(Dot) 계열

| 문자 | 유니코드 | 이름 | Org/MD 호환 | ODT 호환 | HWP 호환 | 비고 |
|------|----------|------|:-----------:|:--------:|:--------:|------|
| `·` | U+00B7 | MIDDLE DOT | O | O | O | 가운뎃점, Latin-1 범위, **가장 안전** |
| `•` | U+2022 | BULLET | O | O | O | 표준 불릿, ODT 리스트 기본값 |
| `⋅` | U+22C5 | DOT OPERATOR | O | O | △ | 수학기호, 일부 한글 폰트 미지원 가능 |
| `∙` | U+2219 | BULLET OPERATOR | O | O | △ | 수학기호, ⋅보다 약간 큼 |
| `‣` | U+2023 | TRIANGULAR BULLET | O | O | △ | 삼각 불릿, 지원 폰트 적음 |
| `⁃` | U+2043 | HYPHEN BULLET | △ | O | △ | 하이픈 불릿, 폰트 지원 제한적 |

### 도형(Shape) 계열

| 문자 | 유니코드 | 이름 | Org/MD 호환 | ODT 호환 | HWP 호환 | 비고 |
|------|----------|------|:-----------:|:--------:|:--------:|------|
| `□` | U+25A1 | WHITE SQUARE | O | O | O | 빈 사각형, CJK 폰트에 대부분 포함 |
| `■` | U+25A0 | BLACK SQUARE | O | O | O | 채운 사각형 |
| `▪` | U+25AA | BLACK SMALL SQUARE | O | O | △ | 작은 사각형, 일부 폰트 미지원 |
| `○` | U+25CB | WHITE CIRCLE | O | O | O | 빈 원, 한글 인명 마스킹 표준 |
| `●` | U+25CF | BLACK CIRCLE | O | O | O | 채운 원 |
| `◆` | U+25C6 | BLACK DIAMOND | O | O | O | 채운 마름모 |
| `◇` | U+25C7 | WHITE DIAMOND | O | O | O | 빈 마름모 |
| `▶` | U+25B6 | BLACK RIGHT TRIANGLE | O | O | O | 삼각형 |

### 화살표 계열

| 문자 | 유니코드 | 이름 | 호환성 | 비고 |
|------|----------|------|--------|------|
| `→` | U+2192 | RIGHTWARDS ARROW | 최상 | 현재 사용 중, **가장 안전** |
| `←` | U+2190 | LEFTWARDS ARROW | 최상 | |
| `↑` | U+2191 | UPWARDS ARROW | 최상 | 현재 사용 중 |
| `↓` | U+2193 | DOWNWARDS ARROW | 최상 | |
| `⇒` | U+21D2 | RIGHTWARDS DOUBLE ARROW | 양호 | 논리 "이면" |
| `⇐` | U+21D0 | LEFTWARDS DOUBLE ARROW | 양호 | |

---

## Emacs Org-mode 불릿 체계

### Org-mode 기본 리스트 마커

```
- 항목 (하이픈)               ← 가장 기본, 모든 내보내기 호환
+ 항목 (플러스)               ← 하이픈과 동일
* 항목 (별표, 최상위만)       ← 헤딩과 혼동 주의
1. 번호 항목                  ← 순서 리스트
1) 번호 항목                  ← 순서 리스트 (대안)
```

### Org-mode 헤딩 (내보내기 시)

```
* 레벨1        → ODT: Heading_20_1
** 레벨2       → ODT: Heading_20_2
*** 레벨3      → ODT: Heading_20_3
**** 레벨4     → ODT: Heading_20_4
```

- Org 자체에는 헤딩 불릿 개념 없음 (별표가 레벨 표시)
- 현재 문서에서 `□`, `⋅`는 **원본 HWPX에서 가져온 장식용 불릿**
- ODT 내보내기 시 이들은 그냥 텍스트로 출력됨 (리스트 스타일 아님)

---

## 폰트 현황

### 현재 reference.odt 폰트

| 폰트 | 용도 | 사용 횟수 |
|------|------|----------|
| **Dotum (돋움)** | 본문, 표, 헤딩 전체 | 46회 |
| OpenSymbol | 불릿 리스트 기호 | 10회 |
| Courier New | 코드 블록 (OrgFixedWidthBlock 등) | 4회 |
| NSimSun | CJK fallback | 4회 |
| Arial1 | 서양 글꼴 fallback | 1회 |

### 한글 폰트 유니코드 지원 비교

| 폰트 | 출처 | `·` B7 | `•` 2022 | `⋅` 22C5 | `□` 25A1 | `○` 25CB | `→` 2192 | 비고 |
|------|------|:------:|:--------:|:--------:|:--------:|:--------:|:--------:|------|
| **Dotum (돋움)** | Windows/HWP | O | O | O | O | O | O | 현재 사용 중 |
| **Batang (바탕)** | Windows/HWP | O | O | O | O | O | O | 명조체 |
| **Malgun Gothic (맑은 고딕)** | Windows 7+ | O | O | O | O | O | O | 현대 고딕 |
| **Noto Sans CJK KR** | Google | O | O | O | O | O | O | 오픈소스, 범용 |
| **NanumGothic (나눔고딕)** | Naver | O | O | △ | O | O | O | 수학기호 일부 미지원 |
| **HY헤드라인M** | 한양시스템 | O | O | △ | O | O | O | HWP 번들 |

### 변환 파이프라인별 주의점

```
Org → ODT: reference.odt 폰트 설정 사용 (현재 Dotum)
ODT → DOC: LibreOffice 변환, 폰트 유지
DOC → HWP: 한컴오피스 변환, Dotum이 HWP 기본 폰트라 안전
```

**주의**: Noto Sans CJK KR → HWP 변환 시 폰트가 없으면 대체됨.
Dotum은 HWP에서 가져온 폰트이므로 HWP 재변환 시 **가장 안전한 선택**.

---

## 권장 사항 (향후 수정 시)

### 안전한 불릿 조합 (3단계)

```
레벨1 헤딩 장식: □ (U+25A1 WHITE SQUARE) — 현재 사용 중, 유지
레벨2 소제목:    · (U+00B7 MIDDLE DOT) — ⋅(U+22C5) 대신 권장
표 내 구분자:    · (U+00B7 MIDDLE DOT) — 현재 사용 중, 유지
리스트 불릿:     - (하이픈) — Org 기본, 변환 안전
```

### `⋅` → `·` 교체 검토

- `⋅` (U+22C5 DOT OPERATOR): 수학기호, NanumGothic 등 일부 폰트 미지원
- `·` (U+00B7 MIDDLE DOT): Latin-1 범위, **모든 폰트에서 지원**
- 현재 61건, 전부 소제목 불릿 (`****** ⋅동작 원리`)
- 시각 차이 거의 없음, 호환성은 `·`가 우위
- 교체 명령: `(replace-string "⋅" "·")` (Emacs) 또는 Python 일괄 치환

### 폰트 변경 시 체크리스트

- [ ] reference.odt의 Dotum → 새 폰트로 일괄 교체
- [ ] 새 폰트가 위 유니코드 문자 전부 포함하는지 확인
- [ ] ODT → DOC → HWP 파이프라인에서 폰트 매핑 테스트
- [ ] 특히 `⋅` (U+22C5), `▪` (U+25AA) 같은 수학/소형 기호 렌더링 확인

---

*작성: 2026-02-12 — 제안서-통합-5장 유니코드 기호 분석 기준*

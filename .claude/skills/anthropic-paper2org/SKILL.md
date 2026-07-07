---
name: anthropic-paper2org
description: "Anthropic Distill(transformer-circuits.pub) HTML 공개논문을 Org 로 재현가능하게 가져오는 변환 파이프라인 (memex-kb). 수식은 <d-math> LaTeX 소스 무손실, 인용은 org-cite, 각주 보존, 그림은 정적 PNG 임베드 + JS 인터랙티브는 캡션+라이브링크 대체. 범용 HTML→org 아님(Anthropic Distill 전용). org→HTML 왕복으로 '논문 쓰기 포맷=org' 실증. Use when transformer-circuits.pub 논문을 org 로 담을 때, J-space/jacobian-lens 같은 Anthropic HTML 논문 아카이브, HTML↔org 왕복 변환, paper2org 명령을 쓸 때. Triggers: 'paper2org', 'transformer-circuits', 'distill 논문', 'anthropic 논문 org', 'j-space 논문', 'jacobian-lens', 'HTML 논문 변환', '논문 org 로', 'org html 왕복'."
user_invocable: true
---

# anthropic-paper2org — Anthropic HTML 논문 → Org

Repo: `~/repos/gh/memex-kb`. `run.sh paper2org`가 *명령*을 덮고, 이 파일이 *판단·규칙·함정*을 덮는다.
로직 런타임 SSOT = `scripts/anthropic_paper_to_org.py`. 작업축/로드맵은 `NEXT.md`.

## 멘탈 모델 — 왜 하는가

GLG 원칙: **논문을 PDF로 올리면 활용이 안 된다.** transformer-circuits.pub 논문은 **HTML**(PDF 아님)
→ 재활용 가능 = "논문은 이렇게 써야 한다"의 실증. 목표는 **왕복**:

```
Anthropic HTML 논문 (Distill 템플릿)
      ↓  paper2org (이 스킬) — 수식/그림/인용/각주 보존
Org (아카이브·편집 가능한 SSOT)
      ↓  ox-html / 자체 템플릿
HTML 로 재출판 (GLG 가 org 로 논문 쓰면 그대로 웹으로)
```

**문서 변환이 본질, 논문 정독이 목적 아님.** 해설/독후감은 별개 축(다른 담당자).

## ⚠️ 범위 고정 — 다음 세션이 넓히지 말 것

**Anthropic Distill 템플릿(`<d-article>`/`<d-math>`/`<d-cite>`/`<d-footnote>`) 전용.**
범용 HTML→org 로 넓히면 지금 커버 못 하고 산으로 간다(GLG 방침). 다른 사이트 HTML 은 대상 아님 —
`_isolate()` 가 `<d-article>` 못 찾으면 즉시 종료한다. 새 Anthropic 논문은 같은 템플릿이라 그대로 먹는다.

## 파이프라인 — 조합 도구 (pandoc 은 "일부만")

pandoc 은 LLM 이전 도구다. **골격 추출에만** 쓰고 나머지는 커스텀 로직으로 조합한다.

```
fetch → isolate <d-article> → protect(Distill 태그 → sentinel) → pandoc HTML→org
      → restore(math/cite/footnote) → assemble(org 헤더 + 경로/레벨 보정)
```

- **isolate**: `<d-article>…</d-article>` 만 자른다. visual-toc `<nav>`(섹션 썸네일 내비)는 버린다.
  첫 `<h2>`부터가 본문(그 앞 제목/byline 은 헤더로 따로 추출).
- **protect**: Distill 태그를 `ZZ<KIND><n>ZZ` sentinel(순수 대문자+숫자 → pandoc 이 안 건드림)로 빼돌린다.
  pandoc `--wrap=none` 필수(줄바꿈이 sentinel 쪼개면 복원 실패).
- **restore**: sentinel → 실제 org 문법. 각주 INNER 는 **따로 pandoc** 후 한 줄로 접어 `[fn:N: …]`.
- **assemble**: `#+title/#+author/#+date/#+source/#+bibliography/#+cite_export` 헤더. 헤딩 한 단계 승급
  (본문 최상위가 `<h2>`=`**` → `*`). 이미지 경로 `./png/` → `file:png/`.

### Distill 태그별 처리 (핵심 지식)

| 태그 | HTML | Org 결과 | 왜 |
|---|---|---|---|
| 인라인 수식 | `<d-math>W_U</d-math>` | `\(W_U\)` | **LaTeX 소스가 태그 안에 그대로** (KaTeX 렌더 아님) → 무손실 |
| 디스플레이 수식 | `<d-math block>…</d-math>` | `\[…\]` | 인라인보다 **먼저** 치환(안 그러면 `<d-math`가 겹침) |
| 인용 | `<d-cite key="a,b">` | `[cite:@a;@b]` | comma 분리 bibtex 키 → org-cite. `bibliography.bib` 같이 받음 |
| 각주 | `<d-footnote>…</d-footnote>` | `[fn:N: …]` | INNER 에 d-cite/d-math 중첩 → cite/math 를 **먼저** 보호해야 함 |

### 그림 2분기 — 이 스킬의 핵심 판단

Distill 논문은 그림이 두 종류다. **개수를 반드시 검수**한다(J-space: 정적 10 / 인터랙티브 84).

- **정적 PNG** (본문 `<figure>` 안 `<img src="./png/…">`): 다운로드 후 `[[file:png/…]]` + `#+caption` 임베드.
  단 **visual-toc 내비 썸네일**(`<nav>` 안)은 본문 그림 아님 → 버린다. `fetch()`는 nav 바깥 img 만 받는다.
- **JS 렌더 인터랙티브** (`<figure>` 에 `<img>` 없음, bundle.js 가 d3 로 그림): org 에 못 담는다
  → **캡션 + `원문#앵커` 라이브 링크로 대체**. 각 `<figure id="fig-…">`의 id 가 앵커. 이게 "못 담는 건
  대체" 규칙(scanbook 과 같은 철학). 스크린샷이 꼭 필요하면 브라우저로 따로 떠서 붙인다(수동, 스킬 밖).

## org → HTML 왕복 (2단계)

`pandoc -f org -t html5 --mathjax --standalone` 로 구조·수식(MathJax)·이미지·헤딩앵커 전부 생존 확인됨
= "논문 쓰기 포맷 = org" 성립. **단 pandoc org 리더는 `[cite:@key]`/`#+bibliography` 를 못 읽는다**(평문으로 남음).
→ 인용까지 제대로 렌더하려면 **ox-html + org-cite/citeproc**(Emacs)이 프로덕션 경로. 왕복 "증명"은 pandoc,
"출판"은 ox-html.

## org → ArXiv급 PDF (acmart) — `paper2org-pdf`

`--acmart` 가 `<name>.acmart.org` 를 같이 낸다(웹 org 의 자매). 이걸 `templates/arxiv-acm` 의 acmart
파이프(org→LaTeX→PDF)에 물려 **ArXiv급 학술 PDF** 를 만든다. 검증됨: J-space = **93쪽, 인용 155개 bibtex
전부 해석, 수식·그림 정상**.

**브리지(웹 org → acmart org)가 하는 일** — `assemble_acmart()`:
- 헤더를 acmart 관례로: `#+OPTIONS: title:nil author:nil` + `#+LATEX_CLASS: acmart [manuscript, nonacm]`
  (**단일컬럼 manuscript** — 넓은 수식/그림에 2컬럼 sigconf 보다 안전) + `\settopmatter{printacmref=false}` + `\setcopyright{none}`.
- **저자 → acmart 프리앰블 자동생성**: `#+BEGIN_EXPORT latex` 안에 `\title` + N명 `\author`/`\affiliation`
  (affiliation = **Anthropic 고정** — "앤트로픽 논문 변환기") + `\maketitle`.
- **인용 org-cite → natbib**: `[cite:@a;@b]` → `\cite{a,b}`. 끝에 `\bibliographystyle{ACM-Reference-Format}` +
  `\bibliography{bibliography}`(bibliography.bib). latexmk 가 bibtex 자동 다중패스.
- 이미지 폭맞춤 `\setkeys{Gin}{width=\linewidth,keepaspectratio}`(2컬럼 오버플로 방지).

**빌드**: `./run.sh paper2org-pdf <URL> --name <name>` → acmart org 생성 후
`nix-shell` (texlive scheme-full + emacs) 안에서 `scripts/paper_build.el` 로 `org-latex-export-to-pdf`.
산출 `out/anthropic-paper/<name>/<name>.acmart.pdf`.

**`paper_build.el` 가 build.el 과 다른 점(둘 다 필요)**:
- `org-export-with-broken-links t` — 원문의 **미해결 fig 참조**(`[[#fig-..][??]]`, HTML 에도 `??`)에서
  ox-latex 가 export 를 **중단(abort)** 하는 걸 막는다. 없으면 "Unable to resolve link" 로 실패.
- `backtrace-on-error-noninteractive nil` — 에러 시 org AST 전체 덤프로 **로그가 수백 MB** 터지는 것 방지.

**함정/한계(PDF)**:
- **texlive scheme-full 은 494MB 다운로드(1회, 이후 캐시)** — acmart 엔 과잉. 슬림화(scheme-basic+acmart+deps)는
  후속 최적화(의존성 누락 토끼굴 주의). 지금은 GLG 플레이크(geworfen/docs·arxiv-acm)가 핀한 scheme-full 그대로.
- 원문의 깨진 `??` 참조는 PDF 에서 **빈 괄호/공백**으로 렌더된다(소스 문제, 우리 버그 아님). 필요하면 브리지에서
  `[[#anchor][desc]]`(비헤딩 앵커) → 평문화로 개선 가능(현재 미적용).
- `latexmk -f` 라 일부 경고(Overfull/undefined)를 강행 통과해 "produced with errors" 떠도 PDF 는 정상 생성.
- amssymb 는 acmart(newtx) 충돌로 **제거**(build.el 관례). `\mathbb` 등은 newtxmath 가 제공.

## ⚠️ 저작권 — 산출물 커밋 금지

논문 전문·그림은 **Anthropic 저작물**이다. memex-kb(공개 repo)엔 **변환 로직만 커밋**하고 산출물은 안 담는다:
`out/anthropic-paper/` 는 `.gitignore`. org/png/html 은 로컬 재현물(개인 아카이브/연구용). 재현은 `run.sh paper2org`
한 방이면 언제든 다시 만들어진다 = 굳이 커밋할 이유 없음.

## jacobian-lens 담당자 워크플로 (로드맵 4단계)

`~/repos/gh/jacobian-lens`(GLG fork `junghan0611/*`, public)에 담당자를 세워 org 산출물을 담을 때:

1. 담당자는 이 스킬을 읽고 `run.sh paper2org <URL> --name jspace --fetch` 실행.
2. `out/anthropic-paper/jspace/`(org+png+bib) 를 jacobian-lens repo 로 옮긴다.
3. **⚠️ identity 훅**: jacobian-lens 는 public `junghan0611/*` → 커밋 diff 에 GLG 식별자(이름/블로그/가든 URL)가
   들어가면 훅이 **차단**한다. 논문 org 본문엔 GLG 식별자 없음(안전)이나, 담당자가 붙이는 핸드오프/서문 메모엔
   식별자 넣지 말 것. 넣어야 하면 `PRIVATE.md`(gitignore) 로.
4. 원문 저작권 존중: jacobian-lens(Anthropic 코드의 fork)에 논문 org 를 담는 건 GLG 판단 — 재배포 성격이면
   `#+source` 링크 + "개인 아카이브" 명시 유지.

## 검수 (실행 후 자동 리포트 + 눈검수)

`run.sh paper2org` 끝에 카운트 리포트가 뜬다. **원문 grep 수와 대조**:
- 헤딩 = h2+h3+h4 (byline h3 3개 제외) · 인라인수식 = `<d-math>` 수 · 디스플레이 = `<d-math block>` 수
- 인용 = `<d-cite>` 수 · 각주 = `<d-footnote>` 수 · 임베드이미지 = 본문(nav 밖) img 수 · 인터랙티브 = img 없는 figure 수
- **잔여 sentinel/태그 = 0 필수** (0 아니면 protect/restore 짝 깨진 것 → 버그).

눈검수: 헤딩 승급(`* 대절`/`** 소절`), CUSTOM_ID = 원본 앵커(`intro` 등, 슬러그 아님 → 상호참조 해석),
디스플레이 수식 `\[…\]` LaTeX, 각주 `[fn:1: …중첩 인용까지]`, 인터랙티브 그림 캡션+링크.

## 함정

- **pandoc `--wrap=none` 빼면** sentinel 이 줄바꿈으로 쪼개져 복원 실패. 반드시 유지.
- **수식 치환 순서**: 디스플레이(`block`) → 인라인 → 인용 → 각주. 순서 바뀌면 겹쳐서 깨진다.
- **CUSTOM_ID**: 앵커 id 를 헤딩으로 안 올리면(`_lift_heading_ids`) pandoc 이 제목 슬러그로 id 를 새로 만들어
  본문 `[[#intro]]` 상호참조가 다 깨진다.
- 원문 자체의 깨진 참조(`[[#fig-…][??]]`, 미해결 `??`)는 **소스 그대로** — 우리 버그 아님(HTML 에도 `??`).
- pandoc 은 flake.nix 에 있음 → `nix develop --command` 로 실행(run.sh 가 래핑).

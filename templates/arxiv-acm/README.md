# Org-mode to ArXiv (ACM format) Pipeline Template

이 디렉토리는 Emacs `org-mode` 파일을 기반으로 ACM의 `acmart` LaTeX 클래스를 활용하여 ArXiv 제출용 논문 PDF를 생성하는 파이프라인의 완성된 샘플입니다.

## 파일 구성

- `sample.org`: 본문이 작성된 org-mode 소스 파일. `acmart` 특유의 양식(저자, 초록, 키워드, `\maketitle`)을 처리하기 위한 설정 포함
- `sample.bib`: 참고문헌 관리를 위한 BibTeX 데이터 파일
- `build.el`: `ox-latex` 설정 및 `acmart` 클래스를 org-mode에 인식시키고 PDF를 익스포트하는 Emacs Lisp 스크립트
- `sample_fig.png`: 그림 삽입을 위한 샘플 이미지

## 빌드 방법

터미널에서 아래의 명령어를 실행하면 `sample.pdf`가 생성됩니다:

```bash
# 기본 방법
emacs -Q --batch --script build.el sample.org

# latexmk를 사용하므로 다중 컴파일(참고문헌 등)이 자동으로 처리됩니다.
```

## 핵심 노하우 (org-mode & acmart 조합)

`acmart` 문서 클래스는 매우 엄격한 순서를 요구합니다.
특히 제목, 저자 정보(`\author`, `\affiliation`), 그리고 요약(`abstract`)이 반드시 `\maketitle` 명령 **이전**에 선언되어야 합니다.
이를 위해 `sample.org`에서는 org-mode의 기본 제목/저자 익스포트를 끄고( `#+OPTIONS: title:nil author:nil` ),
`#+BEGIN_EXPORT latex ... #+END_EXPORT` 블록 안에서 `acmart` 전용 양식을 직접 기재하는 패턴을 사용합니다.

## NixOS 환경 구성 (texlive)

NixOS 환경에서 `acmart`와 관련 의존성을 갖춘 빌드 환경을 마련하려면,
`flake.nix` (또는 `shell.nix`)에 다음과 같이 `texlive.combine`을 설정하세요:

```nix
{
  description = "ACM ArXiv Paper Environment";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }: {
    devShells.x86_64-linux.default = let
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
      tex = pkgs.texlive.combine {
        # scheme-full을 사용하면 대부분의 의존성(acmart, 폰트, biber 등)이 해결됩니다.
        inherit (pkgs.texlive) scheme-full latexmk;
      };
    in pkgs.mkShell {
      buildInputs = [
        tex
        pkgs.emacs
      ];
    };
  };
}
```

또는 디스크 공간이 걱정된다면 최소 의존성으로만 구성할 수 있습니다:
```nix
      tex = pkgs.texlive.combine {
        inherit (pkgs.texlive) scheme-basic acmart latexmk
        cmap mweights xcolor microtype libertine inconsolata
        newtx txfonts fontaxes biber biblatex natbib;
      };
```

## ArXiv 제출 시 유의사항

ArXiv에 논문을 제출할 때는 PDF 파일 자체가 아니라 소스 파일(.tex, .bib, 이미지)을 압축해서 업로드해야 합니다.
`build.el`을 통해 생성된 `sample.tex` 파일과 `sample.bib` 그리고 관련된 이미지 파일들을 묶어서 제출하면 됩니다.
`acmart` 클래스의 경우 `[sigconf, authordraft, nonacm]` 옵션을 주어 ArXiv 친화적인 포맷으로 조절할 수 있습니다 (ACM 관련 저작권 문구 등 제거).

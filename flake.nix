{
  description = "memex-kb - Universal Knowledge Base Converter";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # OCR 경로는 marker(surya, uv venv)로 일원화됨. tesseract/ocrmypdf는
        # 한글 스캔 품질이 사용 불가라 제거했다(2026-06-02 smoke). marker/STRATEGY.md 참조.

        # PyPI에만 있는 python-hwpx (nixpkgs에 없음)
        python-hwpx = pkgs.python312Packages.buildPythonPackage rec {
          pname = "python-hwpx";
          version = "1.9";
          format = "wheel";
          src = pkgs.fetchurl {
            url = "https://files.pythonhosted.org/packages/27/08/c757b68fb3d77ff0b2aedee08856cd89ef85cec1b8a62d29f54bd05938a8/python_hwpx-1.9-py3-none-any.whl";
            sha256 = "0xfy3cycp9708sp568gy6708xpihqrhd7d5n3g9ki8hiqq6g6zq9";
          };
          propagatedBuildInputs = [ pkgs.python312Packages.lxml ];
          doCheck = false;
        };

        pythonEnv = pkgs.python312.withPackages (ps: with ps; [
          # Google API
          google-api-python-client
          google-auth
          google-auth-oauthlib
          google-auth-httplib2

          # 문서 처리
          markdown
          beautifulsoup4
          pyyaml
          python-slugify
          python-dotenv
          click
          colorlog
          python-dateutil

          # HTTP (토큰 갱신용)
          requests

          # HWPX 처리
          lxml
          python-hwpx

          # scanpdf2org: 스캔 PDF 페이지 → 이미지 렌더 (vision 전사용, OCR 아님)
          pymupdf
          pillow
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.pandoc
            pkgs.rclone
            pkgs.git
            pkgs.jq
            pkgs.gitleaks  # 비밀 유출 탐지
            pkgs.quarto    # 문서/프레젠테이션 도구

            # PDF / EPUB CLI surface for reproducible memex-kb work.
            pkgs.mupdf      # mutool: PDF inspect/extract/manipulate
            pkgs.poppler-utils # pdftotext/pdfinfo/pdfimages (born-digital PDF helpers)
            pkgs.epubcheck  # EPUB validation
            pkgs.zip        # ox-epub.el이 EPUB 패키징에 system zip 호출 (zip 미설치 환경 대비)
            pkgs.unzip      # EPUB 내부 검사(압축 해제)
            pkgs.uv         # marker-pdf venv/lock runner; same nixpkgs lock as nixos-config avoids duplicate store paths
            # asciidoctor는 nixos-config에서 시스템 전역 설치됨
          ];

          shellHook = ''
            echo "🚀 memex-kb 개발 환경 (flake)"
            echo "================================"
            echo "Python: $(python --version)"
            echo "Pandoc: $(pandoc --version | head -1)"
            echo "Gitleaks: $(gitleaks version)"
            echo "EPUBCheck: $(epubcheck --version 2>/dev/null || echo available)"
            echo ""
            echo "HWPX 변환:"
            echo "  ./hwpx2asciidoc/hwpx2asciidoc.sh input.hwpx   # HWPX → AsciiDoc"
            echo "  ./hwpx2asciidoc/asciidoc2hwpx.sh input.adoc   # AsciiDoc → HWPX"
            echo "  asciidoctor input.adoc                        # → HTML (시스템)"
            echo "  asciidoctor-pdf input.adoc                    # → PDF (시스템)"
            echo ""
            export PYTHONPATH="$PWD:$PYTHONPATH"
            export TERM=xterm-256color

            # MinerU 클라이언트(numpy/opencv manylinux wheel)가 런타임에 요구하는 라이브러리.
            # programs.nix-ld.libraries 가 호스트마다 다르므로(최소 구성 호스트는 libcap 만) flake 가
            # 자립적으로 제공한다. run.sh 의 mineru 명령이 nix develop 안에서 이 변수를 쓴다.
            export MINERU_LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib pkgs.zlib ]}:/run/current-system/sw/share/nix-ld/lib"
          '';
        };

        # 직접 실행 가능한 앱
        apps = {
          threads-token = flake-utils.lib.mkApp {
            drv = pkgs.writeShellScriptBin "threads-token" ''
              cd ${self}
              ${pythonEnv}/bin/python scripts/refresh_threads_token.py "$@"
            '';
          };
          threads-export = flake-utils.lib.mkApp {
            drv = pkgs.writeShellScriptBin "threads-export" ''
              cd ${self}
              ${pythonEnv}/bin/python scripts/threads_exporter.py "$@"
            '';
          };
        };
      }
    );
}

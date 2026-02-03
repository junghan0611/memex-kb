{
  description = "memex-kb - Universal Knowledge Base Converter";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

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

          # HWPX 처리 (직접 XML 파싱)
          lxml
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
            # asciidoctor는 nixos-config에서 시스템 전역 설치됨
          ];

          shellHook = ''
            echo "🚀 memex-kb 개발 환경 (flake)"
            echo "================================"
            echo "Python: $(python --version)"
            echo "Pandoc: $(pandoc --version | head -1)"
            echo "Gitleaks: $(gitleaks version)"
            echo ""
            echo "HWPX 변환:"
            echo "  ./hwpx2asciidoc/hwpx2asciidoc.sh input.hwpx   # HWPX → AsciiDoc"
            echo "  ./hwpx2asciidoc/asciidoc2hwpx.sh input.adoc   # AsciiDoc → HWPX"
            echo "  asciidoctor input.adoc                        # → HTML (시스템)"
            echo "  asciidoctor-pdf input.adoc                    # → PDF (시스템)"
            echo ""
            export PYTHONPATH="$PWD:$PYTHONPATH"
            export TERM=xterm-256color
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

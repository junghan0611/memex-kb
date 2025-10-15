{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python 및 관련 패키지
    python312
    python312Packages.pip
    python312Packages.virtualenv

    # Google API 패키지
    python312Packages.google-api-python-client
    python312Packages.google-auth
    python312Packages.google-auth-oauthlib
    python312Packages.google-auth-httplib2

    # 문서 처리
    python312Packages.markdown
    python312Packages.beautifulsoup4
    python312Packages.pyyaml
    python312Packages.python-slugify
    python312Packages.python-dotenv
    python312Packages.click
    python312Packages.colorlog
    python312Packages.python-dateutil

    # 외부 도구
    pandoc
    rclone

    # 개발 도구
    git
    jq
  ];

  shellHook = ''
    echo "🚀 Google Drive 지식베이스 POC 환경"
    echo "================================"
    echo "Python: $(python --version)"
    echo "Pandoc: $(pandoc --version | head -1)"
    echo "Rclone: $(rclone version | head -1)"
    echo ""
    echo "사용 가능한 명령어:"
    echo "  python scripts/denote_namer.py          - Denote 네이밍 테스트"
    echo "  python scripts/categorizer.py           - 분류기 테스트"
    echo "  python scripts/gdocs_to_markdown_v2.py  - 문서 변환 (Pandoc)"
    echo "  ./scripts/sync_pipeline.sh              - 전체 파이프라인"
    echo ""

    # PYTHONPATH 설정
    export PYTHONPATH="$PWD:$PYTHONPATH"

    # 색상 출력 활성화
    export TERM=xterm-256color
  '';
}

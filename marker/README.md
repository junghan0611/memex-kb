# marker (uv-managed)

scanpdf2org 보조 OCR/레이아웃 경로 검증용 marker-pdf 러너.
flake dev shell의 `uv`로 격리 venv를 만든다. nixos-config와 nixpkgs lock을 맞춰 store path 중복을 피한다.

## 사용

```bash
# 환경 구축 (lock + venv)
nix develop --command uv sync --directory marker

# 단일 PDF → Markdown (CPU)
nix develop --command uv run --directory marker marker_single <INPUT.pdf> --output_dir marker/out
```

CPU 추론이므로 큰 PDF는 작은 페이지 범위로 잘라서 smoke test 한다.

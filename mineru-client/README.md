# mineru-client (원격 vLLM 클라이언트)

MinerU VLM 파싱의 **얇은 클라이언트**. 추론은 gpu2i RTX 5080의 vLLM이 하고,
이쪽은 PDF→이미지 렌더 + 결과 회수만 한다. **로컬에 torch/CUDA/vLLM 불필요**(venv ~480M).

## 구성

```
thinkpad (이 클라이언트) ──SSH터널──> gpu2i:30000 (vLLM 0.11.2, MinerU2.5-Pro-2605-1.2B, served-name: mineru)
```

서버는 nixos 담당이 gpu2i tmux(`mineru-vllm`)로 띄운다. 순수 vLLM(미네루 로직 0).

## 설치 — 한 방

```bash
./run.sh mineru-setup
```

`uv sync` 한 번이면 끝. opencv 는 `pyproject.toml` 의 `[tool.uv] override-dependencies`
로 full opencv-python 을 막고 **headless 만** 설치하게 고정돼 있다(헤드리스 NixOS 에서
full opencv 는 libxcb 부재로 크래시). 별도 교체 단계 불필요.

## 사용 — run.sh 권장 (터널 자동 보장 + env 우회 내장)

```bash
./run.sh mineru-parse <INPUT.pdf|DIR> [OUTPUT_DIR]
# 예: ./run.sh mineru-parse marker/smoke/물질생명인간-p86-91.pdf mineru-client/out
```

직접 호출 시 NixOS 우회 2개 필수:

```bash
env -u PYTHONPATH \                                  # flake/direnv가 주입한 nix Pillow 충돌 제거
    LD_LIBRARY_PATH=/run/current-system/sw/share/nix-ld/lib \   # libstdc++ (magika/onnxruntime)
    mineru-client/.venv/bin/mineru \
    -p <input> -o out -b vlm-http-client -u http://localhost:30000
```

## 터널

thinkpad는 클러스터 10G망(192.168.2.x)에 직접 라우팅이 없고 SSH(ProxyJump)만 통한다.

```bash
ssh -fN -o ExitOnForwardFailure=yes -L 30000:localhost:30000 gpu2i
curl localhost:30000/health   # {"...":"mineru"} 200 확인
```

`run.sh mineru-parse`가 헬스체크 후 없으면 자동으로 띄운다.
클러스터 내부에서 돌릴 땐 터널 없이 `http://192.168.2.12:30000` 직접.

## 산출물

```
out/<doc>/vlm/<doc>.md                 # Markdown (수식 $...$ LaTeX, 그림 ![](images/..))
out/<doc>/vlm/images/*.jpg             # 추출된 그림
out/<doc>/vlm/<doc>_content_list.json  # 구조 JSON
out/<doc>/vlm/<doc>_layout.pdf         # 레이아웃 시각화
```

## 품질 가드

MinerU VLM도 가끔 오독(탈자, 장식헤더)이 있다. `marker/scripts/diff_review.py`는
엔진 무관이라 MinerU md ↔ vision org 대조 QA에 그대로 쓴다. 전략: `marker/STRATEGY.md`.

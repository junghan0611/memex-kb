# scanpdf/ — 스캔 책 작업 영역 (gitignore)

이 폴더는 **저작권 있는 스캔 PDF와 그 변환 산출물**을 두는 작업 영역이다.

> ⚠️ **이 폴더의 내용물은 git에 올라가지 않는다.** 저작권 때문.
> `.gitignore`에서 `scanpdf/*`를 무시하고 이 `README.md`와 `.gitkeep`만 추적한다.
> PDF·렌더 이미지·전사 org(책 본문) 전부 커밋 금지.

## 무엇이 들어가나

```text
scanpdf/
├── <책>.pdf              # 스캔 원본 (전자책 없는 한글 책)
└── work/<책>/
    ├── pages/*.png       # 렌더된 페이지 이미지 (목차 확인용 저해상)
    ├── pages_hi/*.png    # 전사용 고해상 (250dpi)
    ├── pages_check/*.png # 흐릿한 페이지 재확인용 (360dpi)
    ├── org/*.org         # vision 전사 결과 (책 본문)
    └── PROGRESS.md       # 진행 상태 (어디까지 전사했나)
```

## 재사용 로직은 어디에?

이 폴더는 **데이터**만 둔다. 변환 파이프라인(스크립트·전사 규칙·문서)은
저작권이 없으므로 `../scanpdf2org/`에서 커밋된다.

- 파이프라인 설명: `scanpdf2org/README.org`
- 전사 규칙(SSOT): `scanpdf2org/prompts/page-to-org.md`
- 렌더 스크립트: `scanpdf2org/scripts/pdf_to_images.py`
- 명령: `./run.sh scanpdf2org-render <PDF> <OUT> [PAGES] [DPI]`

## 주의

- 각 책 **1장에는 독자의 연필 낙서**가 있다(1장만 정독). 전사 시 손글씨는
  무시하고 인쇄 활자만 옮긴다. 자세한 규칙은 `scanpdf2org/prompts/page-to-org.md`.

;; paper_build.el — Anthropic 논문 acmart org → PDF (memex-kb paper2org)
;;
;; templates/arxiv-acm/build.el 기반 + 논문 변환 특화 2가지:
;;   1. org-export-with-broken-links t — 원문의 미해결 fig 참조([[#fig-..][??]])에서
;;      export 가 중단되지 않게(원문 HTML 에도 ?? 로 깨져 있음 = 우리 버그 아님).
;;   2. backtrace 억제 — 에러 시 org AST 전체가 덤프되어 로그가 수백 MB 로 터지는 것 방지.
;;
;; Usage: emacs -Q --batch --script paper_build.el <name>.acmart.org
;; (acmart 클래스는 texlive scheme-full 등에 포함. nix-shell 안에서 실행.)

(require 'seq)
(require 'ox-latex)

(setq debug-on-error nil
      backtrace-on-error-noninteractive nil
      org-export-with-broken-links t)

;; acmart 는 newtx 를 쓰는데 amssymb 와 충돌 → 기본 패키지에서 제거
(setq org-latex-default-packages-alist
      (seq-remove (lambda (pkg) (equal (cadr pkg) "amssymb"))
                  org-latex-default-packages-alist))

(add-to-list 'org-latex-classes
             '("acmart"
               "\\documentclass[sigconf]{acmart}"
               ("\\section{%s}" . "\\section*{%s}")
               ("\\subsection{%s}" . "\\subsection*{%s}")
               ("\\subsubsection{%s}" . "\\subsubsection*{%s}")
               ("\\paragraph{%s}" . "\\paragraph*{%s}")
               ("\\subparagraph{%s}" . "\\subparagraph*{%s}")))

(setq org-latex-pdf-process
      '("latexmk -f -pdf -interaction=nonstopmode -output-directory=%o %f"))

(let ((org-file (car command-line-args-left)))
  (when org-file
    (find-file org-file)
    (org-latex-export-to-pdf)))

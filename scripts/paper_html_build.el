;; paper_html_build.el — Anthropic 논문 web org → HTML (memex-kb paper2org)
;;
;; PDF(paper_build.el)의 자매. 프로덕션 HTML 경로:
;;   - ox-html standalone (default org CSS + MathJax) → 수식 \(..\)/\[..\] 브라우저 렌더.
;;   - org-cite(oc-basic) → [cite:@key] 를 (Author Year) 로, #+print_bibliography: 를 참고문헌 목록으로.
;;     (pandoc 왕복은 인용을 평문으로 두는 "증명"이었고, 이게 인용까지 렌더하는 "프로덕션".)
;;   - texlive 불필요 — emacs 만. 빠르다.
;;
;; Usage: emacs -Q --batch --script paper_html_build.el <name>.org

(require 'ox-html)
(require 'oc)
(require 'oc-basic)

(setq debug-on-error nil
      backtrace-on-error-noninteractive nil
      org-export-with-broken-links t          ; 원문의 미해결 fig 참조([[#fig-..][??]])
      org-html-validation-link nil
      org-export-with-smart-quotes t
      org-html-mathjax-options '((path "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js")
                                 (scale 1.0) (align "center") (font "mathjax-modern")
                                 (overflow "scroll") (tags "none")))

(let ((org-file (car command-line-args-left)))
  (when org-file
    (find-file org-file)
    (org-html-export-to-html)))

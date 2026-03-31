;; build.el — org → acmart LaTeX → PDF pipeline
;;
;; Usage: emacs -Q --batch --script build.el sample.org
;;
;; Requirements: texlive (scheme-full or with acmart+deps), latexmk
;; NixOS: nix-shell -p '(pkgs.texlive.combine { inherit (pkgs.texlive) scheme-full latexmk; })'

(require 'seq)
(require 'ox-latex)

;; acmart uses newtx which conflicts with amssymb — remove it
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

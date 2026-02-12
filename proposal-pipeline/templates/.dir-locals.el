;;; Directory Local Variables            -*- no-byte-compile: t -*-
;;; For more information see (info "(emacs) Directory Variables")

((org-mode
  . ((org-cite-global-bibliography . nil)
     (org-download-image-dir . "./images/")
     (org-export-with-broken-links . t)
     (org-odt-preferred-output-format . "doc")
     (org-odt-category-map-alist
      . (("__Figure__" "Illustration" "value" "그림" org-odt--enumerable-image-p)
         ("__Table__" "Table" "value" "표" org-odt--enumerable-table-p)
         ("__Equation__" "Text" "value" "수식" org-odt--enumerable-formula-p)
         ("__MathFormula__" "OrgMathFormula" "value" "" org-odt--enumerable-latex-image-p)
         ("__DvipngImage__" "" "value" "" org-odt--enumerable-latex-image-p)
         ("__LaTeXMathFormula__" "OrgMathFormula" "value" "" org-odt--enumerable-latex-image-p))))))

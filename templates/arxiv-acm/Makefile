.PHONY: all clean

all: sample.pdf

sample.pdf: sample.org build.el sample.bib
	emacs -Q --batch --script build.el sample.org

clean:
	rm -f *.aux *.bbl *.blg *.fdb_latexmk *.fls *.log *.out *.toc *.tex *.pdf *~

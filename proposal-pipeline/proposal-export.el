;;; proposal-export.el --- Proposal ODT batch export -*- lexical-binding: t; -*-

;; Copyright (C) 2026 Junghan Kim
;; Author: Junghan Kim <junghanacs@gmail.com>

;; Org → ODT 배치 내보내기 (Doom Emacs 패키지 활용)
;;
;; denote-export.el 에서 Doom 환경 로딩 패턴을 추출하고,
;; citar + org-cite + CSL bibliography 지원으로 ODT를 생성합니다.
;;
;; 사용법:
;;   emacs --batch -l proposal-export.el -- export FILE.org
;;
;; 환경 요구사항:
;;   - Doom Emacs 설치 (straight.el 패키지 사용)
;;   - templates/reference.odt (ODT 스타일 마스터)

;;; Code:

;;;; Configuration

(setq gc-cons-threshold most-positive-fixnum)
(setq load-prefer-newer t)
(setq use-dialog-box nil)
(setq inhibit-startup-screen t)
(setq inhibit-startup-echo-area-message user-login-name)
(setq enable-local-variables :safe)
(setq enable-local-eval nil)
(setq enable-dir-local-variables t)
(setq debug-on-error t)

(message "[Proposal] Starting ODT export initialization...")

;;;; Script Directory

(defvar proposal-script-dir
  (let ((script-path (or load-file-name buffer-file-name)))
    (if script-path
        (file-name-directory (file-truename script-path))
      (expand-file-name "proposal-pipeline/"
                        (expand-file-name ".." default-directory))))
  "proposal-pipeline/ 디렉토리 경로.")

(message "[Proposal] Script dir: %s" proposal-script-dir)

;;;; Doom Emacs Integration
;; (denote-export.el 60-88 패턴)

(defvar doom-user-dir
  (or (getenv "DOOMDIR")
      (expand-file-name "~/repos/gh/doomemacs-config")))

(message "[Proposal] DOOM_USER_DIR: %s" doom-user-dir)

(defvar doom-emacs-dir
  (or (getenv "EMACSDIR")
      (expand-file-name "~/doomemacs-starter")
      (expand-file-name "~/.config/emacs")))

;; Load Doom core (minimal)
(when (file-directory-p doom-emacs-dir)
  (setq user-emacs-directory doom-emacs-dir)
  (load (expand-file-name "lisp/doom.el" doom-emacs-dir) nil t)
  (load (expand-file-name "lisp/doom-start.el" doom-emacs-dir) nil t))

;; Disable package.el (ELPA)
(setq package-enable-at-startup nil)
(setq package-archives nil)
(fset 'package-initialize #'ignore)

;;;; Package Loading (straight.el)
;; (denote-export.el 92-124 패턴)

(defun find-straight-build-dir ()
  "Find the straight build directory, handling different Emacs versions."
  (let ((straight-build-base (expand-file-name ".local/straight/" doom-emacs-dir)))
    (when (file-directory-p straight-build-base)
      (let ((build-dirs (directory-files straight-build-base t "^build-")))
        (when build-dirs
          (car (sort build-dirs #'file-newer-than-file-p)))))))

(let ((build-dir (find-straight-build-dir))
      (repos-dir (expand-file-name ".local/straight/repos/" doom-emacs-dir)))
  (when (and build-dir (file-directory-p build-dir))
    (message "[Proposal] Loading packages from: %s" build-dir)
    (let ((pkg-dirs (directory-files build-dir t "^[^.]" t)))
      (dolist (pkg-dir pkg-dirs)
        (when (and (file-directory-p pkg-dir)
                   (not (string-suffix-p ".el" pkg-dir)))
          (add-to-list 'load-path pkg-dir)
          (let ((autoload-file (expand-file-name
                                (concat (file-name-nondirectory pkg-dir) "-autoloads.el")
                                pkg-dir)))
            (when (file-exists-p autoload-file)
              (load autoload-file nil t)))))))
  (when (file-directory-p repos-dir)
    (let ((repo-dirs (directory-files repos-dir t "^[^.]" t)))
      (dolist (repo-dir repo-dirs)
        (when (file-directory-p repo-dir)
          (add-to-list 'load-path repo-dir))))))

;;;; Org Priority (Doom's org > built-in)

(let ((build-dir (find-straight-build-dir)))
  (when build-dir
    (let ((org-dir (expand-file-name "org" build-dir)))
      (when (file-directory-p org-dir)
        (push org-dir load-path)
        (message "[Proposal] Prioritized Doom's org: %s" org-dir)))))

;;;; Required Packages (minimal for ODT)

(require 'org)
(require 'ox)
(require 'ox-odt)
(require 'cl-lib)

(or (require 'dash nil t) (message "[Proposal] WARNING: dash not found"))
(or (require 'citar nil t) (message "[Proposal] WARNING: citar not found"))
(or (require 'parsebib nil t) (message "[Proposal] WARNING: parsebib not found"))

(require 'oc)
(require 'oc-basic)
(require 'oc-csl)

(message "[Proposal] Required packages loaded")

;;;; User Info + Bibliography

(defvar org-directory (expand-file-name "~/org"))

;; +user-info.el → config-bibfiles
(let ((user-info (expand-file-name "+user-info.el" doom-user-dir)))
  (when (file-exists-p user-info)
    (load user-info nil t)
    (message "[Proposal] Loaded +user-info.el")))

;; citar + org-cite bibliography 설정
(when (boundp 'config-bibfiles)
  (setq citar-bibliography config-bibfiles)
  (setq org-cite-global-bibliography config-bibfiles)
  (message "[Proposal] Personal bibliography: %S" config-bibfiles))

;; 제안서용 references.bib 추가
(let ((proposal-bib (expand-file-name "templates/references.bib" proposal-script-dir)))
  (when (file-exists-p proposal-bib)
    (setq org-cite-global-bibliography
          (append (and (boundp 'org-cite-global-bibliography)
                       org-cite-global-bibliography)
                  (list proposal-bib)))
    (message "[Proposal] Added proposal bibliography: %s" proposal-bib)))

;; CSL 설정
(let ((csl-dir (expand-file-name "templates/" proposal-script-dir)))
  (when (file-directory-p csl-dir)
    (setq org-cite-csl-styles-dir csl-dir)))
(setq org-cite-export-processors '((t csl)))

(message "[Proposal] Bibliography initialized: %S" org-cite-global-bibliography)

;;;; ODT Export Settings

;; reference.odt 스타일 마스터
(let ((ref-odt (expand-file-name "templates/reference.odt" proposal-script-dir)))
  (when (file-exists-p ref-odt)
    (setq org-odt-styles-file ref-odt)
    (message "[Proposal] ODT styles: %s" ref-odt)))

;; 순수 ODT 출력 (DOC 자동변환 비활성화 — odt_postprocess.py 선행 필요)
(setq org-odt-preferred-output-format nil)

;; 한글 캡션 (그림, 표, 수식)
(setq org-odt-category-map-alist
      '(("__Figure__" "Illustration" "value" "그림" org-odt--enumerable-image-p)
        ("__Table__" "Table" "value" "표" org-odt--enumerable-table-p)
        ("__Equation__" "Text" "value" "수식" org-odt--enumerable-formula-p)
        ("__MathFormula__" "OrgMathFormula" "value" "" org-odt--enumerable-latex-image-p)
        ("__DvipngImage__" "" "value" "" org-odt--enumerable-latex-image-p)
        ("__LaTeXMathFormula__" "OrgMathFormula" "value" "" org-odt--enumerable-latex-image-p)))

;; Export 설정
(setq org-export-headline-levels 5)
(setq org-export-with-broken-links t)
(setq org-export-with-toc nil)
(setq org-export-with-author nil)
(setq org-export-use-babel nil)

(message "[Proposal] ODT settings configured")

;;;; Export Function

(defun proposal-export-to-odt (org-file)
  "ORG-FILE을 ODT로 내보내기 (순수 ODT, DOC 자동변환 없음)."
  (message "[Proposal] Exporting: %s" org-file)
  (let ((buf (find-file-noselect org-file)))
    (unwind-protect
        (with-current-buffer buf
          (org-mode)
          (setq default-directory (file-name-directory (expand-file-name org-file)))
          (condition-case err
              (let ((result (org-odt-export-to-odt)))
                (message "[Proposal] SUCCESS: %s" result)
                result)
            (error
             (message "[Proposal] ERROR: %s" (error-message-string err))
             nil)))
      (when (buffer-live-p buf)
        (kill-buffer buf)))))

;;;; Memory Management

(setq gc-cons-threshold (* 16 1024 1024))
(garbage-collect)

;;;; CLI Entry Point

;; emacs --batch -l proposal-export.el -- export FILE.org
(when noninteractive
  (let ((args command-line-args-left))
    (when (and args (string= (car args) "export"))
      (setq command-line-args-left nil)
      (let ((file (cadr args)))
        (unless file
          (message "[Proposal] ERROR: Org 파일 경로가 필요합니다")
          (message "사용법: emacs --batch -l proposal-export.el -- export FILE.org")
          (kill-emacs 1))
        (unless (file-exists-p file)
          (message "[Proposal] ERROR: 파일 없음: %s" file)
          (kill-emacs 1))
        (let ((result (proposal-export-to-odt (expand-file-name file))))
          (if result
              (progn
                (message "[Proposal] 완료: %s" result)
                (kill-emacs 0))
            (message "[Proposal] 내보내기 실패")
            (kill-emacs 1)))))))

(provide 'proposal-export)
;;; proposal-export.el ends here

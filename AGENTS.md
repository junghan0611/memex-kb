# AGENTS

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 🔧 Development Environment

**IMPORTANT: This project uses Nix Flake for dependency management.**

**Always use `nix develop` to run Python scripts:**

```bash
# ✅ Correct way (Nix Flake environment)
nix develop --command python scripts/threads_exporter.py --download-images

# ✅ With direnv (auto-activate on cd)
direnv allow  # once
python scripts/threads_exporter.py --download-images

# ❌ Wrong way (will fail with missing dependencies)
python scripts/threads_exporter.py --download-images
```

**Why Nix Flake?**
- ✅ Declarative dependencies (`flake.nix`)
- ✅ Reproducible builds with lockfile (`flake.lock`)
- ✅ Faster than `nix-shell` (cached evaluation)
- ✅ No `pip install` needed
- ✅ direnv integration (`.envrc`)

**Available packages in `flake.nix`:**
- Python 3.12 + all required packages
- Pandoc (document conversion)
- Git, jq, rclone
- gitleaks (secret detection)

**Quick start:**
```bash
# Enter Nix environment (interactive)
nix develop

# Or run single command
nix develop --command python scripts/your_script.py

# With direnv (recommended)
direnv allow
# → auto-loads environment on cd
```

---

## 🎯 Project Overview

**memex-kb**: Universal Knowledge Base Converter - Denote 기반 범용 지식베이스 변환 시스템

**Core Philosophy**: "Legacy → Denote → RAG-ready" - 산재된 지식을 체계적으로 정리하고 AI 협업 가능한 형태로 변환

**Key Innovation**:
- **Denote File Naming**: `timestamp--한글-제목__태그1_태그2.md` (parsable, time-sortable, semantic)
- **Rule-based Classification**: YAML 설정으로 일관성 확보, LLM 비용 0원
- **Adapter Pattern**: Backend 중립 (Google Docs, Threads SNS, Dooray Wiki, etc.)
- **Git Versioning**: 모든 변환 과정 추적

---

## 🏗️ Architecture

```
[Backend Sources]
    ├── Google Docs (✅)
    ├── Threads SNS (✅)
    ├── Dooray Wiki (🔧 WIP)
    └── Confluence (📋 Planned)
         ↓
[Backend Adapter] ← Adapter Pattern (scripts/adapters/)
         ↓
[Markdown/Org Conversion] ← Pandoc
         ↓
[Common Pipeline]
    ├── DenoteNamer (파일명 생성)
    ├── Categorizer (자동 분류)
    └── Tag Extractor (태그 추출)
         ↓
[Local Git Repository] → docs/
```

**Directory Structure**:
```
memex-kb/
├── flake.nix                     # Nix Flake (dependencies)
├── flake.lock                    # Locked versions
├── .envrc                        # direnv config
├── scripts/                      # Conversion scripts
│   ├── adapters/                 # Backend adapters (extensible)
│   │   ├── base.py               # BaseAdapter (abstract class)
│   │   └── threads.py            # Threads API Adapter
│   ├── gdocs_to_markdown.py      # Google Docs converter
│   ├── threads_exporter.py       # Threads exporter (posts + replies → single Org file)
│   ├── refresh_threads_token.py  # Threads API token refresh (OAuth)
│   ├── denote_namer.py           # Denote filename generator (common)
│   ├── categorizer.py            # Auto categorizer (common)
│   └── sync_pipeline.sh          # Automation pipeline
├── docs/                         # Converted documents
│   ├── threads-aphorisms.org     # Threads 아포리즘 통합 파일
│   ├── images/threads/           # Threads images (gitignored)
│   └── 2025*.org                 # Project docs
├── config/
│   ├── .env                      # Environment variables (gitignored)
│   ├── .env.example              # Template
│   └── categories.yaml           # Classification rules
└── logs/                         # Execution logs
```

---

## 🚀 Common Development Tasks

### Environment Setup

**This project uses Nix Flake (`flake.nix`) - no manual installation needed!**

All dependencies are declared in `flake.nix`:
- Python 3.12 + all required packages
- Pandoc (document conversion)
- Git, jq, rclone
- gitleaks (secret detection)

**To use:**
```bash
# Enter Nix environment
nix develop

# You'll see:
# 🚀 memex-kb 개발 환경 (flake)
# ================================
# Python: Python 3.12.12
# Pandoc: pandoc 3.7.0.2
# Gitleaks: 8.30.0
# ...

# Or use direnv (recommended)
direnv allow
```

**Secret scanning before commit:**
```bash
gitleaks detect              # git repo 스캔
gitleaks detect --no-git     # 파일 스캔 (디지털 가든 배포용)
```

### Running Converters

**⚠️ ALWAYS use `nix develop --command` for Python scripts!**

**Google Docs Conversion**:
```bash
# Single document
nix develop --command python scripts/gdocs_to_markdown.py DOCUMENT_ID

# Batch conversion (pipeline)
nix develop --command ./scripts/sync_pipeline.sh
```

**Threads SNS Export**:
```bash
# Step 1: Get/Refresh OAuth token
# 방법: Graph API Explorer에서 threads.net API로 변경 후 토큰 발급
# https://developers.facebook.com/tools/explorer/1351795096326806/
nix develop --command python scripts/refresh_threads_token.py --exchange "단기토큰"

# Step 2: Test token
nix develop --command python scripts/refresh_threads_token.py --test

# Step 3: Export all posts (with replies!)
nix develop --command python scripts/threads_exporter.py --download-images

# Options:
nix develop --command python scripts/threads_exporter.py --max-posts 5 --download-images  # Test mode
nix develop --command python scripts/threads_exporter.py --reverse                        # Oldest first
```

**Output**:
- `docs/threads-aphorisms.org` (single file, all posts + replies, datetree structure)
- `docs/images/threads/` (downloaded images, gitignored)

**Key Features**:
- ✅ 댓글 자동 수집 (본인 포스트에 달린 모든 댓글)
- ✅ 이미지 다운로드 (단일/캐러셀 모두 지원)
- ✅ Datetree 구조 (연도 → 월 → 일 → 포스트)

### Testing

**No formal test suite yet**. Manual testing workflow:

```bash
# Test Threads API token
nix develop --command python scripts/refresh_threads_token.py --test

# Test Denote filename generation
nix develop --command python scripts/denote_namer.py

# Test categorizer
nix develop --command python scripts/categorizer.py

# Secret scan before commit
nix develop --command gitleaks detect
```

---

## 📋 Key Technical Details

### 1. Denote File Naming Convention

**Format**: `timestamp--한글-제목__태그1_태그2.md`

**Implementation**: `scripts/denote_namer.py`

**Rules**:
- `timestamp`: `YYYYMMDDTHHMMSS` (capital T required!)
- `한글-제목`: Korean title (human-readable, searchable)
- `태그들`: Lowercase English tags (separated by `_`)

**Example**:
```
Input:
  title: "API 설계 가이드"
  tags: ["백엔드", "api", "가이드"]

Output:
  20250913t150000--api-설계-가이드__backend_api_guide.md
```

**Why**:
- **Time-sortable**: Automatic chronological ordering
- **Parsable**: Programmatic metadata extraction
- **Semantic**: Korean titles + English tags
- **Consistent**: No manual naming variations

### 2. Rule-based Classification

**Config**: `config/categories.yaml`

**Categories**:
- `architecture`: 시스템 설계
- `development`: 개발 가이드
- `operations`: 운영 문서
- `products`: 제품별 문서
- `_uncategorized`: 미분류 (manual review required)

**Scoring Algorithm** (`scripts/categorizer.py`):
```python
weights:
  title_keyword: 10      # Keyword in title
  title_pattern: 15      # Regex pattern match
  content_keyword: 5     # Keyword in content
  file_hint: 20          # Filename hint match

min_score: 30            # Minimum threshold
```

**Why No LLM?**:
- ✅ Zero token cost
- ✅ Reproducible
- ✅ Fast
- ✅ Transparent (YAML-based)
- ✅ Version-controllable

### 3. Adapter Pattern

**Base Interface**: `scripts/adapters/base.py`

**Required Methods**:
```python
class BaseAdapter(ABC):
    @abstractmethod
    def authenticate(self) -> Any:
        """인증 수행"""

    @abstractmethod
    def list_documents(self, **kwargs) -> List[Dict]:
        """문서 목록 조회"""

    @abstractmethod
    def fetch_document(self, doc_id: str, **kwargs) -> Dict:
        """개별 문서 내용 가져오기"""

    @abstractmethod
    def convert_to_format(self, content: Dict, output_format: str) -> str:
        """문서를 Markdown/Org로 변환"""
```

**Extending with New Backend**:
1. Create `scripts/adapters/yourbackend.py`
2. Inherit from `BaseAdapter`
3. Implement all abstract methods
4. Use common pipeline (DenoteNamer, Categorizer)

**Example**: `scripts/adapters/threads.py` (Threads SNS adapter)

### 4. Org-mode Special Characters

**Important**: When exporting to Org-mode, escape special characters:

```python
# Org special characters that need escaping
ORG_SPECIAL_CHARS = {
    '\\': '\\\\',      # Backslash (must be first!)
    '[': '\\[',        # Link syntax
    ']': '\\]',
    '*': '\\*',        # Bold/heading
    '/': '\\/',        # Italic
    '_': '\\_',        # Underline
    '=': '\\=',        # Verbatim
    '~': '\\~',        # Code
    '+': '\\+',        # Strikethrough
}
```

**Why**: Prevents Org-mode from misinterpreting text as markup.

**Implementation**: See `scripts/threads_exporter.py:escape_org_special_chars()`

### 5. Threads API Integration

**Token Refresh (60일마다 필요)**:
```bash
# 1. Graph API Explorer에서 단기 토큰 발급
#    https://developers.facebook.com/tools/explorer/1351795096326806/
#    → API를 "threads.net"으로 변경 (중요!)
#    → Generate Access Token

# 2. 장기 토큰(60일)으로 교환
nix develop --command python scripts/refresh_threads_token.py --exchange "단기토큰"

# 3. 테스트
nix develop --command python scripts/refresh_threads_token.py --test
```

**Key Endpoints**:
- `/me`: User profile
- `/me/threads`: List all posts (pagination)
- `/media/{id}`: Post details + comments
- Media URL: Direct image download

**Unique Feature**: "어쏠리즘(Assholism)" - 아포리즘을 단일 Org 파일로 통합, 시간순 정렬, 주제별 자동 분류

---

## 🔧 Environment Variables

**Google Docs** (`.env` or `.env.example`):
```bash
GOOGLE_APPLICATION_CREDENTIALS=config/credentials.json
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
MAX_DOCS_PER_RUN=50
ENABLE_AUTO_COMMIT=false
```

**Threads SNS** (`.env` or `.env.threads.example`):
```bash
APP_ID=your_app_id
APP_SECRET=your_app_secret
REDIRECT_URI=https://localhost/callback
ACCESS_TOKEN=your_access_token           # Auto-populated by get_threads_token.py
USER_ID=your_user_id                     # Auto-populated
THREADS_IMAGES_DIR=docs/images/threads   # Image directory (default)
```

**Security**:
- ✅ All credential files are gitignored
- ✅ Use `.env.example` as template
- ✅ Never commit credentials

---

## 📚 Important Documentation

**Design Philosophy**:
- `docs/20251015T180500--memex-kb-rag-통합-전략__rag_embedding_architecture.org`
  - v2.0 roadmap: RAG pipeline integration
  - Why Denote + Rule-based classification + Adapter pattern
  - Connection to existing tech stack (n8n, Supabase pgvector, Ollama)

**Threads Integration**:
- `docs/20251107T123200--threads-aphorism-exporter-프로젝트__threads_aphorism_assholism.org`
  - "어쏠리즘(Assholism)" concept
  - Architecture (Adapter pattern)
  - Org-mode export structure
  - Special character escaping

**Embedding Strategy**:
- `docs/20251016T140000--구조화-데이터-임베딩-가치-벤치마크__benchmark_structured_embedding.org`
  - Why structured data > raw dumps
  - Embedding benchmarks (2,945 Org files)

---

## 🎨 Code Style

**Python**:
- Follow existing patterns in `scripts/`
- Use type hints (as seen in `adapters/base.py`)
- Korean docstrings + English comments (mixed approach)
- Logging with `logging` module (not `print`)

**Bash**:
- Color output (RED, GREEN, YELLOW, BLUE)
- Error handling with `set -e`
- Log files in `logs/`

**Git Commits**:
- ✅ Professional format (no "Generated with Claude")
- ✅ Follow existing commit patterns
- ✅ Korean or English (project uses both)

---

## 🚨 Common Pitfalls

1. **NixOS Environment** (user runs NixOS on storage server):
   - ❌ No command substitution `$(cmd)` in single Bash call (sandbox escape)
   - ✅ Split into multiple sequential Bash calls
   - ✅ Use `nix develop` (flake) instead of `nix-shell`
   - ✅ Use direnv for auto-environment loading

2. **Org-mode Export**:
   - ❌ Forgetting to escape special characters (`*`, `[`, `]`, etc.)
   - ✅ Always use `escape_org_special_chars()` function

3. **Denote Timestamp**:
   - ❌ Using lowercase `t` → `20250913t150000` (should be capital `T`)
   - ✅ Use capital `T` → `20250913T150000`

4. **Categorization**:
   - ❌ Manually categorizing documents (inconsistent)
   - ✅ Use `categorizer.py` with `categories.yaml` rules

5. **Git Credentials**:
   - ❌ Committing `.env`, `credentials.json`
   - ✅ Check `.gitignore` before adding new config files

---

## 🌟 Future Plans (v2.0)

**Goal**: Legacy → Denote → **RAG-ready** pipeline

**Tech Stack** (already validated):
- ✅ n8n: 40+ node workflows (AI Agent Automation)
- ✅ Supabase pgvector: 2,945 Org files embedded
- ✅ Ollama: multilingual-e5-large (local embedding)
- ✅ Rerank API: Custom server

**v2.0 Features**:
- 💡 Denote Markdown → Vector Embedding
- 💡 Folder-specific chunking (meta 1500, bib 1200, journal 800, notes 1000)
- 💡 Supabase pgvector integration (reuse proven pipeline)
- 💡 n8n RAG workflow (Hybrid Search: keyword + vector + graph)
- 💡 Knowledge hierarchy (meta → bib → journal → notes)

**Differentiation**:
- Not just a "converter tool"
- **Entry point to RAG pipeline**
- Unique approach: Denote + Rule-based + RAG

---

## 📞 Contact

- **Developer**: Junghan Kim (junghanacs)
- **GitHub**: [junghan0611](https://github.com/junghan0611)
- **Blog**: [힣's 디지털가든](https://notes.junghanacs.com)

---

**Version**: 1.2.0
**Last Updated**: 2026-01-21
**Status**: 🟢 Actively developing

**Changelog (1.2.0)**:
- Migrated from `shell.nix` to `flake.nix` for faster builds
- Added `refresh_threads_token.py` for OAuth token management
- Replaced secretlint (npm) with gitleaks (native)
- Added direnv integration (`.envrc`)


<!-- br-agent-instructions-v1 -->

---

## Beads Workflow Integration

This project uses [beads_rust](https://github.com/Dicklesworthstone/beads_rust) (`br`/`bd`) for issue tracking. Issues are stored in `.beads/` and tracked in git.

### Essential Commands

```bash
# View ready issues (unblocked, not deferred)
br ready              # or: bd ready

# List and search
br list --status=open # All open issues
br show <id>          # Full issue details with dependencies
br search "keyword"   # Full-text search

# Create and update
br create --title="..." --type=task --priority=2
br update <id> --status=in_progress
br close <id> --reason="Completed"
br close <id1> <id2>  # Close multiple issues at once

# Sync with git
br sync --flush-only  # Export DB to JSONL
br sync --status      # Check sync status
```

### Workflow Pattern

1. **Start**: Run `br ready` to find actionable work
2. **Claim**: Use `br update <id> --status=in_progress`
3. **Work**: Implement the task
4. **Complete**: Use `br close <id>`
5. **Sync**: Always run `br sync --flush-only` at session end

### Key Concepts

- **Dependencies**: Issues can block other issues. `br ready` shows only unblocked work.
- **Priority**: P0=critical, P1=high, P2=medium, P3=low, P4=backlog (use numbers 0-4, not words)
- **Types**: task, bug, feature, epic, question, docs
- **Blocking**: `br dep add <issue> <depends-on>` to add dependencies

### Session Protocol

**Before ending any session, run this checklist:**

```bash
git status              # Check what changed
git add <files>         # Stage code changes
br sync --flush-only    # Export beads changes to JSONL
git commit -m "..."     # Commit everything
git push                # Push to remote
```

### Best Practices

- Check `br ready` at session start to find available work
- Update status as you work (in_progress → closed)
- Create new issues with `br create` when you discover tasks
- Use descriptive titles and set appropriate priority/type
- Always sync before ending session

<!-- end-br-agent-instructions -->

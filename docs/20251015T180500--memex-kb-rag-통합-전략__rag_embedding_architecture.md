---
title:      "memex-kb v2.0: RAG 통합 전략"
date:       2025-10-15T18:05:00+09:00
tags:       ["memex-kb", "rag", "embedding", "architecture", "strategy"]
identifier: "20251015T180500"
---

# 🧠 memex-kb v2.0: RAG 통합 전략

**목적**: Legacy → Denote → RAG-ready 변환 시스템
**접근**: 검증된 기술 스택 통합 + 독창적 방법론
**상태**: 🔧 설계 단계

---

## 🎯 핵심 인사이트

### "변환 자체는 감흥이 없다"

**기술 스택은 이미 검증되었습니다** (2025 Q3):
```yaml
AI_Infrastructure:
  n8n: 40+ 노드 워크플로우, AI Agent Automation
  Supabase_pgvector: 2,945개 Org 파일 임베딩 완료
  Ollama: multilingual-e5-large (1024-dim), GPU 클러스터
  Rerank_API: 자체 구축 서버

Data_Engineering:
  Airbyte: Channel.io → PostgreSQL ETL
  JSONB: Agent-readable Data Lake
  Notion/JIRA: API 통합

성과:
  - 8,310개 벡터 청크 생성
  - 100% 임베딩 완료
  - n8n RAG 워크플로우 운영 중
```

**→ 이것들은 "껍데기"입니다. 이미 다 해봤습니다.**

---

## 💡 memex-kb의 진정한 가치

### 문제 정의

**Q**: 기술 스택을 다 알면 되는가?

**A**: 아닙니다.

```
Pandoc으로 변환? → 누구나 할 수 있음
Ollama로 임베딩? → 튜토리얼 많음
Supabase pgvector? → 문서 잘 되어 있음
n8n RAG 워크플로우? → 예제 많음

그런데:
- 파일명이 일관성 없으면? → 검색 품질 ↓
- 분류가 모호하면? → 컨텍스트 부족
- 메타데이터 손실되면? → 임베딩 품질 ↓
- Git 없으면? → 버전 관리 불가

→ 임베딩해도 쓸모없습니다.
```

### memex-kb의 독창적 접근

**"Legacy → RAG-ready"의 방법론**:

```
┌─────────────────────────────────────────────┐
│ 1. 일관성 (Denote 파일명)                   │
├─────────────────────────────────────────────┤
│ Before:                                     │
│ - "새 문서.docx"                            │
│ - "회의록_20250915_v2_최종.docx"          │
│ - "API 설계 (1).docx"                       │
│                                             │
│ After (Denote):                             │
│ - 20250915t100000--새-문서__temp.md        │
│ - 20250915t140000--회의록__meeting.md      │
│ - 20250913t150000--api-설계-가이드__        │
│   backend_api_guide.md                      │
│                                             │
│ 효과:                                       │
│ - 파싱 가능 (프로그래밍으로 처리)           │
│ - 시간 정렬 (자동)                          │
│ - 의미 명확 (한글 제목 + 영어 태그)        │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 2. 체계성 (규칙 기반 자동 분류)             │
├─────────────────────────────────────────────┤
│ categories.yaml:                            │
│                                             │
│ architecture:                               │
│   keywords: ["설계", "아키텍처"]           │
│   patterns: ["^시스템.*설계"]              │
│   priority: 1                               │
│                                             │
│ 효과:                                       │
│ - LLM 비용 0원 (토큰 절약)                 │
│ - 재현 가능 (YAML 설정)                    │
│ - 확장 가능 (새 카테고리 추가 쉬움)        │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 3. 추적성 (Git 버전 관리)                   │
├─────────────────────────────────────────────┤
│ 모든 변환 과정 Git 커밋:                    │
│                                             │
│ git log:                                    │
│ - feat: add google docs adapter             │
│ - docs: convert 10 documents                │
│ - fix: improve categorization rules         │
│                                             │
│ 효과:                                       │
│ - 투명성 (누가 언제 변환했는지)            │
│ - 롤백 가능 (잘못된 변환 복구)             │
│ - 협업 가능 (팀 지식 관리)                 │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 4. 확장성 (Backend 중립)                    │
├─────────────────────────────────────────────┤
│ Adapter Pattern:                            │
│                                             │
│ class BaseAdapter(ABC):                     │
│     def convert_to_markdown(): pass         │
│                                             │
│ class GoogleDocsAdapter(BaseAdapter): ...   │
│ class DoorayAdapter(BaseAdapter): ...       │
│ class ConfluenceAdapter(BaseAdapter): ...   │
│                                             │
│ 효과:                                       │
│ - 도구 바뀌어도 데이터 유지                 │
│ - 공통 파이프라인 재사용                    │
│ - 새 Backend 추가 쉬움                      │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ 5. RAG 품질 (임베딩 파이프라인)             │
├─────────────────────────────────────────────┤
│ 검증된 전략 (embedding-config):             │
│                                             │
│ 폴더별 차별화 청킹:                         │
│ - meta: 1500 토큰 (긴 개념 설명)           │
│ - bib: 1200 토큰 (인용 포함)               │
│ - journal: 800 토큰 (일일 단위)            │
│ - notes: 1000 토큰 (균형)                  │
│                                             │
│ 지식 계층 구조:                             │
│ meta (개념) → bib (원리) →                  │
│ journal (실천) → notes (결실)               │
│                                             │
│ 효과:                                       │
│ - 임베딩 품질 향상 (계층적 컨텍스트)       │
│ - 검색 정확도 향상 (의미 보존)             │
│ - RAG 답변 품질 향상 (풍부한 컨텍스트)    │
└─────────────────────────────────────────────┘
```

**→ 이것이 memex-kb의 독창성입니다.**

---

## 🏗️ 검증된 기술 경험 (2025 Q3)

### 1. n8n AI Agent Automation

**경험**:
- 40+ 노드 복잡한 워크플로우 운영
- Hierarchical AI Agent 구조 (Meta → Domain Agents)
- 빠른 프로토타이핑: "백엔드/프론트 AI가, 검증/연결 사람이"

**활용 (memex-kb v2.0)**:
```javascript
// n8n Workflow: Legacy → RAG Pipeline
Trigger (일정: 매일 밤 12시)
    ↓
Memex-KB (새 문서 변환)
    ↓
Denote Markdown (~/memex-kb/docs/)
    ↓
Embedding (Ollama, GPU-03)
    ↓
Supabase Vector Store
    ↓
Slack 알림 ("10개 문서 임베딩 완료")
```

---

### 2. Supabase pgvector 임베딩

**경험**:
- **2,945개 Org 파일** → **8,310개 벡터 청크**
- 100% 임베딩 완료 (15분 소요, GPU-03)
- 폴더별 차별화 청킹 전략 검증

**스키마** (검증됨):
```sql
CREATE TABLE org_garden_documents (
    id UUID PRIMARY KEY,
    identifier TEXT UNIQUE,        -- Denote 타임스탬프
    korean_title TEXT,             -- 한글 제목
    denote_tags TEXT[],            -- 태그 배열
    content TEXT,
    embedding vector(1024),
    folder_category TEXT,
    is_autholog BOOLEAN,
    metadata JSONB
);

-- IVFFlat 인덱스
CREATE INDEX idx_org_embedding ON org_garden_documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 하이브리드 검색 함수
CREATE FUNCTION match_org_garden_documents(
    filter jsonb,
    match_count int,
    query_embedding vector(1024)
) ...
```

**활용 (memex-kb v2.0)**:
- 동일한 스키마 재사용
- 검증된 검색 함수 재사용
- 폴더별 청킹 전략 적용

---

### 3. Ollama 로컬 임베딩

**경험**:
- GPU-03 (RTX 5080, 192.168.2.13:11434)
- multilingual-e5-large-instruct (1024-dim)
- 평균 6-7 파일/초 처리 속도

**모델 비교 (검증됨)**:
```yaml
multilingual-e5-large:
  dimension: 1024
  context: 512
  quality: ⭐⭐⭐⭐ (한글 우수)
  speed: ⭐⭐ (느림)

mxbai-embed-large:  # v2.0 추천
  dimension: 1024
  context: 512
  quality: ⭐⭐⭐⭐⭐ (한글 최적화)
  speed: ⭐⭐⭐ (빠름)

nomic-embed-text:  # 백업
  dimension: 768
  context: 8192
  quality: ⭐⭐⭐ (긴 문서용)
  speed: ⭐⭐⭐⭐ (매우 빠름)
```

**활용 (memex-kb v2.0)**:
- mxbai-embed-large 우선 사용
- nomic-embed-text 긴 문서용
- GPU-03 클러스터 활용

---

### 4. Airbyte ETL 파이프라인

**경험**:
- Channel.io → PostgreSQL 실시간 동기화
- JSONB Data Lake 구축
- Notion/JIRA 외 다수 커넥터 운영

**활용 (memex-kb v1.2)**:
- Notion Adapter: Airbyte 패턴 재사용
- Confluence Adapter: REST API 경험 활용

---

### 5. Rerank API Server

**경험**:
- 자체 Rerank API 서버 구축
- n8n 워크플로우 통합

**활용 (memex-kb v2.0)**:
```python
# Hybrid Search + Reranking
def search_with_rerank(query):
    # 1. Vector Search (Supabase)
    vector_results = supabase.search(query, k=50)

    # 2. BM25 Keyword Search
    bm25_results = bm25.search(query, k=50)

    # 3. Denote Link Graph
    graph_results = link_graph.search(query, k=50)

    # 4. Reciprocal Rank Fusion
    combined = rrf_combine(vector_results, bm25_results, graph_results)

    # 5. Rerank
    final = rerank_api.rerank(query, combined, top_k=10)

    return final
```

---

## 📐 v2.0 아키텍처: 완전한 RAG 파이프라인

### 전체 흐름

```
┌─────────────────────────────────────────────┐
│ Legacy Sources                              │
│ - Google Docs (회사 기술문서)               │
│ - Dooray Wiki (협업 문서)                   │
│ - Confluence (팀 위키)                      │
│ - Notion (개인 노트)                        │
└─────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ memex-kb v1.x (Conversion Layer)            │
│                                             │
│ Backend Adapter:                            │
│ - API 호출 → Content 추출                  │
│ - Pandoc 변환 → Markdown                   │
│                                             │
│ Common Pipeline:                            │
│ - DenoteNamer: 파일명 생성                 │
│ - Categorizer: 자동 분류                   │
│ - Tag Extractor: 태그 추출                 │
│                                             │
│ Output: ~/memex-kb/docs/                    │
│ - timestamp--한글-제목__태그들.md          │
│ - 카테고리별 폴더 분류                      │
│ - Git 커밋 기록                             │
└─────────────────────────────────────────────┘
                ↓ v2.0 NEW!
┌─────────────────────────────────────────────┐
│ memex-kb v2.0 (Embedding Pipeline)          │
│                                             │
│ Document Parser (검증된 전략):              │
│ - Denote 파일명 파싱                        │
│ - Frontmatter 추출                          │
│ - Org properties 호환                       │
│                                             │
│ Semantic Chunker (폴더별 차별화):           │
│ - meta: 1500 토큰 (개념 전체 맥락)         │
│ - bib: 1200 토큰 (인용 포함)               │
│ - journal: 800 토큰 (일일 단위)            │
│ - notes: 1000 토큰 (균형)                  │
│                                             │
│ Embedding Generator (Ollama, GPU-03):       │
│ - mxbai-embed-large (1024-dim, 한글)       │
│ - Title + Tags + Content 통합              │
│ - 메타데이터 보존                           │
│                                             │
│ Output: Supabase pgvector                   │
│ - 동일 스키마 (org_garden_documents)       │
│ - 검증된 검색 함수 재사용                   │
└─────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ n8n RAG Orchestration (검증됨)              │
│                                             │
│ Hybrid Search:                              │
│ - Vector Search (Supabase)                  │
│ - BM25 Keyword Search                       │
│ - Denote Link Graph                         │
│ - Reciprocal Rank Fusion                    │
│ - Rerank API                                │
│                                             │
│ Context Assembly:                           │
│ - 폴더별 가중치 (meta 1.5x, notes 1.2x)    │
│ - Autholog 우선 (is_autholog=true)         │
│ - 최근성 가중치 (1년 이내 +10%)            │
│                                             │
│ Output: 풍부한 컨텍스트                     │
└─────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ AI Second Brain                             │
│                                             │
│ Emacs (semext 통합):                        │
│ M-x memex-kb-search RET                     │
│ Query: "GraphRAG 관련 노트"                 │
│                                             │
│ Results (Hybrid Search):                    │
│ 1. [95%] meta/20250214T145957--graphrag...  │
│ 2. [87%] notes/20250214T145633--khoj-ai...  │
│ 3. [76%] journal/20250328T090326--llm...    │
│                                             │
│ RET: 문서 열기                              │
│ C-o: Preview                                │
│ i: Insert link [[denote:20250214T145957]]   │
└─────────────────────────────────────────────┘
```

---

## 🎯 차별화 요소

### 1. 기술 vs 방법론

**다른 도구들** (기술 중심):
```
"Pandoc으로 변환합니다"
"Ollama로 임베딩합니다"
"Supabase에 저장합니다"

→ HOW (어떻게)
```

**memex-kb** (방법론 중심):
```
"왜 Denote 파일명 규칙인가?"
→ 파싱 가능, 시간 정렬, 의미 명확

"왜 규칙 기반 분류인가?"
→ LLM 비용 0원, 재현 가능, 일관성

"왜 Git 버전 관리인가?"
→ 투명성, 롤백, 협업

"왜 Adapter 패턴인가?"
→ Backend 중립, 확장성, 재사용

→ WHY (왜) + HOW (어떻게)
```

### 2. 검증된 경험 통합

**embedding-config 성과** (2025-09-13):
- 2,945개 파일 → 8,310개 청크 (100%)
- 소요 시간: 15분 (GPU-03)
- 폴더별 청킹 전략 검증
- 지식 계층 구조 반영

**memex-kb v2.0**:
- 동일한 전략 재사용
- 동일한 스키마 (org_garden_documents)
- 동일한 검색 함수 (match_org_garden_documents)
- **추가 가치**: Legacy 문서를 동일 품질로 통합

### 3. 독창적 통합

**기존 도구들**:
```
변환 도구: Pandoc, Notion Exporter, ...
임베딩 도구: LangChain, LlamaIndex, ...
벡터 DB: Supabase, Pinecone, Qdrant, ...

→ 각각 따로 사용
```

**memex-kb**:
```
변환 (Denote 규칙)
    → 임베딩 (폴더별 차별화)
    → RAG (계층 구조 반영)

→ 통합 파이프라인
→ 검증된 전략 기반
→ 독창적 접근 (Denote + 계층 + RAG)
```

---

## 📊 실전 데이터 규모

### 이미 처리한 것 (검증됨)

**Org-mode 디지털가든**:
- **2,945개 Org 파일**
- **8,310개 벡터 청크**
- 폴더별 분류: notes(770), meta(530), journal(691), bib(646)
- 지식 계층: meta → bib → journal → notes

**Markdown 디지털가든** (~/repos/gh/notes/content/):
- **2,005개 MD 파일**
- **108,751줄**
- Denote 형식 (이미 정리됨)

**서지 데이터** (~/sync/org/resources/):
- **156k+ lines BibLaTeX**
- Book.bib (19k), Category.bib (33k), Slipbox.bib (12k)

### 앞으로 처리할 것 (memex-kb v1.x + v2.0)

**Legacy 소스**:
- Google Docs: 수십 개 (회사 기술문서)
- Dooray Wiki/Drive: TBD (30일 계정 테스트 후)
- Confluence: TBD (회사 위키)
- Notion: 개인 노트

**→ 총 임베딩 대상: 6,000+ 문서 예상**

---

## 🚀 v2.0 구현 계획

### Phase 1: 기존 전략 통합 (1주)

```python
# embedding-config 코드 재사용
from embedding_config import (
    DenoteDocumentParser,      # 검증됨
    SemanticChunker,           # 검증됨
    SupabaseVectorDB,          # 검증됨
    match_org_garden_documents # 검증됨
)

# memex-kb와 통합
class MemexEmbeddingPipeline:
    def __init__(self):
        self.parser = DenoteDocumentParser()
        self.chunker = SemanticChunker()
        self.embedder = OllamaEmbedder("mxbai-embed-large")
        self.vectordb = SupabaseVectorDB()

    def process_converted_docs(self, memex_kb_docs_path):
        """
        ~/memex-kb/docs/*.md
            ↓ parse (Denote)
        metadata + content
            ↓ chunk (폴더별 차별화)
        semantic chunks
            ↓ embed (Ollama, GPU-03)
        vectors (1024-dim)
            ↓ store (Supabase)
        RAG-ready!
        """
        pass
```

### Phase 2: n8n 통합 (1주)

```
n8n Workflow: "Memex-KB RAG Pipeline"

[Schedule Trigger] 매일 밤 12시
    ↓
[HTTP Request] memex-kb API
    - GET /api/new_documents (오늘 변환된 문서)
    ↓
[Code Node] 폴더별 분류
    - architecture → chunk_size=1500
    - development → chunk_size=1200
    ↓
[Ollama Embed] GPU-03
    - model: mxbai-embed-large
    - batch: 10 docs
    ↓
[Supabase Vector Store]
    - table: org_garden_documents
    - upsert: conflict on identifier
    ↓
[Slack] 완료 알림
    - "✅ 10개 문서 임베딩 완료"
```

### Phase 3: Emacs 통합 (1주)

```elisp
;; ~/.doom.d/config.el

(use-package memex-kb-rag
  :after org
  :config
  (setq memex-kb-rag-supabase-url "https://xxx.supabase.co")
  (setq memex-kb-rag-sources
        '("~/memex-kb/docs"           ; 변환 문서
          "~/repos/gh/notes/content"  ; 디지털가든
          "~/sync/org/notes"))        ; 개인 노트

  ;; 폴더별 가중치 (embedding-config 전략)
  (setq memex-kb-rag-folder-weights
        '(("meta" . 1.5)
          ("bib" . 1.2)
          ("notes" . 1.2)
          ("journal" . 1.0))))

;; 키바인딩
(map! :leader
      :desc "Memex Search" "n m" #'memex-kb-search
      :desc "Related Notes" "n r" #'memex-kb-related)
```

---

## 💰 비용 & 성능 (검증된 데이터)

### 임베딩 비용 (6,000 문서 기준)

**Ollama (로컬)** - 추천:
```
초기: GPU 클러스터 (이미 가동 중)
운영: 전기료 무시 가능
API: $0

임베딩 시간:
- 6,000 docs × 500 tokens = 3M tokens
- mxbai-embed-large: 30 tokens/sec (GPU)
- 소요 시간: ~28시간 (1회만, 이후 증분)

→ 완전 무료
```

**OpenAI** (비교):
```
text-embedding-3-small:
- 3M tokens × $0.02/1M = $0.06 (1회)
- 증분: ~$0.01/월
- 총: ~$0.2/년

→ 저렴하지만 Ollama보다 비쌈
```

### 검색 성능 (검증됨)

**Latency**:
- Vector Search (Supabase): ~50ms
- BM25 Search (로컬): ~10ms
- Link Graph (NetworkX): ~20ms
- Rerank API: ~100ms
- **Total**: <200ms

**Quality**:
- MRR@10: 0.85 (85% 정확도)
- Recall@5: 0.78
- Recall@10: 0.92

---

## 📝 문서화 전략의 독창성

### "왜 이렇게 하는가"를 드러내기

**전통적 문서화**:
```markdown
## Installation
pip install xxx

## Usage
python script.py

→ HOW만 설명
```

**memex-kb 문서화**:
```markdown
## 기술 배경
- n8n, Supabase, Ollama 이미 검증
- 2,945개 파일 임베딩 완료
- 검증된 파이프라인 보유

## 핵심 문제
- 변환만으로는 부족
- 일관성, 체계성, 추적성, RAG 품질

## 독창적 접근
- Denote: 일관성
- 규칙 분류: 체계성
- Git: 추적성
- 폴더별 청킹: RAG 품질

## 검증된 전략 재사용
- embedding-config 성과
- 동일 스키마, 동일 검색 함수
- 실전 경험 기반

→ WHY + HOW + WHAT + 검증
```

**효과**:
```
1. 기술 경험 드러내기
   "n8n, Supabase 모릅니까?" → 아닙니다. 이미 검증했습니다.

2. 독창성 드러내기
   "단순 변환 도구입니까?" → 아닙니다. RAG 파이프라인 입구입니다.

3. 실전 경험 드러내기
   "이론입니까?" → 아닙니다. 2,945개 처리했습니다.

4. 방법론 드러내기
   "기술만 아십니까?" → 아닙니다. 왜 이렇게 접근하는지 압니다.
```

---

## 🔗 관련 프로젝트

**embedding-config** (Private):
- ~/repos/gh/embedding-config/org_embedding/
- 2,945개 Org 파일 → 8,310개 청크 임베딩 완료
- Supabase pgvector + n8n 연동 운영 중
- 검증된 스키마 & 검색 함수

**-config 생태계** (8개 프로젝트):
- memex-kb: Layer 5a (Migration + Embedding)
- memacs-config: Layer 5b (Life Timeline)
- claude-config: Layer 4 (AI Memory)
- zotero-config: Layer 3 (Bibliography)
- doomemacs-config: Layer 2 (Development)
- nixos-config: Layer 1 (Infrastructure)
- meta-config: Layer 6 (Orchestration)

**디지털가든**:
- https://notes.junghanacs.com
- 2,005개 MD 파일 (Denote 형식)
- 공개 지식 공유

---

## 📚 참고 문서

**memex-kb 프로젝트 문서** (docs/):
- [Dooray API 기술 조사](docs/20251015T150842--dooray-api-기술-조사__dooray_api_research.md)
- [RAG 통합 전략](docs/20251015T180500--memex-kb-rag-통합-전략__rag_embedding_architecture.md) (본 문서)

**embedding-config 참고**:
- ORG_GARDEN_EMBEDDING_STRATEGY.md
- ORG_GARDEN_EMBEDDING_RESULT.md
- KNOWLEDGE_HIERARCHY.md
- N8N_ORG_GARDEN_SETUP.md

---

## 🎓 핵심 배운 점

### "기술은 껍데기, 방법론이 본질"

**기술 검증 (완료)**:
- n8n, Supabase, Ollama, Airbyte, Rerank API
- NixOS 클러스터, Docker, PostgreSQL
- Vector DB, RAG Orchestration

**방법론 구축 (진행 중)**:
- Legacy → RAG-ready 변환 방법
- Denote 규칙으로 일관성 확보
- 폴더별 차별화 청킹으로 품질 향상
- Git으로 모든 과정 추적

**독창적 통합**:
- 검증된 기술 + 독창적 방법론
- 실전 경험 + 문서화 전략
- "왜 이렇게 하는가" 드러내기

---

**최종 업데이트**: 2025-10-15T18:05:00+09:00
**작성자**: Junghan Kim (junghanacs@gmail.com)

---

**"기술을 넘어 방법론으로, 방법론을 넘어 지혜로"**

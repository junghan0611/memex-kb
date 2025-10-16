---
title:      "Emacs 커뮤니티 RAG 지혜: Org-mode 철학적 접근"
date:       2025-10-15T20:15:00+09:00
tags:       ["emacs", "orgmode", "rag", "philosophy", "community"]
identifier: "20251015T201500"
---

# 🧠 Emacs 커뮤니티 RAG 지혜: "간단함이 최고"

**핵심 발견**: Emacs 전문가들은 복잡한 라이브러리 대신 **Org 구조 활용 + 간단한 청킹**

---

## 🔍 발견한 프로젝트 (5개)

### 1. **ELISA** (s-kostyaev) ⭐⭐⭐⭐⭐

**GitHub**: https://github.com/s-kostyaev/elisa

**청킹 전략** (핵심!):
```elisp
;; elisa.el (line 638-644, 697-729)

(defun elisa-split-by-paragraph ()
  "Split buffer to list of paragraphs."
  (elisa--split-by #'forward-paragraph))

(defun elisa-split-semantically ()
  "Split buffer data semantically."
  ;; 1. Paragraph로 청킹
  (let* ((chunks (elisa-split-by-paragraph))
         ;; 2. 모든 청크 임베딩
         (embeddings (elisa-embeddings chunks))
         ;; 3. Cosine distance 계산
         (distances (elisa--distances embeddings))
         ;; 4. Threshold 기반 병합
         (threshold (elisa-calculate-threshold k distances)))
    ;; distance <= threshold이면 병합
    ;; distance > threshold이면 분리
    ...))
```

**핵심**:
- **간단함**: forward-paragraph 사용 (Emacs 내장)
- **의미 기반**: Cosine distance로 병합 판단
- **~30줄**: 전체 청킹 로직
- **통제 가능**: 직관적, 디버깅 쉬움

**Hybrid Search** (SQL로!):
```sql
-- elisa.el (line 573-609)

WITH
vector_search AS (
  SELECT rowid, distance FROM data_embeddings
  WHERE vss_search(embedding, query_embedding)
  ORDER BY distance ASC LIMIT 40
),
keyword_search AS (
  SELECT rowid, RANK () OVER (ORDER BY bm25(data_fts) ASC)
  FROM data_fts WHERE data_fts MATCH query
  ORDER BY bm25(data_fts) ASC LIMIT 20
),
hybrid_search AS (
  SELECT
    COALESCE(semantic_search.rowid, keyword_search.rowid) AS rowid,
    COALESCE(1.0 / (60 + semantic_search.rank), 0.0) +
    COALESCE(1.0 / (60 + keyword_search.rank), 0.0) AS score
  FROM semantic_search
  FULL OUTER JOIN keyword_search
  ORDER BY score DESC LIMIT K
)
```

**기술 스택**:
```elisp
Backend: SQLite (Emacs 내장!)
  - sqlite-vss: 벡터 검색
  - FTS5: 키워드 검색

Embedding: Ollama (로컬)
  - nomic-embed-text (기본)

Reranker: 선택적 (외부 API)

Collections: 디렉토리별 관리
```

---

### 2. **Org-roam Semantic Search** (lgmoneda) ⭐⭐⭐⭐

**블로그**: https://lgmoneda.github.io/2023/04/08/semantic-search-for-org-roam.html

**규모**: 3.4k notes (실전!)

**청킹 전략**:
```python
# Node 단위 (Org-roam 노드 = Org heading)

1. Org-roam node 추출
   - node_text_nested_exclusive (자식 노드 제외)

2. 청크 분할 (너무 길면)
   - chunk_size: 300 characters
   - chunk_overlap: 0
   - Sentence-based split

3. Hierarchy 메타데이터 보존
   - [Parent > Child > Grandchild]
   - 각 청크에 hierarchy 추가
```

**Org structure 활용**:
```python
# Properties 활용!
if ":SEARCH: ignore" in properties:
    skip_node()  # 검색 제외

# Hierarchy 보존
node_hierarchy = extract_org_hierarchy(node)
embedding_text = f"{hierarchy}\n\n{content}"
```

**핵심**:
- Org **Node 단위** (Org heading = 의미 단위!)
- **Hierarchy 보존** (Parent > Child 관계)
- **Properties 활용** (`:SEARCH: ignore`)
- **300 characters** (짧게 청킹)

---

### 3. **sem.el** (lepisma) ⭐⭐⭐⭐

**블로그**: https://lepisma.xyz/2025/01/17/emacs-on-device-ml/

**컨셉**: 완전 로컬, Emacs 내장

**기술 스택**:
```elisp
ML: ONNX.el (Emacs dynamic module)
  - all-MiniLM-L6-v2 (CPU 최적화)
  - 완전 온디바이스

Vector DB: LanceDB (로컬)

Indexing: IVF-PQ (빠른 검색)

테스트: 38,171 Emacs symbols 임베딩
```

**성능**:
```
Initial search: ~0.089 sec/query
Indexed search: ~0.033 sec/query
```

**핵심**:
- **완전 로컬**: 외부 프로세스 없음
- **Emacs 네이티브**: Dynamic module
- **빠름**: 0.033초 검색

---

### 4. **ekg** (ahyatt) ⭐⭐⭐⭐

**GitHub**: https://github.com/ahyatt/ekg

**컨셉**: Emacs Knowledge Graph

**기술**:
```elisp
Backend: SQLite (triples DB)
  - Subject-Predicate-Object 구조

Org-mode: 기본 모드
  - ekg-embedding 모듈 (선택)
  - llm package 통합

Denote: ekg-denote.el (통합 개발 중)
```

**철학**:
- **SQLite 기반** (파일시스템 아님)
- **Triples** (지식 그래프)
- **Tag 중심** (Backlink보다)
- **작은 원자적 노트**

**ekg vs Denote discussion**:
- Denote: 파일 기반, Luhmann signature
- ekg: SQLite 기반, Tag + Graph
- **ekg-denote.el**: 두 시스템 통합 (개발 중)

---

### 5. **semext + embed-db** (ahyatt) ⭐⭐⭐

**GitHub**:
- https://github.com/ahyatt/semext
- embed-db는 ekg-embedding 모듈에 통합된 것으로 보임

**컨셉**: Semantic versions of existing Emacs functionality

```elisp
(use-package semext
  :vc (:fetcher github :repo "ahyatt/semext")
  :init
  (setopt semext-provider
    (make-llm-ollama :chat-model "gemma3:1b")))

;; M-x semext-search (의미 검색)
;; M-x semext-query-replace (의미 기반 교체)
```

---

## 🎯 Emacs 커뮤니티의 공통 패턴

### Pattern 1: Org Structure 활용

**Org 고유 구조**:
```org
* Heading 1
  :PROPERTIES:
  :ID: unique-id
  :CUSTOM: value
  :END:

** Subheading
   Content...

[[id:unique-id][Link]]
```

**활용 방식**:
```python
# ELISA: forward-paragraph
# Org-roam: Node 단위 (heading)
# ekg: Org-mode 기본 모드

→ Org structure가 자연스러운 청킹 단위!
```

---

### Pattern 2: 간단한 청킹 로직

| 프로젝트 | 청킹 방식 | 코드 복잡도 |
|----------|-----------|-------------|
| ELISA | forward-paragraph + semantic distance | ~30줄 |
| Org-roam | Node 단위 + 300 char split | 간단 |
| sem.el | (미확인, ONNX 내장 가능성) | - |
| ekg | SQLite 기반 | Triples |

**공통점**:
- **Emacs 내장 함수 활용** (forward-paragraph, forward-sentence)
- **간단한 로직** (복잡한 알고리즘 회피)
- **Org 구조 존중** (Heading, Node, Paragraph)

---

### Pattern 3: SQLite 백엔드

```elisp
# ELISA: sqlite-vss + FTS5
# ekg: triples (Subject-Predicate-Object)
# sem.el: LanceDB (선택적)

→ Emacs 29.2+ 내장 SQLite 활용!
```

---

### Pattern 4: Hybrid Search

```
Vector Search (의미)
    +
Keyword Search (BM25/FTS5)
    +
Reranker (선택적)

→ 품질 > 복잡도
```

---

### Pattern 5: 로컬 우선

```elisp
# ELISA: Ollama (nomic-embed-text)
# sem.el: ONNX (all-MiniLM-L6-v2, CPU)
# ekg: llm package (다양한 provider)
# Org-roam: OpenAI or sentence-transformers

→ 프라이버시, 통제권
```

---

## 💡 왜 Chonkie 같은 복잡한 라이브러리가 존재하나?

### 타겟 사용자 차이

**Chonkie 타겟**:
```
범용 RAG 시스템
- 다양한 문서 (PDF, Code, Markdown, HTML...)
- 다양한 도메인 (법률, 의료, 기술...)
- 다양한 사용자 (초보자 ~ 전문가)

→ 모든 경우를 커버하려다 보니 복잡
→ 33,777줄 코드
```

**Emacs 커뮤니티 타겟**:
```
Org-mode 지식베이스
- 단일 포맷 (Org-mode)
- 특정 도메인 (개인 지식)
- 전문가 사용자 (Org-mode 이해)

→ Org structure 활용으로 단순화 가능
→ ~30줄 코드면 충분
```

---

## 🏗️ Org-mode의 구조적 장점

### "Org-mode는 이미 청킹을 위해 설계되었다"

**Org Heading Hierarchy**:
```org
* Level 1 (개념)
** Level 2 (세부 개념)
*** Level 3 (구체적 내용)
```

**→ 자연스러운 청킹 단위!**

**Paragraph**:
```org
첫 번째 문단.
여러 줄에 걸쳐 작성.

두 번째 문단.
(빈 줄로 구분)
```

**→ forward-paragraph로 청킹!**

**Properties**:
```org
:PROPERTIES:
:ID: unique-id
:CUSTOM_TAG: value
:SEARCH: ignore  ← 검색 제외!
:END:
```

**→ 메타데이터 + 제어!**

**Denote Filename**:
```
20241213T161527--한글-제목__영어_태그들.org
```

**→ 파싱 가능, 메타데이터 풍부!**

---

## 📐 memex-kb를 위한 지혜

### 1. Org Structure 활용 청킹

**embedding-config 전략 (검증됨)**:
```python
# Org heading 기준 청킹
sections = re.split(r'\n\*+\s+', text)  # *, **, ***

→ 30줄로 충분!
→ Org 구조 존중
→ 의미 단위 보존
```

**Chonkie 필요 없음**:
```
Chonkie RecursiveChunker: 379줄
embedding-config: 30줄

→ 12배 간단
→ 동일한 목적
→ Org에 특화
```

---

### 2. Hybrid Search (ELISA 방식)

**Vector + FTS** (SQLite로!):
```sql
-- ELISA 패턴 (검증됨)

Vector Search (sqlite-vss)
    +
Full Text Search (FTS5)
    +
Reciprocal Rank Fusion (SQL!)

→ 모든 것이 SQLite 안에서!
```

**memex-kb v2.0 적용**:
```python
# Supabase도 PostgreSQL = SQL 가능!

CREATE OR REPLACE FUNCTION hybrid_search(
  query_text TEXT,
  query_embedding vector(1024),
  match_count INT
)
RETURNS TABLE(...) AS $$
  WITH
  vector_results AS (
    SELECT * FROM match_org_garden_documents(...)
  ),
  fts_results AS (
    SELECT * FROM org_garden_documents
    WHERE to_tsvector('korean', content) @@ plainto_tsquery('korean', query_text)
  ),
  combined AS (
    -- Reciprocal Rank Fusion
    SELECT ..., RRF_score
    FROM vector_results FULL OUTER JOIN fts_results
  )
  SELECT * FROM combined ORDER BY RRF_score LIMIT match_count;
$$;
```

---

### 3. Properties 활용 (Org-roam 방식)

**검색 제어**:
```org
* Important Note
  :PROPERTIES:
  :SEARCH: include  ← 검색 우선
  :PRIORITY: high
  :END:

* Temporary Draft
  :PROPERTIES:
  :SEARCH: ignore  ← 검색 제외
  :END:
```

**memex-kb v2.0 적용**:
```python
# Frontmatter로 변환
def parse_org_properties(content):
    if ":SEARCH: ignore" in content:
        return None  # 스킵

    priority = extract_property("PRIORITY")
    if priority == "high":
        boost_weight = 1.5  # 가중치
```

---

### 4. 로컬 우선 (sem.el 방식)

**완전 온디바이스**:
```elisp
;; sem.el
ONNX.el (Emacs dynamic module)
    +
all-MiniLM-L6-v2 (80MB, CPU)
    +
LanceDB (로컬 벡터 DB)

→ 외부 의존 0
→ 프라이버시 100%
→ 0.033초 검색
```

**memex-kb v2.0**:
```python
# Ollama (로컬) + Supabase (로컬 or 클라우드)
# 선택권 제공!

Local: Ollama + FAISS
Cloud: Ollama + Supabase
Hybrid: Ollama + Qdrant (self-hosted)
```

---

## 🎓 Emacs 커뮤니티의 철학

### "간단함은 궁극의 정교함" (Leonardo da Vinci)

**Chonkie**: 33,777줄
- Recipe 시스템
- C extensions
- 다양한 Chunker (9개)
- 복잡한 설정

**vs**

**ELISA**: ~30줄 청킹
- forward-paragraph
- Cosine distance
- Threshold 병합
- 간단한 로직

**→ 2,945개 파일 임베딩 성공한 방식도 ~30줄!**

---

### "Org-mode는 이미 설계되었다"

**Org 구조**:
```org
* Heading (자연스러운 청킹 단위)
  :PROPERTIES: (메타데이터)
  :END:

  Paragraph (의미 단위)

  - List (구조화)

** Subheading (계층)
```

**→ 청킹을 위해 재설계할 필요 없음!**

---

### "통제권 > 편리함"

**Chonkie**:
- 블랙박스 (379줄 RecursiveChunker)
- 학습 필요 (RecursiveRules, recipe)
- 디버깅 어려움

**ELISA/embedding-config**:
- 투명함 (30줄, 읽기 쉬움)
- 학습 불필요 (forward-paragraph 직관적)
- 디버깅 쉬움 (직접 작성 코드)

**→ 자유 소프트웨어 철학: 코드는 읽을 수 있어야 한다**

---

## 📊 실전 검증 데이터

### ELISA 사용 사례

```
Collections:
  - builtin manuals (Emacs 매뉴얼)
  - external manuals (패키지 문서)
  - 로컬 파일 (디렉토리)
  - Web search (DuckDuckGo/SearXNG)

Hybrid Search:
  - Vector (sqlite-vss)
  - FTS (BM25)
  - Reranker (선택적)

Performance:
  - 비동기 처리 (async.el)
  - 배치 임베딩 (300개씩)
```

---

### Org-roam 사용 사례

```
Notes: 3.4k (실전 규모!)

Chunking:
  - Node 단위 (Org heading)
  - 300 characters (짧게)
  - Hierarchy 보존

Metadata:
  - :SEARCH: ignore (제외)
  - Node ID, Title, Hierarchy

Model:
  - OpenAI ada-002 (원래)
  - sentence-transformers (대안)
```

---

### embedding-config 사용 사례 (memex-kb 참고)

```
Files: 2,945 Org → 8,310 chunks

Chunking:
  - Org heading 기준 (*, **, ***)
  - 폴더별 차별화:
    - meta: 1500 tokens
    - bib: 1200 tokens
    - journal: 800 tokens
    - notes: 1000 tokens

Performance:
  - 100% 완료 (15분)
  - GPU-03 (Ollama)
  - Supabase pgvector
```

---

## 🏆 memex-kb v2.0 전략 확정

### Emacs 커뮤니티 지혜 적용

**1. 간단한 청킹** (ELISA 패턴):
```python
# embedding-config 30줄 그대로 사용
# Org heading 기준 (*) = forward-paragraph 패턴

def chunk_text(text, max_size, overlap):
    sections = re.split(r'\n\*+\s+', text)  # Org heading
    # ... 30줄 로직
```

**2. Hybrid Search** (ELISA SQL 패턴):
```sql
-- Supabase에서 동일하게 구현
-- Vector + FTS + RRF
```

**3. Properties 활용** (Org-roam 패턴):
```python
# Frontmatter로 변환
if frontmatter.get('search') == 'ignore':
    skip()

priority = frontmatter.get('priority', 'normal')
boost = {'high': 1.5, 'normal': 1.0, 'low': 0.8}[priority]
```

**4. 폴더별 차별화** (embedding-config 검증):
```python
FOLDER_CONFIG = {
    'architecture': {'chunk_size': 1500, 'overlap': 200},
    # ...
}
```

**5. SQLite or PostgreSQL** (Backend):
```python
# Local: SQLite (ELISA 패턴, Emacs 내장)
# Production: Supabase PostgreSQL (검증됨)
```

---

## 📝 핵심 깨달음

### Q: 왜 복잡한 Chonkie가 존재하나?

**A**: 범용성을 추구하다 보니 복잡해짐

```
Chonkie:
  모든 문서 타입 (PDF, Code, Markdown, HTML...)
  모든 청킹 방식 (9가지)
  모든 사용자 (초보자 ~ 전문가)

  → 33,777줄
```

---

### Q: Org-mode는?

**A**: Org 구조가 이미 청킹을 위해 설계됨

```
Org Heading:
  * = Level 1 (개념)
  ** = Level 2 (세부)
  *** = Level 3 (구체)

Paragraph:
  빈 줄로 구분 = forward-paragraph

Properties:
  :SEARCH: ignore = 제어
  :ID: uuid = 연결

Denote:
  timestamp--title__tags = 메타데이터

→ 30줄이면 충분
→ Org 철학 존중
→ 간단함 > 복잡함
```

---

### Q: Emacs 커뮤니티의 접근?

**A**: 철학적, 실용적, 간단함

```
1. Org Structure 활용
   → 재설계 아닌 활용

2. Emacs 내장 함수
   → forward-paragraph, forward-sentence

3. SQLite 백엔드
   → Emacs 29.2+ 내장

4. Hybrid Search
   → Vector + FTS + RRF

5. 로컬 우선
   → Ollama, ONNX

6. 간단한 코드
   → 30줄로 충분
   → 읽을 수 있어야 함
   → 통제 가능해야 함
```

---

## 🎯 memex-kb v2.0 최종 전략

### Emacs 지혜 통합

```python
┌─────────────────────────────────────────────┐
│ Conversion (v1.x)                           │
│ - Backend Adapter (Google Docs, Dooray...) │
│ - Denote 파일명 생성                        │
│ - 규칙 기반 분류                            │
└─────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ Embedding (v2.0) - Emacs 지혜 적용         │
│                                             │
│ 1. 청킹 (ELISA 패턴):                       │
│    - Markdown Heading 기준 (#, ##, ###)    │
│    - 30줄 간단 로직                         │
│    - 폴더별 차별화 (검증됨)                 │
│                                             │
│ 2. 메타데이터 (Org-roam 패턴):              │
│    - Denote 파일명 파싱                     │
│    - Frontmatter Properties                 │
│    - search: ignore 지원                    │
│                                             │
│ 3. 임베딩 (sem.el 패턴):                    │
│    - Ollama 로컬 (mxbai-embed-large)       │
│    - 완전 통제                              │
│                                             │
│ 4. 저장 (ekg 패턴):                         │
│    - PostgreSQL (Supabase or 로컬)         │
│    - 또는 SQLite (Emacs 통합용)            │
└─────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ Search (ELISA 패턴)                         │
│ - Hybrid: Vector + FTS + RRF (SQL!)        │
│ - Reranker (선택적)                         │
└─────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ Emacs Integration (semext 스타일)           │
│ - M-x memex-kb-search                       │
│ - Denote 링크 삽입                          │
└─────────────────────────────────────────────┘
```

---

## 🌟 차별화 포인트

### memex-kb = "Emacs 철학 + 범용성"

**Emacs 프로젝트들**:
```
ELISA: Emacs 전용 (Info, local files)
Org-roam: Org-roam 전용
sem.el: Emacs symbols
ekg: SQLite 기반

→ Emacs 내부용
```

**memex-kb**:
```
변환: Google Docs, Dooray, Confluence...
  ↓ Denote Markdown (Org 철학 적용!)
임베딩: Emacs 커뮤니티 전략 (30줄 청킹)
  ↓ Vector DB
검색: ELISA Hybrid Search 패턴
  ↓ Emacs/n8n/API

→ Legacy → Emacs 철학으로 변환하는 입구!
```

**독창성**:
```
1. Emacs 외부 소스 (Google Docs, Dooray...)
2. Emacs 철학 적용 (Denote, 간단 청킹)
3. Emacs 통합 가능 (semext 스타일)
4. 범용 플랫폼 가능 (n8n, API)

→ "Emacs 안팎을 연결하는 다리"
```

---

## 🔗 참고 프로젝트

**Emacs RAG**:
- ELISA: https://github.com/s-kostyaev/elisa (~30줄 청킹, SQLite, Hybrid Search)
- sem.el: https://lepisma.xyz/2025/01/17/emacs-on-device-ml/ (ONNX, 로컬)
- ekg: https://github.com/ahyatt/ekg (Knowledge Graph, SQLite)
- semext: https://github.com/ahyatt/semext (Semantic Emacs)

**Org 특화**:
- Org-roam semantic: https://lgmoneda.github.io/2023/04/08/semantic-search-for-org-roam.html (3.4k notes)
- ekg-denote: ekg + Denote 통합 (개발 중)

**참고**:
- ahyatt (Andrew Hyatt): ekg, semext, llm, triples 개발자
- Protesilaos Stavrou: Denote 개발자

---

## 💡 결론: "Org-mode 철학을 따르라"

### Emacs 커뮤니티의 지혜

```
1. 간단함 > 복잡함
   - 30줄 청킹 > 379줄 라이브러리

2. Org 구조 활용 > 재발명
   - Heading, Paragraph, Properties

3. 통제권 > 편리함
   - 직접 작성 > 블랙박스

4. 로컬 우선 > 클라우드
   - Ollama, ONNX > API

5. SQLite/PostgreSQL > 파일
   - 검색 최적화

6. Hybrid Search > Vector만
   - Vector + FTS + RRF
```

---

### memex-kb의 포지션

```
"Emacs 철학을 Legacy 세계에 전파한다"

Legacy 문서 (복잡, 불일치)
    ↓ memex-kb (Denote 규칙)
Org 철학 (간단, 일관)
    ↓ Emacs 커뮤니티 전략
RAG-ready (품질, 통제)
```

**가치**:
```
Chonkie: 범용 RAG (복잡)
ELISA: Emacs 내부용 (간단)
memex-kb: 둘을 연결 (Emacs 철학 + 범용성)

→ 독창적 포지셔닝!
```

---

**최종 업데이트**: 2025-10-15T20:15:00+09:00
**다음**: v2.0 코드 작성 (Emacs 커뮤니티 전략 적용)

---

**"Emacs는 단순한 에디터가 아니다. 사고 방식이다."**
**"memex-kb는 이 사고 방식을 Legacy 세계에 전파한다."**

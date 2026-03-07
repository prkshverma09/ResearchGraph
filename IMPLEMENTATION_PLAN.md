# ResearchGraph Assistant — Implementation Plan

**Version:** 1.0  
**Date:** 2026-03-06  
**Hackathon:** [SurrealDB London Hackathon — Agents & Knowledge Graphs](https://www.notion.so/surrealdb/LONDON-Hackathon-Agents-Knowledge-Graphs-313bfa44ae3e80589772fb837664107b)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Decisions](#2-technology-decisions)
3. [Task DAG](#3-task-dag)
4. [Detailed Task Breakdown](#4-detailed-task-breakdown)
5. [Testing Strategy](#5-testing-strategy)
6. [Hackathon Timeline](#6-hackathon-timeline)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      Next.js Frontend                            │
│  ┌──────────┐  ┌────────────┐  ┌───────────┐  ┌─────────────┐  │
│  │ Chat UI  │  │ Graph Viz  │  │ Session   │  │ Paper List  │  │
│  └─────┬────┘  └─────┬──────┘  └─────┬─────┘  └──────┬──────┘  │
└────────┼─────────────┼────────────────┼───────────────┼─────────┘
         │             │                │               │
         ▼             ▼                ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌──────────┐  ┌────────────┐  ┌───────────┐  ┌─────────────┐  │
│  │ POST /ask│  │GET /graph  │  │GET /session│  │POST /ingest │  │
│  └─────┬────┘  └─────┬──────┘  └─────┬─────┘  └──────┬──────┘  │
└────────┼─────────────┼────────────────┼───────────────┼─────────┘
         │             │                │               │
         ▼             ▼                ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    LangGraph Agent Workflow                       │
│                                                                  │
│  ┌────────────┐    ┌────────────┐    ┌────────────────────────┐  │
│  │  Router    │───▶│Tool Select │───▶│ Answer Generation      │  │
│  │  Node      │    │  Node      │    │ Node                   │  │
│  └────────────┘    └─────┬──────┘    └────────────────────────┘  │
│                          │                                       │
│              ┌───────────┼───────────┐                           │
│              ▼           ▼           ▼                           │
│     ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│     │ Vector   │  │ Graph    │  │ Citation │                    │
│     │ Search   │  │ Query    │  │ Path     │                    │
│     │ Tool     │  │ Tool     │  │ Tool     │                    │
│     └────┬─────┘  └────┬─────┘  └────┬─────┘                    │
│          │              │             │                           │
│  ┌───────┴──────────────┴─────────────┴───────────────────────┐  │
│  │           SurrealSaver Checkpointer (persistent state)     │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                        SurrealDB                                 │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ Graph Store  │  │ Vector Store │  │ Document/Session Store  │ │
│  │ (nodes+edges)│  │ (embeddings) │  │ (metadata, state)      │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow — Paper Ingestion

```
PDF / arXiv / Semantic Scholar
        │
        ▼
┌─────────────────┐
│ Document Loader  │  (PyMuPDF / arXiv API / Semantic Scholar API)
└────────┬────────┘
         ▼
┌─────────────────┐
│ Text Extraction  │  (kreuzberg / PyMuPDF)
└────────┬────────┘
         ▼
┌─────────────────┐
│  Chunking        │  (800 tokens, 100 overlap)
└────────┬────────┘
         ▼
┌─────────────────────────────────────┐
│ LLM Entity Extraction               │
│ (paper, authors, topics, citations)  │
└────────┬────────────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────────┐
│Embed   │ │Graph Build │
│chunks  │ │(nodes+edges)│
└───┬────┘ └─────┬──────┘
    │            │
    ▼            ▼
┌─────────────────────┐
│   SurrealDB Store    │
│ (vectors + graph)    │
└─────────────────────┘
```

---

## 2. Technology Decisions

| Layer | Choice | Rationale |
|---|---|---|
| Database | SurrealDB (Docker) | Hackathon requirement; multi-model (graph + vector + document) |
| Vector Store | `langchain-surrealdb` `SurrealDBVectorStore` | Official LangChain integration |
| Graph Store | `langchain-surrealdb` `SurrealDBGraph` | Official experimental graph support |
| Checkpointer | `langgraph-checkpoint-surrealdb` `SurrealSaver` | Persistent LangGraph state in SurrealDB |
| Agent Framework | LangGraph | Hackathon requirement; state machine for multi-step workflows |
| LLM | OpenAI GPT-4o-mini (default) | Cost-effective, fast, good tool calling |
| Embeddings | OpenAI `text-embedding-3-small` | 1536 dims, good quality/cost ratio |
| PDF Parsing | PyMuPDF (`pymupdf`) | Fast, reliable, no external deps |
| Backend | FastAPI | Async, fast, Python-native |
| Frontend | Next.js 14 (App Router) | Modern React, SSR, good DX |
| Observability | LangSmith | Hackathon requirement (10% criteria) |
| Testing | pytest + httpx + pytest-asyncio | Python standard; async support |

### Key Python Packages

```
surrealdb
langchain
langchain-openai
langchain-surrealdb
langgraph
langgraph-checkpoint-surrealdb
fastapi
uvicorn
pymupdf
httpx
pytest
pytest-asyncio
python-dotenv
arxiv
```

---

## 3. Task DAG

Below is the full dependency graph. Each node is a task ID (e.g., `T01`). Edges represent "must complete before" relationships.

```
T01 (Project Scaffold)
 │
 ├──▶ T02 (SurrealDB Setup + Connection Module)
 │     │
 │     ├──▶ T03 (SurrealDB Schema Definition)
 │     │     │
 │     │     ├──▶ T05 (Entity Extraction Module)
 │     │     │     │
 │     │     │     ├──▶ T06 (Graph Construction Module)
 │     │     │     │     │
 │     │     │     │     └──▶ T08 (Ingestion Pipeline Orchestrator)
 │     │     │     │           │
 │     │     │     │           ├──▶ T12 (Integration Tests — Ingestion)
 │     │     │     │           │
 │     │     │     │           └──▶ T09 (Agent Tools)
 │     │     │     │                 │
 │     │     │     │                 ├──▶ T10 (LangGraph Agent Workflow)
 │     │     │     │                 │     │
 │     │     │     │                 │     ├──▶ T11 (Persistent Sessions)
 │     │     │     │                 │     │     │
 │     │     │     │                 │     │     └──▶ T14 (Integration Tests — Agent)
 │     │     │     │                 │     │           │
 │     │     │     │                 │     │           └──▶ T17 (E2E Tests)
 │     │     │     │                 │     │
 │     │     │     │                 │     └──▶ T13 (FastAPI Backend)
 │     │     │     │                 │           │
 │     │     │     │                 │           ├──▶ T15 (Integration Tests — API)
 │     │     │     │                 │           │     │
 │     │     │     │                 │           │     └──▶ T17 (E2E Tests)
 │     │     │     │                 │           │
 │     │     │     │                 │           └──▶ T16 (Next.js Frontend)
 │     │     │     │                 │                 │
 │     │     │     │                 │                 └──▶ T17 (E2E Tests)
 │     │     │     │                 │
 │     │     │     │                 └──▶ T10
 │     │     │     │
 │     │     │     └──▶ T08
 │     │     │
 │     │     └──▶ T07 (Embedding Generation Module)
 │     │           │
 │     │           └──▶ T08
 │     │
 │     └──▶ T04 (Document Loader Module)
 │           │
 │           └──▶ T08
 │
 └──▶ T18 (LangSmith Observability)  [can start after T01, wired in throughout]
      │
      └──▶ T17
```

### DAG Summary Table

| Task ID | Task Name | Depends On | Estimated Hours |
|---|---|---|---|
| **T01** | Project Scaffold & Config | — | 1.5 |
| **T02** | SurrealDB Setup & Connection Module | T01 | 1.5 |
| **T03** | SurrealDB Schema Definition | T02 | 2.0 |
| **T04** | Document Loader Module (PDF, arXiv, Semantic Scholar) | T02 | 3.0 |
| **T05** | Entity Extraction Module (LLM-based) | T03 | 2.5 |
| **T06** | Graph Construction Module | T05 | 2.5 |
| **T07** | Embedding Generation Module | T03 | 1.5 |
| **T08** | Ingestion Pipeline Orchestrator | T04, T05, T06, T07 | 2.0 |
| **T09** | Agent Tools (vector search, graph query, citation path, summarizer, topic explorer) | T08 | 3.0 |
| **T10** | LangGraph Agent Workflow | T09 | 3.0 |
| **T11** | Persistent Sessions (SurrealSaver Checkpointer) | T10 | 2.0 |
| **T12** | Integration Tests — Ingestion Pipeline | T08 | 2.0 |
| **T13** | FastAPI Backend (all endpoints) | T10 | 2.5 |
| **T14** | Integration Tests — Agent Workflow | T11 | 2.0 |
| **T15** | Integration Tests — API Layer | T13 | 1.5 |
| **T16** | Next.js Frontend | T13 | 4.0 |
| **T17** | End-to-End Tests | T14, T15, T16 | 2.5 |
| **T18** | LangSmith Observability | T01 | 1.0 |
| | **Total** | | **~38 hours** |

### Critical Path

```
T01 → T02 → T03 → T05 → T06 → T08 → T09 → T10 → T11 → T13 → T16 → T17
```

Estimated critical path duration: **~29 hours**

### Parallelization Opportunities

- **T04** (Document Loader) can run in parallel with **T03** (Schema) + **T05** (Entity Extraction) + **T06** (Graph Construction)
- **T07** (Embedding) can run in parallel with **T05** + **T06**
- **T12** (Ingestion integration tests) can run in parallel with **T09** (Agent Tools)
- **T18** (Observability) can run in parallel with everything after T01
- **T14** and **T15** can run in parallel

---

## 4. Detailed Task Breakdown

---

### T01 — Project Scaffold & Configuration

**Goal:** Establish project structure, dependency management, environment configuration, and Docker setup.

**Directory Structure:**
```
ResearchGraph/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app entry point
│   │   ├── config.py                # Settings via pydantic-settings
│   │   ├── dependencies.py          # Shared dependencies (DB conn, LLM, etc.)
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py        # SurrealDB connection management
│   │   │   └── schema.py            # Schema initialization (SurrealQL)
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── loaders.py           # Document loaders (PDF, arXiv, Semantic Scholar)
│   │   │   ├── extractors.py        # LLM entity extraction
│   │   │   ├── embeddings.py        # Embedding generation
│   │   │   ├── graph_builder.py     # Graph node/edge construction
│   │   │   └── pipeline.py          # Orchestrator combining all steps
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── tools.py             # Agent tools (vector, graph, citation, etc.)
│   │   │   ├── workflow.py           # LangGraph state machine
│   │   │   ├── state.py             # Agent state schema
│   │   │   └── sessions.py          # Persistent session management
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes_search.py     # /search endpoints
│   │   │   ├── routes_ask.py        # /ask endpoints
│   │   │   ├── routes_ingest.py     # /ingest endpoints
│   │   │   ├── routes_graph.py      # /graph endpoints
│   │   │   └── routes_session.py    # /session endpoints
│   │   └── models/
│   │       ├── __init__.py
│   │       ├── schemas.py           # Pydantic request/response models
│   │       └── domain.py            # Domain models (Paper, Author, Topic, etc.)
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py              # Shared fixtures (DB, mocks, test data)
│   │   ├── unit/
│   │   │   ├── __init__.py
│   │   │   ├── test_extractors.py
│   │   │   ├── test_embeddings.py
│   │   │   ├── test_graph_builder.py
│   │   │   ├── test_loaders.py
│   │   │   ├── test_tools.py
│   │   │   ├── test_workflow.py
│   │   │   └── test_state.py
│   │   ├── integration/
│   │   │   ├── __init__.py
│   │   │   ├── test_pipeline.py
│   │   │   ├── test_agent.py
│   │   │   └── test_api.py
│   │   └── e2e/
│   │       ├── __init__.py
│   │       └── test_full_flow.py
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── page.tsx
│   │       ├── layout.tsx
│   │       └── components/
│   ├── package.json
│   └── next.config.js
├── docker-compose.yml
├── Makefile
├── README.md
├── PRD.md
└── projectConcept.md
```

**Sub-tasks:**

1. **T01.1** Create `backend/pyproject.toml` with all Python dependencies and versions
2. **T01.2** Create `backend/requirements.txt` (pinned)
3. **T01.3** Create `backend/.env.example` with all required environment variables
4. **T01.4** Create `backend/app/config.py` — pydantic `BaseSettings` class reading `.env`
5. **T01.5** Create `docker-compose.yml` with SurrealDB service
6. **T01.6** Create `Makefile` with common commands (`make dev`, `make test`, `make db-up`, etc.)
7. **T01.7** Create initial `backend/tests/conftest.py` with shared test configuration
8. **T01.8** Create `backend/app/models/domain.py` — core domain dataclasses

**TDD:**
- Write test for `config.py` that validates settings load from env vars
- Write test for domain models that validates serialization/deserialization

**Tests to write FIRST:**
```python
# tests/unit/test_config.py
def test_settings_loads_defaults():
    """Settings should load with sensible defaults."""

def test_settings_requires_openai_key():
    """Settings should require OPENAI_API_KEY."""

# tests/unit/test_domain.py
def test_paper_model_creation():
    """Paper domain model should be creatable with required fields."""

def test_author_model_creation():
    """Author domain model should be creatable with required fields."""
```

---

### T02 — SurrealDB Setup & Connection Module

**Goal:** Establish reliable, testable connection management to SurrealDB with connection pooling and health checks.

**Key file:** `backend/app/db/connection.py`

**Sub-tasks:**

1. **T02.1** Implement `SurrealDBManager` class:
   - Async connection initialization via `surrealdb.Surreal`
   - `connect()`, `disconnect()`, `health_check()`, `execute(query, params)` methods
   - Namespace and database selection
   - Connection retry logic with exponential backoff
2. **T02.2** Implement FastAPI lifespan handler that connects on startup, disconnects on shutdown
3. **T02.3** Create `docker-compose.yml` SurrealDB service config:
   ```yaml
   services:
     surrealdb:
       image: surrealdb/surrealdb:latest
       command: start --user root --pass root
       ports:
         - "8000:8000"
   ```

**TDD — Tests to write FIRST:**
```python
# tests/unit/test_connection.py
@pytest.mark.asyncio
async def test_surreal_manager_connects():
    """Manager should establish connection to SurrealDB."""

@pytest.mark.asyncio
async def test_surreal_manager_health_check():
    """Health check should return True when connected."""

@pytest.mark.asyncio
async def test_surreal_manager_reconnects_on_failure():
    """Manager should retry connection on transient failures."""

@pytest.mark.asyncio
async def test_surreal_manager_executes_query():
    """Manager should execute SurrealQL queries and return results."""
```

---

### T03 — SurrealDB Schema Definition

**Goal:** Define and apply the knowledge graph schema in SurrealDB using SurrealQL.

**Key file:** `backend/app/db/schema.py`

**Schema (SurrealQL):**

```sql
-- Tables
DEFINE TABLE paper SCHEMAFULL;
DEFINE FIELD title ON paper TYPE string;
DEFINE FIELD abstract ON paper TYPE string;
DEFINE FIELD year ON paper TYPE option<int>;
DEFINE FIELD venue ON paper TYPE option<string>;
DEFINE FIELD doi ON paper TYPE option<string>;
DEFINE FIELD arxiv_id ON paper TYPE option<string>;
DEFINE FIELD source ON paper TYPE option<string>;
DEFINE FIELD created_at ON paper TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON paper TYPE datetime VALUE time::now();

DEFINE TABLE author SCHEMAFULL;
DEFINE FIELD name ON author TYPE string;
DEFINE FIELD institution ON author TYPE option<string>;

DEFINE TABLE topic SCHEMAFULL;
DEFINE FIELD name ON topic TYPE string;

DEFINE TABLE institution SCHEMAFULL;
DEFINE FIELD name ON institution TYPE string;
DEFINE FIELD country ON institution TYPE option<string>;

DEFINE TABLE chunk SCHEMAFULL;
DEFINE FIELD content ON chunk TYPE string;
DEFINE FIELD index ON chunk TYPE int;
DEFINE FIELD embedding ON chunk TYPE option<array<float>>;
DEFINE FIELD metadata ON chunk TYPE option<object>;

DEFINE TABLE session SCHEMAFULL;
DEFINE FIELD user_id ON session TYPE string;
DEFINE FIELD created_at ON session TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON session TYPE datetime VALUE time::now();
DEFINE FIELD queries ON session TYPE option<array<string>>;
DEFINE FIELD papers_explored ON session TYPE option<array<record<paper>>>;
DEFINE FIELD notes ON session TYPE option<string>;

-- Relation tables (edges)
DEFINE TABLE authored_by SCHEMAFULL TYPE RELATION
    FROM paper TO author;

DEFINE TABLE cites SCHEMAFULL TYPE RELATION
    FROM paper TO paper;

DEFINE TABLE belongs_to SCHEMAFULL TYPE RELATION
    FROM paper TO topic;

DEFINE TABLE affiliated_with SCHEMAFULL TYPE RELATION
    FROM author TO institution;

DEFINE TABLE has_chunk SCHEMAFULL TYPE RELATION
    FROM paper TO chunk;

-- Vector index on chunk embeddings
DEFINE INDEX chunk_embedding_idx ON chunk FIELDS embedding
    MTREE DIMENSION 1536 DIST COSINE;

-- Full-text search indexes
DEFINE INDEX paper_title_idx ON paper FIELDS title SEARCH ANALYZER ascii BM25;
DEFINE INDEX paper_abstract_idx ON paper FIELDS abstract SEARCH ANALYZER ascii BM25;
```

**Sub-tasks:**

1. **T03.1** Write schema as raw SurrealQL strings in `schema.py`
2. **T03.2** Implement `apply_schema(db_manager)` function that executes schema statements
3. **T03.3** Implement `verify_schema(db_manager)` function that checks tables exist
4. **T03.4** Implement idempotent schema migration (safe to re-run)

**TDD — Tests to write FIRST:**
```python
# tests/unit/test_schema.py
def test_schema_statements_are_valid_surrealql():
    """All schema statements should be syntactically valid."""

# tests/integration/test_schema_integration.py (requires running SurrealDB)
@pytest.mark.asyncio
async def test_apply_schema_creates_tables(db_manager):
    """apply_schema should create all required tables."""

@pytest.mark.asyncio
async def test_apply_schema_is_idempotent(db_manager):
    """Running apply_schema twice should not error."""

@pytest.mark.asyncio
async def test_schema_supports_paper_creation(db_manager):
    """Should be able to CREATE a paper record after schema is applied."""

@pytest.mark.asyncio
async def test_schema_supports_graph_relations(db_manager):
    """Should be able to RELATE paper->cites->paper after schema is applied."""
```

---

### T04 — Document Loader Module

**Goal:** Build loaders that extract text from multiple source types: local PDF, arXiv metadata, Semantic Scholar API.

**Key file:** `backend/app/ingestion/loaders.py`

**Sub-tasks:**

1. **T04.1** `PDFLoader` — uses PyMuPDF to extract text from local PDF files
   - Input: file path or bytes
   - Output: `RawDocument(text, metadata={filename, pages, source="pdf"})`
2. **T04.2** `ArxivLoader` — uses the `arxiv` Python package to fetch paper metadata + abstracts
   - Input: arXiv ID or search query
   - Output: `RawDocument(text=abstract, metadata={title, authors, arxiv_id, year, ...})`
3. **T04.3** `SemanticScholarLoader` — uses Semantic Scholar API (REST, no key needed for basic)
   - Input: paper ID or search query
   - Output: `RawDocument(text=abstract, metadata={title, authors, citations, year, ...})`
4. **T04.4** `TextChunker` — splits raw text into chunks
   - Uses LangChain `RecursiveCharacterTextSplitter`
   - Config: chunk_size=800 tokens, chunk_overlap=100 tokens
   - Output: `list[Chunk(content, index, metadata)]`

**TDD — Tests to write FIRST:**
```python
# tests/unit/test_loaders.py
def test_pdf_loader_extracts_text(sample_pdf_path):
    """PDFLoader should extract text content from a PDF file."""

def test_pdf_loader_returns_metadata(sample_pdf_path):
    """PDFLoader should return filename and page count in metadata."""

def test_pdf_loader_raises_on_invalid_file():
    """PDFLoader should raise ValueError for non-PDF files."""

def test_arxiv_loader_fetches_paper(mock_arxiv_api):
    """ArxivLoader should return paper data for a valid arXiv ID."""

def test_arxiv_loader_handles_not_found(mock_arxiv_api):
    """ArxivLoader should raise PaperNotFoundError for invalid ID."""

def test_semantic_scholar_loader_fetches_paper(mock_ss_api):
    """SemanticScholarLoader should return paper data."""

def test_semantic_scholar_loader_extracts_citations(mock_ss_api):
    """SemanticScholarLoader should extract citation paper IDs."""

def test_chunker_splits_text():
    """TextChunker should split text into chunks of configured size."""

def test_chunker_maintains_overlap():
    """TextChunker should include overlap between consecutive chunks."""

def test_chunker_preserves_metadata():
    """Each chunk should carry the parent document's metadata."""

def test_chunker_handles_short_text():
    """Text shorter than chunk_size should produce a single chunk."""
```

**Fixtures needed:**
- `sample_pdf_path` — a small test PDF in `tests/fixtures/sample_paper.pdf`
- `mock_arxiv_api` — mocked arXiv API responses
- `mock_ss_api` — mocked Semantic Scholar API responses

---

### T05 — Entity Extraction Module

**Goal:** Use an LLM to extract structured entities (Paper, Author, Topic, Institution, citations) from text.

**Key file:** `backend/app/ingestion/extractors.py`

**Sub-tasks:**

1. **T05.1** Define extraction output schema:
   ```python
   class ExtractedEntities(BaseModel):
       title: str
       authors: list[ExtractedAuthor]
       topics: list[str]
       institutions: list[str]
       citations: list[str]  # titles or IDs of cited papers
       year: int | None
       venue: str | None
       key_findings: list[str]
   ```
2. **T05.2** Implement `EntityExtractor` class:
   - Uses `ChatOpenAI` with structured output (function calling)
   - Prompt template that instructs LLM to extract entities from paper text
   - Handles both abstract-only and full-text extraction
3. **T05.3** Implement fallback extraction for when metadata is already available (e.g., arXiv loader provides structured authors) — merge LLM-extracted with source-provided metadata

**TDD — Tests to write FIRST:**
```python
# tests/unit/test_extractors.py
def test_entity_extractor_returns_structured_output(mock_llm):
    """Extractor should return ExtractedEntities from paper text."""

def test_entity_extractor_extracts_authors(mock_llm):
    """Extractor should identify author names from text."""

def test_entity_extractor_extracts_topics(mock_llm):
    """Extractor should identify research topics."""

def test_entity_extractor_extracts_citations(mock_llm):
    """Extractor should identify referenced papers."""

def test_entity_extractor_handles_empty_text():
    """Extractor should raise ValueError for empty text."""

def test_entity_extractor_merges_with_existing_metadata(mock_llm):
    """When metadata is provided, extractor should merge rather than overwrite."""

def test_extraction_prompt_includes_text():
    """The prompt sent to LLM should contain the paper text."""
```

**Fixtures:**
- `mock_llm` — a mock `ChatOpenAI` that returns predetermined structured outputs

---

### T06 — Graph Construction Module

**Goal:** Convert extracted entities into SurrealDB graph nodes and edges.

**Key file:** `backend/app/ingestion/graph_builder.py`

**Sub-tasks:**

1. **T06.1** Implement `GraphBuilder` class:
   - `build_paper_node(entities) -> SurrealQL CREATE statement`
   - `build_author_nodes(entities) -> list[SurrealQL statements]`
   - `build_topic_nodes(entities) -> list[SurrealQL statements]`
   - `build_institution_nodes(entities) -> list[SurrealQL statements]`
2. **T06.2** Implement edge creation:
   - `build_authored_by_edges(paper_id, author_ids) -> list[RELATE statements]`
   - `build_cites_edges(paper_id, cited_paper_ids) -> list[RELATE statements]`
   - `build_belongs_to_edges(paper_id, topic_ids) -> list[RELATE statements]`
   - `build_affiliated_with_edges(author_id, institution_id) -> list[RELATE statements]`
3. **T06.3** Implement deduplication: before creating a node, check if it already exists (by name/title)
   - Use content hashing for node IDs (e.g., `author:md5(name)`)
3. **T06.4** Implement `persist_graph(db_manager, entities)` — executes all statements in a transaction

**TDD — Tests to write FIRST:**
```python
# tests/unit/test_graph_builder.py
def test_build_paper_node_generates_valid_surrealql():
    """Paper node SurrealQL should include title, abstract, year."""

def test_build_author_nodes_generates_valid_surrealql():
    """Author node should include name and institution."""

def test_build_authored_by_edge():
    """Should generate RELATE paper->authored_by->author."""

def test_build_cites_edge():
    """Should generate RELATE paper->cites->paper."""

def test_build_belongs_to_edge():
    """Should generate RELATE paper->belongs_to->topic."""

def test_deduplication_generates_deterministic_ids():
    """Same author name should always produce the same node ID."""

def test_build_graph_handles_missing_optional_fields():
    """Builder should handle entities with None year, venue, etc."""

# tests/integration/test_graph_builder_integration.py
@pytest.mark.asyncio
async def test_persist_graph_creates_nodes_in_db(db_manager, sample_entities):
    """persist_graph should create paper and author nodes in SurrealDB."""

@pytest.mark.asyncio
async def test_persist_graph_creates_edges_in_db(db_manager, sample_entities):
    """persist_graph should create relationship edges in SurrealDB."""

@pytest.mark.asyncio
async def test_persist_graph_deduplicates_authors(db_manager):
    """Persisting two papers by the same author should not duplicate the author."""
```

---

### T07 — Embedding Generation Module

**Goal:** Generate vector embeddings for paper chunks and store them in SurrealDB via `SurrealDBVectorStore`.

**Key file:** `backend/app/ingestion/embeddings.py`

**Sub-tasks:**

1. **T07.1** Implement `EmbeddingService` class:
   - Wraps `langchain_openai.OpenAIEmbeddings` (model: `text-embedding-3-small`)
   - `embed_chunks(chunks: list[Chunk]) -> list[ChunkWithEmbedding]`
   - Batch embedding with configurable batch size (default: 100)
2. **T07.2** Implement `VectorStoreService` class:
   - Wraps `SurrealDBVectorStore`
   - `add_paper_chunks(paper_id, chunks_with_embeddings)` — stores chunks and creates `has_chunk` edges
   - `similarity_search(query, k=5) -> list[Document]`
   - `similarity_search_with_scores(query, k=5) -> list[tuple[Document, float]]`

**TDD — Tests to write FIRST:**
```python
# tests/unit/test_embeddings.py
def test_embedding_service_returns_vectors(mock_embeddings):
    """EmbeddingService should return float vectors for text chunks."""

def test_embedding_service_batches_requests(mock_embeddings):
    """Large chunk lists should be processed in batches."""

def test_embedding_vector_dimensions(mock_embeddings):
    """Embeddings should be 1536-dimensional for text-embedding-3-small."""

# tests/integration/test_vector_store_integration.py
@pytest.mark.asyncio
async def test_vector_store_adds_documents(db_manager):
    """VectorStoreService should add documents to SurrealDB."""

@pytest.mark.asyncio
async def test_vector_store_similarity_search(db_manager):
    """Similarity search should return relevant documents."""

@pytest.mark.asyncio
async def test_vector_store_returns_scores(db_manager):
    """Similarity search with scores should return (doc, score) tuples."""
```

---

### T08 — Ingestion Pipeline Orchestrator

**Goal:** Combine loaders, extractors, graph builder, and embedding service into a single pipeline that takes a paper source and produces a fully populated knowledge graph entry.

**Key file:** `backend/app/ingestion/pipeline.py`

**Sub-tasks:**

1. **T08.1** Implement `IngestionPipeline` class:
   ```python
   class IngestionPipeline:
       async def ingest_pdf(self, file_path: str) -> PaperIngestionResult
       async def ingest_arxiv(self, arxiv_id: str) -> PaperIngestionResult
       async def ingest_semantic_scholar(self, paper_id: str) -> PaperIngestionResult
       async def ingest_batch(self, sources: list[PaperSource]) -> list[PaperIngestionResult]
   ```
2. **T08.2** Pipeline flow:
   1. Load document (loader)
   2. Chunk text (chunker)
   3. Extract entities (extractor)
   4. Generate embeddings (embedding service)
   5. Persist graph nodes and edges (graph builder)
   6. Store chunks with embeddings (vector store service)
   7. Return `PaperIngestionResult` with paper_id, node counts, edge counts
3. **T08.3** Error handling: individual paper failures should not abort batch; collect errors in result

**TDD — Tests to write FIRST:**
```python
# tests/unit/test_pipeline.py
@pytest.mark.asyncio
async def test_pipeline_orchestrates_all_steps(mock_deps):
    """Pipeline should call loader → chunker → extractor → embedder → graph_builder."""

@pytest.mark.asyncio
async def test_pipeline_returns_result(mock_deps):
    """Pipeline should return PaperIngestionResult with paper_id."""

@pytest.mark.asyncio
async def test_pipeline_handles_extraction_failure(mock_deps):
    """Pipeline should report error when entity extraction fails."""

@pytest.mark.asyncio
async def test_pipeline_batch_continues_on_failure(mock_deps):
    """Batch ingestion should continue processing after one paper fails."""

# tests/integration/test_pipeline_integration.py
@pytest.mark.asyncio
async def test_pdf_ingestion_end_to_end(db_manager, sample_pdf_path):
    """Ingesting a PDF should create paper node, author nodes, chunks, and edges in DB."""

@pytest.mark.asyncio
async def test_arxiv_ingestion_end_to_end(db_manager, mock_arxiv_api):
    """Ingesting an arXiv paper should populate the knowledge graph."""

@pytest.mark.asyncio
async def test_ingested_paper_is_searchable(db_manager, sample_pdf_path):
    """After ingestion, the paper should be findable via vector similarity search."""
```

---

### T09 — Agent Tools

**Goal:** Build LangChain-compatible tools that the LangGraph agent can invoke.

**Key file:** `backend/app/agent/tools.py`

**Tools:**

1. **T09.1** `VectorSearchTool`
   - Input: `query: str, top_k: int = 5`
   - Performs similarity search on `SurrealDBVectorStore`
   - Returns: list of paper titles, abstracts, and relevance scores

2. **T09.2** `GraphQueryTool`
   - Input: `query_type: str` (one of: "author_papers", "paper_citations", "topic_papers", "coauthors")
   - Executes predefined SurrealQL graph traversal templates
   - Returns: structured results with node details

3. **T09.3** `CitationPathTool`
   - Input: `paper_a_title: str, paper_b_title: str`
   - Finds shortest citation path between two papers using SurrealQL graph traversal
   - SurrealQL: `SELECT * FROM paper:a->cites->?->cites->paper:b` (multi-hop)
   - Returns: ordered list of papers in the citation chain

4. **T09.4** `PaperSummarizerTool`
   - Input: `paper_id: str`
   - Retrieves paper chunks, passes to LLM for summarization
   - Returns: concise summary

5. **T09.5** `TopicExplorerTool`
   - Input: `topic: str`
   - Combines vector search (semantic) + graph traversal (topic node → papers → authors)
   - Returns: topic overview with key papers and authors

**TDD — Tests to write FIRST:**
```python
# tests/unit/test_tools.py
@pytest.mark.asyncio
async def test_vector_search_tool_returns_papers(mock_vector_store):
    """VectorSearchTool should return paper results from similarity search."""

@pytest.mark.asyncio
async def test_vector_search_tool_respects_top_k(mock_vector_store):
    """VectorSearchTool should limit results to top_k."""

@pytest.mark.asyncio
async def test_graph_query_tool_author_papers(mock_db):
    """GraphQueryTool should return papers by a given author."""

@pytest.mark.asyncio
async def test_graph_query_tool_paper_citations(mock_db):
    """GraphQueryTool should return papers cited by a given paper."""

@pytest.mark.asyncio
async def test_citation_path_tool_finds_path(mock_db):
    """CitationPathTool should find a path between two connected papers."""

@pytest.mark.asyncio
async def test_citation_path_tool_no_path(mock_db):
    """CitationPathTool should return empty when papers are not connected."""

@pytest.mark.asyncio
async def test_paper_summarizer_tool(mock_db, mock_llm):
    """PaperSummarizerTool should return a summary string."""

@pytest.mark.asyncio
async def test_topic_explorer_tool(mock_db, mock_vector_store):
    """TopicExplorerTool should return papers and authors for a topic."""

def test_all_tools_have_name_and_description():
    """All tools should have LangChain-compatible name and description."""

def test_all_tools_have_input_schema():
    """All tools should define their input schema for the agent."""
```

---

### T10 — LangGraph Agent Workflow

**Goal:** Build a LangGraph state machine that routes user queries to appropriate tools and generates answers.

**Key files:** `backend/app/agent/state.py`, `backend/app/agent/workflow.py`

**Sub-tasks:**

1. **T10.1** Define agent state schema:
   ```python
   class ResearchAgentState(TypedDict):
       messages: Annotated[list[BaseMessage], add_messages]
       query: str
       search_results: list[dict]
       graph_results: list[dict]
       citation_path: list[dict]
       final_answer: str
       session_id: str
   ```

2. **T10.2** Implement LangGraph nodes:
   - `router_node` — analyzes query, decides which tools to use
   - `tool_executor_node` — invokes selected tools (via LangGraph ToolNode)
   - `synthesizer_node` — combines tool results into coherent answer with sources

3. **T10.3** Implement LangGraph graph:
   ```python
   builder = StateGraph(ResearchAgentState)
   builder.add_node("router", router_node)
   builder.add_node("tools", ToolNode(tools))
   builder.add_node("synthesizer", synthesizer_node)
   builder.add_edge(START, "router")
   builder.add_conditional_edges("router", route_decision)
   builder.add_edge("tools", "synthesizer")
   builder.add_edge("synthesizer", END)
   ```

4. **T10.4** Implement streaming support — yield intermediate results as agent progresses

**TDD — Tests to write FIRST:**
```python
# tests/unit/test_state.py
def test_agent_state_initializes():
    """ResearchAgentState should initialize with required fields."""

def test_agent_state_accumulates_messages():
    """Messages should be appended via add_messages reducer."""

# tests/unit/test_workflow.py
@pytest.mark.asyncio
async def test_router_selects_vector_search_for_similarity_query(mock_llm):
    """Router should select VectorSearchTool for 'find papers about X' queries."""

@pytest.mark.asyncio
async def test_router_selects_graph_query_for_citation_query(mock_llm):
    """Router should select GraphQueryTool for 'who cites paper X' queries."""

@pytest.mark.asyncio
async def test_router_selects_citation_path_for_connection_query(mock_llm):
    """Router should select CitationPathTool for 'how are X and Y connected'."""

@pytest.mark.asyncio
async def test_synthesizer_includes_sources(mock_llm):
    """Synthesizer should include source papers in the final answer."""

@pytest.mark.asyncio
async def test_workflow_end_to_end(mock_llm, mock_tools):
    """Full workflow should process query through router → tools → synthesizer."""

@pytest.mark.asyncio
async def test_workflow_handles_no_results(mock_llm, mock_tools):
    """Workflow should gracefully handle empty tool results."""
```

---

### T11 — Persistent Sessions (SurrealSaver Checkpointer)

**Goal:** Enable persistent agent state across sessions using `langgraph-checkpoint-surrealdb`.

**Key file:** `backend/app/agent/sessions.py`

**Sub-tasks:**

1. **T11.1** Initialize `SurrealSaver` checkpointer:
   ```python
   from langgraph.checkpoint.surrealdb import SurrealSaver
   
   memory = SurrealSaver(
       url=settings.SURREALDB_URL,
       user=settings.SURREALDB_USER,
       password=settings.SURREALDB_PASSWORD,
       namespace=settings.SURREALDB_NAMESPACE,
       database=settings.SURREALDB_DATABASE,
   )
   graph = builder.compile(checkpointer=memory)
   ```

2. **T11.2** Implement session management:
   - `create_session(user_id) -> session_id`
   - `get_session(session_id) -> SessionData`
   - `list_sessions(user_id) -> list[SessionSummary]`
   - Session data stored in `session` table (queries, papers explored, notes)

3. **T11.3** Wire session_id into LangGraph config:
   ```python
   config = {"configurable": {"thread_id": session_id}}
   result = await graph.ainvoke(state, config=config)
   ```

4. **T11.4** Implement session resumption — when user returns, load previous context

**TDD — Tests to write FIRST:**
```python
# tests/unit/test_sessions.py
@pytest.mark.asyncio
async def test_create_session_returns_id():
    """create_session should return a unique session ID."""

@pytest.mark.asyncio
async def test_get_session_returns_data(mock_db):
    """get_session should return session data for a valid ID."""

@pytest.mark.asyncio
async def test_get_session_raises_for_invalid_id(mock_db):
    """get_session should raise NotFoundError for invalid session."""

# tests/integration/test_sessions_integration.py
@pytest.mark.asyncio
async def test_agent_state_persists_across_invocations(db_manager):
    """Agent should remember previous messages when called with same session_id."""

@pytest.mark.asyncio
async def test_agent_state_isolated_between_sessions(db_manager):
    """Different session_ids should have independent state."""

@pytest.mark.asyncio
async def test_session_stores_explored_papers(db_manager):
    """Session should track which papers the user has explored."""
```

---

### T12 — Integration Tests: Ingestion Pipeline

**Goal:** Validate the full ingestion pipeline against a real SurrealDB instance.

**Key file:** `backend/tests/integration/test_pipeline.py`

**Test scenarios:**

```python
@pytest.mark.integration
class TestIngestionPipelineIntegration:

    async def test_ingest_pdf_creates_complete_graph(self, db, sample_pdf):
        """Ingest PDF → verify paper node, author nodes, topic nodes,
        edges (authored_by, belongs_to), and vector chunks all exist."""

    async def test_ingest_arxiv_paper_creates_graph(self, db, mock_arxiv):
        """Ingest arXiv paper → verify all graph entities are created."""

    async def test_ingest_two_papers_with_shared_author(self, db):
        """Two papers by same author → author node exists once,
        two authored_by edges point to it."""

    async def test_ingest_paper_with_citations(self, db):
        """Paper citing another → cites edge is created."""

    async def test_ingested_chunks_are_searchable(self, db):
        """After ingestion, vector similarity search returns the paper's chunks."""

    async def test_graph_traversal_after_ingestion(self, db):
        """After ingestion, graph query paper->authored_by->author works."""
```

**Fixture requirements:**
- Docker SurrealDB (via `pytest-docker` or manual `docker-compose up`)
- Fresh database namespace per test (isolation)
- Small test PDF fixture in `tests/fixtures/`

---

### T13 — FastAPI Backend

**Goal:** Expose all functionality through REST API endpoints.

**Key files:** `backend/app/api/routes_*.py`, `backend/app/main.py`

**Endpoints:**

| Method | Path | Description | Request | Response |
|---|---|---|---|---|
| POST | `/api/ingest/pdf` | Upload and ingest PDF | multipart file | `{paper_id, status, nodes_created, edges_created}` |
| POST | `/api/ingest/arxiv` | Ingest by arXiv ID | `{arxiv_id}` | `{paper_id, status, ...}` |
| POST | `/api/ingest/semantic-scholar` | Ingest by SS ID | `{paper_id}` | `{paper_id, status, ...}` |
| POST | `/api/search` | Vector similarity search | `{query, top_k}` | `{papers: [{title, abstract, score}]}` |
| POST | `/api/ask` | Ask research agent | `{question, session_id?}` | `{answer, sources, graph_paths, session_id}` |
| GET | `/api/citation-path` | Find citation path | `?paper_a=...&paper_b=...` | `{path: [{paper}]}` |
| GET | `/api/graph/paper/{id}` | Get paper with relations | — | `{paper, authors, topics, citations}` |
| GET | `/api/graph/stats` | Get graph statistics | — | `{papers, authors, topics, edges}` |
| POST | `/api/sessions` | Create session | `{user_id}` | `{session_id}` |
| GET | `/api/sessions/{id}` | Get session | — | `{session data}` |
| GET | `/api/sessions` | List sessions | `?user_id=...` | `{sessions: [...]}` |
| GET | `/api/health` | Health check | — | `{status, db_connected}` |

**Sub-tasks:**

1. **T13.1** Implement request/response Pydantic models in `schemas.py`
2. **T13.2** Implement each route file
3. **T13.3** Wire up FastAPI app with CORS, lifespan, error handlers
4. **T13.4** Implement streaming response for `/api/ask` (SSE)

**TDD — Tests to write FIRST:**
```python
# tests/unit/test_schemas.py
def test_ask_request_validates():
    """AskRequest should require 'question' field."""

def test_ask_response_includes_sources():
    """AskResponse should include sources list."""

def test_ingest_pdf_request_accepts_file():
    """IngestPDFRequest should accept file upload."""

# tests/integration/test_api.py
@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    """GET /api/health should return 200 with db status."""

@pytest.mark.asyncio
async def test_search_endpoint(async_client, seeded_db):
    """POST /api/search should return relevant papers."""

@pytest.mark.asyncio
async def test_ask_endpoint(async_client, seeded_db):
    """POST /api/ask should return answer with sources."""

@pytest.mark.asyncio
async def test_ask_endpoint_creates_session(async_client, seeded_db):
    """POST /api/ask without session_id should create a new session."""

@pytest.mark.asyncio
async def test_ask_endpoint_resumes_session(async_client, seeded_db):
    """POST /api/ask with session_id should load previous context."""

@pytest.mark.asyncio
async def test_ingest_pdf_endpoint(async_client):
    """POST /api/ingest/pdf should ingest paper and return paper_id."""

@pytest.mark.asyncio
async def test_graph_stats_endpoint(async_client, seeded_db):
    """GET /api/graph/stats should return counts."""

@pytest.mark.asyncio
async def test_citation_path_endpoint(async_client, seeded_db):
    """GET /api/citation-path should return path between papers."""

@pytest.mark.asyncio
async def test_session_crud(async_client):
    """Session create → get → list should work."""
```

**Fixture:** `async_client` — `httpx.AsyncClient` with `app=fastapi_app`

---

### T14 — Integration Tests: Agent Workflow

**Goal:** Validate the agent end-to-end with real SurrealDB and mocked LLM.

**Key file:** `backend/tests/integration/test_agent.py`

```python
@pytest.mark.integration
class TestAgentIntegration:

    async def test_agent_answers_paper_discovery_query(self, agent, seeded_db):
        """'Find papers about transformers' → returns paper list with sources."""

    async def test_agent_answers_citation_query(self, agent, seeded_db):
        """'What papers cite Attention Is All You Need?' → returns citing papers."""

    async def test_agent_answers_author_query(self, agent, seeded_db):
        """'What has Vaswani published?' → returns author's papers."""

    async def test_agent_answers_connection_query(self, agent, seeded_db):
        """'How are paper A and paper B connected?' → returns citation path."""

    async def test_agent_persists_state(self, agent, seeded_db):
        """Two queries in same session → second query references first context."""

    async def test_agent_uses_multiple_tools(self, agent, seeded_db):
        """Complex query → agent uses both vector search and graph traversal."""

    async def test_agent_handles_unknown_topic(self, agent, seeded_db):
        """Query about topic not in DB → agent responds gracefully."""
```

---

### T15 — Integration Tests: API Layer

**Goal:** Full API integration tests with real DB, mocked LLM.

(Covered in T13 test list above, but here with real DB instead of mocks)

```python
@pytest.mark.integration
class TestAPIIntegration:

    async def test_ingest_then_search(self, client, db):
        """Ingest a paper via API, then search for it via API."""

    async def test_ingest_then_ask(self, client, db):
        """Ingest a paper via API, then ask a question about it."""

    async def test_session_persistence_via_api(self, client, db):
        """Create session, ask question, ask follow-up — context preserved."""

    async def test_graph_endpoint_after_ingestion(self, client, db):
        """After ingestion, graph endpoint returns paper with relations."""

    async def test_concurrent_ingestion(self, client, db):
        """Multiple simultaneous ingestion requests should not conflict."""
```

---

### T16 — Next.js Frontend

**Goal:** Build a modern, clean research assistant UI.

**Key files:** `frontend/src/app/`

**Pages/Components:**

1. **T16.1** Layout & Theme Setup
   - Dark/light mode support
   - Responsive sidebar + main content layout
   - Tailwind CSS configuration

2. **T16.2** Chat Interface (`/`)
   - Message input with send button
   - Message history display (user + assistant messages)
   - Source citations displayed inline with links
   - Streaming response display
   - Session selector dropdown (resume previous sessions)

3. **T16.3** Paper List Panel
   - Sidebar showing ingested papers
   - Search/filter within ingested papers
   - Click to view paper details

4. **T16.4** Graph Visualization
   - Interactive citation/author graph using `react-force-graph` or `d3`
   - Nodes: papers (blue), authors (green), topics (orange)
   - Edges: cites (solid), authored_by (dashed)
   - Click node to see details
   - Zoom, pan, hover labels

5. **T16.5** Ingestion Interface
   - PDF upload drag-and-drop
   - arXiv ID input field
   - Ingestion progress indicator
   - Success/error feedback

6. **T16.6** API Client
   - Typed fetch wrappers for all backend endpoints
   - Error handling
   - SSE streaming for `/api/ask`

**Frontend Testing (lightweight for hackathon):**
```typescript
// __tests__/api-client.test.ts
test('search endpoint returns papers', async () => { ... });
test('ask endpoint streams response', async () => { ... });

// __tests__/components/ChatMessage.test.tsx
test('renders user message', () => { ... });
test('renders assistant message with sources', () => { ... });
```

---

### T17 — End-to-End Tests

**Goal:** Validate the complete system from frontend to database.

**Key file:** `backend/tests/e2e/test_full_flow.py`

**Test scenarios (against running full stack):**

```python
@pytest.mark.e2e
class TestEndToEnd:

    async def test_full_research_flow(self, running_app):
        """
        1. Ingest a test PDF via /api/ingest/pdf
        2. Verify paper appears in /api/graph/stats
        3. Ask a question via /api/ask
        4. Verify answer contains paper reference
        5. Check session was created
        6. Ask follow-up question with same session_id
        7. Verify follow-up uses previous context
        """

    async def test_citation_discovery_flow(self, running_app, two_papers_ingested):
        """
        1. Ingest paper A (cites paper B)
        2. Ingest paper B
        3. Query citation path between A and B
        4. Verify path is found
        """

    async def test_multi_paper_topic_exploration(self, running_app):
        """
        1. Ingest 3 papers on related topics
        2. Ask 'What are the key themes across these papers?'
        3. Verify answer references multiple papers
        """

    async def test_graph_visualization_data(self, running_app, seeded_db):
        """
        1. Ingest papers
        2. GET /api/graph/paper/{id}
        3. Verify response has nodes and edges suitable for visualization
        """
```

---

### T18 — LangSmith Observability

**Goal:** Instrument the agent and pipeline with LangSmith tracing.

**Sub-tasks:**

1. **T18.1** Configure LangSmith environment variables:
   ```
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=<key>
   LANGCHAIN_PROJECT=researchgraph-assistant
   ```

2. **T18.2** Verify traces appear for:
   - Agent workflow executions
   - Tool invocations (each tool call is a span)
   - LLM calls (entity extraction, summarization, routing)
   - Ingestion pipeline steps

3. **T18.3** Add custom metadata to traces:
   - Session ID
   - Paper IDs involved
   - Query type (discovery, citation, author, etc.)

**TDD:**
```python
# tests/unit/test_observability.py
def test_langsmith_env_vars_configured(settings):
    """LangSmith environment variables should be set."""

def test_agent_workflow_generates_trace(mock_langsmith):
    """Agent invocation should produce a LangSmith trace."""
```

---

## 5. Testing Strategy

### Testing Pyramid

```
          ┌─────────────┐
          │   E2E Tests  │   (T17) — 5 tests
          │  Full stack  │   Slow, run manually / CI
          └──────┬──────┘
                 │
        ┌────────┴────────┐
        │Integration Tests│  (T12, T14, T15) — 25 tests
        │ Real DB, mock   │  Medium speed, require Docker
        │ LLM             │
        └────────┬────────┘
                 │
    ┌────────────┴────────────┐
    │      Unit Tests          │  (in every T*) — 50+ tests
    │  Pure logic, all mocked  │  Fast, no external deps
    └─────────────────────────┘
```

### Test Configuration

**`conftest.py` fixtures:**

```python
# Shared fixtures

@pytest.fixture
def mock_llm():
    """Mock ChatOpenAI that returns predetermined responses."""

@pytest.fixture
def mock_embeddings():
    """Mock OpenAIEmbeddings that returns random 1536-dim vectors."""

@pytest.fixture
async def db_manager():
    """Real SurrealDB connection for integration tests.
    Creates a fresh namespace per test, tears down after."""

@pytest.fixture
async def seeded_db(db_manager):
    """DB pre-populated with 5 test papers, authors, topics, citations."""

@pytest.fixture
async def async_client(db_manager):
    """httpx.AsyncClient bound to FastAPI test app."""

@pytest.fixture
def sample_pdf_path():
    """Path to tests/fixtures/sample_paper.pdf"""

@pytest.fixture
def sample_entities():
    """Pre-built ExtractedEntities for testing graph construction."""
```

### Test Markers

```ini
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests (no external deps)",
    "integration: Integration tests (requires SurrealDB)",
    "e2e: End-to-end tests (requires full stack)",
]
```

### Running Tests

```bash
# Unit tests only (fast, no Docker needed)
make test-unit      # pytest -m unit

# Integration tests (requires SurrealDB running)
make test-integration  # pytest -m integration

# E2E tests (requires full stack)
make test-e2e       # pytest -m e2e

# All tests
make test           # pytest
```

---

## 6. Hackathon Timeline

### Day 1 — Foundation & Data Layer (12 hours)

| Time | Task | Notes |
|---|---|---|
| 0:00–1:30 | **T01** Project Scaffold | Write tests first, then scaffold |
| 1:30–3:00 | **T02** SurrealDB Connection | Docker up, connection tests green |
| 3:00–5:00 | **T03** Schema Definition | Schema applied, creation tests green |
| 5:00–8:00 | **T04** Document Loaders | PDF + arXiv loaders with tests |
| 5:00–7:30 | **T05** Entity Extraction (parallel) | Mock LLM tests green first |
| 7:30–8:00 | **T07** Embedding Module (parallel) | Wraps OpenAI, tests with mocks |
| 8:00–10:30 | **T06** Graph Construction | Node/edge builders with tests |
| 10:30–12:00 | **T08** Ingestion Pipeline | Wire it all together, integration tests |

### Day 2 — Agent & API (12 hours)

| Time | Task | Notes |
|---|---|---|
| 0:00–3:00 | **T09** Agent Tools | 5 tools, each with unit tests |
| 3:00–6:00 | **T10** LangGraph Workflow | State machine, routing tests |
| 6:00–8:00 | **T11** Persistent Sessions | SurrealSaver integration |
| 6:00–7:00 | **T18** LangSmith Observability (parallel) | Env config, verify traces |
| 8:00–10:30 | **T13** FastAPI Backend | All endpoints, API tests |
| 10:30–12:00 | **T12, T14, T15** Integration Tests | Pipeline + agent + API |

### Day 3 — Frontend & Polish (if time permits, or compressed into Day 2)

| Time | Task | Notes |
|---|---|---|
| 0:00–4:00 | **T16** Next.js Frontend | Chat UI, graph viz, ingestion |
| 4:00–6:00 | **T17** E2E Tests | Full flow validation |
| 6:00–8:00 | Polish, Demo Prep | Seed demo data, rehearse demo |

---

## Appendix A — Key SurrealQL Queries for Agent Tools

### Vector Similarity Search
```sql
SELECT *, vector::similarity::cosine(embedding, $query_embedding) AS score
FROM chunk
WHERE embedding <|5|> $query_embedding
ORDER BY score DESC;
```

### Citation Chain (2-hop)
```sql
SELECT
    ->cites->paper.title AS cited_papers,
    ->cites->paper->cites->paper.title AS second_hop
FROM paper
WHERE title = $paper_title;
```

### Author's Papers
```sql
SELECT <-authored_by<-paper AS papers
FROM author
WHERE name = $author_name
FETCH papers;
```

### Papers by Topic
```sql
SELECT <-belongs_to<-paper AS papers
FROM topic
WHERE name = $topic_name
FETCH papers;
```

### Citation Path (shortest path)
```sql
-- Find papers that cite paper_b starting from paper_a (up to 4 hops)
SELECT ->cites->paper WHERE id = $paper_b FROM $paper_a;
```

### Graph Statistics
```sql
SELECT
    (SELECT count() FROM paper GROUP ALL).count AS papers,
    (SELECT count() FROM author GROUP ALL).count AS authors,
    (SELECT count() FROM topic GROUP ALL).count AS topics,
    (SELECT count() FROM cites GROUP ALL).count AS citations;
```

---

## Appendix B — Open Source Contribution Checklist

Per the [LangChain integration guide](https://docs.langchain.com/oss/python/contributing/integrations-langchain), the encouraged components for contribution are:

- [x] **Retrievers** — `SurrealDBCitationRetriever` (graph-based citation chain retrieval)
- [x] **Tools** — `CitationPathTool`, `GraphQueryTool`

### `SurrealDBCitationRetriever`
- Implements `langchain_core.retrievers.BaseRetriever`
- `_get_relevant_documents(query)` → performs hybrid vector + graph retrieval
- Configurable: max hops, similarity threshold, result limit
- Published as part of `langchain-surrealdb` or standalone package

### `SurrealDBPaperLoader`
- While document loaders are not encouraged for contribution to LangChain core, this can be published as a standalone open-source package
- Handles PDF, arXiv, Semantic Scholar sources
- Returns LangChain `Document` objects

---

## Appendix C — Environment Variables

```bash
# .env.example

# SurrealDB
SURREALDB_URL=ws://localhost:8000/rpc
SURREALDB_USER=root
SURREALDB_PASSWORD=root
SURREALDB_NAMESPACE=researchgraph
SURREALDB_DATABASE=main

# OpenAI
OPENAI_API_KEY=sk-...

# LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls-...
LANGCHAIN_PROJECT=researchgraph-assistant

# App
APP_ENV=development
LOG_LEVEL=INFO
```

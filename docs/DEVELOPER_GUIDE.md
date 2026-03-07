# ResearchGraph Assistant Developer Guide

**Last Updated:** March 7, 2026  
**Version:** 0.1.0

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Running Tests](#running-tests)
- [Debugging](#debugging)
- [Code Structure and Conventions](#code-structure-and-conventions)
- [Key Components](#key-components)
- [Database Schema](#database-schema)
- [Agent Workflow](#agent-workflow)
- [Adding New Features](#adding-new-features)

---

## Architecture Overview

ResearchGraph Assistant is built as a full-stack application with the following architecture:

```
┌─────────────────┐
│  Next.js UI     │  Port 3000
│  (Frontend)     │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐
│  FastAPI         │  Port 8001
│  (Backend)       │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌─────────┐ ┌──────────────┐
│SurrealDB│ │ LangGraph     │
│Port 8000│ │ Agent         │
└─────────┘ └───────┬───────┘
                    │
                    ▼
            ┌──────────────┐
            │ OpenAI API   │
            │ (LLM +       │
            │  Embeddings) │
            └──────────────┘
```

### Technology Stack

**Frontend:**
- Next.js 14 (React framework)
- TypeScript
- Tailwind CSS
- React Flow (graph visualization)

**Backend:**
- FastAPI (Python async web framework)
- LangChain/LangGraph (agent framework)
- SurrealDB (graph + vector + document database)
- OpenAI API (GPT-4o-mini for LLM, text-embedding-3-small for embeddings)

**Infrastructure:**
- Rancher Desktop (container runtime)
- Docker Compose (SurrealDB)
- LangSmith (observability)

---

## Project Structure

```
ResearchGraph/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Configuration (env vars)
│   │   ├── dependencies.py     # FastAPI dependencies
│   │   ├── observability.py    # LangSmith setup
│   │   │
│   │   ├── db/                 # Database layer
│   │   │   ├── connection.py   # SurrealDB connection manager
│   │   │   ├── manager.py      # Module-level db manager
│   │   │   └── schema.py       # Schema definitions
│   │   │
│   │   ├── ingestion/          # Paper ingestion pipeline
│   │   │   ├── loaders.py      # PDF, arXiv, Semantic Scholar loaders
│   │   │   ├── extractors.py   # LLM-based entity extraction
│   │   │   ├── embeddings.py   # Vector store service
│   │   │   ├── graph_builder.py # Graph construction
│   │   │   └── pipeline.py     # Main ingestion pipeline
│   │   │
│   │   ├── agent/              # LangGraph agent
│   │   │   ├── state.py        # Agent state definition
│   │   │   ├── tools.py        # Agent tools (search, graph, citation)
│   │   │   ├── workflow.py     # LangGraph state machine
│   │   │   └── sessions.py     # Session management
│   │   │
│   │   ├── api/                # FastAPI routes
│   │   │   ├── routes_ingest.py
│   │   │   ├── routes_search.py
│   │   │   ├── routes_ask.py
│   │   │   ├── routes_sessions.py
│   │   │   ├── routes_graph.py
│   │   │   └── routes_citation.py
│   │   │
│   │   └── models/             # Pydantic schemas
│   │       ├── schemas.py      # Request/response models
│   │       └── domain.py       # Domain models
│   │
│   ├── tests/
│   │   ├── unit/               # Unit tests (no external deps)
│   │   ├── integration/       # Integration tests (SurrealDB)
│   │   ├── e2e/               # End-to-end tests (full stack)
│   │   └── fixtures/          # Test data (PDFs, etc.)
│   │
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example          # Environment template
│   └── .env                  # Environment variables (gitignored)
│
├── frontend/
│   ├── src/
│   │   ├── app/               # Next.js app directory
│   │   │   ├── page.tsx       # Main page
│   │   │   ├── layout.tsx     # Root layout
│   │   │   └── components/   # React components
│   │   └── lib/               # Utilities
│   │       └── api.ts         # API client
│   ├── package.json
│   └── .env.local            # Frontend env vars
│
├── docs/                      # Documentation
│   ├── API.md                # API documentation
│   ├── DEVELOPER_GUIDE.md    # This file
│   └── E2E_TEST_REPORT.md    # Test results
│
├── scripts/                   # Utility scripts
│   ├── start-services.sh     # Start all services
│   └── run-e2e-complete.sh  # E2E test runner
│
├── docker-compose.yml        # SurrealDB service
├── Makefile                  # Common commands
├── README.md                 # Project README
└── PRD.md                    # Product requirements
```

---

## Development Workflow

### Initial Setup

1. **Clone and navigate:**
   ```bash
   cd ResearchGraph
   ```

2. **Backend setup:**
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env and add OPENAI_API_KEY
   ```

3. **Frontend setup:**
   ```bash
   cd frontend
   npm install
   ```

4. **Start SurrealDB:**
   ```bash
   make db-up
   ```

### Daily Development

1. **Start services:**
   ```bash
   # Terminal 1: Backend
   cd backend
   source .venv/bin/activate
   make dev

   # Terminal 2: Frontend
   cd frontend
   npm run dev

   # Terminal 3: SurrealDB (if not already running)
   make db-up
   ```

2. **Make changes:**
   - Backend: Edit Python files in `backend/app/`
   - Frontend: Edit TypeScript/React files in `frontend/src/`
   - Both auto-reload on file changes

3. **Run tests:**
   ```bash
   # Unit tests (fast)
   make test-unit

   # Integration tests (requires SurrealDB)
   make test-integration

   # E2E tests (requires all services)
   make test-e2e
   ```

4. **Format and lint:**
   ```bash
   make format
   make lint
   ```

### Git Workflow

1. **Create feature branch:**
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes and commit:**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

3. **Run tests before pushing:**
   ```bash
   make test
   make lint
   ```

4. **Push and create PR:**
   ```bash
   git push origin feature/my-feature
   ```

---

## Running Tests

### Test Structure

Tests are organized by type:

- **Unit tests** (`tests/unit/`): Fast, isolated, no external dependencies
- **Integration tests** (`tests/integration/`): Test with SurrealDB, require database
- **E2E tests** (`tests/e2e/`): Full stack tests, require all services

### Running Tests

**All tests:**
```bash
cd backend
source .venv/bin/activate
make test
```

**Unit tests only:**
```bash
make test-unit
# Or: pytest -m unit
```

**Integration tests:**
```bash
# Ensure SurrealDB is running
make db-up
make test-integration
# Or: pytest -m integration
```

**E2E tests:**
```bash
# Ensure all services are running
make db-up
# Terminal 1: make dev
# Terminal 2: cd frontend && npm run dev
# Terminal 3:
make test-e2e
# Or: pytest -m e2e -v
```

**Specific test file:**
```bash
pytest tests/unit/test_tools.py -v
```

**Specific test:**
```bash
pytest tests/unit/test_tools.py::test_vector_search_tool -v
```

### Writing Tests

**Unit test example:**
```python
# tests/unit/test_tools.py
import pytest
from app.agent.tools import VectorSearchTool

@pytest.mark.unit
def test_vector_search_tool_creation():
    tool = VectorSearchTool(db_manager=None)
    assert tool.name == "vector_search"
```

**Integration test example:**
```python
# tests/integration/test_vector_store.py
import pytest
from app.ingestion.embeddings import VectorStoreService

@pytest.mark.integration
async def test_similarity_search(db_manager):
    vector_store = VectorStoreService(db_manager=db_manager)
    results = await vector_store.similarity_search("transformers", k=5)
    assert len(results) > 0
```

**E2E test example:**
```python
# tests/e2e/test_api_smoke.py
import pytest
import httpx

@pytest.mark.e2e
async def test_health_endpoint():
    async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
```

---

## Debugging

### Backend Debugging

**1. Enable debug logging:**
```python
# backend/app/main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**2. Use Python debugger:**
```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use breakpoint() in Python 3.7+
breakpoint()
```

**3. Check logs:**
```bash
# If running with nohup
tail -f /tmp/backend.log

# Or check console output
```

**4. Test API endpoints directly:**
```bash
# Health check
curl http://localhost:8001/api/health

# Search
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "transformers", "top_k": 5}'
```

**5. Inspect SurrealDB:**
```bash
# Connect to SurrealDB
nerdctl exec -it researchgraph-db surrealdb sql --conn http://localhost:8000 --user root --pass root --ns research --db research

# Query papers
SELECT * FROM paper LIMIT 10;

# Check schema
INFO FOR DB;
```

### Frontend Debugging

**1. Browser DevTools:**
- Open Chrome DevTools (F12)
- Check Console for errors
- Check Network tab for API calls
- Use React DevTools extension

**2. Check API calls:**
```typescript
// frontend/src/lib/api.ts
console.log('API call:', url, data);
```

**3. Test API directly:**
```bash
# Test backend from frontend's perspective
curl http://localhost:8001/api/health
```

### Common Debugging Scenarios

**Problem: Backend won't start**
```bash
# Check SurrealDB connection
curl http://localhost:8000/health

# Check environment variables
cd backend
cat .env | grep OPENAI_API_KEY

# Check port availability
lsof -i :8001
```

**Problem: Agent returns errors**
```bash
# Check checkpoint data
# Connect to SurrealDB and run:
SELECT * FROM checkpoint LIMIT 5;

# Clear checkpoint if needed
DELETE checkpoint WHERE true;
DELETE checkpoint_blob WHERE true;
```

**Problem: Search returns no results**
```bash
# Check if papers exist
curl http://localhost:8001/api/graph/stats

# Check vector index
# In SurrealDB:
INFO FOR DB;
# Should show chunk_embedding_idx
```

**Problem: Frontend can't connect to backend**
```bash
# Check CORS settings
# Check NEXT_PUBLIC_API_URL in frontend/.env.local
cat frontend/.env.local

# Test backend directly
curl http://localhost:8001/api/health
```

---

## Code Structure and Conventions

### Python (Backend)

**Style:**
- Follow PEP 8
- Use type hints
- Use async/await for I/O operations
- Use Pydantic models for validation

**Naming:**
- Classes: `PascalCase` (e.g., `VectorStoreService`)
- Functions: `snake_case` (e.g., `similarity_search`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `SCHEMA_STATEMENTS`)

**File organization:**
- One class/function per logical unit
- Group related functionality in modules
- Keep files focused (< 500 lines)

**Example:**
```python
from typing import List, Optional
from pydantic import BaseModel
from app.db.connection import SurrealDBManager

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

async def search_papers(
    query: str,
    top_k: int = 5,
    db_manager: Optional[SurrealDBManager] = None
) -> List[dict]:
    """Search papers by vector similarity."""
    # Implementation
    pass
```

### TypeScript (Frontend)

**Style:**
- Use TypeScript strict mode
- Use functional components
- Use hooks for state management
- Follow React best practices

**Naming:**
- Components: `PascalCase` (e.g., `PaperList`)
- Functions: `camelCase` (e.g., `fetchPapers`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `API_BASE_URL`)

**Example:**
```typescript
interface Paper {
  id: string;
  title: string;
  abstract: string;
}

async function fetchPapers(query: string): Promise<Paper[]> {
  const response = await fetch(`${API_BASE_URL}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: 5 }),
  });
  return response.json();
}
```

---

## Key Components

### Database Layer (`app/db/`)

**Connection Manager:**
- `connection.py`: SurrealDB connection and query execution
- `manager.py`: Module-level singleton for dependency injection
- `schema.py`: Schema definitions and initialization

**Key functions:**
```python
from app.db.connection import SurrealDBManager

db = SurrealDBManager(...)
await db.connect()
results = await db.execute("SELECT * FROM paper LIMIT 10")
```

### Ingestion Pipeline (`app/ingestion/`)

**Flow:**
1. Load paper (PDF/arXiv/Semantic Scholar)
2. Extract text and metadata
3. Extract entities using LLM (authors, topics, citations)
4. Generate embeddings
5. Build graph (nodes and edges)
6. Store in SurrealDB

**Key classes:**
- `IngestionPipeline`: Main pipeline orchestrator
- `VectorStoreService`: Vector similarity search
- `GraphBuilder`: Graph construction

### Agent (`app/agent/`)

**LangGraph State Machine:**
- `state.py`: State definition
- `workflow.py`: Graph definition (router → tools → synthesizer)
- `tools.py`: Agent tools (vector_search, graph_query, citation_path)
- `sessions.py`: Session management with checkpointing

**Workflow:**
1. User asks question
2. Router analyzes query
3. Tools execute (search, graph query, etc.)
4. Synthesizer combines results
5. Return answer with sources

### API Routes (`app/api/`)

**Structure:**
- One file per resource group
- FastAPI routers with dependency injection
- Pydantic models for request/response validation

**Example:**
```python
from fastapi import APIRouter, Depends
from app.dependencies import get_db
from app.models.schemas import SearchRequest, SearchResponse

router = APIRouter(prefix="/api", tags=["search"])

@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    db: SurrealDBManager = Depends(get_db),
):
    # Implementation
    pass
```

---

## Database Schema

### Tables

**`paper`**: Research papers
- Fields: `title`, `abstract`, `year`, `venue`, `doi`, `arxiv_id`, `source`
- Relations: `->wrote->author`, `->cites->paper`, `->has_topic->topic`

**`author`**: Paper authors
- Fields: `name`, `institution`
- Relations: `->wrote<-paper`, `->affiliated_with->institution`

**`topic`**: Research topics
- Fields: `name`
- Relations: `->has_topic<-paper`

**`chunk`**: Text chunks for vector search
- Fields: `content`, `index`, `embedding`, `metadata`
- Relations: `->has_chunk<-paper`
- Index: `chunk_embedding_idx` (HNSW vector index)

**`session`**: Agent sessions
- Fields: `user_id`, `created_at`, `updated_at`, `queries`, `papers_explored`, `notes`

### Indexes

- **Vector index**: `chunk_embedding_idx` (HNSW, 1536 dimensions, cosine distance)
- **Full-text indexes**: `paper_title_idx`, `paper_abstract_idx` (BM25)

### Schema Initialization

Schema is automatically applied on backend startup via `app/db/schema.py`.

---

## Agent Workflow

### LangGraph State Machine

**Nodes:**
1. **Router**: Analyzes query and decides which tools to use
2. **Tools**: Executes selected tools (vector_search, graph_query, citation_path)
3. **Synthesizer**: Combines tool results into final answer

**State:**
```python
{
    "messages": List[BaseMessage],
    "query": str,
    "final_answer": str,
    "search_results": List[dict],
    "graph_results": List[dict],
    "citation_path": List[dict],
}
```

### Tools

**1. Vector Search Tool:**
- Finds papers by semantic similarity
- Uses OpenAI embeddings + SurrealDB vector index
- Returns: List of papers with relevance scores

**2. Graph Query Tool:**
- Queries graph relationships
- Examples: "who cites paper X", "what papers did author Y write"
- Returns: Graph query results

**3. Citation Path Tool:**
- Finds citation paths between papers
- Uses graph traversal
- Returns: List of papers in path

### Session Management

Sessions use LangGraph checkpointing with SurrealDB:
- State persisted across queries
- Context maintained in conversation
- Resumable sessions

---

## Adding New Features

### Adding a New API Endpoint

1. **Create route file** (if new resource group):
   ```python
   # app/api/routes_new.py
   from fastapi import APIRouter
   router = APIRouter(prefix="/api/new", tags=["new"])
   ```

2. **Add to main.py:**
   ```python
   from app.api import routes_new
   app.include_router(routes_new.router)
   ```

3. **Define schemas:**
   ```python
   # app/models/schemas.py
   class NewRequest(BaseModel):
       field: str
   ```

4. **Implement endpoint:**
   ```python
   @router.post("/endpoint", response_model=NewResponse)
   async def new_endpoint(request: NewRequest, db=Depends(get_db)):
       # Implementation
       pass
   ```

5. **Add tests:**
   ```python
   # tests/unit/test_new.py
   @pytest.mark.unit
   def test_new_endpoint():
       # Test
       pass
   ```

### Adding a New Agent Tool

1. **Create tool class:**
   ```python
   # app/agent/tools.py
   class NewTool(BaseTool):
       name = "new_tool"
       description = "Tool description"
       
       async def _arun(self, param: str) -> dict:
           # Implementation
           pass
   ```

2. **Add to workflow:**
   ```python
   # app/agent/workflow.py
   tools = [vector_search, graph_query, citation_path, new_tool]
   ```

3. **Update router prompt:**
   ```python
   # Add tool description to router prompt
   ```

### Adding a New Database Table

1. **Define schema:**
   ```python
   # app/db/schema.py
   SCHEMA_STATEMENTS.append("DEFINE TABLE new_table SCHEMAFULL;")
   SCHEMA_STATEMENTS.append("DEFINE FIELD field ON new_table TYPE string;")
   ```

2. **Update domain models:**
   ```python
   # app/models/domain.py
   class NewTable(BaseModel):
       id: str
       field: str
   ```

3. **Test schema:**
   ```python
   # tests/integration/test_schema.py
   async def test_new_table_created(db_manager):
       # Verify table exists
       pass
   ```

---

## Best Practices

1. **Always write tests** for new features
2. **Use type hints** in Python
3. **Follow async/await** patterns for I/O
4. **Validate inputs** with Pydantic
5. **Handle errors** gracefully with proper HTTP status codes
6. **Log important events** for debugging
7. **Document complex logic** with docstrings
8. **Keep functions focused** and single-purpose
9. **Use dependency injection** for testability
10. **Run linters** before committing

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [SurrealDB Documentation](https://surrealdb.com/docs)
- [Next.js Documentation](https://nextjs.org/docs)
- [API Documentation](API.md)
- [E2E Testing Guide](../E2E_TESTING_GUIDE.md)

---

## Getting Help

- Check [README.md](../README.md) for troubleshooting
- Review [API.md](API.md) for endpoint details
- See test files for usage examples
- Check logs for error details

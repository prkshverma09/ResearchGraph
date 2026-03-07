# ResearchGraph Assistant

AI-powered research exploration platform with knowledge graphs, built for the [SurrealDB London Hackathon — Agents & Knowledge Graphs](https://www.notion.so/surrealdb/LONDON-Hackathon-Agents-Knowledge-Graphs-313bfa44ae3e80589772fb837664107b).

## Overview

ResearchGraph Assistant ingests academic papers (PDFs, arXiv, Semantic Scholar), extracts structured entities using LLMs, stores them in SurrealDB as both vector embeddings and graph nodes/edges, and enables a LangGraph-powered research agent to answer complex queries by combining semantic search, citation graph traversal, and contextual summarization.

## Architecture

```
Next.js Frontend → FastAPI Backend → LangGraph Agent → Tools → SurrealDB
```

- **Frontend**: Next.js 14 with React, TypeScript, Tailwind CSS
- **Backend**: FastAPI with async/await
- **Agent**: LangGraph state machine with tool calling
- **Database**: SurrealDB (graph + vector + document storage)
- **LLM**: OpenAI GPT-4o-mini for extraction and synthesis
- **Embeddings**: OpenAI text-embedding-3-small (1536 dimensions)
- **Observability**: LangSmith tracing

## Features

✅ **Paper Ingestion Pipeline**
- PDF upload with drag-and-drop
- arXiv paper ingestion by ID
- Semantic Scholar API integration
- Automatic entity extraction (authors, topics, citations)
- Graph construction (nodes and edges)
- Vector embedding generation and storage

✅ **Research Agent**
- Vector similarity search
- Graph traversal queries (author papers, citations, topics)
- Citation path finding
- Paper summarization
- Topic exploration

✅ **Persistent Sessions**
- Session management with SurrealSaver checkpointer
- Context preservation across queries
- Session resumption

✅ **Modern UI**
- Chat interface with streaming responses
- Interactive graph visualization
- Paper list with search
- Dark/light mode support
- Responsive design

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Rancher Desktop (for SurrealDB via nerdctl)
- OpenAI API key
- (Optional) LangSmith API key for observability

### Backend Setup

1. **Install dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Start SurrealDB**:
   ```bash
   make db-up
   # Or: nerdctl compose up -d surrealdb
   ```

4. **Run backend**:
   ```bash
   make dev
   # Or: cd backend && uvicorn app.main:app --reload
   ```

Backend will be available at `http://localhost:8001`

### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Configure API URL** (if backend is not on localhost:8001):
   ```bash
   # Create .env.local
   echo "NEXT_PUBLIC_API_URL=http://localhost:8001" > .env.local
   ```

3. **Run frontend**:
   ```bash
   npm run dev
   ```

Frontend will be available at `http://localhost:3000`

## Usage

### Ingest Papers

1. **PDF Upload**: Drag and drop a PDF file in the ingestion panel
2. **arXiv**: Enter an arXiv ID (e.g., `2401.00001`) and click "Ingest"
3. **Semantic Scholar**: Enter a Semantic Scholar paper ID

### Ask Questions

Use the chat interface to ask research questions:

- "Find papers about transformers"
- "What papers cite Attention Is All You Need?"
- "What has Vaswani published?"
- "How are paper A and paper B connected?"

The agent will:
1. Analyze your query
2. Select appropriate tools (vector search, graph query, etc.)
3. Execute tools and gather results
4. Synthesize a coherent answer with source citations

### Explore Graph

Click on papers in the graph visualization to see:
- Authors
- Topics
- Citations
- Related papers

## Testing

### Unit Tests
```bash
cd backend
make test-unit
# Or: pytest -m unit
```

### Integration Tests
```bash
# Ensure SurrealDB is running
make db-up
cd backend
make test-integration
# Or: pytest -m integration
```

### End-to-End Tests

**Prerequisites:**
1. Rancher Desktop must be running
2. SurrealDB, backend, and frontend services must be started
3. OpenAI API key configured in `backend/.env`

**Setup:**
```bash
# 1. Start SurrealDB
make db-up

# 2. Start backend (in Terminal 1)
cd backend
source .venv/bin/activate
make dev

# 3. Start frontend (in Terminal 2)
cd frontend
npm install
npm run dev

# 4. Install E2E dependencies (in Terminal 3)
cd backend
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

**Run Tests:**
```bash
cd backend
source .venv/bin/activate
make test-e2e
# Or API-only: make test-e2e-api
```

For detailed E2E testing instructions, see [E2E_TESTING_GUIDE.md](E2E_TESTING_GUIDE.md) and [docs/E2E_TEST_REPORT.md](docs/E2E_TEST_REPORT.md).

## Project Structure

```
ResearchGraph/
├── backend/
│   ├── app/
│   │   ├── db/          # SurrealDB connection and schema
│   │   ├── ingestion/   # Loaders, extractors, embeddings, graph builder, pipeline
│   │   ├── agent/       # Tools, workflow, state, sessions
│   │   ├── api/         # FastAPI routes
│   │   └── models/      # Domain models and schemas
│   └── tests/           # Unit, integration, E2E tests
├── frontend/
│   └── src/
│       ├── app/         # Next.js pages and components
│       └── lib/         # API client utilities
├── docker-compose.yml   # SurrealDB service (uses nerdctl compose)
├── Makefile            # Common commands
└── IMPLEMENTATION_PLAN.md  # Detailed implementation plan
```

## API Keys Required

### Required
- **OPENAI_API_KEY**: For LLM entity extraction, summarization, and agent reasoning
  - Get from: https://platform.openai.com/api-keys

### Optional
- **LANGCHAIN_API_KEY**: For LangSmith observability and tracing
  - Get from: https://smith.langchain.com/
  - Set `LANGCHAIN_TRACING_V2=true` in `.env` to enable

## Development

### Running Tests
```bash
# All tests
make test

# Unit tests only (fast, no Rancher Desktop needed)
make test-unit

# Integration tests (requires SurrealDB)
make test-integration

# E2E tests (requires full stack)
make test-e2e
```

### Code Formatting
```bash
make format
```

### Linting
```bash
make lint
```

## Hackathon Alignment

This project aligns with all hackathon judging criteria:

- ✅ **Structured Memory/Knowledge (30%)**: SurrealDB multi-model storage (graph + vector + document)
- ✅ **Agent Workflow Quality (20%)**: LangGraph state machine with multi-step tool coordination
- ✅ **Persistent Agent State (20%)**: SurrealSaver checkpointer for session persistence
- ✅ **Practical Use Case (20%)**: Real-world research assistant for academic literature exploration
- ✅ **Observability (10%)**: LangSmith tracing for agent execution
- ✅ **Bonus - Open Source**: Reusable LangChain components (tools, retrievers)

## Known Issues

### Issue 2: LangGraph Checkpoint Error ⚠️

**Status:** Identified as library bug  
**Impact:** Research agent `/api/ask` endpoint may fail with checkpoint errors  
**Error:** `TypeError: string indices must be integers, not 'str'` in `langgraph-checkpoint-surrealdb`

**Root Cause:**  
The `langgraph-checkpoint-surrealdb` library (v2.0.0) has a bug where it receives a string response from SurrealDB when it expects a dictionary. This is a known issue with the checkpoint adapter library.

**Workaround:**  
1. Clear checkpoint data: `DELETE checkpoint WHERE true; DELETE checkpoint_blob WHERE true;` in SurrealDB
2. Monitor for library updates: https://github.com/lfnovo/langgraph-checkpoint-surrealdb
3. Consider disabling checkpointing for testing (modify `get_checkpointer()` to return `None`)

**Tracking:**  
- Library: `langgraph-checkpoint-surrealdb>=2.0.0`
- Issue reported to library maintainer

## Troubleshooting

### Backend Won't Start

**Problem:** Backend fails to start or crashes immediately

**Solutions:**
1. **Check SurrealDB is running:**
   ```bash
   nerdctl ps | grep surrealdb
   # If not running: make db-up
   ```

2. **Verify environment variables:**
   ```bash
   cd backend
   cat .env | grep OPENAI_API_KEY
   # Ensure OPENAI_API_KEY is set
   ```

3. **Check port availability:**
   ```bash
   lsof -i :8001
   # Kill process if port is in use
   ```

4. **View backend logs:**
   ```bash
   tail -f /tmp/backend.log
   # Or check console output if running directly
   ```

### Frontend Won't Start

**Problem:** Frontend fails to start or shows connection errors

**Solutions:**
1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Check backend is running:**
   ```bash
   curl http://localhost:8001/api/health
   # Should return: {"status":"ok","db_connected":true}
   ```

3. **Verify API URL configuration:**
   ```bash
   cat frontend/.env.local
   # Should contain: NEXT_PUBLIC_API_URL=http://localhost:8001
   ```

4. **Check port availability:**
   ```bash
   lsof -i :3000
   # Kill process if port is in use
   ```

### Database Connection Issues

**Problem:** Backend cannot connect to SurrealDB

**Solutions:**
1. **Verify SurrealDB is running:**
   ```bash
   nerdctl ps | grep surrealdb
   docker logs researchgraph-db
   ```

2. **Check SurrealDB configuration:**
   ```bash
   # Verify docker-compose.yml settings match backend/.env
   cat docker-compose.yml | grep -A 5 surrealdb
   ```

3. **Restart SurrealDB:**
   ```bash
   make db-down
   make db-up
   ```

4. **Check network connectivity:**
   ```bash
   curl http://localhost:8000/health
   # SurrealDB HTTP endpoint should respond
   ```

### Search Returns No Results

**Problem:** Vector similarity search returns empty results

**Solutions:**
1. **Verify papers have been ingested:**
   ```bash
   curl http://localhost:8001/api/graph/stats
   # Check papers count > 0
   ```

2. **Check vector index exists:**
   ```bash
   # Connect to SurrealDB and verify index:
   # INFO FOR DB;
   # Should show chunk_embedding_idx with HNSW type
   ```

3. **Re-ingest papers if needed:**
   ```bash
   # Use the ingestion API or UI to add papers
   ```

### Agent Fails to Answer Questions

**Problem:** `/api/ask` endpoint returns errors or empty responses

**Solutions:**
1. **Check OpenAI API key:**
   ```bash
   cd backend
   cat .env | grep OPENAI_API_KEY
   # Verify key is valid and has credits
   ```

2. **Clear checkpoint data (if checkpoint error):**
   ```bash
   # Connect to SurrealDB and run:
   # DELETE checkpoint WHERE true;
   # DELETE checkpoint_blob WHERE true;
   ```

3. **Check backend logs for errors:**
   ```bash
   tail -f /tmp/backend.log | grep -i error
   ```

4. **Verify session creation:**
   ```bash
   curl -X POST http://localhost:8001/api/sessions \
     -H "Content-Type: application/json" \
     -d '{"user_id": "test-user"}'
   ```

### E2E Tests Fail

**Problem:** End-to-end tests fail or timeout

**Solutions:**
1. **Ensure all services are running:**
   ```bash
   # Check SurrealDB
   nerdctl ps | grep surrealdb
   
   # Check backend
   curl http://localhost:8001/api/health
   
   # Check frontend
   curl http://localhost:3000
   ```

2. **Install Playwright browsers:**
   ```bash
   cd backend
   source .venv/bin/activate
   playwright install chromium
   ```

3. **Check test fixtures exist:**
   ```bash
   ls backend/tests/fixtures/sample_paper.pdf
   ```

4. **Run tests with verbose output:**
   ```bash
   cd backend
   pytest tests/e2e/ -v --tb=short
   ```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Service not running | Start the service (db-up, make dev, etc.) |
| `OPENAI_API_KEY not found` | Missing env var | Add to `backend/.env` |
| `Port already in use` | Another process using port | Kill process or change port |
| `Checkpoint error` | Library bug | Clear checkpoint data (see Known Issues) |
| `No papers found` | No data ingested | Ingest papers via API or UI |
| `SSL certificate error` | Network/OpenAI issue | Check internet connection and API key |

## License

MIT

## Acknowledgments

Built for the SurrealDB London Hackathon using:
- [SurrealDB](https://surrealdb.com/)
- [LangChain](https://www.langchain.com/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [Next.js](https://nextjs.org/)

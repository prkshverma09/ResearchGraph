# Run E2E Tests - Complete Guide

## Prerequisites Check

✅ **Fixed Issues:**
- Circular import resolved (db_manager moved to separate module)
- Missing dependencies installed (numpy, langchain-text-splitters, python-multipart)
- SurrealDB connection fixed (using AsyncSurreal)
- Backend imports successfully

⚠️ **Required:**
- Rancher Desktop must be running
- OpenAI API key configured in `backend/.env`

## Quick Start (All-in-One)

```bash
cd /Users/paverma/PersonalProjects/ResearchGraph

# 1. Start Rancher Desktop (if not running)
# Open Rancher Desktop application

# 2. Run complete E2E test suite
./scripts/run-e2e-complete.sh
```

## Step-by-Step Manual Execution

### Step 1: Start SurrealDB
```bash
cd /Users/paverma/PersonalProjects/ResearchGraph
make db-up

# Verify:
nerdctl ps | grep surrealdb
```

### Step 2: Start Backend (Terminal 1)
```bash
cd /Users/paverma/PersonalProjects/ResearchGraph/backend
source .venv/bin/activate
make dev

# Backend runs on http://localhost:8001
# Verify: curl http://localhost:8001/api/health
```

### Step 3: Start Frontend (Terminal 2)
```bash
cd /Users/paverma/PersonalProjects/ResearchGraph/frontend
npm run dev

# Frontend runs on http://localhost:3000
```

### Step 4: Run E2E Tests (Terminal 3)
```bash
cd /Users/paverma/PersonalProjects/ResearchGraph/backend
source .venv/bin/activate

# Run all E2E tests
make test-e2e

# Or run specific test suites:
pytest tests/e2e/test_api_smoke.py -v
pytest tests/e2e/test_ingestion_flow.py -v
pytest tests/e2e/test_ask_flow.py -v
pytest tests/e2e/test_ui_flows.py -v
```

## Manual UI Testing (Once Services Running)

Open http://localhost:3000 and test:

1. **PDF Ingestion**: Upload `backend/tests/fixtures/sample_paper.pdf`
2. **arXiv Ingestion**: Enter `1706.03762` and ingest
3. **Ask Questions**: "Find papers about transformers"
4. **Graph Visualization**: Click "Show Graph" button
5. **Session Persistence**: Ask questions, refresh, verify context

## Test Data Available

- **Sample PDF**: `backend/tests/fixtures/sample_paper.pdf` (Attention Is All You Need)
- **arXiv IDs**: See `backend/tests/fixtures/E2E_TEST_DATA.md`

## Expected Results

All E2E tests should pass when:
- ✅ Rancher Desktop/SurrealDB is running
- ✅ Backend is running on :8001
- ✅ Frontend is running on :3000
- ✅ OpenAI API key has credits

## Troubleshooting

**Rancher Desktop not running:**
```bash
# Start Rancher Desktop manually
# Then: make db-up
```

**Backend fails to start:**
- Check SurrealDB: `nerdctl ps`
- Check logs: `tail -f /tmp/backend-e2e.log`
- Verify `.env` has `OPENAI_API_KEY`

**Tests fail:**
- Ensure all 3 services running
- Check backend logs
- Verify OpenAI API key has credits

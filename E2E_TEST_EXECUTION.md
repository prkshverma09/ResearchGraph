# E2E Test Execution Guide

## Current Status

✅ **Backend code fixed** - Circular import resolved, dependencies installed
✅ **OpenAI API key** - Configured in `backend/.env`
⚠️ **Rancher Desktop required** - SurrealDB needs Rancher Desktop running

## Quick Start

### 1. Start Rancher Desktop
```bash
# Open Rancher Desktop application
# Wait for it to fully start
```

### 2. Run Complete E2E Test Suite
```bash
cd /Users/paverma/PersonalProjects/ResearchGraph
./scripts/run-e2e-complete.sh
```

This script will:
- Start SurrealDB
- Start Backend (port 8001)
- Start Frontend (port 3000)
- Run all E2E tests
- Show results

## Manual Step-by-Step

### Terminal 1: Start SurrealDB
```bash
cd /Users/paverma/PersonalProjects/ResearchGraph
make db-up
```

### Terminal 2: Start Backend
```bash
cd /Users/paverma/PersonalProjects/ResearchGraph/backend
source .venv/bin/activate
make dev
```

### Terminal 3: Start Frontend
```bash
cd /Users/paverma/PersonalProjects/ResearchGraph/frontend
npm run dev
```

### Terminal 4: Run Tests
```bash
cd /Users/paverma/PersonalProjects/ResearchGraph/backend
source .venv/bin/activate

# Run all E2E tests
make test-e2e

# Or run specific test files
pytest tests/e2e/test_api_smoke.py -v
pytest tests/e2e/test_ingestion_flow.py -v
pytest tests/e2e/test_ask_flow.py -v
pytest tests/e2e/test_ui_flows.py -v
```

## UI Testing Checklist

Once all services are running, test these flows manually:

### ✅ Test 1: PDF Ingestion
1. Open http://localhost:3000
2. Click sidebar → "Ingest" tab
3. Upload `backend/tests/fixtures/sample_paper.pdf`
4. Wait for success message
5. Verify paper appears in "Papers" list

### ✅ Test 2: arXiv Ingestion  
1. In "Ingest" tab, enter: `1706.03762`
2. Click "Ingest"
3. Wait for success
4. Verify paper appears

### ✅ Test 3: Ask Questions
1. Type: "Find papers about transformers"
2. Click "Send"
3. Verify streaming response
4. Verify sources listed
5. Ask follow-up: "Which is most influential?"
6. Verify context maintained

### ✅ Test 4: Graph Visualization
1. Click "Show Graph"
2. Verify graph renders
3. Click paper node
4. Verify details appear

### ✅ Test 5: Session Persistence
1. Ask question (creates session)
2. Refresh page
3. Select session from dropdown
4. Ask another question
5. Verify context continues

## Automated Test Results

After running `make test-e2e`, you should see:
- ✅ API smoke tests pass
- ✅ Error handling tests pass
- ✅ Ingestion tests (may need papers ingested first)
- ✅ Ask flow tests (may need papers ingested first)
- ✅ UI tests (if Playwright installed)

## Troubleshooting

**Backend won't start:**
- Check SurrealDB: `nerdctl ps | grep surrealdb`
- Check logs: `tail -f /tmp/backend-e2e.log`
- Verify `.env` has `OPENAI_API_KEY`

**Frontend won't start:**
- Run `npm install` in frontend directory
- Check port 3000 is available

**Tests fail:**
- Ensure all services running
- Check backend logs for errors
- Verify OpenAI API key has credits

## Next Steps

Once Rancher Desktop is running, execute:
```bash
./scripts/run-e2e-complete.sh
```

This will run the complete E2E test suite automatically.

# E2E Testing Guide - Step by Step

## Prerequisites

1. **Rancher Desktop** must be running
2. **OpenAI API Key** set in `backend/.env`
3. **Python virtual environment** activated
4. **Node.js** installed for frontend

## Step-by-Step E2E Test Execution

### Step 1: Start Rancher Desktop

```bash
# Open Rancher Desktop application
# Wait until Rancher Desktop is fully started
```

### Step 2: Start SurrealDB

```bash
cd /Users/paverma/PersonalProjects/ResearchGraph
make db-up

# Verify it's running:
nerdctl ps | grep surrealdb
```

### Step 3: Start Backend (Terminal 1)

```bash
cd /Users/paverma/PersonalProjects/ResearchGraph/backend
source .venv/bin/activate
make dev

# Backend should start on http://localhost:8001
# Verify: curl http://localhost:8001/api/health
```

### Step 4: Start Frontend (Terminal 2)

```bash
cd /Users/paverma/PersonalProjects/ResearchGraph/frontend
npm install  # If not already done
npm run dev

# Frontend should start on http://localhost:3000
```

### Step 5: Run E2E Tests (Terminal 3)

```bash
cd /Users/paverma/PersonalProjects/ResearchGraph/backend
source .venv/bin/activate

# Run all E2E tests
make test-e2e

# Or run specific test files:
pytest tests/e2e/test_api_smoke.py -v
pytest tests/e2e/test_ingestion_flow.py -v
pytest tests/e2e/test_ask_flow.py -v
pytest tests/e2e/test_ui_flows.py -v
```

## Manual UI Testing Checklist

### Test 1: PDF Ingestion
1. Open http://localhost:3000
2. Click sidebar → "Ingest" tab
3. Upload `backend/tests/fixtures/sample_paper.pdf`
4. Wait for success message
5. Verify paper appears in "Papers" list

### Test 2: arXiv Ingestion
1. In "Ingest" tab, enter arXiv ID: `1706.03762`
2. Click "Ingest"
3. Wait for success message
4. Verify paper appears in list

### Test 3: Search/Ask Flow
1. Type in chat: "Find papers about transformers"
2. Click "Send"
3. Verify streaming response appears
4. Verify sources are listed
5. Ask follow-up: "Which paper is most influential?"
6. Verify context is maintained

### Test 4: Graph Visualization
1. Click "Show Graph" button
2. Verify graph renders
3. Click on a paper node
4. Verify node details appear

### Test 5: Session Persistence
1. Ask a question (creates session)
2. Refresh page
3. Select session from dropdown
4. Ask another question
5. Verify context continues

## Automated Test Results

Run the automated tests and check results:

```bash
cd backend
source .venv/bin/activate
pytest tests/e2e/ -v --tb=short
```

## Troubleshooting

**Backend won't start:**
- Check SurrealDB is running: `nerdctl ps`
- Check `.env` file has `OPENAI_API_KEY`
- Check logs: `tail -f /tmp/backend.log`

**Frontend won't start:**
- Run `npm install` in frontend directory
- Check port 3000 is not in use

**Tests fail:**
- Ensure all services are running
- Check backend logs for errors
- Verify OpenAI API key has credits

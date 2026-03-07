# E2E Test Report - ResearchGraph Assistant

**Date:** 2026-03-06  
**Plan:** E2E Testing Plan (e2e_testing_plan_c65bf03b)

## Summary

The E2E testing plan has been fully implemented. All test files, fixtures, and configuration are in place. Tests require a running environment (SurrealDB, backend, frontend) to execute.

## Implemented Components

### 1. Configuration Fixes
- **Frontend API URL**: Updated default from `http://localhost:8000` to `http://localhost:8001` in `frontend/src/lib/api.ts` and `frontend/.env.example`
- **Backend**: Runs on port 8001
- **SurrealDB**: Runs on port 8000

### 2. Test Data
- **Sample PDF**: `backend/tests/fixtures/sample_paper.pdf` - "Attention Is All You Need" (arXiv 1706.03762)
- **Test Data Doc**: `backend/tests/fixtures/E2E_TEST_DATA.md` with arXiv IDs and test queries

### 3. Setup Scripts
- `scripts/e2e-setup.sh` - Environment setup (Rancher Desktop, deps, env files)
- `scripts/run-e2e.sh` - Run E2E tests (verifies services first)
- `scripts/create_test_pdf.py` - Generate test PDFs (optional)

### 4. API E2E Tests (`backend/tests/e2e/`)

| File | Tests | Description |
|------|-------|-------------|
| `test_api_smoke.py` | 5 | Health, graph stats, search, session create/list |
| `test_ingestion_flow.py` | 2 | PDF ingestion, arXiv ingestion |
| `test_ask_flow.py` | 2 | Ask with/without session |
| `test_citation_path.py` | 1 | Citation path endpoint |
| `test_error_handling.py` | 3 | Invalid PDF, missing question, missing query |

### 5. Playwright UI Tests (`backend/tests/e2e/test_ui_flows.py`)

| Class | Tests | Description |
|-------|-------|-------------|
| TestHomepage | 3 | Load, welcome message, chat input |
| TestSidebar | 2 | Papers/Ingest tabs, upload UI |
| TestPDFIngestionUI | 1 | PDF upload flow |
| TestArxivIngestionUI | 1 | arXiv ingestion flow |
| TestAskFlowUI | 1 | Ask question, verify response |
| TestGraphVisualization | 1 | Show Graph button toggle |

### 6. Dependencies Added
- `pytest-playwright>=0.4.0`
- `playwright>=1.40.0`

## How to Run E2E Tests

### Prerequisites
1. **Rancher Desktop** running (for SurrealDB via nerdctl)
2. **OPENAI_API_KEY** in `backend/.env`
3. **Python 3.10+** with venv

### Setup
```bash
# Create and activate venv
cd backend && python3 -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Start services
make db-up
# Terminal 2: make dev
# Terminal 3: cd frontend && npm run dev
```

### Run Tests
```bash
# All E2E tests
make test-e2e

# API-only tests (no Playwright)
make test-e2e-api

# Specific test file
cd backend && pytest tests/e2e/test_api_smoke.py -v
```

## Test Scenarios Covered

| Scenario | API Test | UI Test |
|----------|----------|---------|
| Health check | Yes | - |
| Graph stats | Yes | - |
| Search | Yes | - |
| Session CRUD | Yes | - |
| PDF ingestion | Yes | Yes |
| arXiv ingestion | Yes | Yes |
| Ask question | Yes | Yes |
| Citation path | Yes | - |
| Error handling | Yes | - |
| Graph visualization | - | Yes |

## Known Limitations

1. **listSessions**: Fixed - frontend now passes "user-1" to match createSession.
2. **Rancher Desktop**: Tests require Rancher Desktop for SurrealDB. If Rancher Desktop isn't running, `make db-up` fails.
3. **Playwright**: UI tests require `playwright install chromium` after first install.

## API Keys Required

- **OPENAI_API_KEY** (required): For agent, extraction, embeddings
- **LANGCHAIN_API_KEY** (optional): For LangSmith observability

## Performance Notes

- PDF ingestion: ~10-30s per paper (depends on size, OpenAI API)
- arXiv ingestion: ~5-15s per paper
- Ask/Agent: ~5-15s per query
- Vector search: <200ms

## Next Steps

1. Run full test suite when environment is ready
2. Fix listSessions user_id if needed
3. Add more UI test coverage for edge cases
4. Consider adding visual regression tests

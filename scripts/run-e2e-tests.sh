#!/bin/bash
# Comprehensive E2E Test Runner
# Runs all E2E tests with proper environment setup

set -e

echo "=== ResearchGraph E2E Test Runner ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

# Load environment variables from .env file
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Check prerequisites
echo "Checking prerequisites..."

# Check Rancher Desktop
if [ ! -S "$HOME/.rd/docker.sock" ]; then
    echo -e "${RED}ERROR: Rancher Desktop is not running or socket not found.${NC}"
    echo "Please start Rancher Desktop and try again."
    exit 1
fi

if ! docker ps >/dev/null 2>&1; then
    echo -e "${RED}ERROR: Cannot connect to Rancher Desktop.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Rancher Desktop is running${NC}"

# Check Python venv
if [ ! -d "backend/.venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    cd backend && python3 -m venv .venv && cd ..
fi

# Activate venv
source backend/.venv/bin/activate 2>/dev/null || {
    echo -e "${RED}Failed to activate venv${NC}"
    exit 1
}
echo -e "${GREEN}✓ Python venv activated${NC}"

# Check dependencies
if ! python -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    cd backend && pip install -r requirements.txt && cd ..
fi

# Check OpenAI API key
if ! grep -q "OPENAI_API_KEY=sk-" backend/.env 2>/dev/null; then
    echo -e "${RED}ERROR: OPENAI_API_KEY not found in backend/.env${NC}"
    exit 1
fi
echo -e "${GREEN}✓ OpenAI API key found${NC}"

# Start SurrealDB
echo ""
echo "Starting SurrealDB..."
cd /Users/paverma/PersonalProjects/ResearchGraph
make db-up
sleep 5

# Verify SurrealDB is running
if ! docker ps | grep -q surrealdb; then
    echo -e "${RED}ERROR: SurrealDB failed to start${NC}"
    exit 1
fi
echo -e "${GREEN}✓ SurrealDB is running${NC}"

# Check if backend is running
BACKEND_RUNNING=false
if curl -s http://localhost:8001/api/health >/dev/null 2>&1; then
    BACKEND_RUNNING=true
    echo -e "${GREEN}✓ Backend is already running${NC}"
else
    echo -e "${YELLOW}Starting backend...${NC}"
    echo "Please start backend in a separate terminal:"
    echo "  cd backend && source .venv/bin/activate && make dev"
    echo ""
    read -p "Press Enter when backend is running on :8001..."
    
    if curl -s http://localhost:8001/api/health >/dev/null 2>&1; then
        BACKEND_RUNNING=true
        echo -e "${GREEN}✓ Backend is running${NC}"
    else
        echo -e "${RED}ERROR: Backend is not responding${NC}"
        exit 1
    fi
fi

# Check if frontend is running
FRONTEND_RUNNING=false
if curl -s http://localhost:3000 >/dev/null 2>&1; then
    FRONTEND_RUNNING=true
    echo -e "${GREEN}✓ Frontend is already running${NC}"
else
    echo -e "${YELLOW}Starting frontend...${NC}"
    echo "Please start frontend in a separate terminal:"
    echo "  cd frontend && npm run dev"
    echo ""
    read -p "Press Enter when frontend is running on :3000..."
    
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        FRONTEND_RUNNING=true
        echo -e "${GREEN}✓ Frontend is running${NC}"
    else
        echo -e "${RED}ERROR: Frontend is not responding${NC}"
        exit 1
    fi
fi

echo ""
echo "=== Running E2E Tests ==="
echo ""

# Run API smoke tests first
echo "1. Running API smoke tests..."
cd backend
pytest tests/e2e/test_api_smoke.py -v --tb=short || {
    echo -e "${RED}API smoke tests failed${NC}"
    exit 1
}

# Run ingestion tests
echo ""
echo "2. Running ingestion flow tests..."
pytest tests/e2e/test_ingestion_flow.py -v --tb=short || {
    echo -e "${YELLOW}Ingestion tests failed (may need papers ingested first)${NC}"
}

# Run ask flow tests
echo ""
echo "3. Running ask flow tests..."
pytest tests/e2e/test_ask_flow.py -v --tb=short || {
    echo -e "${YELLOW}Ask flow tests failed (may need papers ingested first)${NC}"
}

# Run error handling tests
echo ""
echo "4. Running error handling tests..."
pytest tests/e2e/test_error_handling.py -v --tb=short || {
    echo -e "${RED}Error handling tests failed${NC}"
    exit 1
}

# Run citation path tests
echo ""
echo "5. Running citation path tests..."
pytest tests/e2e/test_citation_path.py -v --tb=short || {
    echo -e "${YELLOW}Citation path tests failed (may need papers with citations)${NC}"
}

# Run UI tests (if Playwright is installed)
echo ""
echo "6. Running UI tests..."
if python -c "import playwright" 2>/dev/null; then
    pytest tests/e2e/test_ui_flows.py -v --tb=short || {
        echo -e "${YELLOW}UI tests failed${NC}"
    }
else
    echo -e "${YELLOW}Skipping UI tests (Playwright not installed)${NC}"
    echo "Install with: pip install pytest-playwright && playwright install chromium"
fi

echo ""
echo -e "${GREEN}=== E2E Test Run Complete ===${NC}"
echo ""
echo "Summary:"
echo "- API smoke tests: Check above"
echo "- Ingestion tests: Check above"
echo "- Ask flow tests: Check above"
echo "- Error handling: Check above"
echo "- Citation path: Check above"
echo "- UI tests: Check above"

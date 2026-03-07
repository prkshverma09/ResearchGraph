#!/bin/bash
# Complete E2E Test Runner - Starts services and runs all tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

# Load environment variables from .env file
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

echo "=== ResearchGraph Complete E2E Test Runner ==="
echo ""

# Ensure DOCKER_HOST is set for Rancher Desktop (from .env or default)
export DOCKER_HOST="${DOCKER_HOST:-unix://${HOME}/.rd/docker.sock}"

# Check Docker/Rancher Desktop - prefer docker ps over socket check (more reliable)
if docker ps >/dev/null 2>&1; then
    echo "✓ Docker/Rancher Desktop is running"
elif [ -S "${HOME}/.rd/docker.sock" ]; then
    echo "❌ ERROR: Socket exists but 'docker ps' failed. Try: docker ps"
    exit 1
elif [ -S "/var/run/docker.sock" ]; then
    export DOCKER_HOST=unix:///var/run/docker.sock
    if docker ps >/dev/null 2>&1; then
        echo "✓ Docker is running"
    else
        echo "❌ ERROR: Cannot connect to Docker."
        exit 1
    fi
else
    echo "❌ ERROR: Docker/Rancher Desktop is not running."
    echo "  - Rancher Desktop: Start the app, ensure socket exists at ~/.rd/docker.sock"
    echo "  - Docker Desktop: Ensure Docker is running"
    exit 1
fi

# Activate venv
if [ ! -d "backend/.venv" ]; then
    echo "Creating virtual environment..."
    cd backend && python3 -m venv .venv && cd ..
fi

source backend/.venv/bin/activate
echo "✓ Python venv activated"

# Install dependencies
echo "Installing dependencies..."
cd backend
pip install -q -i https://pypi.org/simple numpy langchain-text-splitters 2>/dev/null || true
pip install -q -r requirements.txt -i https://pypi.org/simple 2>/dev/null || true
cd ..

# Check OpenAI API key
if ! grep -q "OPENAI_API_KEY=sk-" backend/.env 2>/dev/null; then
    echo "❌ ERROR: OPENAI_API_KEY not found in backend/.env"
    exit 1
fi
echo "✓ OpenAI API key found"

# Start SurrealDB
echo ""
echo "Starting SurrealDB..."
make db-reset
sleep 5

if ! docker ps | grep -q surrealdb; then
    echo "❌ ERROR: SurrealDB failed to start"
    exit 1
fi
echo "✓ SurrealDB is running"

# Start Backend
echo ""
echo "Starting Backend..."
cd backend
source .venv/bin/activate

# Kill any existing backend process
pkill -f "uvicorn app.main:app" 2>/dev/null || true
lsof -ti:18001 | xargs kill -9 2>/dev/null || true
sleep 2

nohup uvicorn app.main:app --host 0.0.0.0 --port 18001 --env-file .env > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s -f http://localhost:18001/api/health >/dev/null 2>&1; then
        echo "✓ Backend is running on http://localhost:18001"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start. Check logs: tail -f /tmp/backend.log"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

cd ..

# Start Frontend
echo ""
echo "Starting Frontend..."
cd frontend

# Install deps if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Kill any existing frontend process
pkill -f "next dev" 2>/dev/null || true
lsof -ti:13000 | xargs kill -9 2>/dev/null || true
sleep 2

NEXT_PUBLIC_API_URL=http://localhost:18001 nohup npm run dev -- -p 13000 > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# Wait for frontend to start
echo "Waiting for frontend to start..."
for i in {1..30}; do
    if curl -s -f http://localhost:13000 >/dev/null 2>&1; then
        echo "✓ Frontend is running on http://localhost:13000"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠ Frontend may still be starting. Check logs: tail -f /tmp/frontend.log"
    fi
    sleep 1
done

cd ..

# Run E2E Tests
echo ""
echo "=== Running E2E Tests ==="
echo ""

cd backend
source .venv/bin/activate

# Run tests
echo "1. API Smoke Tests..."
pytest tests/e2e/test_api_smoke.py -v --tb=short || echo "⚠ Some smoke tests failed"

echo ""
echo "2. Error Handling Tests..."
pytest tests/e2e/test_error_handling.py -v --tb=short || echo "⚠ Some error tests failed"

echo ""
echo "3. Ingestion Flow Tests..."
pytest tests/e2e/test_ingestion_flow.py -v --tb=short || echo "⚠ Ingestion tests failed (may need papers ingested)"

echo ""
echo "4. Ask Flow Tests..."
pytest tests/e2e/test_ask_flow.py -v --tb=short || echo "⚠ Ask flow tests failed"

echo ""
echo "5. Citation Path Tests..."
pytest tests/e2e/test_citation_path.py -v --tb=short || echo "⚠ Citation path tests failed"

echo ""
echo "6. UI Tests (if Playwright installed)..."
if python -c "import playwright" 2>/dev/null; then
    pytest tests/e2e/test_ui_flows.py -v --tb=short || echo "⚠ UI tests failed"
else
    echo "Skipping UI tests (Playwright not installed)"
    echo "Install with: pip install pytest-playwright && playwright install chromium"
fi

cd ..

echo ""
echo "=== Test Run Complete ==="
echo ""
echo "Services are still running:"
echo "  Backend:  http://localhost:18001 (PID: $BACKEND_PID)"
echo "  Frontend: http://localhost:13000 (PID: $FRONTEND_PID)"
echo ""
echo "To stop services:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo "  make db-down"
echo ""
echo "View logs:"
echo "  tail -f /tmp/backend.log"
echo "  tail -f /tmp/frontend.log"

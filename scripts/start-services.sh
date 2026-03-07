#!/bin/bash
# Start all services for E2E testing

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

echo "=== Starting ResearchGraph Services ==="

# Check Rancher Desktop
if [ ! -S "$HOME/.rd/docker.sock" ]; then
    echo "ERROR: Rancher Desktop is not running or socket not found. Please start Rancher Desktop first."
    exit 1
fi

if ! docker ps >/dev/null 2>&1; then
    echo "ERROR: Cannot connect to Rancher Desktop. Please ensure Rancher Desktop is running."
    exit 1
fi

# Start SurrealDB
echo "1. Starting SurrealDB..."
cd /Users/paverma/PersonalProjects/ResearchGraph
make db-up
sleep 5

# Verify SurrealDB
if docker ps | grep -q surrealdb; then
    echo "✓ SurrealDB is running"
else
    echo "ERROR: SurrealDB failed to start"
    exit 1
fi

# Start Backend
echo ""
echo "2. Starting Backend..."
cd /Users/paverma/PersonalProjects/ResearchGraph/backend
source .venv/bin/activate

# Install missing deps if needed
pip install -q numpy langchain-text-splitters 2>/dev/null || true

# Start backend in background
nohup uvicorn app.main:app --host 0.0.0.0 --port 8001 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
echo "Backend logs: tail -f /tmp/backend.log"

sleep 5

# Verify backend
if curl -s http://localhost:8001/api/health >/dev/null 2>&1; then
    echo "✓ Backend is running on http://localhost:8001"
else
    echo "⚠ Backend may still be starting. Check logs: tail -f /tmp/backend.log"
fi

# Start Frontend
echo ""
echo "3. Starting Frontend..."
cd /Users/paverma/PersonalProjects/ResearchGraph/frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start frontend in background
nohup npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"
echo "Frontend logs: tail -f /tmp/frontend.log"

sleep 5

# Verify frontend
if curl -s http://localhost:3000 >/dev/null 2>&1; then
    echo "✓ Frontend is running on http://localhost:3000"
else
    echo "⚠ Frontend may still be starting. Check logs: tail -f /tmp/frontend.log"
fi

echo ""
echo "=== Services Started ==="
echo ""
echo "Backend:  http://localhost:8001"
echo "Frontend: http://localhost:3000"
echo ""
echo "To stop services:"
echo "  kill $BACKEND_PID $FRONTEND_PID"
echo "  make db-down"

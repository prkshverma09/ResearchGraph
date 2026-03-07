#!/bin/bash
# Run E2E tests - assumes backend and frontend are already running
# Start them in separate terminals first:
#   make dev
#   cd frontend && npm run dev

set -e

echo "=== Running E2E Tests ==="

# Verify backend is up
if curl -s http://localhost:8001/api/health >/dev/null 2>&1; then
    echo "Backend is running"
else
    echo "ERROR: Backend not running on :8001. Start with: make dev"
    exit 1
fi

# Verify frontend is up
if curl -s http://localhost:3000 >/dev/null 2>&1; then
    echo "Frontend is running"
else
    echo "ERROR: Frontend not running on :3000. Start with: cd frontend && npm run dev"
    exit 1
fi

cd backend
pytest -m e2e -v

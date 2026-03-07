#!/bin/bash
# E2E Test Environment Setup Script
# Run this before executing E2E tests

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

echo "=== ResearchGraph E2E Setup ==="

# Check for required tools
if [ ! -S "$HOME/.rd/docker.sock" ]; then
    echo "ERROR: Rancher Desktop is not running or socket not found. Please start Rancher Desktop."
    exit 1
fi
command -v docker >/dev/null 2>&1 || { echo "Docker CLI is required but not installed. Aborting."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed. Aborting."; exit 1; }

# Check backend .env
if [ ! -f backend/.env ]; then
    echo "Creating backend/.env from .env.example..."
    cp backend/.env.example backend/.env
    echo "WARNING: Please add your OPENAI_API_KEY to backend/.env"
fi

if ! grep -q "OPENAI_API_KEY=sk-" backend/.env 2>/dev/null; then
    echo "WARNING: OPENAI_API_KEY may not be set in backend/.env"
fi

# Check frontend .env.local
if [ ! -f frontend/.env.local ]; then
    echo "Creating frontend/.env.local..."
    echo "NEXT_PUBLIC_API_URL=http://localhost:8001" > frontend/.env.local
fi

# Start SurrealDB
echo "Starting SurrealDB..."
make db-up
sleep 3

# Verify SurrealDB
if docker ps | grep -q surrealdb; then
    echo "SurrealDB is running"
else
    echo "ERROR: SurrealDB failed to start"
    exit 1
fi

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend && pip install -r requirements.txt && cd ..

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend && npm install && cd ..

echo ""
echo "=== Setup Complete ==="
echo "To run E2E tests:"
echo "  1. Terminal 1: make dev          # Start backend on :8001"
echo "  2. Terminal 2: cd frontend && npm run dev  # Start frontend on :3000"
echo "  3. Terminal 3: make test-e2e     # Run E2E tests"
echo ""
echo "Or use: ./scripts/run-e2e.sh"

.PHONY: help dev test test-unit test-integration test-e2e db-up db-down db-reset install lint format

help:
	@echo "Available commands:"
	@echo "  make dev          - Start development server"
	@echo "  make test         - Run all tests"
	@echo "  make test-unit    - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-e2e     - Run E2E tests"
	@echo "  make db-up        - Start SurrealDB via Rancher Desktop"
	@echo "  make db-down      - Stop SurrealDB"
	@echo "  make db-reset     - Reset SurrealDB database"
	@echo "  make install      - Install Python dependencies"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"

dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

test:
	cd backend && pytest

test-unit:
	cd backend && pytest -m unit

test-integration:
	cd backend && pytest -m integration

test-e2e:
	cd backend && pytest -m e2e -v
test-e2e-api:
	cd backend && pytest -m e2e tests/e2e/test_api_smoke.py tests/e2e/test_error_handling.py tests/e2e/test_citation_path.py -v

# Load DOCKER_HOST from .env file if it exists, otherwise use default
-include .env
export DOCKER_HOST ?= unix://$(HOME)/.rd/docker.sock

db-up:
	@if [ ! -S "$(HOME)/.rd/docker.sock" ]; then \
		echo "❌ ERROR: Rancher Desktop is not running or socket not found."; \
		echo "Please start Rancher Desktop and try again."; \
		exit 1; \
	fi
	docker compose up -d surrealdb
	@echo "Waiting for SurrealDB to be ready..."
	@sleep 3

db-down:
	@if [ ! -S "$(HOME)/.rd/docker.sock" ]; then \
		echo "❌ ERROR: Rancher Desktop is not running or socket not found."; \
		exit 1; \
	fi
	docker compose down

db-reset:
	@if [ ! -S "$(HOME)/.rd/docker.sock" ]; then \
		echo "❌ ERROR: Rancher Desktop is not running or socket not found."; \
		exit 1; \
	fi
	docker compose down -v
	docker compose up -d surrealdb
	@sleep 3

install:
	cd backend && pip install -r requirements.txt

lint:
	cd backend && ruff check .
	cd backend && mypy app

format:
	cd backend && black .
	cd backend && ruff check --fix .

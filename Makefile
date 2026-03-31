# Mosoro Core — Makefile
# ============================================================================

.PHONY: help setup add-robot demo up down logs clean lint fmt fmt-check

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup:  ## Interactive setup wizard
	@./scripts/setup-wizard.sh

add-robot:  ## Add another robot to your configuration
	@./scripts/setup-wizard.sh --add

demo:  ## Start Mosoro with virtual robots — no config needed
	docker compose -f docker-compose.yml -f docker-compose.demo.yml up --build

up:  ## Start the base stack (no simulator)
	docker compose up --build

down:  ## Stop all services
	docker compose -f docker-compose.yml -f docker-compose.demo.yml down

logs:  ## Tail logs for all services
	docker compose -f docker-compose.yml -f docker-compose.demo.yml logs -f

clean:  ## Stop and remove volumes
	docker compose -f docker-compose.yml -f docker-compose.demo.yml down -v

lint:  ## Run ruff linter (matches CI)
	ruff check .

fmt:  ## Auto-format code with ruff (run before committing)
	ruff format .

fmt-check:  ## Check formatting without modifying files (matches CI)
	ruff format --check .

.PHONY: help venv install install-gui install-dev dev run gui test test-cov lint format type-check clean docs docker

VENV ?= .venv
PY = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
PORT ?= 5102

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

venv:  ## Create virtual environment
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip wheel setuptools

install: venv  ## Install core package
	$(PIP) install -e .

install-gui: install  ## Install with GUI support
	$(PIP) install -e .[gui]

install-dev: install-gui  ## Install with dev tools
	$(PIP) install -e .[dev]
	$(VENV)/bin/pre-commit install

dev:  ## Run server in development mode (auto-reload)
	$(VENV)/bin/uvicorn lmarena_bridge.main:create_app --factory --reload --port $(PORT)

run:  ## Run server in production mode
	$(VENV)/bin/lmarena-bridge --port $(PORT)

gui:  ## Launch GUI
	$(VENV)/bin/lmarena-bridge-gui

test:  ## Run tests
	$(VENV)/bin/pytest -v

test-cov:  ## Run tests with coverage report
	$(VENV)/bin/pytest --cov=lmarena_bridge --cov=lmarena_bridge_gui --cov-report=html --cov-report=term

lint:  ## Check code with ruff
	$(VENV)/bin/ruff check .

format:  ## Format code with ruff
	$(VENV)/bin/ruff format .
	$(VENV)/bin/ruff check --fix .

type-check:  ## Run type checking with mypy
	$(VENV)/bin/mypy lmarena_bridge

check: lint type-check test  ## Run all checks (lint, type, test)

clean:  ## Clean up generated files
	rm -rf $(VENV) build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +

docs:  ## Generate documentation
	@echo "Documentation is in README.md and docs/ folder"

docker:  ## Build Docker image
	docker build -t lmarena-bridge:latest .

docker-run:  ## Run Docker container
	docker run -p 5102:5102 -v $(PWD)/config:/app/config lmarena-bridge:latest
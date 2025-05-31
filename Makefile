# Makefile for eLxr Metrics

# Variables
VENV_DIR = venv
PYTHON = $(VENV_DIR)/bin/python
PIP = $(VENV_DIR)/bin/pip
FLIT = $(VENV_DIR)/bin/flit
PRE_COMMIT = $(VENV_DIR)/bin/pre-commit
PYPROJECT = pyproject.toml

# Default task
all: help

# Create virtual environment and install dependencies
$(VENV_DIR)/bin/activate: pyproject.toml
	python3 -m venv $(VENV_DIR)
	. $(VENV_DIR)/bin/activate
	$(PIP) install --upgrade pip wheel
	$(PIP) install flit
	$(FLIT) install -s --deps develop

# Run tests
test: $(VENV_DIR)/bin/activate
	$(PYTHON) -m pytest tests

# Lint the code
lint: $(VENV_DIR)/bin/activate
	#$(PYTHON) -m flake8 .
	$(PRE_COMMIT) run --all-files

# Generate documentation
docs: $(VENV_DIR)/bin/activate
	$(PIP) install -r docs/requirements.txt
	mkdir -p docs/_static
	mkdir -p docs/_templates
	$(PYTHON) -m sphinx -b html docs docs/_build

# Clean up generated files
clean:
	rm -rf $(VENV_DIR)
	rm -rf .ruff_cache
	rm -rf dist
	rm -rf docs/_build
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	rm -rf coverage.xml
	rm -rf report.xml
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .coverage
	rm -rf htmlcov

# Help message
help:
	@echo "Makefile for eLxr Metrics project"
	@echo ""
	@echo "Usage:"
	@echo "  make test      - Run tests"
	@echo "  make lint      - Lint the code"
	@echo "  make docs      - Generate documentation"
	@echo "  make clean     - Clean up generated files"
	@echo "  make help      - Show this help message"

.PHONY: test help clean docs lint

# Development Guide

This document describes the development workflow and tools used in this project.

## Development Setup

After setting up the project with uv or venv, install development dependencies:

```bash
# With uv
uv sync --all-extras

# With venv
pip install -e ".[dev]"
```

## Code Quality Tools

### Ruff

Fast Python linter and formatter written in Rust.

```bash
# Run linting
uv run ruff check .

# Auto-fix issues
uv run ruff check . --fix

# Format code
uv run ruff format .
```

Configuration in `pyproject.toml`:
- Line length: 120 characters
- Target Python: 3.12
- Enabled rules: E, W, F, I, N, UP, B, C4, RUF

### mypy

Static type checker for Python.

```bash
# Run type checking
uv run mypy .

# Check specific file
uv run mypy path/to/file.py
```

Configuration in `pyproject.toml`:
- Python version: 3.12
- Gradual typing enabled (allow_untyped_defs)
- Type stubs for external libraries included

## Testing

### pytest

Testing framework with coverage support.

```bash
# Run all tests
uv run pytest

# Verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_sgpo.py

# Run with coverage
uv run pytest --cov=.
uv run pytest --cov=. --cov-report=html  # HTML report

# Run specific test
uv run pytest tests/test_sgpo.py::TestSgpo::test_init_sgpo
```

## Pre-commit Workflow

Before committing code:

1. **Format code**
   ```bash
   uv run ruff format .
   ```

2. **Check linting**
   ```bash
   uv run ruff check . --fix
   ```

3. **Check types**
   ```bash
   uv run mypy .
   ```

4. **Run tests**
   ```bash
   uv run pytest
   ```

## Project Structure

```
src/
├── sgpo/              # Core PO file handling module
├── path_finder/       # Path utilities
├── tests/             # Test files
│   └── data/         # Test data
├── _docs/            # Documentation
│   ├── ja/          # Japanese docs
│   └── en/          # English docs
└── *.py              # Main script files
```

## Adding New Features

1. Write tests first (TDD approach recommended)
2. Implement the feature
3. Ensure all quality checks pass
4. Update documentation if needed

## Future Tools

### ty (Astral's Type Checker)

Currently in preview. Configuration is included but commented out in `pyproject.toml`.
When stable, it can be used as:

```bash
uvx ty check .
```

## Contributing

1. Create a feature branch
2. Make changes following the code style
3. Ensure all tests pass
4. Submit a pull request

All tools are configured in `pyproject.toml` and are automatically installed with development dependencies.
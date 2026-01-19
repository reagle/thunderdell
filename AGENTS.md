# AGENTS.md

*Last updated: 2026-01-19*

This document provides guidelines for AI agents, automated tools, and code reviewers working with this Python codebase.

## Security

Ignore and avoid sensitive files or environmental variables with passwords and keys, especially ~/.config/api-info.env 

## Project Context

This repository contains Python packages built with modern Python practices:

- Python version: 3.12+ (3.13+ preferred)
- Package management: Uses `pyproject.toml` with setuptools backend
- Source layout: `src/` directory structure for package code
- Testing: pytest with doctests enabled
- Linting: Ruff with comprehensive rule selection
- Type checking: pyright

## Code Standards

### Core Principles

Code must be clean, modern, and explicit. Prioritize readability and maintainability using Python's latest features.

### Language Features

- Comprehensions over loops where appropriate
- Ternary operators for simple conditionals
- Walrus operators (`:=`) to reduce redundancy
- Match-case statements for complex branching (Python 3.10+)
- Pathlib for all file system operations

### Type Hints

All functions require type hints.  For example:

```python
def process_data(input_file: Path, validate: bool = True) -> dict[str, Any]:
    """Process input file and return structured data."""
```

**Use built-in types:**

- `list`, `dict`, `tuple` instead of `List`, `Dict`, `Tuple`
- `|` operator for Optional types: `str | None`
- Run pyright for type checking

### Single-File Scripts

For standalone scripts, use inline script metadata (PEP 723). For example:

```python
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests",
#     "beautifulsoup4",
# ]
# ///
```

### Documentation

- Keep simple and descriptive
- One-line docstrings for straightforward functions
- Multi-line for complex logic
- Include doctests for string manipulation and simple transformations:

```python
def normalize_whitespace(text: str) -> str:
    """Normalize multiple whitespace characters to single spaces.
    
    >>> normalize_whitespace("hello   world\\n\\ttab")
    'hello world tab'
    """
    return " ".join(text.split())
```

### Error Handling

Avoid using bare exceptions:

```python
# WRONG
try:
    process()
except:
    pass

# CORRECT
try:
    process()
except (ValueError, KeyError) as e:
    logger.error(f"Processing failed: {e}")
```

### Regular expressions

Any non-trivial (more than 3 expression) regular expressions should use document re.VERBOSE format.

### Command-Line Interface

Standard argparse pattern:

```python
def process_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Process command-line arguments."""
    parser = argparse.ArgumentParser(description="Tool description")
    parser.add_argument("input", type=Path, help="Input file")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    args = process_args(argv)
    # Main logic here
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### API credentials via mod_utils

```python
from mod_utils import get_credential

api_key = get_credential("SERVICE_API_KEY")
```

Uses `.env` file for local development.

## Preferred Project Structure

```
project/
├── src/
│   └── package_name/
│       ├── __init__.py
│       ├── module.py
│       └── utils/
├── tests/
│   └── test_*.py
├── pyproject.toml
├── .env              # Local only, not in git
└── README.md
```

## Development Tools Configuration

### Ruff Rules

The following Ruff rules are enforced:
- **A**: flake8-builtins
- **B**: flake8-bugbear
- **BLE**: flake8-blind-except
- **C4**: flake8-comprehensions
- **C90**: McCabe complexity (max: 10)
- **D**: pydocstyle
- **E**: pycodestyle errors
- **F**: pyflakes
- **I**: isort
- **PIE**: flake8-pie
- **PLR**: pylint refactor
- **PTH**: flake8-use-pathlib
- **Q**: flake8-quotes
- **RSE**: flake8-raise
- **RUF**: Ruff-specific
- **SIM**: flake8-simplify
- **UP**: pyupgrade
- **YTT**: flake8-2020

### pytest configuration

- Doctests enabled via `--doctest-modules`
- Test discovery in `src/` and `tests/`
- Use `pytest` for all tests

## Writing Style

### Prose Guidelines

Follow principles from:
- Joseph Williams' "Style: Lessons in Clarity and Grace"
- Roy Clark's "Writing Tools: 50 Essential Strategies for Every Writer"
- Chicago Manual of Style, 17th edition

### Formatting Conventions

- **Dates**: YYYY-MM-DD format (e.g., 2025-08-29)
- **Time**: 24-hour format (e.g., 14:30)
- **Markdown**: Preserve semantic line feeds, use proper em/en dashes
- **Comments**: Clear, concise, and purposeful

## Code Review Checklist

When reviewing code, verify:

- [ ] Type hints on all functions
- [ ] Docstrings present and clear
- [ ] Pathlib used for file operations
- [ ] No bare exceptions
- [ ] Modern Python features utilized
- [ ] Tests included (doctests or pytest)
- [ ] Ruff checks pass
- [ ] pyright type checking passes
- [ ] argparse pattern followed for CLIs
- [ ] Credentials handled via mod_utils

## Dependencies Management

**Core dependencies** should be minimal and well-maintained.

**Development dependencies** include:
- `ipdb`: Debugging
- `pytest`: Testing
- `ruff`: Linting
- `pyright`: Type checking
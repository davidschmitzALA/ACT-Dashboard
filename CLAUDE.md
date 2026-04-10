# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

Python must be installed before anything else works. Download from https://www.python.org/downloads/ — check "Add Python to PATH" during install.

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows (bash/Git Bash)
# or
.venv\Scripts\activate.bat      # Windows (Command Prompt)
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Common Commands

```bash
python main.py              # Run the main script
python -m pytest            # Run all tests
python -m pytest tests/test_example.py  # Run a single test file
python -m pytest -k "test_name"         # Run a specific test by name
pip install <package>       # Install a new package
pip freeze > requirements.txt           # Save current dependencies
```

## Project Structure

This is a learning/experimentation project. New experiments live in `experiments/` as standalone scripts. Reusable utilities go in `src/`. Tests go in `tests/` mirroring the structure of `src/`.

## Style

- Follow PEP 8
- Use `black` for formatting: `black .`
- Use `ruff` for linting: `ruff check .`

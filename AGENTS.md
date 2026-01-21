# AGENTS.md — FinNews Repository Guide

This file is for agentic coding tools working in this repo. It summarizes how to build, test, lint, and follow local code style. Keep changes minimal, match existing patterns, and avoid introducing new tooling unless requested.

## Scope
- Applies to the entire repository unless superseded by a deeper `AGENTS.md`.
- No Cursor or Copilot rules detected in `.cursor/rules/`, `.cursorrules`, or `.github/copilot-instructions.md`.

## Tech Stack
- Python 3.10+ (per README)
- Data pipeline: scrapers + processors + storage + scheduler
- Logging: `utils/logger.py` uses stdlib logging + colorlog

---

## Build / Install
There is no formal build system; install dependencies with pip.

- Install deps: `pip install -r requirements.txt`
- Upgrade deps (sometimes recommended in README): `pip install -r requirements.txt --upgrade`

## Run
- One-shot pipeline: `python main.py --mode once`
- Scheduled pipeline: `python main.py --mode scheduled`

## Tests
There is no centralized test runner (pytest/unittest configs are not present). Tests are standalone scripts in the root directory.

### Single test (per component)
**Scrapers**:
- Tavily: `python test_tavily.py`
- yfinance: `python test_yfinance.py`
- RSS: `python test_rss.py`
- FRED: `python test_fred.py`

**Utilities**:
- Email digest: `python test_digest_to_file.py`
- OpenRouter LLM: `python test_openrouter_digest.py`
- Gmail SMTP: `python test_gmail_smtp.py`

### End-to-end check
- Run once: `python main.py --mode once`

### Test file pattern
Tests use absolute imports with `sys.path.insert(0, "D:\\Projects\\FinNews")` at the top. When creating tests, follow this pattern for module imports.

## Lint / Format / Type Check
- No lint/format/typecheck tools are actively configured or enforced.
- A `.ruff_cache/` directory exists but no `ruff.toml` or `pyproject.toml` config is present.
- No black/flake8/mypy/tox/nox configurations detected.
- Do **not** introduce new linters or formatters unless explicitly requested.

---

## Code Style Guidelines
Match the existing Python style and structure. Keep edits minimal.

### Imports
- Order: standard library → third‑party → local modules.
- Use explicit imports from package `__init__.py` where available (e.g., `from scrapers import TavilyScraper`).
- Prefer local package imports (`from config.config import Config`) over relative imports in top-level modules.
- Test files use `sys.path.insert(0, "D:\\Projects\\FinNews")` for absolute imports; maintain this pattern when adding tests.

### Formatting
- 4‑space indentation.
- Blank lines between logical blocks and between top-level definitions.
- Reasonable line length (current code often stays within ~88–100 chars; avoid very long lines).

### Naming
- Classes: `PascalCase` (e.g., `DataCleaner`, `BaseScraper`).
- Functions/methods: `snake_case`.
- Module-level constants: `UPPER_SNAKE_CASE`.
- Private/internal helpers prefixed with `_`.

### Typing
- Type hints are commonly used; keep or add hints when touching code.
- Typical container types: `List[Dict[str, Any]]`, `Optional[...]`.

### Docstrings & Comments
- Modules and classes have short docstrings in Chinese or bilingual (中文/English) format.
- Functions generally include docstrings for non-trivial logic.
- Avoid noisy inline comments; add only when clarifying non-obvious logic.
- User-facing messages and logs often use bilingual format: "中文 | English" or "中文..." followed by English.

### Error Handling
- Wrap risky external calls in `try/except`.
- Log errors with context; use `logger.error(..., exc_info=True)` when stack traces help.
- Fail fast on configuration errors (e.g., `Config.validate()` raises `ValueError`).
- For optional dependencies, handle `ImportError` gracefully (see `processors/cleaner.py` BS4_AVAILABLE pattern).
- Main pipeline uses try/except for scraper initialization, logging warnings for failures without halting.

### Logging
- Use `utils.logger.setup_logger()` in entrypoints/tests.
- Within modules, prefer `logging.getLogger("<namespace>")` or `get_logger()` helper.
- Use `info` for high-level progress, `warning` for recoverable issues, `error` for failures, `debug` for verbose details.

### Data Records
- Scraper records use a normalized dict structure from `BaseScraper._create_base_record`.
- If adding fields, ensure processors and storage handle them safely.

---

## Project Structure Notes
- `scrapers/`: external data sources, subclass `BaseScraper`.
- `processors/`: cleaning and deduplication.
- `storage/`: JSON/Markdown outputs.
- `schedulers/`: APScheduler orchestration.
- `config/config.py`: configuration + env management.

---

## Conventions for Agents
- Do not add new dependencies to `requirements.txt` unless explicitly requested.
- Do not reformat unrelated code or introduce linting tools.
- Prefer minimal, isolated changes tied to the request.
- When editing, keep consistent with existing log messages and bilingual (中文/English) style where used.
- Maintain absolute paths in test files (see `sys.path.insert` pattern in existing tests).
- When adding new scrapers, extend `scrapers/__init__.py` and follow `BaseScraper` interface.

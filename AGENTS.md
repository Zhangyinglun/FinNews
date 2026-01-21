# AGENTS.md — FinNews Repository Guide

**Generated:** 2026-01-20 22:27:00  
**Commit:** 5f741e1  
**Branch:** main

## OVERVIEW
Financial news aggregation pipeline for gold/silver price analysis. Scrapes 5+ sources, filters by keywords, deduplicates, applies rule-based market signals, outputs structured reports for LLM consumption.

## SCOPE
Applies to entire repository unless superseded by subdirectory `AGENTS.md` (see `scrapers/`, `utils/`, `analyzers/`, `models/`).

## TECH STACK
- Python 3.10+
- Pipeline: scrapers → processors → analyzers → storage
- Data models: Pydantic
- Scheduling: APScheduler (documented but not implemented)
- Logging: stdlib + colorlog

---

## STRUCTURE
```
FinNews/
├── scrapers/         # Data fetchers (5 sources), see scrapers/AGENTS.md
├── processors/       # Cleaning (cleaner.py) + dedup (deduplicator.py)
├── analyzers/        # Rule engine + market analyzer, see analyzers/AGENTS.md
├── models/           # Pydantic data models, see models/AGENTS.md
├── storage/          # JSON/Markdown output (json_storage.py)
├── utils/            # Logging, LLM digest, email, see utils/AGENTS.md
├── config/           # Central config + .env management
├── tests/            # Mirrored test structure (14+ files)
├── outputs/          # Generated data (gitignored)
├── main.py           # Entry point (no CLI args despite docs)
├── run_tests.py      # Test runner with argparse
└── test_*.py         # Root-level standalone tests (7 files)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| Add new scraper | `scrapers/` + `main.py` | See `scrapers/AGENTS.md` for BaseScraper pattern |
| Add market analysis rule | `analyzers/rule_engine.py` | Threshold configs in `config/config.py` |
| Add data model | `models/` | Use Pydantic, export in `__init__.py` |
| Modify keyword filters | `config/config.py` | `KEYWORD_WHITELIST`/`KEYWORD_BLACKLIST` |
| Add logging | `utils/logger.py` | `setup_logger()` in entrypoints only |
| Customize output format | `storage/json_storage.py` | JSON + Markdown writers |
| Test single component | `./test_*.py` or `tests/*/` | Standalone scripts, no pytest |

---

## COMMANDS
```bash
# Install
pip install -r requirements.txt

# Run pipeline (single execution)
python main.py

# Test runner (select modules)
python run_tests.py

# Test individual component
python test_tavily.py
```

## TESTING
No pytest/unittest. Tests are standalone executables.

**Dual structure:**
- Root-level: `test_*.py` (7 files) — quick component checks, console output + JSON export
- `tests/` subdirectory: mirrored package structure with assertion-based tests

**Pattern (mandatory):**
```python
import sys
sys.path.insert(0, "D:\\Projects\\FinNews")  # Absolute imports

from scrapers import TavilyScraper
# ... rest of test
```

**Assertions:** Use bilingual messages: `assert len(data) > 0, "应该获取到数据"`

## LINTING
None configured. `.ruff_cache/` exists but inactive. Do NOT introduce linters.

---

## Code Style Guidelines

### Imports
- Order: stdlib → third-party → local
- Use package exports: `from scrapers import TavilyScraper`
- Test files: `sys.path.insert(0, "D:\\Projects\\FinNews")`

### Formatting
- 4-space indentation
- ~88-100 char line length

### Naming
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_prefix`

### Typing
- Type hints mandatory
- Common: `List[Dict[str, Any]]`, `Optional[...]`

### Docstrings
- Chinese or bilingual format
- User-facing logs: `"任务开始 | Task started"`

### Error Handling
- Wrap external calls in `try/except`
- Log with `logger.error(..., exc_info=True)`
- Optional deps: `BS4_AVAILABLE` pattern in `processors/cleaner.py`

---

## UNIQUE PATTERNS (THIS PROJECT)

### Non-Standard Layout
Source in root-level directories, no `src/` or `pyproject.toml`.

### Bilingual Output
Logs/docstrings/reports use Chinese/English: `"数据清洗完成 | Data cleaning complete"`

### Multi-Window Architecture
Three time windows for market analysis:
- **Flash** (24h): VIX, DXY, breaking news
- **Cycle** (7d): CPI, NFP, weekly economic data
- **Trend** (30d): Long-term signals, ETF flows

### Rule Engine Pre-processing
`RuleEngine` generates `MarketSignal` with:
- VIX alert levels (normal/warning/critical)
- Macro bias (bullish/bearish/neutral for gold)
- Sentiment score (-1.0 to +1.0)

### Keyword Filtering
Whitelist (must match ≥1) + Blacklist (exclude if any). Edit in `config/config.py`.

### Deduplication
MD5-based content hashing, 24-hour rolling window.

---

## ANTI-PATTERNS (THIS PROJECT)
- **NO** new dependencies without explicit request
- **NO** linters/formatters
- **NO** refactoring unrelated code
- **NO** changing bilingual log format
- **NO** modifying test import pattern (`sys.path.insert`)
- **NO** fixing pre-existing LSP errors (datetime in `base_scraper.py`, BS4 in `cleaner.py`)

## KNOWN GAPS
- `schedulers/` referenced in docs but directory doesn't exist
- `main.py` lacks `--mode` CLI args despite README documentation
- `ContentFetcher` not exported from `scrapers/__init__.py` but used in `main.py`

## NOTES
- API keys: `.env` required (copy from `.env.example`)
- Required: `TAVILY_API_KEY`, `FRED_API_KEY`
- Optional: `ALPHA_VANTAGE_API_KEY`, `OPENROUTER_API_KEY`
- Output: `outputs/processed/report_YYYYMMDD_HHMMSS.md`

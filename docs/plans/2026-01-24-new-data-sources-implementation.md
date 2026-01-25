# 2026-01-24-new-data-sources-implementation.md

## Goal
Implement DuckDuckGo scraper and extend RSS feeds to run in PARALLEL with Tavily, ensuring robust data collection even when API limits are hit.

## Proposed Changes

### Phase 1: Preparation (Deps & Config)

#### [Step 1] Update Requirements
- **File**: `requirements.txt`
- **Action**: Add `duckduckgo_search>=4.0.0`.

#### [Step 2] Update Configuration
- **File**: `config/config.py`
- **Action**:
    - Add `ENABLE_DDG = True` default.
    - Append new feeds to `RSS_FEEDS` (Kitco, CNBC, DailyFX).

### Phase 2: Core Development (Scraper)

#### [Step 3] Implement DuckDuckGo Scraper
- **File**: `scrapers/ddg_scraper.py`
- **Action**: Create `DuckDuckGoScraper` class.
- **Logic**:
    - Initialize with `DDGS`.
    - Iterate `Config.TAVILY_*_QUERIES`.
    - Extract results and map to standard news dict.
    - Handle `RatelimitException`.

#### [Step 4] Export Module
- **File**: `scrapers/__init__.py`
- **Action**: Import and export `DuckDuckGoScraper`.

### Phase 3: Integration (Main)

#### [Step 5] Integrate into Main Pipeline
- **File**: `main.py`
- **Action**:
    - Import `DuckDuckGoScraper`.
    - Initialize it if `Config.ENABLE_DDG` is True.
    - Append to `scrapers` list (allowing parallel execution with Tavily).

### Phase 4: Verification

#### [Step 6] Test Script
- **File**: `tests/scrapers/test_ddg.py`
- **Action**: Create unit test to verify DDG fetching.
- **Action**: Run test.

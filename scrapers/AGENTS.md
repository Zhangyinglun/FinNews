# AGENTS.md — Scrapers Directory

## OVERVIEW
Data fetchers inheriting from `BaseScraper`. Each scraper normalizes output via `_create_base_record()`.

## SCRAPERS
| Class | Source | API Key | Notes |
|-------|--------|---------|-------|
| `TavilyScraper` | Tavily API | `TAVILY_API_KEY` | AI-powered news search |
| `YFinanceScraper` | yfinance | — | Market data + news |
| `RSSFeedScraper` | RSS/Atom | — | Kitco, FXStreet feeds |
| `FREDScraper` | FRED API | `FRED_API_KEY` | Economic indicators |
| `AlphaVantageScraper` | Alpha Vantage | `ALPHA_VANTAGE_API_KEY` | Market sentiment |
| `ContentFetcher` | Web scraping | — | Full article extraction (not exported in `__init__.py`) |

## BASE CLASS PATTERN
```python
class MyScraper(BaseScraper):
    def scrape_data(self) -> List[Dict[str, Any]]:
        # Fetch data
        # Normalize via self._create_base_record(title, url, source, ...)
        # Return list, or [] on error
```

**Record schema** (from `_create_base_record`):
- `title`, `url`, `source`, `timestamp`, `content`, `category`
- `type`: `"price_data"` | `"economic_data"` | `"news"`
- `window_type`: `"flash"` | `"cycle"` | `"trend"` (optional)

## ADDING NEW SCRAPERS
1. Create `scrapers/your_scraper.py`
2. Inherit `BaseScraper`, implement `scrape_data()`
3. Export in `scrapers/__init__.py`
4. Register in `main.py`
5. Add test: `test_your_scraper.py` (root) using `sys.path.insert` pattern

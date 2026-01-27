"""
Scrapers module - Data collection from various sources
"""

from .base_scraper import BaseScraper
from .tavily_scraper import TavilyScraper
from .yfinance_scraper import YFinanceScraper
from .rss_scraper import RSSFeedScraper
from .fred_scraper import FREDScraper
from .alpha_vantage_scraper import AlphaVantageScraper
from .etf_scraper import EtfScraper
from .comex_scraper import ComexScraper
from .ddg_scraper import DuckDuckGoScraper
from .sonar_scraper import SonarScraper

__all__ = [
    "BaseScraper",
    "TavilyScraper",
    "YFinanceScraper",
    "RSSFeedScraper",
    "FREDScraper",
    "AlphaVantageScraper",
    "EtfScraper",
    "ComexScraper",
    "DuckDuckGoScraper",
    "SonarScraper",
]

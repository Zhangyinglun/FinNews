"""测试 SonarScraper 是否可从 scrapers 导出"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def test_sonar_scraper_export() -> None:
    import scrapers
    from scrapers import SonarScraper

    assert SonarScraper is not None
    assert "SonarScraper" in scrapers.__all__


if __name__ == "__main__":
    test_sonar_scraper_export()

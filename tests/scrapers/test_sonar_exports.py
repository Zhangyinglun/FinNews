"""测试 SonarScraper 是否可从 scrapers 导出"""

import sys

sys.path.insert(0, "D:\\Projects\\FinNews")


def test_sonar_scraper_export():
    import scrapers
    from scrapers import SonarScraper

    assert SonarScraper is not None
    assert "SonarScraper" in scrapers.__all__


if __name__ == "__main__":
    test_sonar_scraper_export()

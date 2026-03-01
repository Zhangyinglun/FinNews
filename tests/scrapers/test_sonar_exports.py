"""测试 SonarScraper 是否可从 scrapers 导出"""


def test_sonar_scraper_export() -> None:
    import scrapers
    from scrapers import SonarScraper

    assert SonarScraper is not None
    assert "SonarScraper" in scrapers.__all__

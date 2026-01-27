"""检查 main.py 是否包含 SonarScraper 初始化"""

import sys

sys.path.insert(0, "D:\\Projects\\FinNews")


def test_main_contains_sonar_scraper():
    with open("D:\\Projects\\FinNews\\main.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert "SonarScraper" in content


if __name__ == "__main__":
    test_main_contains_sonar_scraper()

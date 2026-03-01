"""检查 main.py 是否包含 SonarScraper 初始化"""

from pathlib import Path


def test_main_contains_sonar_scraper() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    main_path = repo_root / "main.py"
    with open(main_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "SonarScraper" in content

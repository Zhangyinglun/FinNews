"""
测试 EtfScraper — 重点验证换行符兼容性（CRLF/CR/LF 通用支持）
"""

import pytest
from scrapers.etf_scraper import EtfScraper

# 使用旧 Mac 风格 CR-only 换行符（会触发 csv "new-line character" 错误）
_GLD_CSV_CR_ONLY = (
    "Date,NAV,Shares,Tonnes,Ounces\r"
    "30-Jan-2026,262.54,333654000,941.35,30263527.0\r"
    "31-Jan-2026,265.12,334000000,943.26,30324980.0\r"
)

# 标准 CRLF（Windows 风格）
_GLD_CSV_CRLF = (
    "Date,NAV,Shares,Tonnes,Ounces\r\n"
    "30-Jan-2026,262.54,333654000,941.35,30263527.0\r\n"
    "31-Jan-2026,265.12,334000000,943.26,30324980.0\r\n"
)


@pytest.fixture
def mock_etf_cr(mocker):
    """模拟返回含 CR-only 换行符的 CSV 响应（复现真实 bug）"""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = _GLD_CSV_CR_ONLY
    mocker.patch("scrapers.etf_scraper.requests.get", return_value=mock_response)
    return mock_response


@pytest.fixture
def mock_etf_crlf(mocker):
    """模拟返回含 CRLF 换行符的 CSV 响应（Windows 格式）"""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = _GLD_CSV_CRLF
    mocker.patch("scrapers.etf_scraper.requests.get", return_value=mock_response)
    return mock_response


def test_etf_fetch_handles_cr_only_line_endings(mock_etf_cr):
    """EtfScraper.fetch() 应能解析 CR-only 换行符的 CSV，不抛出 csv 换行错误"""
    scraper = EtfScraper()
    data = scraper.fetch()

    assert isinstance(data, list)
    assert len(data) > 0, "应能从含 CR-only 换行的 CSV 中解析出数据"


def test_etf_fetch_handles_crlf_line_endings(mock_etf_crlf):
    """EtfScraper.fetch() 应能解析 CRLF 换行符的 CSV"""
    scraper = EtfScraper()
    data = scraper.fetch()

    assert isinstance(data, list)
    assert len(data) > 0, "应能从含 CRLF 换行的 CSV 中解析出数据"


def test_etf_fetch_returns_correct_tonnes(mock_etf_crlf):
    """解析出的持仓量应反映最新一行数据（943.26 吨）"""
    scraper = EtfScraper()
    data = scraper.fetch()

    assert len(data) > 0
    record = data[0]
    assert "943.26" in record.get("title", "") or "943.26" in record.get("summary", ""), (
        f"持仓量应包含 943.26 吨，实际 title={record.get('title')}"
    )

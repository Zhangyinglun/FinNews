"""
爬虫测试专用 fixture —— mock 响应数据
"""

import io
import pytest


@pytest.fixture
def mock_yfinance_ticker(mocker):
    """mock yfinance.Ticker，返回模拟价格与新闻数据"""
    import pandas as pd

    mock_ticker = mocker.MagicMock()
    mock_ticker.info = {
        "regularMarketPrice": 2050.12,
        "regularMarketPreviousClose": 2035.00,
        "regularMarketOpen": 2035.00,
        "regularMarketDayHigh": 2055.00,
        "regularMarketDayLow": 2030.00,
        "regularMarketVolume": 150000,
        "shortName": "Gold Futures",
    }
    mock_ticker.news = [
        {
            "title": "Gold prices rise on inflation fears",
            "link": "https://example.com/gold-1",
            "summary": "Gold futures increased as inflation data beat expectations",
            "providerPublishTime": 1700000000,
            "publisher": "Reuters",
        }
    ]
    # 历史数据
    hist_data = pd.DataFrame(
        {
            "Close": [2000.0, 2010.0, 2020.0, 2030.0, 2050.12],
            "Open": [1990.0, 2005.0, 2015.0, 2025.0, 2035.0],
            "High": [2005.0, 2015.0, 2025.0, 2040.0, 2055.0],
            "Low": [1985.0, 2000.0, 2010.0, 2020.0, 2030.0],
            "Volume": [100000, 110000, 120000, 130000, 150000],
        }
    )
    mock_ticker.history.return_value = hist_data

    mocker.patch("yfinance.Ticker", return_value=mock_ticker)
    return mock_ticker


@pytest.fixture
def mock_fred_client(mocker):
    """mock fredapi.Fred，返回模拟经济数据"""
    import pandas as pd

    mock_fred = mocker.MagicMock()

    def fake_get_series(series_id, **kwargs):
        values = {
            "CPIAUCSL": pd.Series([310.0, 311.5], index=pd.to_datetime(["2026-01-01", "2026-02-01"])),
            "PCEPILFE": pd.Series([170.0, 170.5], index=pd.to_datetime(["2026-01-01", "2026-02-01"])),
            "PAYEMS": pd.Series([158000, 158200], index=pd.to_datetime(["2026-01-01", "2026-02-01"])),
            "UNRATE": pd.Series([4.1, 4.0], index=pd.to_datetime(["2026-01-01", "2026-02-01"])),
            "FEDFUNDS": pd.Series([5.25, 5.25], index=pd.to_datetime(["2026-01-01", "2026-02-01"])),
            "GDP": pd.Series([28000, 28500], index=pd.to_datetime(["2025-10-01", "2026-01-01"])),
            "M1SL": pd.Series([18000, 18100], index=pd.to_datetime(["2026-01-01", "2026-02-01"])),
            "M2SL": pd.Series([21000, 21100], index=pd.to_datetime(["2026-01-01", "2026-02-01"])),
        }
        return values.get(series_id, pd.Series([1.0, 1.1], index=pd.to_datetime(["2026-01-01", "2026-02-01"])))

    mock_fred.get_series.side_effect = fake_get_series
    mocker.patch("fredapi.Fred", return_value=mock_fred)
    return mock_fred


@pytest.fixture
def mock_tavily_client(mocker):
    """mock tavily.TavilyClient，返回模拟搜索结果"""
    mock_client = mocker.MagicMock()
    mock_client.search.return_value = {
        "results": [
            {
                "title": "Gold prices surge on Fed rate cut hopes",
                "url": "https://reuters.com/gold-1",
                "content": "Gold futures rose sharply as investors bet on Fed rate cuts.",
                "score": 0.95,
                "published_date": "2026-03-01T10:00:00Z",
                "source": "reuters.com",
            },
            {
                "title": "Silver demand rises in industrial sector",
                "url": "https://bloomberg.com/silver-1",
                "content": "Silver prices gain as industrial demand improves.",
                "score": 0.88,
                "published_date": "2026-03-01T09:00:00Z",
                "source": "bloomberg.com",
            },
        ]
    }
    mocker.patch("tavily.TavilyClient", return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_feedparser(mocker):
    """mock feedparser.parse，返回模拟 RSS 数据"""
    mock_feed = mocker.MagicMock()
    mock_feed.entries = [
        mocker.MagicMock(
            title="Gold hits two-month high",
            link="https://kitco.com/news/1",
            summary="Gold reached its highest level in two months.",
            published_parsed=(2026, 3, 1, 10, 0, 0, 5, 60, 0),
        ),
        mocker.MagicMock(
            title="Silver industrial demand strong",
            link="https://kitco.com/news/2",
            summary="Industrial silver demand continues to grow.",
            published_parsed=(2026, 3, 1, 9, 0, 0, 5, 60, 0),
        ),
    ]
    mock_feed.bozo = False
    mocker.patch("feedparser.parse", return_value=mock_feed)
    return mock_feed


@pytest.fixture
def mock_stooq_response(mocker):
    """mock requests.get for Stooq CSV data"""
    csv_content = "Symbol,Date,Time,Open,High,Low,Close,Volume\nGC.F,2026-03-01,16:00:00,2035.0,2055.0,2030.0,2050.12,150000\n"

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = csv_content
    mocker.patch("requests.get", return_value=mock_response)
    return mock_response


@pytest.fixture
def mock_requests_get(mocker):
    """通用 requests.get mock，返回模拟 HTML 页面"""
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body><p>Gold prices are rising due to inflation concerns.</p></body></html>"
    mock_response.content = mock_response.text.encode("utf-8")
    mocker.patch("requests.get", return_value=mock_response)
    return mock_response

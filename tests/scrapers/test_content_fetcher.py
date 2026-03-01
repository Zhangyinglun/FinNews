"""
测试 ContentFetcher 完整内容抓取（mock 版）
"""

import pytest

from scrapers.content_fetcher import ContentFetcher


@pytest.fixture
def mock_http(mocker):
    """mock requests.Session.get"""
    # 段落内容需要超过 200 字符才能通过 _extract_content 的最小长度过滤
    html = (
        "<html><body>"
        "<p>Gold prices are rising due to inflation concerns driven by higher-than-expected CPI data. "
        "The Federal Reserve is watching closely and may consider adjusting interest rates. "
        "Investors are moving to safe-haven assets as market volatility increases significantly.</p>"
        "</body></html>"
    )
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = html
    mock_response.content = html.encode("utf-8")
    mock_response.raise_for_status = mocker.MagicMock()

    mock_session = mocker.MagicMock()
    mock_session.get.return_value = mock_response
    mocker.patch("scrapers.content_fetcher.requests.Session", return_value=mock_session)
    return mock_session


def test_content_fetcher_fetch_full_content(mock_http):
    """fetch_full_content 应返回字符串内容"""
    fetcher = ContentFetcher(max_retries=1, timeout=5)
    content = fetcher.fetch_full_content("https://example.com/article")

    assert content is not None
    assert isinstance(content, str)
    assert len(content) > 0


def test_content_fetcher_enrich_articles_with_url(mock_http):
    """enrich_articles 应处理有 URL 的文章"""
    fetcher = ContentFetcher(max_retries=1, timeout=5)
    articles = [
        {
            "title": "Gold prices rise",
            "summary": "Gold futures rose as inflation data beat estimates.",
            "url": "https://example.com/article",
            "source": "Reuters",
        }
    ]
    enriched = fetcher.enrich_articles(articles)

    assert len(enriched) == 1
    assert "title" in enriched[0]


def test_content_fetcher_enrich_articles_without_url(mock_http):
    """enrich_articles 对无 URL 文章不发请求"""
    fetcher = ContentFetcher(max_retries=1, timeout=5)
    articles = [
        {
            "title": "Test article without URL",
            "summary": "This article has no URL",
            "source": "Test",
        }
    ]
    enriched = fetcher.enrich_articles(articles)

    assert len(enriched) == 1
    # 无 URL 时 session.get 不应被调用
    mock_http.get.assert_not_called()

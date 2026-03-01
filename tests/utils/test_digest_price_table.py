"""
测试价格表在数据缺失时仍显示内容
"""

from models.analysis import MarketSignal
from models.market_data import MultiWindowData
from utils.digest_controller import DigestController


def test_price_table_always_renders_rows():
    """价格数据缺失时，价格表仍应显示所有行"""
    controller = DigestController()
    signal = MarketSignal()
    data = MultiWindowData()
    digest_data = {
        "subject": "测试邮件",
        "news_clusters": [],
        "analysis": {},
    }

    html, _ = controller.render_email_html(digest_data, signal, data)

    assert "价格数据暂时不可用" not in html
    for label in [
        "黄金 (XAU)",
        "白银 (XAG)",
        "VIX 恐慌指数",
        "美元指数 (DXY)",
        "10年期国债",
    ]:
        assert label in html

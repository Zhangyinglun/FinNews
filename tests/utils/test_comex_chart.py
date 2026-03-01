"""
COMEX 图表生成器单元测试
"""

import json
import unittest
from datetime import datetime, timedelta

import pytest

from utils.comex_chart import ComexChartGenerator


@pytest.fixture
def history_file(tmp_path):
    """创建临时历史数据文件"""
    now = datetime.now()
    records = {
        "silver_registered": [
            {"date": (now - timedelta(days=i)).strftime("%Y-%m-%d"), "value": 120.0 - i * 0.5}
            for i in range(14, 0, -1)
        ],
        "silver_total": [
            {"date": (now - timedelta(days=i)).strftime("%Y-%m-%d"), "value": 300.0 - i}
            for i in range(14, 0, -1)
        ],
        "gold_registered": [
            {"date": (now - timedelta(days=i)).strftime("%Y-%m-%d"), "value": 18.0 - i * 0.1}
            for i in range(14, 0, -1)
        ],
        "gold_total": [
            {"date": (now - timedelta(days=i)).strftime("%Y-%m-%d"), "value": 30.0 - i * 0.05}
            for i in range(14, 0, -1)
        ],
    }
    f = tmp_path / "comex_history.json"
    f.write_text(json.dumps(records), encoding="utf-8")
    return f


class TestComexChartGenerator(unittest.TestCase):
    """测试 ComexChartGenerator"""

    def setUp(self):
        """初始化测试 - 使用临时文件（通过 pytest fixture 注入）"""
        # 在 unittest 环境中，通过 conftest 的 tmp_path 不可直接用
        # 但我们可以通过 tmp_path 在 test 函数级别使用
        pass

    def test_empty_history(self, tmp_path=None):
        """测试历史数据为空时的处理"""
        from pathlib import Path
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_file = Path(tmpdir) / "fake_history.json"
            gen = ComexChartGenerator(fake_file)
            chart = gen.generate_chart("silver", days=14)
            self.assertIsNone(chart)


def test_generate_silver_chart(history_file):
    """测试生成白银图表"""
    generator = ComexChartGenerator(history_file)
    chart_base64 = generator.generate_chart("silver", days=14)

    assert chart_base64 is not None
    assert isinstance(chart_base64, str)
    assert len(chart_base64) > 100


def test_generate_gold_chart(history_file):
    """测试生成黄金图表"""
    generator = ComexChartGenerator(history_file)
    chart_base64 = generator.generate_chart("gold", days=14)

    assert chart_base64 is not None
    assert isinstance(chart_base64, str)


def test_generate_all_charts(history_file):
    """测试批量生成"""
    generator = ComexChartGenerator(history_file)
    charts = generator.generate_all_charts()

    assert "silver_chart" in charts
    assert "gold_chart" in charts
    assert charts["silver_chart"] is not None
    assert charts["gold_chart"] is not None


def test_empty_history_returns_none(tmp_path):
    """测试历史数据为空时返回 None"""
    fake_file = tmp_path / "fake_history.json"
    gen = ComexChartGenerator(fake_file)
    chart = gen.generate_chart("silver", days=14)
    assert chart is None

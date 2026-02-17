"""
COMEX 图表生成器单元测试
"""

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import unittest
from pathlib import Path
from utils.comex_chart import ComexChartGenerator


class TestComexChartGenerator(unittest.TestCase):
    """测试 ComexChartGenerator"""

    def setUp(self):
        """初始化测试"""
        # 使用真实的历史文件路径
        self.history_file = Path("D:/Projects/FinNews/outputs/comex_history.json")
        self.generator = ComexChartGenerator(self.history_file)

    def test_generate_silver_chart(self):
        """测试生成白银图表"""
        chart_base64 = self.generator.generate_chart("silver", days=14)

        # 验证返回 base64 字符串
        self.assertIsNotNone(chart_base64)
        self.assertIsInstance(chart_base64, str)
        self.assertGreater(len(chart_base64), 100)  # base64 字符串应该很长

    def test_generate_gold_chart(self):
        """测试生成黄金图表"""
        chart_base64 = self.generator.generate_chart("gold", days=14)

        self.assertIsNotNone(chart_base64)
        self.assertIsInstance(chart_base64, str)

    def test_generate_all_charts(self):
        """测试批量生成"""
        charts = self.generator.generate_all_charts()

        self.assertIn("silver_chart", charts)
        self.assertIn("gold_chart", charts)
        self.assertIsNotNone(charts["silver_chart"])
        self.assertIsNotNone(charts["gold_chart"])

    def test_empty_history(self):
        """测试历史数据为空时的处理"""
        # 使用不存在的文件
        fake_file = Path("D:/Projects/FinNews/outputs/fake_history.json")
        gen = ComexChartGenerator(fake_file)

        chart = gen.generate_chart("silver", days=14)
        # 应该返回 None 或空字符串
        self.assertIsNone(chart)


if __name__ == "__main__":
    unittest.main()

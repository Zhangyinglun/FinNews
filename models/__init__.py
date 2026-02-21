"""
数据模型包
包含市场数据和分析结果的 Pydantic 模型
"""

from .market_data import (
    PriceData,
    EconomicData,
    NewsItem,
    FlashWindowData,
    CycleWindowData,
    TrendWindowData,
    MultiWindowData,
)
from .analysis import (
    AlertLevel,
    MarketSignal,
    AnalysisResult,
)

__all__ = [
    # 市场数据模型
    "PriceData",
    "EconomicData",
    "NewsItem",
    "FlashWindowData",
    "CycleWindowData",
    "TrendWindowData",
    "MultiWindowData",
    # 分析结果模型
    "AlertLevel",
    "MarketSignal",
    "AnalysisResult",
]

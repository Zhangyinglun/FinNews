"""
市场数据模型
定义各时间窗口的数据结构
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PriceData(BaseModel):
    """价格数据模型"""

    ticker: str = Field(..., description="股票代码")
    ticker_name: str = Field(..., description="股票名称")
    price: float = Field(..., description="当前价格")
    change: Optional[float] = Field(None, description="价格变化")
    change_percent: Optional[float] = Field(None, description="变化百分比")
    week_change_percent: Optional[float] = Field(None, description="周涨跌幅")
    open: Optional[float] = Field(None, description="开盘价")
    high: Optional[float] = Field(None, description="最高价")
    low: Optional[float] = Field(None, description="最低价")
    volume: Optional[int] = Field(None, description="成交量")
    prev_close: Optional[float] = Field(None, description="前收盘价")
    ma5: Optional[float] = Field(None, description="5日均线")
    timestamp: datetime = Field(default_factory=datetime.now, description="数据时间")

    class Config:
        extra = "allow"  # 允许额外字段


class EconomicData(BaseModel):
    """经济指标数据模型"""

    indicator: str = Field(..., description="指标名称")
    series_id: str = Field(..., description="FRED系列ID")
    value: float = Field(..., description="指标值")
    change: Optional[float] = Field(None, description="变化值")
    change_pct: Optional[float] = Field(None, description="变化百分比")
    timestamp: datetime = Field(..., description="数据时间")
    source: str = Field(default="FRED", description="数据来源")

    class Config:
        extra = "allow"


class NewsItem(BaseModel):
    """新闻条目模型"""

    title: str = Field(..., description="新闻标题")
    summary: str = Field(default="", description="新闻摘要")
    url: str = Field(default="", description="新闻链接")
    source: str = Field(..., description="新闻来源")
    timestamp: datetime = Field(default_factory=datetime.now, description="发布时间")
    impact_tag: Optional[str] = Field(
        None, description="影响标签: #Bullish/#Bearish/#Neutral"
    )
    relevance_score: Optional[float] = Field(None, description="相关性评分")
    full_content: Optional[str] = Field(None, description="完整内容")
    window_type: Optional[str] = Field(
        None, description="时间窗口类型: flash/cycle/trend"
    )

    class Config:
        extra = "allow"


class FlashWindowData(BaseModel):
    """
    Flash Window 数据 (12小时即时窗口)
    用于监控即时市场信号和突发事件
    """

    # VIX 数据
    vix_value: Optional[float] = Field(None, description="VIX当前值")
    vix_prev_close: Optional[float] = Field(None, description="VIX前收盘价")
    vix_change_percent: Optional[float] = Field(None, description="VIX变化百分比")

    # DXY 数据
    dxy_value: Optional[float] = Field(None, description="美元指数当前值")
    dxy_change_percent: Optional[float] = Field(None, description="美元指数变化百分比")

    # US10Y 数据
    us10y_value: Optional[float] = Field(None, description="10年期国债收益率")
    us10y_change_percent: Optional[float] = Field(None, description="10Y变化百分比")

    # 贵金属价格
    gold_price: Optional[float] = Field(None, description="黄金价格")
    gold_change_percent: Optional[float] = Field(None, description="黄金变化百分比")
    silver_price: Optional[float] = Field(None, description="白银价格")
    silver_change_percent: Optional[float] = Field(None, description="白银变化百分比")

    # 即时新闻
    news: List[NewsItem] = Field(default_factory=list, description="12小时内突发新闻")

    # 完整价格数据记录
    price_records: List[Dict[str, Any]] = Field(
        default_factory=list, description="原始价格记录"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now, description="数据采集时间"
    )


class CycleWindowData(BaseModel):
    """
    Cycle Window 数据 (7天周度窗口)
    用于跟踪本周重要经济数据发布
    """

    # 经济指标
    cpi_actual: Optional[float] = Field(None, description="CPI实际值")
    cpi_forecast: Optional[str] = Field(None, description="CPI预期值")
    nfp_actual: Optional[float] = Field(None, description="非农就业实际值")
    nfp_forecast: Optional[str] = Field(None, description="非农就业预期值")
    pce_actual: Optional[float] = Field(None, description="PCE实际值")
    fed_rate: Optional[float] = Field(None, description="联邦基金利率")

    # 本周新闻
    news: List[NewsItem] = Field(default_factory=list, description="本周重要新闻")

    # 经济数据记录
    economic_records: List[Dict[str, Any]] = Field(
        default_factory=list, description="原始经济数据记录"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now, description="数据采集时间"
    )


class TrendWindowData(BaseModel):
    """
    Trend Window 数据 (30天月度窗口)
    用于追踪长期趋势信号
    """

    # 央行购金
    central_bank_buying: Optional[str] = Field(None, description="央行购金情况描述")

    # ETF流向
    etf_flows: Optional[str] = Field(None, description="ETF资金流向描述")

    # 月度新闻
    news: List[NewsItem] = Field(default_factory=list, description="月度趋势新闻")

    timestamp: datetime = Field(
        default_factory=datetime.now, description="数据采集时间"
    )


class MultiWindowData(BaseModel):
    """
    多时间窗口数据聚合
    整合Flash/Cycle/Trend三个窗口的数据
    """

    flash: FlashWindowData = Field(
        default_factory=FlashWindowData, description="即时窗口数据"
    )
    cycle: CycleWindowData = Field(
        default_factory=CycleWindowData, description="周度窗口数据"
    )
    trend: TrendWindowData = Field(
        default_factory=TrendWindowData, description="月度窗口数据"
    )

    # 所有原始记录(用于存储和LLM输入)
    all_records: List[Dict[str, Any]] = Field(
        default_factory=list, description="所有原始记录"
    )

    generated_at: datetime = Field(
        default_factory=datetime.now, description="数据生成时间"
    )

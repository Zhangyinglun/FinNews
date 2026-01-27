"""
分析结果模型
定义规则引擎输出和市场信号结构
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class AlertLevel(str, Enum):
    """警报级别枚举"""

    NORMAL = "normal"  # 正常状态
    WARNING = "warning"  # 警戒状态 (VIX > 20)
    CRITICAL = "critical"  # 紧急状态 (VIX暴涨 > 5%)


class ComexAlertLevel(str, Enum):
    """
    COMEX库存预警级别枚举

    三级预警系统 (白银 Registered 库存):
    - SAFE: >= 40M oz (安全)
    - YELLOW: < 40M oz (警戒线 - 市场紧张)
    - RED: < 30M oz (生死线 - 脱钩风险)
    - SYSTEM_FAILURE: < 20M oz (熔断线 - 系统性风险)
    """

    SAFE = "safe"  # 安全状态
    YELLOW = "yellow"  # 警戒状态 (< 40M oz)
    RED = "red"  # 危险状态 (< 30M oz)
    SYSTEM_FAILURE = "system_failure"  # 系统性风险 (< 20M oz)


class MacroBias(str, Enum):
    """宏观倾向枚举"""

    BULLISH = "利多"  # 利多黄金
    BEARISH = "利空"  # 利空黄金
    NEUTRAL = "中性"  # 中性


class MarketSignal(BaseModel):
    """
    市场信号数据
    由规则引擎生成，用于预处理标记
    """

    # VIX 信号
    vix_value: Optional[float] = Field(None, description="VIX当前值")
    vix_prev_close: Optional[float] = Field(None, description="VIX前收盘价")
    vix_change_percent: Optional[float] = Field(None, description="VIX日变化百分比")
    vix_alert_level: AlertLevel = Field(
        default=AlertLevel.NORMAL, description="VIX警报级别"
    )

    # DXY 信号
    dxy_value: Optional[float] = Field(None, description="美元指数当前值")
    dxy_change_percent: Optional[float] = Field(None, description="DXY日变化百分比")

    # US10Y 信号
    us10y_value: Optional[float] = Field(None, description="10年期国债收益率")
    us10y_change_percent: Optional[float] = Field(None, description="US10Y日变化百分比")

    # 贵金属
    gold_price: Optional[float] = Field(None, description="黄金价格")
    gold_change_percent: Optional[float] = Field(None, description="黄金日变化百分比")
    silver_price: Optional[float] = Field(None, description="白银价格")
    silver_change_percent: Optional[float] = Field(None, description="白银日变化百分比")

    # 综合判断
    macro_bias: MacroBias = Field(default=MacroBias.NEUTRAL, description="宏观倾向判断")
    sentiment_score: float = Field(default=0.0, description="情感评分 (-1.0到1.0)")
    price_source_note: Optional[str] = Field(
        None, description="价格数据来源备注 (如: 含缓存数据)"
    )

    # 警报信息
    alert_messages: List[str] = Field(default_factory=list, description="警报消息列表")
    is_urgent: bool = Field(default=False, description="是否触发紧急警报")

    # 时间戳
    generated_at: datetime = Field(
        default_factory=datetime.now, description="信号生成时间"
    )

    def get_email_subject_tag(self) -> str:
        """
        根据警报状态生成邮件标题标签

        Returns:
            邮件标题前缀
        """
        if self.is_urgent:
            return "【紧急警报】"
        elif self.vix_alert_level == AlertLevel.WARNING:
            return "【市场警戒】"
        else:
            return "【黄金日报】"

    def get_signal_summary(self) -> str:
        """
        生成信号摘要文本

        Returns:
            信号摘要字符串
        """
        parts = []

        if self.vix_value is not None:
            vix_emoji = (
                "🔴"
                if self.is_urgent
                else ("⚠️" if self.vix_alert_level == AlertLevel.WARNING else "🟢")
            )
            parts.append(f"VIX {self.vix_value:.1f} {vix_emoji}")

        if self.macro_bias != MacroBias.NEUTRAL:
            bias_emoji = "📈" if self.macro_bias == MacroBias.BULLISH else "📉"
            parts.append(f"{bias_emoji} {self.macro_bias.value}")

        if self.gold_change_percent is not None:
            gold_emoji = "🥇" if self.gold_change_percent > 0 else "🥇"
            parts.append(f"黄金 {self.gold_change_percent:+.2f}%")

        return " | ".join(parts) if parts else "市场平稳"


class AnalysisResult(BaseModel):
    """
    完整分析结果
    包含市场信号和LLM生成的内容
    """

    # 市场信号
    signal: MarketSignal = Field(..., description="规则引擎生成的市场信号")

    # 邮件内容
    email_subject: str = Field(default="", description="邮件标题")
    email_html_body: str = Field(default="", description="邮件HTML正文")

    # 统计信息
    total_news_count: int = Field(default=0, description="新闻总数")
    flash_news_count: int = Field(default=0, description="Flash窗口新闻数")
    cycle_news_count: int = Field(default=0, description="Cycle窗口新闻数")
    trend_news_count: int = Field(default=0, description="Trend窗口新闻数")

    # 状态
    success: bool = Field(default=False, description="分析是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")

    # 时间戳
    generated_at: datetime = Field(
        default_factory=datetime.now, description="分析完成时间"
    )


class ComexSignal(BaseModel):
    """
    COMEX库存信号数据
    用于邮件模板和规则引擎输出
    """

    # 白银库存数据
    silver_registered: Optional[float] = Field(
        None, description="白银Registered库存(盎司)"
    )
    silver_registered_million: Optional[float] = Field(
        None, description="白银Registered库存(百万盎司)"
    )
    silver_total: Optional[float] = Field(None, description="白银总库存(盎司)")
    silver_alert_level: ComexAlertLevel = Field(
        default=ComexAlertLevel.SAFE, description="白银预警级别"
    )
    silver_alert_message: str = Field(default="", description="白银预警消息")
    silver_recommendation: str = Field(default="", description="白银投资建议")
    silver_daily_change_pct: Optional[float] = Field(
        None, description="白银日变化百分比"
    )
    silver_weekly_change_pct: Optional[float] = Field(
        None, description="白银周变化百分比"
    )

    # 黄金库存数据
    gold_registered: Optional[float] = Field(
        None, description="黄金Registered库存(盎司)"
    )
    gold_registered_million: Optional[float] = Field(
        None, description="黄金Registered库存(百万盎司)"
    )
    gold_total: Optional[float] = Field(None, description="黄金总库存(盎司)")
    gold_alert_level: ComexAlertLevel = Field(
        default=ComexAlertLevel.SAFE, description="黄金预警级别"
    )
    gold_alert_message: str = Field(default="", description="黄金预警消息")
    gold_recommendation: str = Field(default="", description="黄金投资建议")
    gold_daily_change_pct: Optional[float] = Field(None, description="黄金日变化百分比")
    gold_weekly_change_pct: Optional[float] = Field(
        None, description="黄金周变化百分比"
    )

    # 图表 base64
    silver_chart_base64: Optional[str] = Field(None, description="白银趋势图 base64")
    gold_chart_base64: Optional[str] = Field(None, description="黄金趋势图 base64")

    # 报告日期
    report_date: Optional[datetime] = Field(None, description="CME报告日期")

    # 是否有紧急情况
    has_emergency: bool = Field(default=False, description="是否存在紧急警报")

    # 时间戳
    generated_at: datetime = Field(
        default_factory=datetime.now, description="信号生成时间"
    )

    def get_worst_alert_level(self) -> ComexAlertLevel:
        """
        获取最严重的预警级别

        Returns:
            最严重的预警级别
        """
        levels = [self.silver_alert_level, self.gold_alert_level]
        priority = {
            ComexAlertLevel.SYSTEM_FAILURE: 4,
            ComexAlertLevel.RED: 3,
            ComexAlertLevel.YELLOW: 2,
            ComexAlertLevel.SAFE: 1,
        }
        return max(levels, key=lambda x: priority.get(x, 0))

    def get_alert_emoji(self) -> str:
        """
        获取最严重预警级别对应的emoji

        Returns:
            预警emoji
        """
        worst = self.get_worst_alert_level()
        emoji_map = {
            ComexAlertLevel.SYSTEM_FAILURE: "⚫",
            ComexAlertLevel.RED: "🔴",
            ComexAlertLevel.YELLOW: "🟡",
            ComexAlertLevel.SAFE: "🟢",
        }
        return emoji_map.get(worst, "")

    def get_summary(self) -> str:
        """
        生成COMEX库存摘要

        Returns:
            摘要字符串
        """
        parts = []
        if self.silver_registered_million is not None:
            emoji = self.get_alert_emoji()
            parts.append(f"COMEX白银 {self.silver_registered_million}M oz {emoji}")
        if self.gold_registered_million is not None:
            parts.append(f"黄金 {self.gold_registered_million}M oz")
        return " | ".join(parts) if parts else "COMEX数据暂无"

"""
Perplexity Sonar 新闻爬虫
通过 OpenRouter 调用 Sonar 模型搜索新闻，支持多时间窗口
"""

import time
from typing import Any, Dict, List, Literal
from urllib.parse import urlparse

from .base_scraper import BaseScraper
from config.config import Config
from utils.sonar_client import SonarClient, SonarError


# 时间窗口类型
WindowType = Literal["flash", "cycle", "trend"]


class SonarScraper(BaseScraper):
    """
    Perplexity Sonar 新闻爬虫

    通过 OpenRouter 调用 Perplexity Sonar 模型进行新闻搜索，
    复用 Tavily 的关键词池，支持 Flash/Cycle/Trend 三种时间窗口。
    """

    def __init__(self) -> None:
        super().__init__("Sonar")

        # 检查 API 密钥
        if not Config.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY 未配置，无法使用 Sonar 爬虫")

        self.sonar_model = getattr(Config, "SONAR_MODEL", "perplexity/sonar")

        # 初始化 Sonar 客户端
        self.client = SonarClient(
            api_key=Config.OPENROUTER_API_KEY,
            model=self.sonar_model,
            timeout=getattr(Config, "OPENROUTER_TIMEOUT", 60),
            max_retries=getattr(Config, "OPENROUTER_MAX_RETRIES", 3),
            http_referer=getattr(Config, "OPENROUTER_HTTP_REFERER", None),
            x_title=getattr(Config, "OPENROUTER_X_TITLE", None),
        )

        # 复用 Tavily 关键词池
        self.flash_queries = Config.TAVILY_FLASH_QUERIES
        self.cycle_queries = Config.TAVILY_CYCLE_QUERIES
        self.trend_queries = Config.TAVILY_TREND_QUERIES

    def fetch(self) -> List[Dict[str, Any]]:
        """
        执行所有时间窗口的查询并聚合结果

        Returns:
            新闻数据列表 (带 window_type 标记)
        """
        all_results: List[Dict[str, Any]] = []

        # Flash Window (即时新闻)
        flash_results = self._fetch_window(
            queries=self.flash_queries,
            window_type="flash",
        )
        all_results.extend(flash_results)

        # Cycle Window (周度新闻)
        cycle_results = self._fetch_window(
            queries=self.cycle_queries,
            window_type="cycle",
        )
        all_results.extend(cycle_results)

        # Trend Window (月度趋势)
        trend_results = self._fetch_window(
            queries=self.trend_queries,
            window_type="trend",
        )
        all_results.extend(trend_results)

        # 过滤并返回结果
        all_results = self._filter_recent_records(
            all_results,
            Config.FLASH_WINDOW_HOURS,
            allow_fallback=True,
            fallback_note="Sonar 搜索结果",
        )

        self.logger.info(
            f"Sonar采集完成 | Flash={len(flash_results)} "
            f"Cycle={len(cycle_results)} Trend={len(trend_results)}"
        )

        return all_results

    @staticmethod
    def _is_trusted_domain(url: str, trusted_domains: List[str]) -> bool:
        hostname = urlparse(url).hostname or ""
        domain = hostname.lower()
        if not domain:
            return False
        normalized_domains = [d.lower() for d in trusted_domains if d]
        return any(
            domain == trusted or domain.endswith("." + trusted)
            for trusted in normalized_domains
        )

    def _fetch_window(
        self,
        queries: List[str],
        window_type: WindowType,
    ) -> List[Dict[str, Any]]:
        """
        执行单个时间窗口的查询

        Args:
            queries: 查询关键词列表
            window_type: 窗口类型标记 ("flash", "cycle", "trend")

        Returns:
            新闻数据列表
        """
        results: List[Dict[str, Any]] = []

        for query in queries:
            try:
                self.logger.debug(f"[{window_type}] Sonar 查询: {query[:50]}...")

                # 调用 Sonar 搜索
                response = self.client.search(query)
                citations_count = len(response.citations)

                # 解析 citations 为新闻记录
                if not response.citations:
                    self.logger.debug(f"[{window_type}] 无引用结果: {query[:30]}...")
                    continue

                for citation in response.citations:
                    # 跳过无效 URL
                    if not citation.url:
                        continue
                    if Config.SONAR_USE_TRUSTED_DOMAINS and Config.TRUSTED_DOMAINS:
                        if not self._is_trusted_domain(
                            citation.url, Config.TRUSTED_DOMAINS
                        ):
                            self.logger.debug(
                                f"[{window_type}] 过滤不可信引用: {citation.url}"
                            )
                            continue

                    record = self._create_base_record(
                        title=citation.title
                        or self._extract_title_from_url(citation.url),
                        summary=response.answer,  # 使用 Sonar 的摘要
                        url=citation.url,
                        fallback_allowed=True,
                    )
                    record["window_type"] = window_type
                    record["query"] = query
                    record["sonar_answer"] = response.answer  # 保留完整回答
                    record["sonar_citations_count"] = citations_count
                    record["sonar_model"] = self.sonar_model
                    results.append(record)

                # 避免速率限制
                time.sleep(0.5)

            except SonarError as e:
                self.logger.error(
                    f"[{window_type}] Sonar 查询失败 '{query[:30]}...': {e}",
                    exc_info=True,
                )
                continue
            except Exception as e:
                self.logger.error(
                    f"[{window_type}] 查询异常 '{query[:30]}...': {e}",
                    exc_info=True,
                )
                continue

        return results

    def fetch_by_window(self, window_type: WindowType) -> List[Dict[str, Any]]:
        """
        仅获取指定时间窗口的数据

        Args:
            window_type: 窗口类型 ("flash", "cycle", "trend")

        Returns:
            新闻数据列表
        """
        if window_type == "flash":
            return self._fetch_window(self.flash_queries, "flash")
        elif window_type == "cycle":
            return self._fetch_window(self.cycle_queries, "cycle")
        elif window_type == "trend":
            return self._fetch_window(self.trend_queries, "trend")
        else:
            self.logger.error(f"未知窗口类型: {window_type}")
            return []

    @staticmethod
    def _extract_title_from_url(url: str) -> str:
        """
        从 URL 中提取标题 (备用方案)

        Args:
            url: 新闻链接

        Returns:
            提取的标题或原始 URL
        """
        try:
            # 移除协议和参数
            path = url.split("://")[-1].split("?")[0]
            # 取最后一个路径段
            slug = path.rstrip("/").split("/")[-1]
            # 替换连字符为空格
            title = slug.replace("-", " ").replace("_", " ")
            return title.title() if title else url
        except Exception:
            return url

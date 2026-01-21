"""
Full Content Fetcher - 完整新闻内容抓取
从URL抓取完整网页正文
"""

import time
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from utils.logger import get_logger


class ContentFetcher:
    """完整内容抓取器"""

    def __init__(self, max_retries: int = 3, timeout: int = 15):
        """
        初始化内容抓取器

        Args:
            max_retries: 最大重试次数
            timeout: 请求超时时间(秒)
        """
        self.logger = get_logger("ContentFetcher")
        self.timeout = timeout

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests或beautifulsoup4未安装")

        # 创建带重试的session
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 模拟浏览器请求头
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            }
        )

    def fetch_full_content(self, url: str) -> Optional[str]:
        """
        抓取完整网页正文

        Args:
            url: 新闻URL

        Returns:
            提取的正文内容，失败返回None
        """
        try:
            domain = urlparse(url).netloc
            self.logger.debug(f"抓取完整内容: {domain}")

            # 发送请求
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            # 检查响应内容是否为二进制乱码
            if (
                not response.text
                or len(response.text.encode("utf-8", errors="ignore")) < 100
            ):
                self.logger.warning(f"响应内容异常: {url}")
                return None

            # 尝试检测编码
            if response.encoding is None or response.encoding.lower() == "iso-8859-1":
                response.encoding = response.apparent_encoding

            # 验证文本内容是否可读
            try:
                text_content = response.text
                # 检查是否包含大量不可打印字符（更严格的检查）
                sample = (
                    text_content[:2000] if len(text_content) >= 2000 else text_content
                )
                if not sample:
                    return None

                # 计算可打印字符比例
                printable_count = sum(
                    1 for c in sample if c.isprintable() or c.isspace()
                )
                printable_ratio = printable_count / len(sample)

                # 检查是否有过多的控制字符或高位字符
                control_count = sum(
                    1 for c in sample if ord(c) < 32 and c not in "\n\r\t"
                )
                high_byte_count = sum(
                    1 for c in sample if ord(c) > 127 and not c.isprintable()
                )

                if (
                    printable_ratio < 0.7
                    or control_count > len(sample) * 0.1
                    or high_byte_count > len(sample) * 0.3
                ):
                    self.logger.warning(
                        f"检测到二进制/乱码内容，跳过: {url} (可打印比例: {printable_ratio:.2f})"
                    )
                    return None
            except Exception as e:
                self.logger.warning(f"文本解码失败: {url} - {e}")
                return None

            # 解析HTML
            soup = BeautifulSoup(text_content, "lxml")

            # 移除脚本和样式
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            # 根据不同网站选择内容提取策略
            content = self._extract_content(soup, domain)

            if content:
                # 清理特殊字符和零宽度字符
                content = self._clean_text(content)
                return content[:5000]  # 限制最大长度5000字符

            return None

        except requests.exceptions.Timeout:
            self.logger.warning(f"请求超时: {url}")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"请求失败: {url} - {e}")
            return None
        except Exception as e:
            self.logger.error(f"内容提取失败: {url} - {e}")
            return None

    def _clean_text(self, text: str) -> str:
        """
        清理文本中的特殊字符和零宽度字符

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        # 移除零宽度字符（Zero-Width Characters）
        # U+200B: Zero Width Space
        # U+200C: Zero Width Non-Joiner
        # U+200D: Zero Width Joiner
        # U+FEFF: Zero Width No-Break Space (BOM)
        # U+2060: Word Joiner
        # U+180E: Mongolian Vowel Separator
        zero_width_chars = ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060", "\u180e"]
        for char in zero_width_chars:
            text = text.replace(char, "")

        # 移除其他不可见字符
        text = re.sub(r"[\u202a-\u202e]", "", text)  # 双向文本控制字符

        # 标准化空白字符
        text = " ".join(text.split())

        # 移除多余的换行符
        text = re.sub(r"\n\s*\n", "\n", text)

        return text.strip()

    def _extract_content(self, soup: BeautifulSoup, domain: str) -> Optional[str]:
        """
        根据不同网站选择内容提取策略

        Args:
            soup: BeautifulSoup对象
            domain: 域名

        Returns:
            提取的正文
        """
        # 针对特定网站的规则
        selectors = self._get_selectors_for_domain(domain)

        # 尝试使用特定选择器
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                text = " ".join([elem.get_text(strip=True) for elem in elements])
                if len(text) > 200:  # 至少200字符才算有效内容
                    return text

        # 通用策略：查找文章主体
        article_tags = soup.find_all(
            ["article", "div"],
            class_=lambda x: x
            and any(
                keyword in x.lower()
                for keyword in [
                    "article",
                    "content",
                    "story",
                    "post",
                    "entry",
                    "body",
                    "main",
                ]
            ),
        )

        if article_tags:
            # 选择最长的内容块
            longest = max(
                article_tags, key=lambda x: len(x.get_text(strip=True)), default=None
            )
            if longest:
                return longest.get_text(separator=" ", strip=True)

        # 最后的通用策略：提取所有段落
        paragraphs = soup.find_all("p")
        if paragraphs:
            text = " ".join([p.get_text(strip=True) for p in paragraphs])
            if len(text) > 200:
                return text

        return None

    def _get_selectors_for_domain(self, domain: str) -> list:
        """
        获取特定网站的CSS选择器

        Args:
            domain: 域名

        Returns:
            CSS选择器列表
        """
        # 针对常见财经网站的选择器
        domain_rules = {
            "reuters.com": ["article.article-body", "div.StandardArticleBody_body"],
            "bloomberg.com": ["div.body-content", "article div.body-copy"],
            "cnbc.com": ["div.ArticleBody-articleBody", "div.group"],
            "wsj.com": ["article.article", "div.article-content"],
            "marketwatch.com": [
                "div.article__body",
                "div.article__content",
            ],
            "kitco.com": ["div.article-content", "div.entry-content"],
            "fxstreet.com": ["div.fxs_article_content", "article.fxs_article"],
            "goldseek.com": ["div.article-content", "article"],
            "mining.com": ["div.article-body", "article.post"],
        }

        # 查找匹配的域名规则
        for key, selectors in domain_rules.items():
            if key in domain:
                return selectors

        # 默认通用选择器
        return [
            "article",
            "div.content",
            "div.article",
            "div.main-content",
            "main",
        ]

    def enrich_articles(self, articles: list) -> list:
        """
        为文章列表批量添加完整内容

        Args:
            articles: 文章列表（包含url字段）

        Returns:
            添加了full_content字段的文章列表
        """
        enriched = []
        total = len(articles)

        for idx, article in enumerate(articles, 1):
            url = article.get("url", "")

            if not url:
                enriched.append(article)
                continue

            self.logger.info(f"抓取 [{idx}/{total}]: {url[:60]}...")

            # 抓取完整内容
            full_content = self.fetch_full_content(url)

            # 添加到文章数据
            article_copy = article.copy()
            if full_content:
                article_copy["full_content"] = full_content
                article_copy["content_length"] = len(full_content)
                self.logger.debug(f"成功: {len(full_content)} 字符")
            else:
                article_copy["full_content"] = article.get("summary", "")
                article_copy["content_length"] = 0
                self.logger.debug("失败: 使用摘要代替")

            enriched.append(article_copy)

            # 礼貌延迟（避免被封IP）
            time.sleep(1)

        success_count = sum(1 for a in enriched if a.get("content_length", 0) > 0)
        self.logger.info(f"完整内容抓取完成: {success_count}/{total} 成功")

        return enriched

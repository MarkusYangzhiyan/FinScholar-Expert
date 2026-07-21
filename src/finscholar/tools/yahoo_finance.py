"""定义 Agent 可调用的 Yahoo_Finance_Tool。"""

from typing import ClassVar, Protocol

from finscholar.schemas.yahoo_finance import (
    YahooFinanceHistoryInput,
    YahooFinanceHistoryOutput,
)


class YahooHistoryClient(Protocol):
    """
    定义 Tool 需要的 Yahoo Client 能力。
    这里没有真正请求 yfinance，它只声明：
        方法名称：get_history
        输入类型：YahooFinanceHistoryInput
        输出类型：YahooFinanceHistoryOutput
        异步方法：是
    """

    async def get_history(
        self,
        query: YahooFinanceHistoryInput,
    ) -> YahooFinanceHistoryOutput:
        """获取结构化历史行情。"""
        ...


class YahooFinanceTool:
    """向 Agent 暴露 Yahoo Finance 结构化行情能力。"""

    name: ClassVar[str] = "Yahoo_Finance_Tool"
    description: ClassVar[str] = (
        "获取股票、ETF、指数等金融标的的结构化历史行情；不用于通用财经新闻搜索。"
    )
    args_schema: ClassVar[type[YahooFinanceHistoryInput]] = YahooFinanceHistoryInput
    output_schema: ClassVar[type[YahooFinanceHistoryOutput]] = YahooFinanceHistoryOutput

    def __init__(self, client: YahooHistoryClient) -> None:
        self._client = client

    async def get_history(
        self,
        query: YahooFinanceHistoryInput,
    ) -> YahooFinanceHistoryOutput:
        """调用 Client 获取结构化历史行情。"""

        return await self._client.get_history(query)


__all__ = [
    "YahooFinanceTool",
    "YahooHistoryClient",
]

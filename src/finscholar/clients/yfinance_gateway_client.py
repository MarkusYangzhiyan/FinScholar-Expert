"""使用 yfinance 获取 Yahoo Finance 原始历史行情。"""

from collections.abc import Callable
from typing import Protocol, TypeAlias, cast

import pandas as pd
import yfinance as yf

from finscholar.clients.yahoo_finance_client import YahooHistoryRawResult
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput


# 这里只声明接口，具体代码由实际对象提供
class YahooTicker(Protocol):
    """定义 Gateway 使用的最小 yf.Ticker 接口。"""

    def history(
        self,
        *,
        period: str,
        interval: str,
        auto_adjust: bool,
        actions: bool,
        timeout: float,
        raise_errors: bool,
    ) -> pd.DataFrame:
        """获取原始历史行情。"""
        ...

    def get_history_metadata(self) -> dict[str, object]:
        """获取历史行情元数据。"""
        ...


# 类型别名: 符合这个类型的对象必须是可以调用的，接收一个str，返回一个 YahooTicker
YahooTickerFactory: TypeAlias = Callable[[str], YahooTicker]


def _create_yfinance_ticker(symbol: str) -> YahooTicker:
    """创建生产环境使用的 yf.Ticker。"""

    return cast(YahooTicker, yf.Ticker(symbol))


class YFinanceHistoryGateway:
    """通过 yfinance 获取原始 Yahoo 历史行情。"""

    def __init__(
        self,
        *,
        ticker_factory: YahooTickerFactory = _create_yfinance_ticker,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._ticker_factory = ticker_factory
        self._timeout_seconds = timeout_seconds

    def fetch_history(
        self,
        query: YahooFinanceHistoryInput,
    ) -> YahooHistoryRawResult:
        """将 FinScholar 查询参数转换成 yfinance 调用。"""

        ticker = self._ticker_factory(query.symbol)

        frame = ticker.history(
            period=query.period,
            interval=query.interval,
            auto_adjust=query.auto_adjust,
            actions=False,
            timeout=self._timeout_seconds,
            raise_errors=True,
        )

        metadata = ticker.get_history_metadata()
        currency_value = metadata.get("currency")
        currency = currency_value if isinstance(currency_value, str) else None

        return YahooHistoryRawResult(
            frame=frame,
            currency=currency,
        )


__all__ = ["YFinanceHistoryGateway"]

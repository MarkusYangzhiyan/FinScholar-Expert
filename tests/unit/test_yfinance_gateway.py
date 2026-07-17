"""测试真实 yfinance Gateway 的参数转换。"""

import pandas as pd

from finscholar.clients.yfinance_gateway_client import YFinanceHistoryGateway
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput
from finscholar.clients.yahoo_finance_client import YahooHistoryRawResult, YahooFinanceClient

class FakeTicker:
    """模拟 yf.Ticker，不访问网络。"""

    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame
        self.history_calls: list[dict[str, object]] = []

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
        self.history_calls.append(
            {
                "period": period,
                "interval": interval,
                "auto_adjust": auto_adjust,
                "actions": actions,
                "timeout": timeout,
                "raise_errors": raise_errors,
            }
        )

        return self._frame

    def get_history_metadata(self) -> dict[str, object]:
        return {"currency": "USD"}


class FakeTickerFactory:
    """记录 Gateway 创建了哪个股票的 Ticker。"""

    def __init__(self, ticker: FakeTicker) -> None:
        self._ticker = ticker
        self.created_symbols: list[str] = []

    def __call__(self, symbol: str) -> FakeTicker:
        self.created_symbols.append(symbol)
        return self._ticker


def test_gateway_forwards_history_query_to_yfinance() -> None:
    """Gateway 应把结构化查询转换成 yfinance 调用。"""

    frame = pd.DataFrame(
        {"Close": [407.76]},
        index=pd.DatetimeIndex(
            ["2026-07-10"],
            name="Date",
        ),
    )
    ticker = FakeTicker(frame)
    ticker_factory = FakeTickerFactory(ticker)
    gateway = YFinanceHistoryGateway(
        ticker_factory=ticker_factory,
        timeout_seconds=10.0,
    )
    query = YahooFinanceHistoryInput(
        symbol=" tsla ",
        period="1mo",
        interval="1d",
        auto_adjust=False,
    )

    result = gateway.fetch_history(query)

    assert ticker_factory.created_symbols == ["TSLA"]
    assert ticker.history_calls == [
        {
            "period": "1mo",
            "interval": "1d",
            "auto_adjust": False,
            "actions": False,
            "timeout": 10.0,
            "raise_errors": True,
        }
    ]

    pd.testing.assert_frame_equal(result.frame, frame)
    assert result.currency == "USD"

class EmptyYahooHistoryGateway:
    """模拟 Yahoo 返回空历史行情。"""

    def fetch_history(
        self,
        query: YahooFinanceHistoryInput,
    ) -> YahooHistoryRawResult:
        return YahooHistoryRawResult(
            frame=pd.DataFrame(),
            currency="USD",
        )


async def test_client_returns_empty_data_points_for_empty_history() -> None:
    """Yahoo 返回空行情时，应明确返回空数据点列表。"""

    client = YahooFinanceClient(
        gateway=EmptyYahooHistoryGateway()
    )
    query = YahooFinanceHistoryInput(
        symbol="TSLA",
        period="1mo",
        interval="1d",
    )

    result = await client.get_history(query)

    assert result.query == query
    assert result.data_points == []
    assert result.evidence.source_name == "Yahoo Finance"
    assert result.evidence.content
    assert result.evidence.content_hash
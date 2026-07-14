"""测试 Yahoo Finance 客户端。"""

from decimal import Decimal

import pandas as pd

from finscholar.clients.yahoo_finance import YahooFinanceClient
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput


class FakeYahooHistoryGateway:
    """返回固定行情，不访问真实网络。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def fetch_history(
        self,
        *,
        symbol: str,
        period: str,
        interval: str,
        auto_adjust: bool,
    ) -> tuple[pd.DataFrame, str | None]:
        self.calls.append(
            {
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "auto_adjust": auto_adjust,
            }
        )

        history = pd.DataFrame(
            {"Close": [407.76]},
            index=pd.DatetimeIndex(
                ["2026-07-10"],
                name="Date",
            ),
        )

        return history, "USD"


async def test_client_converts_yahoo_close_price() -> None:
    """客户端应把 Yahoo 收盘价转换成标准化金融数据。"""

    gateway = FakeYahooHistoryGateway()
    client = YahooFinanceClient(gateway=gateway)
    query = YahooFinanceHistoryInput(
        symbol=" tsla ",
        period="1mo",
        interval="1d",
    )

    result = await client.get_history(query)

    assert gateway.calls == [
        {
            "symbol": "TSLA",
            "period": "1mo",
            "interval": "1d",
            "auto_adjust": False,
        }
    ]
    assert result.query == query
    assert result.evidence.source_type == "market_data"
    assert result.evidence.source_name == "Yahoo Finance"

    assert len(result.data_points) == 1

    close_price = result.data_points[0]

    assert close_price.symbol == "TSLA"
    assert close_price.metric_name == "close_price"
    assert close_price.value == Decimal("407.76")
    assert close_price.currency == "USD"
    assert close_price.unit == "per_share"
    assert close_price.evidence_id == result.evidence.evidence_id
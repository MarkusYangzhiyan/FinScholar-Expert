"""测试 Yahoo_Finance_Tool。"""

import pandas as pd

from finscholar.clients.yahoo_finance_client import (
    YahooFinanceClient,
    YahooHistoryRawResult,
)
from finscholar.schemas.yahoo_finance import (
    YahooFinanceHistoryInput,
    YahooFinanceHistoryOutput,
)
from finscholar.tools.yahoo_finance import YahooFinanceTool


class FakeYahooHistoryGateway:
    """为 Tool 测试提供固定 Yahoo 行情。"""

    def fetch_history(
        self,
        query: YahooFinanceHistoryInput,
    ) -> YahooHistoryRawResult:
        frame = pd.DataFrame(
            {"Close": [407.76]},
            index=pd.DatetimeIndex(
                ["2026-07-10"],
                name="Date",
            ),
        )

        return YahooHistoryRawResult(
            frame=frame,
            currency="USD",
        )


async def test_yahoo_finance_tool_returns_history_output() -> None:
    """Tool 应调用 Client 并返回标准历史行情结果。"""

    client = YahooFinanceClient(gateway=FakeYahooHistoryGateway())
    tool = YahooFinanceTool(client=client)
    query = YahooFinanceHistoryInput(
        symbol="TSLA",
        period="1mo",
        interval="1d",
    )

    result = await tool.get_history(query)

    assert tool.name == "Yahoo_Finance_Tool"
    assert tool.args_schema is YahooFinanceHistoryInput
    assert tool.output_schema is YahooFinanceHistoryOutput

    assert result.query == query
    assert result.evidence.source_name == "Yahoo Finance"
    assert len(result.data_points) == 1
    assert result.data_points[0].metric_name == "close_price"

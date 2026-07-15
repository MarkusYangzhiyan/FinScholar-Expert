"""测试 Agent Graph 的 Yahoo Finance 主链路。"""

from decimal import Decimal

import pandas as pd

from finscholar.clients.yahoo_finance import (
    YahooFinanceClient,
    YahooHistoryRawResult,
)
from finscholar.graph.agent_graph import (
    build_agent_graph,
    invoke_agent_graph,
)
from finscholar.schemas.yahoo_finance import (
    YahooFinanceHistoryInput,
)
from finscholar.tools.yahoo_finance import YahooFinanceTool


class FakeYahooHistoryGateway:
    """返回固定行情，不访问真实网络。"""

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


async def test_agent_graph_routes_to_yahoo_finance() -> None:
    """Router 应进入 Yahoo Node 并返回结构化行情。"""

    client = YahooFinanceClient(
        gateway=FakeYahooHistoryGateway()
    )
    tool = YahooFinanceTool(client=client)
    graph = build_agent_graph(
        yahoo_finance_tool=tool,
    )

    result = await invoke_agent_graph(
        compiled_graph=graph,
        user_query="查询 TSLA 历史行情",
        yahoo_finance_input={
            "symbol": "TSLA",
            "period": "1mo",
            "interval": "1d",
        },
    )

    assert (
        result["router_selected_tool"]
        == "Yahoo_Finance_Tool"
    )

    output = result["yahoo_finance_output"]

    assert output is not None
    assert output.query.symbol == "TSLA"
    assert output.data_points[0].value == Decimal("407.76")
    assert result["yahoo_finance_error_type"] is None
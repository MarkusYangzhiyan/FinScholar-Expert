"""测试 Agent Graph 的 Yahoo Finance 主链路。"""

from decimal import Decimal

import pandas as pd

from finscholar.clients.yahoo_finance_client import (
    YahooFinanceClient,
    YahooHistoryRawResult,
)
from finscholar.graph.agent_graph import build_agent_graph, invoke_agent_graph
from finscholar.schemas.router import RouterDecision
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput
from finscholar.tools.yahoo_finance import YahooFinanceTool
from finscholar.schemas.calculator import CalculatorInput

class FakeRouterClient:
    """返回固定的 Yahoo Finance 路由决策。"""

    def __init__(self) -> None:
        self.received_query: str | None = None

    async def route(self, user_query: str) -> RouterDecision:
        self.received_query = user_query

        return RouterDecision(
            selected_tool="Yahoo_Finance_Tool",
            reason="用户要求查询历史行情",
            yahoo_finance_input=YahooFinanceHistoryInput(
                symbol="TSLA",
                period="1mo",
                interval="1d",
            ),
        )

class FakeCalculatorRouterClient:
    """返回固定的 Calculator 路由决策。"""

    def __init__(self) -> None:
        self.received_query: str | None = None

    async def route(
        self,
        user_query: str,
    ) -> RouterDecision:
        self.received_query = user_query

        return RouterDecision(
            selected_tool="Math_Calculator",
            reason="用户要求执行数学计算",
            calculator_input=CalculatorInput(
                expression="1 + 2 * 3",
            ),
        )

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

    router_client = FakeRouterClient()
    client = YahooFinanceClient(
        gateway=FakeYahooHistoryGateway(),
    )
    tool = YahooFinanceTool(client=client)
    graph = build_agent_graph(
        router_client=router_client,
        yahoo_finance_tool=tool,
    )

    result = await invoke_agent_graph(
        compiled_graph=graph,
        user_query="查询 TSLA 历史行情",
    )

    assert router_client.received_query == "查询 TSLA 历史行情"
    assert result["router_selected_tool"] == "Yahoo_Finance_Tool"

    output = result["yahoo_finance_output"]

    assert output is not None
    assert output.query.symbol == "TSLA"
    assert output.data_points[0].value == Decimal("407.76")
    assert result["yahoo_finance_error_type"] is None


async def test_agent_graph_routes_to_calculator() -> None:
    """Router 应进入 Calculator Node 并返回结构化计算结果。"""

    router_client = FakeCalculatorRouterClient()

    yahoo_client = YahooFinanceClient(
        gateway=FakeYahooHistoryGateway(),
    )
    yahoo_tool = YahooFinanceTool(
        client=yahoo_client,
    )

    graph = build_agent_graph(
        router_client=router_client,
        yahoo_finance_tool=yahoo_tool,
    )

    result = await invoke_agent_graph(
        compiled_graph=graph,
        user_query="计算 1 + 2 * 3",
    )

    assert router_client.received_query == "计算 1 + 2 * 3"
    assert result["router_selected_tool"] == "Math_Calculator"

    output = result["calculator_output"]

    assert output is not None
    assert output.result == Decimal("7")
    assert result["calculator_error_type"] is None
    assert result["yahoo_finance_output"] is None
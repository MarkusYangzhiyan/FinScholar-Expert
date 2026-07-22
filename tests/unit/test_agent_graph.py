"""测试主 Agent Graph 的批次工具调用链路。"""

from decimal import Decimal

import pandas as pd

from finscholar.clients.yahoo_finance_client import (
    YahooFinanceClient,
    YahooHistoryRawResult,
)
from finscholar.graph.agent_graph import build_agent_graph, invoke_agent_graph
from finscholar.schemas.calculator import CalculatorInput
from finscholar.schemas.schemas_router import (
    RouterAction,
    RouterBatch,
    RouterContext,
)
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput
from finscholar.tools.yahoo_finance import YahooFinanceTool


class FakeRouterClient:
    """第一轮调用工具，第二轮结束。"""

    def __init__(self) -> None:
        self.contexts: list[RouterContext] = []

    async def route(self, context: RouterContext) -> RouterBatch:
        self.contexts.append(context)

        if context.action_results:
            return RouterBatch(
                status="finalize",
                reason="工具结果已经足够",
            )

        return RouterBatch(
            status="execute",
            reason="行情查询和计算互不依赖，可以并行执行",
            actions=[
                RouterAction(
                    selected_tool="Yahoo_Finance_Tool",
                    reason="用户要求查询行情",
                    yahoo_finance_input=YahooFinanceHistoryInput(
                        symbol="TSLA",
                        period="1mo",
                        interval="1d",
                    ),
                ),
                RouterAction(
                    selected_tool="Math_Calculator",
                    reason="用户要求执行计算",
                    calculator_input=CalculatorInput(
                        expression="1 + 2 * 3",
                    ),
                ),
            ],
        )


class FakeYahooHistoryGateway:
    """返回固定行情，不访问网络。"""

    def fetch_history(
        self,
        query: YahooFinanceHistoryInput,
    ) -> YahooHistoryRawResult:
        frame = pd.DataFrame(
            {"Close": [407.76]},
            index=pd.DatetimeIndex(["2026-07-10"], name="Date"),
        )
        return YahooHistoryRawResult(
            frame=frame,
            currency="USD",
        )


async def test_agent_graph_executes_action_batch() -> None:
    """主图应并行执行工具，并把结果交回 Router。"""

    router_client = FakeRouterClient()
    yahoo_tool = YahooFinanceTool(
        client=YahooFinanceClient(
            gateway=FakeYahooHistoryGateway(),
        )
    )
    graph = build_agent_graph(
        router_client=router_client,
        yahoo_finance_tool=yahoo_tool,
    )

    state = await invoke_agent_graph(
        compiled_graph=graph,
        user_query="查询 TSLA 行情，并计算 1 + 2 * 3",
    )

    assert [context.round_number for context in router_client.contexts] == [1, 2]
    assert len(router_client.contexts[1].action_results) == 2
    assert state["router_batch"].status == "finalize"

    results = {
        result.action.selected_tool: result
        for result in state["router_action_results"]
    }

    calculator_result = results["Math_Calculator"]
    assert calculator_result.status == "success"
    assert calculator_result.output is not None
    assert calculator_result.output["result"] == "7"

    yahoo_result = results["Yahoo_Finance_Tool"]
    assert yahoo_result.status == "success"
    assert yahoo_result.output is not None
    assert yahoo_result.output["query"]["symbol"] == "TSLA"
    assert Decimal(yahoo_result.output["data_points"][0]["value"]) == Decimal(
        "407.76"
    )
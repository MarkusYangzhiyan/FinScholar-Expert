"""测试 Router Node 的主要路由链路。"""

from finscholar.nodes.router_node import run_router_node
from finscholar.schemas.schemas_router import RouterDecision
from finscholar.schemas.yahoo_finance import (
    YahooFinanceHistoryInput,
)


class FakeRouterClient:
    """返回固定 Yahoo Finance 路由决策。"""

    def __init__(self) -> None:
        self.received_query: str | None = None

    async def route(
        self,
        user_query: str,
    ) -> RouterDecision:
        self.received_query = user_query

        return RouterDecision(
            selected_tool="Yahoo_Finance_Tool",
            reason="用户要求查询历史行情",
            yahoo_finance_input=(
                YahooFinanceHistoryInput(
                    symbol="TSLA",
                    period="1mo",
                    interval="1d",
                )
            ),
        )


async def test_router_node_updates_yahoo_state() -> None:
    """Router Node 应调用 Client 并更新 Yahoo State。"""

    router_client = FakeRouterClient()

    update = await run_router_node(
        {"user_query": (" 查询 TSLA 最近一个月的行情 ")},
        router_client=router_client,
    )

    assert router_client.received_query == "查询 TSLA 最近一个月的行情"
    assert update["router_selected_tool"] == "Yahoo_Finance_Tool"
    assert update["router_decision"] is not None
    assert update["yahoo_finance_input"] == {
        "symbol": "TSLA",
        "period": "1mo",
        "interval": "1d",
        "auto_adjust": False,
    }
    assert update["calculator_input"] is None
    assert update["router_error_type"] is None

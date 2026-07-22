"""测试 Router Node 的主要路由链路。"""

from finscholar.nodes.router_node import run_router_node
from finscholar.schemas.schemas_router import RouterBatch, RouterAction, RouterContext
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput
from finscholar.state.state_agent import create_initial_agent_state
    

class FakeRouterClient:
    """返回固定的 Yahoo Finance 路由批次。"""

    def __init__(self) -> None:
        self.received_context: RouterContext | None = None

    async def route(
        self,
        context: RouterContext,
    ) -> RouterBatch:
        self.received_context = context

        return RouterBatch(
            status="execute",
            reason="本轮执行 Yahoo Finance",
            actions=[
                RouterAction(
                    selected_tool="Yahoo_Finance_Tool",
                    reason="用户要求查询历史行情",
                    yahoo_finance_input=YahooFinanceHistoryInput(
                        symbol="TSLA",
                        period="1mo",
                        interval="1d",
                    ),
                )
            ],
        )


async def test_router_node_creates_first_batch() -> None:
    """Router Node 应构造上下文并写回路由批次。"""

    router_client = FakeRouterClient()
    state = create_initial_agent_state(
        " 查询 TSLA 最近一个月的行情 "
    )

    update = await run_router_node(
        state,
        router_client=router_client,
    )

    context = router_client.received_context

    assert context is not None
    assert context.user_query == "查询 TSLA 最近一个月的行情"
    assert context.round_number == 1
    assert context.action_results == []

    batch = update["router_batch"]

    assert batch is not None
    assert batch.status == "execute"
    assert len(batch.actions) == 1
    assert (
        batch.actions[0].selected_tool
        == "Yahoo_Finance_Tool"
    )
    assert update["router_round_number"] == 1
    assert update["router_error_type"] is None
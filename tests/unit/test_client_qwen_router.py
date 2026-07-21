"""测试 Qwen Router Client 的主要路由链路。"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from finscholar.clients.client_qwen_router import QwenRouterClient
from finscholar.schemas.schemas_router import RouterContext


async def test_client_qwen_router_parses_yahoo_call() -> None:
    """Yahoo Function Calling 应转换成 RouterDecision。"""

    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[
                        SimpleNamespace(
                            function=SimpleNamespace(
                                name="Yahoo_Finance_Tool",
                                arguments=json.dumps(
                                    {
                                        "reason": ("用户要求查询历史行情"),
                                        "symbol": "TSLA",
                                        "period": "1mo",
                                        "interval": "1d",
                                        "auto_adjust": False,
                                    }
                                ),
                            )
                        )
                    ]
                )
            )
        ]
    )

    create = AsyncMock(return_value=response)

    openai_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=create,
            )
        )
    )

    router_client = QwenRouterClient(
        client=openai_client,
        model="qwen-router",
        enable_thinking=False,
    )

    batch = await router_client.route(
        RouterContext(
            user_query=" 查询 TSLA 最近一个月的行情 ",
            round_number=1,
        )
    )

    assert batch.status == "execute"
    assert len(batch.actions) == 1

    action = batch.actions[0]

    assert action.selected_tool == "Yahoo_Finance_Tool"
    assert action.reason == "用户要求查询历史行情"
    assert action.yahoo_finance_input is not None
    assert action.yahoo_finance_input.symbol == "TSLA"
    assert action.yahoo_finance_input.period == "1mo"
    assert action.yahoo_finance_input.interval == "1d"

    request = create.await_args.kwargs

    assert request["parallel_tool_calls"] is True

    router_context = json.loads(request["messages"][1]["content"])

    assert router_context == {
        "user_query": "查询 TSLA 最近一个月的行情",
        "round_number": 1,
        "action_results": [],
    }

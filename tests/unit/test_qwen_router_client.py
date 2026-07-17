"""测试 Qwen Router Client 的主要路由链路。"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

from finscholar.clients.qwen_router_client import (
    QwenRouterClient,
)


async def test_qwen_router_client_parses_yahoo_call() -> None:
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
                                        "reason": (
                                            "用户要求查询历史行情"
                                        ),
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

    decision = await router_client.route(
        " 查询 TSLA 最近一个月的行情 "
    )

    assert decision.selected_tool == "Yahoo_Finance_Tool"
    assert decision.reason == "用户要求查询历史行情"
    assert decision.yahoo_finance_input is not None
    assert decision.yahoo_finance_input.symbol == "TSLA"
    assert decision.yahoo_finance_input.period == "1mo"
    assert decision.yahoo_finance_input.interval == "1d"

    request = create.await_args.kwargs

    assert request["model"] == "qwen-router"
    assert request["tool_choice"] == "required"
    assert request["parallel_tool_calls"] is False
    assert (
        request["messages"][1]["content"]
        == "查询 TSLA 最近一个月的行情"
    )
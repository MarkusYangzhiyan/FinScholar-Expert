"""测试 FastAPI 到 AgentRuntime 的最小 HTTP 闭环。"""

from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from finscholar.main import create_app
from finscholar.state.agent_state import create_initial_agent_state

def test_agent_query_uses_shared_runtime() -> None:
    """应用应复用 lifespan 创建的 Runtime 并返回结构化响应。"""

    settings = Mock()
    runtime = Mock()

    runtime.invoke = AsyncMock(
        side_effect=lambda user_query: create_initial_agent_state(
            user_query
        )
    )
    runtime.close = AsyncMock()

    with (
        patch(
            "finscholar.main.get_settings",
            return_value=settings,
        ),
        patch(
            "finscholar.main.AgentRuntime.from_settings",
            return_value=runtime,
        ) as runtime_factory,
        TestClient(create_app()) as client,
    ):
        response = client.post(
            "/v1/agent/query",
            json={"user_query": "  查询 TSLA 行情  "},
        )

    assert response.status_code == 200
    assert response.json() == {
        "user_query": "查询 TSLA 行情",
        "router_decision": None,
        "calculator_output": None,
        "yahoo_finance_output": None,
        "errors": [],
    }

    runtime_factory.assert_called_once_with(settings)
    runtime.invoke.assert_awaited_once_with("查询 TSLA 行情")
    runtime.close.assert_awaited_once_with()
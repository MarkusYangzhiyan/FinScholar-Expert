"""测试 AgentRuntime 的 Router 后端选择。验证配置可以在 Qwen 和 DeepSeek 之间切换。"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from finscholar.clients.deepseek_router_client import (
    DeepSeekRouterClient,
)
from finscholar.clients.qwen_router_client import (
    QwenRouterClient,
)
from finscholar.runtime.agent_runtime import AgentRuntime


@pytest.mark.parametrize(
    ("backend", "expected_client_name"),
    [
        ("vllm", "qwen"),
        ("deepseek", "deepseek"),
    ],
)
def test_agent_runtime_selects_router_backend(
    backend: str,
    expected_client_name: str,
) -> None:
    """Runtime 应根据配置选择对应 Router Client。"""

    settings = SimpleNamespace(
        router_backend=backend,
        yfinance_request_timeout_seconds=30.0,
    )

    qwen_client = SimpleNamespace(
        close=AsyncMock(),
    )
    deepseek_client = SimpleNamespace(
        close=AsyncMock(),
    )
    compiled_graph = Mock()

    with (
        patch.object(
            QwenRouterClient,
            "from_settings",
            return_value=qwen_client,
        ) as qwen_factory,
        patch.object(
            DeepSeekRouterClient,
            "from_settings",
            return_value=deepseek_client,
        ) as deepseek_factory,
        patch(
            "finscholar.runtime.agent_runtime."
            "build_agent_graph",
            return_value=compiled_graph,
        ) as build_graph,
    ):
        runtime = AgentRuntime.from_settings(settings)

    expected_client = (
        qwen_client
        if expected_client_name == "qwen"
        else deepseek_client
    )

    assert runtime._router_client is expected_client
    assert runtime._compiled_graph is compiled_graph
    assert (
        build_graph.call_args.kwargs["router_client"]
        is expected_client
    )

    if backend == "vllm":
        qwen_factory.assert_called_once_with(settings)
        deepseek_factory.assert_not_called()
    else:
        deepseek_factory.assert_called_once_with(settings)
        qwen_factory.assert_not_called()
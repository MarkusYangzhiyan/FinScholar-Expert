"""
定义 FastAPI 使用的 AgentRuntime 依赖。

存放 Agent 相关的 FastAPI 依赖
"""

from typing import cast

from fastapi import HTTPException, Request, status

from finscholar.runtime.agent_runtime import AgentRuntime


def get_agent_runtime(
    request: Request,
) -> AgentRuntime:
    """从 FastAPI 应用状态中获取 AgentRuntime。"""

    runtime = getattr(
        request.app.state,
        "agent_runtime",
        None,
    )

    if runtime is None:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail="Agent runtime is not available",
        )

    return cast(AgentRuntime, runtime)


__all__ = ["get_agent_runtime"]
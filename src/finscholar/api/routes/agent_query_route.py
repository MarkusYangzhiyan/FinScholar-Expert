"""定义 Agent 查询接口。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from finscholar.api.agent_runtime_dependency import (
    get_agent_runtime,
)
from finscholar.api.agent_response_mapper import (
    build_agent_query_response,
)
from finscholar.runtime.agent_runtime import AgentRuntime
from finscholar.schemas.agent_api import (
    AgentQueryRequest,
    AgentQueryResponse,
)


router = APIRouter(
    prefix="/v1/agent",
    tags=["agent"],
)


@router.post(
    "/query",
    response_model=AgentQueryResponse,
)
async def query_agent(
    payload: AgentQueryRequest,
    runtime: Annotated[
        AgentRuntime,
        Depends(get_agent_runtime),
    ],
) -> AgentQueryResponse:
    """执行一次 Agent 查询。"""

    state = await runtime.invoke(payload.user_query)

    return build_agent_query_response(state)


__all__ = ["router"]

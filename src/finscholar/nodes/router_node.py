"""
定义调用 RouterClient 的 LangGraph Router Node。
"""

from typing import Any, TypedDict

from finscholar.clients.client_router import RouterClient, RouterClientError
from finscholar.schemas.schemas_router import RouterBatch, RouterDecision, ToolName, RouterContext
from finscholar.state.state_agent import AgentState


class RouterNodeUpdate(TypedDict, total=False):
    """Router Node 写回 AgentState 的局部增量。"""

    router_batch : RouterBatch | None 
    router_round_number : int
    router_error_type : str | None 
    router_error_message : str | None 

async def run_router_node(state: AgentState, router_client: RouterClient) -> RouterNodeUpdate:
    """据当前 Agent 状态执行一轮路由。"""

    user_query = state.get("user_query")
    current_round = state.get("router_round_number",0)

    if user_query is None or not user_query.strip():
        return {
            "router_batch": None,
            "router_round_number": current_round,
            "router_error_type": "MissingUserQuery",
            "router_error_message": "state 中缺少 user_query",
        }

    next_round = current_round + 1

    context = RouterContext(
        user_query = user_query.strip(),
        round_number = next_round,
        action_results = state.get("router_action_results",[])
    )

    try:
        batch = await router_client.route(context)
    except RouterClientError as exc:
        return {
            "router_batch": None,
            "router_round_number": next_round,
            "router_error_type": type(exc).__name__,
            "router_error_message": str(exc),
        }

    return {
        "router_batch":batch,
        "router_round_number": next_round,
        "router_error_type": None,
        "router_error_message": None,
    }



__all__ = [
    "RouterNodeUpdate",
    "run_router_node",
]
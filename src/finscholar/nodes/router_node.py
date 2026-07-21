"""
定义调用 RouterClient 的 LangGraph Router Node。
"""

from typing import Any, TypedDict

from finscholar.clients.client_router import RouterClient, RouterClientError
from finscholar.schemas.schemas_router import RouterDecision, ToolName
from finscholar.state.agent_state import AgentState


class RouterNodeUpdate(TypedDict, total=False):
    """Router Node 写回 AgentState 的局部增量。"""

    router_selected_tool: ToolName | None
    router_decision: RouterDecision | None
    router_reason: str | None
    router_error_type: str | None
    router_error_message: str | None

    # Router 会为 Calculator Node 准备这个字段。  from user_query
    calculator_input: dict[str, Any] | None
    yahoo_finance_input: dict[str, Any] | None


async def run_router_node(state: AgentState, router_client: RouterClient) -> RouterNodeUpdate:
    """调用 RouterClient，并返回 State 局部更新。"""

    user_query = state.get("user_query")

    if user_query is None or not user_query.strip():
        return {
            "router_selected_tool": None,
            "router_decision": None,
            "router_reason": None,
            "router_error_type": "MissingUserQuery",
            "router_error_message": "state 中缺少 user_query",
            "calculator_input": None,
            "yahoo_finance_input": None,
        }

    try:
        decision = await router_client.route(user_query.strip())
    except RouterClientError as exc:
        return {
            "router_selected_tool": None,
            "router_decision": None,
            "router_reason": None,
            "router_error_type": type(exc).__name__,
            "router_error_message": str(exc),
            "calculator_input": None,
            "yahoo_finance_input": None,
        }

    return _decision_to_update(decision)


def _decision_to_update(decision: RouterDecision) -> RouterNodeUpdate:
    """将 RouterDecision 转换为 AgentState 局部更新。"""

    calculator_input = None
    yahoo_finance_input = None

    if decision.calculator_input is not None:
        # 使用 json 模式，让写入 state 的 calculator_input 更接近模型工具调用参数。
        calculator_input = decision.calculator_input.model_dump(mode="json")

    if decision.yahoo_finance_input is not None:
        yahoo_finance_input = decision.yahoo_finance_input.model_dump(mode="json")

    return {
        "router_selected_tool": decision.selected_tool,
        "router_decision": decision,
        "router_reason": decision.reason,
        "router_error_type": None,
        "router_error_message": None,
        "calculator_input": calculator_input,
        "yahoo_finance_input": yahoo_finance_input,
    }


__all__ = [
    "RouterNodeUpdate",
    "run_router_node",
]

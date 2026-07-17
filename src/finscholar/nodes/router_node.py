"""
定义规则版 Router Node，用于最小 LangGraph 垂直切片。

当前 Router 不调用 Qwen3.5，也不做复杂自然语言理解。
它只负责通过 reg_patterns.toml 中的配置化正则规则生成 RouterDecision，
便于本地开发阶段验证 AgentState、Node、Tool 和 Graph 的完整链路。

后续接入 Qwen3.5 RouterClient 时，仍然应输出符合 RouterDecision
Schema 的结构化结果。
"""

from decimal import Decimal, InvalidOperation
from re import Pattern
from typing import Any, TypedDict

from pydantic import ValidationError

from finscholar.config.reg_patterns import (
    RegexPatternConfigError,
    get_regex_pattern,
)
from finscholar.schemas.calculator import CalculatorInput
from finscholar.schemas.router import RouterDecision, ToolName
from finscholar.state.agent_state import AgentState
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput
from finscholar.clients.router_client import RouterClient,RouterClientError


class RouterNodeUpdate(TypedDict, total=False):
    """Router Node 写回 AgentState 的局部增量。"""

    router_selected_tool: ToolName | None
    router_decision: RouterDecision | None
    router_reason: str | None
    router_error_type: str | None
    router_error_message: str | None

    # Router 会为 Calculator Node 准备这个字段。  from user_query
    calculator_input: dict[str, Any] | None
    yahoo_finance_input : dict[str,Any] | None


async def run_router_node(state: AgentState,router_client:RouterClient) -> RouterNodeUpdate:
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
        }

    try:
        decision = await router_client.route(
            user_query.strip()
        )
    except RouterClientError  as exc:
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
        yahoo_finance_input = (
            decision.yahoo_finance_input.model_dump(mode="json")
        )

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

"""将内部 AgentState 转换为对外 API 响应。"""

from finscholar.schemas.agent_api import (
    AgentExecutionError,
    AgentExecutionStage,
    AgentQueryResponse,
)
from finscholar.state.state_agent import AgentState


def _append_error(
    errors: list[AgentExecutionError],
    *,
    stage: AgentExecutionStage,
    error_type: str | None,
    message: str | None,
) -> None:
    """将 State 中的错误字段转换成结构化错误。"""

    if error_type is None:
        return

    errors.append(
        AgentExecutionError(
            stage=stage,
            error_type=error_type,
            message=message or "未提供错误详情",
        )
    )


def build_agent_query_response(
    state: AgentState,
) -> AgentQueryResponse:
    """根据最终 AgentState 构建 HTTP 响应。"""

    errors: list[AgentExecutionError] = []

    _append_error(
        errors,
        stage="router",
        error_type=state.get("router_error_type"),
        message=state.get("router_error_message"),
    )
    _append_error(
        errors,
        stage="calculator",
        error_type=state.get("calculator_error_type"),
        message=state.get("calculator_error_message"),
    )
    _append_error(
        errors,
        stage="yahoo_finance",
        error_type=state.get("yahoo_finance_error_type"),
        message=state.get("yahoo_finance_error_message"),
    )

    return AgentQueryResponse(
        user_query=state["user_query"],
        router_decision=state.get("router_decision"),
        calculator_output=state.get("calculator_output"),
        yahoo_finance_output=state.get("yahoo_finance_output"),
        errors=errors,
    )


__all__ = ["build_agent_query_response"]

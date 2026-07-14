"""
定义 Yahoo Finance LangGraph Node。

YahooFinanceTool
    ↓ 委托
YahooFinanceClient
    ↓ 调用
YFinanceHistoryGateway
    ↓ 请求
yfinance

"""

from typing import TypedDict

from pydantic import ValidationError

from finscholar.schemas.yahoo_finance import (
    YahooFinanceHistoryInput,
    YahooFinanceHistoryOutput,
)
from finscholar.state.agent_state import AgentState
from finscholar.tools.yahoo_finance import YahooFinanceTool


class YahooFinanceNodeUpdate(TypedDict, total=False):
    """Yahoo Finance Node 写回 AgentState 的局部增量。"""

    yahoo_finance_output: YahooFinanceHistoryOutput | None
    yahoo_finance_error_type: str | None
    yahoo_finance_error_message: str | None


async def run_yahoo_finance_node(
    state: AgentState,
    tool: YahooFinanceTool,
) -> YahooFinanceNodeUpdate:
    """校验查询参数，调用 Yahoo Finance Tool 并写回结果。"""

    raw_input = state.get("yahoo_finance_input")

    if raw_input is None:
        return {
            "yahoo_finance_output": None,
            "yahoo_finance_error_type": "MissingYahooFinanceInput",
            "yahoo_finance_error_message": (
                "state 中缺少 yahoo_finance_input"
            ),
        }

    try:
        query = YahooFinanceHistoryInput.model_validate(raw_input)
    except ValidationError as exc:
        return {
            "yahoo_finance_output": None,
            "yahoo_finance_error_type": (
                "YahooFinanceInputValidationError"
            ),
            "yahoo_finance_error_message": str(exc),
        }

    try:
        output = await tool.get_history(query)
    except Exception as exc:
        # Node 是 LangGraph 的执行边界，需要把异常转换成结构化状态。
        return {
            "yahoo_finance_output": None,
            "yahoo_finance_error_type": type(exc).__name__,
            "yahoo_finance_error_message": str(exc),
        }

    return {
        "yahoo_finance_output": output,
        "yahoo_finance_error_type": None,
        "yahoo_finance_error_message": None,
    }


__all__ = [
    "YahooFinanceNodeUpdate",
    "run_yahoo_finance_node",
]
from typing import TypedDict

from finscholar.schemas.schemas_router import RouterAction, RouterActionResult
from finscholar.tools.math_calculator import MathCalculator
from finscholar.tools.yahoo_finance import YahooFinanceTool


class ToolActionState(TypedDict):
    """单个并行工具分支接收的状态。"""

    action : RouterAction

class ToolActionNodeUpdate(TypedDict):
    """工具分支写回主状态的增量。"""

    router_action_results : list[RouterActionResult]


async def run_tool_action_node(
    state: ToolActionState,
    *,
    calculator: MathCalculator,
    yahoo_finance_tool: YahooFinanceTool,
) -> ToolActionNodeUpdate:
    """执行一个 RouterAction，并统一包装执行结果。"""

    action = state["action"]

    try:
        if action.selected_tool == "Math_Calculator":
            if action.calculator_input is None:
                raise ValueError(
                    "Math_Calculator action 缺少输入参数"
                )

            output = calculator.calculate(
                action.calculator_input
            )

        elif action.selected_tool == "Yahoo_Finance_Tool":
            if action.yahoo_finance_input is None:
                raise ValueError(
                    "Yahoo_Finance_Tool action 缺少输入参数"
                )

            output = await yahoo_finance_tool.get_history(
                action.yahoo_finance_input
            )

        else:
            raise ValueError(
                f"不可执行的工具：{action.selected_tool}"
            )

        result = RouterActionResult(
            action=action,
            status="success",
            output=output.model_dump(mode="json"),
        )

    except Exception as exc:
        result = RouterActionResult(
            action=action,
            status="error",
            error_type=type(exc).__name__,
            error_message=str(exc) or "工具执行失败",
        )

    return {
        "router_action_results": [result],
    }


__all__ = [
    "ToolActionNodeUpdate",
    "ToolActionState",
    "run_tool_action_node",
]
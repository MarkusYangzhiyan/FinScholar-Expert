"""定义 Calculator Node，用于在 LangGraph 状态流中调用 Math_Calculator。

本模块不直接做数学计算，而是负责：
1. 从 Agent state 中读取 calculator 请求；
2. 调用 MathCalculator 工具；
3. 将成功结果或错误信息写回 state；
4. 保持节点输入输出结构稳定，便于后续接入 LangGraph。
"""

from typing import TypedDict

from pydantic import ValidationError

from finscholar.schemas.calculator import CalculatorInput, CalculatorOutput
from finscholar.state.agent_state import AgentState
from finscholar.tools.math_calculator import CalculatorError, MathCalculator


# total = False: 字典里的键都是可选的
class CalculatorNodeUpdate(TypedDict, total=False):
    """Calculator Node 写回 AgentState 的局部增量。"""

    # Calculator 成功执行后的结构化结果。
    calculator_output: CalculatorOutput

    # Calculator 失败时写入的错误类型。
    calculator_error_type: str | None

    # Calculator 失败时写入的错误信息。
    calculator_error_message: str | None


def run_calculator_node(
    state: AgentState,
    calculator: MathCalculator | None = None,
) -> CalculatorNodeUpdate:
    """执行 Calculator 节点，并返回对 LangGraph state 的局部更新。

    Args:
        state: 当前 LangGraph state，必须包含 calculator_input。
        calculator: 可注入的 Calculator 实例，方便单元测试替换。

    Returns:
        只返回本节点新增或更新的字段，不直接修改原始 state。
    """

    calculator_input = state.get("calculator_input")

    if calculator_input is None:
        return {
            "calculator_output": None,
            "calculator_error_type": "MissingCalculatorInput",
            "calculator_error_message": "state 中缺少 calculator_input",
        }

    try:
        # 用预先写好的CalculatorInput Pydantic模型验证输入，确保结构正确。
        request = CalculatorInput.model_validate(calculator_input)
    except ValidationError as exc:
        return {
            "calculator_output": None,
            "calculator_error_type": "CalculatorInputValidationError",
            "calculator_error_message": str(exc),
        }

    tool = calculator or MathCalculator()

    try:
        result = tool.calculate(request)
    except CalculatorError as exc:
        return {
            "calculator_output": None,
            "calculator_error_type": type(exc).__name__,
            "calculator_error_message": str(exc),
        }

    return {
        "calculator_output": result,
        "calculator_error_message": None,
        "calculator_error_type": None,
    }


__all__ = [
    "CalculatorNodeUpdate",
    "run_calculator_node",
]

"""测试统一工具 Action Node。"""

from unittest.mock import Mock

from finscholar.nodes.tool_action_node import (
    run_tool_action_node,
)
from finscholar.schemas.calculator import CalculatorInput
from finscholar.schemas.schemas_router import RouterAction
from finscholar.tools.math_calculator import MathCalculator
from finscholar.tools.yahoo_finance import YahooFinanceTool


async def test_tool_action_node_executes_calculator() -> None:
    """节点应执行 Calculator Action 并返回统一结果。"""

    action = RouterAction(
        selected_tool="Math_Calculator",
        reason="用户要求执行数学计算",
        calculator_input=CalculatorInput(
            expression="1 + 2 * 3",
        ),
    )

    update = await run_tool_action_node(
        {"action": action},
        calculator=MathCalculator(),
        yahoo_finance_tool=Mock(
            spec=YahooFinanceTool,
        ),
    )

    results = update["router_action_results"]

    assert len(results) == 1

    result = results[0]

    assert result.action.action_id == action.action_id
    assert result.status == "success"
    assert result.output is not None
    assert result.output["formula"] == "1 + 2 * 3"
    assert result.output["result"] == "7"
    assert result.error_type is None
    assert result.error_message is None
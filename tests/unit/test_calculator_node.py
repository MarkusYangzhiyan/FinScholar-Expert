"""测试 Calculator Node 的状态读写与错误处理行为。"""

from decimal import Decimal

from finscholar.nodes.calculator_node import run_calculator_node, CalculatorNodeState


def test_run_calculator_node_returns_output_and_clears_error() -> None:
    """正常输入时，节点应返回 calculator_output，并清空旧错误。"""

    state = {
        "calculator_input": {
            "expression": "profit / revenue * 100",
            "variables": {
                "profit": "25",
                "revenue": "100",
            },
            "unit": "%",
        },
        # 模拟上一次失败留下的旧错误。
        "calculator_error_type": "OldError",
        "calculator_error_message": "旧错误信息",
    }

    result = run_calculator_node(state)

    assert result["calculator_output"] is not None
    assert result["calculator_output"].result == Decimal("25.00")
    assert result["calculator_output"].unit == "%"
    assert result["calculator_error_type"] is None
    assert result["calculator_error_message"] is None


def test_run_calculator_node_handles_missing_input() -> None:
    """缺少 calculator_input 时，节点应返回结构化错误。"""

    result = run_calculator_node({})

    assert result["calculator_output"] is None
    assert result["calculator_error_type"] == "MissingCalculatorInput"
    assert "calculator_input" in result["calculator_error_message"]


def test_run_calculator_node_handles_invalid_input_schema() -> None:
    """calculator_input 不符合 CalculatorInput 时，节点应返回校验错误。"""

    state = {
        "calculator_input": {
            # expression 缺失，故意制造 Schema 校验失败。
            "variables": {
                "profit": "25",
                "revenue": "100",
            },
            "unit": "%",
        }
    }

    result = run_calculator_node(state)

    assert result["calculator_output"] is None
    assert result["calculator_error_type"] == "CalculatorInputValidationError"
    assert "expression" in result["calculator_error_message"]


def test_run_calculator_node_handles_calculator_error() -> None:
    """Calculator 工具内部报错时，节点应把错误写成 state 字段。"""

    state = {
        "calculator_input": {
            "expression": "profit / revenue",
            "variables": {
                "profit": "25",
            },
        }
    }

    result = run_calculator_node(state)

    assert result["calculator_output"] is None
    assert result["calculator_error_type"] == "UnknownVariableError"
    assert "revenue" in result["calculator_error_message"]
"""测试 Calculator 最小 LangGraph。"""

from decimal import Decimal

from finscholar.graph.calculator_graph import (
    build_calculator_graph,
    invoke_calculator_graph,
)


def test_build_calculator_graph_can_invoke() -> None:
    """build_calculator_graph 应返回可执行的 LangGraph 图。"""

    graph = build_calculator_graph()

    result = graph.invoke(
        {
            "user_query": "帮我计算利润率",
            "calculator_input": {
                "expression": "profit / revenue * 100",
                "variables": {
                    "profit": "25",
                    "revenue": "100",
                },
                "unit": "%",
            },
            "calculator_output": None,
            "calculator_error_type": None,
            "calculator_error_message": None,
        }
    )

    assert result["calculator_output"] is not None
    assert result["calculator_output"].result == Decimal("25.00")
    assert result["calculator_error_type"] is None
    assert result["calculator_error_message"] is None


def test_invoke_calculator_graph_returns_success_state() -> None:
    """invoke_calculator_graph 应返回 Calculator 成功后的最终状态。"""

    result = invoke_calculator_graph(
        calculator_input={
            "expression": "profit / revenue * 100",
            "variables": {
                "profit": "25",
                "revenue": "100",
            },
            "unit": "%",
        },
        user_query="帮我计算利润率",
    )

    assert result["user_query"] == "帮我计算利润率"
    assert result["calculator_output"] is not None
    assert result["calculator_output"].result == Decimal("25.00")
    assert result["calculator_output"].unit == "%"
    assert result["calculator_error_type"] is None
    assert result["calculator_error_message"] is None


def test_invoke_calculator_graph_returns_error_state() -> None:
    """Calculator 失败时，Graph 应保留节点写回的错误状态。"""

    result = invoke_calculator_graph(
        calculator_input={
            "expression": "profit / revenue",
            "variables": {
                "profit": "25",
            },
        },
        user_query="帮我计算利润率",
    )

    assert result["calculator_output"] is None
    assert result["calculator_error_type"] == "UnknownVariableError"
    assert "revenue" in result["calculator_error_message"]
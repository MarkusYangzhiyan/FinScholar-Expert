"""
测试规则版 Router Node。
1. state 已有 calculator_input 时，Router 选择 Math_Calculator
2. user_query 是利润率问题时，Router 自动生成 calculator_input
3. user_query 是显式表达式时，Router 自动生成 calculator_input
4. 无法识别的问题返回 Unsupported
5. 缺少 user_query 返回 MissingUserQuery
6. 已有 calculator_input 但格式错误时，返回 RouterInputValidationError
"""

from finscholar.nodes.router_node import run_router_node


def test_router_node_uses_existing_calculator_input() -> None:
    """state 已有 calculator_input 时，Router 应选择 Math_Calculator。"""

    result = run_router_node(
        {
            "user_query": "请计算这个表达式",
            "calculator_input": {
                "expression": "1 + 2 * 3",
                "variables": {},
                "unit": None,
            },
        }
    )

    assert result["router_selected_tool"] == "Math_Calculator"
    assert result["router_decision"] is not None
    assert result["calculator_input"] is not None
    assert result["calculator_input"]["expression"] == "1 + 2 * 3"
    assert result["router_error_type"] is None
    assert result["router_error_message"] is None


def test_router_node_parses_profit_margin_query() -> None:
    """Router 可以从利润率问题中生成 Calculator 参数。"""

    result = run_router_node(
        {
            "user_query": "利润为25，收入为100，请计算利润率",
        }
    )

    assert result["router_selected_tool"] == "Math_Calculator"
    assert result["router_decision"] is not None
    assert result["calculator_input"] is not None
    assert (
        result["calculator_input"]["expression"]
        == "profit / revenue * 100"
    )
    assert result["calculator_input"]["variables"] == {
        "profit": "25",
        "revenue": "100",
    }
    assert result["calculator_input"]["unit"] == "%"
    assert result["router_error_type"] is None
    assert result["router_error_message"] is None


def test_router_node_parses_explicit_expression_query() -> None:
    """Router 可以识别显式表达式。"""

    result = run_router_node(
        {
            "user_query": "表达式: 1 + 2 * 3 单位: 元",
        }
    )

    assert result["router_selected_tool"] == "Math_Calculator"
    assert result["router_decision"] is not None
    assert result["calculator_input"] is not None
    assert result["calculator_input"]["expression"] == "1 + 2 * 3"
    assert result["calculator_input"]["unit"] == "元"
    assert result["router_error_type"] is None
    assert result["router_error_message"] is None


def test_router_node_returns_unsupported_for_unknown_query() -> None:
    """无法识别的问题应返回 Unsupported，而不是伪造工具调用。"""

    result = run_router_node(
        {
            "user_query": "帮我总结一下这篇论文",
        }
    )

    assert result["router_selected_tool"] == "Unsupported"
    assert result["router_decision"] is not None
    assert result["router_reason"] == "规则版 Router 无法安全识别该问题所需工具"
    assert result["calculator_input"] is None
    assert result["router_error_type"] is None
    assert result["router_error_message"] is None


def test_router_node_handles_missing_user_query() -> None:
    """缺少 user_query 时应返回结构化错误。"""

    result = run_router_node({})

    assert result["router_selected_tool"] is None
    assert result["router_decision"] is None
    assert result["router_reason"] is None
    assert result["calculator_input"] is None
    assert result["router_error_type"] == "MissingUserQuery"
    assert "user_query" in result["router_error_message"]


def test_router_node_handles_invalid_existing_calculator_input() -> None:
    """已有 calculator_input 但格式非法时应返回校验错误。"""

    result = run_router_node(
        {
            "user_query": "请计算这个表达式",
            "calculator_input": {
                "variables": {},
            },
        }
    )

    assert result["router_selected_tool"] is None
    assert result["router_decision"] is None
    assert result["router_reason"] is None
    assert result["calculator_input"] is None
    assert result["router_error_type"] == "RouterInputValidationError"
    assert "expression" in result["router_error_message"]
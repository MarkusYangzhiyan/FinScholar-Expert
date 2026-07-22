"""测试 Router + Calculator 最小 LangGraph 工作流。"""

from decimal import Decimal

from langgraph.graph import END

from finscholar.graph.router_calculator_graph import (
    CALCULATOR_NODE_NAME,
    build_router_calculator_graph,
    invoke_router_calculator_graph,
    route_after_router,
)
from finscholar.state.state_agent import create_initial_agent_state


def test_route_after_router_selects_calculator_node() -> None:
    """Router 选择 Math_Calculator 时，应进入 Calculator Node。"""

    state = create_initial_agent_state("请计算这个表达式")
    state["router_selected_tool"] = "Math_Calculator"

    next_node = route_after_router(state)

    assert next_node == CALCULATOR_NODE_NAME


def test_route_after_router_ends_for_unsupported_query() -> None:
    """Router 返回 Unsupported 时，工作流应直接结束。"""

    state = create_initial_agent_state("帮我总结一下这篇论文")
    state["router_selected_tool"] = "Unsupported"

    next_node = route_after_router(state)

    assert next_node == END


def test_route_after_router_prioritizes_router_error() -> None:
    """Router 出错时，即使存在工具选择，也不应调用下游工具。"""

    state = create_initial_agent_state("请计算这个表达式")
    state["router_selected_tool"] = "Math_Calculator"
    state["router_error_type"] = "RouterInputValidationError"

    next_node = route_after_router(state)

    assert next_node == END


def test_built_graph_passes_state_from_router_to_calculator() -> None:
    """直接运行编译后的图时，Router 准备的参数应传给 Calculator。"""

    graph = build_router_calculator_graph()
    initial_state = create_initial_agent_state("请计算这个表达式")
    initial_state["calculator_input"] = {
        "expression": "1 + 2 * 3",
        "variables": {},
        "unit": None,
    }

    result = graph.invoke(initial_state)

    assert result["router_selected_tool"] == "Math_Calculator"
    assert result["calculator_output"] is not None
    assert result["calculator_output"].result == Decimal("7")
    assert result["calculator_error_type"] is None
    assert result["calculator_error_message"] is None


def test_invoke_graph_parses_and_calculates_expression() -> None:
    """封装入口应完成 Router 解析、路由和 Calculator 计算。"""

    result = invoke_router_calculator_graph(
        user_query="表达式: 1 + 2 * 3",
    )

    assert result["router_selected_tool"] == "Math_Calculator"
    assert result["calculator_input"] is not None
    assert result["calculator_input"]["expression"] == "1 + 2 * 3"
    assert result["calculator_output"] is not None
    assert result["calculator_output"].result == Decimal("7")
    assert result["router_error_type"] is None
    assert result["calculator_error_type"] is None


def test_invoke_graph_ends_without_calculator_for_unsupported_query() -> None:
    """不支持的问题应在 Router 后结束，不得调用 Calculator。"""

    result = invoke_router_calculator_graph(
        user_query="帮我总结一下这篇论文",
    )

    assert result["router_selected_tool"] == "Unsupported"
    assert result["calculator_input"] is None
    assert result["calculator_output"] is None
    assert result["router_error_type"] is None
    assert result["calculator_error_type"] is None


def test_invoke_graph_ends_when_user_query_is_empty() -> None:
    """用户问题为空时，应保留 Router 错误并直接结束。"""

    result = invoke_router_calculator_graph(
        user_query="   ",
    )

    assert result["router_selected_tool"] is None
    assert result["router_error_type"] == "MissingUserQuery"
    assert result["router_error_message"] is not None
    assert "user_query" in result["router_error_message"]
    assert result["calculator_output"] is None
    assert result["calculator_error_type"] is None

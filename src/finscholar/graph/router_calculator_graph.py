"""
构建 Router 与 Math Calculator 组成的最小 LangGraph 工作流。

工作流程：
1. Router Node 分析用户问题并决定是否调用 Math_Calculator。
2. 如果 Router 选择 Math_Calculator，则进入 Calculator Node。
3. 如果问题暂不支持或 Router 发生错误，则直接结束工作流。

START
  ↓
Router Node
  ├─ Math_Calculator → Calculator Node → END
  ├─ Unsupported → END
  └─ Router 出错 → END

"""

from functools import lru_cache
from typing import Any, cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from finscholar.nodes.calculator_node import run_calculator_node
from finscholar.nodes.router_node import run_router_node
from finscholar.state.agent_state import AgentState, create_initial_agent_state


# LangGraph 中使用的节点名称。
ROUTER_NODE_NAME = "router"
CALCULATOR_NODE_NAME = "calculator"


def route_after_router(state: AgentState) -> str:
    """根据 Router Node 写入的状态决定下一步节点。

    Args:
        state: Router Node 执行后的全局 AgentState。

    Returns:
        Calculator 节点名称或 LangGraph 的 END 标识。
    """

    # Router 本身发生错误时，不继续调用下游工具。
    if state.get("router_error_type") is not None:
        return END

    # Router 明确选择 Math_Calculator 时，进入 Calculator Node。
    if state.get("router_selected_tool") == "Math_Calculator":
        return CALCULATOR_NODE_NAME

    # 当前不支持的问题直接结束工作流。
    return END


@lru_cache(maxsize=1)
def build_router_calculator_graph() -> CompiledStateGraph:
    """构建并编译 Router + Calculator 最小工作流。"""

    graph_builder = StateGraph(AgentState)

    # 注册节点，并将节点名称与节点函数绑定。
    graph_builder.add_node(
        ROUTER_NODE_NAME,
        run_router_node,
    )
    graph_builder.add_node(
        CALCULATOR_NODE_NAME,
        run_calculator_node,
    )

    # 每次运行都先进入 Router Node。
    graph_builder.add_edge(
        START,
        ROUTER_NODE_NAME,
    )

    # Router 执行完后，根据路由结果选择下一步。
    graph_builder.add_conditional_edges(
        ROUTER_NODE_NAME,
        route_after_router,
        {
            CALCULATOR_NODE_NAME: CALCULATOR_NODE_NAME,
            END: END,
        },
    )

    # Calculator 执行完成后结束工作流。
    graph_builder.add_edge(
        CALCULATOR_NODE_NAME,
        END,
    )
    app = graph_builder.compile()

    return app

def invoke_router_calculator_graph(
    user_query: str,
    calculator_input: dict[str, Any] | None = None,
) -> AgentState:
    """创建初始状态并运行 Router + Calculator 工作流。

    Args:
        user_query: 用户输入的问题。
        calculator_input: 可选的结构化计算参数。主要用于上层调用或测试。

    Returns:
        工作流执行完成后的全局 AgentState。
    """

    initial_state = create_initial_agent_state(user_query)

    # 如果调用方已经提供结构化计算参数，将其写入初始状态。
    if calculator_input is not None:
        initial_state["calculator_input"] = calculator_input

    graph = build_router_calculator_graph()
    result = graph.invoke(initial_state)

    return cast(AgentState, result)


__all__ = [
    "CALCULATOR_NODE_NAME",
    "ROUTER_NODE_NAME",
    "build_router_calculator_graph",
    "invoke_router_calculator_graph",
    "route_after_router",
]
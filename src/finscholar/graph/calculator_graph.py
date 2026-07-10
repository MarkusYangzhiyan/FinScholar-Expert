"""构建 Calculator 最小 LangGraph。

本模块只负责验证最小垂直切片：
AgentState -> Calculator Node -> AgentState。

当前图不包含 Router、RAG、Grader 或最终回答生成。
后续完整 Agent 图会在此基础上扩展多个节点和条件边。
"""
from typing import Any, cast
from functools import lru_cache
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from finscholar.state.agent_state import AgentState, create_initial_agent_state
from finscholar.nodes.calculator_node import run_calculator_node


CALCULATOR_NODE_NAME = "calculator"


# 缓存函数的返回结果，避免重复计算
# 这个函数负责搭图
@lru_cache(maxsize=1)
def build_calculator_graph() -> CompiledStateGraph:
    """构建并编译 Calculator 最小图。

    使用缓存是为了避免在同一进程内重复编译图。

    负责搭图，告诉LangGraph：
        我的全局状态是AgentState
        我要注册calculator节点
        启动后先走calculator
        执行完就结束
    """

    workflow = StateGraph(AgentState)

    workflow.add_node(
        CALCULATOR_NODE_NAME,
        run_calculator_node,
    )

    workflow.add_edge(START, CALCULATOR_NODE_NAME)
    workflow.add_edge(CALCULATOR_NODE_NAME,END)
    app = workflow.compile()
    return app

# 方便测试和调用的小包装
def invoke_calculator_graph(
    calculator_input : dict[str,Any],
    user_query : str = "执行 Calculator 工具",
) -> AgentState:
    """运行 Calculator 最小图，并返回执行后的 AgentState。

    Args:
        calculator_input: Calculator 工具参数，通常来自 Router 或测试代码。
        user_query: 用户原始问题，当前最小图只保留，不参与路由。

    Returns:
        LangGraph 执行完成后的完整 AgentState。
    """

    initial_state = create_initial_agent_state(user_query)

    initial_state['calculator_input'] = calculator_input

    result = build_calculator_graph().invoke(initial_state)

    return cast(AgentState,result)


__all__ = [
    "CALCULATOR_NODE_NAME",
    "build_calculator_graph",
    "invoke_calculator_graph",
]

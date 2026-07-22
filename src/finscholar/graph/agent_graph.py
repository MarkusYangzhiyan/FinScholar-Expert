"""构建 FinScholar Expert 主 LangGraph。"""

from typing import cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from finscholar.clients.client_router import RouterClient
from finscholar.nodes.router_node import RouterNodeUpdate, run_router_node
from finscholar.nodes.tool_action_node import (
    ToolActionNodeUpdate,
    ToolActionState,
    run_tool_action_node,
)
from finscholar.state.state_agent import AgentState, create_initial_agent_state
from finscholar.tools.math_calculator import MathCalculator
from finscholar.tools.yahoo_finance import YahooFinanceTool

ROUTER_NODE_NAME = "router"
TOOL_ACTION_NODE_NAME = "tool_action"


def route_after_router(state: AgentState) -> str | list[Send]:
    """根据 RouterBatch 决定结束或分发工具 Action。"""

    if state.get("router_error_type") is not None:
        return END

    batch = state.get("router_batch")

    if batch is None or batch.status != "execute":
        return END

    return [Send(TOOL_ACTION_NODE_NAME, {"action": action}) for action in batch.actions]


def build_agent_graph(
    *,
    router_client: RouterClient,
    yahoo_finance_tool: YahooFinanceTool,
) -> CompiledStateGraph:
    """构建支持批次工具调用的主 Agent Graph。"""

    calculator = MathCalculator()

    async def router_node(
        state: AgentState,
    ) -> RouterNodeUpdate:
        return await run_router_node(
            state,
            router_client=router_client,
        )

    async def tool_action_node(
        state: ToolActionState,
    ) -> ToolActionNodeUpdate:
        return await run_tool_action_node(
            state,
            calculator=calculator,
            yahoo_finance_tool=yahoo_finance_tool,
        )

    graph_builder = StateGraph(AgentState)

    graph_builder.add_node(ROUTER_NODE_NAME, router_node)
    graph_builder.add_node(TOOL_ACTION_NODE_NAME, tool_action_node)

    graph_builder.add_edge(START, ROUTER_NODE_NAME)
    graph_builder.add_conditional_edges(ROUTER_NODE_NAME, route_after_router)
    graph_builder.add_edge(TOOL_ACTION_NODE_NAME, ROUTER_NODE_NAME)

    return graph_builder.compile()


async def invoke_agent_graph(
    *,
    compiled_graph: CompiledStateGraph,
    user_query: str,
) -> AgentState:
    """建初始状态并异步运行主图。"""

    initial_state = create_initial_agent_state(user_query)
    result = await compiled_graph.ainvoke(initial_state)

    return cast(AgentState, result)


__all__ = [
    "ROUTER_NODE_NAME",
    "TOOL_ACTION_NODE_NAME",
    "build_agent_graph",
    "invoke_agent_graph",
    "route_after_router",
]

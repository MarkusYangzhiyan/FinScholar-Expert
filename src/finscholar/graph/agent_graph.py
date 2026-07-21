"""构建 FinScholar Expert 主 LangGraph。"""

from typing import cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from finscholar.clients.client_router import RouterClient
from finscholar.nodes.calculator_node import run_calculator_node
from finscholar.nodes.router_node import RouterNodeUpdate, run_router_node
from finscholar.nodes.yahoo_finance_node import (
    YahooFinanceNodeUpdate,
    run_yahoo_finance_node,
)
from finscholar.state.agent_state import AgentState, create_initial_agent_state
from finscholar.tools.yahoo_finance import YahooFinanceTool

ROUTER_NODE_NAME = "router"
CALCULATOR_NODE_NAME = "calculator"
YAHOO_FINANCE_NODE_NAME = "yahoo_finance"


def route_after_router(state: AgentState) -> str:
    """根据 Router 决策选择下一个节点。"""

    if state.get("router_error_type") is not None:
        return END

    selected_tool = state.get("router_selected_tool")

    if selected_tool == "Math_Calculator":
        return CALCULATOR_NODE_NAME

    if selected_tool == "Yahoo_Finance_Tool":
        return YAHOO_FINANCE_NODE_NAME

    return END


def build_agent_graph(
    *,
    router_client: RouterClient,
    yahoo_finance_tool: YahooFinanceTool,
) -> CompiledStateGraph:
    """构建并编译主 Agent Graph。"""

    async def router_node(
        state: AgentState,
    ) -> RouterNodeUpdate:
        return await run_router_node(
            state,
            router_client=router_client,
        )

    async def yahoo_finance_node(
        state: AgentState,
    ) -> YahooFinanceNodeUpdate:
        return await run_yahoo_finance_node(
            state,
            tool=yahoo_finance_tool,
        )

    graph_builder = StateGraph(AgentState)

    graph_builder.add_node(ROUTER_NODE_NAME, router_node)
    graph_builder.add_node(CALCULATOR_NODE_NAME, run_calculator_node)
    graph_builder.add_node(YAHOO_FINANCE_NODE_NAME, yahoo_finance_node)

    graph_builder.add_edge(START, ROUTER_NODE_NAME)
    graph_builder.add_conditional_edges(
        ROUTER_NODE_NAME,
        route_after_router,
        {
            CALCULATOR_NODE_NAME: CALCULATOR_NODE_NAME,
            YAHOO_FINANCE_NODE_NAME: YAHOO_FINANCE_NODE_NAME,
            END: END,
        },
    )
    graph_builder.add_edge(CALCULATOR_NODE_NAME, END)
    graph_builder.add_edge(YAHOO_FINANCE_NODE_NAME, END)

    return graph_builder.compile()


async def invoke_agent_graph(
    *,
    compiled_graph: CompiledStateGraph,
    user_query: str,
) -> AgentState:
    """创建初始 State，并异步运行 Agent Graph。"""

    initial_state = create_initial_agent_state(user_query)
    result = await compiled_graph.ainvoke(initial_state)

    return cast(AgentState, result)


__all__ = [
    "CALCULATOR_NODE_NAME",
    "ROUTER_NODE_NAME",
    "YAHOO_FINANCE_NODE_NAME",
    "build_agent_graph",
    "invoke_agent_graph",
    "route_after_router",
]

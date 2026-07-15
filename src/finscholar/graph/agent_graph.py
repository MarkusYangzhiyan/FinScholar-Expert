"""构建 FinScholar Expert 主 LangGraph。"""

from typing import Any, cast 
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph


from finscholar.state.agent_state import AgentState, create_initial_agent_state
from finscholar.tools.yahoo_finance import YahooFinanceTool
from finscholar.nodes.yahoo_finance_node import YahooFinanceNodeUpdate, run_yahoo_finance_node
from finscholar.nodes.router_node import run_router_node
from finscholar.nodes.calculator_node import run_calculator_node


# =================================================================================================
# LangGraph 节点统一命名
# =================================================================================================

ROUTER_NODE_NAME = "router"
CALCULATOR_NODE_NAME = "calculator"
YAHOO_FINANCE_NODE_NAME = "yahoo_finance"

# =================================================================================================

def route_after_router(state:AgentState) -> str:
    """ 根据 Router 决策选择下一个节点"""

    if state.get("router_error_type"):
        return END
    
    selected_tool = state.get("router_selected_tool")

    if selected_tool == "Math_Calculator":
        return CALCULATOR_NODE_NAME

    if selected_tool == "Yahoo_Finance_Tool":
        return YAHOO_FINANCE_NODE_NAME

    return END 

# =================================================================================================
# 构建工作流
# =================================================================================================

def build_agent_graph(
        *,
        yahoo_finance_tool: YahooFinanceTool,

) -> CompiledStateGraph:
    """
    构建并编译主 Agent Graph。

    Tool 在应用启动时创建并注入，Node 内部不创建依赖。
    """

    async def yahoo_finance_node(
            state: AgentState,

    ) -> YahooFinanceNodeUpdate:
        
        return await run_yahoo_finance_node(
            state,
            tool = yahoo_finance_tool
        )
    
    graph_builder = StateGraph(AgentState)

    graph_builder.add_node(ROUTER_NODE_NAME,run_router_node)
    graph_builder.add_node(CALCULATOR_NODE_NAME,run_calculator_node)
    graph_builder.add_node(YAHOO_FINANCE_NODE_NAME,yahoo_finance_node)

    graph_builder.add_edge(START,ROUTER_NODE_NAME)
    graph_builder.add_conditional_edges(
        ROUTER_NODE_NAME,               # 从哪个节点出发
        route_after_router,             # 用哪个函数判断

        # 判断结果对应哪个目标节点: 判断函数的返回值 → 实际进入的目标节点
        {
            CALCULATOR_NODE_NAME:CALCULATOR_NODE_NAME,
            YAHOO_FINANCE_NODE_NAME:YAHOO_FINANCE_NODE_NAME,
            END:END,
        },
    )
    graph_builder.add_edge(CALCULATOR_NODE_NAME,END)
    graph_builder.add_edge(YAHOO_FINANCE_NODE_NAME,END)
    compiled_graph = graph_builder.compile()
    return compiled_graph



# =================================================================================================
# 执行一次工作流
# =================================================================================================

async def invoke_agent_graph(
    *,
    compiled_graph: CompiledStateGraph,
    user_query: str,
    calculator_input : dict[str,Any] | None = None,
    yahoo_finance_input : dict[str,Any] | None = None
) -> AgentState:
    """创建初始 State，并异步运行 Agent Graph。"""

    # step 1 创建本次请求的初始 State,每个用户请求都有自己独立的 State
    initial_state = create_initial_agent_state(user_query)

    # step 2 写入调用参数
    if calculator_input is not None: 
        initial_state['calculator_input'] = calculator_input

    if yahoo_finance_input is not None:
        initial_state['yahoo_finance_input'] = yahoo_finance_input

    # step 3 执行编译好的 Graph
    result = await compiled_graph.ainvoke(initial_state)

    # step 4 返回最终 State
    return cast(AgentState, result)


__all__ = [
    "CALCULATOR_NODE_NAME",
    "ROUTER_NODE_NAME",
    "YAHOO_FINANCE_NODE_NAME",
    "build_agent_graph",
    "invoke_agent_graph",
    "route_after_router",
]
    


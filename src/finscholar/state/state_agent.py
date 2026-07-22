"""
定义 FinScholar Expert 的 LangGraph 主状态。
"""

from operator import add
from typing import TypedDict, Annotated

from finscholar.schemas.schemas_router import RouterBatch, RouterActionResult


# total=False 表示字段可以按需逐步写入。
class AgentState(TypedDict, total=False):
    """
    FinScholar Expert 的 LangGraph 主状态。
    """

    user_query: str

    router_batch : RouterBatch | None 
    router_round_number : int 
    router_action_results : Annotated[list[RouterActionResult], add]
    router_error_type : str | None
    router_error_message : str | None 


def create_initial_agent_state(user_query: str) -> AgentState:
    """
    创建一次 Agent 查询的初始状态。
    """

    return {
        "user_query": user_query,
        "router_batch": None,
        "router_round_number": 0,
        "router_action_results": [],
        "router_error_type": None,
        "router_error_message": None,
    }


__all__ = ["AgentState", "create_initial_agent_state"]

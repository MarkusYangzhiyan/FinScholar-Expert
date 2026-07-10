"""定义 FinScholar Expert 的 LangGraph 主状态骨架。

本模块集中维护 AgentState，避免不同节点各自定义不兼容的 state 字段。
当前版本只覆盖 Calculator 最小垂直切片；后续会逐步扩展路由、工具结果、
证据链、审计事件和最终回答等字段。
"""

from typing import Any, TypedDict

from finscholar.schemas.calculator import  CalculatorOutput


class AgentState(TypedDict,total = False):
    """FinScholar Expert 的 LangGraph 主状态。

    total=False 表示字段可以按需逐步写入。
    LangGraph 节点通常只返回自己负责更新的字段，也就是 state 增量。
    """

    user_query : str 

    calculator_input : dict[str,Any] | None

    calculator_output : CalculatorOutput | None

    calculator_error_type : str | None

    calculator_error_message : str | None


def create_initial_agent_state(user_query:str) -> AgentState:
    """创建最小 Agent 初始状态。

    这个函数用于测试和后续 LangGraph 入口，保证初始 state 结构稳定。
    """

    return {
        "user_query":user_query,
        "calculator_input":None,
        "calculator_output":None,
        "calculator_error_type":None,
        "calculator_error_message":None,
    }

__all__ = [
    "AgentState",
    "create_initial_agent_state"
]
"""测试 AgentState 初始状态构造。"""

from finscholar.state.agent_state import create_initial_agent_state


def test_create_initial_agent_state() -> None:
    """create_initial_agent_state 应返回稳定的最小初始状态。"""

    state = create_initial_agent_state("帮我计算利润率")

    assert state["user_query"] == "帮我计算利润率"
    assert state["calculator_input"] is None
    assert state["calculator_output"] is None
    assert state["calculator_error_type"] is None
    assert state["calculator_error_message"] is None
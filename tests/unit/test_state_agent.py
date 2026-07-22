"""测试 AgentState 初始状态构造。"""

from finscholar.state.state_agent import create_initial_agent_state


def test_create_initial_agent_state() -> None:
    """初始状态应满足多轮、多工具执行要求。"""

    state = create_initial_agent_state(
        "查询 TSLA 行情并计算涨幅"
    )

    assert state == {
        "user_query": "查询 TSLA 行情并计算涨幅",
        "router_batch": None,
        "router_round_number": 0,
        "router_action_results": [],
        "router_error_type": None,
        "router_error_message": None,
    }
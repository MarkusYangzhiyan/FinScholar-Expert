"""手动验证 FinScholar Agent 的完整运行链路。"""

import asyncio
import json
from typing import Any

from finscholar.config.settings import get_settings
from finscholar.runtime.agent_runtime import AgentRuntime
from finscholar.state.agent_state import AgentState


def build_error(
    error_type: str | None,
    error_message: str | None,
) -> dict[str, str | None] | None:
    """生成结构化错误信息。"""

    if error_type is None:
        return None

    return {
        "type": error_type,
        "message": error_message,
    }


def summarize_state(
    state: AgentState,
) -> dict[str, Any]:
    """提取完整链路中的关键结构化结果。"""

    decision = state.get("router_decision")
    output = state.get("yahoo_finance_output")

    yahoo_result = None

    if output is not None:
        yahoo_result = {
            "query": output.query.model_dump(mode="json"),
            "evidence": output.evidence.model_dump(
                mode="json",
                exclude={"content"},
            ),
            "data_point_count": len(output.data_points),
            "latest_data_points": [
                point.model_dump(mode="json")
                for point in output.data_points[-5:]
            ],
        }

    return {
        "user_query": state.get("user_query"),
        "router_decision": (
            decision.model_dump(mode="json")
            if decision is not None
            else None
        ),
        "router_error": build_error(
            state.get("router_error_type"),
            state.get("router_error_message"),
        ),
        "yahoo_finance": yahoo_result,
        "yahoo_finance_error": build_error(
            state.get("yahoo_finance_error_type"),
            state.get("yahoo_finance_error_message"),
        ),
    }


async def main() -> None:
    """执行一次完整 Agent 请求。"""

    settings = get_settings()
    runtime = AgentRuntime.from_settings(settings)

    try:
        state = await runtime.invoke(
            "查询特斯拉 TSLA 最近一个月的每日历史行情"
        )
    finally:
        await runtime.close()

    print(
        json.dumps(
            summarize_state(state),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
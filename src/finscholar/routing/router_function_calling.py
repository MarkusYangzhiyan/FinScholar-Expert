"""定义不同 Router 模型共用的 Function Calling 协议。"""

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from finscholar.clients.router_client import RouterResponseError
from finscholar.schemas.calculator import CalculatorInput
from finscholar.schemas.router import RouterDecision
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput

ROUTER_SYSTEM_PROMPT = """
你是 FinScholar Expert 的工具路由器。
你必须调用且仅调用一个函数，不要直接回答用户问题。
无法安全确定工具或参数时调用 Unsupported。
reason 只写简短依据，不要输出思维过程。
""".strip()


def _parameters_with_reason(model: type[BaseModel]) -> dict[str, Any]:
    """在工具输入 Schema 中增加路由依据字段。"""

    schema = model.model_json_schema()

    schema["properties"]["reason"] = {
        "type": "string",
        "minLength": 1,
        "maxLength": 500,
    }

    schema["required"] = [*schema.get("required", []), "reason"]

    return schema


ROUTER_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "Math_Calculator",
            "description": "执行受限且精确的数学计算。",
            "parameters": _parameters_with_reason(CalculatorInput),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Yahoo_Finance_Tool",
            "description": "查询结构化历史行情和金融指标。",
            "parameters": _parameters_with_reason(YahooFinanceHistoryInput),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Unsupported",
            "description": "当前工具无法安全处理用户请求。",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string", "minLength": 1, "maxLength": 500}},
                "required": ["reason"],
                "additionalProperties": False,
            },
        },
    },
]


def parse_router_tool_call(*, name: str, raw_arguments: str) -> RouterDecision:
    """把模型返回的 Tool Call 转换为 RouterDecision。"""

    try:
        arguments = json.loads(raw_arguments)

        if not isinstance(arguments, dict):
            raise ValueError("工具参数必须是 JSON 对象")

        reason = arguments.pop("reason", None)

        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("工具参数缺少 reason")

        reason = reason.strip()

        if name == "Yahoo_Finance_Tool":
            return RouterDecision(
                selected_tool=name,
                reason=reason,
                yahoo_finance_input=YahooFinanceHistoryInput.model_validate(arguments),
            )

        if name == "Math_Calculator":
            return RouterDecision(
                selected_tool=name,
                reason=reason,
                calculator_input=CalculatorInput.model_validate(arguments),
            )

        if name == "Unsupported" and not arguments:
            return RouterDecision(selected_tool=name, reason=reason)

        raise ValueError("模型返回了未知工具或多余参数")

    except (TypeError, ValueError, ValidationError) as exc:
        raise RouterResponseError("Router 工具调用参数无效") from exc


__all__ = [
    "ROUTER_SYSTEM_PROMPT",
    "ROUTER_TOOLS",
    "parse_router_tool_call",
]

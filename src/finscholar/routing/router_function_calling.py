"""定义不同 Router 模型共用的 Function Calling 协议。"""

import json
from typing import Any

from pydantic import BaseModel, ValidationError

from finscholar.clients.client_router import RouterResponseError
from finscholar.schemas.calculator import CalculatorInput
from finscholar.schemas.schemas_router import RouterAction, RouterBatch
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput

ROUTER_SYSTEM_PROMPT = """
你是 FinScholar Expert 的工具路由器。
输入是当前轮的 RouterContext JSON。

你每次只规划当前这一轮：
1. 可以调用一个或多个参数已经完整、相互没有依赖的工具。
2. 依赖本轮执行结果的工具必须留到下一轮，不得提前猜测参数。
3. 已有 action_results 足以回答用户时，只调用 Finalize。
4. 当前系统无法安全处理问题时，只调用 Unsupported。
5. Finalize 和 Unsupported 不得与其他函数同时调用。
6. 不要直接回答用户问题。
7. reason 只写简短依据，不要输出思维过程。
8. 用户未明确指定可选参数时，使用工具 Schema 默认值。
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


def _reason_only_parameters() -> dict[str, Any]:
    """定义 Finalize 和 Unsupported 的参数。"""

    return {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500,
            }
        },
        "required": ["reason"],
        "additionalProperties": False,
    }


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
            "name": "Finalize",
            "description": "已有工具结果足以生成最终回答时，结束工具调用。",
            "parameters": _reason_only_parameters(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "Unsupported",
            "description": "当前工具无法安全处理用户请求。",
            "parameters": _reason_only_parameters(),
        },
    },
]


def _parse_tool_arguments(
    raw_arguments: str,
) -> tuple[dict[str, Any], str]:
    """解析并取出一次 Tool Call 的参数和原因。"""

    arguments = json.loads(raw_arguments)

    if not isinstance(arguments, dict):
        raise ValueError("工具参数必须是 JSON 对象")

    reason = arguments.pop("reason", None)

    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("工具参数缺少 reason")

    return arguments, reason.strip()


def _build_router_action(
    *,
    name: str,
    arguments: dict[str, Any],
    reason: str,
) -> RouterAction:
    """将一个可执行 Tool Call 转换成 RouterAction。"""

    if name == "Yahoo_Finance_Tool":
        return RouterAction(
            selected_tool=name,
            reason=reason,
            yahoo_finance_input=(YahooFinanceHistoryInput.model_validate(arguments)),
        )

    if name == "Math_Calculator":
        return RouterAction(
            selected_tool=name,
            reason=reason,
            calculator_input=CalculatorInput.model_validate(arguments),
        )

    raise ValueError("模型返回了未知工具")


def parse_router_tool_calls(
    *,
    tool_calls: list[tuple[str, str]],
) -> RouterBatch:
    """将本轮一个或多个 Tool Call 转换成 RouterBatch。"""

    try:
        if not tool_calls:
            raise ValueError("Router 没有返回工具调用")

        parsed_calls = [
            (
                name,
                *_parse_tool_arguments(raw_arguments),
            )
            for name, raw_arguments in tool_calls
        ]

        control_calls = [call for call in parsed_calls if call[0] in {"Finalize", "Unsupported"}]

        if control_calls:
            if len(parsed_calls) != 1:
                raise ValueError("Finalize 或 Unsupported 不得与其他工具同时调用")

            name, arguments, reason = control_calls[0]

            if arguments:
                raise ValueError(f"{name} 不得包含多余参数")

            return RouterBatch(
                status=("finalize" if name == "Finalize" else "unsupported"),
                reason=reason,
            )

        actions = [
            _build_router_action(
                name=name,
                arguments=arguments,
                reason=reason,
            )
            for name, arguments, reason in parsed_calls
        ]

        batch_reason = (
            actions[0].reason if len(actions) == 1 else f"本轮执行 {len(actions)} 个相互独立的工具"
        )

        return RouterBatch(
            status="execute",
            reason=batch_reason,
            actions=actions,
        )

    except (TypeError, ValueError, ValidationError) as exc:
        raise RouterResponseError("Router 工具调用批次无效") from exc


__all__ = [
    "ROUTER_SYSTEM_PROMPT",
    "ROUTER_TOOLS",
    "parse_router_tool_calls",
]

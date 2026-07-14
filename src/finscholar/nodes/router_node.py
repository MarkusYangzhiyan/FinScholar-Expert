"""定义规则版 Router Node，用于最小 LangGraph 垂直切片。

当前 Router 不调用 Qwen3.5，也不做复杂自然语言理解。
它只负责通过 reg_patterns.toml 中的配置化正则规则生成 RouterDecision，
便于本地开发阶段验证 AgentState、Node、Tool 和 Graph 的完整链路。

后续接入 Qwen3.5 RouterClient 时，仍然应输出符合 RouterDecision
Schema 的结构化结果。
"""

from decimal import Decimal, InvalidOperation
from re import Pattern
from typing import Any, TypedDict

from pydantic import ValidationError

from finscholar.config.reg_patterns import (
    RegexPatternConfigError,
    get_regex_pattern,
)
from finscholar.schemas.calculator import CalculatorInput
from finscholar.schemas.router import RouterDecision, ToolName
from finscholar.state.agent_state import AgentState
from finscholar.schemas.yahoo_finance import YahooFinanceHistoryInput

class RouterNodeUpdate(TypedDict, total=False):
    """Router Node 写回 AgentState 的局部增量。"""

    router_selected_tool: ToolName | None
    router_decision: RouterDecision | None
    router_reason: str | None
    router_error_type: str | None
    router_error_message: str | None

    # Router 会为 Calculator Node 准备这个字段。  from user_query
    calculator_input: dict[str, Any] | None
    yahoo_finance_input : dict[str,Any] | None


def run_router_node(state: AgentState) -> RouterNodeUpdate:
    """执行规则版 Router，并返回对 AgentState 的局部更新。"""

    user_query = state.get("user_query")

    if user_query is None or not user_query.strip():
        return {
            "router_selected_tool": None,
            "router_decision": None,
            "router_reason": None,
            "router_error_type": "MissingUserQuery",
            "router_error_message": "state 中缺少 user_query",
            "calculator_input": None,
        }

    try:
        decision = _make_rule_based_decision(
            user_query=user_query,
            existing_calculator_input=state.get("calculator_input"),
            existing_yahoo_finance_input=state.get("yahoo_finance_input"),
        )
    except RegexPatternConfigError as exc:
        return {
            "router_selected_tool": None,
            "router_decision": None,
            "router_reason": None,
            "router_error_type": "RegexPatternConfigError",
            "router_error_message": str(exc),
            "calculator_input": None,
        }
    except ValidationError as exc:
        return {
            "router_selected_tool": None,
            "router_decision": None,
            "router_reason": None,
            "router_error_type": "RouterInputValidationError",
            "router_error_message": str(exc),
            "calculator_input": None,
        }

    return _decision_to_update(decision)


def _make_rule_based_decision(
    user_query: str,
    existing_calculator_input: dict[str, Any] | None,
    existing_yahoo_finance_input: dict[str, Any] | None,
) -> RouterDecision:
    """根据配置化正则规则生成 RouterDecision。

    规则优先级：
    1. 如果 state 已经提供 calculator_input，则校验后直接选择 Calculator；
    2. 如果能从 user_query 中识别利润率问题，则生成 Calculator 参数；
    3. 如果能识别显式表达式，则生成 Calculator 参数；
    4. 否则返回 Unsupported。
    """

    if existing_yahoo_finance_input is not None:
        yahoo_finance_input = (
            YahooFinanceHistoryInput.model_validate(
                existing_yahoo_finance_input
            )
        )

        return RouterDecision(
            selected_tool="Yahoo_Finance_Tool",
            reason=(
                "state 中已存在 yahoo_finance_input，"
                "Router 校验后选择 Yahoo Finance"
            ),
            yahoo_finance_input=yahoo_finance_input,
        )

    if existing_calculator_input is not None:
        calculator_input = CalculatorInput.model_validate(existing_calculator_input)

        return RouterDecision(
            selected_tool="Math_Calculator",
            reason="state 中已存在 calculator_input，Router 校验后选择 Calculator",
            calculator_input=calculator_input,
        )

    profit_margin_input = _parse_profit_margin_query(user_query)

    if profit_margin_input is not None:
        return RouterDecision(
            selected_tool="Math_Calculator",
            reason="识别到利润率计算问题，选择 Calculator",
            calculator_input=profit_margin_input,
        )

    expression_input = _parse_explicit_expression_query(user_query)

    if expression_input is not None:
        return RouterDecision(
            selected_tool="Math_Calculator",
            reason="识别到显式数学表达式，选择 Calculator",
            calculator_input=expression_input,
        )

    return RouterDecision(
        selected_tool="Unsupported",
        reason="规则版 Router 无法安全识别该问题所需工具",
        calculator_input=None,
    )


def _parse_profit_margin_query(user_query: str) -> CalculatorInput | None:
    """从简单利润率问题中抽取 profit 和 revenue。"""

    profit_margin_pattern = get_regex_pattern("router.profit_margin_query")

    if profit_margin_pattern.search(user_query) is None:
        return None

    profit = _extract_decimal(
        pattern=get_regex_pattern("router.profit"),
        text=user_query,
    )
    revenue = _extract_decimal(
        pattern=get_regex_pattern("router.revenue"),
        text=user_query,
    )

    if profit is None or revenue is None:
        return None

    return CalculatorInput(
        expression="profit / revenue * 100",
        variables={
            "profit": profit,
            "revenue": revenue,
        },
        unit="%",
    )


def _parse_explicit_expression_query(
    user_query: str,
) -> CalculatorInput | None:
    """识别显式表达式，例如：表达式: 1 + 2 * 3。"""

    expression_pattern = get_regex_pattern("router.explicit_expression")

    match = expression_pattern.search(user_query)

    if match is None:
        return None

    expression = match.group("expression").strip()
    unit = _extract_unit(
        pattern=get_regex_pattern("router.unit"),
        text=user_query,
    )

    return CalculatorInput(
        expression=expression,
        variables={},
        unit=unit,
    )


def _extract_decimal(
    pattern: Pattern[str],
    text: str,
) -> Decimal | None:
    """按配置化正则提取 value 分组，并转换为 Decimal。"""

    match = pattern.search(text)

    if match is None:
        return None

    raw_value = match.groupdict().get("value")

    if raw_value is None:
        return None

    try:
        return Decimal(raw_value)
    except InvalidOperation:
        return None


def _extract_unit(
    pattern: Pattern[str],
    text: str,
) -> str | None:
    """按配置化正则提取 unit 分组。"""

    match = pattern.search(text)

    if match is None:
        return None

    return match.group("unit")


def _decision_to_update(decision: RouterDecision) -> RouterNodeUpdate:
    """将 RouterDecision 转换为 AgentState 局部更新。"""

    calculator_input = None

    if decision.calculator_input is not None:
        # 使用 json 模式，让写入 state 的 calculator_input 更接近模型工具调用参数。
        calculator_input = decision.calculator_input.model_dump(mode="json")

    return {
        "router_selected_tool": decision.selected_tool,
        "router_decision": decision,
        "router_reason": decision.reason,
        "router_error_type": None,
        "router_error_message": None,
        "calculator_input": calculator_input,
    }


__all__ = [
    "RouterNodeUpdate",
    "run_router_node",
]

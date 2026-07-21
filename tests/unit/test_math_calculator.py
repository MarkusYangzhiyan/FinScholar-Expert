"""测试 Math_Calculator 的安全算术计算行为。"""

from decimal import Decimal

import pytest

from finscholar.schemas.calculator import CalculatorInput
from finscholar.tools.math_calculator import (
    CalculationExecutionError,
    MathCalculator,
    UnknownVariableError,
    UnsafeExpressionError,
)

# ----------------------------------------------------
# 最小正向测试
# 公式可导入、变量值可导入、能计算出结果、单元符号符合、计算时间保存
# ----------------------------------------------------


def test_math_calculator_can_calculate_profit_margin() -> None:
    """
    Calculator 可以根据利润和收入计算利润率。
    """

    request = CalculatorInput(
        expression="profit / revenue * 100",
        variables={
            "profit": Decimal("25"),
            "revenue": Decimal("100"),
        },
        unit="%",
    )

    result = MathCalculator().calculate(request)

    assert result.formula == "profit / revenue * 100"
    assert result.input_values == {
        "profit": Decimal("25"),
        "revenue": Decimal("100"),
    }
    assert result.result == Decimal("25.00")
    assert result.unit == "%"
    assert result.calculated_at.tzinfo is not None


# ----------------------------------------------------
# 一元正负号运算
# ----------------------------------------------------
def test_math_calculator_can_negate_variable() -> None:
    """Calculator 应支持对变量使用一元负号。"""

    request = CalculatorInput(
        expression="-profit",
        variables={
            "profit": Decimal("25"),
        },
    )

    result = MathCalculator().calculate(request)

    assert result.formula == "-profit"
    assert result.input_values == {
        "profit": Decimal("25"),
    }
    assert result.result == Decimal("-25")
    assert result.unit is None


def test_math_calculator_can_negate_parenthesized_expression() -> None:
    """Calculator 应支持对括号中的完整表达式使用一元负号。"""

    request = CalculatorInput(
        expression="-(1 + 2)",
        variables={},
    )

    result = MathCalculator().calculate(request)

    assert result.formula == "-(1 + 2)"
    assert result.input_values == {}
    assert result.result == Decimal("-3")
    assert result.unit is None


# ------------------------------------------------------
# 未知变量/缺少变量 报错
# ------------------------------------------------------


def test_math_calculator_rejects_unknown_variable() -> None:
    """表达式引用未提供变量时必须报错。"""

    request = CalculatorInput(
        expression="profit / revenue",
        variables={
            "profit": Decimal("25"),
        },
    )

    with pytest.raises(UnknownVariableError):
        MathCalculator().calculate(request)


# -------------------------------------------------------
# 除0错误
# -------------------------------------------------------


def test_math_calculator_rejects_division_by_zero() -> None:
    """除数为 0 时必须报错，不能静默返回无限值。"""

    request = CalculatorInput(
        expression="profit / revenue",
        variables={
            "profit": Decimal("25"),
            "revenue": Decimal("0"),
        },
    )

    with pytest.raises(CalculationExecutionError):
        MathCalculator().calculate(request)


# --------------------------------------------------------------
# expression禁止调用函数
# --------------------------------------------------------------
def test_math_calculator_rejects_function_call() -> None:
    """禁止函数调用，防止模型构造任意代码执行入口。"""

    request = CalculatorInput(
        expression="abs(profit)",
        variables={
            "profit": Decimal("-25"),
        },
    )

    with pytest.raises(UnsafeExpressionError):
        MathCalculator().calculate(request)


# -----------------------------------------------------------
# expression 禁止访问属性
# ------------------------------------------------------------
def test_math_calculator_rejects_attribute_access() -> None:
    """禁止属性访问，防止访问对象内部属性。"""

    request = CalculatorInput(
        expression="profit.__class__",
        variables={
            "profit": Decimal("25"),
        },
    )

    with pytest.raises(UnsafeExpressionError):
        MathCalculator().calculate(request)


# --------------------------------------------------------------
# expression禁止下标访问
# --------------------------------------------------------------


def test_math_calculator_rejects_subscript_access() -> None:
    """禁止下标访问，Calculator 只接受标量计算。"""

    request = CalculatorInput(
        expression="profit[0]",
        variables={
            "profit": Decimal("25"),
        },
    )

    with pytest.raises(UnsafeExpressionError):
        MathCalculator().calculate(request)


# -------------------------------------------------------
# 指数最大值限制
# --------------------------------------------------------


def test_math_calculator_rejects_too_large_power() -> None:
    """禁止过大的指数运算，避免资源消耗异常。"""

    request = CalculatorInput(
        expression="base ** exponent",
        variables={
            "base": Decimal("2"),
            "exponent": Decimal("101"),
        },
    )

    with pytest.raises(UnsafeExpressionError):
        MathCalculator().calculate(request)

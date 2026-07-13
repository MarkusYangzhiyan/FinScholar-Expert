"""
接收  CalculatorInput
用 AST 白名单解析表达式
禁止 eval/import/函数调用/属性访问
用 Decimal 做金融计算
返回 CaluculatorOutput
"""

import ast
from datetime import UTC, datetime
from decimal import Decimal, DivisionByZero, InvalidOperation, localcontext

from finscholar.schemas.calculator import CalculatorInput, CalculatorOutput


class CalculatorError(ValueError):
    """Math_Calculator 的基础异常"""


class UnsafeExpressionError(CalculatorError):
    """表达式包含不允许的语法或运算。"""


class UnknownVariableError(CalculatorError):
    """表达式引用了未提供的变量。"""


class CalculationExecutionError(CalculatorError):
    """表达式通过安全检查后，在计算阶段失败。"""


class MathCalculator:
    """使用 AST 白名单和 Decimal 执行安全金融算术计算。"""

    # 防止模型生成超长表达式，造成解析或计算资源浪费。
    _max_ast_nodes: int = 100

    # 防止指数运算造成巨大数值或性能问题。
    _max_power_abs: Decimal = Decimal("100")

    def calculate(self, request: CalculatorInput) -> CalculatorOutput:
        """执行一次安全计算，并返回可审计的结构化结果。"""

        try:
            ast_parsed_expression = ast.parse(request.expression, mode="eval")

        except SyntaxError as exc:
            raise UnsafeExpressionError(f"表达式语法错误：{request.expression}") from exc

        self._validate_ast_size(ast_parsed_expression)

        try:
            # 无菌实验室
            with localcontext() as context:
                context.prec = 38  # 精度
                result = self._evaluate(ast_parsed_expression, request.variables)

            pass
        except CalculatorError:
            raise
        except (ArithmeticError, InvalidOperation, DivisionByZero) as exc:
            raise CalculationExecutionError("计算失败") from exc

        return CalculatorOutput(
            formula=request.expression,
            input_values=request.variables,
            result=result,
            unit=request.unit,
            calculated_at=datetime.now(UTC),
        )

    def _validate_ast_size(self, ast_parsed_expression: ast.AST) -> None:
        """限制表达式复杂度，避免异常长表达式消耗资源。"""

        # 遍历整棵树，每有一个节点就计1，计算共有多少个节点
        node_count = sum(1 for _ in ast.walk(ast_parsed_expression))

        if node_count > self._max_ast_nodes:
            raise UnsafeExpressionError(
                f"表达式过于复杂：AST 节点数量 {node_count} 超过限制 {self._max_ast_nodes} "
            )

    def _evaluate(
        self,
        ast_parsed_expression: ast.AST,
        variables: dict[str, Decimal],
    ) -> Decimal:
        """递归计算 AST 节点，只允许白名单语法。"""

        if isinstance(ast_parsed_expression, ast.Expression):
            return self._evaluate(ast_parsed_expression.body, variables)

        if isinstance(ast_parsed_expression, ast.Constant):
            return self._evaluate_constant(ast_parsed_expression)

        if isinstance(ast_parsed_expression, ast.Name):
            return self._evaluate_name(ast_parsed_expression, variables)

        if isinstance(ast_parsed_expression, ast.UnaryOp):
            return self._evaluate_unary(ast_parsed_expression, variables)

        if isinstance(ast_parsed_expression, ast.BinOp):
            return self._evaluate_binary(ast_parsed_expression, variables)

        raise UnsafeExpressionError(f"不允许的表达式语法：{type(ast_parsed_expression).__name__}")

    def _evaluate_constant(self, ast_parsed_expression: ast.Constant) -> Decimal:
        """将数字常量转换为 Decimal。"""

        value = ast_parsed_expression.value

        # bool 是 int 的子类，所以必须单独禁止。
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise UnsafeExpressionError("只允许数字常量")

        return Decimal(str(value))

    def _evaluate_name(
        self,
        ast_parsed_expression: ast.Name,
        variables: dict[str, Decimal],
    ) -> Decimal:
        """读取表达式中的变量值。"""

        try:
            return variables[ast_parsed_expression.id]

        except KeyError as exc:
            raise UnknownVariableError(
                f"表达式引用了未提供的变量：{ast_parsed_expression.id}"
            ) from exc

    # 一元运算
    def _evaluate_unary(
        self, ast_parsed_expression: ast.UnaryOp, variables: dict[str, Decimal]
    ) -> Decimal:
        """处理正号和负号。"""

        # 操作数的数值是多少
        # ast_parsed_expression.operand： 看一下符号后的对象的数值是多少
        # 符号后的对象可能是一个复杂公式，所以还要用_evaluate()公式检查
        operand = self._evaluate(ast_parsed_expression.operand, variables)

        if isinstance(ast_parsed_expression.op, ast.UAdd):
            return operand

        if isinstance(ast_parsed_expression.op, ast.USub):
            return -operand

        raise UnsafeExpressionError(f"不允许的一元运算：{type(ast_parsed_expression.op).__name__}")

    def _evaluate_binary(
        self, ast_parsed_expression: ast.BinOp, variables: dict[str, Decimal]
    ) -> Decimal:
        """处理加、减、乘、除、幂运算。"""

        left = self._evaluate(ast_parsed_expression.left, variables)
        right = self._evaluate(ast_parsed_expression.right, variables)

        if isinstance(ast_parsed_expression.op, ast.Add):
            return left + right

        if isinstance(ast_parsed_expression.op, ast.Sub):
            return left - right

        if isinstance(ast_parsed_expression.op, ast.Mult):
            return left * right

        if isinstance(ast_parsed_expression.op, ast.Div):
            if right == 0:
                raise CalculationExecutionError("分母不能为0")

            return left / right

        if isinstance(ast_parsed_expression.op, ast.Pow):
            return self._evaluate_power(left, right)

        raise UnsafeExpressionError(f"不允许的二元运算：{type(ast_parsed_expression.op).__name__}")

    def _evaluate_power(
        self,
        left: Decimal,
        right: Decimal,
    ) -> Decimal:
        """处理指数运算，并限制指数大小。"""

        if right != right.to_integral_value():
            raise UnsafeExpressionError("指数必须是整数")

        if abs(right) > self._max_power_abs:
            raise UnsafeExpressionError(f"指数绝对值不能超过 {self._max_power_abs}")

        return left ** int(right)


__all__ = [
    "CalculationExecutionError",
    "CalculatorError",
    "MathCalculator",
    "UnknownVariableError",
    "UnsafeExpressionError",
]

import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

_VARIABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z_]*$")


class CalculatorInput(BaseModel):
    """规范和检查传入Math_Calculator工具的数据
    BaseModel: 用数据实例化这个类时，Pydantic会自动验证数据类型和规则"""

    model_config = ConfigDict(
        extra="forbid"  # 禁止传入任何未在类中定义的额外字段
    )

    expression: str = Field(
        min_length=1,
        max_length=500,
        description="只包含白名单算术运算的表达式",
    )

    # decimal 代表高精度数字
    variables: dict[str, Decimal] = Field(
        default_factory=dict, description="表达式使用的变量及其精确数值"
    )

    unit: str | None = Field(
        default=None,
        max_length=64,
    )

    # 在创建这个对象之前，请以类的名义拦截指定的字段，并运行下面的检查逻辑
    # classmethod:类方法，在数据刚传进来、对象还没真正建好之前，这个方法就可以直接在类的层面上运行了
    # field_validator:当有人想要给括号里指定的字段赋值时，必须先通过下面这个函数的检查
    @field_validator(
        "expression"
    )  
    @classmethod  
    def validate_expression(cls, value: str) -> str:
        """清理表达式无用空格并禁止空白输入。"""

        expression = value.strip()

        if not expression:
            raise ValueError("expression 不得为空")

        return expression

    @field_validator("variables")
    @classmethod
    def validate_variable_names(
        cls,
        value: dict[str, Decimal],
    ) -> dict[str, Decimal]:
        """变量名必须是普通 Python 标识符，禁止比如 user.password 或者 drop_table; 
        等可能引发安全漏洞的写法"""

        invalid_names = [name for name in value if not _VARIABLE_NAME_PATTERN.fullmatch(name)]

        if invalid_names:
            invalid_names_list = ",".join(sorted(invalid_names))
            raise ValueError(f"存在非法变量名{invalid_names_list}")

        return value


class CalculatorOutput(BaseModel):
    """Math_Calculator工具成功执行后的结构化结果。"""

    model_config = ConfigDict(extra="forbid")

    # 保留原始公式，便于审计和结果复算。
    formula: str

    # 保留计算输入，不只保存最终结果。
    input_values: dict[str, Decimal]

    # 计算结果必须是 Decimal
    result: Decimal

    # 原样保留调用方提供的单位。
    unit: str | None = None

    calculated_at: datetime

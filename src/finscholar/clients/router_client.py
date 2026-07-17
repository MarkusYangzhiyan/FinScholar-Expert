"""
定义的是统一接口

它不调用任何模型，只规定：
所有 Router Client 都必须接收 user_query，并返回 RouterDecision。

具体实现可以是：
RouterClient
├── QwenRouterClient
├── FakeRouterClient
└── 未来的其他模型Client

"""

from typing import Protocol

from finscholar.schemas.router import RouterDecision


class RouterClient(Protocol):
    async def route(
        self,
        user_query: str,
    ) -> RouterDecision:
        """
        将 用户问题 转化成 结构化路由决策
        """
        ...


# 下面两类错误的公共父类
class RouterClientError(RuntimeError):
    """Router Client 调用失败。"""


# 连接失败、超时、vLLM 服务异常
class RouterServiceError(RouterClientError):
    """Qwen/vLLM 服务请求失败。"""


# 模型没有调用工具、调用多个工具、参数 JSON 错误
class RouterResponseError(RouterClientError):
    """Qwen 返回内容无法转换成 RouterDecision。"""


__all__ = [
    "RouterClient",
    "RouterClientError",
    "RouterResponseError",
    "RouterServiceError",
]

from typing import Self

import httpx
from openai import APIError, AsyncOpenAI

from finscholar.clients.client_router import RouterResponseError, RouterServiceError
from finscholar.config.settings import Settings
from finscholar.routing.router_function_calling import (
    ROUTER_SYSTEM_PROMPT,
    ROUTER_TOOLS,
    parse_router_tool_call,
)
from finscholar.schemas.schemas_router import RouterDecision


class DeepSeekRouterClient:
    """调用 DeepSeek API 完成工具路由。"""

    def __init__(self, *, client: AsyncOpenAI, model: str, enable_thinking: bool) -> None:
        self._client = client
        self._model = model
        self._enable_thinking = enable_thinking

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        """根据统一配置创建 DeepSeek Router Client。"""

        api_key = settings.deepseek_api_key

        if api_key is None:
            raise ValueError("使用 DeepSeek Router 时必须配置 DEEPSEEK_API_KEY")

        timeout = httpx.Timeout(
            settings.deepseek_request_timeout_seconds, connect=settings.http_connect_timeout_seconds
        )

        client = AsyncOpenAI(
            api_key=api_key.get_secret_value(),
            base_url=settings.deepseek_base_url,
            timeout=timeout,
            max_retries=settings.http_max_retries,
        )

        return cls(
            client=client,
            model=settings.deepseek_model,
            enable_thinking=settings.deepseek_router_thinking_enabled,
        )

    async def route(self, user_query: str) -> RouterDecision:
        """请求 DeepSeek 并返回结构化路由决策。"""

        query = user_query.strip()

        if not query:
            raise RouterResponseError("user_query must not be empty")

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                tools=ROUTER_TOOLS,
                tool_choice="required",
                parallel_tool_calls=False,
                temperature=0,
                extra_body={
                    "thinking": {"type": ("enabled" if self._enable_thinking else "disabled")}
                },
            )

        except APIError as exc:
            raise RouterServiceError("DeepSeek Router 服务调用失败") from exc

        tool_calls = response.choices[0].message.tool_calls if len(response.choices) == 1 else None

        if tool_calls is None or len(tool_calls) != 1:
            raise RouterResponseError("DeepSeek Router 必须返回一次工具调用")

        tool_call = tool_calls[0]

        return parse_router_tool_call(
            name=tool_call.function.name, raw_arguments=tool_call.function.arguments
        )

    async def close(self) -> None:
        """关闭底层 HTTP 连接。"""

        await self._client.close()


__all__ = ["DeepSeekRouterClient"]

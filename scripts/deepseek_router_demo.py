import json 
import asyncio
from typing import Any
from finscholar.config.settings import get_settings
from finscholar.clients.deepseek_router_client import DeepSeekRouterClient
from finscholar.clients.client_router import RouterClientError



async def main() -> None:
    """调用 DeepSeek 并打印结构化路由结果。"""

    settings = get_settings()

    if settings.router_backend != "deepseek":
        raise RuntimeError("运行此脚本前需要设置ROUTER_BACKEND=deepseek")
    
    client = DeepSeekRouterClient.from_settings(settings)

    result : dict[str, Any]

    try:
        decision = await client.route("查询特斯拉 TSLA 最近一个月的每日历史行情")

        result = {
            "status": "success",
            "decision":decision.model_dump(mode = "json"),
        }

    except RouterClientError as exc:
        result = {
            "status":"error",
            "error_type":type(exc).__name__,
            "error_message": str(exc),
        }
    
    finally:
        await client.close()

    
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    asyncio.run(main())
                           
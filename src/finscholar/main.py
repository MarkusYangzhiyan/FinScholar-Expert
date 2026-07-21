"""创建 FinScholar Expert FastAPI 应用。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from finscholar.api.routes.agent_query_route import (
    router as agent_query_router,
)
from finscholar.config.settings import get_settings
from finscholar.runtime.agent_runtime import AgentRuntime

"""
yield 之前：应用启动
yield 期间：应用正在运行和处理请求
yield 之后：应用关闭

每个服务进程初始化一次。如果 Uvicorn 启动 4 个 Worker，那么每个 Worker 各有一个 Runtime，
不是整台机器绝对只有一个


"""

# 服务真正启动时，进入 lifespan(app)
@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    """管理 AgentRuntime 的启动和关闭。"""

    # 读取 .env → Pydantic Settings 校验 → 得到统一配置对象
    settings = get_settings()
    runtime = AgentRuntime.from_settings(settings)

    # app.state：当前 FastAPI 应用进程共享的对象存放区
    app.state.agent_runtime = runtime

    try:
        # lifespan 执行到 yield
        yield
    finally:
        app.state.agent_runtime = None
        await runtime.close()


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用。"""

    # 创建 FastAPI 服务端应用
    application = FastAPI(
        title="FinScholar Expert API",
        version="0.1.0",
        lifespan=lifespan,  
    )
    
    # 注册 Agent Route
    # 注册以后，FastAPI 才知道：POST /v1/agent/query
    application.include_router(agent_query_router)

    return application


app = create_app()


__all__ = [
    "app",
    "create_app",
]
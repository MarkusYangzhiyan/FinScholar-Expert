"""
集中读取并校验 FinScholar Expert 的环境变量与项目路径配置。
定义Calculator的输入输出结构
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_project_root() -> Path:
    """向上查找包含 pyproject.toml 的项目根目录。"""

    search_starts = (
        Path.cwd().resolve(),  # 当前工作目录
        Path(__file__).resolve().parent,  # 当前模块所在目录
    )

    for start in search_starts:
        for candidate in (start, *start.parents):
            if (candidate / "pyproject.toml").is_file():
                return candidate

    raise RuntimeError("无法定位项目根目录：未找到 pyproject.toml")


def _resolve_project_path(
    root: Path,
    value: Path,
    field_name: str,
) -> Path:
    """将项目相对路径安全解析到 PROJECT_ROOT 之下。"""

    candidate = value.expanduser()
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (root / candidate).resolve()
    # 防止通过 ../../ 等方式逃逸到项目根目录之外。
    try:
        resolved.relative_to(root)
    except ValueError as e:
        raise ValueError(f"{field_name} 必须位于 PROJECT_ROOT 下：{resolved}") from e

    return resolved


class Settings(BaseSettings):
    """FinScholar Expert 的统一强类型配置对象。"""

    model_config = SettingsConfigDict(
        # 默认读取项目当前目录下的.env
        env_file=str(_find_project_root() / ".env"),
        env_file_encoding="utf-8",
        # 环境变量没有统一前缀
        env_prefix="",
        # 忽略大小写
        case_sensitive=False,
        # .env 中出现未定义字段时直接报错，避免配置拼写错误。
        extra="forbid",
        # 允许 .env 中使用 KEY= 表示暂未配置。
        env_ignore_empty=True,
        validate_default=True,
    )

    # --------------------------------------------------
    # 主应用
    # --------------------------------------------------

    app_env: Literal["development", "test", "production"] = "development"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8080, ge=1, le=65535)

    app_log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"

    # 允许哪个前端地址访问我们的后端API（默认允许本地 3000 端口的比如 React/Vue 访问）
    app_cors_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1:3000"])

    gpu_operations_enabled: bool = False

    # PROJECT_ROOT 为空时自动发现。
    project_root: Path | None = None

    data_dir: Path = Path("data")
    artifact_dir: Path = Path("artifacts")
    log_dir: Path = Path("logs")
    run_dir: Path = Path("run")

    # -----------------------------------------------------
    # 统一网络策略
    # -----------------------------------------------------
    # 连接超时
    http_connect_timeout_seconds: float = Field(default=10, gt=0)
    # 读取超时
    http_read_timeout_seconds: float = Field(default=60, gt=0)
    # 重试次数
    http_max_retries: int = Field(default=3, ge=0, le=10)
    # 重试间隔时间
    http_retry_backoff_seconds: float = Field(default=3, ge=0)

    # -----------------------------------------------------------------
    # Modelscope 与本地模型
    # -----------------------------------------------------------------

    # SecretStr 可防止 Token 在日志中被直接打印。
    modelscope_token: SecretStr | None = None
    modelscope_cache: Path = Path("cache/modelscope")

    qwen_modelscope_id: str = "Qwen/Qwen3.5-4B"
    qwen_modelscope_revision: str | None = None
    qwen_model_path: Path = Path("models/pretrained/qwen3.5-4b")

    bge_m3_modelscope_id: str = "BAAI/bge-m3"
    bge_m3_modelscope_revision: str | None = None
    embedding_model_path: Path = Path("models/pretrained/bge-m3")

    bge_reranker_modelscope_id: str = "BAAI/bge-reranker-v2-m3"
    bge_reranker_modelscope_revision: str | None = None
    reranker_model_path: Path = Path("models/pretrained/bge-reranker-v2-m3")

    # 微调模型补丁
    lora_adapter_path: Path = Path("models/lora/finscholar-router")

    # ----------------------------------------------------------
    # 本地 Qwen Router
    # ----------------------------------------------------------

    router_backend: Literal["vllm"] = "vllm"
    # vLLM 在本地 8000 端口提供 OpenAI 兼容接口。
    qwen_base_url: str = "http://127.0.0.1:8000/v1"
    # 本地服务无需真实密钥，EMPTY 用于满足客户端的非空校验。
    qwen_api_key: SecretStr = SecretStr("EMPTY")
    qwen_model: str = "qwen-router"
    qwen_enable_thinking: bool = False
    qwen_request_timeout_seconds: float = Field(
        default=30,
        gt=0,
    )

    # -------------------------------------------------------------
    # DeepSeek-v4 API
    # -------------------------------------------------------------

    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str | None = None
    deepseek_model: str | None = None
    deepseek_request_timeout_seconds: float = Field(
        default=300,
        gt=0,
    )

    # --------------------------------------------------------------
    # Qwen3.7-plus 视觉 API
    # --------------------------------------------------------------

    dashscope_api_key: SecretStr | None = None
    # 请求地址
    dashscope_base_url: str | None = None
    qwen_vl_model: str = "qwen3.7-plus"
    qwen_vl_request_timeout_seconds: float = Field(
        default=300,
        gt=0,
    )

    # ------------------------------------------------------------------
    # LightRAG
    # ------------------------------------------------------------------

    # 本地运行
    lightrag_enabled: bool = True
    lightrag_base_url: str = "http://127.0.0.1:9621"
    lightrag_working_dir: Path = Path("data/lightrag")

    # 查询模式
    lightrag_query_mode: Literal[
        "naive",  # 传统RAG - 语义相似度
        "local",  # 局部图谱 - 提取关键字（实体） - 知识图谱找节点
        "global",  # 全局图谱 - 社区级总结和关系检索
        "hybrid",  # 混合图谱 - local+global - 又看节点又看总结摘要
        "mix",  # 全能模式 - naive+local+global
    ] = "mix"

    lightrag_llm_backend: Literal["deepseek"] = "deepseek"

    lightrag_vector_storage: Literal["MilvusVectorDBStorage"] = "MilvusVectorDBStorage"

    lightrag_kv_storage: str | None = None
    lightrag_graph_storage: str | None = None
    lightrag_doc_status_storage: str | None = None

    lightrag_request_timeout_seconds: float = Field(
        default=120,
        gt=0,
    )

    # ------------------------------------------------------------------
    # 父子切分与混合检索
    # ------------------------------------------------------------------

    chunk_strategy: Literal["parent_child"] = "parent_child"

    # Parent Chunk 用于保存完整上下文。
    parent_chunk_target_tokens: int = Field(
        default=1000,
        ge=500,
        le=2000,
    )

    parent_chunk_max_tokens: int = Field(
        default=1400,
        ge=600,
        le=3000,
    )

    parent_chunk_overlap_tokens: int = Field(
        default=100,
        ge=0,
        le=300,
    )

    # Child Chunk 用于向量化、BM25 召回和 Reranker。
    child_chunk_target_tokens: int = Field(
        default=300,
        ge=150,
        le=500,
    )

    child_chunk_min_tokens: int = Field(
        default=150,
        ge=50,
        le=300,
    )

    child_chunk_max_tokens: int = Field(
        default=450,
        ge=200,
        le=800,
    )

    child_chunk_overlap_tokens: int = Field(
        default=60,
        ge=0,
        le=150,
    )

    # 检索到 Child 后，最多展开多少个 Parent。
    parent_context_top_k: int = Field(
        default=6,
        ge=1,
        le=20,
    )

    # 同一 Parent 最多保留多少个命中的 Child 证据。
    max_children_per_parent: int = Field(
        default=3,
        ge=1,
        le=20,
    )

    embedding_backend: Literal["bge-m3"] = "bge-m3"
    embedding_dimension: Literal[1024] = 1024

    reranker_backend: Literal["bge-reranker-v2-m3"] = "bge-reranker-v2-m3"

    dense_top_k: int = Field(default=30, ge=1, le=200)
    sparse_top_k: int = Field(default=30, ge=1, le=200)
    lightrag_top_k: int = Field(default=30, ge=1, le=200)
    rerank_top_k: int = Field(default=10, ge=1, le=100)

    # ------------------------------------------------------------------
    # Milvus
    # ------------------------------------------------------------------

    vector_store_backend: Literal["milvus"] = "milvus"

    milvus_uri: str | None = None
    milvus_token: SecretStr | None = None
    milvus_database: str = "default"
    milvus_collection_prefix: str = "finscholar"

    milvus_dense_dimension: Literal[1024] = 1024

    milvus_metric_type: Literal[
        "COSINE",
        "IP",
        "L2",
    ] = "COSINE"

    # ------------------------------------------------------------------
    # 外部工具
    # ------------------------------------------------------------------

    tavily_api_key: SecretStr | None = None

    web_search_primary: Literal["tavily"] = "tavily"
    web_search_fallback: Literal["ddgs"] = "ddgs"

    wikipedia_language: str = "zh"

    wikipedia_user_agent: str = "FinScholar-Expert/0.1 contact=replace-with-email@example.com"

    arxiv_page_size: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    arxiv_delay_seconds: float = Field(
        default=3,
        ge=3,
    )

    arxiv_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
    )

    yfinance_request_timeout_seconds: float = Field(
        default=30,
        gt=0,
    )

    # ------------------------------------------------------------------
    # Python Sandbox
    # ------------------------------------------------------------------

    sandbox_backend: Literal["docker"] = "docker"
    sandbox_base_url: str | None = None
    # 断网模式
    sandbox_network_enabled: bool = False
    # 代码运行时间上限
    sandbox_timeout_seconds: float = Field(
        default=60,
        gt=0,
    )

    sandbox_memory_limit_mb: int = Field(
        default=1024,
        ge=128,
    )

    sandbox_cpu_limit: float = Field(
        default=1,
        gt=0,
    )

    # 限制单次任务可创建的进程数量。
    sandbox_process_limit: int = Field(
        default=64,
        ge=1,
    )

    # 限制标准输出和错误输出的总大小。
    sandbox_output_limit_bytes: int = Field(
        default=10_485_760,
        ge=1024,
    )

    # ------------------------------------------------------------------
    # 日志与审计
    # ------------------------------------------------------------------

    # 本地开发可以使用 console；生产环境应使用 json。
    log_format: Literal["json", "console"] = "json"

    # 审计功能不能代替普通应用日志。
    audit_enabled: bool = True

    # 审计记录使用 SHA-256 生成内容哈希。
    audit_hash_algorithm: Literal["sha256"] = "sha256"

    # 审计日志单独存放，避免与普通应用日志混合。
    audit_log_dir: Path = Path("logs/audit")

    # 审计日志保留天数，实际清理由后续日志模块执行。
    audit_retention_days: int = Field(
        default=360,
        ge=1,
        le=3650,
    )

    # 日志输出前必须对 API Key、Token 等敏感字段脱敏。
    audit_redact_secrets: bool = True

    # 默认不把完整私有文档正文写入审计日志。
    # 审计日志保留 content_hash、chunk_id 和文档定位信息。
    audit_include_content: bool = False

    # 当所有的基础字段（如整数是不是正数、字符串有没有拼错）都被 Pydantic 检查完之后，
    # 立刻自动执行这个函数，进行最终的“全局体检和数据加工”
    @model_validator(mode="after")
    def resolve_and_validate(self) -> Self:
        """解析项目路径并校验不会随部署环境变化的架构约束。"""

        root = (self.project_root or _find_project_root()).expanduser().resolve()

        self.project_root = root

        # 所有项目数据路径都必须位于 PROJECT_ROOT 下。
        path_fields = (
            "data_dir",
            "artifact_dir",
            "log_dir",
            "run_dir",
            "modelscope_cache",
            "qwen_model_path",
            "embedding_model_path",
            "reranker_model_path",
            "lora_adapter_path",
            "lightrag_working_dir",
            "audit_log_dir",
        )

        for field_name in path_fields:
            value = getattr(self, field_name)

            setattr(
                self,
                field_name,
                _resolve_project_path(
                    root=root,
                    value=value,
                    field_name=field_name,
                ),
            )

        self._validate_fixed_architecture()
        self._validate_chunk_settings()
        self._validate_production_requirements()
        self._validate_gpu_requirements()

        return self

    # ---------------------------------------
    # 交叉逻辑审查
    # ----------------------------------------

    def _validate_fixed_architecture(self) -> None:
        """校验项目中不允许通过环境变量改变的安全约束。"""

        # if self.qwen_enable_thinking:
        #     raise ValueError(
        #         "QWEN_ENABLE_THINKING 必须为 false"
        #     )

        if self.sandbox_network_enabled:
            raise ValueError("SANDBOX_NETWORK_ENABLED 必须为 false")

        if not self.audit_redact_secrets:
            raise ValueError("AUDIT_REDACT_SECRETS 必须为 true")

        if self.audit_include_content:
            raise ValueError("AUDIT_INCLUDE_CONTENT 必须为 false，禁止把完整私有文档写入审计日志")

    def _validate_chunk_settings(self) -> None:
        """校验 Parent/Child Chunk 参数之间的大小关系。"""

        # 父重叠大于父默认
        if self.parent_chunk_overlap_tokens >= self.parent_chunk_target_tokens:
            raise ValueError("PARENT_CHUNK_OVERLAP_TOKENS 必须小于 PARENT_CHUNK_TARGET_TOKENS")

        # 父默认大于父最大
        if self.parent_chunk_target_tokens > self.parent_chunk_max_tokens:
            raise ValueError("PARENT_CHUNK_TARGET_TOKENS 不得大于 PARENT_CHUNK_MAX_TOKENS")

        # 子重叠大于子默认
        if self.child_chunk_overlap_tokens >= self.child_chunk_target_tokens:
            raise ValueError("CHILD_CHUNK_OVERLAP_TOKENS 必须小于 CHILD_CHUNK_TARGET_TOKENS")

        # 子最小大于子默认
        if self.child_chunk_min_tokens > self.child_chunk_target_tokens:
            raise ValueError("CHILD_CHUNK_MIN_TOKENS 不得大于 CHILD_CHUNK_TARGET_TOKENS")

        # 子默认大于子最大
        if self.child_chunk_target_tokens > self.child_chunk_max_tokens:
            raise ValueError("CHILD_CHUNK_TARGET_TOKENS 不得大于 CHILD_CHUNK_MAX_TOKENS")

        # 子最大大于父默认
        if self.child_chunk_max_tokens >= self.parent_chunk_target_tokens:
            raise ValueError("CHILD_CHUNK_MAX_TOKENS 必须小于 PARENT_CHUNK_TARGET_TOKENS")

        if self.parent_context_top_k > self.rerank_top_k:
            raise ValueError("PARENT_CONTEXT_TOP_K 不得大于 RERANK_TOP_K")

        if self.max_children_per_parent > self.rerank_top_k:
            raise ValueError("MAX_CHILDREN_PER_PARENT 不得大于 RERANK_TOP_K")

    def _validate_production_requirements(self) -> None:
        """生产环境缺少关键服务配置时快速失败。"""

        if self.app_env != "production":
            return

        required_values = {
            "DEEPSEEK_API_KEY": self.deepseek_api_key,
            "DEEPSEEK_BASE_URL": self.deepseek_base_url,
            "DEEPSEEK_MODEL": self.deepseek_model,
            "DASHSCOPE_API_KEY": self.dashscope_api_key,
            "DASHSCOPE_BASE_URL": self.dashscope_base_url,
            "MILVUS_URI": self.milvus_uri,
            "SANDBOX_BASE_URL": self.sandbox_base_url,
            "TAVILY_API_KEY": self.tavily_api_key,
        }

        if self.lightrag_enabled:
            required_values.update(
                {
                    "LIGHTRAG_KV_STORAGE": self.lightrag_kv_storage,
                    "LIGHTRAG_GRAPH_STORAGE": self.lightrag_graph_storage,
                    "LIGHTRAG_DOC_STATUS_STORAGE": self.lightrag_doc_status_storage,
                }
            )

        missing = [name for name, value in required_values.items() if value is None]

        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"生产环境缺少必需配置：{missing_text}")

        if not self.audit_enabled:
            raise ValueError("生产环境不允许关闭审计功能")

        if self.log_format != "json":
            raise ValueError("生产环境 LOG_FORMAT 必须为 json")

        if "replace-with-email" in self.wikipedia_user_agent:
            raise ValueError("生产环境必须配置真实可识别的 WIKIPEDIA_USER_AGENT")

    def _validate_gpu_requirements(self) -> None:
        """开启 GPU 操作后检查本地模型目录。"""

        if not self.gpu_operations_enabled:
            return

        required_models = {
            "QWEN_MODEL_PATH": self.qwen_model_path,
            "EMBEDDING_MODEL_PATH": self.embedding_model_path,
            "RERANKER_MODEL_PATH": self.reranker_model_path,
        }

        missing = [name for name, path in required_models.items() if not path.is_dir()]

        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"GPU 操作已开启，但模型目录不存在：{missing_text}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回进程内复用的配置对象。"""

    return Settings()


def clear_settings_cache() -> None:
    """清空配置缓存，供单元测试重新加载环境变量。"""

    get_settings.cache_clear()


__all__ = [
    "Settings",
    "clear_settings_cache",
    "get_settings",
]

# FinScholar Expert 项目目录骨架

`FinScholar-Expert` 是项目的唯一根目录。本地 WSL2 与 AutoDL 使用相同的相对目录结构，只允许根目录的绝对路径不同：

- 本地 WSL2：`/home/ubuntu/FinScholar-Expert`
- AutoDL：`/root/autodl-tmp/FinScholar-Expert`

所有需要本地下载的模型统一从 ModelScope 获取。正式模型放在 `models/pretrained/`，ModelScope 下载缓存放在 `cache/modelscope/`。

## 1. 外层骨架总览

```text
FinScholar-Expert/
├── .git/                         # Git 仓库元数据
├── .gitignore                   # Git 忽略规则
├── .python-version              # Python 3.12 版本约定
├── .env.example                 # 环境变量契约，不含真实密钥
├── .env                         # 当前机器私有配置，不提交
│
├── pyproject.toml               # 主应用依赖与工具配置
├── uv.lock                      # 主应用锁文件
├── requirements-vllm.lock.txt   # vLLM 环境锁文件
├── requirements-train.in        # 训练环境直接依赖
├── requirements-train.lock.txt  # 训练环境锁文件
│
├── .venv/                       # 主应用环境，由 uv 生成
├── .venv-vllm/                  # Qwen/vLLM 推理环境
├── .venv-train/                 # LoRA 训练环境
│
├── src/                         # 可安装的 Python 业务代码
├── tests/                       # 分层测试与评测
├── deploy/                      # 基础设施和沙箱部署配置
├── scripts/                     # 初始化、入库、评测和迁移脚本
│
├── models/                      # 本地模型权重与 LoRA 产物
├── cache/                       # 可重新下载或生成的缓存
├── data/                        # 原始数据、处理数据和存储数据
├── artifacts/                   # 报告、图表、评测和训练产物
├── logs/                        # 应用、审计和训练日志
├── run/                         # PID 和临时运行状态
│
├── AGENTS.md                    # Agent 工程规范
├── README.md                    # 项目入口与目录说明
├── 项目背景与说明.md            # 业务背景与架构决策
└── 项目运行环境与启动SOP.md     # 环境初始化与运行流程
```

外层目录按职责分为四类：


| 类别         | 目录                             | 说明                                   |
| ------------ | -------------------------------- | -------------------------------------- |
| 工程代码     | `src/`、`tests/`、`scripts/`     | 需要版本管理的代码和测试               |
| 部署配置     | `deploy/`                        | Milvus、LightRAG 和 Sandbox 的部署定义 |
| 大文件与数据 | `models/`、`data/`、`artifacts/` | 模型、私有文档和生成产物，默认不提交   |
| 运行时目录   | `cache/`、`logs/`、`run/`        | 可重建的缓存、日志与临时状态           |

## 2. 模型与缓存分骨架

```text
models/
├── pretrained/                  # 从 ModelScope 下载完成的正式模型
│   ├── qwen3.5-4b/             # 本地 Router 模型
│   ├── bge-m3/                 # 1024 维 Dense Embedding 模型
│   └── bge-reranker-v2-m3/     # 混合召回重排模型
├── lora/
│   └── finscholar-router/       # Qwen3.5-4B 路由 LoRA Adapter
└── manifests/
    ├── qwen3.5-4b.json          # Model ID、Revision、校验值
    ├── bge-m3.json
    └── bge-reranker-v2-m3.json

cache/
├── modelscope/                  # ModelScope SDK/CLI 缓存
├── torch/                       # PyTorch 缓存
└── uv/                          # Python 包下载与构建缓存
```

`models/pretrained/` 表示“项目正式使用的预训练模型”，不将目录绑定到下载平台名称。`cache/modelscope/` 则明确表示 ModelScope 工具的可重建缓存。DeepSeek-v4 和 Qwen-VL-Max 是 API 服务，不在 `models/` 下保存权重。

## 3. 数据与产物分骨架

```text
data/
├── private_docs/                # 原始私有 PDF、财报和论文
├── processed/                   # 解析、OCR、表格与 Chunk 结果
├── lightrag/                    # LightRAG 工作数据和状态
├── milvus/                      # Milvus 本地持久化数据
└── evals/                       # 脱敏的检索和问答评测集

artifacts/
├── reports/                     # Markdown、HTML 或 PDF 报告
├── charts/                      # Python Sandbox 生成的图表
├── evaluations/                 # 评测结果与对比报告
└── training/                    # 训练指标和训练报告

logs/
├── app/                         # FastAPI、LangGraph 和工具日志
├── audit/                       # 证据链、Grader 与工具调用审计日志
└── training/                    # LoRA 训练日志

run/
├── pids/                        # 服务进程 PID
└── tmp/                         # 单次任务临时文件
```

`data/` 保存输入数据和可持续的中间状态；`artifacts/` 保存系统生成的可交付结果；`logs/` 和 `run/` 只服务于运行观测与进程管理。

## 4. 部署与脚本分骨架

```text
deploy/
├── compose.infra.yml             # Milvus、Attu、etcd、MinIO 固定版本编排
├── milvus/                      # Milvus 和依赖服务配置
├── lightrag/                    # LightRAG API/WebUI 部署配置
└── sandbox/                     # Dockerfile、Seccomp 和资源限制配置

scripts/
├── bootstrap/                   # 环境初始化与目录验收
├── ingestion/                   # 文档解析、切块和入库
├── evaluation/                  # 路由、RAG 和证据支持率评测
└── migration/                   # Embedding 更换和重新向量化
```

`deploy/` 只保存部署定义，不保存 Milvus 数据。`scripts/` 保存可重复执行的运维或数据流程，不应把业务逻辑从 `src/finscholar/` 复制到脚本中。

## 5. 测试分骨架

```text
tests/
├── unit/                         # 默认离线的单元测试
├── integration/                  # Milvus、LightRAG 和外部适配器集成测试
├── smoke/                        # 完整环境启动后的最小链路验证
├── evals/                        # 路由、检索和证据质量评测
└── fixtures/                     # Mock 响应、脱敏样本和公用测试数据
```

`unit/` 不访问真实网络、GPU 或付费 API；`integration/` 显式验证服务边界；`smoke/` 只验证部署后的关键链路；`evals/` 评估模型与 RAG 效果，不代替功能测试。

## 6. `src/finscholar` 内层代码骨架

```text
src/
└── finscholar/
    ├── __init__.py
    │
    ├── api/
    │   ├── app.py                    # FastAPI 应用入口
    │   ├── dependencies.py           # API 依赖注入
    │   └── routes/
    │       ├── health.py             # 健康检查
    │       ├── query.py              # Agent 查询接口
    │       └── documents.py          # 文档管理接口
    │
    ├── config/
    │   └── settings.py               # Pydantic Settings 与启动校验
    │
    ├── schemas/
    │   ├── evidence.py               # 来源、页码和证据对象
    │   ├── financial.py              # 币种、单位和报告期
    │   ├── tool.py                   # 工具输入输出契约
    │   └── api.py                    # API 请求与响应契约
    │
    ├── state/
    │   └── agent_state.py            # LangGraph 集中状态定义
    │
    ├── graph/
    │   ├── builder.py                # State Graph 构建
    │   ├── routes.py                 # 条件边决策
    │   └── policies.py               # 终止、重试与并发策略
    │
    ├── nodes/
    │   ├── router.py                 # Qwen3.5 路由节点
    │   ├── tool_executor.py          # 工具执行节点
    │   ├── doc_grader.py             # 文档相关性评估
    │   ├── generator.py              # 云端报告生成
    │   └── hallucination_grader.py   # 证据支持性校验
    │
    ├── tools/
    │   ├── base.py                   # 通用工具协议
    │   ├── market_wiki.py            # Market_Wiki_Tool
    │   ├── web_news.py               # Web_News_Search
    │   ├── arxiv_search.py           # ArXiv_Search_Tool
    │   ├── yahoo_finance.py          # Yahoo_Finance_Tool
    │   ├── calculator.py             # Math_Calculator
    │   ├── python_repl.py            # Python_REPL_Tool
    │   └── private_doc_rag.py        # Private_Doc_RAG 工具边界
    │
    ├── models/
    │   ├── protocols.py              # 模型能力协议
    │   ├── router_client.py          # Qwen Router 客户端
    │   ├── deepseek_client.py        # DeepSeek-v4 API 客户端
    │   ├── qwen_vl_client.py         # Qwen-VL-Max API 客户端
    │   ├── embedding_client.py       # BGE-M3 客户端
    │   └── reranker_client.py        # BGE Reranker 客户端
    │
    ├── rag/
    │   ├── parsing/                  # PDF、表格和图像解析
    │   ├── chunking/                 # 语义切块与页码映射
    │   ├── lightrag/                 # LightRAG Adapter
    │   ├── milvus/                  # Milvus Adapter 与 Collection
    │   ├── retrieval/               # Dense、BM25 和混合召回
    │   ├── reranking/               # BGE Reranker
    │   └── evidence/                # 去重、证据融合与引用组装
    │
    ├── sandbox/
    │   └── client.py                 # 外部 Python Sandbox 客户端
    │
    └── observability/
        ├── logging.py                # 结构化日志
        └── audit.py                  # 证据链与审计事件
```

`src/finscholar/models/` 只存放模型客户端和接口代码，不存放权重。`src/finscholar/rag/` 将解析、切块、LightRAG、Milvus、召回、重排和证据融合分开，避免把整条检索链写成单个函数。

`src/finscholar/` 下的每个 Python 包目录都应包含 `__init__.py`；上图为了可读性没有重复列出每一个 `__init__.py`。

## 7. 命名约定

- 仓库名可以使用 `FinScholar-Expert`，Python 包名使用可导入的 `finscholar`。

# AGENTS.md

## 2. 项目目标

FinScholar Expert 是面向金融投研、大宗商品分析与学术情报检索的单智能体系统。系统使用 Python 与 LangGraph 构建确定性的状态机工作流，融合公开数据、实时新闻、金融行情、学术论文和私有财报。

核心质量目标：

- 工具调用可控、可测试、可回放。
- 输出具有来源引用、页码定位与可审计证据链。
- 金融数值保留原始口径、币种、单位和报告期。
- 模型失败、数据缺失与证据冲突必须显式暴露。
- 本地与 AutoDL 使用相同的软件依赖环境。

不得使用“100% 事实正确”“绝对精准”等无法验证的承诺。

## 3. 已确定的架构决策

除非用户明确要求修改，否则不得擅自替换以下决策。

### 3.1 工作流

- 使用 LangGraph 构建 State Graph。
- 使用显式节点、条件边、终止条件和有限重试。
- 保留 Doc Grader 与 Hallucination Grader。
- 不引入不可控的开放式强化学习探索流程。
- 独立工具可并发执行；结果合并必须确定、可复现。

### 3.2 模型职责


| 职责     | 模型或服务         | 约束                                                 |
| -------- | ------------------ | ---------------------------------------------------- |
| 本地路由 | Qwen3.5-4B         | 关闭思考模式；负责意图、JSON 策略和 Function Calling |
| 云端生成 | DeepSeek-v4 API    | 具体 Model ID 由配置提供，不得硬编码                 |
| 视觉解析 | Qwen-3.7-plus API | 用于复杂图表、表格与图片解析                         |
|          |                    |                                                      |

LangGraph 节点不得直接加载 Qwen、BGE 或 Reranker。模型能力必须通过可替换的客户端或服务接口注入，例如 `RouterClient`、`EmbeddingService` 和 `RerankerService`。

### 3.3 七个工具

必须保留以下业务边界：

1. `Market_Wiki_Tool`：宏观概念和通用背景。
2. `Web_News_Search`：实时财经新闻。
3. `ArXiv_Search_Tool`：论文元数据和摘要。
4. `Yahoo_Finance_Tool`：行情和结构化金融指标。
5. `Math_Calculator`：受限算术计算。
6. `Python_REPL_Tool`：沙盒分析和图表生成。
7. `Private_Doc_RAG`：私有文档的多模态混合检索。

不得把多个工具的网络访问、业务规则和数据清洗全部堆入单个 LangGraph 节点。

### 3.4 RAG

- LightRAG 是 `Private_Doc_RAG` 的核心组成。
- LangGraph 负责上层 Agent 状态机与工具编排；LightRAG 负责知识图谱构建、图谱检索和文档检索。
- 检索必须融合传统混合 RAG 与 LightRAG：BGE-M3 Dense、BM25 Sparse、LightRAG 图谱/向量召回和 Reranker 共同组成完整链路。
- 向量数据库使用 Milvus，管理界面使用 Attu。
- LightRAG 的 Vector Storage 使用 `MilvusVectorDBStorage`。
- LightRAG 的 KV、Graph 与 Doc Status Storage 必须通过配置明确选择；生产环境不得无意使用默认的本地文件存储。
- LightRAG 查询优先评估 `mix` 模式，以融合 Knowledge Graph 与 Vector Retrieval；最终模式和 Top-K 必须由检索评测确定。
- LightRAG WebUI 用于文档状态、查询调试和知识图谱可视化，但不得替代项目面向用户的应用接口。
- 检索采用 BGE-M3 Dense + BM25 Sparse 双路召回，再接 Reranker。
- Milvus Dense 字段维度必须为 1024。
- 建库与查询必须使用同一 Embedding 模型和版本。
- 更换 Embedding 模型必须显式迁移并重新向量化，不得复用旧向量。

LightRAG 的实体关系抽取和查询生成使用 DeepSeek-v4 AP。Qwen3.5-4B 只负责 Agent 工具路由。视觉角色使用 Qwen-3.7-plus，Embedding 使用 BGE-M3，Reranker 使用 BGE-Reranker-v2-M3。

## 4. 证据与审计规范

所有外部工具和 RAG 结果必须返回结构化数据，不得只返回一段无来源文本。

证据对象至少应包含：

```text
source_type
source_name
source_uri
document_id
page_number
section_title
chunk_id
retrieved_at
content
content_hash
```

不适用字段可以为空，但不得伪造。网页或 API 没有页码时必须通过 URL、记录 ID、发布时间和抓取时间定位。

金融数据还必须包含：

```text
symbol
metric_name
value
currency
unit
period_start
period_end
as_of_date
provider
```

要求：

- 区分事实、计算结果、模型判断和预测。
- 计算结果保留输入值、公式和单位换算过程。
- 同一指标来源冲突时不得静默选择，必须记录冲突和选择依据。
- Hallucination Grader 只能校验“输出是否受证据支持”，不得把模型自评当成事实证明。
- 最终报告引用必须可回溯到原始工具结果或文档位置。

## 5. 环境规范

### 5.1 统一环境

- Python：3.12。
- 包管理器和虚拟环境工具：`uv`。
- 不使用 Conda 管理项目依赖。

三个环境均在本地和 AutoDL 创建：


| 环境          | 用途                                                               | 依赖来源                                                |
| ------------- | ------------------------------------------------------------------ | ------------------------------------------------------- |
| `.venv`       | 主应用、LangGraph、LightRAG Core/API/WebUI、工具、RAG 客户端与测试 | `pyproject.toml` + `uv.lock`                            |
| `.venv-vllm`  | Qwen3.5 推理与 LoRA 加载                                           | `requirements-vllm.lock.txt`                            |
| `.venv-train` | LoRA 数据处理与训练                                                | `requirements-train.in` + `requirements-train.lock.txt` |

本地只延迟执行需要 4090 的模型加载、推理、训练和部署操作，不得通过删减依赖维护另一套环境。

物理 GPU、NVIDIA 驱动、API 密钥和服务地址属于机器运行层，可以不同；Python 依赖版本和配置字段必须一致。

### 5.2 模型下载与存储

- 所有需要下载到本地的模型统一从 ModelScope 获取。
- 下载完成、可被项目直接加载的模型固定放在 `models/pretrained/`；ModelScope 下载缓存放在 `cache/modelscope/`。
- Qwen3.5-4B、BGE-M3 和 BGE-Reranker-v2-M3 必须记录 ModelScope Model ID、Revision、下载时间和校验信息，记录文件放在 `models/manifests/`。
- 代码和启动命令使用由 `PROJECT_ROOT` 派生的本地模型路径，不得依赖运行时隐式网络下载。
- DeepSeek-v4 和 Qwen-3.7-plus 是 API 服务，不在 `models/` 中创建本地权重目录。

## 6. 目录规范

本地根目录：

```text
/home/ubuntu/FinScholar-Expert
```

AutoDL 根目录：

```text
/root/autodl-tmp/FinScholar-Expert
```

## 7. 推荐代码结构

`rag/` 中应明确区分 LightRAG Adapter、Milvus Adapter、BM25 Retriever、Reranker 与 Evidence Fusion，不得把整个检索链路写成单个函数。

## 8. Python 编码规范

- 新代码必须有类型标注。
- 使用 Pydantic V2 定义外部输入、工具参数、工具结果和 API 响应。
- I/O 密集型网络和数据库操作优先使用 `async`，不得在异步节点中执行长时间阻塞调用。
- 所有外部请求必须设置连接超时、读取超时、有限重试和退避策略。
- 重试只覆盖临时性错误；认证失败、参数错误和数据校验错误不得盲目重试。
- 使用 UTC 保存时间，展示层再转换时区。
- 金融金额禁止使用二进制浮点完成最终精确计算；使用 `Decimal` 或经过验证的数值方案。
- 不使用裸 `except:`，不得吞掉异常。
- 错误信息不得泄露密钥、Token、私有文档内容或完整请求头。
- 公共接口、关键业务规则和复杂算法需要简洁 Docstring。
- 优先小模块和组合，不创建全知全能的 Manager 类。

格式与静态检查以 Ruff 和 mypy 配置为准。禁止通过大范围 `# noqa`、`type: ignore` 或关闭规则掩盖设计问题。

## 9. LangGraph 规范

- 状态字段必须集中定义并具有明确类型。
- 节点只完成一个可描述的业务动作。
- 节点输入、输出和可能异常必须可测试。
- 路由结果必须通过 Schema 校验，不直接信任模型产生的 JSON。
- 条件边必须覆盖成功、可重试失败、不可重试失败和终止状态。
- 所有循环必须具有最大次数或明确终止条件。
- 并发工具任务必须互相独立，并设置单任务超时。
- 合并并发结果时保留来源，不得只拼接自然语言。
- Grader 的输入、输出、阈值和触发回退原因必须写入审计事件。

不得将业务关键规则只写在 Prompt 中；能用代码、Schema 和状态边界约束的规则必须工程化实现。

## 10. 工具实现规范

每个工具至少包含：

- 稳定的工具名称和用途说明。
- Pydantic 输入 Schema。
- 结构化输出 Schema。
- 超时、重试和速率限制处理。
- 来源与抓取时间。
- 可注入客户端，便于 Mock。
- 成功、空结果、限流、无效输入和上游失败测试。

工具不得：

- 返回未经标注来源的事实。
- 在日志中记录完整 API Key。
- 静默用另一个数据源替代失败的数据源。
- 把网页搜索摘要当作已验证财务事实。
- 无限制抓取或绕过服务限流。

特别约束：

- Wikipedia 请求必须配置可识别的 User-Agent。
- arXiv 查询需要缓存并遵守请求间隔。
- DuckDuckGo 相关库不得描述为稳定的官方全文搜索 API。
- `yfinance` 数据必须附带提供方和抓取时间；不得把它描述为商业级授权行情源。
- Calculator 仅允许白名单数学操作，禁止任意 `eval`。
- Python REPL 必须在沙盒内运行，禁止退化为主进程 `exec`。

## 11. Sandbox 安全要求

Python Sandbox 默认必须：

- 禁止外网。
- 使用非特权用户。
- 根文件系统只读。
- 只挂载单次任务临时目录。
- 限制 CPU、内存、进程数、输出大小和执行时间。
- 任务结束后销毁容器和临时文件。
- 禁止挂载 Docker Socket、项目 `.env`、SSH Key 或主机敏感目录。

AutoDL 普通容器不支持 Docker。没有已批准的外部 Sandbox 时，不得声称完整执行环境可用，也不得在主应用进程中直接执行生成代码。

## 12. 配置与密钥

- 使用 `.env.example` 维护完整配置契约。
- 真实值写入未跟踪的 `.env`，文件权限应为 `600`。
- 配置由 Pydantic Settings 读取并在启动时校验。
- `GPU_OPERATIONS_ENABLED=false` 只禁止 GPU 操作，不允许切换为另一套依赖环境。
- 模型 ID、Base URL、Milvus URI、数据目录和超时不得散落硬编码。
- 缺少必需配置时快速失败，并指出缺失字段；不得使用不安全默认值继续运行。

提交前检查 `.env`、日志、Notebook 输出、测试快照和异常信息中是否包含秘密。

## 13. 测试规范

### 13.1 测试层级

- `tests/unit`：默认离线、无 GPU、无真实网络、无真实付费 API。
- `tests/integration`：验证 Milvus、工具适配器和服务边界；通过标记与环境变量显式开启。
- `tests/smoke`：AutoDL 或完整集成环境启动后的最小链路验证。
- `tests/evals`：路由准确率、参数合法率、检索质量和报告证据支持率。

### 13.2 必测内容

- Qwen 路由 JSON Schema 校验与非法输出恢复。
- 七个工具的成功、空结果、限流、超时和异常。
- LangGraph 每条条件边与最大重试次数。
- BGE-M3 Dense 向量维度为 1024。
- 混合召回、去重、Reranker 和 Top-K。
- LightRAG 实体关系索引、`mix` 查询、图谱/向量结果融合和 WebUI/API 健康状态。
- 文档页码、Chunk 与最终引用的映射。
- 金融单位、币种、报告期和 Decimal 计算。
- Sandbox 越权、网络、超时与资源限制。
- Hallucination Grader 对“有证据、缺证据、证据冲突”的处理。

## 14. 变更工作流

执行编码任务时遵循：

1. 阅读相关设计、实现和测试，确认影响范围。
2. 优先做最小、内聚、可回滚的修改。
3. 先更新或新增测试，再验证相关测试和静态检查。
4. 配置、接口、目录或启动方式改变时同步更新 SOP 和 `.env.example`。
5. 最终说明修改文件、验证结果、未覆盖风险和必要的后续步骤。

未经用户明确授权不得：

- 创建、切换或删除 Git 分支和其他git操作。
- 删除用户文件、数据、模型或向量库。
- 清空缓存或重建 Milvus Collection。
- 调用产生明显费用的批量 API 或模型任务。
- 修改既定模型、七工具边界或端云架构。
- 仅以降低费用为理由替换用户已经确定的组件或设计另一套“最低成本方案”。

## 15. 文档规范

- 文档和代码注释以中文为主，标准技术名词保留英文。
- 命令必须注明适用环境：本地、AutoDL 或 Docker 主机。
- 路径优先使用项目根目录相对路径；必须写绝对路径时同时说明适用机器。
- 示例不得包含真实 Token、主机地址、私有文档名或客户信息。
- 修改架构说明时检查模型名称、环境数量、目录与 SOP 是否一致。

## 16. 完成标准

任务只有同时满足以下条件才算完成：

- 实现符合当前用户需求和既定架构。
- 没有破坏证据链、页码定位和审计字段。
- 相关测试和静态检查通过，或明确说明无法执行的原因。
- 没有新增密钥、私有数据、模型缓存或大文件到 Git。
- 新增依赖已进入正确虚拟环境并更新对应锁文件。
- 配置和运行方式变化已同步文档。
- 工作区中用户原有修改得到保留。

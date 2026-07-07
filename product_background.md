# 🤖 FinScholar Expert: 企业级金融与学术双引擎智能体

## 📌 1. 项目背景 (Project Background)

在现代金融投研、大宗商品分析与科技情报挖掘中，分析师往往面临严重的“数据孤岛”**与**“工具割裂”问题。传统的 LLM 聊天机器人无法同时兼顾前沿学术算法检索（ArXiv）、宏观经济定义获取（Wikipedia）、实时市场动态追踪（News API）以及高度复杂的私有化财报解析（Multimodal RAG + LightRAG）。更致命的是，在金融与严谨学术场景下，大模型的“幻觉（Hallucination）”会导致整个研报结论的失效。

**FinScholar Expert** 旨在通过纯 Python 栈与状态机工作流，打造一个**高确定性、低成本落地**的单智能体系统。本项目主动摒弃了不可控的强化学习（RL）探索机制，采用 **端云结合（Edge-Cloud Orchestration）** 的异构大模型架构，在保障企业级数据隐私与执行效率的同时，使自动生成的投研报告具备来源引用、页码定位与可审计证据链。

## 🎯 2. 核心架构概述 (Architecture Overview)

本项目基于 **LangGraph** 构建底座，将复杂的 ReAct（推理-执行）逻辑重构为具备纠错机制的有向图结构（State Graph）。

### 2.1 端云异构双大脑模型 (Hybrid LLM Engine)

* **端侧路由大脑 (Local Router - Edge)：** 部署于本地单卡显卡（如 RTX 4090），核心采用经过 LoRA 定向微调的 **Qwen3.5-4B**，并在路由场景中关闭思考模式。模型专注意图识别、结构化 JSON 策略生成与 Function Calling，作为“交警”极速调度工具，实现高频交互零 API 成本。
* **云端推理大脑 (Cloud Generator - Cloud)：** 接入 **DeepSeek-v4 API**。专注于 LightRAG 实体关系抽取、复杂非结构化数据理解、长上下文推理与最终的深度研报撰写。

### 2.2 企业级状态机控制流 (LangGraph Workflow)

系统内置双重工程评估机制，死守金融数据准确性底线：

1. **Doc Grader (文档相关性评估)：** 动态过滤无效检索结果，降低上下文噪声。
2. **Hallucination Grader (反幻觉事实校验)：** 生成报告后反向比对数据源，若发生“数据捏造”，触发图节点条件边（Conditional Edge）自动回溯并重试。

## 🧰 3. 全链路 7 大工具矩阵 (The 7-Tool Arsenal)

Agent 具备自主调用以下垂直工具的能力，实现了从宏观到微观的数据闭环：

| 工具名称 | 功能描述 | 技术支撑 |
| --- | --- | --- |
| **Market_Wiki_Tool** | 宏观经济概念与通用行业背景检索 | `wikipedia` API |
| **Web_News_Search** | 获取 24 小时内突发财经新闻，弥补知识库滞后 | `Tavily` / `DuckDuckGo` API |
| **ArXiv_Search_Tool** | 检索前沿学术情报与算法论文摘要列表 | `arxiv` 官方 Python SDK |
| **Yahoo_Finance_Tool** | 抓取真实的股票 K 线、市盈率等结构化金融指标 | `yfinance` 库 |
| **Math_Calculator** | 安全沙盒计算器，解决 LLM 算术幻觉（如同比/CAGR计算） | Python REPL 限制执行 |
| **Python_REPL_Tool** | 高级代码解释器，根据数据自主生成数据可视化图表 | Docker Sandbox / Local REPL |
| **Private_Doc_RAG** | **(核心)** 多模态私有文档与知识图谱增强检索引擎 | LightRAG + Milvus + 混合检索 + Vision RAG |

## 📚 4. 工业级多模态 RAG 引擎 (Enterprise RAG Pipeline)

针对金融财报与学术论文中复杂的非结构化排版，本项目摒弃了传统的单一文本向量化方案：

* **LightRAG 图谱增强检索：** 将 LightRAG 作为 `Private_Doc_RAG` 的核心检索编排层，对文档实体与关系进行增量构图，并融合 Local、Global 与 Naive Retrieval；LangGraph 负责上层任务工作流，LightRAG 负责知识图谱与文档检索，两者职责相互独立。
* **多源融合向量库：** 底层采用支持百亿级扩展的 **Milvus** 向量数据库，并使用 **Attu** 提供直观的数据流可视化管理。
* **Vision RAG 解析：** 引入视觉大模型 API 处理 PDF 中的 Boxplot、架构图与复杂财务表格，将其转化为高精度文本描述后入库。
* **混合检索与重排：** 采用 `BGE-m3` 多语言模型，结合 Dense（稠密语义）+ BM25（稀疏关键词）双路召回，并与 LightRAG 的图谱召回结果融合，再串联 Reranker 模型进行 Top-K 截断，提升金融专有名词与跨文档关系检索的准确性；所有召回结果保留来源引用、页码定位与可审计证据链。

## 🚀 5. 系统工作流演练 (Workflow Execution)

1. **[Input]** 用户提问：“分析特斯拉近期财报利润率，并结合马斯克最新的具身智能学术布局，预测其相关技术对估值的影响，最后画一张营收走势图。”
2. **[Routing]** 本地 Qwen3.5-4B 在关闭思考模式后输出 JSON 策略，并发调度 `Private_Doc_RAG`、`ArXiv_Search_Tool` 与 `Python_REPL_Tool`。
3. **[Execution]** LightRAG 联合 Milvus 召回财报片段、实体与关系，ArXiv 抓取机器人控制论文，REPL 环境生成走势图。
4. **[Evaluation]** LangGraph 状态机验证数据有效性，过滤不相关论文。
5. **[Generation]** DeepSeek-v4 综合所有真实数据流，撰写并输出带有引用溯源的深度研报。

## 💡 6. 项目亮点与工程沉淀 (Key Takeaways)

* **极致的成本控制：** 验证了在单卡消费级算力（24G 显存）下，如何通过合成数据集与 LoRA 微调，将 4B 模型打造成高效、稳定的工具调度中枢。
* **防御性编程思维：** Agent 设计不盲目追求“自由探索”，而是通过 LangGraph 将 LLM 封装在严格的业务执行边界内，具备极高的商业落地可行性。
* **多语言与多模态兼容：** 彻底打通了中英双语检索壁垒与“图-文”数据解析孤岛。

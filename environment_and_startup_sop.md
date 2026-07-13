# FinScholar Expert 项目运行环境与启动 SOP

## 1. 文档信息


| 项目          | 内容                                                 |
| ------------- | ---------------------------------------------------- |
| 文档名称      | FinScholar Expert 项目运行环境与启动 SOP             |
| 适用环境      | 本地 WSL2 Ubuntu 24.04；AutoDL Ubuntu 24.04 GPU 环境 |
| Python 版本   | Python 3.12                                          |
| 环境管理工具  | `uv`                                                 |
| 主应用环境    | `.venv`                                              |
| 模型服务环境  | `.venv-vllm`，本地与 AutoDL 均创建                   |
| LoRA 训练环境 | `.venv-train`，本地与 AutoDL 均创建                  |
| 文档状态      | 初版                                                 |

本文规定“本地优先开发、AutoDL 按锁文件重建运行环境”的完整流程，包括本地虚拟环境、服务器选型、远端环境重建、密钥配置、日常启动、健康检查、停止服务和数据备份。

## 2. 核心原则

1. 项目统一使用 `uv`，不使用 Conda 管理项目依赖。
2. 本地与 AutoDL 都创建主应用 `.venv`、推理 `.venv-vllm` 和训练 `.venv-train`，并使用相同锁文件安装相同软件依赖。
3. 三个虚拟环境职责固定且相互隔离，禁止混装依赖；本地只是不执行需要 4090 的推理、训练和部署操作。
4. 不在操作系统中重复安装 CUDA Toolkit；优先使用 AutoDL 镜像提供的 NVIDIA 驱动和 CUDA 运行环境。
5. 本地与 AutoDL 使用相同的项目相对目录结构；所有项目文件都位于各自的 `FinScholar-Expert` 根目录下。
6. API 密钥只写入 `.env`，不得写入源码、日志或提交到 Git。
7. AutoDL 每次启动必须按照“基础设施 → 本地模型 → 主应用 → 健康检查”的顺序执行。
8. 不允许在同一个 Shell 中反复切换多个虚拟环境；启动服务时优先直接调用对应虚拟环境中的可执行文件。
9. 迁移到 AutoDL 时只迁移 Git 代码、锁文件和必要数据；三个虚拟环境必须按相同锁文件重建，禁止直接复制虚拟环境目录。
10. “环境一致”指 Ubuntu/Python 版本、项目依赖和配置契约一致；物理 GPU、NVIDIA 驱动、密钥与服务地址属于机器运行层，允许按机器配置不同值。

### 2.1 仓库文件契约

执行完整 SOP 前，代码仓库必须包含以下文件。缺失时说明项目尚未完成对应工程初始化，不应通过临时命令绕过：

```text
pyproject.toml                 # 主应用依赖定义
uv.lock                       # 主应用跨环境锁文件
requirements-vllm.lock.txt    # vLLM 推理环境锁文件
requirements-train.in         # LoRA 训练环境直接依赖清单
requirements-train.lock.txt   # LoRA 训练环境锁文件
.env.example
src/finscholar/api.py
tests/smoke/
deploy/compose.infra.yml      # 仅 Docker 部署方案需要
```

其中 `pyproject.toml` 与 `uv.lock` 管理主应用；`requirements-vllm.lock.txt` 与 `requirements-train.lock.txt` 分别锁定容易发生 CUDA/PyTorch 冲突的推理和训练环境。三个环境都先在本地创建并锁定，再在 AutoDL 重建。

### 2.2 同环境、延迟执行模式


| 位置      | 创建的环境                           | 软件依赖       | 实际执行范围                                                |
| --------- | ------------------------------------ | -------------- | ----------------------------------------------------------- |
| 本地 WSL2 | `.venv`、`.venv-vllm`、`.venv-train` | 与 AutoDL 相同 | 编码、静态检查、单元测试；暂不启动 GPU 推理、训练及部署服务 |
| AutoDL    | `.venv`、`.venv-vllm`、`.venv-train` | 与本地相同     | Qwen3.5 推理、BGE-M3、Reranker、LoRA 训练和全链路运行       |

业务代码仍需通过接口隔离模型能力。单元测试可以注入 Mock，但 Mock 只是测试替身，不代表本地使用另一套依赖环境。迁移到 AutoDL 后不修改代码或依赖版本，只开启 GPU 操作并填写机器相关配置。

### 2.3 本地开发环境初始化

当前本地项目根目录为：

```text
/home/ubuntu/FinScholar-Expert
```

进入仓库并确认根目录：

```bash
cd /home/ubuntu/FinScholar-Expert
git rev-parse --show-toplevel
```

先创建统一目录并把缓存固定到项目根目录：

```bash
export PROJECT_ROOT="$(git rev-parse --show-toplevel)"
mkdir -p models/modelscope models/lora
mkdir -p cache/torch cache/uv
mkdir -p logs run data artifacts

export HF_HOME="$PROJECT_ROOT/models/modelscope"
export modelscope_HUB_CACHE="$PROJECT_ROOT/models/modelscope/hub"
export TRANSFORMERS_CACHE="$PROJECT_ROOT/models/modelscope/transformers"
export TORCH_HOME="$PROJECT_ROOT/cache/torch"
export UV_CACHE_DIR="$PROJECT_ROOT/cache/uv"
export TOKENIZERS_PARALLELISM=false
```

退出可能存在的 Conda 环境并安装 `uv`：

```bash
conda deactivate 2>/dev/null || true
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

首次创建本地主应用环境：

```bash
test -f pyproject.toml || { echo 'ERROR: pyproject.toml 尚未创建'; exit 1; }
uv venv .venv --python 3.12 --seed
```

如果仓库已经存在 `uv.lock`：

```bash
uv sync --frozen --group dev
```

首次建立项目依赖时由项目维护者执行：

```bash
uv sync --group dev
```

随后必须提交 `pyproject.toml` 和 `uv.lock`。

在本地创建与 AutoDL 相同的 vLLM 环境：

```bash
uv venv .venv-vllm --python 3.12 --seed
```

第一次建立 vLLM 锁文件时执行：

```bash
uv pip install \
  --python .venv-vllm/bin/python \
  vllm \
  --torch-backend=auto \
  --extra-index-url https://wheels.vllm.ai/nightly

uv pip freeze \
  --python .venv-vllm/bin/python \
  > requirements-vllm.lock.txt
```

已有锁文件时严格同步：

```bash
uv pip sync \
  --python .venv-vllm/bin/python \
  requirements-vllm.lock.txt \
  --torch-backend=auto \
  --extra-index-url https://wheels.vllm.ai/nightly
```

创建与 AutoDL 相同的训练环境：

```bash
test -f requirements-train.in || { echo 'ERROR: requirements-train.in 尚未创建'; exit 1; }
uv venv .venv-train --python 3.12 --seed
```

第一次建立训练锁文件时执行：

```bash
uv pip install \
  --python .venv-train/bin/python \
  -r requirements-train.in

uv pip freeze \
  --python .venv-train/bin/python \
  > requirements-train.lock.txt
```

已有锁文件时严格同步：

```bash
uv pip sync \
  --python .venv-train/bin/python \
  requirements-train.lock.txt
```

三个环境及其锁文件建立后，确认所有目录均位于项目根目录：

```bash
test "$PROJECT_ROOT" = "/home/ubuntu/FinScholar-Expert"
test -d "$PROJECT_ROOT/models"
test -d "$PROJECT_ROOT/cache"
```

本地和 AutoDL 共用同一份 `.env.example` 配置契约。本地先创建私有 `.env`：

```bash
test -e .env || cp .env.example .env
chmod 600 .env
```

本地保留与 AutoDL 相同的后端声明，只关闭 GPU 操作：

```dotenv
APP_ENV=development
GPU_OPERATIONS_ENABLED=false
ROUTER_BACKEND=vllm
EMBEDDING_BACKEND=bge-m3
RERANKER_BACKEND=bge-reranker-v2-m3
VECTOR_STORE_BACKEND=milvus
SANDBOX_BACKEND=docker
```

本地单元测试可以通过测试夹具注入 Mock，但不得通过删减依赖、替换持久化实现或维护另一套项目环境来实现。

验证本地环境：

```bash
.venv/bin/python --version
.venv-vllm/bin/python --version
uv pip show --python .venv-vllm/bin/python vllm
.venv-train/bin/python --version
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
```

本地 GPU 与驱动不满足要求时，不执行 `torch.cuda.get_device_name()`、模型加载或 CUDA 健康检查；软件包成功安装、版本与锁文件一致即可。

### 2.4 本地日常开发启动

每次开始本地开发时执行：

```bash
cd /home/ubuntu/FinScholar-Expert
source "$HOME/.local/bin/env"
conda deactivate 2>/dev/null || true
export PROJECT_ROOT="$(git rev-parse --show-toplevel)"
export HF_HOME="$PROJECT_ROOT/models/modelscope"
export modelscope_HUB_CACHE="$PROJECT_ROOT/models/modelscope/hub"
export TRANSFORMERS_CACHE="$PROJECT_ROOT/models/modelscope/transformers"
export TORCH_HOME="$PROJECT_ROOT/cache/torch"
export UV_CACHE_DIR="$PROJECT_ROOT/cache/uv"
export TOKENIZERS_PARALLELISM=false
uv sync --frozen --group dev
uv pip sync \
  --python .venv-vllm/bin/python \
  requirements-vllm.lock.txt \
  --torch-backend=auto \
  --extra-index-url https://wheels.vllm.ai/nightly
uv pip sync \
  --python .venv-train/bin/python \
  requirements-train.lock.txt
.venv/bin/python -m pytest tests/unit -q
```

启动本地主应用：

```bash
.venv/bin/python -m uvicorn src.finscholar.api:app \
  --host 127.0.0.1 \
  --port 8080 \
  --reload
```

本地阶段只暂缓以下需要 GPU 或部署资源的操作：

- 启动 vLLM 并加载 Qwen3.5。
- 下载 Qwen3.5-4B 全量权重。
- 启动 LoRA 训练。
- 启动 Milvus、Attu、Sandbox 等部署服务。
- 执行 GPU 集成测试或性能测试。

### 2.5 从本地迁移到 AutoDL

虚拟环境不能迁移，必须在 AutoDL 根据锁文件重新创建。迁移前在本地执行：

```bash
cd /home/ubuntu/FinScholar-Expert
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
git status --short
sha256sum uv.lock requirements-vllm.lock.txt requirements-train.lock.txt
```

确认以下内容已经提交并推送：

- `src/`、`tests/`、配置模板和部署文件。
- `pyproject.toml` 与 `uv.lock`。
- 不包含密钥的 `.env.example`。
- `requirements-vllm.lock.txt`、`requirements-train.in` 和 `requirements-train.lock.txt`。

禁止提交或复制：

```text
.venv/
.venv-vllm/
.venv-train/
.env
models/modelscope/
cache/
logs/
run/
```

AutoDL 上通过 Git 获取相同代码：

```bash
cd /root/autodl-tmp
git clone <项目Git地址> FinScholar-Expert
cd FinScholar-Expert
uv venv .venv --python 3.12 --seed
uv sync --frozen
uv venv .venv-vllm --python 3.12 --seed
uv pip sync \
  --python .venv-vllm/bin/python \
  requirements-vllm.lock.txt \
  --torch-backend=auto \
  --extra-index-url https://wheels.vllm.ai/nightly
uv venv .venv-train --python 3.12 --seed
uv pip sync \
  --python .venv-train/bin/python \
  requirements-train.lock.txt
```

私有文档、训练集和 LoRA 产物不进入 Git，应通过对象存储、AutoDL 文件存储或 SCP 单独同步。API 密钥在 AutoDL 上从 `.env.example` 重新创建，禁止复制本地 `.env`。

## 3. AutoDL 实例选型要求

### 3.1 GPU 与资源

完整开发与集成环境建议选择：


| 资源   | 最低要求              | 推荐配置      |
| ------ | --------------------- | ------------- |
| GPU    | NVIDIA GPU，显存 24GB | RTX 4090 24GB |
| CPU    | 8 核                  | 12 核以上     |
| 内存   | 32GB                  | 64GB          |
| 数据盘 | 100GB                 | 200GB 以上    |
| 系统   | Ubuntu 24.04          | Ubuntu 24.04  |

### 3.2 Docker 硬性检查

AutoDL 普通容器实例内部不支持 Docker。项目中的 Milvus、Attu 和 Python Docker Sandbox 需要 Docker，因此完整运行必须满足以下方案之一：

- 方案 A：使用 AutoDL 裸金属服务器，在同一台服务器部署全部组件。
- 方案 B：AutoDL 普通 GPU 实例只运行主应用、Qwen3.5、BGE-M3 和 Reranker；Milvus、Attu 与 Python Sandbox 部署到外部 Docker 主机。

禁止把“Docker 命令不可用”当作普通告警后继续以完整模式启动。若 Docker 组件没有外部替代部署，环境验收应判定为失败。

## 4. 目录规范

本地和 AutoDL 使用相同的相对目录结构，只允许项目根目录的绝对路径不同：


| 环境      | 项目根目录                           |
| --------- | ------------------------------------ |
| 本地 WSL2 | `/home/ubuntu/FinScholar-Expert`     |
| AutoDL    | `/root/autodl-tmp/FinScholar-Expert` |

项目相关的环境、模型、缓存、数据和运行产物均必须位于 `FinScholar-Expert` 根目录之下：

```text
FinScholar-Expert/
├── .venv/                   # 主应用虚拟环境
├── .venv-vllm/              # Qwen/vLLM 环境，本地与 AutoDL 均创建
├── .venv-train/             # LoRA 训练环境，本地与 AutoDL 均创建
├── models/
│   ├── modelscope/         # modelscope 模型与下载缓存
│   └── lora/                # Qwen3.5 LoRA Adapter
├── cache/
│   ├── torch/               # PyTorch 缓存
│   └── uv/                  # uv 包缓存
├── logs/                    # 运行日志
├── run/                     # PID、运行状态文件
├── data/                    # 开发数据和上传文档
└── artifacts/               # 图表、报告和临时产物
```

禁止在项目根目录之外创建与项目相关的 `models`、`cache`、`logs`、`data` 或 `artifacts` 目录。

重要文件必须定期备份到 `/root/autodl-fs`、对象存储或本地电脑。AutoDL 数据盘不是永久备份介质。

## 5. AutoDL 首次初始化 SOP

本节仅在新建服务器、重装镜像或迁移实例后执行一次。

### 5.1 登录并检查服务器

从 AutoDL 控制台复制 SSH 命令，在本地终端登录：

```bash
ssh -p <SSH端口> root@<AutoDL主机地址>
```

执行环境检查：

```bash
source /root/.bashrc
nvidia-smi
python3 --version
free -h
df -h
```

验收标准：

- `nvidia-smi` 能识别目标 GPU，且显存符合租用配置。
- Python 版本为 3.12，或允许由 `uv` 安装受管的 Python 3.12。
- `/root/autodl-tmp` 数据盘剩余空间满足项目要求。
- 内存不少于 32GB。

### 5.2 安装系统基础工具

```bash
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  git \
  jq \
  tmux \
  build-essential \
  pkg-config \
  libgl1 \
  libglib2.0-0 \
  poppler-utils
```

验证：

```bash
git --version
curl --version
tmux -V
pdftotext -v
```

### 5.3 退出 Conda

AutoDL 镜像可能默认激活 Conda，执行：

```bash
conda deactivate 2>/dev/null || true
```

确认当前没有使用 Conda 环境：

```bash
echo "${CONDA_DEFAULT_ENV:-not-active}"
```

期望输出：

```text
not-active
```

如不希望每次登录自动进入 Conda base，可执行一次：

```bash
conda config --set auto_activate_base false
```

### 5.4 配置数据盘缓存

将以下内容加入 `/root/.bashrc`。添加前先检查，避免重复写入：

```bash
grep -q 'FINSCHOLAR_RUNTIME_ENV' /root/.bashrc || tee -a /root/.bashrc >/dev/null <<'EOF'

# FINSCHOLAR_RUNTIME_ENV
export HF_HOME=/root/autodl-tmp/FinScholar-Expert/models/modelscope
export modelscope_HUB_CACHE=/root/autodl-tmp/FinScholar-Expert/models/modelscope/hub
export TRANSFORMERS_CACHE=/root/autodl-tmp/FinScholar-Expert/models/modelscope/transformers
export TORCH_HOME=/root/autodl-tmp/FinScholar-Expert/cache/torch
export UV_CACHE_DIR=/root/autodl-tmp/FinScholar-Expert/cache/uv
export TOKENIZERS_PARALLELISM=false
EOF
```

使配置生效：

```bash
source /root/.bashrc
```

验证：

```bash
echo "$HF_HOME"
echo "$UV_CACHE_DIR"
```

### 5.5 安装 uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv --version
```

若服务器重新登录后找不到 `uv`，执行：

```bash
source "$HOME/.local/bin/env"
```

### 5.6 获取项目代码

项目统一存放在数据盘：

```bash
cd /root/autodl-tmp
test ! -e FinScholar-Expert || { echo 'ERROR: FinScholar-Expert 已存在，请先确认其内容'; exit 1; }
git clone <项目Git地址> FinScholar-Expert
cd /root/autodl-tmp/FinScholar-Expert
```

如果代码已通过 SCP、文件存储或其他方式上传，只需进入项目目录：

```bash
cd /root/autodl-tmp/FinScholar-Expert
```

获取代码后，在项目根目录内创建模型、缓存与运行目录：

```bash
cd /root/autodl-tmp/FinScholar-Expert
mkdir -p models/modelscope models/lora
mkdir -p cache/torch cache/uv
mkdir -p logs run data artifacts
```

### 5.7 创建主应用虚拟环境

主应用环境负责：

- LangGraph 和 FastAPI。
- 七个业务工具。
- Milvus 客户端。
- BGE-M3 与 Reranker。
- PDF 解析、数据处理、图表生成和测试。

执行：

```bash
cd /root/autodl-tmp/FinScholar-Expert
uv venv .venv --python 3.12 --seed
```

AutoDL 必须使用本地已经生成并提交的 `pyproject.toml` 和 `uv.lock`，严格按锁文件安装：

```bash
uv sync --frozen
```

禁止在 AutoDL 上首次解析或升级主应用依赖；依赖变更必须先在本地完成、测试并提交锁文件。

验证主环境：

```bash
.venv/bin/python --version
.venv/bin/python -c "import langgraph; print('langgraph: OK')"
.venv/bin/python -c "import pymilvus; print('pymilvus: OK')"
```

### 5.8 创建 vLLM 独立虚拟环境

执行：

```bash
cd /root/autodl-tmp/FinScholar-Expert
uv venv .venv-vllm --python 3.12 --seed
```

Qwen3.5 当前需要新版 vLLM。AutoDL 不重新解析版本，直接使用本地生成并提交的锁文件同步：

```bash
uv pip sync \
  --python .venv-vllm/bin/python \
  requirements-vllm.lock.txt \
  --torch-backend=auto \
  --extra-index-url https://wheels.vllm.ai/nightly
```

验证：

```bash
.venv-vllm/bin/python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
.venv-vllm/bin/vllm --version
```

`torch.cuda.is_available()` 必须输出 `True`。

#### 5.8.1 创建 LoRA 训练环境

训练环境与本地保持一致，在 AutoDL 初始化时一并创建，但没有训练任务时不启动任何训练进程：

```bash
cd /root/autodl-tmp/FinScholar-Expert
uv venv .venv-train --python 3.12 --seed
```

仓库存在经过验证的训练锁文件时执行：

```bash
test -f requirements-train.lock.txt || { echo 'ERROR: 训练依赖尚未锁定'; exit 1; }
uv pip sync \
  --python .venv-train/bin/python \
  requirements-train.lock.txt
```

验证训练环境：

```bash
.venv-train/bin/python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

训练脚本必须使用 `.venv-train/bin/python`；模型服务必须使用 `.venv-vllm/bin/vllm`，两者不得交叉调用。

### 5.9 下载并缓存模型

下载 Qwen3.5-4B：

```bash
.venv-vllm/bin/python - <<'PY'
from modelscope_hub import snapshot_download

snapshot_download(
    repo_id="Qwen/Qwen3.5-4B",
)
print("Qwen3.5-4B download: OK")
PY
```

BGE-M3 与 Reranker 在主应用环境中首次加载时会自动下载到 `HF_HOME`。也可以在部署阶段主动预下载：

```bash
.venv/bin/python - <<'PY'
from modelscope_hub import snapshot_download

for model_id in (
    "BAAI/bge-m3",
    "BAAI/bge-reranker-v2-m3",
):
    snapshot_download(repo_id=model_id)
    print(f"{model_id}: OK")
PY
```

下载完成后检查数据盘：

```bash
du -sh /root/autodl-tmp/FinScholar-Expert/models/modelscope
df -h /root/autodl-tmp
```

### 5.10 创建环境变量文件

从模板创建 `.env`：

```bash
cd /root/autodl-tmp/FinScholar-Expert
test -e .env || cp .env.example .env
chmod 600 .env
```

`.env` 至少应包含：

```dotenv
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8080
GPU_OPERATIONS_ENABLED=true

ROUTER_BACKEND=vllm
EMBEDDING_BACKEND=bge-m3
RERANKER_BACKEND=bge-reranker-v2-m3
VECTOR_STORE_BACKEND=milvus
SANDBOX_BACKEND=docker

QWEN_BASE_URL=http://127.0.0.1:8000/v1
QWEN_API_KEY=EMPTY
QWEN_MODEL=qwen-router
QWEN_ENABLE_THINKING=false

DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=
DEEPSEEK_MODEL=

DASHSCOPE_API_KEY=
QWEN_VL_MODEL=qwen-vl-max

MILVUS_URI=
MILVUS_TOKEN=
MILVUS_DATABASE=default

TAVILY_API_KEY=
WIKIPEDIA_USER_AGENT=FinScholar-Expert/1.0 contact@example.com

DATA_DIR=/root/autodl-tmp/FinScholar-Expert/data
ARTIFACT_DIR=/root/autodl-tmp/FinScholar-Expert/artifacts
LOG_DIR=/root/autodl-tmp/FinScholar-Expert/logs
LORA_ADAPTER_PATH=/root/autodl-tmp/FinScholar-Expert/models/lora/finscholar-router
```

规则：

- `.env.example` 只保留变量名和安全示例值。
- `.env` 必须列入 `.gitignore`。
- 禁止通过聊天、截图或日志传递真实密钥。
- `DEEPSEEK_MODEL` 使用控制台实际开通的模型 ID，不在代码中硬编码。

### 5.11 配置 Milvus、Attu 与 Sandbox

#### Docker 可用的裸金属环境

确认：

```bash
docker version
docker compose version
docker run --rm --gpus all nvidia/cuda:12.9.0-base-ubuntu24.04 nvidia-smi
```

通过项目维护的 Compose 文件启动基础设施：

```bash
docker compose -f deploy/compose.infra.yml up -d
```

禁止直接从网络下载未经版本锁定的 Compose 文件。Milvus、Attu、etcd 和 MinIO 镜像版本必须在仓库内固定。

#### AutoDL 普通容器实例

普通实例不得执行 Docker 安装或 Docker-in-Docker。必须在 `.env` 中配置外部 `MILVUS_URI`，并配置外部 Python Sandbox 服务地址。Attu 在外部 Docker 主机或本地电脑运行。

如果外部 Milvus 或 Sandbox 未准备好，只允许进行单元测试，不允许把环境标记为“完整集成可运行”。

## 6. AutoDL 每次启动 SOP

以下步骤在每次 AutoDL 实例开机后执行。

### 6.1 进入项目并加载基础环境

```bash
source /root/.bashrc
source "$HOME/.local/bin/env"
conda deactivate 2>/dev/null || true
cd /root/autodl-tmp/FinScholar-Expert
```

确认：

```bash
pwd
uv --version
nvidia-smi
df -h /root/autodl-tmp
```

### 6.2 同步代码与依赖

如果服务器工作区没有未提交修改：

```bash
git status --short
git pull --ff-only
uv sync --frozen
```

如果 `git status --short` 有输出，必须先确认修改归属，禁止直接覆盖、重置或删除。

只有 `requirements-vllm.lock.txt` 发生变更时才同步模型环境：

```bash
uv pip sync \
  --python .venv-vllm/bin/python \
  requirements-vllm.lock.txt \
  --torch-backend=auto \
  --extra-index-url https://wheels.vllm.ai/nightly
```

### 6.3 检查配置

```bash
test -f .env || { echo 'ERROR: .env 不存在'; exit 1; }
test -f pyproject.toml || { echo 'ERROR: pyproject.toml 不存在'; exit 1; }
test -f uv.lock || { echo 'ERROR: uv.lock 不存在'; exit 1; }
test -x .venv/bin/python || { echo 'ERROR: 主虚拟环境不存在'; exit 1; }
test -x .venv-vllm/bin/vllm || { echo 'ERROR: vLLM 虚拟环境不存在'; exit 1; }
```

### 6.4 启动基础设施

裸金属/Docker 环境：

```bash
docker compose -f deploy/compose.infra.yml up -d
docker compose -f deploy/compose.infra.yml ps
```

普通 AutoDL 实例：确认外部 Milvus 与 Sandbox 可访问，不执行 Docker 命令。

### 6.5 启动 Qwen3.5 路由模型

清理同名旧会话：

```bash
tmux has-session -t finscholar-qwen 2>/dev/null && tmux kill-session -t finscholar-qwen
```

启动模型服务：

```bash
tmux new-session -d -s finscholar-qwen "\
cd /root/autodl-tmp/FinScholar-Expert && \
exec .venv-vllm/bin/vllm serve Qwen/Qwen3.5-4B \
  --host 127.0.0.1 \
  --port 8000 \
  --served-model-name qwen-router \
  --tensor-parallel-size 1 \
  --max-model-len 16384 \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice \
  --tool-call-parser qwen3_coder \
  >> logs/qwen-router.log 2>&1"
```

说明：

- 路由场景在请求参数中设置 `enable_thinking=false`。
- 未训练或未准备 LoRA Adapter 前，不得添加 LoRA 启动参数。
- LoRA 就绪后，应由项目配置文件统一注入 Adapter 路径，不在 SOP 中临时拼接未知路径。

等待并检查模型服务：

```bash
for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8000/v1/models >/dev/null; then
    echo 'Qwen router: READY'
    break
  fi
  sleep 5
done

curl -fsS http://127.0.0.1:8000/v1/models
```

若 5 分钟内未就绪，停止后续启动，检查：

```bash
tail -n 200 logs/qwen-router.log
nvidia-smi
```

### 6.6 启动主应用

```bash
tmux has-session -t finscholar-api 2>/dev/null && tmux kill-session -t finscholar-api
```

启动：

```bash
tmux new-session -d -s finscholar-api "\
cd /root/autodl-tmp/FinScholar-Expert && \
exec .venv/bin/python -m uvicorn src.finscholar.api:app \
  --host 127.0.0.1 \
  --port 8080 \
  >> logs/api.log 2>&1"
```

如果后续项目入口模块发生变化，必须同步更新本 SOP，禁止个人长期使用未记录的启动命令。

### 6.7 应用健康检查

```bash
curl -fsS http://127.0.0.1:8080/health
```

健康检查至少应验证：

- 主应用进程正常。
- Qwen Router 可访问。
- Milvus 可连接。
- BGE-M3 与 Reranker 已加载或可以加载。
- DeepSeek、Qwen-VL-Max 和 Tavily 的密钥已经配置，但健康检查不得产生高成本调用。
- 数据目录和日志目录可写。
- Sandbox 服务可访问。

### 6.8 执行冒烟测试

```bash
.venv/bin/python -m pytest tests/smoke -q
```

冒烟测试必须至少包含：

1. 单工具路由与合法 JSON 参数。
2. Wikipedia、ArXiv 或 Tavily 的一个低成本测试请求。
3. Milvus 写入、召回和删除测试数据。
4. BGE-M3 输出维度为 1024。
5. Reranker 可处理候选片段。
6. Python Sandbox 拒绝网络访问和越权文件访问。
7. 报告引用中包含来源、页码或可定位元数据。

全部通过后，当前实例才可标记为“项目已启动”。

## 7. 本地访问服务器

Qwen Router 只监听 `127.0.0.1:8000`，不得直接暴露公网。

需要从本地访问主应用时，优先使用 SSH 隧道：

```bash
ssh -N \
  -L 8080:127.0.0.1:8080 \
  -p <SSH端口> \
  root@<AutoDL主机地址>
```

随后在本地访问：

```text
http://127.0.0.1:8080
```

如使用 AutoDL 的 6006/6008 自定义服务端口，应用必须启用身份认证，不允许把无认证的管理接口、Milvus 或 vLLM 端口暴露出去。

## 8. 查看运行状态与日志

查看会话：

```bash
tmux ls
```

进入 Qwen 会话：

```bash
tmux attach -t finscholar-qwen
```

进入 API 会话：

```bash
tmux attach -t finscholar-api
```

退出 tmux 但保持程序运行：按 `Ctrl+B`，再按 `D`。

查看日志：

```bash
tail -f logs/qwen-router.log
tail -f logs/api.log
```

查看 GPU：

```bash
watch -n 2 nvidia-smi
```

## 9. 停止项目 SOP

按照“主应用 → 模型服务 → 基础设施”的逆序停止。

### 9.1 停止主应用

```bash
tmux has-session -t finscholar-api 2>/dev/null && tmux kill-session -t finscholar-api
```

### 9.2 停止 Qwen 服务

```bash
tmux has-session -t finscholar-qwen 2>/dev/null && tmux kill-session -t finscholar-qwen
```

### 9.3 停止 Docker 基础设施

仅在 Docker 主机上执行：

```bash
docker compose -f deploy/compose.infra.yml stop
```

日常停止使用 `stop`，不要使用会删除数据卷的命令。任何涉及删除 Milvus、MinIO 或 etcd 数据卷的操作必须单独审批并提前备份。

### 9.4 关机前检查

```bash
git status --short
du -sh data artifacts logs models/lora 2>/dev/null
```

必须确认：

- 代码已提交或同步到远程仓库。
- LoRA Adapter、私有文档索引元数据和重要报告已经备份。
- 没有仍在写文件的训练、索引或报告生成任务。

## 10. 更新依赖 SOP

依赖更新只能在单独分支进行：

```bash
git switch -c codex/dependency-update-<日期>
```

主应用依赖更新：

```bash
uv lock --upgrade-package <包名>
uv sync
.venv/bin/python -m pytest -q
```

vLLM 更新：

1. 新建临时 vLLM 环境。
2. 安装目标 nightly 或指定 commit。
3. 验证 Qwen3.5 启动、Tool Calling、LoRA、显存和延迟。
4. 通过后重新生成 `requirements-vllm.lock.txt`。
5. 禁止在正在服务的 `.venv-vllm` 中直接升级。

## 11. 常见故障处理

### 11.1 `uv: command not found`

```bash
source "$HOME/.local/bin/env"
```

### 11.2 系统盘空间不足

检查：

```bash
df -h /
du -sh /root/.cache 2>/dev/null
```

确认 `HF_HOME` 和 `UV_CACHE_DIR` 是否指向 `/root/autodl-tmp/FinScholar-Expert` 下的标准子目录。禁止在不了解内容的情况下递归删除缓存目录。

### 11.3 CUDA 不可用

```bash
nvidia-smi
.venv-vllm/bin/python -c "import torch; print(torch.cuda.is_available()); print(torch.version.cuda)"
```

不要优先使用 Conda 重装 CUDA。先确认 AutoDL 镜像、驱动、PyTorch 和 vLLM wheel 是否匹配。

### 11.4 Qwen 启动时显存不足

处理顺序：

1. 使用 `nvidia-smi` 检查是否有残留进程。
2. 确认没有重复启动 Qwen 服务。
3. 降低 `--max-model-len`，但不得低于项目实际路由上下文需求。
4. 降低并发或 GPU 内存利用率配置。
5. 重新评估 BGE-M3、Reranker 与 vLLM 是否需要同时常驻显存。

禁止未经评估直接更换模型或量化方案。

### 11.5 AutoDL 中没有 Docker

这是普通容器实例的正常限制，不是安装错误。应切换到已规划的外部 Milvus/Sandbox，或使用 Docker 可用的裸金属服务器。禁止尝试在普通实例中强行部署 Docker-in-Docker。

### 11.6 API 启动失败

```bash
tail -n 200 logs/api.log
.venv/bin/python -m pytest tests/smoke -q
```

重点检查 `.env`、Milvus 地址、Qwen Router 健康状态和模块入口路径。

## 12. 启动验收清单

每次启动完成后逐项确认：

- [ ]  已退出 Conda 环境。
- [ ]  `uv` 可用。
- [ ]  当前目录为 `/root/autodl-tmp/FinScholar-Expert`。
- [ ]  GPU、显存和数据盘空间正常。
- [ ]  `.env` 存在且权限为 `600`。
- [ ]  主应用已通过 `uv sync --frozen` 同步。
- [ ]  Qwen Router `/v1/models` 正常。
- [ ]  Milvus 连接正常。
- [ ]  BGE-M3 输出 1024 维向量。
- [ ]  Reranker 正常。
- [ ]  Sandbox 正常且隔离策略生效。
- [ ]  主应用 `/health` 正常。
- [ ]  冒烟测试全部通过。
- [ ]  vLLM、Milvus 和管理端口未直接暴露公网。

## 13. 官方参考资料

- [AutoDL 实例环境与目录](https://www.autodl.com/docs/env/)
- [AutoDL SSH 使用说明](https://api.autodl.com/docs/ssh/)
- [AutoDL 实例数据保留规则](https://www.autodl.com/docs/instance_data/)
- [uv 官方文档](https://docs.astral.sh/uv/)
- [vLLM GPU 安装文档](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/)
- [Qwen3.5-4B 官方模型卡](https://modelscope.co/Qwen/Qwen3.5-4B)
- [Milvus Standalone 环境要求](https://milvus.io/docs/v2.6.x/prerequisite-docker.md)
- [Attu 官方仓库与版本兼容表](https://github.com/zilliztech/attu)

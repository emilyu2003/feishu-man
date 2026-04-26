# 虚拟招聘系统 (Virtual Recruitment System)

基于 LangGraph 和 飞书多维表格 (Bitable) 构建的多智能体协同招聘系统。

## 核心亮点
- **多智能体协作**：HR、面试官、候选人三大 Agent 通过 Bitable 共享状态进行异步协作。
- **CLI 驱动**：所有飞书操作均通过官方 `lark-cli` 工具执行，符合竞赛原生设计要求。
- **LangGraph 驱动**：使用有向有环图精准控制招聘流程（筛选 -> 安排 -> 面试 -> 报告）。
- **自动化面试**：实现基于 JD 的自动出题、候选人自动答题（MCQ 模拟）及自动评分。
- **数据驱动**：所有过程数据实时持久化至飞书表格，并自动生成招聘分析报告。

## 快速开始

### 1. 安装环境 (Conda)
推荐使用 Conda 管理 Python 环境：

```bash
# 创建环境
conda env create -f environment.yml

# 激活环境
conda activate feishu-man

# 安装 CLI 工具 (如果未安装)
npm install -g @larksuite/cli
```

### 2. 配置环境
复制 `.env.example` 为 `.env` 并填写相关信息：
- **必填项**：`OPENAI_API_KEY` (或兼容接口)，用于驱动 Agent 逻辑。
- **选填项**：`FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_BASE_ID`。如果不填写，系统将进入 **Mock 模拟模式**，在本地终端打印操作日志。

### 3. 运行系统
```bash
# Windows (PowerShell)
$env:PYTHONPATH="."; python src/main.py

# Linux / macOS
PYTHONPATH=. python src/main.py
```

## 飞书多维表格结构说明
若需连接真实飞书环境，请在 Base 中创建以下四张表：
1. **简历池**：包含姓名、学历、筛选状态、相似度评分等字段。
2. **面试官可用时间**：包含面试官ID、日期、时段、可用状态。
3. **面试安排**：包含面试ID、候选人ID、面试时间、面试状态、反馈、评分。
4. **招聘数据分析**：包含报告类型、报告内容、生成时间。

## 技术栈
- **框架**: [LangGraph](https://github.com/langchain-ai/langgraph)
- **SDK**: [lark-oapi](https://github.com/larksuite/oapi-sdk-python)
- **模型**: GPT-4o / Claude 3.5 (通过 LangChain 调用)
- **数据模型**: Pydantic

# 虚拟招聘系统技术实施文档

## 一、 项目架构
本项目基于 **LangGraph** 构建多智能体协同工作流，使用 **飞书多维表格 (Bitable)** 作为统一的状态存储和消息总线。

### 目录结构
```text
feishu-man/
├── src/
│   ├── agents/             # 各角色 Agent 实现
│   │   ├── hr_agent.py
│   │   ├── interviewer_agent.py
│   │   └── candidate_agent.py
│   ├── core/               # 核心引擎
│   │   ├── graph.py        # LangGraph 工作流定义
│   │   └── state.py        # 状态定义
│   ├── utils/              # 工具类
│   │   ├── feishu_client.py# 飞书 API 封装
│   │   └── llm.py          # LLM 调用封装
│   ├── schema/             # 数据模型 (Pydantic)
│   │   └── models.py
│   └── main.py             # 入口脚本
├── tests/                  # 测试用例
├── .env.example            # 环境变量模板
├── requirements.txt        # 依赖列表
└── technical_spec.md       # 技术文档 (本文件)
```

## 二、 核心组件设计

### 1. 飞书 Bitable 客户端 (`feishu_client.py`)
封装 `lark-cli` 调用，通过 Python 的 `subprocess` 模块执行命令行指令。这种方式符合竞赛对 CLI 使用的要求，并能利用官方 CLI 提供的重试、日志和身份管理能力。
- `list_records`: 调用 `lark-cli base +record-list`。
- `add_record`: 调用 `lark-cli base +record-upsert`。
- `update_record`: 调用 `lark-cli base +record-upsert` 并指定 `--record-id`。

### 2. 数据模型 (`models.py`)
使用 Pydantic 定义与飞书表格字段一一对应的模型：
- `Resume`: 候选人简历信息。
- `InterviewSlot`: 面试官可用时间。
- `InterviewRecord`: 面试安排与反馈。

### 3. Agent 逻辑实现

#### HR Agent
- **筛选逻辑**：调用 LLM 对比 JD 与简历，生成 0-100 分及简短评价。
- **调度逻辑**：匹配可用时间槽与高分候选人。

#### Interviewer Agent
- **出题逻辑**：基于 JD 生成 20-40 道选择题，包含正确答案。
- **评分逻辑**：比对候选人答案，计算正确率并判定通过。

#### Candidate Agent
- **生成逻辑**：基于 JD 随机生成个人背景。
- **答题逻辑**：对面试题进行随机 A/B/C/D 选择。

### 4. LangGraph 工作流
定义 `RecruitmentGraph`：
- **Nodes**: `node_hr_screening`, `node_schedule_interview`, `node_conduct_interview`, `node_final_decision`, `node_report_gen`。
- **Edges**: 根据飞书表格中的状态位触发流转。

## 三、 运行流程
1. **初始化**：检查/创建飞书多维表格结构。
2. **简历阶段**：候选人池生成简历 -> 写入 Bitable。
3. **筛选阶段**：HR Agent 扫描“待筛选”记录 -> 打分 -> 更新状态。
4. **安排阶段**：HR Agent 扫描可用时间 -> 匹配候选人 -> 创建面试记录。
5. **面试阶段**：Interviewer 出题 -> Candidate 答题 -> Interviewer 判分 -> 更新结果。
6. **归档阶段**：HR Agent 发放结果 -> 生成分析报告。

## 四、 环境变量
需配置以下变量以运行项目：
- `FEISHU_APP_ID`: 飞书应用 ID
- `FEISHU_APP_SECRET`: 飞书应用密钥
- `FEISHU_BASE_ID`: 多维表格 ID
- `OPENAI_API_KEY`: 大模型 API Key (或国内兼容模型)
- `OPENAI_API_BASE`: 大模型 API 接口地址

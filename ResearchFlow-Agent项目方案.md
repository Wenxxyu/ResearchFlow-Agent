# ResearchFlow-Agent 项目方案

## 1. 项目定位

**项目名称**：ResearchFlow-Agent：支持多层记忆与 Skill 自进化的科研任务智能体

**一句话描述**：面向研究生科研和代码实验场景，构建一个能读论文、理解代码仓库、检索项目知识、调用工具执行任务、沉淀长期记忆并自动生成 Skill 的 Agent 工作流系统。

这个项目适合作为人工智能方向实习简历项目，因为它覆盖了当前 Agent 应用中比较关键的能力：Agentic RAG、MCP 工具调用、多层记忆、Skill 系统、自反思、自进化闭环、工作流编排与可观测评估。

---

## 2. 推荐技术栈

### 后端

- Python
- FastAPI
- LangGraph
- LangChain 或 LlamaIndex，二选一即可
- MCP Python SDK 或自定义 Tool Adapter
- SQLAlchemy
- PostgreSQL，开发期可使用 SQLite
- FAISS / Milvus / Chroma，优先 FAISS
- Redis，可选，用于任务队列或缓存

推荐组合：

```text
FastAPI + LangGraph + PostgreSQL + FAISS + MCP
```

### 模型调用

支持多模型适配层：

- OpenAI / Claude / Qwen / DeepSeek / Ollama
- 国内环境可优先使用 Qwen 或 DeepSeek API
- 如果强调生态前沿，可支持 OpenAI Responses API 或 Claude + MCP

简历中不必堆模型名，重点写“多模型适配层”和“Agent workflow”。

### 前端

- Vue 3
- TypeScript
- Element Plus / Naive UI

建议页面：

- Agent Workspace：任务对话和执行状态
- Knowledge Base：文档、论文、代码仓库管理
- Memory Center：多层记忆查看与管理
- Skill Registry：Skill 注册、审核、触发记录
- Trace Viewer：Agent 执行轨迹与工具调用日志

### 文档和代码解析

- PyMuPDF：PDF 解析
- pdfplumber：表格抽取，可选
- BeautifulSoup：网页解析
- tree-sitter：代码结构解析，可选但加分
- ripgrep：代码仓库快速搜索

### 检索与重排

- Embedding：bge-m3 / Qwen embedding / text-embedding-3-small
- Vector DB：FAISS / Milvus / Chroma
- BM25：rank-bm25 / Elasticsearch，可选
- Reranker：bge-reranker / Jina reranker / Cohere rerank

建议实现 hybrid retrieval：

```text
BM25 关键词检索 + 向量检索 + rerank
```

---

## 3. 项目场景设计

不建议做通用聊天机器人，建议聚焦“科研实验与代码仓库助手”。

用户可以上传：

- 论文 PDF
- 项目 README
- 代码仓库
- 实验日志
- 训练配置
- 报错日志
- 数据集说明

Agent 可以完成：

1. 读论文并总结方法、创新点、实验设置
2. 对比多篇论文的方法差异
3. 理解代码仓库结构
4. 根据论文方法定位代码实现
5. 分析训练报错日志
6. 生成实验计划和 ablation 表格
7. 调用 Python 工具做数据统计
8. 把成功处理流程沉淀为 Skill
9. 在下次相似任务中自动调用 Skill

---

## 4. 核心系统架构

```text
Frontend: Vue 3
  ├─ Chat / Task Workspace
  ├─ Knowledge Base
  ├─ Memory Viewer
  ├─ Skill Registry
  └─ Trace Viewer

Backend: FastAPI
  ├─ Auth / Project API
  ├─ File Upload API
  ├─ Agent Task API
  ├─ Memory API
  ├─ Skill API
  └─ Trace API

Agent Runtime: LangGraph
  ├─ Router Node
  ├─ Planner Node
  ├─ Memory Recall Node
  ├─ Retriever Node
  ├─ Tool Executor Node
  ├─ Critic Node
  ├─ Reflection Node
  └─ Skill Miner Node

Knowledge Layer
  ├─ Document Parser
  ├─ Chunker
  ├─ Embedding
  ├─ Vector Index
  ├─ BM25 Index
  └─ Reranker

Tool Layer: MCP / Tool Adapter
  ├─ File Tool
  ├─ Code Search Tool
  ├─ Python Tool
  ├─ Database Tool
  └─ Paper Parser Tool

Storage
  ├─ PostgreSQL: users, tasks, memories, traces, skills
  ├─ FAISS: vector index
  ├─ File System / MinIO: uploaded files
  └─ Redis optional: task queue/cache
```

---

## 5. Agentic RAG 设计

不要做普通 RAG：

```text
用户问题 -> 检索 -> 拼上下文 -> 回答
```

建议做 Agentic RAG：

```text
用户问题
  -> Router 判断任务类型
  -> Query Rewriter 重写查询
  -> Retriever 多路检索
  -> Reranker 重排
  -> Evidence Selector 选择证据
  -> Answer Generator 生成答案
  -> Citation Verifier 校验引用
  -> Reflection Writer 写入记忆
```

任务类型可以包括：

- paper_qa：论文问答
- repo_qa：代码仓库问答
- log_debug：实验日志分析
- experiment_planning：实验计划生成
- skill_management：Skill 生成与管理
- general_chat：普通对话

核心亮点：

- query rewrite
- BM25 + vector hybrid retrieval
- rerank
- evidence selection
- citation verification
- answer self-check

---

## 6. 多层记忆模块

建议设计六层记忆：

```text
Working Memory
当前任务状态、计划、临时变量

Episodic Memory
历史任务记录、执行轨迹、用户反馈

Semantic Memory
稳定知识，比如项目背景、术语解释、论文结论

User Profile Memory
用户偏好，比如喜欢 PyTorch、中文回答、简历风格

Reflection Memory
失败原因、修正策略、下次注意事项

Skill Memory
可复用操作流程、工具调用 SOP、代码模板
```

存储方式：

```text
PostgreSQL 存结构化元数据
FAISS 存向量索引
文件系统存 Skill 文件和附件
```

记忆字段示例：

```json
{
  "id": "mem_xxx",
  "user_id": "u001",
  "project_id": "p001",
  "memory_type": "reflection",
  "content": "上次解析训练日志时，需要优先检查 CUDA_VISIBLE_DEVICES 和 checkpoint 路径。",
  "importance": 0.82,
  "confidence": 0.76,
  "created_at": "2026-05-05",
  "last_accessed_at": "2026-05-05",
  "source_task_id": "task_001",
  "tags": ["training", "debug", "pytorch"]
}
```

召回评分可以综合：

```text
score = 语义相似度 * 0.5 + 重要性 * 0.2 + 新近性 * 0.2 + 任务类型匹配 * 0.1
```

---

## 7. Skill 系统设计

Skill 不要只做成 prompt 文件，而要做成标准目录。

示例目录：

```text
skills/
  paper_review/
    SKILL.md
    scripts/
      extract_tables.py
      parse_references.py
    references/
      review_template.md

  pytorch_log_debug/
    SKILL.md
    scripts/
      parse_train_log.py
    references/
      common_errors.md

  repo_understanding/
    SKILL.md
    scripts/
      tree_summary.py
      symbol_search.py
```

`SKILL.md` 示例：

```markdown
---
name: pytorch_log_debug
description: 当用户上传 PyTorch 训练报错、CUDA OOM、checkpoint 加载失败或 loss 异常时使用
tools:
  - file_reader
  - python_executor
  - log_parser
---

# PyTorch 训练日志排查 Skill

## 触发条件
用户询问训练报错、显存不足、loss nan、模型无法加载等问题。

## 执行步骤
1. 读取日志最后 200 行
2. 检查 CUDA、路径、shape mismatch、dtype、device
3. 提取错误栈
4. 给出根因和修复建议
5. 如果修复成功，将经验写入 Reflection Memory
```

Skill 触发方式：

- 基于 description 的语义匹配
- 基于任务类型匹配
- 基于历史成功率排序
- 基于用户显式指定

---

## 8. Skill 自进化机制

自进化要做成受控闭环，不建议让 Agent 自动无限制改自己。

推荐流程：

```text
任务执行完成
  -> Evaluator 判断是否成功
  -> Reflection Generator 总结经验
  -> Skill Miner 判断是否值得沉淀
  -> 生成 candidate skill
  -> 自动跑测试样例
  -> 人工审核
  -> 注册到 Skill Registry
```

判断是否生成 Skill 的条件：

- 任务执行成功
- 同类任务出现频率高
- 执行步骤稳定
- 工具调用链可复用
- 用户给了正反馈

生成后不要直接启用，而是进入候选状态：

```text
candidate -> tested -> approved -> active -> deprecated
```

这样可以避免错误 Skill 污染系统行为。

---

## 9. MCP / 工具调用层

建议实现几个 MCP server 或 MCP 风格工具：

```text
filesystem-server
读取/写入用户工作区文件

code-search-server
基于 rg/tree-sitter 搜索代码符号和引用

python-executor-server
执行安全 Python 脚本，做数据分析

database-server
查询实验记录或结构化数据

paper-parser-server
解析 PDF、抽取标题、摘要、表格、参考文献
```

Agent 不直接操作所有资源，而是通过 Tool Router 调用工具：

```text
Agent 决策
  -> MCP Tool Router
  -> 调用具体工具
  -> 返回结构化结果
  -> 写入执行轨迹
```

---

## 10. MVP 开发计划

### 第一期：能用的 Agentic RAG

目标：先做出可运行系统。

功能：

- 上传 PDF / Markdown / TXT
- 文档切分
- 向量检索
- BM25 检索
- rerank
- 引用回答
- 任务路由
- 对话 UI

最小技术栈：

```text
FastAPI + Vue + FAISS + SQLite + LangGraph
```

### 第二期：工具调用和代码仓库理解

功能：

- 上传代码仓库
- 代码结构分析
- rg 搜索
- 读取文件片段
- 解释函数调用关系
- 分析报错日志
- 调用 Python 执行器

重点做一个实用功能：

```text
上传 train.log，Agent 自动定位错误原因，并给出修改建议。
```

### 第三期：多层记忆和 Skill 自进化

功能：

- 跨会话记忆
- 用户偏好记忆
- 任务历史记忆
- 失败反思
- Skill Registry
- 候选 Skill 生成
- Skill 触发和执行
- 执行轨迹可视化

---

## 11. 前端页面规划

### Agent Workspace

左侧是对话，右侧展示：

- 当前计划
- 检索到的证据
- 工具调用记录
- 引用来源
- 最终答案

### Knowledge Base

展示：

- 已上传论文
- 代码仓库
- 文档 chunk 数
- 索引状态
- 检索测试

### Memory Center

展示不同记忆：

- Working Memory
- Episodic Memory
- Semantic Memory
- User Profile Memory
- Reflection Memory
- Skill Memory

支持手动删除或禁用错误记忆，降低记忆污染。

### Skill Registry

展示：

- 已有 Skills
- 触发条件
- 使用次数
- 成功率
- 最近更新时间
- 候选 Skill
- 审核状态

### Trace Viewer

每次任务记录完整执行轨迹：

```text
Router: 判断为代码调试任务
Memory: 命中 3 条历史经验
Retriever: 检索 5 个文档片段
Tool: 调用 code_search
Tool: 调用 python_executor
Critic: 检查答案是否包含修复步骤
Reflection: 写入失败经验
```

---

## 12. 数据库表设计

最小表结构：

```text
users
projects
documents
chunks
tasks
task_steps
tool_calls
memories
skills
skill_versions
feedbacks
```

`tasks` 表：

```text
id
user_id
project_id
task_type
input
status
final_answer
created_at
updated_at
```

`task_steps` 表：

```text
id
task_id
node_name
input_json
output_json
latency_ms
created_at
```

`memories` 表：

```text
id
user_id
project_id
memory_type
content
summary
importance
confidence
embedding_id
source_task_id
created_at
last_accessed_at
```

`skills` 表：

```text
id
name
description
trigger
path
status
usage_count
success_count
created_from_task_id
created_at
updated_at
```

---

## 13. 项目亮点总结

### 亮点 1：任务路由

用户输入后先分类，不同任务走不同 graph：

- paper_qa
- repo_qa
- log_debug
- experiment_planning
- skill_management
- general_chat

### 亮点 2：多路检索

```text
向量检索找语义相关
BM25 找关键词匹配
代码搜索找精确符号
历史记忆找过往经验
Skill 检索找可复用流程
```

### 亮点 3：引用校验

生成答案后检查：

- 答案关键结论是否有来源 chunk 支撑
- 引用是否真实存在
- 是否出现无来源数字

校验失败则回到检索节点补证据。

### 亮点 4：执行前计划，执行后反思

每个任务包含：

```text
Plan
Action
Observation
Final Answer
Reflection
```

### 亮点 5：Skill 自动沉淀

将高频成功任务抽象成 Skill，并经过测试和人工审核后加入 Skill Registry。

---

## 14. 简历写法

**2026.03 - 2026.05　　　　　　　　　　　　　　　　ResearchFlow-Agent：支持多层记忆与 Skill 自进化的科研任务智能体**
**核心开发者**

- **技术栈**：Python｜FastAPI｜LangGraph｜MCP｜FAISS｜PostgreSQL｜Vue3｜PyMuPDF｜Tree-sitter｜Transformers
- **项目简介**：面向科研论文阅读、代码仓库理解和实验日志分析场景，构建具备 Agentic RAG、工具调用、多层记忆和 Skill 自进化能力的科研任务智能体，实现跨会话知识积累、任务执行追踪和可复用流程沉淀。
- **Agent 工作流编排**：基于 LangGraph 设计 Router、Planner、Memory Recall、Retriever、Tool Executor、Critic、Reflection Writer 等节点，实现可恢复、可追踪的多步骤 Agent 执行流程。
- **多层记忆模块**：设计 Working Memory、Episodic Memory、Semantic Memory、User Profile、Reflection Memory 和 Skill Memory 六层结构，结合语义相似度、重要性评分、时间衰减和任务类型进行记忆召回。
- **Agentic RAG 检索链路**：实现 query rewrite、BM25 + 向量混合检索、rerank、证据选择和引用校验机制，提升论文问答与代码问答的准确性和可溯源性。
- **MCP 工具调用**：封装文件读取、代码搜索、Python 执行、PDF 解析和数据库查询等工具接口，使 Agent 能够根据任务计划调用外部工具完成代码分析、日志排查和数据统计。
- **Skill 自进化机制**：设计“任务执行-结果评估-失败反思-经验抽取-Skill 生成-人工审核-Skill 注册”闭环，将高频成功任务沉淀为 `SKILL.md` 技能包，并在相似任务中自动触发复用。
- **可观测与评估**：实现任务执行轨迹、工具调用日志、检索证据、记忆命中和 Skill 触发记录可视化，构建任务成功率、引用准确率、记忆命中率和 Skill 复用率等评估指标。

---

## 15. 最终建议

如果时间有限，优先完成：

1. 论文 + 代码仓库问答
2. LangGraph 工作流
3. FAISS + BM25 + rerank
4. Memory Viewer
5. Skill Registry 雏形
6. Trace Viewer

后续再补 MCP 和 Skill 自进化闭环。

这个项目比普通“RAG 知识库问答系统”更强，因为它不只是回答问题，而是具备检索、决策、工具调用、记忆积累、经验沉淀和可观测评估能力。

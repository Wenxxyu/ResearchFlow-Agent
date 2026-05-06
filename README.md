# ResearchFlow-Agent

ResearchFlow-Agent 是一个面向研究生科研场景的全栈 Agent 系统，主要用于论文阅读、代码仓库理解、实验日志分析和科研任务管理。项目支持 Agentic RAG、多类型记忆、Skill Registry、受控 Skill 自进化、工具调用和执行轨迹可视化。

当前版本是可运行 MVP，默认使用 Mock LLM 和 Mock Embedding，因此没有 API Key 也可以启动并跑通基础流程。后续可以通过 `.env` 切换到 OpenAI、Qwen、DeepSeek 等兼容 OpenAI API 的模型服务。

## 核心能力

- 文档问答：支持 PDF、Markdown、TXT 上传、解析、切分、索引和带引用问答。
- 混合检索：支持 FAISS 向量检索、BM25 关键词检索、分数归一化、结果融合和去重。
- Agentic RAG：根据问题自动判断是否需要检索，不需要外部知识时直接回答，需要外部知识时进入检索增强流程。
- 多类型记忆：支持 working、episodic、semantic、user_profile、reflection、skill 等记忆类型。
- 会话级 Working Memory：前端生成 `conversation_id`，后端保存当前会话最近对话，用于多轮追问。
- Skill Registry：通过 `skills/*/SKILL.md` 管理可复用技能。
- Skill 自进化雏形：支持从任务中生成 candidate skill，人工审核后注册。
- 代码仓库理解：支持 zip 仓库上传、本地仓库导入、文件树扫描、Python class/function 解析和代码搜索。
- 实验日志分析：支持 Traceback、CUDA OOM、shape mismatch、NaN loss 等常见训练错误分析。
- Trace Viewer：记录并展示 Agent 每个节点的输入、输出和耗时。

## 技术栈

后端：

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- LangGraph
- FAISS
- rank-bm25
- PyMuPDF

前端：

- Vue 3
- TypeScript
- Vite
- Element Plus
- Axios

模型接口：

- MockLLMProvider
- OpenAI-compatible LLM Provider
- MockEmbeddingProvider
- OpenAI-compatible Embedding Provider
- NoopReranker

## 系统架构

```text
用户问题
  -> Router / Intent Classifier
  -> 判断任务类型和是否需要外部知识
     -> Direct Answer
     -> Paper QA / RAG
     -> Repo QA
     -> Log Debug
  -> Memory Recall
  -> Skill Recall
  -> Tool / Retrieval
  -> Answer Generation
  -> Citation Verify
  -> Working Memory Writer
  -> Reflection Writer
  -> Trace Writer
```

后端分层：

```text
backend/app/
  api/        API 路由层
  schemas/    Pydantic 请求和响应模型
  models/     SQLAlchemy ORM 模型
  services/   业务服务层
  agent/      LangGraph Agent 工作流
  rag/        文档解析、切分、检索和索引
  memory/     多类型记忆管理
  skills/     Skill 解析、注册、检索和候选生成
  repo/       代码仓库导入、扫描和搜索
  tools/      日志解析等工具
```

前端页面：

```text
frontend/src/pages/
  AgentWorkspace.vue    Agent 对话工作区
  KnowledgeBase.vue     文档和代码仓库管理
  MemoryCenter.vue      记忆管理
  SkillRegistry.vue     Skill 管理和审核
  TraceViewer.vue       执行轨迹查看
```

## 项目结构

```text
ResearchFlow-Agent/
  backend/
  frontend/
  docs/
  skills/
  data/
  tests/
  .env.example
  README.md
```


## 环境变量

复制示例配置：

```powershell
Copy-Item .env.example .env
```

默认 Mock 配置：

```env
RESEARCHFLOW_LLM_PROVIDER=mock
RESEARCHFLOW_EMBEDDING_PROVIDER=mock
RESEARCHFLOW_RERANKER_PROVIDER=noop
```

SQLite 和本地数据目录：

```env
RESEARCHFLOW_DATABASE_URL=sqlite:///./data/researchflow.sqlite3
RESEARCHFLOW_UPLOAD_DIR=data/uploads
RESEARCHFLOW_REPO_DIR=data/repos
RESEARCHFLOW_SKILL_DIR=skills
```

Qwen 示例：

```env
RESEARCHFLOW_LLM_PROVIDER=qwen
RESEARCHFLOW_LLM_API_KEY=your_api_key
RESEARCHFLOW_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
RESEARCHFLOW_LLM_MODEL=qwen-plus
```


## 后端启动

在项目根目录执行：

```powershell
cd D:\desktop\ResearchFlow-Agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
$env:PYTHONPATH="backend"
uvicorn app.main:app --reload --app-dir backend
```

后端地址：

```text
http://127.0.0.1:8000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

预期返回：

```json
{
  "status": "ok",
  "app_name": "ResearchFlow-Agent",
  "version": "0.1.0"
}
```

## 前端启动

打开新的 PowerShell：

```powershell
cd D:\desktop\ResearchFlow-Agent\frontend
npm install
npm run dev
```

前端地址：

```text
http://127.0.0.1:5173
```

## 端到端使用流程

1. 打开前端页面。
2. 在 Knowledge Base 创建项目。
3. 上传 PDF、Markdown 或 TXT 文档。
4. 点击 Build Index 构建 FAISS 和 BM25 索引。
5. 进入 Agent Workspace 选择项目并提问。
6. 查看回答中的引用，例如 `[doc:xxx.pdf chunk:3]`。
7. 在 Trace Viewer 查看完整执行步骤。
8. 在 Memory Center 查看 working、episodic、reflection、skill 等记忆。
9. 在 Skill Registry 查看和审核技能。


## 常用 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| POST | `/api/projects` | 创建项目 |
| GET | `/api/projects` | 项目列表 |
| POST | `/api/projects/{project_id}/documents/upload` | 上传文档 |
| GET | `/api/projects/{project_id}/documents` | 文档列表 |
| POST | `/api/projects/{project_id}/index/build` | 构建索引 |
| POST | `/api/projects/{project_id}/retrieve` | 混合检索 |
| POST | `/api/projects/{project_id}/agent/chat` | Agent 对话 |
| GET | `/api/projects/{project_id}/memories` | 记忆列表 |
| POST | `/api/projects/{project_id}/memories/search` | 搜索记忆 |
| GET | `/api/skills` | Skill 列表 |
| POST | `/api/skills/scan` | 扫描 Skill |
| GET | `/api/projects/{project_id}/tasks` | 任务列表 |
| GET | `/api/tasks/{task_id}/steps` | 执行轨迹 |

Agent 请求示例：

```json
{
  "message": "这篇论文的核心方法是什么？",
  "conversation_id": "conv-demo-001"
}
```

## 检查命令

后端测试：

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m pytest tests
```

前端构建：

```powershell
cd frontend
npm run build
```

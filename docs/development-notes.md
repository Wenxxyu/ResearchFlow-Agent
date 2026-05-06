# ResearchFlow-Agent 开发经验与项目理解

本文档记录当前阶段对 ResearchFlow-Agent 的架构理解、实现决策、踩坑经验和后续开发建议。后续继续扩展 Agentic RAG、多层记忆、Skill Registry 和执行轨迹时，优先参考这里的边界和约定。

## 1. 项目定位理解

ResearchFlow-Agent 不是一个普通聊天机器人，也不是只做“上传文档后问答”的简单 RAG 系统。它的核心价值应该落在科研工作流上：

- 论文阅读：解析 PDF、Markdown、TXT，切分、索引，并基于引用回答。
- 代码仓库理解：理解目录结构、搜索代码、解释函数和定位报错。
- 实验日志分析：读取训练日志、错误栈、配置文件和 checkpoint 信息，给出排查建议。
- Agent 工作流：根据任务自动路由到论文问答、代码问答、日志分析、实验计划、Skill 管理等流程。
- 多层记忆：把历史任务、稳定知识、用户偏好、反思经验和 Skill 经验持续沉淀下来。
- 可观测性：记录路由结果、检索证据、工具调用、模型输入输出、记忆命中和最终答案。

当前实现仍是 MVP 基础能力，重点是先建立稳定的工程分层、数据库模型和文档处理闭环。

## 2. 当前已实现能力

### 后端

技术栈：

- FastAPI
- SQLAlchemy ORM
- SQLite
- Pydantic
- PyMuPDF
- pytest

已实现模块：

- 健康检查：`GET /api/health`
- 项目管理：
  - `POST /api/projects`
  - `GET /api/projects`
  - `GET /api/projects/{project_id}`
  - `DELETE /api/projects/{project_id}`
- 文档管理：
  - `POST /api/projects/{project_id}/documents/upload`
  - `GET /api/projects/{project_id}/documents`
  - `GET /api/documents/{document_id}`
  - `DELETE /api/documents/{document_id}`
  - `GET /api/documents/{document_id}/chunks`
- 文档解析：
  - PDF 使用 PyMuPDF
  - Markdown/TXT 直接读取文本
- 文档切分：
  - 自研 `RecursiveTextSplitter`
  - 不依赖 LangChain
  - 支持 `chunk_size` 和 `chunk_overlap`
  - 默认 `chunk_size=800`，`chunk_overlap=120`
- RAG 检索：
  - `MockEmbeddingProvider` 使用 deterministic hashing，便于无 API Key 跑通。
  - FAISS 索引按 project 保存到 `data/indexes/{project_id}/faiss.index`。
  - chunk id 映射保存到 `chunk_mapping.json`。
  - BM25 索引按 project 保存到 `data/indexes/{project_id}/bm25.pkl`。
  - Hybrid retriever 同时查询向量索引和 BM25，去重后做简单 score fusion。
- Agentic RAG：
  - `BaseLLMProvider` 定义统一 `generate(messages, temperature, max_tokens)` 接口。
  - 默认 `MockLLMProvider`，无 API Key 也能跑通。
  - LangGraph 节点保持线性 MVP：router、query rewrite、retrieval、answer、citation verify、trace writer。
  - AgentState 保持可序列化，便于写 trace 和前端展示。
  - `tasks` 存任务级状态，`task_steps` 存节点级输入输出和耗时。
- 多层记忆：
  - `MemoryManager` 统一处理写入、搜索、访问时间更新和任务摘要沉淀。
  - 当前支持 `working`、`episodic`、`semantic`、`user_profile`、`reflection`、`skill`。
  - 召回公式为 `similarity * 0.5 + importance * 0.2 + recency * 0.2 + type_match * 0.1`。
  - `confidence` 是防止错误记忆污染的核心字段，低于阈值的记忆不会进入召回。
  - 当前删除策略是硬删除，原因是 MVP 阶段更看重防止错误记忆继续污染上下文。
  - Agent 在文档检索前执行 `memory_recall_node`，在 trace 写入前执行 `reflection_writer_node`。
- Skill Registry：
  - `app/skills/parser.py` 只解析 `SKILL.md` 和 YAML frontmatter。
  - `app/skills/registry.py` 负责扫描、注册、搜索和加载内容。
  - 启动时会扫描根目录 `skills/` 并同步到数据库。
  - Agent 执行时通过 `skill_recall_node` 检索相关 Skill，把摘要注入上下文。
  - 当前不会自动执行 `scripts/`，这是刻意的安全边界。
  - 后续受控执行脚本时，应增加审批、沙箱、输入输出 schema 和执行审计。
- Skill 自进化雏形：
  - 自进化只生成 candidate，不会自动修改启用中的 Skill。
  - `SkillMiner.should_create_skill` 要求任务成功、步骤数足够、有可复用节点，并且反馈 positive 或任务类型属于 `log_debug/repo_qa/paper_qa`。
  - candidate 内容先存入 `skill_candidates` 表。
  - approve 后才写入 `skills/{skill_name}/SKILL.md` 并触发 scan。
  - reject 只更新状态，不写文件。
  - skill name 做 slug 化和路径校验，防止路径穿越。
  - 当前只生成 `SKILL.md`，不生成 scripts。
- 文件保存：
  - `data/uploads/{project_id}/`
- chunks 入库：
  - 每个 chunk 写入 `chunks`
  - `metadata_json` 保存 `document_id`、`project_id`、`filename`、`page_number`、`chunk_index`、`start_index`、`end_index`

### 前端

技术栈：

- Vue 3
- TypeScript
- Vite
- Element Plus
- Axios

已实现页面：

- Agent Workspace
- Knowledge Base
- Memory Center
- Skill Registry
- Trace Viewer

Knowledge Base 已接入真实后端：

- 自动创建或复用默认项目
- 上传 PDF/Markdown/TXT
- 显示文档状态和 chunk 数
- 查看 chunks
- 删除文档

## 3. 工程分层约定

后端采用以下分层：

```text
API Route -> Pydantic Schema -> Service Layer -> Model / Parser / Splitter / DB
```

各层职责：

- `app/api/routes/`：HTTP 边界，只处理请求参数、依赖注入、状态码和错误映射。
- `app/schemas/`：Pydantic request/response schema。
- `app/services/`：业务逻辑层。文件保存、数据库写入、状态更新、事务控制都放这里。
- `app/models/`：SQLAlchemy ORM 模型。
- `app/rag/parser.py`：文档解析，不写数据库。
- `app/rag/splitter.py`：文本切分，不依赖数据库和 Web 框架。
- `app/db/session.py`：数据库 engine、session、`create_all` 初始化。
- `app/agent/`：后续放 LangGraph 工作流。
- `app/memory/`：后续放记忆召回和写入逻辑。
- `app/skills/`：后续放 Skill Registry 后端逻辑。
- `app/tools/`：后续放文件、代码搜索、Python 执行器等工具适配层。

这个分层要继续保持。API 层不要堆业务逻辑，尤其不要在 route 里直接解析 PDF、切分文本或批量写 chunks。

## 4. 数据库模型理解

当前核心表：

```text
projects
documents
chunks
tasks
task_steps
memories
skills
```

关系理解：

- `projects` 是所有资源的上层容器。
- `documents` 属于 project，记录上传文件元数据和索引状态。
- `chunks` 属于 document，也冗余保存 `project_id`，方便按项目检索。
- `tasks` 属于 project，后续每次 Agent 执行都应该产生一条 task。
- `task_steps` 属于 task，用于记录 LangGraph 节点、工具调用、输入输出和耗时。
- `memories` 属于 project，可选关联 `source_task_id`。
- `skills` 可选关联 `created_from_task_id`，表示这个 Skill 从哪个任务沉淀出来。

后续做检索时，`chunks.project_id` 很重要。它避免每次检索都 join documents 才能限制项目范围。

## 5. 文档处理链路

上传文档的当前链路：

```text
POST upload
  -> 校验 project 是否存在
  -> 校验文件类型
  -> 保存到 data/uploads/{project_id}/
  -> 创建 documents 记录，status=processing
  -> parser 解析文本
  -> RecursiveTextSplitter 切分
  -> 批量写 chunks
  -> documents.status=indexed
  -> documents.chunk_count=实际 chunk 数
```

失败时：

```text
documents.status=failed
documents.chunk_count=0
```

注意：当前失败后不会删除已保存的原始文件，也不会删除 document 记录。这对调试有价值。后续如果需要更干净的行为，可以在 service 层提供配置项。

## 6. RecursiveTextSplitter 设计理解

当前 splitter 的目标不是做到最完美，而是做到：

- 无 LangChain 依赖。
- 对中文友好。
- 保留 chunk overlap。
- 逻辑足够透明，便于后续改成 token-based splitter。

默认分隔符：

```python
["\n\n", "\n", "。", "；", "，", " ", ""]
```

含义：

- 优先按段落切。
- 其次按行切。
- 中文句号、分号、逗号作为中粒度切分点。
- 空格适配英文文本。
- 最后按字符硬切兜底。

后续如果引入 embedding model，建议把字符长度切分升级为 token-aware 切分，但仍保留当前实现作为无依赖 fallback。

## 7. 前端实现理解

当前前端没有引入 Vue Router，而是使用 `activePage` 做简单页面切换。这是 MVP 阶段的合理选择：

- 少依赖。
- 页面数量少。
- 便于快速验证后端 API。

Knowledge Base 的当前策略：

- 页面加载时先请求 `/api/projects`。
- 如果没有项目，创建 `default-project`。
- 上传文档默认使用第一个项目。

这是为了 MVP 先跑通上传链路。后续应增加 Project Selector，让用户明确选择当前 project。

## 8. 已验证命令

后端启动：

```powershell
cd D:\desktop\ResearchFlow-Agent
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="backend"
uvicorn app.main:app --reload --app-dir backend
```

前端启动：

```powershell
cd D:\desktop\ResearchFlow-Agent\frontend
npm run dev
```

后端编译检查：

```powershell
.\.venv\Scripts\python.exe -m compileall backend\app tests
```

后端测试：

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m pytest tests
```

前端构建：

```powershell
cd D:\desktop\ResearchFlow-Agent\frontend
npm run build
```

实际验证过的结果：

```text
pytest: 20 passed
frontend build: success
document upload runtime check: indexed, chunks written and readable
```

## 9. 开发环境经验和坑

### 9.1 PowerShell 中文显示乱码

PowerShell 输出里曾出现中文乱码，但这主要是终端编码显示问题，不一定代表文件内容损坏。

建议：

- 文档文件统一用 UTF-8。
- 代码里尽量避免不必要的中文字符串。
- 前端页面如果出现乱码，再检查源文件编码和浏览器渲染，而不是只看 PowerShell 输出。

### 9.2 npm 启动问题

在 Windows 上，后台启动 `npm` 时可能需要显式使用：

```powershell
npm.cmd run dev
```

浏览器 `ERR_CONNECTION_REFUSED` 的含义：

- 访问 `127.0.0.1:5173` 失败：前端 dev server 没启动。
- 页面能打开但显示后端未连接：后端 `8000` 没启动或代理失败。

### 9.3 pytest cache warning

测试时可能出现：

```text
PytestCacheWarning: could not create cache path ...
```

这是 `.pytest_cache` 写入权限问题，不影响测试结果。

### 9.4 SQLite in-memory 测试

测试里使用 SQLite 内存库时必须使用 `StaticPool`，否则建表和请求可能落在不同连接，导致：

```text
sqlite3.OperationalError: no such table: projects
```

当前 `tests/conftest.py` 已处理：

```python
poolclass=StaticPool
```

### 9.5 create_all 与开发库 schema 演进

`Base.metadata.create_all()` 不会自动修改已存在表的结构。之前 `projects` 表新增 `updated_at` 后，需要兼容旧 SQLite 文件。

当前 `app/db/session.py` 加了轻量兼容：

- 如果 SQLite 中 `projects` 已存在但缺少 `updated_at`，启动时自动 `ALTER TABLE`。

后续表结构频繁变化时，建议引入 Alembic，而不是继续手写兼容逻辑。

## 10. 代码风格和工程约定

建议继续遵守：

- API 层不写业务流程。
- Service 层处理事务和状态流转。
- Parser/Splitter 保持纯逻辑，方便单测。
- Pydantic schema 不直接混进 ORM 模型。
- 文件路径统一从 `Settings` 读取。
- 所有新增 API 都补 pytest。
- 前端 API 调用统一放在 `frontend/src/api/`。
- 前端页面只组合状态和交互，不直接拼后端 URL 逻辑。

## 11. 下一阶段建议

推荐下一阶段实现“最小混合检索”：

1. 为 chunks 构建 BM25 索引。
2. 用简单 embedding fallback 或 Mock embedding 先设计接口。
3. 实现：

```text
GET /api/projects/{project_id}/search?q=...
```

4. 返回命中的 chunks、score 和 metadata。
5. 前端 Knowledge Base 增加检索测试框。

再下一步实现 Agent Router：

```text
POST /api/agent/tasks
```

MVP 流程：

```text
user_input
  -> router 判断 task_type
  -> retrieval 检索 chunks
  -> MockLLMProvider 生成回答
  -> 写 tasks 和 task_steps
  -> 返回 answer + evidence
```

这样就能自然接上：

- Agentic RAG
- Trace Viewer
- Memory Center
- Skill Registry

## 12. 当前优先级判断

短期不要急着引入复杂模型和多个 LLM Provider。更重要的是先把数据闭环打稳：

```text
上传 -> 解析 -> 切分 -> 检索 -> 生成任务 -> 记录轨迹 -> 写入记忆
```

只有这个闭环稳定后，OpenAI、Qwen、DeepSeek、Claude 等 Provider 才有明确接入点。

当前代码已经为这个方向留出了位置：

- `app/llm/provider.py`
- `app/rag/`
- `app/agent/`
- `app/memory/`
- `app/skills/`
- `app/tools/`

后续每次扩展都应该落在对应目录里，避免把项目退化成一个大而乱的 FastAPI demo。
## 2026-05-06 Code Repository Module Notes

The repository understanding module is intentionally filesystem-index based for the MVP. It does not add a database table yet; imported repositories are stored under `data/repos/{project_id}/current/`, and the derived metadata is stored in `data/repos/{project_id}/repo_index.json`. This keeps the first version simple while still leaving a clear future path for a `repositories` table if multiple repositories per project become necessary.

Backend ownership:

- `app/repo/manager.py`: import, path safety, ZIP extraction, scanning, AST symbol extraction, search, and bounded file reads.
- `app/api/routes/repos.py`: HTTP boundary and error mapping.
- `app/schemas/repo.py`: request/response schemas.
- `app/agent/workflow.py`: `repo_qa` routing, `code_search_node`, and code citations.

Important decisions:

- ZIP extraction validates every member path before extraction to prevent path traversal.
- Local repository import is restricted to paths inside the current workspace.
- File reads go through `safe_repo_path()` and are limited to the imported project repository root.
- Large file reads are truncated to keep API responses and Agent context bounded.
- `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `dist`, `build`, `.idea`, and `.pytest_cache` are ignored.
- Python symbols are extracted with `ast`, including classes, functions, async functions, and methods. Tree-sitter can be added later when multi-language symbol extraction becomes necessary.
- Search tokenizes the query and filters simple stopwords, then matches any meaningful term against filename, symbol name, and content. This is important because Agent query rewriting may add generic words like `implementation function code`.

Agent behavior:

```text
router_node
  -> query_rewrite_node
  -> skill_recall_node
  -> memory_recall_node
  -> code_search_node
  -> retrieval_node
  -> answer_node
  -> citation_verify_node
  -> reflection_writer_node
  -> trace_writer_node
```

For `repo_qa`, if code search finds results, document retrieval is skipped and the answer is generated from code snippets. Code references use:

```text
[code:relative/path.py:line]
```

Frontend:

- `frontend/src/api/repos.ts` contains the repo API client.
- `KnowledgeBase.vue` includes ZIP upload, local path import, tree refresh, README/file/symbol summary, and code search.
- `AgentWorkspace.vue` already renders citations generically, so code citations display alongside document citations.

## 2026-05-06 Experiment Log Debugging Notes

The experiment log debugging feature adds a rule-based `log_debug` path to the existing Agent workflow. It is meant for triage of pasted training logs and tracebacks, especially PyTorch-style failures, without executing user code.

Backend ownership:

- `app/tools/log_parser.py`: static log parsing and rule-based diagnosis.
- `app/agent/workflow.py`: routing, parse/diagnosis/fix nodes, reflection memory write.
- `app/schemas/agent.py`: exposes structured `log_analysis` in chat responses.
- `frontend/src/pages/AgentWorkspace.vue`: renders structured log sections.

Router signals:

- `Traceback`
- `CUDA out of memory`
- `RuntimeError`
- `shape mismatch` or `size mismatch`
- `nan loss`
- `checkpoint loading failed`
- `module not found`
- permission errors

Parser output:

```text
tail_lines
tail_text
error_type
file_references
keywords
line_count
```

Diagnosis output:

```text
summary
possible_causes
troubleshooting_steps
fix_suggestions
need_more_info
```

Workflow shape:

```text
router_node
  -> query_rewrite_node
  -> parse_log_node
  -> memory_recall_node
  -> skill_recall_node
  -> code_search_node
  -> retrieval_node
  -> diagnosis_node
  -> fix_suggestion_node
  -> answer_node
  -> citation_verify_node
  -> reflection_writer_node
  -> trace_writer_node
```

For non-log tasks, `parse_log_node`, `diagnosis_node`, and `fix_suggestion_node` are no-ops. For `log_debug`, document retrieval is skipped because the primary evidence is the pasted log. Future versions can optionally retrieve project docs, code snippets, or experiment notes as secondary evidence.

The feature intentionally does not claim certainty. If the parser cannot find a known pattern, it returns a low-specificity diagnosis and asks for full traceback, command/config, environment, and relevant shapes. Successful log debug tasks write a `reflection` memory with the summary, likely causes, and fix suggestions so future similar failures can be recalled.

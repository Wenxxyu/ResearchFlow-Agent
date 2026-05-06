# ResearchFlow-Agent 当前状态

最后更新：2026-05-05

## 已完成

- FastAPI 后端骨架。
- Vue 3 + TypeScript + Vite + Element Plus 前端骨架。
- SQLite + SQLAlchemy ORM。
- 7 张核心表：
  - projects
  - documents
  - chunks
  - tasks
  - task_steps
  - memories
  - skills
- Projects API。
- Documents upload API。
- PDF/Markdown/TXT 解析。
- 自研 RecursiveTextSplitter。
- chunks 入库和查看接口。
- MockEmbeddingProvider。
- 每项目独立 FAISS 向量索引。
- 每项目独立 BM25 索引。
- Hybrid retrieval API。
- LLM Provider 抽象和 MockLLMProvider。
- LangGraph Agentic RAG MVP。
- Agent chat API。
- tasks/task_steps 写入。
- 多层记忆管理器。
- Memory API。
- Agent workflow memory_recall_node。
- Agent workflow reflection_writer_node。
- Skill Registry parser and scanner.
- Skill API.
- Agent workflow skill_recall_node.
- Skill candidate table and API.
- Controlled candidate approve/reject workflow.
- Knowledge Base 前端上传、列表、查看 chunks、删除。
- Knowledge Base 前端构建索引和检索测试。
- Agent Workspace 前端问答、引用和执行步骤展示。
- Memory Center 前端记忆列表、搜索、写入和删除。
- Skill Registry 前端扫描、列表、详情展示。
- Agent Workspace candidate skill generation button.
- Skill Registry candidate review queue.
- pytest 基础测试。

## 最近一次验证

```text
backend compile: passed
pytest: 20 passed
frontend build: passed
runtime document upload: passed
```

## 重要入口

- 项目理解和开发经验：`docs/development-notes.md`
- 架构说明：`docs/architecture.md`
- 原始项目方案：`ResearchFlow-Agent项目方案.md`

## 下一步推荐

优先实现检索层：

- BM25 检索。
- FAISS/embedding 接口。
- Hybrid retrieval service。
- Search API。
- 前端检索测试入口。

随后实现最小 Agent Task：

- 任务创建。
- Router。
- MockLLM 回答。
- Evidence 返回。
- task_steps 轨迹记录。
## 2026-05-06 Update: Code Repository Understanding

Implemented the repository understanding MVP:

- ZIP repository upload and local workspace path import.
- Imported repos are stored in `data/repos/{project_id}/current/`.
- Repository index is stored as `data/repos/{project_id}/repo_index.json`.
- Scanner produces file tree, language metadata, README summary, and Python class/function/method symbols through `ast`.
- Code search supports filename search, content keyword search, and Python symbol search.
- APIs:
  - `POST /api/projects/{project_id}/repos/upload`
  - `GET /api/projects/{project_id}/repos/tree`
  - `POST /api/projects/{project_id}/repos/search`
  - `GET /api/projects/{project_id}/repos/files?path=...`
- Agent workflow now includes `code_search_node`.
- Router can classify code questions as `repo_qa`.
- `repo_qa` answers can cite code evidence with `[code:path:line]`.
- Knowledge Base page includes repository import and code search controls.

Safety constraints:

- ZIP extraction validates target paths before extraction.
- Local path import is restricted to the current workspace.
- File reads are restricted to the imported repository root.
- Large file reads are truncated.
- Ignored directories include `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `dist`, `build`, `.idea`, and `.pytest_cache`.

## 2026-05-06 Update: Experiment Log Debugging

Implemented the `log_debug` MVP:

- Router recognizes traceback, CUDA OOM, RuntimeError, shape/size mismatch, NaN loss, checkpoint loading failures, module import failures, and permission errors.
- Added `app/tools/log_parser.py`.
- Log parser extracts tail lines, error type, traceback file/line references, and common keywords.
- Agent workflow now includes `parse_log_node`, `diagnosis_node`, and `fix_suggestion_node`.
- `skill_recall_node` biases log tasks toward `pytorch_log_debug`.
- `memory_recall_node` recalls reflection memories for similar past failures.
- The chat response includes structured `log_analysis` with summary, possible causes, troubleshooting steps, fix suggestions, and missing information.
- Agent Workspace renders `log_debug` answers as structured sections.
- Completed log debug tasks write an additional `reflection` memory.

Current limitation: diagnosis is rule-based and uses MockLLM-compatible context only. It should be treated as a triage assistant, not as a guaranteed fix.

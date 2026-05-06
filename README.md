# ResearchFlow-Agent

ResearchFlow-Agent is an MVP full-stack Agent system for graduate research workflows. It helps users read papers, inspect code repositories, analyze experiment logs, manage reusable skills, and review the full execution trace of Agent runs.

The current implementation is designed to run without external model API keys. It provides mock LLM and embedding providers so the complete flow can be started locally, tested end to end, and later extended to real model providers such as OpenAI, Qwen, DeepSeek, Claude, or local embedding models.

## Core Capabilities

### Agentic RAG

ResearchFlow-Agent supports document ingestion and citation-grounded question answering:

- Upload PDF, Markdown, and TXT documents.
- Parse documents with PyMuPDF for PDF and direct text reading for Markdown/TXT.
- Split text with a local `RecursiveTextSplitter`.
- Store document chunks in SQLite.
- Build hybrid retrieval indexes:
  - FAISS vector index
  - rank-bm25 keyword index
  - simple score fusion reranking
- Run Agentic RAG through LangGraph.
- Return answers with document citations such as:

```text
[doc:paper.txt chunk:3]
```

### Multi-Layer Memory

The memory module supports project-scoped memory records:

- `working`: short-term task state, not necessarily long lived.
- `episodic`: historical tasks and execution summaries.
- `semantic`: stable project knowledge.
- `user_profile`: user preferences.
- `reflection`: failure causes, improvements, and debugging lessons.
- `skill`: reusable workflow and Skill-related memories.

Session-level working memory is enabled for Agent chat. The frontend creates a per-project
`conversation_id`, sends it to `/api/projects/{project_id}/agent/chat`, and stores it in
`localStorage`. The backend reuses the `memories` table with `memory_type="working"` and tags
such as `conversation:conv-...`; each turn is written after the answer and the latest 12 turns
are retained for that conversation. This is session continuity, not checkpoint recovery.

Memory search combines semantic similarity, importance, recency, and memory type match:

```text
score = similarity * 0.5 + importance * 0.2 + recency * 0.2 + type_match * 0.1
```

The MVP uses hard delete for memories. This keeps wrong or low-quality memories from continuing to pollute future recall. A later version can add soft delete and audit history.

Skill memory is project-scoped usage experience for registered skills. It is different from
`skills/*/SKILL.md`: the Skill Registry stores the reusable skill definition, while skill memory
stores when a skill was recalled for a task, whether it succeeded, and what trigger pattern should
help future tasks. Agent runs recall skill memories during `skill_recall_node`, inject them into
answer context, and write new `memory_type="skill"` records after tasks that used recalled skills.

### Skill Registry

Reusable skills live under the root `skills/` directory:

```text
skills/
  skill_name/
    SKILL.md
    scripts/
    references/
    assets/
```

`SKILL.md` supports YAML frontmatter:

```yaml
---
name: pytorch_log_debug
description: Diagnose PyTorch training logs and common runtime errors.
tools:
  - log_parser
status: active
trigger: CUDA OOM, checkpoint error, shape mismatch, NaN loss
---
```

The registry can:

- Scan `skills/`.
- Parse YAML frontmatter.
- Sync skills into the database.
- Search relevant skills with the mock embedding provider.
- Inject skill summaries into Agent context.

For safety, the current system only parses and displays skill content. It does not automatically execute arbitrary scripts from `skills/*/scripts/`.

### Skill Self-Evolution

ResearchFlow-Agent includes a controlled candidate skill workflow:

```text
task completed
  -> evaluator checks whether the task is eligible
  -> reflection generator summarizes reusable experience
  -> skill miner generates candidate SKILL.md
  -> user reviews candidate
  -> approve writes skills/{skill_name}/SKILL.md
  -> scan skills syncs it into the database
```

Safety constraints:

- Candidate skills are inactive by default.
- A user must approve a candidate before it is written into `skills/`.
- Only `SKILL.md` is generated.
- No executable scripts are generated or executed.
- Skill names and output paths are validated to prevent path traversal.

### MCP / Tool Calling Foundation

The current project does not yet implement a full MCP server/client integration, but it has the foundations needed for MCP-style tool calling:

- `app/tools/` contains tool-style modules such as `log_parser`.
- `app/repo/manager.py` provides repository import, scan, search, and safe file read functions.
- `app/rag/` provides retrieval tools.
- `app/skills/` provides skill parsing, registry, search, and mining.
- Agent workflow nodes call these tools explicitly and record outputs in `task_steps`.

Future MCP integration can wrap these modules as formal MCP tools while keeping the existing Agent workflow and trace model.

### Execution Trace Visualization

Every Agent run creates:

- a row in `tasks`
- multiple rows in `task_steps`

Each `task_step` records:

- `node_name`
- `input_json`
- `output_json`
- `latency_ms`
- `created_at`

The frontend Trace Viewer can load a task and inspect every step of the execution path.

## Technology Stack

Backend:

- Python
- FastAPI
- SQLAlchemy ORM
- SQLite by default, with PostgreSQL migration path
- Pydantic
- LangGraph
- FAISS
- rank-bm25
- PyMuPDF
- pytest

Frontend:

- Vue 3
- TypeScript
- Vite
- Element Plus
- Axios

Model abstraction:

- `BaseLLMProvider`
- `MockLLMProvider`
- `BaseEmbeddingProvider`
- `MockEmbeddingProvider`
- placeholders for OpenAI, Qwen, DeepSeek, Claude, and real embedding providers

## Project Structure

```text
ResearchFlow-Agent/
  backend/
    app/
      api/
        routes/
          agent.py
          documents.py
          health.py
          memories.py
          projects.py
          repos.py
          retrieval.py
          skill_candidates.py
          skills.py
          tasks.py
        router.py
      agent/
        state.py
        workflow.py
      core/
        config.py
      db/
        base.py
        session.py
      llm/
        provider.py
      memory/
        manager.py
      models/
        chunk.py
        document.py
        memory.py
        project.py
        skill.py
        skill_candidate.py
        task.py
        task_step.py
      rag/
        bm25_store.py
        embeddings.py
        parser.py
        retriever.py
        splitter.py
        vector_store.py
      repo/
        manager.py
      schemas/
      services/
      skills/
        miner.py
        parser.py
        registry.py
      tools/
        log_parser.py
      main.py
    requirements.txt
  frontend/
    src/
      api/
        agent.ts
        documents.ts
        health.ts
        memories.ts
        projects.ts
        repos.ts
        retrieval.ts
        skillCandidates.ts
        skills.ts
        tasks.ts
      pages/
        AgentWorkspace.vue
        KnowledgeBase.vue
        MemoryCenter.vue
        SkillRegistry.vue
        TraceViewer.vue
      styles/
        main.css
      types/
        api.ts
      App.vue
      main.ts
    package.json
    vite.config.ts
  docs/
    architecture.md
    current-status.md
    development-notes.md
  skills/
    paper_review/
      SKILL.md
    pytorch_log_debug/
      SKILL.md
    repo_understanding/
      SKILL.md
  data/
    indexes/
    repos/
    uploads/
  tests/
```

## Backend Startup

From PowerShell:

```powershell
cd D:\desktop\ResearchFlow-Agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
$env:PYTHONPATH="backend"
uvicorn app.main:app --reload --app-dir backend
```

Health check:

```powershell
curl http://127.0.0.1:8000/api/health
```

Expected response:

```json
{
  "status": "ok",
  "app_name": "ResearchFlow-Agent",
  "version": "0.1.0"
}
```

If you prefer installing dependencies into a local target directory:

```powershell
python -m pip install --target .deps -r backend\requirements.txt
$env:PYTHONPATH=".deps;backend"
uvicorn app.main:app --reload --app-dir backend
```

## Frontend Startup

```powershell
cd D:\desktop\ResearchFlow-Agent\frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

The Vite proxy forwards `/api` requests to:

```text
http://127.0.0.1:8000
```

## Environment Variables

Backend settings are defined in `backend/app/core/config.py`.

| Variable | Default | Description |
| --- | --- | --- |
| `RESEARCHFLOW_DATABASE_URL` | `sqlite:///./data/researchflow.sqlite3` | SQLAlchemy database URL. SQLite is the default development database. |
| `RESEARCHFLOW_UPLOAD_DIR` | `data/uploads` | Uploaded document storage directory. |
| `RESEARCHFLOW_REPO_DIR` | `data/repos` | Imported code repository storage directory. |
| `RESEARCHFLOW_SKILL_DIR` | `skills` | Root directory scanned by the Skill Registry. |
| `RESEARCHFLOW_LLM_PROVIDER` | `mock` | LLM provider: `mock`, `openai`, `openai_compatible`, `qwen`, or `deepseek`. |
| `RESEARCHFLOW_LLM_API_KEY` | empty | API key for real LLM providers. |
| `RESEARCHFLOW_LLM_BASE_URL` | empty | Optional OpenAI-compatible base URL. Leave empty for OpenAI default. |
| `RESEARCHFLOW_LLM_MODEL` | `gpt-4.1-mini` | Chat model name. |
| `RESEARCHFLOW_EMBEDDING_PROVIDER` | `mock` | Embedding provider: `mock`, `openai`, `openai_compatible`, or `qwen`. |
| `RESEARCHFLOW_EMBEDDING_API_KEY` | empty | API key for real embedding providers. Falls back to LLM key if empty. |
| `RESEARCHFLOW_EMBEDDING_BASE_URL` | empty | Optional embedding base URL. Falls back to LLM base URL if empty. |
| `RESEARCHFLOW_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model name. |
| `RESEARCHFLOW_EMBEDDING_DIMENSION` | `1536` | Expected embedding dimension for FAISS index construction. |
| `RESEARCHFLOW_RERANKER_PROVIDER` | `noop` | Reranker provider: `noop`, `openai`, `openai_compatible`, `qwen`, or `deepseek`. |
| `RESEARCHFLOW_RERANKER_API_KEY` | empty | API key for real reranker providers. Falls back to LLM key if empty. |
| `RESEARCHFLOW_RERANKER_BASE_URL` | empty | Optional reranker base URL. Falls back to LLM base URL if empty. |
| `RESEARCHFLOW_RERANKER_MODEL` | `gpt-4.1-mini` | Chat model used by the OpenAI-compatible reranker. |

Example:

```powershell
$env:RESEARCHFLOW_DATABASE_URL="sqlite:///./data/dev.sqlite3"
$env:RESEARCHFLOW_UPLOAD_DIR="data/uploads"
$env:RESEARCHFLOW_REPO_DIR="data/repos"
$env:RESEARCHFLOW_SKILL_DIR="skills"
```

The backend loads `.env` automatically through `python-dotenv`. Copy `.env.example` to `.env` for local development:

```powershell
Copy-Item .env.example .env
```

`.env` is ignored by Git. Do not commit real API keys.

Example OpenAI-compatible configuration:

```env
RESEARCHFLOW_LLM_PROVIDER=openai
RESEARCHFLOW_LLM_API_KEY=sk-your-key
RESEARCHFLOW_LLM_MODEL=gpt-4.1-mini

RESEARCHFLOW_EMBEDDING_PROVIDER=openai
RESEARCHFLOW_EMBEDDING_API_KEY=sk-your-key
RESEARCHFLOW_EMBEDDING_MODEL=text-embedding-3-small
RESEARCHFLOW_EMBEDDING_DIMENSION=1536

RESEARCHFLOW_RERANKER_PROVIDER=noop
```

Example DeepSeek LLM with mock embeddings:

```env
RESEARCHFLOW_LLM_PROVIDER=deepseek
RESEARCHFLOW_LLM_API_KEY=your-deepseek-key
RESEARCHFLOW_LLM_BASE_URL=https://api.deepseek.com
RESEARCHFLOW_LLM_MODEL=deepseek-chat

RESEARCHFLOW_EMBEDDING_PROVIDER=mock
RESEARCHFLOW_RERANKER_PROVIDER=noop
```

After switching from mock embeddings to real embeddings, rebuild project indexes because FAISS dimensions change:

```powershell
curl -X POST http://127.0.0.1:8000/api/projects/1/index/build
```

## End-to-End Demo Flow

### 1. Start Backend and Frontend

Backend:

```powershell
cd D:\desktop\ResearchFlow-Agent
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="backend"
uvicorn app.main:app --reload --app-dir backend
```

Frontend:

```powershell
cd D:\desktop\ResearchFlow-Agent\frontend
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

### 2. Create a Project

In the frontend:

1. Use the top project selector.
2. Click `New Project`.
3. Enter a project name and description.
4. Select the project.

API alternative:

```powershell
curl -X POST http://127.0.0.1:8000/api/projects `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"demo\",\"description\":\"Research demo project\"}"
```

### 3. Upload a Document

In `Knowledge Base`:

1. Click `Upload Document`.
2. Upload `.pdf`, `.md`, `.markdown`, or `.txt`.
3. Confirm the document appears in the document table.
4. Click `Chunks` to inspect parsed chunks.

API alternative:

```powershell
curl -X POST http://127.0.0.1:8000/api/projects/1/documents/upload `
  -F "file=@D:\path\paper.txt" `
  -F "chunk_size=800" `
  -F "chunk_overlap=120"
```

### 4. Build the Retrieval Index

In `Knowledge Base`, click `Build Index`.

API alternative:

```powershell
curl -X POST http://127.0.0.1:8000/api/projects/1/index/build
```

Indexes are stored under:

```text
data/indexes/{project_id}/
```

Main files:

```text
faiss.index
chunk_mapping.json
bm25.pkl
```

### 5. Ask a Question

In `Agent Workspace`, ask:

```text
What are the main methods in this document?
```

API alternative:

```powershell
curl -X POST http://127.0.0.1:8000/api/projects/1/agent/chat `
  -H "Content-Type: application/json" `
  -d "{\"message\":\"What are the main methods in this document?\"}"
```

### 6. View Citations

The Agent response includes citations such as:

```text
[doc:paper.txt chunk:3]
```

For repository QA, citations look like:

```text
[code:app.py:12]
```

### 7. View Trace

In `Agent Workspace`, the right panel shows runtime steps for the latest response.

In `Trace Viewer`:

1. Select a recent task.
2. Click `Load Trace`.
3. Inspect `node_name`, `input_json`, `output_json`, and `latency_ms`.

API alternative:

```powershell
curl http://127.0.0.1:8000/api/projects/1/tasks
curl http://127.0.0.1:8000/api/tasks/1/steps
```

### 8. View Memory

In `Memory Center`:

1. Filter by memory type.
2. Search memories.
3. Inspect episodic and reflection memories generated by Agent runs.
4. Delete bad memories if needed.

API alternative:

```powershell
curl http://127.0.0.1:8000/api/projects/1/memories
```

## API Summary

### Health

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Backend health check. |

### Projects

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/projects` | Create project. |
| `GET` | `/api/projects` | List projects. |
| `GET` | `/api/projects/{project_id}` | Get project. |
| `DELETE` | `/api/projects/{project_id}` | Delete project. |

### Documents

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/projects/{project_id}/documents/upload` | Upload and parse PDF/Markdown/TXT. |
| `GET` | `/api/projects/{project_id}/documents` | List project documents. |
| `GET` | `/api/documents/{document_id}` | Get document metadata. |
| `DELETE` | `/api/documents/{document_id}` | Delete document and chunks. |
| `GET` | `/api/documents/{document_id}/chunks` | List document chunks. |

### Retrieval

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/projects/{project_id}/index/build` | Build FAISS and BM25 indexes. |
| `POST` | `/api/projects/{project_id}/retrieve` | Hybrid retrieval test. |

### Agent

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/projects/{project_id}/agent/chat` | Run Agent workflow. |

Supported task types:

```text
paper_qa
repo_qa
log_debug
general_qa
```

### Repository Understanding

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/projects/{project_id}/repos/upload` | Upload ZIP repo or import local workspace path. |
| `GET` | `/api/projects/{project_id}/repos/tree` | Get file tree, README summary, files, and symbols. |
| `POST` | `/api/projects/{project_id}/repos/search` | Search filenames, content, and Python symbols. |
| `GET` | `/api/projects/{project_id}/repos/files?path=...` | Read a safe relative file path. |

### Memories

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/projects/{project_id}/memories` | Create memory. |
| `GET` | `/api/projects/{project_id}/memories` | List memories, optionally by type. |
| `POST` | `/api/projects/{project_id}/memories/search` | Search memories. |
| `DELETE` | `/api/memories/{memory_id}` | Delete memory. |

### Skills

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/skills` | List registered skills. |
| `GET` | `/api/skills/{skill_id}` | Get skill detail and `SKILL.md` content. |
| `POST` | `/api/skills/scan` | Scan `skills/` and sync database. |
| `POST` | `/api/projects/{project_id}/skills/search` | Search relevant skills for a task. |

### Skill Candidates

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/tasks/{task_id}/skill-candidates` | Generate candidate skill from a completed task. |
| `GET` | `/api/projects/{project_id}/skill-candidates` | List project candidate skills. |
| `POST` | `/api/skill-candidates/{candidate_id}/approve` | Approve and register candidate skill. |
| `POST` | `/api/skill-candidates/{candidate_id}/reject` | Reject candidate skill. |

### Tasks and Trace

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/projects/{project_id}/tasks` | List project tasks. |
| `GET` | `/api/tasks/{task_id}` | Get task metadata. |
| `GET` | `/api/tasks/{task_id}/steps` | Get persisted task steps. |

## Current Implemented Features

Backend:

- FastAPI application skeleton.
- SQLite + SQLAlchemy ORM.
- Startup database initialization with `create_all`.
- Project CRUD.
- Document upload, parsing, splitting, chunk persistence.
- Hybrid retrieval with FAISS + BM25 + score fusion.
- Mock embedding provider.
- LLM provider abstraction and MockLLMProvider.
- LangGraph Agent workflow.
- Agentic RAG with citations.
- Repository import, scan, search, safe file read.
- Experiment log parsing and rule-based diagnosis.
- Multi-layer memory manager, including session working memory and skill usage memory.
- Skill Registry parser, scanner, search, and APIs.
- Controlled skill candidate generation, approve, and reject flow.
- Persisted task and task step trace APIs.
- pytest coverage for main backend flows.

Frontend:

- Vue 3 + TypeScript + Element Plus management console.
- Left navigation, top project selector, and backend health indicator.
- Agent Workspace with answer, task type, citations, runtime steps, and session-level working memory.
- Structured `log_debug` result display.
- Knowledge Base with project creation, document upload/list/delete, chunk viewer, index build, retrieval test, repository import/search.
- Memory Center with list, filter, search, create, and delete.
- Skill Registry with skill list, SKILL.md viewer, scan button, candidate review.
- Trace Viewer with task selection and persisted step inspection.
- Centralized `src/api/` API clients.
- Shared TypeScript API types in `src/types/api.ts`.

Testing and checks:

```powershell
.\.venv\Scripts\python.exe -m compileall backend\app tests
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m pytest tests
cd frontend
npm run build
```

The latest validation completed with:

```text
backend compile: passed
pytest: 23 passed
frontend build: passed
```

## Roadmap

Near-term:

- Add Alembic migrations instead of relying only on `create_all`.
- Add richer task list and task detail views.
- Add document re-index and repository re-scan controls.
- Add frontend project delete and edit support.
- Add better markdown rendering for Agent answers.
- Add pagination for documents, memories, tasks, and trace steps.

Model and retrieval:

- Add real embedding providers such as bge-m3, OpenAI embeddings, or Qwen embeddings.
- Add real LLM providers for OpenAI, Qwen, DeepSeek, and Claude.
- Add reranker model support.
- Add token-aware text splitting.
- Add document-level metadata filters and citation previews.

Repository understanding:

- Add multi-repository support per project.
- Add tree-sitter for multi-language symbol extraction.
- Add code chunk indexing into the RAG retrieval layer.
- Add dependency graph and call graph analysis.
- Add safer, opt-in repository commands with explicit approval.

Memory and skills:

- Add soft delete and audit trail for memories.
- Add memory quality review.
- Add skill versioning.
- Add skill execution sandbox design.
- Add approval workflow for generated scripts before any execution support.

MCP and tools:

- Wrap existing tool modules as MCP-compatible tools.
- Add MCP server/client configuration.
- Add tool permission policies.
- Add richer trace records for tool inputs, outputs, and errors.

Production readiness:

- Add authentication and workspace isolation.
- Add PostgreSQL deployment profile.
- Add background jobs for large uploads and indexing.
- Add file size limits and upload progress.
- Add Docker Compose.
- Add structured logging and observability.

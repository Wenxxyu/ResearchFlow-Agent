# ResearchFlow-Agent Architecture

## Phase 1 Scope

第一阶段只实现可运行项目骨架，不实现完整 Agentic RAG。目标是为后续模块提供清晰边界。

## Backend Layers

```text
API Route -> Pydantic Schema -> Service Layer -> DB / Agent / LLM / Tool
```

- `api/`：HTTP 路由，只负责请求响应边界。
- `schemas/`：Pydantic request/response schema。
- `services/`：业务服务层，后续承载文档处理、检索、记忆和 Skill 管理。
- `db/`：SQLAlchemy engine、session 和 ORM models。
- `agent/`：LangGraph 工作流层。
- `llm/`：统一 LLM Provider 接口，当前默认 `MockLLMProvider`。

## Frontend Layers

```text
Vue Page -> API Client -> FastAPI
```

- `src/api/`：Axios API 客户端。
- `src/components/`：可复用组件。
- `src/styles/`：全局样式。

## Data Directories

- `data/researchflow.sqlite3`：开发默认 SQLite 数据库。
- `data/uploads/`：后续存放上传论文、文档和日志。
- `data/indexes/`：后续存放 FAISS、BM25 等本地索引。

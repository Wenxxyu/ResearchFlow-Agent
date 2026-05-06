# ResearchFlow-Agent

ResearchFlow-Agent 鏄竴涓潰鍚戠爺绌剁敓绉戠爺鍦烘櫙鐨勫叏鏍?Agent 鏅鸿兘浣撶郴缁?MVP銆傞」鐩仛鐒﹁鏂囬槄璇汇€佷唬鐮佷粨搴撶悊瑙ｃ€佸疄楠屾棩蹇楀垎鏋愬拰鍙鐢?Skill 绠＄悊锛屾敮鎸?Agentic RAG銆佸绫诲瀷璁板繂銆丼kill Registry銆佸彈鎺?Skill 鑷繘鍖栥€佸伐鍏疯皟鐢ㄥ拰鎵ц杞ㄨ抗鍙鍖栥€?
褰撳墠鐗堟湰榛樿鍙互鍦ㄦ棤鐪熷疄妯″瀷 API Key 鐨勬儏鍐典笅杩愯銆傜郴缁熷唴缃?`MockLLMProvider`銆乣MockEmbeddingProvider` 鍜?`NoopReranker`锛屼究浜庢湰鍦板揩閫熻窇閫氬畬鏁存祦绋嬶紱鍚庣画鍙€氳繃 `.env` 鍒囨崲鍒?OpenAI銆丵wen銆丏eepSeek 绛?OpenAI-compatible API銆?
## 鏍稿績鑳藉姏

### Agentic RAG

ResearchFlow-Agent 鐨勯棶绛旀祦绋嬩笉鏄畝鍗曗€滄瘡涓棶棰橀兘妫€绱⑩€濓紝鑰屾槸涓€涓彲杩借釜鐨?Agentic RAG 宸ヤ綔娴侊細

```text
User Query
  -> Working Memory Recall
  -> Router / Intent Classifier
  -> 鍒ゆ柇鏄惁闇€瑕佸閮ㄧ煡璇?    -> 涓嶉渶瑕侊細Direct Answer
    -> 闇€瑕侊細Query Rewrite
            -> Memory Recall
            -> Skill Recall
            -> Code Search / Hybrid Retrieval
            -> Evidence Selection
            -> Answer with Citations
            -> Citation Verify
  -> Working Memory Writer
  -> Reflection Writer
  -> Trace Writer
```

宸叉敮鎸侊細

- 涓婁紶 PDF銆丮arkdown銆乀XT 鏂囨。銆?- PDF 浣跨敤 PyMuPDF 瑙ｆ瀽銆?- Markdown/TXT 鐩存帴璇诲彇鏂囨湰銆?- 浣跨敤鏈湴 `RecursiveTextSplitter` 鍒囧垎鏂囨。銆?- 鏂囨。 chunk 鍐欏叆 SQLite銆?- 鏋勫缓椤圭洰绾ф贩鍚堟绱㈢储寮曪細
  - FAISS 鍚戦噺妫€绱?  - rank-bm25 鍏抽敭璇嶆绱?  - score normalization
  - merge and deduplicate
  - task_type 鍔ㄦ€佹潈閲?  - NoopReranker 棰勭暀鎺ュ彛
- 鍥炵瓟涓繑鍥炲紩鐢ㄦ爣璁帮紝渚嬪锛?
```text
[doc:paper.txt chunk:3]
[code:backend/app/main.py:12]
```

### 澶氱被鍨嬭蹇?
椤圭洰閲囩敤缁熶竴 `memories` 琛ㄥ拰 `MemoryManager` 绠＄悊澶氱被鍨嬭蹇嗭紝涓嶆槸鍏鐙珛绯荤粺銆侻VP 闃舵閲嶇偣钀藉湴 working銆乪pisodic銆乺eflection銆乻kill锛宻emantic 鍜?user_profile 浣滀负鎵╁睍绫诲瀷淇濈暀銆?
璁板繂绫诲瀷鍖呮嫭锛?
| 绫诲瀷 | 浣滅敤 |
| --- | --- |
| `working` | 浼氳瘽绾х煭鏈熶笂涓嬫枃锛岀敤浜庡杞璇濄€佽拷闂拰鎸囦唬娑堣В |
| `episodic` | 鍘嗗彶浠诲姟鎽樿锛岃褰?Agent 鍋氳繃浠€涔?|
| `semantic` | 绋冲畾椤圭洰鐭ヨ瘑銆佽鏂囩粨璁恒€佽儗鏅簨瀹?|
| `user_profile` | 鐢ㄦ埛鍋忓ソ锛屼緥濡傝瑷€銆佸洖绛旈鏍笺€佺爺绌舵柟鍚?|
| `reflection` | 澶辫触鍘熷洜銆佹棩蹇楄瘖鏂粡楠屻€佹敼杩涘缓璁?|
| `skill` | Skill 浣跨敤缁忛獙锛屼緥濡傛煇涓?Skill 浣曟椂瑙﹀彂銆佹晥鏋滃浣?|

璁板繂鍙洖璇勫垎鍏紡锛?
```text
score = similarity * 0.5 + importance * 0.2 + recency * 0.2 + type_match * 0.1
```

浼氳瘽绾?working memory 宸叉帴鍏?Agent Chat锛?
- 鍓嶇涓烘瘡涓」鐩敓鎴?`conversation_id`銆?- 璇锋眰 `/api/projects/{project_id}/agent/chat` 鏃舵惡甯?`conversation_id`銆?- 鍚庣鍐欏叆 `memory_type="working"`銆?- 閫氳繃 `tags_json` 淇濆瓨 `conversation:conv-...`銆?- 姣忎釜 conversation 榛樿淇濈暀鏈€杩?12 杞€?- 杩欐槸浼氳瘽杩炵画涓婁笅鏂囷紝涓嶆槸 checkpoint 鎭㈠銆?
Skill memory 涓?Skill Registry 鐨勫尯鍒細

```text
Skill Registry = 鎶€鑳藉畾涔夛紝鏉ヨ嚜 skills/*/SKILL.md
Skill Memory   = 鎶€鑳藉湪鍏蜂綋椤圭洰浠诲姟涓殑浣跨敤缁忛獙
```

渚嬪 `pytorch_log_debug` 琚煇娆?CUDA OOM 浠诲姟鍛戒腑骞舵垚鍔熺粰鍑哄缓璁悗锛岀郴缁熶細娌夋穩涓€鏉?`memory_type="skill"` 鐨勭粡楠岋紝鍚庣画绫讳技鏃ュ織闂鍙互鍙洖鍙傝€冦€?
### Skill Registry

Skill 鐩綍缁撴瀯锛?
```text
skills/
  skill_name/
    SKILL.md
    scripts/
    references/
    assets/
```

`SKILL.md` 鏀寔 YAML frontmatter锛屼緥濡傦細

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

褰撳墠榛樿鎻愪緵 3 涓ず渚?Skill锛?
- `paper_review`
- `pytorch_log_debug`
- `repo_understanding`

瀹夊叏杈圭晫锛?
- 褰撳墠鐗堟湰鍙鍙栧拰灞曠ず Skill銆?- Agent 鍙互鎶?Skill 鎽樿娉ㄥ叆涓婁笅鏂囥€?- 涓嶈嚜鍔ㄦ墽琛?`scripts/` 涓嬬殑浠绘剰浠ｇ爜銆?- 涓哄悗缁彈鎺ф墽琛屻€佸鎵瑰拰娌欑鏈哄埗棰勭暀鎺ュ彛銆?
### Skill 鑷繘鍖栭洀褰?
椤圭洰瀹炵幇浜嗗彈鎺х殑 candidate skill 鐢熸垚銆佸鏍稿拰娉ㄥ唽娴佺▼锛?
```text
浠诲姟鎵ц瀹屾垚
  -> Evaluator 鍒ゆ柇浠诲姟鏄惁鎴愬姛
  -> Reflection Generator 鎬荤粨鍙鐢ㄧ粡楠?  -> Skill Miner 鍒ゆ柇鏄惁鍊煎緱娌夋穩
  -> 鐢熸垚 candidate SKILL.md
  -> 鐢ㄦ埛瀹℃牳
  -> 瀹℃牳閫氳繃鍚庡啓鍏?skills/{skill_name}/SKILL.md
  -> scan skills 鍚屾鍒版暟鎹簱
```

瀹夊叏绛栫暐锛?
- candidate skill 榛樿涓嶅惎鐢ㄣ€?- 蹇呴』浜哄伐 approve 鍚庢墠鍐欏叆 `skills/`銆?- 鍐欏叆璺緞浼氭牎楠岋紝閬垮厤璺緞绌胯秺銆?- 褰撳墠鍙敓鎴?`SKILL.md`锛屼笉鑷姩鐢熸垚鍙墽琛岃剼鏈€?
### 浠ｇ爜浠撳簱鐞嗚В

鏀寔涓婁紶 zip 浠ｇ爜浠撳簱鎴栨寚瀹氭湰鍦颁粨搴撹矾寰勶紝骞跺鍏ュ埌锛?
```text
data/repos/{project_id}/
```

宸插疄鐜帮細

- 瀹夊叏瑙ｅ帇鍜岃矾寰勬牎楠屻€?- 蹇界暐 `.git`銆乣node_modules`銆乣__pycache__`銆乣.venv`銆乣dist`銆乣build` 绛夌洰褰曘€?- 鏂囦欢鏍戞壂鎻忋€?- 鏂囦欢璇█绫诲瀷璇嗗埆銆?- README 鎽樿銆?- Python 鏂囦欢 class/function 瑙ｆ瀽锛屽熀浜?`ast`銆?- 鏂囦欢鍚嶆悳绱€?- 鍐呭鍏抽敭璇嶆悳绱€?- Python 绗﹀彿鎼滅储銆?- 瀹夊叏璇诲彇鏂囦欢锛岄檺鍒跺ぇ鏂囦欢闀垮害銆?- `repo_qa` 宸ヤ綔娴佸彲鏍规嵁浠ｇ爜鐗囨鍥炵瓟锛屽苟杩斿洖鏂囦欢璺緞鍜岃鍙峰紩鐢ㄣ€?
### 瀹為獙鏃ュ織鍒嗘瀽

鏀寔鐢ㄦ埛绮樿创璁粌鏃ュ織銆佹姤閿欎俊鎭垨 traceback锛孉gent 鑷姩璇嗗埆 `log_debug` 浠诲姟銆?
鍙瘑鍒ā寮忓寘鎷細

- `Traceback`
- `CUDA out of memory`
- `RuntimeError`
- `shape mismatch`
- `nan loss`
- `checkpoint loading failed`
- `ModuleNotFoundError`
- `PermissionError`

杈撳嚭缁撴瀯锛?
- 閿欒鎽樿
- 鍙兘鍘熷洜
- 鎺掓煡姝ラ
- 淇寤鸿
- 闇€瑕佺敤鎴疯ˉ鍏呯殑淇℃伅

褰撳墠瀹炵幇鍩轰簬瑙勫垯鍜?MockLLMProvider锛屼笉浼氬亣瑁呬竴瀹氳兘淇锛涙棤娉曞垽鏂椂浼氭彁绀虹敤鎴疯ˉ鍏呮棩蹇椼€佺幆澧冨拰閰嶇疆銆?
### 鎵ц杞ㄨ抗鍙鍖?
姣忔 Agent 杩愯閮戒細鎸佷箙鍖栧畬鏁?trace锛?
- 璺敱缁撴灉
- 鏄惁闇€瑕佹绱?- 妫€绱㈣瘉鎹?- Skill 鍙洖
- Memory 鍙洖
- 宸ュ叿璋冪敤缁撴灉
- 鑺傜偣杈撳叆鎽樿
- 鑺傜偣杈撳嚭
- 寤惰繜 `latency_ms`
- 鏈€缁堢瓟妗?
鍓嶇 Trace Viewer 鏀寔鎸?`task_id` 鏌ョ湅鎵ц姝ラ銆?
## 鎶€鏈爤

鍚庣锛?
- Python
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- LangGraph
- FAISS
- rank-bm25
- PyMuPDF
- python-dotenv

鍓嶇锛?
- Vue 3
- TypeScript
- Vite
- Element Plus
- Axios

妯″瀷鎺ュ彛锛?
- `MockLLMProvider`
- `OpenAICompatibleLLMProvider`
- OpenAI / Qwen / DeepSeek 鍏煎鎵╁睍
- `MockEmbeddingProvider`
- `OpenAICompatibleEmbeddingProvider`
- `NoopReranker`
- OpenAI-compatible reranker 棰勭暀

## 椤圭洰缁撴瀯

```text
ResearchFlow-Agent/
  backend/
    requirements.txt
    app/
      main.py
      core/
        config.py
      db/
        base.py
        session.py
      api/
        router.py
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
      agent/
        state.py
        workflow.py
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

  frontend/
    package.json
    vite.config.ts
    src/
      App.vue
      main.ts
      api/
      pages/
        AgentWorkspace.vue
        KnowledgeBase.vue
        MemoryCenter.vue
        SkillRegistry.vue
        TraceViewer.vue
      styles/
      types/

  skills/
    paper_review/
      SKILL.md
    pytorch_log_debug/
      SKILL.md
    repo_understanding/
      SKILL.md

  data/
    .gitkeep
    uploads/.gitkeep
    indexes/.gitkeep
    repos/.gitkeep

  docs/
  tests/
  .env.example
  README.md
```

## 鐜鍙橀噺

澶嶅埗 `.env.example` 涓?`.env`锛?
```powershell
Copy-Item .env.example .env
```

榛樿 Mock 閰嶇疆鍙互鐩存帴杩愯锛?
```env
RESEARCHFLOW_LLM_PROVIDER=mock
RESEARCHFLOW_EMBEDDING_PROVIDER=mock
RESEARCHFLOW_RERANKER_PROVIDER=noop
```

鏍稿績璺緞閰嶇疆锛?
```env
RESEARCHFLOW_DATABASE_URL=sqlite:///./data/researchflow.sqlite3
RESEARCHFLOW_UPLOAD_DIR=data/uploads
RESEARCHFLOW_REPO_DIR=data/repos
RESEARCHFLOW_SKILL_DIR=skills
```

鎺ュ叆鐪熷疄 LLM 绀轰緥锛?
```env
RESEARCHFLOW_LLM_PROVIDER=qwen
RESEARCHFLOW_LLM_API_KEY=your_api_key
RESEARCHFLOW_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
RESEARCHFLOW_LLM_MODEL=qwen-plus
RESEARCHFLOW_LLM_TIMEOUT_SECONDS=30
```

鎺ュ叆鐪熷疄 embedding 绀轰緥锛?
```env
RESEARCHFLOW_EMBEDDING_PROVIDER=openai
RESEARCHFLOW_EMBEDDING_API_KEY=your_api_key
RESEARCHFLOW_EMBEDDING_BASE_URL=https://api.openai.com/v1
RESEARCHFLOW_EMBEDDING_MODEL=text-embedding-3-small
RESEARCHFLOW_EMBEDDING_DIMENSION=1536
```

娉ㄦ剰锛?
- `.env` 鍖呭惈鐪熷疄瀵嗛挜锛屽凡琚?`.gitignore` 蹇界暐銆?- GitHub 鍙笂浼?`.env.example`銆?- 鏈湴 SQLite銆佷笂浼犳枃浠躲€佺储寮曞拰浠撳簱鏁版嵁榛樿涓嶄笂浼犮€?
## 鍚庣鍚姩

鍦ㄩ」鐩牴鐩綍鎵ц锛?
```powershell
cd D:\desktop\ResearchFlow-Agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
$env:PYTHONPATH="backend"
uvicorn app.main:app --reload --app-dir backend
```

鍚庣榛樿鍦板潃锛?
```text
http://127.0.0.1:8000
```

鍋ュ悍妫€鏌ワ細

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

棰勬湡杩斿洖锛?
```json
{
  "status": "ok",
  "app_name": "ResearchFlow-Agent",
  "version": "0.1.0"
}
```

## 鍓嶇鍚姩

鎵撳紑鏂扮殑 PowerShell锛?
```powershell
cd D:\desktop\ResearchFlow-Agent\frontend
npm install
npm run dev
```

鍓嶇榛樿鍦板潃锛?
```text
http://127.0.0.1:5173
```

鍓嶇浼氶€氳繃 Vite proxy 璋冪敤鍚庣 `/api`銆?
## 绔埌绔?Demo 娴佺▼

### 1. 鍒涘缓椤圭洰

杩涘叆鍓嶇锛?
```text
Knowledge Base -> Create Project
```

鍒涘缓涓€涓」鐩紝渚嬪锛?
```text
Agentic RAG Paper Reading
```

### 2. 涓婁紶鏂囨。

鍦?Knowledge Base 椤甸潰閫夋嫨椤圭洰锛屼笂浼狅細

- PDF
- Markdown
- TXT

涓婁紶鍚庣郴缁熶細锛?
```text
淇濆瓨鏂囦欢 -> 瑙ｆ瀽鏂囨湰 -> 鍒囧垎 chunk -> 鍐欏叆 documents/chunks 琛?```

### 3. 鏋勫缓绱㈠紩

鐐瑰嚮锛?
```text
Build Index
```

绯荤粺浼氫负褰撳墠椤圭洰鏋勫缓锛?
- FAISS index
- BM25 index
- chunk id mapping

绱㈠紩淇濆瓨鍒帮細

```text
data/indexes/{project_id}/
```

### 4. 妫€绱㈡祴璇?
鍦?Knowledge Base 鐨?retrieval test 杈撳叆闂锛屼緥濡傦細

```text
What retrieval methods does this project use?
```

杩斿洖缁撴灉浼氬寘鍚細

- source
- content
- score
- score_breakdown
- metadata

### 5. Agent 闂瓟

杩涘叆 Agent Workspace锛岄€夋嫨椤圭洰锛岃緭鍏ワ細

```text
What retrieval methods does this project use?
```

Agent 浼氳嚜鍔細

```text
Router -> Query Rewrite -> Memory Recall -> Skill Recall -> Hybrid Retrieval -> Evidence Selection -> Answer
```

鍥炵瓟涓簲鍖呭惈绫讳技寮曠敤锛?
```text
[doc:agent.txt chunk:1]
```

### 6. 澶氳疆浼氳瘽

Agent Workspace 宸叉敮鎸侊細

- `Enter` 鍙戦€?- `Shift + Enter` 鎹㈣
- 姣忎釜椤圭洰鐙珛 `conversation_id`
- New Conversation 閲嶇疆浼氳瘽

鍙互娴嬭瘯锛?
```text
鎴戝枩娆㈢殑妗嗘灦鏄?LangGraph
```

鐒跺悗缁х画闂細

```text
鎴戝垰鎵嶈鎴戝枩娆粈涔堟鏋讹紵
```

Trace 涓簲鐪嬪埌锛?
```text
working_memory_recall_node
working_memory_writer_node
```

### 7. 鏌ョ湅 Memory

杩涘叆 Memory Center锛?
- 鎸?`memory_type` 绛涢€?- 鎼滅储璁板繂
- 鏌ョ湅 `working`銆乣episodic`銆乣reflection`銆乣skill`
- 鍒犻櫎閿欒璁板繂

褰撳墠 MVP 浣跨敤纭垹闄わ紝渚夸簬娓呴櫎閿欒璁板繂锛岄伩鍏嶆薄鏌撳悗缁彫鍥炪€?
### 8. 鏌ョ湅 Skill

杩涘叆 Skill Registry锛?
- 鏌ョ湅 Skill 鍒楄〃
- 鏌ョ湅 `SKILL.md` 鍐呭
- 鐐瑰嚮 scan skills
- 鏌ョ湅 usage count 鍜?success rate
- 瀹℃牳 candidate skill

### 9. 鏌ョ湅 Trace

杩涘叆 Trace Viewer锛?
- 閫夋嫨椤圭洰
- 閫夋嫨 task
- 鏌ョ湅鑺傜偣鎵ц姝ラ

姣忎釜 step 鍖呭惈锛?
- `node_name`
- `input_json`
- `output_json`
- `latency_ms`

## API 绠€琛?
### Health

| Method | Path | 璇存槑 |
| --- | --- | --- |
| `GET` | `/api/health` | 鍋ュ悍妫€鏌?|

### Projects

| Method | Path | 璇存槑 |
| --- | --- | --- |
| `POST` | `/api/projects` | 鍒涘缓椤圭洰 |
| `GET` | `/api/projects` | 椤圭洰鍒楄〃 |
| `GET` | `/api/projects/{project_id}` | 椤圭洰璇︽儏 |
| `DELETE` | `/api/projects/{project_id}` | 鍒犻櫎椤圭洰 |

### Documents

| Method | Path | 璇存槑 |
| --- | --- | --- |
| `POST` | `/api/projects/{project_id}/documents/upload` | 涓婁紶鏂囨。 |
| `GET` | `/api/projects/{project_id}/documents` | 椤圭洰鏂囨。鍒楄〃 |
| `GET` | `/api/documents/{document_id}` | 鏂囨。璇︽儏 |
| `GET` | `/api/documents/{document_id}/chunks` | 鏌ョ湅 chunk |
| `DELETE` | `/api/documents/{document_id}` | 鍒犻櫎鏂囨。 |

### Retrieval

| Method | Path | 璇存槑 |
| --- | --- | --- |
| `POST` | `/api/projects/{project_id}/index/build` | 鏋勫缓妫€绱㈢储寮?|
| `POST` | `/api/projects/{project_id}/retrieve` | 娣峰悎妫€绱?|

### Agent

| Method | Path | 璇存槑 |
| --- | --- | --- |
| `POST` | `/api/projects/{project_id}/agent/chat` | Agent 闂瓟 |

璇锋眰绀轰緥锛?
```json
{
  "message": "What retrieval methods does this project use?",
  "conversation_id": "conv-123"
}
```

鍝嶅簲鍖呭惈锛?
- `task_id`
- `conversation_id`
- `task_type`
- `answer`
- `citations`
- `steps`
- `errors`

### Memories

| Method | Path | 璇存槑 |
| --- | --- | --- |
| `POST` | `/api/projects/{project_id}/memories` | 鍒涘缓璁板繂 |
| `GET` | `/api/projects/{project_id}/memories` | 璁板繂鍒楄〃 |
| `POST` | `/api/projects/{project_id}/memories/search` | 鎼滅储璁板繂 |
| `DELETE` | `/api/memories/{memory_id}` | 鍒犻櫎璁板繂 |

### Skills

| Method | Path | 璇存槑 |
| --- | --- | --- |
| `GET` | `/api/skills` | Skill 鍒楄〃 |
| `GET` | `/api/skills/{skill_id}` | Skill 璇︽儏 |
| `POST` | `/api/skills/scan` | 鎵弿 Skill 鐩綍 |
| `POST` | `/api/projects/{project_id}/skills/search` | 鎼滅储鐩稿叧 Skill |

### Skill Candidates

| Method | Path | 璇存槑 |
| --- | --- | --- |
| `POST` | `/api/tasks/{task_id}/skill-candidates` | 浠庝换鍔＄敓鎴?candidate skill |
| `GET` | `/api/projects/{project_id}/skill-candidates` | 椤圭洰 candidate skills |
| `POST` | `/api/skill-candidates/{candidate_id}/approve` | 瀹℃牳閫氳繃 |
| `POST` | `/api/skill-candidates/{candidate_id}/reject` | 鎷掔粷 |

### Repositories

| Method | Path | 璇存槑 |
| --- | --- | --- |
| `POST` | `/api/projects/{project_id}/repos/upload` | 涓婁紶 zip 浠ｇ爜浠撳簱 |
| `POST` | `/api/projects/{project_id}/repos/import-local` | 瀵煎叆鏈湴浠撳簱 |
| `GET` | `/api/projects/{project_id}/repos/tree` | 鑾峰彇鏂囦欢鏍戝拰绗﹀彿 |
| `POST` | `/api/projects/{project_id}/repos/search` | 鎼滅储浠ｇ爜 |
| `GET` | `/api/projects/{project_id}/repos/files?path=` | 瀹夊叏璇诲彇鏂囦欢 |

### Tasks / Trace

| Method | Path | 璇存槑 |
| --- | --- | --- |
| `GET` | `/api/projects/{project_id}/tasks` | 椤圭洰浠诲姟鍒楄〃 |
| `GET` | `/api/tasks/{task_id}` | 浠诲姟璇︽儏 |
| `GET` | `/api/tasks/{task_id}/steps` | 浠诲姟鎵ц姝ラ |

## 娴嬭瘯涓庢鏌?
鍚庣缂栬瘧妫€鏌ワ細

```powershell
.\.venv\Scripts\python.exe -m compileall backend\app tests
```

鍚庣娴嬭瘯锛?
```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m pytest tests
```

鍓嶇鏋勫缓锛?
```powershell
cd frontend
npm run build
```

褰撳墠娴嬭瘯瑕嗙洊涓昏鍖呮嫭锛?
- health
- project CRUD
- document upload / chunks
- hybrid retrieval
- agent workflow
- working memory
- skill memory
- memories API
- skill registry
- skill candidates
- repository import/search

## 褰撳墠宸插疄鐜板姛鑳?
鍚庣锛?
- FastAPI 搴旂敤楠ㄦ灦銆?- SQLite + SQLAlchemy ORM銆?- 鍚姩鏃惰嚜鍔?`create_all`銆?- Project CRUD銆?- Document upload / parse / split / chunk persistence銆?- Hybrid retrieval锛欶AISS + BM25 + fusion銆?- BaseRetriever / BM25Retriever / VectorRetriever / HybridRetriever銆?- Mock embedding provider銆?- LLM provider 鎶借薄鍜?MockLLMProvider銆?- OpenAI-compatible LLM provider銆?- LangGraph Agent workflow銆?- Agentic RAG with citations銆?- Direct Answer 璺敱銆?- Session-level working memory銆?- Episodic / reflection / skill memory銆?- Skill Registry parser / scanner / search銆?- Controlled candidate skill approve/reject銆?- Repository import / scan / search / safe file read銆?- Experiment log parser and rule-based diagnosis銆?- Persisted task steps and trace APIs銆?- pytest 瑕嗙洊鏍稿績娴佺▼銆?
鍓嶇锛?
- Vue 3 + TypeScript + Element Plus 绠＄悊鐣岄潰銆?- 宸︿晶瀵艰埅銆?- 椤堕儴椤圭洰閫夋嫨銆?- 鍚庣鍋ュ悍鐘舵€併€?- Agent Workspace銆?- Enter 鍙戦€侊紝Shift+Enter 鎹㈣銆?- 浼氳瘽绾?working memory 鏍囪瘑鍜?New Conversation銆?- Knowledge Base銆?- Memory Center銆?- Skill Registry銆?- Trace Viewer銆?- `src/api` 缁熶竴 API 灏佽銆?- `src/types` 缁熶竴 TypeScript 绫诲瀷銆?
## GitHub 涓婁紶璇存槑

椤圭洰 `.gitignore` 宸查厤缃細

```text
.env
.venv/
.tmp/
.idea/
frontend/node_modules/
frontend/dist/
data/**
skills/*_task_*/
```

鍙繚鐣欙細

```text
.env.example
data/.gitkeep
data/uploads/.gitkeep
data/indexes/.gitkeep
data/repos/.gitkeep
skills/paper_review/SKILL.md
skills/pytorch_log_debug/SKILL.md
skills/repo_understanding/SKILL.md
```

鍥犳涓嶄細涓婁紶锛?
- 鐪熷疄 API Key
- SQLite 鏁版嵁搴?- 涓婁紶 PDF
- FAISS/BM25 绱㈠紩
- 鏈湴瀵煎叆浠撳簱
- 澶фā鍨嬫潈閲嶆枃浠?- node_modules
- Python 铏氭嫙鐜

## 鍚庣画瑙勫垝

Agent 鑳藉姏锛?
- 鏇寸粏绮掑害 Query Analyzer銆?- 鏇村己 Evidence Selection銆?- 鍙彃鎷?bge-reranker銆?- LangGraph checkpoint 鎭㈠銆?- 鏇村畬鏁村伐鍏疯皟鐢ㄥ崗璁€?- MCP 宸ュ叿鎺ュ叆銆?
RAG 鑳藉姏锛?
- 鎺ュ叆鐪熷疄 embedding锛屼緥濡?bge-m3銆丱penAI embedding銆?- 澧炲姞 chunk-level metadata filter銆?- 澧炲姞 citation verification銆?- 澧炲姞澶氭枃妗ｅ姣旈棶绛斻€?
浠ｇ爜鐞嗚В锛?
- 寮曞叆 tree-sitter銆?- 鏋勫缓璺ㄨ瑷€ symbol graph銆?- 鏀寔璋冪敤閾惧垎鏋愩€?- 鏀寔渚濊禆鍥惧拰妯″潡鍏崇郴鍥俱€?
璁板繂涓?Skill锛?
- 璁板繂杞垹闄ゅ拰瀹¤銆?- 璁板繂璐ㄩ噺璇勫垎銆?- Skill 鐗堟湰绠＄悊銆?- Skill 浣跨敤鏁堟灉璇勪及銆?- 鍙楁帶鑴氭湰鎵ц娌欑銆?
鍓嶇锛?
- Markdown 娓叉煋銆?- 寮曠敤鐐瑰嚮璺宠浆鍘熸枃 chunk銆?- Trace 鑺傜偣鍥惧彲瑙嗗寲銆?- Skill candidate diff 瀹℃牳銆?- 鏂囨。棰勮鍜屼唬鐮佹枃浠堕瑙堛€?

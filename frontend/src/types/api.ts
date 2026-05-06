export interface Project {
  id: number
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface DocumentRecord {
  id: number
  project_id: number
  filename: string
  file_type: string
  file_path: string
  status: string
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface ChunkRecord {
  id: number
  document_id: number
  project_id: number
  chunk_index: number
  content: string
  metadata_json: string | null
  created_at: string
}

export interface BuildIndexResponse {
  project_id: number
  chunk_count: number
  vector_count: number
  bm25_count: number
  status: string
}

export interface RetrievalResult {
  chunk_id: number
  document_id: number
  project_id: number
  chunk_index: number
  source: string
  content: string
  filename: string
  file_type: string
  score: number
  score_breakdown: Record<string, number>
  vector_score: number
  bm25_score: number
  metadata: Record<string, unknown>
}

export interface RetrieveResponse {
  project_id: number
  query: string
  top_k: number
  results: RetrievalResult[]
}

export interface LogAnalysis {
  summary: string
  possible_causes: string[]
  troubleshooting_steps: string[]
  fix_suggestions: string[]
  need_more_info: string[]
}

export interface AgentStep {
  node_name: string
  input: Record<string, unknown>
  output: Record<string, unknown>
  latency_ms: number
}

export interface AgentChatResponse {
  task_id: number
  conversation_id: string | null
  task_type: string
  answer: string
  log_analysis: LogAnalysis | null
  citations: string[]
  steps: AgentStep[]
  errors: string[]
}

export interface MemoryRecord {
  id: number
  project_id: number
  memory_type: string
  content: string
  summary: string | null
  importance: number
  confidence: number
  source_task_id: number | null
  tags_json: string | null
  created_at: string
  last_accessed_at: string | null
}

export interface MemorySearchResult {
  memory: MemoryRecord
  score: number
  similarity: number
  recency: number
  type_match: number
}

export interface SkillRecord {
  id: number
  name: string
  description: string | null
  trigger: string | null
  path: string
  status: string
  usage_count: number
  success_count: number
  created_from_task_id: number | null
  created_at: string
  updated_at: string
}

export interface SkillDetail extends SkillRecord {
  tools: string[]
  content: string
}

export interface SkillScanResponse {
  scanned_count: number
  skills: SkillRecord[]
}

export interface SkillCandidate {
  id: number
  project_id: number
  name: string
  description: string
  content: string
  source_task_id: number
  status: string
  created_at: string
  updated_at: string
}

export interface RepoImportResponse {
  project_id: number
  file_count: number
  symbol_count: number
  readme_summary: string
}

export interface RepoTreeResponse {
  project_id: number
  tree: Record<string, unknown>[]
  files: Array<{ path: string; language: string; size: number }>
  symbols: Array<{ name: string; type: string; path: string; line_start: number; line_end: number }>
  readme_summary: string
}

export interface RepoSearchResult {
  path: string
  line_start: number
  line_end: number
  snippet: string
  match_type: string
  symbol_name: string | null
}

export interface TaskRecord {
  id: number
  project_id: number
  task_type: string
  user_input: string
  status: string
  final_answer: string | null
  created_at: string
  updated_at: string
}

export interface TaskStepRecord {
  id: number
  task_id: number
  node_name: string
  input_json: string | null
  output_json: string | null
  latency_ms: number | null
  created_at: string
}

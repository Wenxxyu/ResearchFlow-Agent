import axios from 'axios'
import type { MemoryRecord, MemorySearchResult } from '../types/api'
export type { MemoryRecord, MemorySearchResult } from '../types/api'

export async function listMemories(projectId: number, memoryType?: string): Promise<MemoryRecord[]> {
  const { data } = await axios.get<MemoryRecord[]>(`/api/projects/${projectId}/memories`, {
    params: memoryType ? { memory_type: memoryType } : undefined
  })
  return data
}

export async function createMemory(
  projectId: number,
  payload: {
    memory_type: string
    content: string
    summary?: string | null
    importance: number
    confidence: number
    tags: string[]
  }
): Promise<MemoryRecord> {
  const { data } = await axios.post<MemoryRecord>(`/api/projects/${projectId}/memories`, payload)
  return data
}

export async function searchMemories(
  projectId: number,
  payload: { query: string; top_k: number; memory_type?: string | null; min_confidence: number }
): Promise<MemorySearchResult[]> {
  const { data } = await axios.post<MemorySearchResult[]>(`/api/projects/${projectId}/memories/search`, payload)
  return data
}

export async function deleteMemory(memoryId: number): Promise<void> {
  await axios.delete(`/api/memories/${memoryId}`)
}

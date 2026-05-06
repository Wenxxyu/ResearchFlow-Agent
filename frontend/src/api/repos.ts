import axios from 'axios'
import type { RepoImportResponse, RepoSearchResult, RepoTreeResponse } from '../types/api'
export type { RepoImportResponse, RepoSearchResult, RepoTreeResponse } from '../types/api'

export async function uploadRepoZip(projectId: number, file: File): Promise<RepoImportResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await axios.post<RepoImportResponse>(`/api/projects/${projectId}/repos/upload`, formData)
  return data
}

export async function importLocalRepo(projectId: number, localPath: string): Promise<RepoImportResponse> {
  const formData = new FormData()
  formData.append('local_path', localPath)
  const { data } = await axios.post<RepoImportResponse>(`/api/projects/${projectId}/repos/upload`, formData)
  return data
}

export async function getRepoTree(projectId: number): Promise<RepoTreeResponse> {
  const { data } = await axios.get<RepoTreeResponse>(`/api/projects/${projectId}/repos/tree`)
  return data
}

export async function searchRepo(projectId: number, query: string, topK = 10): Promise<RepoSearchResult[]> {
  const { data } = await axios.post<RepoSearchResult[]>(`/api/projects/${projectId}/repos/search`, {
    query,
    top_k: topK
  })
  return data
}

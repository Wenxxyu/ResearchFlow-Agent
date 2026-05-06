import axios from 'axios'
import type { BuildIndexResponse, RetrieveResponse } from '../types/api'
export type { BuildIndexResponse, RetrievalResult, RetrieveResponse } from '../types/api'

export async function buildProjectIndex(projectId: number): Promise<BuildIndexResponse> {
  const { data } = await axios.post<BuildIndexResponse>(`/api/projects/${projectId}/index/build`)
  return data
}

export async function retrieveProject(
  projectId: number,
  query: string,
  topK = 5,
  taskType = 'general_qa'
): Promise<RetrieveResponse> {
  const { data } = await axios.post<RetrieveResponse>(`/api/projects/${projectId}/retrieve`, {
    query,
    top_k: topK,
    task_type: taskType
  })
  return data
}

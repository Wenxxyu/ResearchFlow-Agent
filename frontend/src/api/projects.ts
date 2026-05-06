import axios from 'axios'
import type { Project } from '../types/api'
export type { Project } from '../types/api'

export async function listProjects(): Promise<Project[]> {
  const { data } = await axios.get<Project[]>('/api/projects')
  return data
}

export async function createProject(payload: { name: string; description?: string | null }): Promise<Project> {
  const { data } = await axios.post<Project>('/api/projects', payload)
  return data
}

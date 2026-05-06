import axios from 'axios'
import type { TaskRecord, TaskStepRecord } from '../types/api'

export type { TaskRecord, TaskStepRecord } from '../types/api'

export async function listProjectTasks(projectId: number): Promise<TaskRecord[]> {
  const { data } = await axios.get<TaskRecord[]>(`/api/projects/${projectId}/tasks`)
  return data
}

export async function getTask(taskId: number): Promise<TaskRecord> {
  const { data } = await axios.get<TaskRecord>(`/api/tasks/${taskId}`)
  return data
}

export async function listTaskSteps(taskId: number): Promise<TaskStepRecord[]> {
  const { data } = await axios.get<TaskStepRecord[]>(`/api/tasks/${taskId}/steps`)
  return data
}

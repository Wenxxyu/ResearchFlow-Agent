import axios from 'axios'
import type { SkillCandidate } from '../types/api'
export type { SkillCandidate } from '../types/api'

export async function createSkillCandidate(taskId: number, feedback = 'positive'): Promise<SkillCandidate> {
  const { data } = await axios.post<SkillCandidate>(`/api/tasks/${taskId}/skill-candidates`, { feedback })
  return data
}

export async function listSkillCandidates(projectId: number): Promise<SkillCandidate[]> {
  const { data } = await axios.get<SkillCandidate[]>(`/api/projects/${projectId}/skill-candidates`)
  return data
}

export async function approveSkillCandidate(candidateId: number): Promise<SkillCandidate> {
  const { data } = await axios.post<SkillCandidate>(`/api/skill-candidates/${candidateId}/approve`)
  return data
}

export async function rejectSkillCandidate(candidateId: number): Promise<SkillCandidate> {
  const { data } = await axios.post<SkillCandidate>(`/api/skill-candidates/${candidateId}/reject`)
  return data
}

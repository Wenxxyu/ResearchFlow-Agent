import axios from 'axios'
import type { SkillDetail, SkillRecord, SkillScanResponse } from '../types/api'
export type { SkillDetail, SkillRecord, SkillScanResponse } from '../types/api'

export async function listSkills(): Promise<SkillRecord[]> {
  const { data } = await axios.get<SkillRecord[]>('/api/skills')
  return data
}

export async function getSkill(skillId: number): Promise<SkillDetail> {
  const { data } = await axios.get<SkillDetail>(`/api/skills/${skillId}`)
  return data
}

export async function scanSkills(): Promise<SkillScanResponse> {
  const { data } = await axios.post<SkillScanResponse>('/api/skills/scan')
  return data
}

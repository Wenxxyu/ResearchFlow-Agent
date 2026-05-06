import axios from 'axios'
import type { AgentChatResponse } from '../types/api'
export type { AgentChatResponse, AgentStep, LogAnalysis } from '../types/api'

export async function sendAgentMessage(
  projectId: number,
  message: string,
  conversationId?: string
): Promise<AgentChatResponse> {
  const { data } = await axios.post<AgentChatResponse>(`/api/projects/${projectId}/agent/chat`, {
    message,
    conversation_id: conversationId,
  })
  return data
}

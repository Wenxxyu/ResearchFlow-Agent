import axios from 'axios'

export interface HealthResponse {
  status: string
  app_name: string
  version: string
}

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await axios.get<HealthResponse>('/api/health')
  return data
}

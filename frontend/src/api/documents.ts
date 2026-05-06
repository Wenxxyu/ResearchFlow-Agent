import axios from 'axios'
import type { ChunkRecord, DocumentRecord } from '../types/api'
export type { ChunkRecord, DocumentRecord } from '../types/api'

export async function listProjectDocuments(projectId: number): Promise<DocumentRecord[]> {
  const { data } = await axios.get<DocumentRecord[]>(`/api/projects/${projectId}/documents`)
  return data
}

export async function uploadProjectDocument(
  projectId: number,
  file: File,
  chunkSize = 800,
  chunkOverlap = 120
): Promise<DocumentRecord> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('chunk_size', String(chunkSize))
  formData.append('chunk_overlap', String(chunkOverlap))
  const { data } = await axios.post<DocumentRecord>(`/api/projects/${projectId}/documents/upload`, formData)
  return data
}

export async function deleteDocument(documentId: number): Promise<void> {
  await axios.delete(`/api/documents/${documentId}`)
}

export async function listDocumentChunks(documentId: number): Promise<ChunkRecord[]> {
  const { data } = await axios.get<ChunkRecord[]>(`/api/documents/${documentId}/chunks`)
  return data
}

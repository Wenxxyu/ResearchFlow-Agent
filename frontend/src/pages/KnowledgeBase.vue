<template>
  <section class="page-section">
    <div class="panel">
      <div class="panel-header split">
        <div>
          <span class="eyebrow">Knowledge Base</span>
          <h2>Knowledge Base</h2>
          <p>Create projects, upload documents, build indexes, and test retrieval.</p>
        </div>
        <div class="upload-actions">
          <el-tag v-if="activeProject" type="info">Project: {{ activeProject.name }}</el-tag>
          <el-button :loading="buildingIndex" @click="buildIndex">Build Index</el-button>
          <el-upload
            :show-file-list="false"
            :http-request="handleUpload"
            :before-upload="beforeUpload"
            accept=".pdf,.md,.markdown,.txt"
          >
            <el-button type="primary" :loading="uploading">Upload Document</el-button>
          </el-upload>
        </div>
      </div>

      <el-alert
        v-if="error"
        :title="error"
        type="error"
        show-icon
        :closable="false"
        class="kb-alert"
      />

      <div class="project-create-row">
        <el-input v-model="projectDraft.name" placeholder="New project name" clearable />
        <el-input v-model="projectDraft.description" placeholder="Description" clearable />
        <el-button :loading="creatingProject" @click="createNewProject">Create Project</el-button>
      </div>

      <el-table :data="documents" border v-loading="loading">
        <el-table-column prop="filename" label="Filename" min-width="220" />
        <el-table-column prop="file_type" label="Type" width="110" />
        <el-table-column prop="status" label="Status" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === 'indexed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="Chunks" width="110" />
        <el-table-column prop="created_at" label="Created" min-width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="Actions" width="210" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openChunks(row.id)">Chunks</el-button>
            <el-button size="small" type="danger" @click="removeDocument(row.id)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="panel retrieval-panel">
      <div class="panel-header split">
        <div>
          <span class="eyebrow">Hybrid Retrieval</span>
          <h2>Retrieval Test</h2>
          <p>BM25 keyword retrieval plus FAISS vector search with score fusion.</p>
        </div>
        <el-tag v-if="lastIndexBuild" type="success">
          {{ lastIndexBuild.chunk_count }} chunks indexed
        </el-tag>
      </div>

      <div class="retrieval-form">
        <el-input v-model="query" placeholder="Search uploaded documents" clearable @keyup.enter="runRetrieve" />
        <el-input-number v-model="topK" :min="1" :max="20" />
        <el-button type="primary" :loading="retrieving" @click="runRetrieve">Retrieve</el-button>
      </div>

      <div class="retrieval-results">
        <article v-for="result in retrievalResults" :key="result.chunk_id" class="retrieval-item">
          <div class="chunk-meta">
            <el-tag size="small">{{ result.filename }}</el-tag>
            <el-tag size="small" type="info">{{ result.source }}</el-tag>
            <span>chunk #{{ result.chunk_index }}</span>
            <span>score {{ result.score.toFixed(3) }}</span>
            <span>vector {{ result.score_breakdown.vector_normalized?.toFixed(3) ?? '0.000' }}</span>
            <span>bm25 {{ result.score_breakdown.bm25_normalized?.toFixed(3) ?? '0.000' }}</span>
          </div>
          <p>{{ result.content }}</p>
        </article>
        <el-empty v-if="hasSearched && !retrieving && retrievalResults.length === 0" description="No retrieval results" />
      </div>
    </div>

    <div class="panel retrieval-panel">
      <div class="panel-header split">
        <div>
          <span class="eyebrow">Code Repository</span>
          <h2>Repository Understanding</h2>
          <p>Upload a zip repository or import a local workspace path, then search files, content, and Python symbols.</p>
        </div>
        <el-upload :show-file-list="false" :http-request="handleRepoUpload" accept=".zip">
          <el-button :loading="repoLoading">Upload ZIP Repo</el-button>
        </el-upload>
      </div>

      <div class="retrieval-form repo-import-form">
        <el-input v-model="localRepoPath" placeholder="Local repo path inside workspace" clearable />
        <el-button :loading="repoLoading" @click="importRepoPath">Import Path</el-button>
        <el-button :loading="repoLoading" @click="refreshRepo">Refresh Tree</el-button>
      </div>

      <div v-if="repoInfo" class="repo-summary">
        <el-tag type="success">{{ repoInfo.files.length }} files</el-tag>
        <el-tag type="info">{{ repoInfo.symbols.length }} Python symbols</el-tag>
        <p>{{ repoInfo.readme_summary || 'No README summary found.' }}</p>
      </div>

      <div class="retrieval-form">
        <el-input v-model="repoQuery" placeholder="Search filename, content, or Python symbol" clearable @keyup.enter="runRepoSearch" />
        <el-input-number v-model="repoTopK" :min="1" :max="30" />
        <el-button type="primary" :loading="repoSearching" @click="runRepoSearch">Search Code</el-button>
      </div>

      <div class="retrieval-results">
        <article v-for="result in repoResults" :key="`${result.path}-${result.line_start}-${result.match_type}`" class="retrieval-item">
          <div class="chunk-meta">
            <el-tag size="small">{{ result.match_type }}</el-tag>
            <span>{{ result.path }}:{{ result.line_start }}</span>
            <span v-if="result.symbol_name">{{ result.symbol_name }}</span>
          </div>
          <pre>{{ result.snippet }}</pre>
        </article>
      </div>
    </div>

    <el-drawer v-model="chunkDrawerVisible" title="Document Chunks" size="46%">
      <div v-loading="chunksLoading" class="chunk-list">
        <article v-for="chunk in chunks" :key="chunk.id" class="chunk-item">
          <div class="chunk-meta">
            <el-tag size="small">#{{ chunk.chunk_index }}</el-tag>
            <span>{{ parseMetadata(chunk.metadata_json) }}</span>
          </div>
          <p>{{ chunk.content }}</p>
        </article>
        <el-empty v-if="!chunksLoading && chunks.length === 0" description="No chunks" />
      </div>
    </el-drawer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import type { UploadRequestOptions } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createProject } from '../api/projects'
import {
  deleteDocument,
  listDocumentChunks,
  listProjectDocuments,
  uploadProjectDocument,
  type ChunkRecord,
  type DocumentRecord
} from '../api/documents'
import {
  buildProjectIndex,
  retrieveProject,
  type BuildIndexResponse,
  type RetrievalResult
} from '../api/retrieval'
import {
  getRepoTree,
  importLocalRepo,
  searchRepo,
  uploadRepoZip,
  type RepoSearchResult,
  type RepoTreeResponse
} from '../api/repos'
import type { Project } from '../types/api'

const props = defineProps<{
  activeProject: Project | null
}>()
const emit = defineEmits<{
  refreshProjects: [preferredProjectId?: number]
}>()
const documents = ref<DocumentRecord[]>([])
const chunks = ref<ChunkRecord[]>([])
const loading = ref(false)
const uploading = ref(false)
const chunksLoading = ref(false)
const chunkDrawerVisible = ref(false)
const error = ref('')
const buildingIndex = ref(false)
const retrieving = ref(false)
const query = ref('')
const topK = ref(5)
const lastIndexBuild = ref<BuildIndexResponse | null>(null)
const retrievalResults = ref<RetrievalResult[]>([])
const hasSearched = ref(false)
const repoInfo = ref<RepoTreeResponse | null>(null)
const repoResults = ref<RepoSearchResult[]>([])
const repoLoading = ref(false)
const repoSearching = ref(false)
const localRepoPath = ref('')
const repoQuery = ref('')
const repoTopK = ref(10)
const creatingProject = ref(false)
const projectDraft = reactive({ name: '', description: '' })

const activeProject = computed(() => props.activeProject)

async function refreshDocuments() {
  if (!props.activeProject) return
  loading.value = true
  error.value = ''
  try {
    documents.value = await listProjectDocuments(props.activeProject.id)
  } catch {
    ElMessage.error('Failed to load documents.')
  } finally {
    loading.value = false
  }
}

async function createNewProject() {
  if (!projectDraft.name.trim()) {
    ElMessage.warning('Project name is required.')
    return
  }
  creatingProject.value = true
  try {
    const created = await createProject({
      name: projectDraft.name.trim(),
      description: projectDraft.description.trim() || null
    })
    projectDraft.name = ''
    projectDraft.description = ''
    emit('refreshProjects', created.id)
    ElMessage.success('Project created.')
  } catch {
    ElMessage.error('Failed to create project.')
  } finally {
    creatingProject.value = false
  }
}

function beforeUpload(file: File) {
  const filename = file.name.toLowerCase()
  const allowed = ['.pdf', '.md', '.markdown', '.txt'].some((suffix) => filename.endsWith(suffix))
  if (!allowed) {
    ElMessage.error('Only PDF, Markdown, and TXT files are supported.')
  }
  return allowed
}

async function handleUpload(options: UploadRequestOptions) {
  if (!props.activeProject) return
  uploading.value = true
  error.value = ''
  try {
    await uploadProjectDocument(props.activeProject.id, options.file)
    ElMessage.success('Document uploaded and indexed.')
    await refreshDocuments()
  } catch {
    ElMessage.error('Upload failed. Check backend logs for parser details.')
  } finally {
    uploading.value = false
  }
}

async function buildIndex() {
  if (!props.activeProject) return
  buildingIndex.value = true
  error.value = ''
  try {
    lastIndexBuild.value = await buildProjectIndex(props.activeProject.id)
    ElMessage.success(`Index built for ${lastIndexBuild.value.chunk_count} chunks.`)
  } catch {
    ElMessage.error('Failed to build retrieval index.')
  } finally {
    buildingIndex.value = false
  }
}

async function runRetrieve() {
  if (!props.activeProject || !query.value.trim()) return
  retrieving.value = true
  hasSearched.value = true
  error.value = ''
  try {
    const response = await retrieveProject(props.activeProject.id, query.value.trim(), topK.value)
    retrievalResults.value = response.results
  } catch {
    ElMessage.error('Retrieval failed. Build the index first, then retry.')
    retrievalResults.value = []
  } finally {
    retrieving.value = false
  }
}

async function handleRepoUpload(options: UploadRequestOptions) {
  if (!props.activeProject) return
  repoLoading.value = true
  error.value = ''
  try {
    await uploadRepoZip(props.activeProject.id, options.file)
    ElMessage.success('Repository imported.')
    await refreshRepo()
  } catch {
    ElMessage.error('Repository upload failed.')
  } finally {
    repoLoading.value = false
  }
}

async function importRepoPath() {
  if (!props.activeProject || !localRepoPath.value.trim()) return
  repoLoading.value = true
  error.value = ''
  try {
    await importLocalRepo(props.activeProject.id, localRepoPath.value.trim())
    ElMessage.success('Repository imported from local path.')
    await refreshRepo()
  } catch {
    ElMessage.error('Local repository import failed. The path must be inside the current workspace.')
  } finally {
    repoLoading.value = false
  }
}

async function refreshRepo() {
  if (!props.activeProject) return
  repoLoading.value = true
  try {
    repoInfo.value = await getRepoTree(props.activeProject.id)
  } catch {
    repoInfo.value = null
  } finally {
    repoLoading.value = false
  }
}

async function runRepoSearch() {
  if (!props.activeProject || !repoQuery.value.trim()) return
  repoSearching.value = true
  try {
    repoResults.value = await searchRepo(props.activeProject.id, repoQuery.value.trim(), repoTopK.value)
  } finally {
    repoSearching.value = false
  }
}

async function removeDocument(documentId: number) {
  await ElMessageBox.confirm('Delete this document and all chunks?', 'Delete Document', {
    type: 'warning'
  })
  await deleteDocument(documentId)
  ElMessage.success('Document deleted.')
  await refreshDocuments()
}

async function openChunks(documentId: number) {
  chunkDrawerVisible.value = true
  chunksLoading.value = true
  chunks.value = []
  try {
    chunks.value = await listDocumentChunks(documentId)
  } finally {
    chunksLoading.value = false
  }
}

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

function parseMetadata(raw: string | null) {
  if (!raw) return ''
  try {
    const metadata = JSON.parse(raw) as { page_number?: number | null; filename?: string }
    return metadata.page_number ? `${metadata.filename ?? ''} page ${metadata.page_number}` : metadata.filename ?? ''
  } catch {
    return ''
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await refreshDocuments()
  } catch {
    ElMessage.error('Failed to initialize knowledge base.')
  } finally {
    loading.value = false
  }
})

watch(
  () => props.activeProject?.id,
  async () => {
    documents.value = []
    retrievalResults.value = []
    repoInfo.value = null
    repoResults.value = []
    await refreshDocuments()
    await refreshRepo()
  }
)
</script>

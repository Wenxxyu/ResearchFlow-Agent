<template>
  <section class="page-section">
    <div class="panel">
      <div class="panel-header split">
        <div>
          <span class="eyebrow">Memory Center</span>
          <h2>Memory Center</h2>
          <p>Inspect, filter, search, and delete project memories. Delete is hard delete in this MVP.</p>
        </div>
        <div class="upload-actions">
          <el-tag v-if="activeProject" type="info">Project: {{ activeProject.name }}</el-tag>
          <el-button type="primary" @click="createDialogVisible = true">New Memory</el-button>
        </div>
      </div>

      <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="kb-alert" />

      <div class="retrieval-form memory-search-form">
        <el-input v-model="query" placeholder="Search memories" clearable @keyup.enter="runSearch" />
        <el-select v-model="selectedType" clearable placeholder="All types">
          <el-option v-for="type in memoryTypes" :key="type" :label="type" :value="type" />
        </el-select>
        <el-input-number v-model="minConfidence" :min="0" :max="1" :step="0.05" />
        <el-button :loading="searching" @click="runSearch">Search</el-button>
      </div>

      <el-tabs v-model="activeType" @tab-change="refreshMemories">
        <el-tab-pane label="All" name="" />
        <el-tab-pane v-for="type in memoryTypes" :key="type" :label="type" :name="type" />
      </el-tabs>

      <el-table :data="displayedMemories" border v-loading="loading">
        <el-table-column prop="memory_type" label="Type" width="130" />
        <el-table-column label="Summary" min-width="220">
          <template #default="{ row }">
            <strong>{{ row.summary || '(no summary)' }}</strong>
            <p class="table-subtext">{{ row.content }}</p>
          </template>
        </el-table-column>
        <el-table-column prop="importance" label="Importance" width="120">
          <template #default="{ row }">{{ row.importance.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="confidence" label="Confidence" width="120">
          <template #default="{ row }">
            <el-tag :type="row.confidence >= 0.7 ? 'success' : row.confidence >= 0.4 ? 'warning' : 'danger'">
              {{ row.confidence.toFixed(2) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Score" width="100">
          <template #default="{ row }">{{ scoreByMemoryId[row.id]?.toFixed(3) ?? '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="Created" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="Actions" width="110">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="removeMemory(row.id)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="createDialogVisible" title="New Memory" width="560px">
      <el-form label-position="top">
        <el-form-item label="Type">
          <el-select v-model="draft.memory_type">
            <el-option v-for="type in memoryTypes" :key="type" :label="type" :value="type" />
          </el-select>
        </el-form-item>
        <el-form-item label="Summary">
          <el-input v-model="draft.summary" />
        </el-form-item>
        <el-form-item label="Content">
          <el-input v-model="draft.content" type="textarea" :rows="5" />
        </el-form-item>
        <el-form-item label="Importance">
          <el-slider v-model="draft.importance" :min="0" :max="1" :step="0.05" />
        </el-form-item>
        <el-form-item label="Confidence">
          <el-slider v-model="draft.confidence" :min="0" :max="1" :step="0.05" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="saveMemory">Save</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createMemory,
  deleteMemory,
  listMemories,
  searchMemories,
  type MemoryRecord
} from '../api/memories'
import type { Project } from '../types/api'

const memoryTypes = ['working', 'episodic', 'semantic', 'user_profile', 'reflection', 'skill']
const props = defineProps<{
  activeProject: Project | null
}>()
const activeProject = computed(() => props.activeProject)
const memories = ref<MemoryRecord[]>([])
const searchResults = ref<MemoryRecord[]>([])
const scoreByMemoryId = ref<Record<number, number>>({})
const activeType = ref('')
const selectedType = ref('')
const query = ref('')
const minConfidence = ref(0.35)
const loading = ref(false)
const searching = ref(false)
const error = ref('')
const createDialogVisible = ref(false)

const draft = reactive({
  memory_type: 'semantic',
  summary: '',
  content: '',
  importance: 0.5,
  confidence: 0.75
})

const displayedMemories = computed(() => (searchResults.value.length > 0 ? searchResults.value : memories.value))

async function refreshMemories() {
  if (!props.activeProject) return
  loading.value = true
  error.value = ''
  scoreByMemoryId.value = {}
  searchResults.value = []
  try {
    memories.value = await listMemories(props.activeProject.id, activeType.value || undefined)
  } catch {
    ElMessage.error('Failed to load memories.')
  } finally {
    loading.value = false
  }
}

async function runSearch() {
  if (!props.activeProject || !query.value.trim()) return
  searching.value = true
  error.value = ''
  try {
    const results = await searchMemories(props.activeProject.id, {
      query: query.value.trim(),
      top_k: 10,
      memory_type: selectedType.value || null,
      min_confidence: minConfidence.value
    })
    searchResults.value = results.map((result) => result.memory)
    scoreByMemoryId.value = Object.fromEntries(results.map((result) => [result.memory.id, result.score]))
  } catch {
    ElMessage.error('Failed to search memories.')
  } finally {
    searching.value = false
  }
}

async function saveMemory() {
  if (!props.activeProject || !draft.content.trim()) return
  await createMemory(props.activeProject.id, {
    memory_type: draft.memory_type,
    content: draft.content,
    summary: draft.summary || null,
    importance: draft.importance,
    confidence: draft.confidence,
    tags: []
  })
  createDialogVisible.value = false
  draft.summary = ''
  draft.content = ''
  ElMessage.success('Memory saved.')
  await refreshMemories()
}

async function removeMemory(memoryId: number) {
  await ElMessageBox.confirm('Hard delete this memory?', 'Delete Memory', { type: 'warning' })
  await deleteMemory(memoryId)
  ElMessage.success('Memory deleted.')
  await refreshMemories()
}

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

onMounted(async () => {
  await refreshMemories()
})

watch(
  () => props.activeProject?.id,
  async () => {
    memories.value = []
    searchResults.value = []
    await refreshMemories()
  }
)
</script>

<template>
  <section class="page-section">
    <div class="panel">
      <div class="panel-header split">
        <div>
          <span class="eyebrow">Trace Viewer</span>
          <h2>Execution Trace</h2>
          <p>Load a task by id and inspect stored Agent node inputs, outputs, and latency.</p>
        </div>
        <el-tag v-if="activeProject" type="info">Project: {{ activeProject.name }}</el-tag>
      </div>

      <div class="trace-toolbar">
        <el-select v-model="selectedTaskId" :loading="loadingTasks" placeholder="Recent project tasks" filterable clearable>
          <el-option
            v-for="task in tasks"
            :key="task.id"
            :label="`#${task.id} ${task.task_type} ${task.status}`"
            :value="task.id"
          />
        </el-select>
        <el-input-number v-model="manualTaskId" :min="1" placeholder="Task ID" />
        <el-button :loading="loadingSteps" type="primary" @click="loadSelectedTrace">Load Trace</el-button>
        <el-button :loading="loadingTasks" @click="refreshTasks">Refresh Tasks</el-button>
      </div>

      <el-descriptions v-if="task" :column="4" border class="trace-task-meta">
        <el-descriptions-item label="Task ID">#{{ task.id }}</el-descriptions-item>
        <el-descriptions-item label="Type">{{ task.task_type }}</el-descriptions-item>
        <el-descriptions-item label="Status">{{ task.status }}</el-descriptions-item>
        <el-descriptions-item label="Created">{{ formatDate(task.created_at) }}</el-descriptions-item>
      </el-descriptions>

      <el-table :data="steps" border v-loading="loadingSteps" class="trace-table">
        <el-table-column prop="node_name" label="Node" width="190" />
        <el-table-column prop="latency_ms" label="Latency" width="110">
          <template #default="{ row }">{{ row.latency_ms ?? 0 }}ms</template>
        </el-table-column>
        <el-table-column label="Input JSON" min-width="300">
          <template #default="{ row }">
            <pre>{{ formatJson(row.input_json) }}</pre>
          </template>
        </el-table-column>
        <el-table-column label="Output JSON" min-width="360">
          <template #default="{ row }">
            <pre>{{ formatJson(row.output_json) }}</pre>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loadingSteps && steps.length === 0" description="No trace loaded" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getTask, listProjectTasks, listTaskSteps, type TaskRecord, type TaskStepRecord } from '../api/tasks'
import type { Project } from '../types/api'

const props = defineProps<{
  activeProject: Project | null
}>()

const tasks = ref<TaskRecord[]>([])
const task = ref<TaskRecord | null>(null)
const steps = ref<TaskStepRecord[]>([])
const selectedTaskId = ref<number | null>(null)
const manualTaskId = ref<number | undefined>()
const loadingTasks = ref(false)
const loadingSteps = ref(false)

async function refreshTasks() {
  if (!props.activeProject) return
  loadingTasks.value = true
  try {
    tasks.value = await listProjectTasks(props.activeProject.id)
    if (!selectedTaskId.value && tasks.value.length > 0) {
      selectedTaskId.value = tasks.value[0].id
    }
  } catch {
    ElMessage.error('Failed to load tasks.')
  } finally {
    loadingTasks.value = false
  }
}

async function loadSelectedTrace() {
  const taskId = manualTaskId.value ?? selectedTaskId.value
  if (!taskId) {
    ElMessage.warning('Select or enter a task id first.')
    return
  }
  loadingSteps.value = true
  try {
    const [taskRecord, taskSteps] = await Promise.all([getTask(taskId), listTaskSteps(taskId)])
    task.value = taskRecord
    steps.value = taskSteps
  } catch {
    ElMessage.error('Failed to load task trace.')
    steps.value = []
    task.value = null
  } finally {
    loadingSteps.value = false
  }
}

function formatJson(raw: string | null) {
  if (!raw) return ''
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}

onMounted(refreshTasks)

watch(
  () => props.activeProject?.id,
  async () => {
    tasks.value = []
    task.value = null
    steps.value = []
    selectedTaskId.value = null
    manualTaskId.value = undefined
    await refreshTasks()
  }
)
</script>

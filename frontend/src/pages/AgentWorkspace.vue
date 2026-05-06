<template>
  <section class="page-section workspace-grid">
    <div class="panel conversation-panel">
      <div class="panel-header split">
        <div>
          <span class="eyebrow">Agent Workspace</span>
          <h2>Agent Workspace</h2>
          <p>Ask about papers, repositories, memories, skills, or paste experiment tracebacks.</p>
        </div>
        <div v-if="activeProject" class="header-actions">
          <el-tag type="info">Project: {{ activeProject.name }}</el-tag>
          <el-tag v-if="conversationId" type="warning">Session: {{ shortConversationId }}</el-tag>
          <el-button size="small" @click="startNewConversation">New Conversation</el-button>
        </div>
      </div>

      <div class="chat-placeholder" v-loading="loading">
        <p v-if="!response" class="assistant-line">
          Select a project, upload knowledge or a repository if needed, then send a task to the Agent.
        </p>

        <article v-if="response" class="answer-block">
          <div class="chunk-meta">
            <el-tag type="success">task #{{ response.task_id }}</el-tag>
            <el-tag v-if="response.conversation_id" type="warning">session memory on</el-tag>
            <el-tag type="info">{{ response.task_type }}</el-tag>
            <el-button size="small" :loading="miningSkill" @click="mineSkill">Save as Candidate Skill</el-button>
          </div>

          <div v-if="response.task_type === 'log_debug' && response.log_analysis" class="log-debug-result">
            <section>
              <h3>Error Summary</h3>
              <p>{{ response.log_analysis.summary }}</p>
            </section>
            <section>
              <h3>Possible Causes</h3>
              <ul>
                <li v-for="item in response.log_analysis.possible_causes" :key="item">{{ item }}</li>
              </ul>
            </section>
            <section>
              <h3>Troubleshooting Steps</h3>
              <ol>
                <li v-for="item in response.log_analysis.troubleshooting_steps" :key="item">{{ item }}</li>
              </ol>
            </section>
            <section>
              <h3>Fix Suggestions</h3>
              <ul>
                <li v-for="item in response.log_analysis.fix_suggestions" :key="item">{{ item }}</li>
              </ul>
            </section>
            <section>
              <h3>Need More Info</h3>
              <ul>
                <li v-for="item in response.log_analysis.need_more_info" :key="item">{{ item }}</li>
              </ul>
            </section>
          </div>
          <p v-else>{{ response.answer }}</p>
        </article>

        <div v-if="response?.citations.length" class="citation-list">
          <h3>Citations</h3>
          <el-tag v-for="citation in response.citations" :key="citation" type="info">
            {{ citation }}
          </el-tag>
        </div>
      </div>

      <div class="composer">
        <el-input
          v-model="message"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 8 }"
          placeholder="Ask a question or paste an experiment traceback"
          @keydown.enter.exact.prevent="sendMessage"
        />
        <el-button type="primary" :loading="loading" @click="sendMessage">Send</el-button>
      </div>
    </div>

    <div class="panel trace-summary">
      <div class="panel-header">
        <span class="eyebrow">Runtime Trace</span>
        <h2>Execution Steps</h2>
      </div>
      <el-timeline>
        <el-timeline-item
          v-for="step in response?.steps ?? []"
          :key="`${step.node_name}-${step.latency_ms}`"
          :timestamp="`${step.node_name} - ${step.latency_ms}ms`"
          type="primary"
        >
          <pre>{{ formatStep(step.output) }}</pre>
        </el-timeline-item>
        <el-timeline-item v-if="!response" timestamp="Idle">Waiting for a question</el-timeline-item>
      </el-timeline>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { sendAgentMessage, type AgentChatResponse, type AgentStep } from '../api/agent'
import { createSkillCandidate } from '../api/skillCandidates'
import type { Project } from '../types/api'

const props = defineProps<{
  activeProject: Project | null
}>()

const message = ref('')
const response = ref<AgentChatResponse | null>(null)
const loading = ref(false)
const miningSkill = ref(false)
const conversationId = ref('')

const shortConversationId = computed(() => {
  if (!conversationId.value) return ''
  return conversationId.value.length > 18 ? `${conversationId.value.slice(0, 18)}...` : conversationId.value
})

async function sendMessage() {
  if (!props.activeProject || !message.value.trim()) {
    ElMessage.warning('Select a project and enter a question first.')
    return
  }
  ensureConversationId()
  loading.value = true
  try {
    response.value = await sendAgentMessage(props.activeProject.id, message.value.trim(), conversationId.value)
    if (response.value.errors.length) {
      ElMessage.warning(response.value.errors[0])
    }
  } catch {
    ElMessage.error('Agent request failed.')
  } finally {
    loading.value = false
  }
}

function createConversationId() {
  return `conv-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function conversationStorageKey(projectId: number) {
  return `researchflow.conversation.${projectId}`
}

function ensureConversationId() {
  if (!props.activeProject) return
  const key = conversationStorageKey(props.activeProject.id)
  const stored = localStorage.getItem(key)
  conversationId.value = stored || conversationId.value || createConversationId()
  localStorage.setItem(key, conversationId.value)
}

function startNewConversation() {
  if (!props.activeProject) return
  conversationId.value = createConversationId()
  localStorage.setItem(conversationStorageKey(props.activeProject.id), conversationId.value)
  response.value = null
  ElMessage.success('Started a new conversation session.')
}

async function mineSkill() {
  if (!response.value) return
  miningSkill.value = true
  try {
    const candidate = await createSkillCandidate(response.value.task_id, 'positive')
    ElMessage.success(`Candidate skill created: ${candidate.name}`)
  } catch {
    ElMessage.warning('This task is not eligible for candidate skill generation.')
  } finally {
    miningSkill.value = false
  }
}

function formatStep(output: AgentStep['output']) {
  return JSON.stringify(output, null, 2)
}

watch(
  () => props.activeProject?.id,
  (projectId) => {
    response.value = null
    if (!projectId) {
      conversationId.value = ''
      return
    }
    const key = conversationStorageKey(projectId)
    conversationId.value = localStorage.getItem(key) || createConversationId()
    localStorage.setItem(key, conversationId.value)
  },
  { immediate: true }
)
</script>

<style scoped>
.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  align-items: center;
}
</style>

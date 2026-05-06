<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Files, Monitor, Notebook, Operation, Setting, Timer } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getHealth, type HealthResponse } from './api/health'
import { createProject, listProjects } from './api/projects'
import AgentWorkspace from './pages/AgentWorkspace.vue'
import KnowledgeBase from './pages/KnowledgeBase.vue'
import MemoryCenter from './pages/MemoryCenter.vue'
import SkillRegistry from './pages/SkillRegistry.vue'
import TraceViewer from './pages/TraceViewer.vue'
import type { Project } from './types/api'

type PageKey = 'workspace' | 'knowledge' | 'memory' | 'skills' | 'trace'

const activePage = ref<PageKey>('workspace')
const health = ref<HealthResponse | null>(null)
const healthLoading = ref(false)
const projectsLoading = ref(false)
const projects = ref<Project[]>([])
const activeProjectId = ref<number | null>(null)
const createProjectVisible = ref(false)
const projectDraft = ref({ name: '', description: '' })

const navItems = [
  { key: 'workspace', label: 'Agent Workspace', icon: Monitor },
  { key: 'knowledge', label: 'Knowledge Base', icon: Files },
  { key: 'memory', label: 'Memory Center', icon: Notebook },
  { key: 'skills', label: 'Skill Registry', icon: Setting },
  { key: 'trace', label: 'Trace Viewer', icon: Operation }
] as const

const activeComponent = computed(() => {
  const pages = {
    workspace: AgentWorkspace,
    knowledge: KnowledgeBase,
    memory: MemoryCenter,
    skills: SkillRegistry,
    trace: TraceViewer
  }
  return pages[activePage.value]
})

const activeProject = computed(() => projects.value.find((project) => project.id === activeProjectId.value) ?? null)

async function refreshHealth() {
  healthLoading.value = true
  try {
    health.value = await getHealth()
  } catch {
    health.value = null
    ElMessage.error('Backend is not reachable.')
  } finally {
    healthLoading.value = false
  }
}

async function refreshProjects(preferredProjectId?: number) {
  projectsLoading.value = true
  try {
    projects.value = await listProjects()
    if (projects.value.length === 0) {
      const created = await createProject({
        name: 'default-project',
        description: 'Default ResearchFlow-Agent project'
      })
      projects.value = [created]
    }
    const nextId = preferredProjectId ?? activeProjectId.value
    activeProjectId.value = projects.value.some((project) => project.id === nextId) ? nextId : projects.value[0].id
  } catch {
    ElMessage.error('Failed to load projects.')
  } finally {
    projectsLoading.value = false
  }
}

async function saveProject() {
  if (!projectDraft.value.name.trim()) {
    ElMessage.warning('Project name is required.')
    return
  }
  try {
    const created = await createProject({
      name: projectDraft.value.name.trim(),
      description: projectDraft.value.description.trim() || null
    })
    createProjectVisible.value = false
    projectDraft.value = { name: '', description: '' }
    await refreshProjects(created.id)
    ElMessage.success('Project created.')
  } catch {
    ElMessage.error('Failed to create project. The name may already exist.')
  }
}

function selectPage(index: string) {
  activePage.value = index as PageKey
}

onMounted(async () => {
  await Promise.all([refreshHealth(), refreshProjects()])
})
</script>

<template>
  <el-container class="app-shell">
    <el-aside width="244px" class="sidebar">
      <div class="brand">
        <div class="brand-mark">RF</div>
        <div>
          <h1>ResearchFlow</h1>
          <p>Agent Console</p>
        </div>
      </div>

      <el-menu :default-active="activePage" class="nav-menu" @select="selectPage">
        <el-menu-item v-for="item in navItems" :key="item.key" :index="item.key">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div class="topbar-title">
          <h2>ResearchFlow-Agent</h2>
          <p>Research papers, repositories, experiment logs, memory, skills, and traces.</p>
        </div>
        <div class="topbar-actions">
          <el-select
            v-model="activeProjectId"
            :loading="projectsLoading"
            placeholder="Select project"
            class="project-select"
            filterable
          >
            <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
          </el-select>
          <el-button @click="createProjectVisible = true">New Project</el-button>
          <el-tag :type="health ? 'success' : 'danger'" size="large">
            {{ health ? `${health.app_name} v${health.version}` : 'Backend offline' }}
          </el-tag>
          <el-button :loading="healthLoading" :icon="Timer" @click="refreshHealth">Refresh</el-button>
        </div>
      </el-header>

      <el-main class="content">
        <component
          :is="activeComponent"
          :active-project="activeProject"
          @refresh-projects="refreshProjects"
        />
      </el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="createProjectVisible" title="Create Project" width="520px">
    <el-form label-position="top">
      <el-form-item label="Name">
        <el-input v-model="projectDraft.name" placeholder="paper-reading-demo" />
      </el-form-item>
      <el-form-item label="Description">
        <el-input v-model="projectDraft.description" type="textarea" :rows="3" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createProjectVisible = false">Cancel</el-button>
      <el-button type="primary" @click="saveProject">Create</el-button>
    </template>
  </el-dialog>
</template>

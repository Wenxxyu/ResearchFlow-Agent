<template>
  <section class="page-section">
    <div class="panel">
      <div class="panel-header split">
        <div>
          <span class="eyebrow">Skill Registry</span>
          <h2>Skill Registry</h2>
          <p>Scan SKILL.md packages and inject relevant skills into Agent context. Scripts are not executed.</p>
        </div>
        <el-button type="primary" :loading="loading" @click="runScan">Scan skills/</el-button>
      </div>

      <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="kb-alert" />

      <el-table :data="skills" border v-loading="loading" @row-click="openSkill">
        <el-table-column prop="name" label="Skill" min-width="180" />
        <el-table-column prop="description" label="Description" min-width="300" />
        <el-table-column prop="trigger" label="Trigger" min-width="240" />
        <el-table-column prop="status" label="Status" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="usage_count" label="Uses" width="90" />
        <el-table-column label="Success" width="110">
          <template #default="{ row }">{{ successRate(row) }}</template>
        </el-table-column>
      </el-table>
    </div>

    <div class="panel retrieval-panel">
      <div class="panel-header split">
        <div>
          <span class="eyebrow">Candidate Skills</span>
          <h2>Review Queue</h2>
          <p>Candidate skills are inactive until manually approved.</p>
        </div>
        <el-button :loading="loadingCandidates" @click="refreshCandidates">Refresh Candidates</el-button>
      </div>
      <el-table :data="candidates" border v-loading="loadingCandidates">
        <el-table-column prop="name" label="Candidate" min-width="180" />
        <el-table-column prop="description" label="Description" min-width="280" />
        <el-table-column prop="source_task_id" label="Task" width="90" />
        <el-table-column prop="status" label="Status" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === 'approved' ? 'success' : row.status === 'rejected' ? 'danger' : 'warning'">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="240">
          <template #default="{ row }">
            <el-button size="small" @click="openCandidate(row)">View</el-button>
            <el-button size="small" type="success" :disabled="row.status !== 'candidate'" @click="approveCandidate(row.id)">
              Approve
            </el-button>
            <el-button size="small" type="danger" :disabled="row.status !== 'candidate'" @click="rejectCandidate(row.id)">
              Reject
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-drawer v-model="drawerVisible" title="SKILL.md" size="48%">
      <div v-if="selectedSkill" class="skill-detail">
        <h3>{{ selectedSkill.name }}</h3>
        <p>{{ selectedSkill.description }}</p>
        <div class="skill-tools">
          <el-tag v-for="tool in selectedSkill.tools" :key="tool" type="info">{{ tool }}</el-tag>
        </div>
        <pre>{{ selectedSkill.content }}</pre>
      </div>
    </el-drawer>

    <el-drawer v-model="candidateDrawerVisible" title="Candidate SKILL.md" size="48%">
      <div v-if="selectedCandidate" class="skill-detail">
        <h3>{{ selectedCandidate.name }}</h3>
        <p>{{ selectedCandidate.description }}</p>
        <el-tag :type="selectedCandidate.status === 'candidate' ? 'warning' : 'info'">
          {{ selectedCandidate.status }}
        </el-tag>
        <pre>{{ selectedCandidate.content }}</pre>
      </div>
    </el-drawer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  approveSkillCandidate,
  listSkillCandidates,
  rejectSkillCandidate,
  type SkillCandidate
} from '../api/skillCandidates'
import { getSkill, listSkills, scanSkills, type SkillDetail, type SkillRecord } from '../api/skills'
import type { Project } from '../types/api'

const skills = ref<SkillRecord[]>([])
const candidates = ref<SkillCandidate[]>([])
const selectedSkill = ref<SkillDetail | null>(null)
const selectedCandidate = ref<SkillCandidate | null>(null)
const props = defineProps<{
  activeProject: Project | null
}>()
const activeProject = computed(() => props.activeProject)
const drawerVisible = ref(false)
const candidateDrawerVisible = ref(false)
const loading = ref(false)
const loadingCandidates = ref(false)
const error = ref('')

async function refreshSkills() {
  loading.value = true
  error.value = ''
  try {
    skills.value = await listSkills()
  } catch {
    ElMessage.error('Failed to load skills.')
  } finally {
    loading.value = false
  }
}

async function runScan() {
  loading.value = true
  error.value = ''
  try {
    const response = await scanSkills()
    skills.value = response.skills
    ElMessage.success(`Scanned ${response.scanned_count} skills.`)
  } catch {
    ElMessage.error('Failed to scan skills.')
  } finally {
    loading.value = false
  }
}

async function refreshCandidates() {
  if (!props.activeProject) return
  loadingCandidates.value = true
  try {
    candidates.value = await listSkillCandidates(props.activeProject.id)
  } catch {
    ElMessage.error('Failed to load candidate skills.')
  } finally {
    loadingCandidates.value = false
  }
}

async function openSkill(row: SkillRecord) {
  selectedSkill.value = await getSkill(row.id)
  drawerVisible.value = true
}

function successRate(skill: SkillRecord) {
  if (skill.usage_count === 0) return '-'
  return `${Math.round((skill.success_count / skill.usage_count) * 100)}%`
}

function openCandidate(row: SkillCandidate) {
  selectedCandidate.value = row
  candidateDrawerVisible.value = true
}

async function approveCandidate(candidateId: number) {
  await approveSkillCandidate(candidateId)
  ElMessage.success('Candidate approved and registered.')
  await refreshCandidates()
  await refreshSkills()
}

async function rejectCandidate(candidateId: number) {
  await rejectSkillCandidate(candidateId)
  ElMessage.success('Candidate rejected.')
  await refreshCandidates()
}

onMounted(async () => {
  await refreshSkills()
  await refreshCandidates()
})

watch(
  () => props.activeProject?.id,
  async () => {
    candidates.value = []
    await refreshCandidates()
  }
)
</script>

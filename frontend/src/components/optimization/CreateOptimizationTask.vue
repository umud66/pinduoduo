<script setup>
import { computed, ref, watch } from 'vue'
import { createTaskFromDiagnosis } from '@/api/optimization.js'

const props = defineProps({ diagnosis: { type: Object, default: null } })
const emit = defineEmits(['created'])
const issueCode = ref('')
const actionIndex = ref(0)
const saving = ref(false)

const issues = computed(() => Array.isArray(props.diagnosis?.issues) ? props.diagnosis.issues : [])
const selectedIssue = computed(() => issues.value.find((item) => item.code === issueCode.value) || issues.value[0] || null)
const actions = computed(() => Array.isArray(selectedIssue.value?.actions) ? selectedIssue.value.actions : [])

watch(issues, (items) => {
  if (!items.length) return
  if (!items.some((item) => item.code === issueCode.value)) issueCode.value = items[0].code
  actionIndex.value = 0
}, { immediate: true })
watch(issueCode, () => { actionIndex.value = 0 })

async function createTask() {
  const diagnosisId = props.diagnosis?.id || props.diagnosis?.diagnosis_id
  if (!diagnosisId || !selectedIssue.value || !actions.value.length) return
  saving.value = true
  try {
    const task = await createTaskFromDiagnosis(diagnosisId, {
      issue_code: selectedIssue.value.code,
      action_index: Number(actionIndex.value || 0),
    })
    window.dispatchEvent(new CustomEvent('pdd:toast', { detail: { message: '已创建优化任务', type: 'success' } }))
    window.dispatchEvent(new CustomEvent('pdd:optimization-updated'))
    emit('created', task)
  } catch (error) {
    window.dispatchEvent(new CustomEvent('pdd:toast', { detail: { message: error.message, type: 'error' } }))
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <article v-if="issues.length" class="optimization-create card compact">
    <div class="card-heading">
      <div><p class="section-kicker">ACTION LOOP</p><h3>把建议变成优化任务</h3></div>
      <RouterLink class="button ghost" to="/tasks">任务中心</RouterLink>
    </div>
    <p class="helper-text">选择一个确定性诊断问题和动作。开始执行后系统会冻结前 7 日基线，并在 3/7/14 天窗口复盘。</p>
    <div class="optimization-create-grid">
      <label class="field">诊断问题
        <select v-model="issueCode">
          <option v-for="issue in issues" :key="issue.code" :value="issue.code">{{ issue.title }} · 优先级 {{ issue.priority_score }}</option>
        </select>
      </label>
      <label class="field">计划动作
        <select v-model.number="actionIndex">
          <option v-for="(action, index) in actions" :key="`${selectedIssue?.code}-${index}`" :value="index">{{ action }}</option>
        </select>
      </label>
    </div>
    <div v-if="selectedIssue?.validation_metrics?.length" class="field-tags">
      <span class="field-tag" v-for="metric in selectedIssue.validation_metrics" :key="metric">复盘：{{ metric }}</span>
    </div>
    <div class="card-actions"><button class="button primary" :disabled="saving || !actions.length" @click="createTask">{{ saving ? '创建中…' : '创建优化任务' }}</button></div>
  </article>
</template>

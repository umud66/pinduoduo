<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAppStore } from '@/stores/app.js'
import {
  cancelOptimizationTask,
  completeOptimizationTask,
  listOptimizationTasks,
  refreshOptimizationTask,
  refreshShopOptimizationReviews,
  startOptimizationTask,
} from '@/api/optimization.js'
import TaskCard from '@/components/optimization/TaskCard.vue'

const app = useAppStore()
const items = ref([])
const status = ref('all')
const loading = ref(false)
const refreshing = ref(false)
const counts = computed(() => ({
  total: items.value.length,
  planned: items.value.filter((item) => item.status === 'planned').length,
  in_progress: items.value.filter((item) => item.status === 'in_progress').length,
  completed: items.value.filter((item) => item.status === 'completed').length,
  improved: items.value.filter((item) => item.latest_outcome === 'improved').length,
}))

function toast(message, type = '') { window.dispatchEvent(new CustomEvent('pdd:toast', { detail: { message, type } })) }
async function load() {
  if (!app.selectedShopId) { items.value = []; return }
  loading.value = true
  try { items.value = (await listOptimizationTasks(app.selectedShopId, status.value)).items || [] }
  catch (error) { toast(error.message, 'error') }
  finally { loading.value = false }
}
async function refreshAll({ quiet = false } = {}) {
  if (!app.selectedShopId) return
  refreshing.value = true
  try {
    const result = await refreshShopOptimizationReviews(app.selectedShopId)
    await load()
    if (!quiet) toast(`已刷新 ${result.tasks_refreshed || 0} 个任务的复盘状态`, 'success')
  } catch (error) { if (!quiet) toast(error.message, 'error') }
  finally { refreshing.value = false }
}
async function run(action, success) {
  try { await action(); toast(success, 'success'); await load() }
  catch (error) { toast(error.message, 'error') }
}
const start = (id) => run(() => startOptimizationTask(id), '任务已开始，已冻结执行前 7 日基线')
const complete = (id, note) => run(() => completeOptimizationTask(id, note), '已记录执行完成')
const cancel = (id) => run(() => cancelOptimizationTask(id), '任务已取消')
const refreshOne = (id) => run(() => refreshOptimizationTask(id), '复盘状态已刷新')
function optimizationUpdated() { load() }
function dataUpdated() { refreshAll({ quiet: true }) }
watch(() => app.selectedShopId, () => refreshAll({ quiet: true }))
watch(status, load)
onMounted(() => { refreshAll({ quiet: true }); window.addEventListener('pdd:optimization-updated', optimizationUpdated); window.addEventListener('pdd:data-updated', dataUpdated) })
onBeforeUnmount(() => { window.removeEventListener('pdd:optimization-updated', optimizationUpdated); window.removeEventListener('pdd:data-updated', dataUpdated) })
</script>

<template>
  <section class="page-content optimization-page">
    <div class="optimization-summary-grid">
      <article class="stat-card"><span>全部任务</span><strong>{{ counts.total }}</strong><small>当前筛选范围</small></article>
      <article class="stat-card"><span>待执行</span><strong>{{ counts.planned }}</strong><small>尚未冻结基线</small></article>
      <article class="stat-card"><span>执行中</span><strong>{{ counts.in_progress }}</strong><small>等待完成与复盘</small></article>
      <article class="stat-card"><span>已改善</span><strong>{{ counts.improved }}</strong><small>至少一次复盘改善</small></article>
    </div>

    <div class="toolbar card compact optimization-toolbar">
      <select v-model="status">
        <option value="all">全部状态</option><option value="planned">待执行</option><option value="in_progress">执行中</option><option value="completed">已完成</option><option value="cancelled">已取消</option>
      </select>
      <span class="helper-text">复盘窗口：执行后 3 / 7 / 14 天</span>
      <button class="button secondary" :disabled="refreshing || !app.selectedShopId" @click="refreshAll()">{{ refreshing ? '刷新中…' : '刷新全部复盘' }}</button>
    </div>

    <div v-if="loading" class="loading-block">正在读取优化任务…</div>
    <div v-else-if="!items.length" class="empty-state card">暂无优化任务。可以从 SKU 诊断详情中选择一个建议，创建第一条优化任务。</div>
    <div v-else class="optimization-task-list">
      <TaskCard v-for="task in items" :key="task.id" :task="task" @start="start" @complete="complete" @cancel="cancel" @refresh="refreshOne" />
    </div>
  </section>
</template>
